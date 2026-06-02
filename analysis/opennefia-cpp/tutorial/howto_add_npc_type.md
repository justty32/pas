# 教學：新增 NPC 種類

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/`。

本教學說明如何在現有的 `putit / warrior / bat` 三種 NPC 之外加入新種類。這個改動橫跨四個檔案，但每步都很局部，不影響現有 36 個測試。

---

## 修改點一覽

| 步驟 | 檔案 | 改動 |
|---|---|---|
| ① 宣告種類 | `src/core/components/combat_stats_component.h` | 在 `NpcVariant` 加新 enum 值 |
| ② 調整生成機率 | `src/gbind/opennefia_world_gd.cpp` → `pick_variant` | 加機率分支 |
| ③ 設定數值 | `src/gbind/opennefia_world_gd.cpp` → `setup_map()` switch | 加 case（HP / 攻擊 / 移動機率 / 名稱） |
| ④ 設定顏色 | `src/gbind/opennefia_world_gd.cpp` → `generate_map_image()` | 加 case（RGB 顏色） |

---

## 1. 在 `NpcVariant` 加新值

**`src/core/components/combat_stats_component.h`**

```cpp
// 原本（combat_stats_component.h:5）
enum class NpcVariant : uint8_t { putit=0, warrior=1, bat=2 };

// 改成（加 golem=3）
enum class NpcVariant : uint8_t { putit=0, warrior=1, bat=2, golem=3 };
```

`NpcVariant` 以 `uint8_t` 儲存，直接序列化進 `CombatStatsComponent::serialize()`，**不需要修改 all_components.h 或序列化代碼**。

---

## 2. 調整 `pick_variant` 生成機率

**`src/gbind/opennefia_world_gd.cpp`**，`setup_map()` 裡的 lambda（約 `cpp:141`）：

```cpp
auto pick_variant = [&](int npc_idx) -> opennefia::NpcVariant {
    std::uniform_int_distribution<int> d(0, 9);
    int r = d(rng);
    if (current_floor_ <= 2) {
        // 原始：70% putit + 30% bat
        // 改成：60% putit + 20% bat + 20% golem（新）
        if (r < 6) return opennefia::NpcVariant::putit;
        if (r < 8) return opennefia::NpcVariant::bat;
        return opennefia::NpcVariant::golem;
    } else if (current_floor_ <= 4) {
        if (r < 2) return opennefia::NpcVariant::putit;
        if (r < 5) return opennefia::NpcVariant::warrior;
        if (r < 8) return opennefia::NpcVariant::bat;
        return opennefia::NpcVariant::golem;
    } else {
        // 深層：golem 比例提高
        if (r < 1) return opennefia::NpcVariant::putit;
        if (r < 4) return opennefia::NpcVariant::warrior;
        if (r < 6) return opennefia::NpcVariant::bat;
        return opennefia::NpcVariant::golem;
    }
};
```

---

## 3. 在 switch 加設定數值

**同一個函式**，switch 區塊（約 `cpp:163`）：

```cpp
switch (variant) {
    case opennefia::NpcVariant::putit:
        npc_hp = 6  + (current_floor_ - 1);     atk = 1; mv = 40; vname = "putit";   break;
    case opennefia::NpcVariant::warrior:
        npc_hp = 15 + (current_floor_ - 1) * 3; atk = 3; mv = 65; vname = "warrior"; break;
    case opennefia::NpcVariant::bat:
        npc_hp = 5  + (current_floor_ - 1);     atk = 2; mv = 90; vname = "bat";     break;
    // ↓ 新增
    case opennefia::NpcVariant::golem:
        npc_hp = 25 + (current_floor_ - 1) * 5; atk = 4; mv = 25; vname = "golem";  break;
    default:
        npc_hp = 10; atk = 2; mv = 50; vname = "npc"; break;
}
```

Golem 設計：高 HP（25 起）、高攻（4 dmg）、低移速（25%），在深層作為「坦克型 Boss NPC」。

---

## 4. 設定渲染顏色

**`generate_map_image()`**，NPC 顏色 switch（約 `cpp:312`）：

```cpp
if (const auto* stats = em_.registry().try_get<opennefia::CombatStatsComponent>(e)) {
    switch (stats->variant) {
        case opennefia::NpcVariant::putit:   nc = Color(0.60f, 0.20f, 0.70f); break;  // 紫
        case opennefia::NpcVariant::warrior: nc = Color(0.90f, 0.50f, 0.10f); break;  // 橙
        case opennefia::NpcVariant::bat:     nc = Color(0.20f, 0.80f, 0.90f); break;  // 青
        // ↓ 新增（灰色，配合「石像」形象）
        case opennefia::NpcVariant::golem:   nc = Color(0.65f, 0.65f, 0.65f); break;
        default: break;
    }
}
```

---

## 5. 驗證

重建 GDExtension：

```powershell
cmake -S . -B build -DOPENNEFIA_BUILD_GDEXTENSION=ON
cmake --build build --target opennefia_gd
# 複製 build/bin/opennefia_gd.dll → godot_test/bin/opennefia_gd.dll
```

跑 C++ 測試確認未破壞現有 36 cases：

```powershell
cd build && ctest --output-on-failure
```

測試不直接涉及 `NpcVariant`（無對應 test case），但 `CombatStatsComponent` 的 round-trip 序列化測試（`test_serialize.cpp`）會驗證 `serialize()` 函式仍正常。

---

## 設計備注

- **移動機率（`move_chance`）** 由 `npc_ai_system.cpp` 在每個 tick 骰點決定 NPC 是否行動。Golem 設 25% 意味它約每 4 回合才移動一次，但一旦追到就很危險。
- `NpcVariant` 加的新值必須大於現有最大值（目前 bat=2），因為 enum 值作為 `uint8_t` 存入存檔。若舊存檔有未知值（如舊存檔沒有 golem=3），讀出後落入 `switch` 的 `default` 分支，安全降級為預設 NPC。
