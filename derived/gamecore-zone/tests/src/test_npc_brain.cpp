#include <doctest/doctest.h>
#include <entt/entt.hpp>

#include "core/turn/npc_brain.h"
#include "core/turn/action_def.h"
#include "core/turn/move_dir.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"

using zone::Action;
using zone::ActionKind;

namespace {
entt::entity at(entt::registry& reg, int x, int y) {
    auto e = reg.create();
    auto& sp = reg.emplace<zone::SpatialComponent>(e);
    sp.x = x; sp.y = y;
    return e;
}
}

TEST_CASE("npc_brain — 朝英雄移動的方向正確") {
    entt::registry reg;
    zone::ActionLibrary lib; lib.load_defaults();
    auto npc  = at(reg, 2, 2);
    auto hero = at(reg, 7, 5);  // 右下方

    Action a = zone::decide_chase(reg, npc, hero, lib);
    REQUIRE(a.kind == ActionKind::Move);
    int dx, dy; zone::decode_dir(a.param, dx, dy);
    CHECK(dx == 1);   // 朝 +x
    CHECK(dy == 1);   // 朝 +y
}

TEST_CASE("npc_brain — 一般 NPC 相鄰仍走 Move（撞擊攻擊）") {
    entt::registry reg;
    zone::ActionLibrary lib; lib.load_defaults();
    auto npc  = at(reg, 4, 4);
    reg.emplace<zone::NpcAiComponent>(npc);  // 非 caster
    auto hero = at(reg, 5, 4);               // 相鄰

    Action a = zone::decide_chase(reg, npc, hero, lib);
    CHECK(a.kind == ActionKind::Move);
}

TEST_CASE("npc_brain — caster 相鄰放 npc_flame 技能") {
    entt::registry reg;
    zone::ActionLibrary lib; lib.load_defaults();
    auto npc  = at(reg, 4, 4);
    reg.emplace<zone::NpcAiComponent>(npc).is_caster = true;
    auto hero = at(reg, 5, 4);               // 相鄰

    Action a = zone::decide_chase(reg, npc, hero, lib);
    REQUIRE(a.kind == ActionKind::Skill);
    CHECK(a.def == lib.find("npc_flame"));
    CHECK(a.weight == lib.at(lib.find("npc_flame")).weight);
}

TEST_CASE("npc_brain — caster 但距離遠時仍移動") {
    entt::registry reg;
    zone::ActionLibrary lib; lib.load_defaults();
    auto npc  = at(reg, 0, 0);
    reg.emplace<zone::NpcAiComponent>(npc).is_caster = true;
    auto hero = at(reg, 6, 0);               // 不相鄰

    Action a = zone::decide_chase(reg, npc, hero, lib);
    CHECK(a.kind == ActionKind::Move);
}
