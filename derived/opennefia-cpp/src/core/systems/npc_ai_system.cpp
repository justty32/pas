#include "npc_ai_system.h"

#include "core/components/npc_ai_component.h"
#include "core/components/spatial_component.h"
#include "core/components/health_component.h"
#include "core/maps/map_data.h"

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
    std::uniform_int_distribution<int> act_dist(0, 1);  // 50% 機率行動

    auto view = reg.view<NpcAiComponent, SpatialComponent>();
    for (auto e : view) {
        if (act_dist(s_rng) == 0) continue;  // 50% 站原地

        auto& sp = view.get<SpatialComponent>(e);

        // ---- 追蹤模式：英雄在 8 格 Chebyshev 距離內 ----
        bool chasing = false;
        if (hero_ent != entt::null) {
            const auto& hero_sp = reg.get<SpatialComponent>(hero_ent);
            int chebyshev = std::max(std::abs(hero_sp.x - sp.x),
                                     std::abs(hero_sp.y - sp.y));
            if (chebyshev <= 8) {
                chasing = true;

                // 鄰接時直接攻擊英雄（不移動）
                if (chebyshev == 1) {
                    if (auto* hero_hp = reg.try_get<HealthComponent>(hero_ent)) {
                        hero_hp->hp -= 2;
                        if (hero_hp->hp < 0) hero_hp->hp = 0;
                    }
                } else {
                    int hdx = hero_sp.x - sp.x;
                    int hdy = hero_sp.y - sp.y;
                    int cx = (hdx > 0) - (hdx < 0);  // sign(hdx)
                    int cy = (hdy > 0) - (hdy < 0);  // sign(hdy)

                    // 優先沿 delta 較大的軸移動（4 方向）
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
                        if (nx == hero_sp.x && ny == hero_sp.y) continue;  // 不踩英雄
                        if (map.in_bounds(nx, ny) && map.at(nx, ny).is_walkable()) {
                            sp.x = nx; sp.y = ny; moved = true; break;
                        }
                    }
                    if (!moved) chasing = false;  // 被擋住，退回 wander
                }
            }
        }

        // ---- Wander 模式 ----
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
