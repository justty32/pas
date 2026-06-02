#pragma once
#include "core/maps/map_data.h"

namespace opennefia {

// compute_fov — 以 Bresenham 射線計算英雄視野。
//
// 對半徑 radius 圓內每格投射射線；射線沿途遇到 blocks_sight 格則停止。
// 更新 map.visible[]（本回合視野）與 map.explored[]（霧中戰爭）。
// 複雜度 O(R² · R) = O(R³)；radius ≤ 10 時效能可接受（地圖小）。
void compute_fov(MapData& map, int origin_x, int origin_y, int radius);

} // namespace opennefia
