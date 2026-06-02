#include "fov_system.h"
#include <cstdlib>  // std::abs

namespace opennefia {

// Bresenham 直線 LOS 判定。
// 起點 (x0,y0) 本身不做 blocks_sight 檢查（觀察者站在此格）。
// 終點是牆時仍回傳 true（可「看到」牆面）。
static bool has_los(const MapData& map, int x0, int y0, int x1, int y1) {
    int dx =  std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -std::abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    int x = x0, y = y0;
    for (;;) {
        if (x == x1 && y == y1) return true;
        // 中間格（非起點）擋視線 → LOS 被遮蔽
        if ((x != x0 || y != y0) && map.in_bounds(x, y) && map.at(x, y).blocks_sight())
            return false;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x += sx; }
        if (e2 <= dx) { err += dx; y += sy; }
    }
}

void compute_fov(MapData& map, int ox, int oy, int radius) {
    map.reset_visible();
    int r2 = radius * radius;
    for (int x = ox - radius; x <= ox + radius; ++x) {
        for (int y = oy - radius; y <= oy + radius; ++y) {
            if (!map.in_bounds(x, y)) continue;
            int ddx = x - ox, ddy = y - oy;
            if (ddx*ddx + ddy*ddy > r2) continue;  // 圓形視野
            if (has_los(map, ox, oy, x, y)) {
                map.set_visible(x, y, true);
                map.set_explored(x, y, true);
            }
        }
    }
}

bool los(const MapData& map, int x0, int y0, int x1, int y1) {
    return has_los(map, x0, y0, x1, y1);
}

} // namespace opennefia
