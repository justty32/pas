#pragma once
#include <entt/entt.hpp>
#include "core/ecs/system_ctx.h"

namespace zone {

// NPC wander AI 系統。
// 對每個有 NpcAiComponent + SpatialComponent 的實體，以 50% 機率向隨機可走方向移動一格。
// 使用模組級固定種子 RNG（可重現，未來可改由 SystemCtx 注入）。
void npc_ai_system(entt::registry& reg, SystemCtx& ctx);

} // namespace zone
