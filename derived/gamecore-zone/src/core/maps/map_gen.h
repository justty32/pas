#pragma once
#include "map_data.h"
#include <random>
#include <vector>

namespace zone {

struct Room {
    int x, y, w, h;
    int cx() const { return x + w/2; }
    int cy() const { return y + h/2; }
};

// BSP 地下城生成。初始化整張地圖為牆壁，然後挖出房間+走廊。
// 回傳房間列表（第 0 個 = 英雄起始房）。
std::vector<Room> generate_bsp_dungeon(MapData& map, std::mt19937& rng);

} // namespace zone
