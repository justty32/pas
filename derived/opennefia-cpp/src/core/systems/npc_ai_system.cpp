#include "npc_ai_system.h"

#include "core/components/npc_ai_component.h"
#include "core/components/spatial_component.h"
#include "core/maps/map_data.h"

#include <random>

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

    std::uniform_int_distribution<int> dir_dist(0, 3);
    std::uniform_int_distribution<int> act_dist(0, 1);  // 50% 機率行動

    auto view = reg.view<NpcAiComponent, SpatialComponent>();
    for (auto e : view) {
        if (act_dist(s_rng) == 0) continue;  // 50% 站原地

        auto& sp = view.get<SpatialComponent>(e);

        // 最多試 4 個方向，找到第一個可走的就動
        int start = dir_dist(s_rng);
        for (int i = 0; i < 4; ++i) {
            int d  = (start + i) % 4;
            int nx = sp.x + DX[d];
            int ny = sp.y + DY[d];
            if (map.in_bounds(nx, ny) && map.at(nx, ny).is_walkable()) {
                sp.x = nx;
                sp.y = ny;
                break;
            }
        }
    }
}

} // namespace opennefia
