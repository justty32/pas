#ifndef TURNMAP_PATHFINDING_HPP
#define TURNMAP_PATHFINDING_HPP

#include <vector>

#include "turnmap/tilemap.hpp"

namespace turnmap {

// 方格座標。用於尋路的輸入與輸出。
struct Vec2 {
    int x = 0;
    int y = 0;
};

// 在方格地圖上用 A* 找從 start 到 goal 的最短路徑（四方向移動，每步成本 1）。
//
// 回傳的路徑「不含 start、含 goal」，依序是要踏上的格子；
// path.front() 就是下一步要走的那一格。找不到路徑時回傳空 vector。
//
// 設計對齊 mapcore_cpp_square 的 astar：g_score / came_from / closed 全部用
// flat 一維陣列，heuristic = Manhattan 距離（4 鄰居 + 單位成本下 admissible）。
//
// 特例：goal 那一格「即使不可走」也允許作為終點 —— 這樣敵人可以把玩家
// 所在的格子當成目標，走到旁邊時下一步就會踏上去（觸發 bump-to-attack）。
std::vector<Vec2> findPath(const TileMap& map, Vec2 start, Vec2 goal);

} // namespace turnmap

#endif // TURNMAP_PATHFINDING_HPP
