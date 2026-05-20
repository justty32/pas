#include "turnmap/tilemap.hpp"

#include <algorithm>

namespace turnmap {

TileMap::TileMap(int width, int height)
    : width_(width),
      height_(height),
      tiles_(static_cast<size_t>(width) * static_cast<size_t>(height), TileType::Floor) {}

TileMap TileMap::fromAscii(const std::vector<std::string>& rows) {
    const int height = static_cast<int>(rows.size());
    int width = 0;
    for (const auto& r : rows) {
        width = std::max(width, static_cast<int>(r.size()));
    }

    TileMap map(width, height);
    for (int y = 0; y < height; ++y) {
        const std::string& row = rows[static_cast<size_t>(y)];
        for (int x = 0; x < width; ++x) {
            // 行尾不足寬度的部分補成牆，讓地圖永遠是完整的矩形。
            const char c = (x < static_cast<int>(row.size())) ? row[static_cast<size_t>(x)] : '#';
            TileType t;
            switch (c) {
                case '#': t = TileType::Wall;  break;
                case '~': t = TileType::Water; break;
                case '>': t = TileType::Exit;  break;
                default:  t = TileType::Floor; break;  // '.'、'@'、'g' 等都當地板
            }
            map.set(x, y, t);
        }
    }
    return map;
}

bool TileMap::inBounds(int x, int y) const {
    return x >= 0 && x < width_ && y >= 0 && y < height_;
}

TileType TileMap::at(int x, int y) const {
    if (!inBounds(x, y)) return TileType::Wall;  // 界外視為牆，呼叫端不必到處檢查
    return tiles_[static_cast<size_t>(y) * static_cast<size_t>(width_) + static_cast<size_t>(x)];
}

void TileMap::set(int x, int y, TileType t) {
    if (inBounds(x, y)) {
        tiles_[static_cast<size_t>(y) * static_cast<size_t>(width_) + static_cast<size_t>(x)] = t;
    }
}

bool TileMap::isWalkable(int x, int y) const {
    return inBounds(x, y) && tileWalkable(at(x, y));
}

} // namespace turnmap
