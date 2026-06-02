#include "npc_ai_system.h"

#include "core/components/npc_ai_component.h"
#include "core/components/spatial_component.h"
#include "core/components/health_component.h"
#include "core/components/combat_stats_component.h"
#include "core/maps/map_data.h"
#include "core/systems/fov_system.h"

#include <random>
#include <algorithm>  // std::abs, std::max

namespace opennefia {

// 模組級 RNG（固定種子，可重現；未來改由 SystemCtx::rng 注入）
static std::mt19937 s_rng{ 42 };

void npc_ai_system(entt::registry& reg, SystemCtx& /*ctx*/) {
    // 四個方向：N / S / E / W
    static constexpr int DX[4] = { 0,  0, 1, -1 };
    static constexpr int DY[4] = {-1,  1, 0,  0 };

    // 找地圖實體
    entt::entity map_ent = entt::null;
    for (auto e : reg.view<MapData>()) { map_ent = e; break; }
    if (map_ent == entt::null) return;
    const auto& map = reg.get<MapData>(map_ent);

    // 找英雄實體（有 SpatialComponent 但沒有 NpcAiComponent 者）
    entt::entity hero_ent = entt::null;
    for (auto e : reg.view<SpatialComponent>(entt::exclude<NpcAiComponent>)) {
        hero_ent = e; break;
    }

    std::uniform_int_distribution<int> dir_dist(0, 3);
    std::uniform_int_distribution<int> pct_dist(0, 99);

    auto view = reg.view<NpcAiComponent, SpatialComponent>();
    for (auto e : view) {
        // 使用 CombatStatsComponent 的 move_chance（無則預設 50%）
        int move_chance = 50;
        if (const auto* stats = reg.try_get<CombatStatsComponent>(e))
            move_chance = stats->move_chance;
        if (pct_dist(s_rng) >= move_chance) continue;

        auto& sp = view.get<SpatialComponent>(e);
        auto& ai = view.get<NpcAiComponent>(e);

        // ---- 視野 + 警覺狀態更新 ----
        if (hero_ent != entt::null) {
            const auto& hero_sp = reg.get<SpatialComponent>(hero_ent);
            int chebyshev = std::max(std::abs(hero_sp.x - sp.x),
                                     std::abs(hero_sp.y - sp.y));
            bool can_see = (chebyshev <= 10) &&
                           opennefia::los(map, sp.x, sp.y, hero_sp.x, hero_sp.y);
            if (can_see) {
                ai.alerted     = true;
                ai.alert_turns = 6;   // 見到英雄：記住 6 回合
            } else if (ai.alerted) {
                --ai.alert_turns;
                if (ai.alert_turns <= 0) ai.alerted = false;
            }
        }

        // ---- 追蹤模式（已警覺）----
        bool chasing = false;
        if (ai.alerted && hero_ent != entt::null) {
            const auto& hero_sp = reg.get<SpatialComponent>(hero_ent);
            int chebyshev = std::max(std::abs(hero_sp.x - sp.x),
                                     std::abs(hero_sp.y - sp.y));
            chasing = true;

            if (chebyshev == 1) {
                // 鄰接：攻擊英雄
                if (auto* hero_hp = reg.try_get<HealthComponent>(hero_ent)) {
                    int dmg = 2;
                    if (const auto* stats = reg.try_get<CombatStatsComponent>(e))
                        dmg = stats->attack;
                    hero_hp->hp -= dmg;
                    if (hero_hp->hp < 0) hero_hp->hp = 0;
                }
            } else {
                // 移動朝英雄（大 delta 軸優先）
                int hdx = hero_sp.x - sp.x;
                int hdy = hero_sp.y - sp.y;
                int cx = (hdx > 0) - (hdx < 0);
                int cy = (hdy > 0) - (hdy < 0);

                int try_x[2], try_y[2];
                if (std::abs(hdx) >= std::abs(hdy)) {
                    try_x[0] = cx; try_y[0] = 0;
                    try_x[1] = 0;  try_y[1] = cy;
                } else {
                    try_x[0] = 0;  try_y[0] = cy;
                    try_x[1] = cx; try_y[1] = 0;
                }

                bool moved = false;
                for (int i = 0; i < 2; ++i) {
                    int nx = sp.x + try_x[i];
                    int ny = sp.y + try_y[i];
                    if (nx == hero_sp.x && ny == hero_sp.y) continue;
                    if (map.in_bounds(nx, ny) && map.at(nx, ny).is_walkable()) {
                        sp.x = nx; sp.y = ny; moved = true; break;
                    }
                }
                if (!moved) chasing = false;
            }
        }

        // ---- Wander 模式（未警覺或追蹤受阻）----
        if (!chasing) {
            int start = dir_dist(s_rng);
            for (int i = 0; i < 4; ++i) {
                int d  = (start + i) % 4;
                int nx = sp.x + DX[d];
                int ny = sp.y + DY[d];
                if (map.in_bounds(nx, ny) && map.at(nx, ny).is_walkable()) {
                    sp.x = nx; sp.y = ny; break;
                }
            }
        }
    }
}

} // namespace opennefia
