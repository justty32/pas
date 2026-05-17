"""地圖後處理 (Phase 4)。

對既有 TileMap 做：
- 連通分量分析 (BFS)
- 清掉過小的陸地島嶼（淹成 OCEAN）
- 填掉「不接地圖邊界」的小水體（避免內陸有奇怪小洞）
- 清完後重新標記 COAST

走 2D visited 陣列，跟其他模組一致，不用 hash set。
"""

from __future__ import annotations

from typing import Callable

from ..hex import Hex
from ..map import TerrainType, TileMap
from .classify import expand_coast


WATER = (TerrainType.OCEAN, TerrainType.COAST)


def is_land(t: TerrainType) -> bool:
    return t not in WATER


def is_water(t: TerrainType) -> bool:
    return t in WATER


def find_components(
    tile_map: TileMap,
    predicate: Callable[[TerrainType], bool],
) -> list[list[Hex]]:
    """BFS 找出 predicate(terrain) 為真的格子組成的所有連通分量。"""
    h_map = tile_map.height
    w_map = tile_map.width
    visited = [[False] * w_map for _ in range(h_map)]
    components: list[list[Hex]] = []

    for r in range(h_map):
        for q in range(w_map):
            if visited[r][q]:
                continue
            # 不符 predicate 的格子也標 visited，避免後續重複檢查
            # 這讓函式對「兩種地形交錯」的地圖也是 O(N)
            if not predicate(tile_map.get(Hex(q, r)).terrain):
                visited[r][q] = True
                continue
            comp: list[Hex] = []
            stack = [Hex(q, r)]
            visited[r][q] = True
            # DFS（用 stack 而非 queue）：節省記憶體，順序對結果不影響
            while stack:
                h = stack.pop()
                comp.append(h)
                for n in tile_map.neighbors(h):
                    if visited[n.r][n.q]:
                        continue
                    if predicate(tile_map.get(n).terrain):
                        visited[n.r][n.q] = True
                        stack.append(n)
                    else:
                        # 邊界鄰居也標 visited，防止外層 for 又掃進來
                        visited[n.r][n.q] = True
            components.append(comp)
    return components


def remove_small_islands(tile_map: TileMap, min_size: int = 3) -> int:
    """把 size < min_size 的陸地連通分量整片淹成 OCEAN。回傳被淹的格數。"""
    if min_size <= 1:
        return 0
    removed = 0
    for comp in find_components(tile_map, is_land):
        if len(comp) < min_size:
            for h in comp:
                tile_map.set_terrain(h, TerrainType.OCEAN)
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
        # 「接邊界」是大海被地圖切掉一角的判斷依據：真正的內陸湖不會碰到 q=0/q=W-1/r=0/r=H-1
        # 沒這個檢查的話，地圖邊上一小塊海會被誤判成湖而填掉
        on_edge = any(
            h.q == 0 or h.q == w_map - 1 or h.r == 0 or h.r == h_map - 1
            for h in comp
        )
        if on_edge:
            continue
        for h in comp:
            tile_map.set_terrain(h, fill)
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
    清完島的格子是 OCEAN，可能會跟旁邊原本就是 OCEAN 的格子合併；接著填湖會把新形成的
    小水體（被陸地包圍的）填回去；最後重標 COAST 保證海岸線正確。
    """
    islands_removed = remove_small_islands(tile_map, island_min_size)
    lakes_filled = remove_small_lakes(tile_map, lake_max_size, lake_fill)
    relabel_coast(tile_map, coast_depth)
    return {
        "islands_removed": islands_removed,
        "lakes_filled": lakes_filled,
    }
