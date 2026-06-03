#pragma once
#include "tile.h"
#include <vector>
#include <stdexcept>

namespace zone {

// MapData：一張地圖的稠密 tile 網格，持有在單一「地圖實體」上的 component。
//
// 仿 medps AreaTerrain（Rimworld-style dense grid）設計原則：
// - 整張地圖的 tile 是一個 component 在一個 "map entity" 上，NOT 每格一個 entity。
// - 可移動的演員 / 道具是獨立 entity（帶 SpatialComponent 定位）。
// - 序列化走標準 cereal 路徑（AllComponents 裡面）。
//
// 索引規則：tiles[x * height + y]（列優先 / column-major）——與 medps tdarray 一致。
struct MapData {
    int width{0};
    int height{0};
    std::vector<Tile> tiles;

    // 執行期可見性（不序列化；每次 compute_fov 後更新）
    std::vector<uint8_t> visible;   // 本回合視野內
    std::vector<uint8_t> explored;  // 曾探索過（霧中戰爭）

    // ---- 建構 / 重置 -------------------------------------------------------

    MapData() = default;
    MapData(int w, int h) { resize(w, h); }

    void resize(int w, int h) {
        width  = w;
        height = h;
        tiles.assign(static_cast<std::size_t>(w) * h, Tile{});
        visible.assign(static_cast<std::size_t>(w) * h, 0);
        explored.assign(static_cast<std::size_t>(w) * h, 0);
    }

    bool empty() const { return tiles.empty(); }

    // ---- tile 存取 ---------------------------------------------------------

    bool in_bounds(int x, int y) const {
        return x >= 0 && x < width && y >= 0 && y < height;
    }

    Tile& at(int x, int y)             { return tiles[idx(x, y)]; }
    const Tile& at(int x, int y) const { return tiles[idx(x, y)]; }

    // 安全存取（越界回傳 nullptr）
    Tile* get(int x, int y) {
        if (!in_bounds(x, y)) return nullptr;
        return &at(x, y);
    }

    // ---- FOV 查詢 ----------------------------------------------------------

    bool is_visible(int x, int y)  const { return in_bounds(x, y) && visible[idx(x, y)]; }
    bool is_explored(int x, int y) const { return in_bounds(x, y) && explored[idx(x, y)]; }

    void set_visible(int x, int y, bool v) {
        if (in_bounds(x, y)) visible[idx(x, y)] = static_cast<uint8_t>(v);
    }
    void set_explored(int x, int y, bool e) {
        if (in_bounds(x, y)) explored[idx(x, y)] = static_cast<uint8_t>(e);
    }
    void reset_visible() { visible.assign(visible.size(), 0); }

    // ---- 序列化（save/load 分離；load 後重置 visible/explored）-------------
    // visible / explored 是執行期快取，不需持久化，load 後以 0 填滿即可。

    template<class Archive>
    void save(Archive& ar) const { ar(width, height, tiles); }

    template<class Archive>
    void load(Archive& ar) {
        ar(width, height, tiles);
        visible.assign(static_cast<std::size_t>(width) * height, 0);
        explored.assign(static_cast<std::size_t>(width) * height, 0);
    }

private:
    std::size_t idx(int x, int y) const {
        return static_cast<std::size_t>(x) * height + static_cast<std::size_t>(y);
    }
};

} // namespace zone
