"""A* 尋路。

設計理念：
- g_score / came_from / closed 全部用 2D array (list of list)，不用 dict。
  對齊未來 C++ 移植（指標 / 陣列）的記憶體佈局。
- 啟發式 h(n) = hex distance(n, goal)，乘上「最便宜可通行地形成本」確保 admissibility。
  目前所有可通行地形成本 ≥ 1.0，所以 hex distance 本身就是 admissible heuristic。
- 邊權 = 進入目標格的 terrain_cost。起點不計成本。
- 不可通行 (math.inf) 的格子不會作為中間節點；起點本身可不可通行均可從中離開。

對齊 analysis/wesnoth/details/astar_pathfinding_geometry.md 的 A* 結構。
"""

from __future__ import annotations

import heapq
import math
from typing import Optional

from .hex import DIRECTIONS, Hex, distance
from .map import TERRAIN_COST, TileMap, is_passable, terrain_cost
from .rivers import get_river_strength

INF = math.inf
MIN_PASSABLE_COST = min(c for c in TERRAIN_COST.values() if math.isfinite(c))


def astar(
    tile_map: TileMap,
    start: Hex,
    goal: Hex,
    river_crossing_cost: float = 0.0,
) -> Optional[list[Hex]]:
    """從 start 到 goal 的最短路徑（含兩端點），不可達回 None。

    river_crossing_cost：跨越河流邊每點流量加的成本（0 表示不影響；math.inf 表示不可跨）。
    實際 = river_crossing_cost × 該邊流量（strength）。
    """
    if not tile_map.in_bounds(start) or not tile_map.in_bounds(goal):
        return None
    if start == goal:
        return [start]

    w, h = tile_map.width, tile_map.height
    g_score: list[list[float]] = [[INF] * w for _ in range(h)]
    came_from: list[list[Optional[Hex]]] = [[None] * w for _ in range(h)]
    closed: list[list[bool]] = [[False] * w for _ in range(h)]

    g_score[start.r][start.q] = 0.0
    open_heap: list[tuple[float, int, Hex]] = []
    counter = 0
    heapq.heappush(
        open_heap, (float(distance(start, goal)) * MIN_PASSABLE_COST, counter, start)
    )

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        cq, cr = current.q, current.r
        if closed[cr][cq]:
            continue
        if current == goal:
            return _reconstruct(came_from, current)
        closed[cr][cq] = True

        current_g = g_score[cr][cq]
        for d in range(6):
            n = current + DIRECTIONS[d]
            if not tile_map.in_bounds(n):
                continue
            n_tile = tile_map.get(n)
            if not is_passable(n_tile.terrain):
                continue
            nq, nr = n.q, n.r
            if closed[nr][nq]:
                continue
            step = terrain_cost(n_tile.terrain)
            if river_crossing_cost > 0:
                rs = get_river_strength(tile_map, current, d)
                if rs > 0:
                    step += river_crossing_cost * rs
            tentative = current_g + step
            if tentative < g_score[nr][nq]:
                g_score[nr][nq] = tentative
                came_from[nr][nq] = current
                f = tentative + distance(n, goal) * MIN_PASSABLE_COST
                counter += 1
                heapq.heappush(open_heap, (f, counter, n))

    return None


def _reconstruct(came_from: list[list[Optional[Hex]]], end: Hex) -> list[Hex]:
    path: list[Hex] = [end]
    cur = came_from[end.r][end.q]
    while cur is not None:
        path.append(cur)
        cur = came_from[cur.r][cur.q]
    path.reverse()
    return path


def path_cost(tile_map: TileMap, path: list[Hex]) -> float:
    """路徑總成本 = 進入每個非起點格的 terrain_cost 累加。"""
    if len(path) <= 1:
        return 0.0
    total = 0.0
    for h in path[1:]:
        total += terrain_cost(tile_map.get(h).terrain)
    return total
