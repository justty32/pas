# gamecore-zone 重構實作計劃

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 從 opennefia-cpp hard fork 出 `derived/gamecore-zone/`，刪除 OpenNefia 特有機制，建立乾淨的 gamecore 區域層（Area Layer）ECS 基底，回合制 Actor poll 模式。

**Architecture:** CMake STATIC `zone_core`（godot-free）+ 選用 GDExtension `zone_gd`。ECS 以 EnTT 為核心，`ActorComponent` 空 tag 標記有行動資格的實體，`advance_turn()` 輪詢所有 Actor 實體執行對應系統。服務層（ServiceContext/CVar/Locale/Prototype）全部刪除，用編譯期常數取代。

**Tech Stack:** C++20、EnTT v3.16.0、cereal v1.3.2、spdlog v1.14.1、doctest v2.4.11、godot-cpp 4.6（GDExtension 選用）

---

## 檔案結構（完成後）

```
derived/gamecore-zone/
├── CMakeLists.txt
├── PROJECT.md
├── src/core/
│   ├── ecs/entity_manager.h/.cpp, system_ctx.h
│   ├── components/
│   │   ├── actor_component.h        ← NEW
│   │   ├── combat_stats_component.h ← 簡化
│   │   ├── health_component.h
│   │   ├── hero_component.h
│   │   ├── item_component.h         ← 簡化（移除 value_per_floor）
│   │   ├── npc_ai_component.h
│   │   ├── spatial_component.h
│   │   └── world_state_component.h
│   ├── maps/map_data.h, map_gen.h/.cpp, tile.h
│   ├── serialize/all_components.h, entt_cereal_archive.h, save_load.h, save_store.h
│   ├── systems/fov_system.h/.cpp, npc_ai_system.h/.cpp
│   └── util/resource_path.h, vector2i.h
├── src/gbind/
│   ├── register_types.h/.cpp
│   ├── zone_core_gd.h/.cpp
│   └── zone_world_gd.h/.cpp         ← 重構
├── godot_zone/
│   ├── project.godot, zone.gdextension, verify.gd, bin/
└── tests/src/
    ├── main.cpp, smoke_test.cpp
    ├── test_ecs.cpp      ← 更新
    ├── test_npc_combat.cpp ← 更新（加 ActorComponent）
    ├── test_phase4.cpp   ← 更新
    └── test_serialize.cpp ← 更新
```

已刪除：`prototypes/`, `locale/`, `cvar/`, `event_bus.h`, `meta_data_component.h`, `services/`, `test_prototypes.cpp`, `test_locale.cpp`, `test_cvar.cpp`

---

## Task 1: Fork — 複製 opennefia-cpp 到 gamecore-zone

**Files:**
- Create: `derived/gamecore-zone/`（從 opennefia-cpp 複製）

- [ ] **Step 1: 複製 src、tests、data、godot_test 目錄**

```bash
cd /home/lorkhan/repo/pas
rsync -av --exclude='build/' --exclude='*.so' --exclude='*.dll' \
  --exclude='.godot/' --exclude='*.uid' \
  derived/opennefia-cpp/src/ derived/gamecore-zone/src/
rsync -av derived/opennefia-cpp/tests/ derived/gamecore-zone/tests/
rsync -av derived/opennefia-cpp/CMakeLists.txt derived/gamecore-zone/CMakeLists.txt
```

- [ ] **Step 2: 複製 godot_test → godot_zone**

```bash
rsync -av --exclude='.godot/' --exclude='*.uid' --exclude='bin/*.so' --exclude='bin/*.dll' \
  derived/opennefia-cpp/godot_test/ derived/gamecore-zone/godot_zone/
```

- [ ] **Step 3: 建立 PROJECT.md**

建立 `derived/gamecore-zone/PROJECT.md`，內容：
```markdown
# PROJECT — gamecore-zone

gamecore 三層架構（World/Region/Area）的第三層——區域層（Area Layer）。
Hard fork 自 derived/opennefia-cpp/，保留 ECS/FOV/戰鬥，刪除 OpenNefia 特有機制。
設計文件：docs/superpowers/specs/2026-06-03-gamecore-zone-design.md
```

- [ ] **Step 4: Confirm files exist**

```bash
ls derived/gamecore-zone/src/core/ && ls derived/gamecore-zone/godot_zone/
```
Expected: 見到 `ecs/`, `components/`, `maps/`, 以及 `project.godot`, `verify.gd`

---

## Task 2: 刪除不需要的子系統

**Files:**
- Delete: `src/core/prototypes/`, `src/core/locale/`, `src/core/cvar/`, `src/core/services/`
- Delete: `src/core/ecs/event_bus.h`, `src/core/components/meta_data_component.h`
- Delete: `tests/src/test_prototypes.cpp`, `tests/src/test_locale.cpp`, `tests/src/test_cvar.cpp`
- Delete: `data/` 目錄（YAML 原型/語言檔）

- [ ] **Step 1: 刪除服務層與 OpenNefia 特有模組**

```bash
cd derived/gamecore-zone
rm -rf src/core/prototypes src/core/locale src/core/cvar src/core/services
rm -f  src/core/ecs/event_bus.h
rm -f  src/core/components/meta_data_component.h
rm -f  tests/src/test_prototypes.cpp tests/src/test_locale.cpp tests/src/test_cvar.cpp
rm -rf data
```

- [ ] **Step 2: 刪除 gbind 中的舊命名檔（之後用新名重建）**

```bash
rm -f src/gbind/opennefia_core_gd.h src/gbind/opennefia_core_gd.cpp
rm -f src/gbind/opennefia_world_gd.h src/gbind/opennefia_world_gd.cpp
```

- [ ] **Step 3: 確認刪除**

```bash
ls src/core/ && ls tests/src/
```
Expected: `prototypes/`, `locale/`, `cvar/`, `services/` 均不再出現

---

## Task 3: 全域改名 opennefia → zone

**Files:**
- Modify: `src/` 下所有 `.h`, `.cpp`；`tests/src/` 下所有 `.cpp`；`CMakeLists.txt`

- [ ] **Step 1: namespace 與前綴替換**

```bash
cd /home/lorkhan/repo/pas/derived/gamecore-zone
# namespace opennefia → namespace zone
find src tests -name '*.h' -o -name '*.cpp' | \
  xargs sed -i 's/namespace opennefia/namespace zone/g; s/opennefia::/zone::/g'

# include guard 與命名
find src tests -name '*.h' -o -name '*.cpp' | \
  xargs sed -i 's/OPENNEFIA_/ZONE_/g; s/opennefia_/zone_/g'

# CMakeLists 目標名
sed -i 's/opennefia_core/zone_core/g; s/opennefia_gd/zone_gd/g; \
        s/opennefia_cpp/gamecore_zone/g; s/OPENNEFIA_BUILD_GDEXTENSION/ZONE_BUILD_GDEXTENSION/g; \
        s/OPENNEFIA_DATA_DIR/ZONE_DATA_DIR/g' CMakeLists.txt
```

- [ ] **Step 2: class / struct 大寫前綴替換（OpenNefia → Zone）**

```bash
find src tests -name '*.h' -o -name '*.cpp' | \
  xargs sed -i 's/OpenNefiaWorld/ZoneWorld/g; s/OpenNefiaCore/ZoneCore/g; \
                s/opennefia_gd::/zone_gd::/g'
```

- [ ] **Step 3: godot_zone 目錄內的 gdextension 描述檔**

```bash
# zone.gdextension（從 godot_zone/ 裡改名並更新）
mv godot_zone/opennefia.gdextension godot_zone/zone.gdextension 2>/dev/null || true
sed -i 's/opennefia/zone/g; s/OpenNefia/Zone/g' godot_zone/zone.gdextension 2>/dev/null || true
find godot_zone -name '*.gd' | xargs sed -i 's/OpenNefiaWorld/ZoneWorld/g; s/opennefia/zone/g' 2>/dev/null || true
```

- [ ] **Step 4: 快速確認**

```bash
grep -r 'opennefia' src/ tests/ CMakeLists.txt 2>/dev/null | grep -v 'Binary' | head -20
```
Expected: 零輸出（或只剩註解中的說明文字）

---

## Task 4: 簡化 CombatStatsComponent 和 ItemComponent

**Files:**
- Modify: `src/core/components/combat_stats_component.h`
- Modify: `src/core/components/item_component.h`

- [ ] **Step 1: 寫新版 CombatStatsComponent（移除 NpcVariant、base_hp、hp_per_floor）**

覆寫 `src/core/components/combat_stats_component.h`：
```cpp
#pragma once
#include <cstdint>

namespace zone {

struct CombatStatsComponent {
    int attack{ 2 };
    int move_chance{ 50 };

    template<class Archive>
    void serialize(Archive& ar) { ar(attack, move_chance); }
};

} // namespace zone
```

- [ ] **Step 2: 寫新版 ItemComponent（移除 value_per_floor）**

覆寫 `src/core/components/item_component.h`：
```cpp
#pragma once
#include <cstdint>

namespace zone {

enum class ItemType : uint8_t {
    health_potion = 0,
};

struct ItemComponent {
    ItemType type{ ItemType::health_potion };
    int      value{ 8 };

    template<class Archive>
    void serialize(Archive& ar) { ar(type, value); }
};

} // namespace zone
```

---

## Task 5: 新增 ActorComponent 空 tag

**Files:**
- Create: `src/core/components/actor_component.h`
- Modify: `src/core/serialize/all_components.h`

- [ ] **Step 1: 寫 ActorComponent**

建立 `src/core/components/actor_component.h`：
```cpp
#pragma once

namespace zone {

// ActorComponent — 空 tag，標記「有行動資格」的實體（英雄、NPC）。
// advance_turn() 的 actor poll 依此 tag 選取行動者；物品、地形等不掛此 tag。
struct ActorComponent {};

} // namespace zone
```

- [ ] **Step 2: 寫失敗測試（確認 ActorComponent 可掛上 entity）**

在 `tests/src/test_ecs.cpp` 末尾加入（文件最後一個 TEST_CASE 後）：

```cpp
#include <core/components/actor_component.h>

TEST_CASE("ActorComponent — 可作為 actor poll 標記") {
    zone::EntityManager em;
    auto hero = em.create();
    auto item = em.create();

    em.registry().emplace<zone::ActorComponent>(hero);
    // item 不掛 ActorComponent

    auto actors = em.registry().view<zone::ActorComponent>();
    int count = 0;
    for (auto e : actors) {
        (void)e;
        ++count;
    }
    CHECK(count == 1);
    CHECK(em.registry().all_of<zone::ActorComponent>(hero));
    CHECK_FALSE(em.registry().all_of<zone::ActorComponent>(item));
}
```

- [ ] **Step 3: 嘗試 build（預期因 all_components.h 還未加 ActorComponent 而可能警告，但測試需能編譯）**

```bash
cd /home/lorkhan/repo/pas/derived/gamecore-zone
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug 2>&1 | tail -5 && cmake --build build -j$(nproc) 2>&1 | tail -20
```

- [ ] **Step 4: 更新 all_components.h（加入 ActorComponent、移除 MetaDataComponent）**

覆寫 `src/core/serialize/all_components.h`：
```cpp
#pragma once
#include <entt/entt.hpp>
#include <core/components/actor_component.h>
#include <core/components/spatial_component.h>
#include <core/maps/map_data.h>
#include <core/components/npc_ai_component.h>
#include <core/components/health_component.h>
#include <core/components/item_component.h>
#include <core/components/combat_stats_component.h>
#include <core/components/world_state_component.h>
#include <core/components/hero_component.h>

namespace zone::serialize {

using AllComponents = entt::type_list<
    ActorComponent,
    SpatialComponent,
    MapData,
    NpcAiComponent,
    HealthComponent,
    ItemComponent,
    CombatStatsComponent,
    WorldStateComponent,
    HeroComponent
>;

} // namespace zone::serialize
```

---

## Task 6: 更新 CMakeLists.txt（移除 yaml-cpp）

**Files:**
- Modify: `CMakeLists.txt`

- [ ] **Step 1: 移除 yaml-cpp FetchContent 宣告與相關設定**

在 `CMakeLists.txt` 中，刪除以下三個區塊（用 Edit 工具）：

```cmake
# 刪除 FetchContent_Declare(yaml-cpp ...) 整塊（約 4 行）
# 刪除 yaml-cpp 的選項設定（YAML_CPP_BUILD_TESTS / YAML_CPP_BUILD_TOOLS）（2 行）
# 刪除 FetchContent_MakeAvailable(...) 中的 yaml-cpp（從 entt cereal yaml-cpp spdlog doctest → entt cereal spdlog doctest）
# 刪除 yaml-cpp GCC -include cstdint workaround 整塊（約 5 行）
```

- [ ] **Step 2: 移除 zone_core 的 yaml-cpp 連結**

`target_link_libraries(zone_core ...)` 中移除 `yaml-cpp::yaml-cpp`。

- [ ] **Step 3: 確認 CMakeLists.txt 不含 yaml 字樣**

```bash
grep -n yaml CMakeLists.txt
```
Expected: 零輸出

---

## Task 7: 重建 zone_core_gd（smoke-test GDClass）

**Files:**
- Create: `src/gbind/zone_core_gd.h`
- Create: `src/gbind/zone_core_gd.cpp`

- [ ] **Step 1: 建立 zone_core_gd.h**

```cpp
#pragma once
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>

namespace zone_gd {

class ZoneCore : public godot::RefCounted {
    GDCLASS(ZoneCore, godot::RefCounted)
protected:
    static void _bind_methods();
public:
    godot::String version() const;
};

} // namespace zone_gd
```

- [ ] **Step 2: 建立 zone_core_gd.cpp**

```cpp
#include "zone_core_gd.h"
#include <core/version.h>

void zone_gd::ZoneCore::_bind_methods() {
    godot::ClassDB::bind_method(
        godot::D_METHOD("version"), &ZoneCore::version);
}

godot::String zone_gd::ZoneCore::version() {
    return godot::String(zone::version().c_str());
}
```

---

## Task 8: 重建 zone_world_gd.h

**Files:**
- Create: `src/gbind/zone_world_gd.h`

- [ ] **Step 1: 建立 zone_world_gd.h（移除 EventBus、ServiceContext、PrototypeManager）**

```cpp
#pragma once
#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/image.hpp>
#include <godot_cpp/core/class_db.hpp>

#include "core/ecs/entity_manager.h"
#include "core/ecs/system_ctx.h"

#include <entt/entt.hpp>

namespace zone_gd {

// ZoneWorld — gamecore 區域層（Area Layer）的核心 Node。
// 回合制 Actor poll 模式：advance_turn() 輪詢所有 ActorComponent 實體。
class ZoneWorld : public godot::Node {
    GDCLASS(ZoneWorld, godot::Node)

protected:
    static void _bind_methods();

public:
    ZoneWorld();
    ~ZoneWorld() override = default;

    void _ready() override;

    // ---- 地圖查詢 ----
    int  get_map_width()  const;
    int  get_map_height() const;
    bool is_walkable(int x, int y) const;
    godot::Ref<godot::Image> generate_map_image(int cell_px) const;

    // ---- 動作介面 ----
    bool move(int dx, int dy);
    void wait_turn();

    // ---- 狀態查詢 ----
    int get_hero_x()      const;
    int get_hero_y()      const;
    int get_turn_count()  const;
    int get_hero_hp()     const;
    int get_hero_max_hp() const;
    int get_npc_count()   const;
    int get_current_floor() const;
    void restart();

    // ---- 存讀檔 ----
    bool save_game(const godot::String& path);
    bool load_game(const godot::String& path);
    bool has_save_game(const godot::String& path) const;

private:
    void setup_world();
    void setup_map();
    void next_floor();
    void advance_turn();   // actor poll entry point
    void recompute_fov();

    zone::EntityManager em_;
    zone::SystemCtx     ctx_;

    entt::entity map_entity_{ entt::null };
    entt::entity hero_entity_{ entt::null };
    int turn_count_{ 0 };
    bool game_over_{ false };
    int  current_floor_{ 1 };
    bool systems_ready_{ false };
};

} // namespace zone_gd
```

---

## Task 9: 重建 zone_world_gd.cpp

**Files:**
- Create: `src/gbind/zone_world_gd.cpp`

這是最大的重構任務。原 opennefia_world_gd.cpp ~480 行，移除三個 init 函式（locale/cvar/prototype），以直接 component 賦值取代 prototype spawn，以常數取代 CVar 讀取。

- [ ] **Step 1: 建立 zone_world_gd.cpp — static binding 與 lifecycle**

```cpp
#include "zone_world_gd.h"

#include "core/components/actor_component.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"
#include "core/components/health_component.h"
#include "core/components/item_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/hero_component.h"
#include "core/components/world_state_component.h"
#include "core/maps/map_data.h"
#include "core/maps/map_gen.h"
#include "core/systems/npc_ai_system.h"
#include "core/systems/fov_system.h"
#include "core/serialize/save_load.h"

#include <algorithm>
#include <random>
#include <filesystem>
#include <godot_cpp/variant/rect2i.hpp>
#include <godot_cpp/variant/color.hpp>

using namespace godot;

// 遊戲常數（取代 CVar）
static constexpr int MAP_W          = 60;
static constexpr int MAP_H          = 40;
static constexpr int NPC_CAP_BASE   = 4;
static constexpr int NPC_CAP_MAX    = 8;
static constexpr int FOV_RADIUS     = 8;
static constexpr int ITEM_PCT       = 60;
static constexpr int HERO_HP        = 20;
static constexpr int NPC_BASE_HP    = 5;
static constexpr int NPC_HP_SCALE   = 2;   // HP += (floor-1) * NPC_HP_SCALE
static constexpr int NPC_ATK_BASE   = 2;
static constexpr int NPC_ATK_SCALE  = 1;   // attack += (floor-1) * NPC_ATK_SCALE

void zone_gd::ZoneWorld::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_map_width"),  &ZoneWorld::get_map_width);
    ClassDB::bind_method(D_METHOD("get_map_height"), &ZoneWorld::get_map_height);
    ClassDB::bind_method(D_METHOD("is_walkable", "x", "y"), &ZoneWorld::is_walkable);
    ClassDB::bind_method(D_METHOD("generate_map_image", "cell_px"), &ZoneWorld::generate_map_image);
    ClassDB::bind_method(D_METHOD("move", "dx", "dy"), &ZoneWorld::move);
    ClassDB::bind_method(D_METHOD("wait_turn"), &ZoneWorld::wait_turn);
    ClassDB::bind_method(D_METHOD("get_hero_x"),      &ZoneWorld::get_hero_x);
    ClassDB::bind_method(D_METHOD("get_hero_y"),      &ZoneWorld::get_hero_y);
    ClassDB::bind_method(D_METHOD("get_turn_count"),  &ZoneWorld::get_turn_count);
    ClassDB::bind_method(D_METHOD("get_hero_hp"),     &ZoneWorld::get_hero_hp);
    ClassDB::bind_method(D_METHOD("get_hero_max_hp"), &ZoneWorld::get_hero_max_hp);
    ClassDB::bind_method(D_METHOD("get_npc_count"),   &ZoneWorld::get_npc_count);
    ClassDB::bind_method(D_METHOD("get_current_floor"), &ZoneWorld::get_current_floor);
    ClassDB::bind_method(D_METHOD("restart"),           &ZoneWorld::restart);
    ClassDB::bind_method(D_METHOD("save_game", "path"),     &ZoneWorld::save_game);
    ClassDB::bind_method(D_METHOD("load_game", "path"),     &ZoneWorld::load_game);
    ClassDB::bind_method(D_METHOD("has_save_game", "path"), &ZoneWorld::has_save_game);

    ADD_SIGNAL(MethodInfo("world_changed"));
    ADD_SIGNAL(MethodInfo("floor_changed",
        PropertyInfo(Variant::INT, "floor_num")));
    ADD_SIGNAL(MethodInfo("hero_bumped_wall"));
    ADD_SIGNAL(MethodInfo("hero_bumped_npc",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("npc_died",
        PropertyInfo(Variant::STRING, "npc_id")));
    ADD_SIGNAL(MethodInfo("item_picked_up",
        PropertyInfo(Variant::STRING, "item_name"),
        PropertyInfo(Variant::INT,    "heal_amount")));
    ADD_SIGNAL(MethodInfo("game_over"));
}

zone_gd::ZoneWorld::ZoneWorld() = default;

void zone_gd::ZoneWorld::_ready() {
    setup_world();
    recompute_fov();
}
```

- [ ] **Step 2: setup_world / setup_map（直接 component 賦值，無原型）**

在同一 .cpp 中繼續：
```cpp
void zone_gd::ZoneWorld::setup_world() {
    setup_map();
    if (!systems_ready_) {
        em_.add_system(zone::npc_ai_system);
        systems_ready_ = true;
    }
}

void zone_gd::ZoneWorld::setup_map() {
    auto& reg = em_.registry();

    // 銷毀舊 NPC
    { std::vector<entt::entity> v;
      for (auto e : reg.view<zone::NpcAiComponent>()) v.push_back(e);
      for (auto e : v) reg.destroy(e); }

    // 銷毀舊物品
    { std::vector<entt::entity> v;
      for (auto e : reg.view<zone::ItemComponent>()) v.push_back(e);
      for (auto e : v) reg.destroy(e); }

    // 銷毀舊地圖
    if (map_entity_ != entt::null) { reg.destroy(map_entity_); map_entity_ = entt::null; }

    // 建立新地圖
    map_entity_ = em_.create();
    auto& map = em_.emplace<zone::MapData>(map_entity_, MAP_W, MAP_H);
    em_.emplace<zone::WorldStateComponent>(map_entity_,
        zone::WorldStateComponent{ turn_count_, current_floor_ });

    std::mt19937 rng(std::random_device{}());
    auto rooms = zone::generate_bsp_dungeon(map, rng);

    // 英雄：第一次建立，之後只更新位置
    int hx = rooms.empty() ? MAP_W / 2 : rooms[0].cx();
    int hy = rooms.empty() ? MAP_H / 2 : rooms[0].cy();
    if (hero_entity_ == entt::null) {
        hero_entity_ = em_.create();
        reg.emplace<zone::HeroComponent>(hero_entity_);
        reg.emplace<zone::ActorComponent>(hero_entity_);
        reg.emplace<zone::SpatialComponent>(hero_entity_, hx, hy);
        reg.emplace<zone::HealthComponent>(hero_entity_, HERO_HP, HERO_HP);
    } else {
        if (auto* sp = reg.try_get<zone::SpatialComponent>(hero_entity_))
            { sp->x = hx; sp->y = hy; }
    }

    // 樓梯
    if (rooms.size() >= 2) {
        auto& tile = map.at(rooms.back().cx(), rooms.back().cy());
        tile.flags |= zone::TILE_STAIR_DOWN;
    }

    // NPC
    int npc_cap = std::min(NPC_CAP_BASE + current_floor_, NPC_CAP_MAX);
    int npc_count = 0;
    for (int r = 1; r < (int)rooms.size() && npc_count < npc_cap; ++r, ++npc_count) {
        int hp  = NPC_BASE_HP + (current_floor_ - 1) * NPC_HP_SCALE;
        int atk = NPC_ATK_BASE + (current_floor_ - 1) * NPC_ATK_SCALE;
        auto e = em_.create();
        reg.emplace<zone::NpcAiComponent>(e);
        reg.emplace<zone::ActorComponent>(e);
        reg.emplace<zone::SpatialComponent>(e, rooms[r].cx(), rooms[r].cy());
        reg.emplace<zone::HealthComponent>(e, hp, hp);
        reg.emplace<zone::CombatStatsComponent>(e, zone::CombatStatsComponent{atk, 50});
    }

    // 物品
    std::uniform_int_distribution<int> pct(0, 99);
    for (int r = 1; r < (int)rooms.size() - 1; ++r) {
        if (pct(rng) >= ITEM_PCT) continue;
        int val = 5 + (current_floor_ - 1) * 2;
        auto e = em_.create();
        reg.emplace<zone::ItemComponent>(e, zone::ItemComponent{zone::ItemType::health_potion, val});
        reg.emplace<zone::SpatialComponent>(e, rooms[r].x + 1, rooms[r].y + 1);
    }
}
```

- [ ] **Step 3: next_floor / restart / recompute_fov**

```cpp
void zone_gd::ZoneWorld::next_floor() {
    ++current_floor_;
    setup_map();
    recompute_fov();
    emit_signal("floor_changed", current_floor_);
    emit_signal("world_changed");
}

void zone_gd::ZoneWorld::restart() {
    if (hero_entity_ != entt::null) {
        em_.registry().destroy(hero_entity_);
        hero_entity_ = entt::null;
    }
    game_over_ = false; turn_count_ = 0; current_floor_ = 1;
    setup_map();
    recompute_fov();
    emit_signal("world_changed");
}

void zone_gd::ZoneWorld::recompute_fov() {
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return;
    const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_);
    if (!sp) return;
    auto& map = em_.get<zone::MapData>(map_entity_);
    zone::compute_fov(map, sp->x, sp->y, FOV_RADIUS);
}
```

- [ ] **Step 4: advance_turn（actor poll entry point）**

```cpp
void zone_gd::ZoneWorld::advance_turn() {
    auto& reg = em_.registry();
    // Actor poll: 輪詢所有 ActorComponent 實體，對 NPC 執行 AI 系統。
    // 英雄的行動由前端（玩家輸入）在呼叫 advance_turn() 之前完成，此處跳過。
    zone::npc_ai_system(reg, ctx_);
    recompute_fov();
    ++turn_count_;
    if (map_entity_ != entt::null)
        reg.get<zone::WorldStateComponent>(map_entity_).turn_count = turn_count_;
    emit_signal("world_changed");
}
```

- [ ] **Step 5: move() / wait_turn()（移除 MetaData、Locale 依賴）**

```cpp
bool zone_gd::ZoneWorld::move(int dx, int dy) {
    if (game_over_) return false;
    if (hero_entity_ == entt::null || map_entity_ == entt::null) return false;
    auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_);
    if (!sp) return false;

    int nx = sp->x + dx, ny = sp->y + dy;
    const auto& map = em_.get<zone::MapData>(map_entity_);

    if (!map.in_bounds(nx, ny) || !map.at(nx, ny).is_walkable()) {
        emit_signal("hero_bumped_wall");
        return false;
    }

    auto& reg = em_.registry();

    // NPC 碰撞
    for (auto e : reg.view<zone::NpcAiComponent, zone::SpatialComponent>()) {
        const auto& nsp = reg.get<zone::SpatialComponent>(e);
        if (nsp.x == nx && nsp.y == ny) {
            if (auto* hp = reg.try_get<zone::HealthComponent>(e)) {
                hp->hp -= 3;
                if (hp->hp <= 0) { reg.destroy(e); emit_signal("npc_died", String("npc")); }
                else             { emit_signal("hero_bumped_npc", String("npc")); }
            }
            advance_turn();
            return true;
        }
    }

    sp->x = nx; sp->y = ny;

    // 物品拾取
    for (auto e : reg.view<zone::ItemComponent, zone::SpatialComponent>()) {
        const auto& isp = reg.get<zone::SpatialComponent>(e);
        if (isp.x == sp->x && isp.y == sp->y) {
            const auto& item = reg.get<zone::ItemComponent>(e);
            int heal_done = 0;
            if (item.type == zone::ItemType::health_potion) {
                if (auto* hp = reg.try_get<zone::HealthComponent>(hero_entity_)) {
                    int healed = std::min(item.value, hp->max_hp - hp->hp);
                    hp->hp += healed;
                    heal_done = healed;
                }
            }
            reg.destroy(e);
            emit_signal("item_picked_up", String("health_potion"), heal_done);
            break;
        }
    }

    // 樓梯
    if (map.at(nx, ny).is_stair_down()) { next_floor(); return true; }

    // 英雄死亡
    if (const auto* hp = reg.try_get<zone::HealthComponent>(hero_entity_)) {
        if (hp->hp <= 0) { game_over_ = true; emit_signal("game_over"); }
    }

    advance_turn();
    return true;
}

void zone_gd::ZoneWorld::wait_turn() {
    if (!game_over_) advance_turn();
}
```

- [ ] **Step 6: 狀態查詢與 generate_map_image（移除 NpcVariant 著色分支）**

```cpp
int zone_gd::ZoneWorld::get_map_width()  const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<zone::MapData>(map_entity_).width;
}
int zone_gd::ZoneWorld::get_map_height() const {
    if (map_entity_ == entt::null) return 0;
    return em_.get<zone::MapData>(map_entity_).height;
}
bool zone_gd::ZoneWorld::is_walkable(int x, int y) const {
    if (map_entity_ == entt::null) return false;
    const auto& map = em_.get<zone::MapData>(map_entity_);
    return map.in_bounds(x, y) && map.at(x, y).is_walkable();
}
int zone_gd::ZoneWorld::get_hero_x() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_)) return sp->x;
    return 0;
}
int zone_gd::ZoneWorld::get_hero_y() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* sp = em_.registry().try_get<zone::SpatialComponent>(hero_entity_)) return sp->y;
    return 0;
}
int zone_gd::ZoneWorld::get_turn_count()  const { return turn_count_; }
int zone_gd::ZoneWorld::get_hero_hp()     const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* hp = em_.registry().try_get<zone::HealthComponent>(hero_entity_)) return hp->hp;
    return 0;
}
int zone_gd::ZoneWorld::get_hero_max_hp() const {
    if (!em_.registry().valid(hero_entity_)) return 0;
    if (const auto* hp = em_.registry().try_get<zone::HealthComponent>(hero_entity_)) return hp->max_hp;
    return 0;
}
int zone_gd::ZoneWorld::get_npc_count() const {
    return (int)em_.registry().view<zone::NpcAiComponent>().size_hint();
}
int zone_gd::ZoneWorld::get_current_floor() const { return current_floor_; }

godot::Ref<godot::Image> zone_gd::ZoneWorld::generate_map_image(int cell_px) const {
    if (map_entity_ == entt::null) return {};
    const auto& map = em_.get<zone::MapData>(map_entity_);
    auto& reg = em_.registry();
    Ref<Image> img = Image::create(map.width * cell_px, map.height * cell_px, false, Image::FORMAT_RGB8);

    const Color floor_c(0.40f, 0.35f, 0.25f), wall_c(0.12f, 0.10f, 0.08f);
    const Color hero_c(1.00f, 0.90f, 0.20f),  npc_c(0.90f, 0.20f, 0.20f);
    const Color item_c(0.20f, 0.85f, 0.40f),  black(0.00f, 0.00f, 0.00f);

    for (int x = 0; x < map.width; ++x)
        for (int y = 0; y < map.height; ++y) {
            Color c;
            if (map.is_visible(x, y))
                c = map.at(x, y).is_stair_down() ? Color(0.80f,0.65f,0.10f)
                  : (map.at(x, y).is_walkable() ? floor_c : wall_c);
            else if (map.is_explored(x, y)) {
                Color b = map.at(x, y).is_walkable() ? floor_c : wall_c;
                c = Color(b.r*0.4f, b.g*0.4f, b.b*0.4f);
            } else c = black;
            img->fill_rect(Rect2i(x*cell_px, y*cell_px, cell_px, cell_px), c);
        }

    for (auto e : reg.view<zone::ItemComponent, zone::SpatialComponent>()) {
        const auto& sp = reg.get<zone::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), item_c);
    }
    for (auto e : reg.view<zone::NpcAiComponent, zone::SpatialComponent>()) {
        const auto& sp = reg.get<zone::SpatialComponent>(e);
        if (map.is_visible(sp.x, sp.y))
            img->fill_rect(Rect2i(sp.x*cell_px, sp.y*cell_px, cell_px, cell_px), npc_c);
    }
    if (reg.valid(hero_entity_)) {
        if (const auto* sp = reg.try_get<zone::SpatialComponent>(hero_entity_))
            if (map.in_bounds(sp->x, sp->y))
                img->fill_rect(Rect2i(sp->x*cell_px, sp->y*cell_px, cell_px, cell_px), hero_c);
    }
    return img;
}
```

- [ ] **Step 7: save_game / load_game / has_save_game（與原版相同邏輯，只改 namespace）**

```cpp
bool zone_gd::ZoneWorld::save_game(const godot::String& path) {
    try {
        std::string p = path.utf8().get_data();
        zone::serialize::FolderSaveStore store(p);
        zone::serialize::save(em_.registry(), store);
        return true;
    } catch (...) { return false; }
}
bool zone_gd::ZoneWorld::load_game(const godot::String& path) {
    try {
        std::string p = path.utf8().get_data();
        zone::serialize::FolderSaveStore store(p);
        zone::serialize::load(em_.registry(), store);
        // 重建 C++ 指標
        for (auto e : em_.registry().view<zone::HeroComponent>())
            { hero_entity_ = e; break; }
        for (auto e : em_.registry().view<zone::MapData>())
            { map_entity_ = e; break; }
        if (map_entity_ != entt::null) {
            const auto& ws = em_.registry().get<zone::WorldStateComponent>(map_entity_);
            turn_count_    = ws.turn_count;
            current_floor_ = ws.current_floor;
        }
        recompute_fov();
        return true;
    } catch (...) { return false; }
}
bool zone_gd::ZoneWorld::has_save_game(const godot::String& path) const {
    return std::filesystem::exists(path.utf8().get_data());
}
```

---

## Task 10: 更新 register_types.cpp

**Files:**
- Modify: `src/gbind/register_types.cpp`, `src/gbind/register_types.h`

- [ ] **Step 1: 確認 register_types.cpp 已正確引用 ZoneCore / ZoneWorld**

讀取現有 register_types.cpp（經 Task 3 rename 後），確認包含：
```cpp
#include "zone_core_gd.h"
#include "zone_world_gd.h"
// ...
GDREGISTER_CLASS(zone_gd::ZoneCore);
GDREGISTER_CLASS(zone_gd::ZoneWorld);
```
若有遺漏，用 Edit 補齊。

---

## Task 11: 修正測試（移除 EventBus / MetaData 依賴）

**Files:**
- Modify: `tests/src/test_ecs.cpp`
- Modify: `tests/src/test_npc_combat.cpp`
- Modify: `tests/src/test_phase4.cpp`
- Modify: `tests/src/test_serialize.cpp`

- [ ] **Step 1: 更新 test_ecs.cpp（移除 EventBus 與 MetaDataComponent）**

`test_ecs.cpp` 中：
1. 刪除 `#include <core/ecs/event_bus.h>` 和 `#include <core/components/meta_data_component.h>`
2. 刪除所有含 `EventBus`、`DamageEvent`、`BroadcastSpawnEvent` 的 TEST_CASE
3. 刪除所有含 `MetaDataComponent` 的 TEST_CASE
4. 確保 `ActorComponent` 測試（Task 5 Step 2 加入的）可正常編譯

- [ ] **Step 2: 更新 test_npc_combat.cpp（加 ActorComponent）**

搜尋所有建立英雄或 NPC 的地方，加上 `ActorComponent`：
- 建英雄：加 `reg.emplace<zone::ActorComponent>(hero);`
- 建 NPC：加 `reg.emplace<zone::ActorComponent>(npc);`
- 移除 `MetaDataComponent` 使用（如有）

- [ ] **Step 3: 更新 test_phase4.cpp 與 test_serialize.cpp**

- 移除 `#include <core/ecs/event_bus.h>` 等已刪除標頭
- 移除 `MetaDataComponent` 的使用（改用直接 component 賦值取代原型相關呼叫）
- `test_serialize.cpp` 確認 `AllComponents` 不再含 `MetaDataComponent`

- [ ] **Step 4: 嘗試 build + 看錯誤**

```bash
cd /home/lorkhan/repo/pas/derived/gamecore-zone
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug 2>&1 | tail -5
cmake --build build -j$(nproc) 2>&1 | grep -E 'error:|warning:' | head -30
```

- [ ] **Step 5: 逐一修正編譯錯誤，直到 build 成功**

---

## Task 12: 跑 ctest — 確認全綠

**Files:** 無（只跑測試）

- [ ] **Step 1: 執行所有測試**

```bash
cd /home/lorkhan/repo/pas/derived/gamecore-zone/build && ctest --output-on-failure
```
Expected: 全部 PASSED（原 40 cases 扣掉刪除的 proto/locale/cvar 測試後，約 20–25 cases）

- [ ] **Step 2: 若有 FAIL，閱讀輸出並修正，重複直到全綠**

- [ ] **Step 3: Commit**

```bash
cd /home/lorkhan/repo/pas
git add derived/gamecore-zone/
git commit -m "feat(gamecore-zone): hard fork from opennefia-cpp — zone core 重構完成

刪除原型/locale/cvar/EventBus；新增 ActorComponent actor poll；
zone_core 測試全綠；命名改 zone_* 前綴。"
```

---

## Task 13: GDExtension 建置 + Godot 驗證

**Files:**
- Modify: `godot_zone/zone.gdextension`
- Modify: `godot_zone/verify.gd`（namespace 改名）

- [ ] **Step 1: 確認 zone.gdextension 路徑正確**

`godot_zone/zone.gdextension` 應包含：
```ini
[configuration]
entry_symbol = "zone_library_init"
compatibility_minimum = "4.1"

[libraries]
linux.debug.x86_64 = "res://bin/libzone_gd.so"
```
若 entry_symbol 或路徑不符，用 Edit 修正。

- [ ] **Step 2: 建置 GDExtension**

```bash
cd /home/lorkhan/repo/pas/derived/gamecore-zone
cmake -S . -B build -DZONE_BUILD_GDEXTENSION=ON \
      -DGODOT_CPP_DIR="$(pwd)/../../projects/godot-cpp"
cmake --build build --target zone_gd -j$(nproc)
cp build/bin/libzone_gd.so godot_zone/bin/
```
Expected: `libzone_gd.so` 出現在 `godot_zone/bin/`

- [ ] **Step 3: 更新 verify.gd（改用 ZoneWorld）**

確認 `godot_zone/verify.gd` 中所有 `OpenNefiaWorld` 已改為 `ZoneWorld`（Task 3 的 sed 應已處理；若未處理則手動 Edit）。

- [ ] **Step 4: 首次 import（建 .godot/extension_list.cfg）**

```bash
cd godot_zone && godot-mono --headless --path . --import 2>&1 | tail -5
```

- [ ] **Step 5: 跑 headless verify**

```bash
godot-mono --headless --path . -s res://verify.gd 2>&1 | tail -20
```
Expected: `VERIFY PASSED`

- [ ] **Step 6: Commit**

```bash
cd /home/lorkhan/repo/pas
git add derived/gamecore-zone/
git commit -m "feat(gamecore-zone): GDExtension zone_gd 建置通過，headless VERIFY PASSED"
```
