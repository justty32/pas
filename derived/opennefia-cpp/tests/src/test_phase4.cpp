#include <doctest/doctest.h>
#include <string>
#include <filesystem>
#include <core/ecs/entity_manager.h>
#include <core/ecs/event_bus.h>
#include <core/ecs/system_ctx.h>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>
#include <core/maps/tile.h>
#include <core/maps/map_data.h>
#include <core/prototypes/prototype_manager.h>
#include <core/serialize/save_load.h>
#include <core/serialize/save_store.h>

namespace fs  = std::filesystem;
namespace ser = opennefia::serialize;

// ==============================================================
// 工具：建立最小可用 PrototypeManager（只登錄 Spatial + MetaData）
// CharaStats 未登錄 → apply_to 時靜默略過（前向相容驗證）
// ==============================================================
static opennefia::PrototypeManager make_minimal_pm() {
    opennefia::PrototypeManager pm;

    pm.register_loader("Spatial",
        [](entt::registry& reg, entt::entity e, const YAML::Node& n) {
            opennefia::SpatialComponent s;
            if (n["x"]) s.x = n["x"].as<int>();
            if (n["y"]) s.y = n["y"].as<int>();
            reg.emplace_or_replace<opennefia::SpatialComponent>(e, s);
        }
    );
    pm.register_loader("MetaData",
        [](entt::registry& reg, entt::entity e, const YAML::Node& n) {
            opennefia::MetaDataComponent m;
            if (n["name"]) m.proto_id = n["name"].as<std::string>();
            reg.emplace_or_replace<opennefia::MetaDataComponent>(e, m);
        }
    );

    pm.load_file(std::string(OPENNEFIA_TEST_DATA_DIR) + "/test_prototypes.yaml");
    pm.resolve_inheritance();
    return pm;
}

// ==============================================================
// MapData 基本操作
// ==============================================================
TEST_CASE("MapData — resize / in_bounds / at") {
    opennefia::MapData map{10, 8};
    CHECK(map.width  == 10);
    CHECK(map.height == 8);
    CHECK_FALSE(map.empty());
    CHECK(map.in_bounds(0, 0));
    CHECK(map.in_bounds(9, 7));
    CHECK_FALSE(map.in_bounds(-1, 0));
    CHECK_FALSE(map.in_bounds(10, 0));
    CHECK_FALSE(map.in_bounds(0, 8));
}

TEST_CASE("MapData — tile 旗標讀寫") {
    opennefia::MapData map{5, 5};
    map.at(2, 3).flags = opennefia::TILE_WALKABLE;
    CHECK(map.at(2, 3).is_walkable());
    CHECK_FALSE(map.at(2, 3).blocks_sight());

    map.at(1, 1).flags = opennefia::TILE_BLOCKS_SIGHT;
    CHECK_FALSE(map.at(1, 1).is_walkable());
    CHECK(map.at(1, 1).blocks_sight());
}

TEST_CASE("MapData — get() 越界安全") {
    opennefia::MapData map{3, 3};
    CHECK(map.get(1, 1) != nullptr);
    CHECK(map.get(-1, 0) == nullptr);
    CHECK(map.get(3, 0)  == nullptr);
}

// ==============================================================
// MapData 序列化 round-trip
// ==============================================================
TEST_CASE("MapData — 序列化 round-trip（tile 旗標保存）") {
    entt::registry reg;

    // 地圖實體
    auto map_e = reg.create();
    reg.emplace<opennefia::MetaDataComponent>(map_e,
        opennefia::MetaDataComponent{"world_map", true});
    auto& map = reg.emplace<opennefia::MapData>(map_e, 6, 4);
    // 設定一列可走 tile
    for (int x = 0; x < 6; ++x) {
        map.at(x, 2).flags = opennefia::TILE_WALKABLE;
        map.at(x, 2).terrain = 1;
    }
    map.at(1, 1).flags = opennefia::TILE_BLOCKS_SIGHT;

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    // 找回地圖實體
    bool found = false;
    reg.view<opennefia::MetaDataComponent, opennefia::MapData>().each(
        [&](entt::entity, const opennefia::MetaDataComponent& m,
                          const opennefia::MapData& mp) {
            if (m.proto_id != "world_map") return;
            found = true;
            CHECK(mp.width  == 6);
            CHECK(mp.height == 4);
            CHECK(mp.at(0, 2).is_walkable());
            CHECK(mp.at(5, 2).is_walkable());
            CHECK(mp.at(0, 2).terrain == 1);
            CHECK_FALSE(mp.at(0, 0).is_walkable());
            CHECK(mp.at(1, 1).blocks_sight());
        }
    );
    CHECK(found);
}

// ==============================================================
// Phase 4 整合測試：原型生成 → 地圖可走性系統 → tick N → 存檔 → 還原
// ==============================================================
TEST_CASE("Phase 4 整合測試 — 完整流程（PROJECT.md §5 完成定義）") {
    auto tmp_dir = fs::temp_directory_path() / "opennefia_phase4_test";
    fs::create_directories(tmp_dir);

    // ---- 1. 初始化 ----------------------------------------------------------
    auto pm = make_minimal_pm();
    opennefia::EventBus    bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx   ctx{bus};

    // ---- 2. 建地圖實體（帶 MapData + MetaData，無 SpatialComponent）----------
    auto map_e = em.create();
    em.emplace<opennefia::MetaDataComponent>(map_e,
        opennefia::MetaDataComponent{"world_map", true});
    auto& world_map = em.emplace<opennefia::MapData>(map_e, 20, 20);

    // 設定 y=5 整行為可走地板
    for (int x = 0; x < 20; ++x) {
        world_map.at(x, 5).flags = opennefia::TILE_WALKABLE;
    }
    // x=10 是牆（不可走）
    world_map.at(10, 5).flags = 0;

    // ---- 3. 從原型生成角色 --------------------------------------------------
    // Putit 原型（test_prototypes.yaml）：繼承 BaseEntity 的 Spatial(0,0)；
    // spawn 後手動設定到可走位置。
    auto hero = pm.spawn(em, "Putit");
    em.get<opennefia::SpatialComponent>(hero).x = 3;
    em.get<opennefia::SpatialComponent>(hero).y = 5;  // 在可走行上

    // 驗證初始狀態
    CHECK(em.get<opennefia::MetaDataComponent>(hero).proto_id == "Putit");
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 3);

    // ---- 4. 登錄移動系統：嘗試向右走一格，碰牆停下 --------------------------
    // map_e capture by value（entity ID 在 registry 中是穩定的整數）
    em.add_system([map_e](entt::registry& reg, opennefia::SystemCtx&) {
        auto* mp = reg.try_get<opennefia::MapData>(map_e);
        if (!mp) return;

        reg.view<opennefia::SpatialComponent,
                 opennefia::MetaDataComponent>()
            .each([&](entt::entity e,
                      opennefia::SpatialComponent& sp,
                      const opennefia::MetaDataComponent&) {
                if (e == map_e) return;      // 地圖實體不移動
                int nx = sp.x + 1;
                int ny = sp.y;
                if (mp->in_bounds(nx, ny) && mp->at(nx, ny).is_walkable()) {
                    sp.x = nx;
                }
            });
    });

    // ---- 5. Tick 3 回合（3→4→5→6，到 x=6 還是可走；牆在 x=10）--------------
    em.tick(ctx);
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 4);
    em.tick(ctx);
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 5);
    em.tick(ctx);
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 6);

    // ---- 6. 存檔 -------------------------------------------------------------
    ser::FolderSaveStore store{tmp_dir};
    ser::save(em.registry(), store, "world");
    CHECK(store.has("world"));

    // ---- 7. 清空 registry（和系統）→ 還原 -----------------------------------
    em = opennefia::EntityManager{};    // 清空所有 entity + 系統
    ser::load(em.registry(), store, "world");

    // ---- 8. 驗證還原後的狀態 ------------------------------------------------
    // 8a. 英雄存在，座標正確
    bool hero_ok = false;
    em.registry().view<opennefia::MetaDataComponent,
                       opennefia::SpatialComponent>()
        .each([&](entt::entity,
                  const opennefia::MetaDataComponent& m,
                  const opennefia::SpatialComponent& sp) {
            if (m.proto_id == "Putit") {
                hero_ok = true;
                CHECK(sp.x == 6);
                CHECK(sp.y == 5);
                bool parent_null = (sp.parent == entt::null);
                CHECK(parent_null);
            }
        });
    CHECK(hero_ok);

    // 8b. 地圖實體存在，tile 旗標正確
    bool map_ok = false;
    em.registry().view<opennefia::MetaDataComponent,
                       opennefia::MapData>()
        .each([&](entt::entity,
                  const opennefia::MetaDataComponent& m,
                  const opennefia::MapData& mp) {
            if (m.proto_id != "world_map") return;
            map_ok = true;
            CHECK(mp.width  == 20);
            CHECK(mp.height == 20);
            // 可走行在 y=5，牆在 x=10,y=5
            CHECK(mp.at(3, 5).is_walkable());
            CHECK_FALSE(mp.at(10, 5).is_walkable());
        });
    CHECK(map_ok);

    // ---- 清理 ---------------------------------------------------------------
    fs::remove_all(tmp_dir);
}

// ==============================================================
// 牆阻擋：英雄無法走入不可走格
// ==============================================================
TEST_CASE("移動系統 — 牆阻擋：碰牆停止前進") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx ctx{bus};

    // 建 3x1 地圖：只有 x=0,y=0 可走；x=1,y=0 是牆
    auto map_e = em.create();
    em.emplace<opennefia::MetaDataComponent>(map_e,
        opennefia::MetaDataComponent{"wall_test", true});
    auto& wmap = em.emplace<opennefia::MapData>(map_e, 3, 1);
    wmap.at(0, 0).flags = opennefia::TILE_WALKABLE;
    // at(1,0) = 無旗標（牆）
    wmap.at(2, 0).flags = opennefia::TILE_WALKABLE;

    auto hero = em.create();
    em.emplace<opennefia::MetaDataComponent>(hero,
        opennefia::MetaDataComponent{"hero", true});
    em.emplace<opennefia::SpatialComponent>(hero,
        opennefia::SpatialComponent{0, 0, entt::null});

    em.add_system([map_e](entt::registry& reg, opennefia::SystemCtx&) {
        auto* mp = reg.try_get<opennefia::MapData>(map_e);
        if (!mp) return;
        reg.view<opennefia::SpatialComponent, opennefia::MetaDataComponent>()
            .each([&](entt::entity e,
                      opennefia::SpatialComponent& sp,
                      const opennefia::MetaDataComponent&) {
                if (e == map_e) return;
                int nx = sp.x + 1;
                int ny = sp.y;
                if (mp->in_bounds(nx, ny) && mp->at(nx, ny).is_walkable())
                    sp.x = nx;
            });
    });

    // Tick 1：嘗試 x=0→1，但 at(1,0) 不可走 → 不動
    em.tick(ctx);
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 0);

    // Tick 2：仍不動
    em.tick(ctx);
    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 0);
}

// ==============================================================
// 多實體並存：地圖 + 英雄 + NPC，各自 tick 移動
// ==============================================================
TEST_CASE("多實體 — 地圖 + 英雄 + NPC 同時存在並序列化") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx ctx{bus};

    auto map_e = em.create();
    em.emplace<opennefia::MetaDataComponent>(map_e,
        opennefia::MetaDataComponent{"multi_map", true});
    auto& mmap = em.emplace<opennefia::MapData>(map_e, 10, 1);
    for (int x = 0; x < 10; ++x) mmap.at(x, 0).flags = opennefia::TILE_WALKABLE;

    auto hero = em.create();
    em.emplace<opennefia::MetaDataComponent>(hero,
        opennefia::MetaDataComponent{"hero", true});
    em.emplace<opennefia::SpatialComponent>(hero,
        opennefia::SpatialComponent{0, 0, entt::null});

    auto npc = em.create();
    em.emplace<opennefia::MetaDataComponent>(npc,
        opennefia::MetaDataComponent{"npc", true});
    em.emplace<opennefia::SpatialComponent>(npc,
        opennefia::SpatialComponent{5, 0, entt::null});

    em.add_system([map_e](entt::registry& reg, opennefia::SystemCtx&) {
        auto* mp = reg.try_get<opennefia::MapData>(map_e);
        if (!mp) return;
        reg.view<opennefia::SpatialComponent, opennefia::MetaDataComponent>()
            .each([&](entt::entity e, opennefia::SpatialComponent& sp,
                      const opennefia::MetaDataComponent&) {
                if (e == map_e) return;
                int nx = sp.x + 1;
                if (mp->in_bounds(nx, 0) && mp->at(nx, 0).is_walkable())
                    sp.x = nx;
            });
    });

    em.tick(ctx);
    em.tick(ctx);

    CHECK(em.get<opennefia::SpatialComponent>(hero).x == 2);
    CHECK(em.get<opennefia::SpatialComponent>(npc).x  == 7);

    // Round-trip
    std::ostringstream oss;
    ser::save(em.registry(), oss);
    em = opennefia::EntityManager{};
    std::istringstream iss{oss.str()};
    ser::load(em.registry(), iss);

    int hero_x = -1, npc_x = -1;
    em.registry().view<opennefia::MetaDataComponent,
                       opennefia::SpatialComponent>()
        .each([&](entt::entity, const opennefia::MetaDataComponent& m,
                                const opennefia::SpatialComponent& s) {
            if (m.proto_id == "hero") hero_x = s.x;
            if (m.proto_id == "npc")  npc_x  = s.x;
        });
    CHECK(hero_x == 2);
    CHECK(npc_x  == 7);
}
