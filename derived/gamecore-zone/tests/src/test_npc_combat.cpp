#include <doctest/doctest.h>
#include <core/ecs/entity_manager.h>
#include <core/ecs/system_ctx.h>
#include <core/components/actor_component.h>
#include <core/components/spatial_component.h>
#include <core/components/health_component.h>
#include <core/components/npc_ai_component.h>
#include <core/components/combat_stats_component.h>
#include <core/components/item_component.h>
#include <core/components/hero_component.h>
#include <core/maps/map_data.h>
#include <core/maps/tile.h>
#include <core/systems/npc_ai_system.h>
#include <core/serialize/save_load.h>
#include <sstream>

// ==============================================================
// NPC AI 戰鬥：警覺且鄰接的 NPC 應對英雄造成傷害
// （對應前端回報：撞 NPC 能傷敵，但英雄不會被反擊扣血）
// ==============================================================

// 建一張全可走的小地圖實體
static entt::entity make_open_map(zone::EntityManager& em, int w, int h) {
    auto map_e = em.create();
    auto& map = em.emplace<zone::MapData>(map_e, w, h);
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
            map.at(x, y).flags = zone::TILE_WALKABLE;
    return map_e;
}

TEST_CASE("NPC AI — 警覺且鄰接時攻擊英雄（核心戰鬥邏輯）") {
    zone::SystemCtx ctx;
    zone::EntityManager em;
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    // 英雄：ActorComponent + Spatial + Health，無 NpcAi、無 Item
    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero, zone::SpatialComponent{2, 2, entt::null});
    em.emplace<zone::HealthComponent>(hero, 20, 20);
    em.emplace<zone::HeroComponent>(hero);  // 正向辨識標記

    // NPC：鄰接 (2,3)，已警覺，move_chance=100（確定行動），attack=5
    auto npc = em.create();
    em.emplace<zone::ActorComponent>(npc);
    em.emplace<zone::SpatialComponent>(npc, zone::SpatialComponent{2, 3, entt::null});
    em.emplace<zone::NpcAiComponent>(npc, zone::NpcAiComponent{true, 6});
    em.emplace<zone::HealthComponent>(npc, 10, 10);
    em.emplace<zone::CombatStatsComponent>(npc,
        zone::CombatStatsComponent{5, 100});

    em.add_system(zone::npc_ai_system);
    em.tick(ctx);

    CHECK(reg.get<zone::HealthComponent>(hero).hp == 15);  // 20 - 5
}

// 真機回歸：物品實體建立在「英雄之後」（與 setup_test_world 的順序一致）。
// 舊版 hero 辨識 `view<Spatial>(exclude<NpcAi>)` 由 storage 尾端往前掃，
// 會先碰到較晚建立的物品 → hero_ent 誤指向無 Health 的物品 → 攻擊打空、英雄不掉血。
// 此案例必須讓物品在英雄之後生成，才能重現該 bug（物品在前反而矇混過關）。
TEST_CASE("NPC AI — 物品建立於英雄之後時仍應正確攻擊英雄（真機順序回歸）") {
    zone::SystemCtx ctx;
    zone::EntityManager em;
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    // 1) 英雄（先建立，如同 setup_test_world）
    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero, zone::SpatialComponent{2, 2, entt::null});
    em.emplace<zone::HealthComponent>(hero, 20, 20);
    em.emplace<zone::HeroComponent>(hero);  // 正向辨識標記

    // 2) 鄰接、警覺的 NPC
    auto npc = em.create();
    em.emplace<zone::ActorComponent>(npc);
    em.emplace<zone::SpatialComponent>(npc, zone::SpatialComponent{2, 3, entt::null});
    em.emplace<zone::NpcAiComponent>(npc, zone::NpcAiComponent{true, 6});
    em.emplace<zone::HealthComponent>(npc, 10, 10);
    em.emplace<zone::CombatStatsComponent>(npc,
        zone::CombatStatsComponent{5, 100});

    // 3) 物品「最後」建立（pool 尾端）——舊版反向掃描會誤選它當英雄
    auto item = em.create();
    em.emplace<zone::SpatialComponent>(item, zone::SpatialComponent{0, 0, entt::null});
    em.emplace<zone::ItemComponent>(item);

    em.add_system(zone::npc_ai_system);
    em.tick(ctx);

    // 英雄應受傷；若 hero 辨識被物品搶走，傷害會打在無 Health 的物品上，hp 維持 20
    CHECK(reg.get<zone::HealthComponent>(hero).hp == 15);
}

// 回歸測試：重現前端「撞 NPC 能傷敵但自己不掉血」的根因。
// move_chance=0 的 NPC（從不移動）若已警覺且貼身，仍必須攻擊英雄——
// 攻擊不該被行動機率閘門吃掉。修正前此案例會失敗（hp 維持 20）。
TEST_CASE("NPC AI — move_chance=0 的鄰接警覺 NPC 仍必定攻擊") {
    zone::SystemCtx ctx;
    zone::EntityManager em;
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero, zone::SpatialComponent{2, 2, entt::null});
    em.emplace<zone::HealthComponent>(hero, 20, 20);
    em.emplace<zone::HeroComponent>(hero);  // 正向辨識標記

    auto npc = em.create();
    em.emplace<zone::ActorComponent>(npc);
    em.emplace<zone::SpatialComponent>(npc, zone::SpatialComponent{2, 3, entt::null});
    em.emplace<zone::NpcAiComponent>(npc, zone::NpcAiComponent{true, 6});
    em.emplace<zone::HealthComponent>(npc, 10, 10);
    em.emplace<zone::CombatStatsComponent>(npc,
        zone::CombatStatsComponent{3, 0});  // move_chance=0

    em.add_system(zone::npc_ai_system);
    em.tick(ctx);
    em.tick(ctx);
    em.tick(ctx);

    CHECK(reg.get<zone::HealthComponent>(hero).hp == 11);  // 20 - 3*3
}

// HeroComponent 是空 tag：驗證它能通過 cereal/EnTT snapshot round-trip，
// 讀檔後 view<HeroComponent> 仍唯一指回英雄（gbind 載入路徑依賴此）。
TEST_CASE("HeroComponent — 空 tag 序列化 round-trip 後仍可辨識英雄") {
    zone::EntityManager em;

    auto hero = em.create();
    em.emplace<zone::ActorComponent>(hero);
    em.emplace<zone::SpatialComponent>(hero, zone::SpatialComponent{4, 7, entt::null});
    em.emplace<zone::HealthComponent>(hero, 20, 20);
    em.emplace<zone::HeroComponent>(hero);

    // 另建一個非英雄實體，確保不是「碰巧只有一個」
    auto npc = em.create();
    em.emplace<zone::ActorComponent>(npc);
    em.emplace<zone::SpatialComponent>(npc, zone::SpatialComponent{1, 1, entt::null});
    em.emplace<zone::NpcAiComponent>(npc, zone::NpcAiComponent{});

    std::ostringstream oss;
    zone::serialize::save(em.registry(), oss);
    em = zone::EntityManager{};
    std::istringstream iss{oss.str()};
    zone::serialize::load(em.registry(), iss);

    auto& reg = em.registry();
    int hero_count = 0;
    entt::entity found = entt::null;
    for (auto e : reg.view<zone::HeroComponent>()) { ++hero_count; found = e; }
    bool found_valid = (found != entt::null);  // 先求值，避免 doctest 分解 operator!= 歧義
    CHECK(hero_count == 1);
    CHECK(found_valid);
    CHECK(reg.get<zone::SpatialComponent>(found).x == 4);
    CHECK(reg.get<zone::SpatialComponent>(found).y == 7);
}
