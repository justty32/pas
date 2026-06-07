#include "core/turn/npc_brain.h"
#include "core/turn/move_dir.h"
#include "core/turn/action_def.h"
#include "core/components/spatial_component.h"
#include "core/components/npc_ai_component.h"

namespace zone {

namespace {
int sign(int v) { return (v > 0) - (v < 0); }
}

Action decide_chase(entt::registry& reg, entt::entity self, entt::entity hero,
                    const ActionLibrary& lib) {
    auto* sp = reg.try_get<SpatialComponent>(self);
    if (!sp) return Action::idle();
    if (hero == entt::null || !reg.valid(hero)) return Action::idle();
    auto* hsp = reg.try_get<SpatialComponent>(hero);
    if (!hsp) return Action::idle();

    const int ddx = hsp->x - sp->x, ddy = hsp->y - sp->y;
    const int adx = ddx < 0 ? -ddx : ddx;
    const int ady = ddy < 0 ? -ddy : ddy;
    const bool adjacent = (adx <= 1 && ady <= 1 && (adx + ady) > 0);

    // caster 且相鄰 → 放 nova 技能（命中含英雄）
    if (adjacent) {
        const auto* ai = reg.try_get<NpcAiComponent>(self);
        if (ai && ai->is_caster) {
            const int idx = lib.find("npc_flame");
            if (idx >= 0)
                return Action{ ActionKind::Skill, 0, lib.at(idx).weight, idx };
        }
    }

    // 否則朝英雄移動一格（相鄰時 resolve_move 會變成撞擊攻擊）
    return Action{ ActionKind::Move, encode_dir(sign(ddx), sign(ddy)), 1 };
}

} // namespace zone
