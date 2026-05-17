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
# 最便宜可通行地形的成本；乘上 hex distance 作為 A* heuristic 的下界，確保 admissibility
# （絕不高估剩餘成本）。若 TERRAIN_COST 中所有可通行值 >= 1.0，h = hex_distance 即夠 admissible。
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
    # 三張 2D array 對應未來 C++ 版的 std::vector：g_score / came_from / closed
    # 用 INF 初始化省去「未訪問過」的特殊判斷，第一次抵達就一定 < INF
    g_score: list[list[float]] = [[INF] * w for _ in range(h)]
    came_from: list[list[Optional[Hex]]] = [[None] * w for _ in range(h)]
    closed: list[list[bool]] = [[False] * w for _ in range(h)]

    g_score[start.r][start.q] = 0.0
    # heap 元素第 2 個 counter 是 tie-breaker：當 f-score 相同時用插入順序排序，
    # 避免 heap 試圖比較不可比的 Hex 物件而拋例外
    open_heap: list[tuple[float, int, Hex]] = []
    counter = 0
    heapq.heappush(
        open_heap, (float(distance(start, goal)) * MIN_PASSABLE_COST, counter, start)
    )

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        cq, cr = current.q, current.r
        # 同一個 hex 可能被多次 push 到 heap（因為我們用 lazy deletion 而非 decrease-key）
        # 跳過已 closed 的，相當於用最新的 g_score 處理
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
            # 不可通行格子不會成為路徑的中間節點；起點本身不可通行時仍允許離開
            # （這就是為什麼 is_passable 檢查只放在鄰居判斷裡）
            if not is_passable(n_tile.terrain):
                continue
            nq, nr = n.q, n.r
            if closed[nr][nq]:
                continue
            # 邊權 = 進入目標格的 terrain_cost；起點不算。對齊 Civ-like「進入該地形要花多少 move」
            step = terrain_cost(n_tile.terrain)
            if river_crossing_cost > 0:
                # 跨河成本跟流量成正比：大河比小溪難跨
                rs = get_river_strength(tile_map, current, d)
                if rs > 0:
                    step += river_crossing_cost * rs
            tentative = current_g + step
            if tentative < g_score[nr][nq]:
                g_score[nr][nq] = tentative
                came_from[nr][nq] = current
                # f = g + h；heuristic 必須是 hex distance × MIN_PASSABLE_COST 才 admissible
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
