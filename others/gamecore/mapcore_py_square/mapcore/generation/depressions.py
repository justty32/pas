"""窪地填充 (Phase 4.5)：Priority-Flood 演算法。

對齊 mapcore_py 的 hex 版 generation/depressions.py；本檔僅把 6 鄰居偏移換成
4 鄰居 (N/S/E/W)。演算法本身與拓樸無關，只是鄰居集合不同。

識別 heightmap 中無法排水到海的內陸窪地，回傳：
- lake_tiles：set of (y, x)，原始高程 > sea_level 但被水淹沒的格子（湖底）
- filled：填充後的高程圖（每格 ≥ 原始高程，供河流階段選用）

Barnes et al. 2014 "Priority-Flood" 簡化版：
  1. 將所有邊界格與海洋格推入最小堆（作為天然出口種子）。
  2. 持續從堆中取出最低的未處理格，把其鄰居的填充高程設為
     max(鄰居原始高程, 當前填充高程)，並推入堆。
  3. 處理完後，filled[y][x] > heightmap[y][x] 且 heightmap[y][x] > sea_level
     的格子即為湖格。
"""

from __future__ import annotations

import heapq

# 4 鄰居偏移 (dx, dy)；對齊 mapcore.grid.DIRECTIONS 的 E/N/W/S
_NEIGHBORS_4: tuple[tuple[int, int], ...] = (
    (1, 0),    # E
    (0, -1),   # N
    (-1, 0),   # W
    (0, 1),    # S
)


def fill_depressions(
    heightmap: list[list[float]],
    sea_level: float = 0.4,
) -> tuple[set[tuple[int, int]], list[list[float]]]:
    """Priority-Flood 窪地填充。

    參數：
        heightmap : H × W 的高程陣列，值 ∈ [0, 1]
        sea_level : 海平面高程閾值；低於此值視為已能排水

    回傳：
        lake_tiles : set of (y, x)，湖格（原始高程 > sea_level 且被淹沒）
        filled     : 填充後的高程圖（shape 同 heightmap）
    """
    H = len(heightmap)
    if H == 0:
        return set(), []
    W = len(heightmap[0])

    filled: list[list[float]] = [row[:] for row in heightmap]
    processed: list[list[bool]] = [[False] * W for _ in range(H)]
    pq: list[tuple[float, int, int]] = []

    def _push(y: int, x: int, h: float) -> None:
        if not processed[y][x]:
            processed[y][x] = True
            heapq.heappush(pq, (h, y, x))

    # 地圖邊界格：可往地圖外排水（視同無限大的外部海洋）
    for x in range(W):
        _push(0,     x, heightmap[0][x])
        _push(H - 1, x, heightmap[H - 1][x])
    for y in range(1, H - 1):
        _push(y, 0,     heightmap[y][0])
        _push(y, W - 1, heightmap[y][W - 1])

    # 所有海洋格也是天然出口
    for y in range(H):
        for x in range(W):
            if heightmap[y][x] <= sea_level:
                _push(y, x, heightmap[y][x])

    while pq:
        fill_h, y, x = heapq.heappop(pq)
        filled[y][x] = fill_h
        for dx, dy in _NEIGHBORS_4:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not processed[ny][nx]:
                # 鄰居的填充水面 = max(自身高程, 當前水面)
                new_fill = heightmap[ny][nx] if heightmap[ny][nx] >= fill_h else fill_h
                processed[ny][nx] = True
                filled[ny][nx] = new_fill
                heapq.heappush(pq, (new_fill, ny, nx))

    _EPS = 1e-9
    lake_tiles: set[tuple[int, int]] = set()
    for y in range(H):
        for x in range(W):
            if heightmap[y][x] > sea_level and filled[y][x] > heightmap[y][x] + _EPS:
                lake_tiles.add((y, x))

    return lake_tiles, filled
