# 教學：如何擴充 opennefia-cpp 這套系統

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/`。

本教學面向已看過架構總結（`architecture/summary.md`）的開發者，說明在**不破壞現有測試的前提下**，如何一步步擴充這套系統的四個主要面向。

---

## 1. 新增一個 Component（核心層）

以「新增 `HealthComponent`」為例。

### 步驟

**① 定義 struct**（`src/core/components/health_component.h`）

```cpp
#pragma once
#include <cstdint>

namespace opennefia {

struct HealthComponent {
    int max_hp{ 10 };
    int cur_hp{ 10 };

    bool is_dead() const { return cur_hp <= 0; }

    template<class Archive>
    void serialize(Archive& ar) { ar(max_hp, cur_hp); }
};

} // namespace opennefia
```

**② 加入 `AllComponents`**（`src/core/serialize/all_components.h`）

```cpp
// 改這一行：
using AllComponents = entt::type_list<
    MetaDataComponent,
    SpatialComponent,
    MapData,
    HealthComponent   // ← 新增
>;
```

這一改，`save_load.h` 的 fold expression 會自動把 `HealthComponent` 納入 snapshot 存讀。

**③ 視需要加 YAML ComponentLoader**（若原型 YAML 要設定 HP）

```cpp
// 在使用 PrototypeManager 的地方（如測試或遊戲初始化）：
pm.register_loader("Health", [](auto& reg, auto e, const auto& n) {
    opennefia::HealthComponent h;
    if (n["max_hp"]) h.max_hp = n["max_hp"].as<int>();
    h.cur_hp = h.max_hp;
    reg.emplace_or_replace<opennefia::HealthComponent>(e, h);
});
```

**④ 在 YAML 原型中使用**（`data/test_prototypes.yaml`）

```yaml
- id: Putit
  parent: BaseChara
  components:
    Health: { max_hp: 30 }
```

**測試方式**：重建後跑 `ctest`，現有 36 cases 應全部繼續通過。再寫一個 `CHECK(em.has<HealthComponent>(e))` 的新測試。

---

## 2. 新增一個系統（自由函式）

以「每 tick 回復 1 HP 的再生系統」為例。

### 步驟

**① 寫自由函式**（可放在 `src/core/systems/regen_system.cpp`）

```cpp
#include <entt/entt.hpp>
#include "core/ecs/system_ctx.h"
#include "core/components/health_component.h"

namespace opennefia {

void regen_system(entt::registry& reg, SystemCtx& ctx) {
    auto view = reg.view<HealthComponent>();
    for (auto e : view) {
        auto& hp = view.get<HealthComponent>(e);
        if (hp.cur_hp < hp.max_hp) {
            ++hp.cur_hp;
        }
    }
}

} // namespace opennefia
```

**② 在 EntityManager 登錄**

```cpp
em.add_system(opennefia::regen_system);
// 或用 lambda：
em.add_system([](entt::registry& reg, SystemCtx& ctx) {
    // ...
});
```

**關鍵原則**：系統是無狀態自由函式，所有需要的服務透過 `SystemCtx` 傳入。執行順序就是 `add_system` 的呼叫順序，無需額外排序標記。

---

## 3. 新增一種地圖地形

以「新增「深水」地形（不可走、不擋視線）」為例。

### 步驟

**① 定義 terrain ID 常數**（建議放 `src/core/maps/terrain_defs.h`）

```cpp
#pragma once
#include <cstdint>

namespace opennefia {
    inline constexpr uint16_t TERRAIN_FLOOR     = 0;
    inline constexpr uint16_t TERRAIN_WALL      = 1;
    inline constexpr uint16_t TERRAIN_DEEP_WATER = 2;
}
```

**② 在建圖時設定 flags**

```cpp
auto& tile = map.at(x, y);
tile.terrain = opennefia::TERRAIN_DEEP_WATER;
tile.flags   = 0;  // 不可走（!TILE_WALKABLE）、不擋視線（!TILE_BLOCKS_SIGHT）
```

**③ 在 GDExtension 端加渲染顏色**（`opennefia_world_gd.cpp`）

在 `generate_map_image` 的 tile 迴圈中改用 terrain id 決定顏色：

```cpp
Color c;
switch (map.at(x, y).terrain) {
    case 0:  c = floor_color; break;   // TERRAIN_FLOOR
    case 1:  c = wall_color;  break;   // TERRAIN_WALL
    case 2:  c = Color(0.10f, 0.20f, 0.55f); break;  // TERRAIN_DEEP_WATER
    default: c = floor_color; break;
}
```

---

## 4. 橋接新資料到 Godot（gbind 層）

以「在 GDScript 取得 hero 的 HP」為例。

### 步驟

**① 在 `OpenNefiaWorld` 加 C++ 方法**（`src/gbind/opennefia_world_gd.h`）

```cpp
int get_hero_hp() const;
int get_hero_max_hp() const;
```

**② 實作**（`src/gbind/opennefia_world_gd.cpp`）

```cpp
int opennefia_gd::OpenNefiaWorld::get_hero_hp() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    const auto* hp = em_.registry().try_get<opennefia::HealthComponent>(hero_entity_);
    return hp ? hp->cur_hp : 0;
}
```

**③ 在 `_bind_methods()` 登錄**

```cpp
ClassDB::bind_method(D_METHOD("get_hero_hp"),     &OpenNefiaWorld::get_hero_hp);
ClassDB::bind_method(D_METHOD("get_hero_max_hp"), &OpenNefiaWorld::get_hero_max_hp);
```

**④ GDScript 使用**

```gdscript
info_label.text = "HP: %d/%d" % [world.get_hero_hp(), world.get_hero_max_hp()]
```

**重建**：`cmake --build build --target opennefia_gd`，複製 .dll 到 `godot_test/bin/`。

---

## 5. 新增一個 GDExtension 類別

當需要暴露一套新功能（如 FOV 計算）時，建一個新的 `RefCounted` 工具類。

### 步驟

**① 建 `src/gbind/opennefia_fov_gd.h`**

```cpp
#pragma once
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>

namespace opennefia_gd {

class OpenNefiaFov : public godot::RefCounted {
    GDCLASS(OpenNefiaFov, godot::RefCounted)
protected:
    static void _bind_methods();
public:
    // 傳入 World node，計算以 (cx,cy) 為中心、半徑 r 的可視格子
    // 回傳 PackedVector2Array（GDScript 直接可用）
    godot::PackedVector2Array compute_fov(
        godot::Object* world_node, int cx, int cy, int radius);
};

} // namespace opennefia_gd
```

**② 建 `.cpp`**，實作 `_bind_methods()` + 計算邏輯

**③ 在 `register_types.cpp` 加入**

```cpp
#include "opennefia_fov_gd.h"
// ...
GDREGISTER_CLASS(opennefia_gd::OpenNefiaFov);
```

**④ GDScript 使用**

```gdscript
var fov := OpenNefiaFov.new()
var visible_cells := fov.compute_fov(world, hero_x, hero_y, 5)
```

---

## 速查：各層修改點

| 要做的事 | 改哪裡 |
|---|---|
| 新增 component 定義 | `src/core/components/xxx_component.h` |
| 讓 component 可序列化 | `src/core/serialize/all_components.h`（加一行） |
| 讓 component 從 YAML 載入 | `register_loader()` 呼叫（遊戲初始化時） |
| 新增系統邏輯 | 自由函式 + `em.add_system()` |
| 新地形外觀 | `src/core/maps/terrain_defs.h` + `generate_map_image` switch |
| 暴露資料給 GDScript | `opennefia_world_gd.h+cpp` 新增方法 + `_bind_methods()` |
| 新的 GDExtension 工具類 | 新 `xxxxx_gd.h+cpp` + `register_types.cpp` |
| 重建並更新 DLL | `cmake --build build --target opennefia_gd` + 複製 .dll |
