#pragma once
#include <cstdint>

namespace opennefia {

// 地圖單格的資料（仿 medps area_terrain.h）。
// terrain：地形 def id（圖形層負責對應視覺；核心層只看 flags）。
// flags：從 terrain def 快取出來的模擬相關旗標，FOV / 尋路不必查 def table。
inline constexpr uint8_t TILE_WALKABLE     = 1 << 0;  // 可走入
inline constexpr uint8_t TILE_BLOCKS_SIGHT = 1 << 1;  // 擋視線

struct Tile {
    uint16_t terrain{0};
    uint8_t  flags{0};

    bool is_walkable()     const { return (flags & TILE_WALKABLE)     != 0; }
    bool blocks_sight()    const { return (flags & TILE_BLOCKS_SIGHT) != 0; }

    template<class Archive>
    void serialize(Archive& ar) { ar(terrain, flags); }
};

} // namespace opennefia
