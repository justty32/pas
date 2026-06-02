# 教學：新增物品類型

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/`。

本教學說明如何在現有的 `health_potion`（回血藥）之外加入新種類物品，並讓英雄走上去時觸發不同效果。

---

## 修改點一覽

| 步驟 | 檔案 | 改動 |
|---|---|---|
| ① 宣告新類型 | `src/core/components/item_component.h` | 在 `ItemType` 加新 enum 值 |
| ② 加拾取效果 | `src/gbind/opennefia_world_gd.cpp` → `move()` | 把 `if` 改成 `switch`，加新 case |
| ③ 調整生成（選用） | `src/gbind/opennefia_world_gd.cpp` → `setup_map()` | 讓部分房間生成新物品 |
| ④ GDScript UI | `godot_test/map_view.gd` | 在 `_on_item_picked_up` 顯示不同提示文字 |

---

## 1. 在 `ItemType` 加新值

**`src/core/components/item_component.h`**（約 `item_component.h:5`）：

```cpp
// 原本
enum class ItemType : uint8_t { health_potion = 0 };

// 改成（加 max_hp_boost）
enum class ItemType : uint8_t {
    health_potion = 0,   // 立即回血
    max_hp_boost  = 1    // 永久提升最大 HP
};
```

`ItemType` 直接序列化進 `ItemComponent::serialize()`，不需要修改 `all_components.h`。

---

## 2. 在 `move()` 加拾取效果

**`src/gbind/opennefia_world_gd.cpp`**，`move()` 裡的物品拾取段落（約 `cpp:393`）：

```cpp
// 原本（只處理 health_potion）
if (item.type == opennefia::ItemType::health_potion) {
    auto* hp = reg.try_get<opennefia::HealthComponent>(hero_entity_);
    if (hp) hp->hp = std::min(hp->hp + item.value, hp->max_hp);
}

// 改成（switch 分支，容納多種類型）
switch (item.type) {
    case opennefia::ItemType::health_potion: {
        auto* hp = reg.try_get<opennefia::HealthComponent>(hero_entity_);
        if (hp) hp->hp = std::min(hp->hp + item.value, hp->max_hp);
        break;
    }
    case opennefia::ItemType::max_hp_boost: {
        auto* hp = reg.try_get<opennefia::HealthComponent>(hero_entity_);
        if (hp) {
            hp->max_hp += item.value;   // value 作「提升量」
            hp->hp     += item.value;   // 順便補滿差額
        }
        break;
    }
    default:
        break;
}
```

`item.value` 欄位在不同類型下語義不同：`health_potion` 用作「回血量」，`max_hp_boost` 用作「HP 上限提升量」。

---

## 3. 在 `setup_map()` 生成新物品（選用）

**`src/gbind/opennefia_world_gd.cpp`**，物品生成段落（約 `cpp:185`）：

```cpp
// 原本：每個中間房間 60% 機率生成 health_potion
{
    std::uniform_int_distribution<int> chance(0, 99);
    int heal_val = 8 + (current_floor_ - 1) * 2;
    for (int r = 1; r < n_rooms - 1; ++r) {
        if (chance(rng) >= 60) continue;
        auto e = em_.create();
        em_.emplace<opennefia::MetaDataComponent>(e, "health_potion", true);
        em_.emplace<opennefia::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
        em_.emplace<opennefia::ItemComponent>(e);
        em_.get<opennefia::ItemComponent>(e).value = heal_val;
    }
}

// 改成：15% 機率生成 max_hp_boost，其餘 45% 生成 health_potion（合計仍 60%）
{
    std::uniform_int_distribution<int> chance(0, 99);
    int heal_val   = 8 + (current_floor_ - 1) * 2;
    int boost_val  = 3 + (current_floor_ - 1);       // 深層 HP 上限提升更多
    for (int r = 1; r < n_rooms - 1; ++r) {
        int roll = chance(rng);
        if (roll >= 60) continue;   // 40% 空房間
        auto e = em_.create();
        if (roll < 15) {
            // 15% 生成 max_hp_boost（稀有）
            em_.emplace<opennefia::MetaDataComponent>(e, "max_hp_boost", true);
            em_.emplace<opennefia::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
            em_.emplace<opennefia::ItemComponent>(e,
                opennefia::ItemComponent{ opennefia::ItemType::max_hp_boost, boost_val });
        } else {
            // 45% 生成 health_potion（一般）
            em_.emplace<opennefia::MetaDataComponent>(e, "health_potion", true);
            em_.emplace<opennefia::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
            em_.emplace<opennefia::ItemComponent>(e);
            em_.get<opennefia::ItemComponent>(e).value = heal_val;
        }
    }
}
```

---

## 4. GDScript 端 UI（選用）

**`godot_test/map_view.gd`**，`_on_item_picked_up` 回調：

```gdscript
func _on_item_picked_up(item_name: String, value: int) -> void:
    match item_name:
        "health_potion":
            info_label.text = "拾取回血藥（+%d HP）" % value
        "max_hp_boost":
            info_label.text = "拾取強化藥水（最大 HP +%d）" % value
        _:
            info_label.text = "拾取物品：%s" % item_name
```

`item_picked_up` signal 的第二個參數 `heal_amount` 在 `max_hp_boost` 情境下實際意義是「HP 上限提升量」。GDScript 端用 `match` 依名稱分支，可以顯示不同說明文字。

---

## 設計備注

- **`ItemComponent::value` 的語義**：此欄位沒有強型別語義，靠呼叫端約定。若未來物品種類很多，建議把效果做成獨立 component（如 `HealOnPickupComponent { int amount; }`）並由拾取系統依 component 決定行為——這樣每個效果可以疊加在同一個 entity 上。
- **物品渲染**：現有 `generate_map_image()` 對所有 `ItemComponent` 統一顯示綠點（`Color(0.20, 0.85, 0.40)`）。若想區分，可在顏色 block 查 `item.type`，對 `max_hp_boost` 改用金色（`Color(1.0, 0.8, 0.0)`）。
