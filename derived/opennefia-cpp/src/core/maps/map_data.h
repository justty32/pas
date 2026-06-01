#pragma once
#include "tile.h"
#include <vector>
#include <stdexcept>

namespace opennefia {

// MapData：一張地圖的稠密 tile 網格，持有在單一「地圖實體」上的 component。
//
// 仿 medps AreaTerrain（Rimworld-style dense grid）設計原則：
// - 整張地圖的 tile 是一個 component 在一個 "map entity" 上，NOT 每格一個 entity。
// - 可移動的演員 / 道具是獨立 entity（帶 SpatialComponent 定位）。
// - 序列化走標準 cereal 路徑（AllComponents 裡面）。
//
// 索引規則：tiles[x * height + y]（列優先 / column-major）——與 medps tdarray 一致。
// 之後若需要更豐富的 2D 存取 API（eachxy、getptr...），可升級引入移植版 tdarray。
struct MapData {
    int width{0};
    int height{0};
    std::vector<Tile> tiles;

    // ---- 建構 / 重置 -------------------------------------------------------

    MapData() = default;
    MapData(int w, int h) { resize(w, h); }

    void resize(int w, int h) {
        width  = w;
        height = h;
        tiles.assign(static_cast<std::size_t>(w) * h, Tile{});
    }

    bool empty() const { return tiles.empty(); }

    // ---- 存取 ---------------------------------------------------------------

    bool in_bounds(int x, int y) const {
        return x >= 0 && x < width && y >= 0 && y < height;
    }

    Tile& at(int x, int y) {
        return tiles[static_cast<std::size_t>(x) * height + y];
    }
    const Tile& at(int x, int y) const {
        return tiles[static_cast<std::size_t>(x) * height + y];
    }

    // 安全存取（越界回傳 nullptr）
    Tile* get(int x, int y) {
        if (!in_bounds(x, y)) return nullptr;
        return &at(x, y);
    }

    // ---- 序列化（Phase 3 路徑）----------------------------------------------
    // 需 save_load.h 包含 <cereal/types/vector.hpp>（已加入）。

    template<class Archive>
    void serialize(Archive& ar) { ar(width, height, tiles); }
};

} // namespace opennefia
