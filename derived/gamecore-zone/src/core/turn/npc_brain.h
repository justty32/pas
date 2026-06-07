#pragma once
#include <entt/entt.hpp>
#include "core/turn/action.h"

namespace zone {

class ActionLibrary;

// NPC 決策：朝英雄移動一格（相鄰時即為撞擊攻擊）；caster 且相鄰時改放 nova 技能。
// 放在 core 以便 ctest 驗證（ZoneWorld::npc_decide 只是轉呼叫）。
Action decide_chase(entt::registry&, entt::entity self, entt::entity hero,
                    const ActionLibrary& lib);

} // namespace zone
