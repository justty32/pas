#include <doctest/doctest.h>
#include <core/ecs/entity_manager.h>
#include <core/ecs/event_bus.h>
#include <core/ecs/system_ctx.h>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>
#include <core/components/health_component.h>
#include <core/components/npc_ai_component.h>
#include <core/components/combat_stats_component.h>
#include <core/components/item_component.h>
#include <core/maps/map_data.h>
#include <core/maps/tile.h>
#include <core/systems/npc_ai_system.h>

// ==============================================================
// NPC AI 戰鬥：警覺且鄰接的 NPC 應對英雄造成傷害
// （對應前端回報：撞 NPC 能傷敵，但英雄不會被反擊扣血）
// ==============================================================

// 建一張全可走的小地圖實體
static entt::entity make_open_map(opennefia::EntityManager& em, int w, int h) {
    auto map_e = em.create();
    auto& map = em.emplace<opennefia::MapData>(map_e, w, h);
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x)
            map.at(x, y).flags = opennefia::TILE_WALKABLE;
    return map_e;
}

TEST_CASE("NPC AI — 警覺且鄰接時攻擊英雄（核心戰鬥邏輯）") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx ctx{bus};
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    // 英雄：Spatial + Health，無 NpcAi、無 Item
    auto hero = em.create();
    em.emplace<opennefia::MetaDataComponent>(hero, opennefia::MetaDataComponent{"hero", true});
    em.emplace<opennefia::SpatialComponent>(hero, opennefia::SpatialComponent{2, 2, entt::null});
    em.emplace<opennefia::HealthComponent>(hero, 20, 20);

    // NPC：鄰接 (2,3)，已警覺，move_chance=100（確定行動），attack=5
    auto npc = em.create();
    em.emplace<opennefia::MetaDataComponent>(npc, opennefia::MetaDataComponent{"putit", true});
    em.emplace<opennefia::SpatialComponent>(npc, opennefia::SpatialComponent{2, 3, entt::null});
    em.emplace<opennefia::NpcAiComponent>(npc, opennefia::NpcAiComponent{true, 6});
    em.emplace<opennefia::HealthComponent>(npc, 10, 10);
    em.emplace<opennefia::CombatStatsComponent>(npc,
        opennefia::CombatStatsComponent{5, 100, opennefia::NpcVariant::putit});

    em.add_system(opennefia::npc_ai_system);
    em.tick(ctx);

    CHECK(reg.get<opennefia::HealthComponent>(hero).hp == 15);  // 20 - 5
}

// 真機回歸：物品實體建立在「英雄之後」（與 setup_test_world 的順序一致）。
// 舊版 hero 辨識 `view<Spatial>(exclude<NpcAi>)` 由 storage 尾端往前掃，
// 會先碰到較晚建立的物品 → hero_ent 誤指向無 Health 的物品 → 攻擊打空、英雄不掉血。
// 此案例必須讓物品在英雄之後生成，才能重現該 bug（物品在前反而矇混過關）。
TEST_CASE("NPC AI — 物品建立於英雄之後時仍應正確攻擊英雄（真機順序回歸）") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx ctx{bus};
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    // 1) 英雄（先建立，如同 setup_test_world）
    auto hero = em.create();
    em.emplace<opennefia::MetaDataComponent>(hero, opennefia::MetaDataComponent{"hero", true});
    em.emplace<opennefia::SpatialComponent>(hero, opennefia::SpatialComponent{2, 2, entt::null});
    em.emplace<opennefia::HealthComponent>(hero, 20, 20);

    // 2) 鄰接、警覺的 NPC
    auto npc = em.create();
    em.emplace<opennefia::MetaDataComponent>(npc, opennefia::MetaDataComponent{"putit", true});
    em.emplace<opennefia::SpatialComponent>(npc, opennefia::SpatialComponent{2, 3, entt::null});
    em.emplace<opennefia::NpcAiComponent>(npc, opennefia::NpcAiComponent{true, 6});
    em.emplace<opennefia::HealthComponent>(npc, 10, 10);
    em.emplace<opennefia::CombatStatsComponent>(npc,
        opennefia::CombatStatsComponent{5, 100, opennefia::NpcVariant::putit});

    // 3) 物品「最後」建立（pool 尾端）——舊版反向掃描會誤選它當英雄
    auto item = em.create();
    em.emplace<opennefia::MetaDataComponent>(item, opennefia::MetaDataComponent{"health_potion", true});
    em.emplace<opennefia::SpatialComponent>(item, opennefia::SpatialComponent{0, 0, entt::null});
    em.emplace<opennefia::ItemComponent>(item);

    em.add_system(opennefia::npc_ai_system);
    em.tick(ctx);

    // 英雄應受傷；若 hero 辨識被物品搶走，傷害會打在無 Health 的物品上，hp 維持 20
    CHECK(reg.get<opennefia::HealthComponent>(hero).hp == 15);
}

// 回歸測試：重現前端「撞 NPC 能傷敵但自己不掉血」的根因。
// move_chance=0 的 NPC（從不移動）若已警覺且貼身，仍必須攻擊英雄——
// 攻擊不該被行動機率閘門吃掉。修正前此案例會失敗（hp 維持 20）。
TEST_CASE("NPC AI — move_chance=0 的鄰接警覺 NPC 仍必定攻擊") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    opennefia::SystemCtx ctx{bus};
    auto& reg = em.registry();

    make_open_map(em, 5, 5);

    auto hero = em.create();
    em.emplace<opennefia::MetaDataComponent>(hero, opennefia::MetaDataComponent{"hero", true});
    em.emplace<opennefia::SpatialComponent>(hero, opennefia::SpatialComponent{2, 2, entt::null});
    em.emplace<opennefia::HealthComponent>(hero, 20, 20);

    auto npc = em.create();
    em.emplace<opennefia::MetaDataComponent>(npc, opennefia::MetaDataComponent{"putit", true});
    em.emplace<opennefia::SpatialComponent>(npc, opennefia::SpatialComponent{2, 3, entt::null});
    em.emplace<opennefia::NpcAiComponent>(npc, opennefia::NpcAiComponent{true, 6});
    em.emplace<opennefia::HealthComponent>(npc, 10, 10);
    em.emplace<opennefia::CombatStatsComponent>(npc,
        opennefia::CombatStatsComponent{3, 0, opennefia::NpcVariant::putit});  // move_chance=0

    em.add_system(opennefia::npc_ai_system);
    em.tick(ctx);
    em.tick(ctx);
    em.tick(ctx);

    CHECK(reg.get<opennefia::HealthComponent>(hero).hp == 11);  // 20 - 3*3
}
