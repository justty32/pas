"""窪地填充 (Phase 4.5)：Priority-Flood 演算法。

識別 heightmap 中無法排水到海的內陸窪地，回傳：
- lake_tiles：set of (r, q)，原始高程 > sea_level 但被水淹沒的格子（湖底）
- filled：填充後的高程圖（每格 ≥ 原始高程，供河流階段選用）

演算法對齊 Barnes et al. 2014 "Priority-Flood: An Optimal Depression-Filling
and Watershed-Labeling Algorithm for Digital Elevation Models"（簡化版）：

1. 將所有邊界格與海洋格推入最小堆（作為天然出口種子）。
2. 持續從堆中取出最低的未處理格，把其鄰居的填充高程設為
   max(鄰居原始高程, 當前填充高程)，並推入堆。
3. 所有格子處理完後，filled[r][q] > heightmap[r][q] 且 heightmap[r][q] > sea_level
   的格子即為湖格。
"""

from __future__ import annotations

import heapq

# 六向軸向座標鄰居偏移 (dq, dr)；與 Hex.neighbors() 一致
_HEX_NEIGHBORS: tuple[tuple[int, int], ...] = (
    (1, 0), (-1, 0),
    (0, 1), (0, -1),
    (1, -1), (-1, 1),
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
        lake_tiles : set of (r, q)，湖格（原始高程 > sea_level 且被淹沒）
        filled     : 填充後的高程圖（shape 同 heightmap）
    """
    H = len(heightmap)
    if H == 0:
        return set(), []
    W = len(heightmap[0])

    filled: list[list[float]] = [row[:] for row in heightmap]
    processed: list[list[bool]] = [[False] * W for _ in range(H)]
    pq: list[tuple[float, int, int]] = []

    def _push(r: int, q: int, h: float) -> None:
        if not processed[r][q]:
            processed[r][q] = True
            heapq.heappush(pq, (h, r, q))

    # 地圖邊界格：可往地圖外排水（視同無限大的外部海洋）
    for q in range(W):
        _push(0,     q, heightmap[0][q])
        _push(H - 1, q, heightmap[H - 1][q])
    for r in range(1, H - 1):
        _push(r, 0,     heightmap[r][0])
        _push(r, W - 1, heightmap[r][W - 1])

    # 所有海洋格（≤ sea_level）也是天然出口
    for r in range(H):
        for q in range(W):
            if heightmap[r][q] <= sea_level:
                _push(r, q, heightmap[r][q])

    # Priority-Flood 主迴圈
    while pq:
        fill_h, r, q = heapq.heappop(pq)
        filled[r][q] = fill_h
        for dq, dr in _HEX_NEIGHBORS:
            nq, nr = q + dq, r + dr
            if 0 <= nq < W and 0 <= nr < H and not processed[nr][nq]:
                # 鄰居的填充水面 = max(自身高程, 當前水面)
                # 保證水不會往更高的格子倒流
                new_fill = heightmap[nr][nq] if heightmap[nr][nq] >= fill_h else fill_h
                processed[nr][nq] = True
                filled[nr][nq] = new_fill
                heapq.heappush(pq, (new_fill, nr, nq))

    # 湖格 = 陸地格（原始高程 > sea_level）且被水淹沒（filled > 原始高程）
    _EPS = 1e-9
    lake_tiles: set[tuple[int, int]] = set()
    for r in range(H):
        for q in range(W):
            if heightmap[r][q] > sea_level and filled[r][q] > heightmap[r][q] + _EPS:
                lake_tiles.add((r, q))

    return lake_tiles, filled
