#include <doctest/doctest.h>
#include <entt/entt.hpp>
#include <vector>

#include "core/turn/turn_scheduler.h"
#include "core/turn/turn_world.h"
#include "core/turn/zone_effects.h"
#include "core/turn/timed_effect.h"
#include "core/turn/action_def.h"
#include "core/turn/move_dir.h"
#include "core/turn/zone_event.h"
#include <string>
#include <vector>
#include "core/maps/map_data.h"
#include "core/components/actor_component.h"
#include "core/components/player_controlled_component.h"
#include "core/components/energy_component.h"
#include "core/components/spatial_component.h"
#include "core/components/health_component.h"
#include "core/components/combat_stats_component.h"
#include "core/components/item_component.h"

using zone::Action;
using zone::ActionKind;
using zone::SchedulerMode;
using zone::TurnWorld;

namespace {

// 全可走、無視線阻擋的開放地圖。
zone::MapData open_map(int w, int h) {
    zone::MapData m(w, h);
    for (auto& t : m.tiles) t.flags = zone::TILE_WALKABLE;
    return m;
}

entt::entity make_actor(entt::registry& reg, int x, int y, bool player) {
    auto e = reg.create();
    reg.emplace<zone::ActorComponent>(e);
    if (player) reg.emplace<zone::PlayerControlledComponent>(e);
    auto& en = reg.emplace<zone::EnergyComponent>(e);
    en.value = 0; en.speed_mod = 100;
    reg.emplace<zone::SpatialComponent>(e).x = x;
    reg.get<zone::SpatialComponent>(e).y = y;
    reg.emplace<zone::HealthComponent>(e, 10, 10);
    reg.emplace<zone::CombatStatsComponent>(e);  // attack 預設 2
    return e;
}

// 推進直到玩家被阻塞（回 idle 等指令）或達上限。
void run_until_block(zone::TurnScheduler& s, TurnWorld& w, entt::entity who) {
    for (int i = 0; i < 50; ++i) {
        s.advance(w);
        if (s.waiting_actor() == who) return;
    }
}

} // namespace

// =============================================================================
// Move 效果：移動一格
// =============================================================================
TEST_CASE("zone_effects — Move 移動一格") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::MoveEffects move_fx; zone::WaitEffects wait_fx;
    zone::EffectRegistry fx;
    fx.register_kind(ActionKind::Move, &move_fx);
    fx.register_kind(ActionKind::Wait, &wait_fx);

    auto hero = make_actor(reg, 4, 4, true);
    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider npc = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, npc }; w.map = &map; w.events = &events;

    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
    run_until_block(*sch, w, hero);

    CHECK(reg.get<zone::SpatialComponent>(hero).x == 5);
    CHECK(reg.get<zone::SpatialComponent>(hero).y == 4);
}

// =============================================================================
// Move 撞牆：不可走則不移動，發 BumpedWall
// =============================================================================
TEST_CASE("zone_effects — 撞牆不動") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    map.at(5, 4).flags = 0;  // 右邊變牆
    zone::MoveEffects move_fx;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Move, &move_fx);

    auto hero = make_actor(reg, 4, 4, true);
    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider npc = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, npc }; w.map = &map; w.events = &events;

    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
    run_until_block(*sch, w, hero);

    CHECK(reg.get<zone::SpatialComponent>(hero).x == 4);  // 沒動
    REQUIRE(events.size() >= 1);
    CHECK(events.back().kind == zone::EventKind::BumpedWall);
}

// =============================================================================
// Move 攻擊：撞 NPC 扣血；致死則消滅並發 ActorDied
// =============================================================================
TEST_CASE("zone_effects — 攻擊與擊殺") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::MoveEffects move_fx;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Move, &move_fx);

    auto hero = make_actor(reg, 4, 4, true);
    auto npc  = make_actor(reg, 5, 4, false);
    reg.get<zone::CombatStatsComponent>(hero).attack = 4;
    reg.get<zone::HealthComponent>(npc) = zone::HealthComponent{ 6, 6 };

    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider decide = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, decide }; w.map = &map; w.events = &events;

    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);

    SUBCASE("一擊未死") {
        run_until_block(*sch, w, hero);
        sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
        run_until_block(*sch, w, hero);
        CHECK(reg.valid(npc));
        CHECK(reg.get<zone::HealthComponent>(npc).hp == 2);   // 6 - 4
        CHECK(reg.get<zone::SpatialComponent>(hero).x == 4);  // 攻擊不移動
    }
    SUBCASE("兩擊擊殺") {
        for (int hit = 0; hit < 2; ++hit) {
            run_until_block(*sch, w, hero);
            sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
        }
        run_until_block(*sch, w, hero);
        CHECK_FALSE(reg.valid(npc));   // 6 - 4 - 4 <= 0 → 消滅
        bool died = false;
        for (auto& ev : events) if (ev.kind == zone::EventKind::ActorDied) died = true;
        CHECK(died);
    }
}

// =============================================================================
// Move 拾取：踩上血瓶治療並消滅道具
// =============================================================================
TEST_CASE("zone_effects — 拾取血瓶治療") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::MoveEffects move_fx;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Move, &move_fx);

    auto hero = make_actor(reg, 4, 4, true);
    reg.get<zone::HealthComponent>(hero) = zone::HealthComponent{ 3, 10 };
    auto potion = reg.create();
    reg.emplace<zone::ItemComponent>(potion, zone::ItemType::health_potion, 8);
    reg.emplace<zone::SpatialComponent>(potion).x = 5;
    reg.get<zone::SpatialComponent>(potion).y = 4;

    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider npc = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, npc }; w.map = &map; w.events = &events;

    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
    run_until_block(*sch, w, hero);

    CHECK(reg.get<zone::SpatialComponent>(hero).x == 5);
    CHECK(reg.get<zone::HealthComponent>(hero).hp == 10);  // 3 + min(8, 7) = 10
    CHECK_FALSE(reg.valid(potion));
}

// =============================================================================
// Cast：多回合詠唱 nova 傷鄰格；詠唱中被移動打斷則不發傷害
// =============================================================================
TEST_CASE("zone_effects — Cast 詠唱 nova 與打斷") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::MoveEffects move_fx;
    zone::CastEffects cast_fx; cast_fx.damage = 4;
    zone::EffectRegistry fx;
    fx.register_kind(ActionKind::Move, &move_fx);
    fx.register_kind(ActionKind::Cast, &cast_fx);

    auto hero = make_actor(reg, 4, 4, true);
    auto npc  = make_actor(reg, 5, 4, false);  // 鄰格
    reg.get<zone::HealthComponent>(npc) = zone::HealthComponent{ 10, 10 };

    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider decide = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, decide }; w.map = &map; w.events = &events;
    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);

    SUBCASE("詠唱完成傷鄰格") {
        run_until_block(*sch, w, hero);
        sch->submit(hero, Action{ ActionKind::Cast, 0, 3 });
        run_until_block(*sch, w, hero);
        CHECK(reg.get<zone::HealthComponent>(npc).hp == 6);  // 10 - 4
    }
    SUBCASE("詠唱中被移動打斷→無傷害") {
        run_until_block(*sch, w, hero);
        sch->submit(hero, Action{ ActionKind::Cast, 0, 3 });
        sch->advance(w);  // channel0
        sch->advance(w);  // channel1
        sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(0, 1), 1 });  // 打斷
        run_until_block(*sch, w, hero);
        CHECK(reg.get<zone::HealthComponent>(npc).hp == 10);   // nova 未發
        CHECK(reg.get<zone::SpatialComponent>(hero).y == 5);   // 改成移動
    }
}

// =============================================================================
// DoT 持續效果：每回合扣血、過期、致死
// =============================================================================
TEST_CASE("timed_effect — 逐回合扣血並過期") {
    entt::registry reg;
    auto e = reg.create();
    reg.emplace<zone::HealthComponent>(e, 10, 10);
    zone::EffectRegistry fx;
    zone::NpcDecider none;
    TurnWorld w{ reg, fx, none };

    zone::apply_timed_effect(reg, e, zone::TimedEffectKind::Burning, 3, 2);
    zone::tick_timed_effects(w, e);
    CHECK(reg.get<zone::HealthComponent>(e).hp == 8);
    zone::tick_timed_effects(w, e);
    zone::tick_timed_effects(w, e);
    CHECK(reg.get<zone::HealthComponent>(e).hp == 4);
    CHECK(reg.get<zone::TimedEffectsComponent>(e).effects.empty());  // 3 回合後過期
    zone::tick_timed_effects(w, e);
    CHECK(reg.get<zone::HealthComponent>(e).hp == 4);                // 不再扣
}

TEST_CASE("die — 玩家操控者致死不消滅實體（只 game over）") {
    entt::registry reg;
    auto hero = reg.create();
    reg.emplace<zone::PlayerControlledComponent>(hero);
    reg.emplace<zone::HealthComponent>(hero, 2, 10);
    zone::EffectRegistry fx; zone::NpcDecider none;
    TurnWorld w{ reg, fx, none };
    zone::apply_timed_effect(reg, hero, zone::TimedEffectKind::Poison, 3, 5);
    zone::tick_timed_effects(w, hero);   // 2 - 5 <= 0
    CHECK(reg.valid(hero));              // 實體仍在（供 game over / restart）
    CHECK(reg.get<zone::HealthComponent>(hero).hp <= 0);
}

TEST_CASE("timed_effect — 致死 DoT 消滅並發事件") {
    entt::registry reg;
    auto e = reg.create();
    reg.emplace<zone::HealthComponent>(e, 3, 10);
    std::vector<zone::ZoneEvent> events;
    zone::EffectRegistry fx;
    zone::NpcDecider none;
    TurnWorld w{ reg, fx, none }; w.events = &events;

    zone::apply_timed_effect(reg, e, zone::TimedEffectKind::Poison, 5, 5);
    zone::tick_timed_effects(w, e);   // 3 - 5 <= 0 → 死
    CHECK_FALSE(reg.valid(e));
    bool died = false;
    for (auto& ev : events) if (ev.kind == zone::EventKind::ActorDied) died = true;
    CHECK(died);
}

TEST_CASE("timed_effect — 透過排程器在 actor 回合 tick") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::EffectRegistry fx;  // 空：NPC idle 不需 effect
    auto e = make_actor(reg, 4, 4, false);  // NPC，每回合 idle
    reg.get<zone::HealthComponent>(e) = zone::HealthComponent{ 10, 10 };
    zone::apply_timed_effect(reg, e, zone::TimedEffectKind::Burning, 3, 2);

    zone::NpcDecider npc = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, npc }; w.map = &map;
    w.on_actor_turn = [](TurnWorld& tw, entt::entity x){ zone::tick_timed_effects(tw, x); };

    auto sch = zone::make_scheduler(SchedulerMode::EnergyInstant);
    for (int i = 0; i < 12 && reg.valid(e); ++i) sch->advance(w);

    REQUIRE(reg.valid(e));
    CHECK(reg.get<zone::HealthComponent>(e).hp == 4);  // 3 回合燒 6 點後過期
}

// =============================================================================
// 資料驅動：ActionLibrary JSON 載入 + LibraryEffects 套用
// =============================================================================
TEST_CASE("action_def — 載入 JSON 並查名") {
    zone::ActionLibrary lib;
    REQUIRE(lib.load_json(std::string(ZONE_TEST_DATA_DIR) + "/actions.json"));
    const int fb = lib.find("fireball");
    REQUIRE(fb >= 0);
    CHECK(lib.at(fb).weight == 3);
    CHECK(lib.at(fb).nova_damage == 4);
    CHECK(lib.at(fb).dot_turns == 3);
    CHECK(lib.find("heal") >= 0);
    CHECK(lib.find("nonexistent") == -1);
}

TEST_CASE("action_def — load_defaults 後備") {
    zone::ActionLibrary lib; lib.load_defaults();
    CHECK(lib.find("fireball") >= 0);
    CHECK(lib.find("heal") >= 0);
}

TEST_CASE("LibraryEffects — 資料驅動 fireball nova + 燃燒") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::ActionLibrary lib; lib.load_defaults();
    zone::LibraryEffects lib_fx; lib_fx.lib = &lib;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Skill, &lib_fx);

    auto hero = make_actor(reg, 4, 4, true);
    auto npc  = make_actor(reg, 5, 4, false);
    reg.get<zone::HealthComponent>(npc) = zone::HealthComponent{ 10, 10 };

    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider decide = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, decide }; w.map = &map; w.events = &events;
    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);

    const int fb = lib.find("fireball");
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Skill, 0, lib.at(fb).weight, fb });  // weight=3 → channel
    run_until_block(*sch, w, hero);

    CHECK(reg.get<zone::HealthComponent>(npc).hp == 6);          // nova 4
    CHECK(reg.all_of<zone::TimedEffectsComponent>(npc));         // 殘留燃燒已施加
}

TEST_CASE("LibraryEffects — 資料驅動 heal 回血") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::ActionLibrary lib; lib.load_defaults();
    zone::LibraryEffects lib_fx; lib_fx.lib = &lib;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Skill, &lib_fx);

    auto hero = make_actor(reg, 4, 4, true);
    reg.get<zone::HealthComponent>(hero) = zone::HealthComponent{ 3, 10 };

    std::vector<zone::ZoneEvent> events;
    zone::NpcDecider decide = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, decide }; w.map = &map; w.events = &events;
    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);

    const int h = lib.find("heal");
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Skill, 0, lib.at(h).weight, h });
    run_until_block(*sch, w, hero);

    CHECK(reg.get<zone::HealthComponent>(hero).hp == 10);  // 3 + 8 → 封頂 10
    CHECK(reg.all_of<zone::TimedEffectsComponent>(hero));  // 並施加回復 buff
}

TEST_CASE("resolve_nova — radius 與 dot_kind") {
    entt::registry reg;
    zone::MapData map = open_map(12, 12);
    zone::EffectRegistry fx; zone::NpcDecider none;
    TurnWorld w{ reg, fx, none }; w.map = &map;

    auto self = make_actor(reg, 6, 6, false);
    auto a1 = make_actor(reg, 7, 6, false);  // chebyshev 1
    auto a2 = make_actor(reg, 8, 6, false);  // chebyshev 2
    reg.get<zone::HealthComponent>(a1) = zone::HealthComponent{ 20, 20 };
    reg.get<zone::HealthComponent>(a2) = zone::HealthComponent{ 20, 20 };

    SUBCASE("radius1 只命中鄰格") {
        zone::resolve_nova(w, self, 5, 0, 0, 1, 0);
        CHECK(reg.get<zone::HealthComponent>(a1).hp == 15);
        CHECK(reg.get<zone::HealthComponent>(a2).hp == 20);
    }
    SUBCASE("radius2 命中兩者") {
        zone::resolve_nova(w, self, 5, 0, 0, 2, 0);
        CHECK(reg.get<zone::HealthComponent>(a1).hp == 15);
        CHECK(reg.get<zone::HealthComponent>(a2).hp == 15);
    }
    SUBCASE("dot_kind=1 施加中毒") {
        zone::resolve_nova(w, self, 1, 5, 2, 1, 1);
        REQUIRE(reg.all_of<zone::TimedEffectsComponent>(a1));
        CHECK(reg.get<zone::TimedEffectsComponent>(a1).effects.front().kind
              == zone::TimedEffectKind::Poison);
    }
}

TEST_CASE("trace — 效果會吐出 debug 行") {
    entt::registry reg;
    zone::MapData map = open_map(8, 8);
    zone::MoveEffects move_fx;
    zone::EffectRegistry fx; fx.register_kind(ActionKind::Move, &move_fx);
    auto hero = make_actor(reg, 4, 4, true);

    std::vector<std::string> log;
    zone::NpcDecider npc = [](entt::registry&, entt::entity){ return Action::idle(); };
    TurnWorld w{ reg, fx, npc }; w.map = &map;
    w.trace = [&log](const std::string& s){ log.push_back(s); };

    auto sch = zone::make_scheduler(SchedulerMode::EnergyChannel);
    run_until_block(*sch, w, hero);
    sch->submit(hero, Action{ ActionKind::Move, zone::encode_dir(1, 0), 1 });
    run_until_block(*sch, w, hero);

    CHECK_FALSE(log.empty());  // 至少有「移動→…」一行
}
