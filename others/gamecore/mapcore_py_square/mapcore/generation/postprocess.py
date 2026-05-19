"""地圖後處理 (Phase 4)。

對既有 TileMap 做：
- 連通分量分析 (DFS)
- 清掉過小的陸地島嶼（淹成 OCEAN）
- 填掉「不接地圖邊界」的小水體（避免內陸有奇怪小洞）
- 清完後重新標記 COAST

對齊 mapcore_py 的 hex 版 generation/postprocess.py；本檔僅把 Hex(q,r) 換成
Coord(x,y) 並改用 4 鄰居。注意 4 鄰居連通分量平均面積比 6 鄰居小，
island_min_size / lake_max_size 預設可能要視實際結果調整。
"""

from __future__ import annotations

from typing import Callable

from ..grid import Coord
from ..map import TerrainType, TileMap
from ..terrain import DEFAULT_REGISTRY
from .classify import expand_coast


def is_land(terrain_id: int) -> bool:
    return not DEFAULT_REGISTRY.is_water(terrain_id)


def is_water(terrain_id: int) -> bool:
    return DEFAULT_REGISTRY.is_water(terrain_id)


def find_components(
    tile_map: TileMap,
    predicate: Callable[[int], bool],
) -> list[list[Coord]]:
    """DFS 找出 predicate(terrain) 為真的格子組成的所有連通分量。"""
    h_map = tile_map.height
    w_map = tile_map.width
    visited = [[False] * w_map for _ in range(h_map)]
    components: list[list[Coord]] = []

    for y in range(h_map):
        for x in range(w_map):
            if visited[y][x]:
                continue
            if not predicate(tile_map.get(Coord(x, y)).terrain):
                visited[y][x] = True
                continue
            comp: list[Coord] = []
            stack = [Coord(x, y)]
            visited[y][x] = True
            while stack:
                c = stack.pop()
                comp.append(c)
                for n in tile_map.neighbors(c):
                    if visited[n.y][n.x]:
                        continue
                    if predicate(tile_map.get(n).terrain):
                        visited[n.y][n.x] = True
                        stack.append(n)
                    else:
                        # 邊界鄰居也標 visited，防止外層 for 又掃進來
                        visited[n.y][n.x] = True
            components.append(comp)
    return components


def remove_small_islands(tile_map: TileMap, min_size: int = 3) -> int:
    """把 size < min_size 的陸地連通分量整片淹成 OCEAN。回傳被淹的格數。"""
    if min_size <= 1:
        return 0
    removed = 0
    for comp in find_components(tile_map, is_land):
        if len(comp) < min_size:
            for c in comp:
                tile_map.set_terrain(c, TerrainType.OCEAN)
            removed += len(comp)
    return removed


def remove_small_lakes(
    tile_map: TileMap,
    max_size: int = 4,
    fill: TerrainType = TerrainType.PLAINS,
) -> int:
    """把 size <= max_size 且不接地圖邊界的水體填成 fill 地形。回傳被填的格數。

    「接地圖邊界」的水體一般是大海被切掉的一角，不算內陸湖，不會被填。
    """
    if max_size < 1:
        return 0
    h_map = tile_map.height
    w_map = tile_map.width
    filled = 0
    for comp in find_components(tile_map, is_water):
        if len(comp) > max_size:
            continue
        on_edge = any(
            c.x == 0 or c.x == w_map - 1 or c.y == 0 or c.y == h_map - 1
            for c in comp
        )
        if on_edge:
            continue
        for c in comp:
            tile_map.set_terrain(c, fill)
        filled += len(comp)
    return filled


def relabel_coast(tile_map: TileMap, coast_depth: int = 1) -> None:
    """先把所有 COAST 還原為 OCEAN，再重跑 coast_depth 圈擴張。"""
    for _, tile in tile_map:
        if tile.terrain == TerrainType.COAST:
            tile.terrain = TerrainType.OCEAN
    expand_coast(tile_map, coast_depth)


def post_process(
    tile_map: TileMap,
    island_min_size: int = 3,
    lake_max_size: int = 4,
    coast_depth: int = 1,
    lake_fill: TerrainType = TerrainType.PLAINS,
) -> dict[str, int]:
    """跑完 Phase 4，回傳 {'islands_removed': N, 'lakes_filled': N}。

    順序固定：清島 → 填湖 → 重標 COAST。
    """
    islands_removed = remove_small_islands(tile_map, island_min_size)
    lakes_filled = remove_small_lakes(tile_map, lake_max_size, lake_fill)
    relabel_coast(tile_map, coast_depth)
    return {
        "islands_removed": islands_removed,
        "lakes_filled": lakes_filled,
    }
