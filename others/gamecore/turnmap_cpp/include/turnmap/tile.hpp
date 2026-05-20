#ifndef TURNMAP_TILE_HPP
#define TURNMAP_TILE_HPP

namespace turnmap {

// 地圖上每一格 (tile) 的種類。
// 回合制 tilemap 的第一個關鍵：每種地形決定「能不能走」與「長什麼樣」。
enum class TileType {
    Floor,   // 地板：可通行
    Wall,    // 牆壁：阻擋移動
    Water,   // 水：阻擋移動（示範第二種不可走地形）
    Exit,    // 出口：玩家走到這裡就獲勝
};

// 取得某種地形在終端機上的顯示字元。
inline char tileGlyph(TileType t) {
    switch (t) {
        case TileType::Floor: return '.';
        case TileType::Wall:  return '#';
        case TileType::Water: return '~';
        case TileType::Exit:  return '>';
    }
    return '?';
}

// 該地形是否可被單位踏入。出口也算可走（踩上去才能觸發獲勝）。
inline bool tileWalkable(TileType t) {
    return t == TileType::Floor || t == TileType::Exit;
}

} // namespace turnmap

#endif // TURNMAP_TILE_HPP
