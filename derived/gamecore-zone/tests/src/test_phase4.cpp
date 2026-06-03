#include <doctest/doctest.h>
#include <string>
#include <filesystem>
#include <core/ecs/entity_manager.h>
#include <core/ecs/system_ctx.h>
#include <core/components/actor_component.h>
#include <core/components/spatial_component.h>
#include <core/components/world_state_component.h>
#include <core/maps/tile.h>
#include <core/maps/map_data.h>
#include <core/serialize/save_load.h>
#include <core/serialize/save_store.h>

namespace fs  = std::filesystem;
namespace ser = zone::serialize;

// ==============================================================
// MapData 基本操作
// ==============================================================
TEST_CASE("MapData — resize / in_bounds / at") {
    zone::MapData map{10, 8};
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
    zone::MapData map{5, 5};
    map.at(2, 3).flags = zone::TILE_WALKABLE;
    CHECK(map.at(2, 3).is_walkable());
    CHECK_FALSE(map.at(2, 3).blocks_sight());

    map.at(1, 1).flags = zone::TILE_BLOCKS_SIGHT;
    CHECK_FALSE(map.at(1, 1).is_walkable());
    CHECK(map.at(1, 1).blocks_sight());
}

TEST_CASE("MapData — get() 越界安全") {
    zone::MapData map{3, 3};
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
    auto& map = reg.emplace<zone::MapData>(map_e, 6, 4);
    // 設定一列可走 tile
    for (int x = 0; x < 6; ++x) {
        map.at(x, 2).flags = zone::TILE_WALKABLE;
        map.at(x, 2).terrain = 1;
    }
    map.at(1, 1).flags = zone::TILE_BLOCKS_SIGHT;

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    // 找回地圖實體（只有 MapData 的實體）
    bool found = false;
    reg.view<zone::MapData>().each(
        [&](entt::entity, const zone::MapData& mp) {
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
// WorldStateComponent round-trip
// ==============================================================
TEST_CASE("WorldStateComponent — 序列化 round-trip") {
    entt::registry reg;
    auto e = reg.create();
    reg.emplace<zone::WorldStateComponent>(e, zone::WorldStateComponent{42, 3});

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    bool found = false;
    reg.view<zone::WorldStateComponent>().each(
        [&](entt::entity, const zone::WorldStateComponent& ws) {
            found = true;
            CHECK(ws.turn_count    == 42);
            CHECK(ws.current_floor == 3);
        }
    );
    CHECK(found);
}

// ==============================================================
// 移動系統 — 牆阻擋：英雄無法走入不可走格
// ==============================================================
TEST_CASE("移動系統 — 牆阻擋：碰牆停止前進") {
    zone::EntityManager em;
    zone::SystemCtx ctx;

    // 建 3x1 地圖：只有 x=0,y=0 可走；x=1,y=0 是牆
    auto map_e = em.create();
    auto& wmap = em.emplace<zone::MapData>(map_e, 3, 1);
    wmap.at(0, 0).flags = zone::TILE_WALKABLE;
    // at(1,0) = 無旗標（牆）
    wmap.at(2, 0).flags = zone::TILE_WALKABLE;

    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero,
        zone::SpatialComponent{0, 0, entt::null});

    em.add_system([map_e](entt::registry& reg, zone::SystemCtx&) {
        auto* mp = reg.try_get<zone::MapData>(map_e);
        if (!mp) return;
        for (auto e : reg.view<zone::SpatialComponent, zone::ActorComponent>()) {
            auto& sp = reg.get<zone::SpatialComponent>(e);
            if (e == map_e) continue;
            int nx = sp.x + 1;
            int ny = sp.y;
            if (mp->in_bounds(nx, ny) && mp->at(nx, ny).is_walkable())
                sp.x = nx;
        }
    });

    // Tick 1：嘗試 x=0→1，但 at(1,0) 不可走 → 不動
    em.tick(ctx);
    CHECK(em.get<zone::SpatialComponent>(hero).x == 0);

    // Tick 2：仍不動
    em.tick(ctx);
    CHECK(em.get<zone::SpatialComponent>(hero).x == 0);
}

// ==============================================================
// 多實體並存：地圖 + 英雄 + NPC，各自 tick 移動，序列化 round-trip
// ==============================================================
TEST_CASE("多實體 — 地圖 + 英雄 + NPC 同時存在並序列化") {
    zone::EntityManager em;
    zone::SystemCtx ctx;

    auto map_e = em.create();
    auto& mmap = em.emplace<zone::MapData>(map_e, 10, 1);
    for (int x = 0; x < 10; ++x) mmap.at(x, 0).flags = zone::TILE_WALKABLE;

    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero,
        zone::SpatialComponent{0, 0, entt::null});

    auto npc = em.create();
    em.emplace<zone::ActorComponent>(npc);
    em.emplace<zone::SpatialComponent>(npc,
        zone::SpatialComponent{5, 0, entt::null});

    em.add_system([map_e](entt::registry& reg, zone::SystemCtx&) {
        auto* mp = reg.try_get<zone::MapData>(map_e);
        if (!mp) return;
        for (auto e : reg.view<zone::SpatialComponent, zone::ActorComponent>()) {
            auto& sp = reg.get<zone::SpatialComponent>(e);
            if (e == map_e) continue;
            int nx = sp.x + 1;
            if (mp->in_bounds(nx, 0) && mp->at(nx, 0).is_walkable())
                sp.x = nx;
        }
    });

    em.tick(ctx);
    em.tick(ctx);

    CHECK(em.get<zone::SpatialComponent>(hero).x == 2);
    CHECK(em.get<zone::SpatialComponent>(npc).x  == 7);

    // Round-trip（用 entity 本身在 registry 中唯一的位置來驗）
    int hero_x_before = em.get<zone::SpatialComponent>(hero).x;
    int npc_x_before  = em.get<zone::SpatialComponent>(npc).x;

    std::ostringstream oss;
    ser::save(em.registry(), oss);
    em = zone::EntityManager{};
    std::istringstream iss{oss.str()};
    ser::load(em.registry(), iss);

    // 還原後應有 2 個 ActorComponent 實體，各自座標正確
    int xs[2] = {-1, -1};
    int idx = 0;
    for (auto e : em.registry().view<zone::ActorComponent, zone::SpatialComponent>()) {
        const auto& s = em.registry().get<zone::SpatialComponent>(e);
        if (idx < 2) xs[idx++] = s.x;
    }
    CHECK(idx == 2);
    // 兩個 actor 的 x 應包含 hero_x_before 和 npc_x_before
    bool found_hero = (xs[0] == hero_x_before || xs[1] == hero_x_before);
    bool found_npc  = (xs[0] == npc_x_before  || xs[1] == npc_x_before);
    CHECK(found_hero);
    CHECK(found_npc);
}
