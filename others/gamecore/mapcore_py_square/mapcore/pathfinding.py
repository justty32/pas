"""A* 尋路（4 鄰居版）。

對應 mapcore_py/mapcore/pathfinding.py：
- 啟發式 h(n) = Manhattan distance(n, goal) × MIN_PASSABLE_COST，admissible
- 邊權 = 進入目標格的 terrain_cost；起點不算
- g_score / came_from / closed 全 2D array，對齊未來 C++ 版的記憶體佈局
- 不可通行 (math.inf) 格子不能當中間節點；起點本身不可通行仍可離開
"""

from __future__ import annotations

import heapq
import math
from typing import Optional

from .grid import DIRECTIONS, Coord, distance
from .map import TileMap, is_passable, terrain_cost
from .terrain import DEFAULT_REGISTRY

INF = math.inf
MIN_PASSABLE_COST = min(
    d.move_cost for d in DEFAULT_REGISTRY.all_defs() if math.isfinite(d.move_cost)
)


def astar(
    tile_map: TileMap,
    start: Coord,
    goal: Coord,
) -> Optional[list[Coord]]:
    """從 start 到 goal 的最短路徑（含兩端點），不可達回 None。"""
    if not tile_map.in_bounds(start) or not tile_map.in_bounds(goal):
        return None
    if start == goal:
        return [start]

    w, h = tile_map.width, tile_map.height
    g_score: list[list[float]] = [[INF] * w for _ in range(h)]
    came_from: list[list[Optional[Coord]]] = [[None] * w for _ in range(h)]
    closed: list[list[bool]] = [[False] * w for _ in range(h)]

    g_score[start.y][start.x] = 0.0
    # heap 元素第 2 個 counter 是 tie-breaker，避免比較不可比的 Coord
    open_heap: list[tuple[float, int, Coord]] = []
    counter = 0
    heapq.heappush(
        open_heap, (float(distance(start, goal)) * MIN_PASSABLE_COST, counter, start)
    )

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        cx, cy = current.x, current.y
        # lazy deletion：同一個 Coord 可能被多次 push，跳過已 closed 的
        if closed[cy][cx]:
            continue
        if current == goal:
            return _reconstruct(came_from, current)
        closed[cy][cx] = True

        current_g = g_score[cy][cx]
        for d in range(4):
            n = current + DIRECTIONS[d]
            if not tile_map.in_bounds(n):
                continue
            n_tile = tile_map.get(n)
            # 不可通行格子不能當中間節點；起點不可通行時仍允許離開
            if not is_passable(n_tile.terrain):
                continue
            nx, ny = n.x, n.y
            if closed[ny][nx]:
                continue
            step = terrain_cost(n_tile.terrain)
            tentative = current_g + step
            if tentative < g_score[ny][nx]:
                g_score[ny][nx] = tentative
                came_from[ny][nx] = current
                f = tentative + distance(n, goal) * MIN_PASSABLE_COST
                counter += 1
                heapq.heappush(open_heap, (f, counter, n))

    return None


def _reconstruct(came_from: list[list[Optional[Coord]]], end: Coord) -> list[Coord]:
    path: list[Coord] = [end]
    cur = came_from[end.y][end.x]
    while cur is not None:
        path.append(cur)
        cur = came_from[cur.y][cur.x]
    path.reverse()
    return path


def path_cost(tile_map: TileMap, path: list[Coord]) -> float:
    """路徑總成本 = 進入每個非起點格的 terrain_cost 累加。"""
    if len(path) <= 1:
        return 0.0
    total = 0.0
    for c in path[1:]:
        total += terrain_cost(tile_map.get(c).terrain)
    return total
