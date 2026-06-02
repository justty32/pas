# 教學：新增 NPC 種類

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/`。
>
> **F7 後更新**：NPC 生成已改為 YAML 原型系統（`data/game_prototypes.yaml` + `PrototypeManager`），本教學反映新流程。

本教學說明如何在現有的 `putit / warrior / bat` 三種 NPC 之外加入新種類（以「Golem」為例）。改動跨五個位置，但每步都很局部。

---

## 修改點一覽

| 步驟 | 位置 | 改動 |
|---|---|---|
| ① 宣告種類 enum | `src/core/components/combat_stats_component.h` | 在 `NpcVariant` 加新值 |
| ② 加 YAML 原型 | `data/game_prototypes.yaml` | 繼承 `BaseNpc`，設定 CombatStats 數值 |
| ③ 加在地化名稱 | `data/locale/zh-TW.yaml` | `npc.golem: "石像鬼"` |
| ④ 調整生成機率 | `src/gbind/opennefia_world_gd.cpp` → `pick_proto` lambda | 加機率分支回傳 `"Golem"` |
| ⑤ 設定渲染顏色 | `src/gbind/opennefia_world_gd.cpp` → `generate_map_image()` | 加 `switch` case（RGB 顏色） |

---

## 1. 在 `NpcVariant` 加新值

**`src/core/components/combat_stats_component.h`**

```cpp
// 原本
enum class NpcVariant : uint8_t { putit=0, warrior=1, bat=2 };

// 改成（加 golem=3）
enum class NpcVariant : uint8_t { putit=0, warrior=1, bat=2, golem=3 };
```

`NpcVariant` 以 `uint8_t` 儲存，直接序列化進 `CombatStatsComponent::serialize()`，**不需要修改 all_components.h 或序列化代碼**。新值必須大於現有最大值（bat=2），舊存檔中未知值（如升級前存的 golem=3）走 `switch` 的 `default` 分支安全降級。

---

## 2. 加 YAML 原型

**`data/game_prototypes.yaml`**，在 `Bat` 定義後加入：

```yaml
# Golem：重裝・高HP低速（灰）  HP = 25 + 5/層  ATK 4  MOV 25
- id: "Golem"
  parent: "BaseNpc"
  components:
    CombatStats:
      base_hp: 25
      hp_per_floor: 5
      attack: 4
      move_chance: 25
      variant: 3
```

設計說明：
- `parent: "BaseNpc"` 自動繼承 `NpcAiComponent`，不需要重複宣告。
- `base_hp + (floor-1)*hp_per_floor` 在 `setup_map()` 生成後自動套用。
- `variant: 3` 對應 `NpcVariant::golem`（渲染顏色依步驟 ⑤ 選擇）。

---

## 3. 加在地化名稱

**`data/locale/zh-TW.yaml`**：

```yaml
npc.golem: "石像鬼"
```

Signal（`hero_bumped_npc` / `npc_died`）會自動呼叫 `locale.get("npc.golem", fallback)` 取得顯示名稱。

---

## 4. 調整 `pick_proto` 生成機率

**`src/gbind/opennefia_world_gd.cpp`**，`setup_map()` 裡的 `pick_proto` lambda（約 `cpp:218`）：

```cpp
auto pick_proto = [&](int /*idx*/) -> std::string {
    std::uniform_int_distribution<int> d(0, 9);
    int r = d(rng);
    if (current_floor_ <= 2)
        return (r < 6) ? "Putit" : (r < 8) ? "Bat" : "Golem";
    if (current_floor_ <= 4) {
        if (r < 2) return "Putit";
        if (r < 5) return "Warrior";
        if (r < 8) return "Bat";
        return "Golem";
    }
    // 深層：golem 比例提高
    if (r < 1) return "Putit";
    if (r < 4) return "Warrior";
    if (r < 7) return "Bat";
    return "Golem";
};
```

---

## 5. 設定渲染顏色

**`generate_map_image()`**，NPC 顏色 switch（約 `cpp:390`）：

```cpp
if (const auto* stats = em_.registry().try_get<opennefia::CombatStatsComponent>(e)) {
    switch (stats->variant) {
        case opennefia::NpcVariant::putit:   nc = Color(0.60f, 0.20f, 0.70f); break;  // 紫
        case opennefia::NpcVariant::warrior: nc = Color(0.90f, 0.50f, 0.10f); break;  // 橙
        case opennefia::NpcVariant::bat:     nc = Color(0.20f, 0.80f, 0.90f); break;  // 青
        case opennefia::NpcVariant::golem:   nc = Color(0.65f, 0.65f, 0.65f); break;  // 灰
        default: break;
    }
}
```

---

## 6. 驗證

重建 GDExtension（Linux）：

```bash
cmake -S . -B build -DOPENNEFIA_BUILD_GDEXTENSION=ON
cmake --build build --target opennefia_gd
cp build/bin/libopennefia_gd.so godot_test/bin/
```

跑 C++ 測試確認 52 cases 未破壞：

```bash
cd build && ctest --output-on-failure
```

`CombatStatsComponent` 的 round-trip 序列化測試（`test_serialize.cpp`）會驗證 `variant` 欄位仍正常序列化。

---

## 設計備注

- `NpcVariant` 加值只需大於現有最大值；舊存檔出現未知值時 `switch default` 安全降級。
- 移動機率 `move_chance` 直接寫在 YAML，`npc_ai_system.cpp` 讀取並骰點，Golem 設 25% 表示它每 4 回合才移動一次。
- `pick_proto` 回傳的是**原型 id 字串**（"Golem"），`pm_.spawn()` 根據 YAML 定義建立實體，無需修改其他 C++ 代碼。
- 若不需要特殊渲染顏色，步驟 ⑤ 可省略（`default` 分支會用 `npc_color` 紅色）。
