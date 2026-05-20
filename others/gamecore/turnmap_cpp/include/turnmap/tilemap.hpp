#ifndef TURNMAP_TILEMAP_HPP
#define TURNMAP_TILEMAP_HPP

#include <string>
#include <vector>

#include "turnmap/tile.hpp"

namespace turnmap {

// 二維方格地圖。內部以一維 vector 行優先 (row-major) 儲存：
//     index = y * width + x
// 這是 tilemap 最常見、最有效率的儲存方式：記憶體連續、存取 O(1)。
class TileMap {
public:
    TileMap(int width, int height);

    // 由多行 ASCII 字串建構地圖，例如：
    //     "#####"
    //     "#..>#"
    //     "#####"
    // 每個字元對應一種地形，方便快速手繪關卡。
    // 無法辨識的字元（含放置單位用的 '@'、'g'）一律當成地板。
    static TileMap fromAscii(const std::vector<std::string>& rows);

    int width()  const { return width_; }
    int height() const { return height_; }

    // 座標是否落在地圖範圍內 —— 任何存取前都該先檢查，避免越界。
    bool inBounds(int x, int y) const;

    TileType at(int x, int y) const;       // 界外回傳 Wall，呼叫端更安全
    void set(int x, int y, TileType t);

    // 該格能否被單位踏入（同時檢查邊界與地形）。
    bool isWalkable(int x, int y) const;

private:
    int width_;
    int height_;
    std::vector<TileType> tiles_;
};

} // namespace turnmap

#endif // TURNMAP_TILEMAP_HPP
