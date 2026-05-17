"""河流：拓撲、流量與生成。

河流走 hex 邊，不走 tile 中心。每條邊只被「兩個共享 tile 中的一個」儲存，避免重複：
- DIRECTIONS[0,1,2] (E / NE / NW) 由 tile 本身儲存 (Tile.rivers 的 8-bit slot 0/1/2)
- DIRECTIONS[3,4,5] (W / SW / SE) 由鄰居儲存

每條邊存「流量」(0~255)：0 = 無河，>0 = 流量值。多源頭匯入同條主流時，
generate_rivers 會用 add_river_flow 在共用邊上累加，讓主流流量自然變大。

對外 API：
- has_river_edge(map, h, d) -> bool
- get_river_strength(map, h, d) -> int
- set_river_strength(map, h, d, n) / set_river_edge(map, h, d, bool)
- add_river_flow(map, h, d, amount=1)
- iter_river_edges(map) -> yields (Hex, direction, strength)

對齊 analysis/unciv/tutorial/cpp_hex_map_structure.md 第 124-128 行：
「每個 Tile 只負責定義它『下方』、『右下方』、『左下方』的三條邊。」
"""

from __future__ import annotations

import random
from typing import Iterator, Optional

from .hex import DIRECTIONS, Hex
from .map import TerrainType, TileMap

WATER = (TerrainType.OCEAN, TerrainType.COAST)

# 渲染用：direction d 的邊由 hex 上哪兩個 corner 連起來（pointy-top，
# corners 從 angle -30° 開始順時針：0=右上, 1=右下, 2=下, 3=左下, 4=左上, 5=上）
EDGE_CORNERS: tuple[tuple[int, int], ...] = (
    (0, 1),  # d=0 E  右邊
    (5, 0),  # d=1 NE 右上邊
    (4, 5),  # d=2 NW 左上邊
    (3, 4),  # d=3 W  左邊
    (2, 3),  # d=4 SW 左下邊
    (1, 2),  # d=5 SE 右下邊
)

RIVER_BITS = 8
RIVER_MASK = (1 << RIVER_BITS) - 1  # 0xFF
RIVER_MAX_STRENGTH = RIVER_MASK     # 255


def _edge_owner(h: Hex, direction: int) -> tuple[Hex, int]:
    """回傳 (owner_hex, slot_index)；direction < 3 自己擁有，其餘由鄰居擁有。"""
    if 0 <= direction < 3:
        return h, direction
    if 3 <= direction < 6:
        return h + DIRECTIONS[direction], direction - 3
    raise ValueError(f"direction must be in [0, 6), got {direction}")


def _read_slot(rivers: int, slot: int) -> int:
    return (rivers >> (slot * RIVER_BITS)) & RIVER_MASK


def _write_slot(rivers: int, slot: int, value: int) -> int:
    value = max(0, min(RIVER_MAX_STRENGTH, value))
    clear = ~(RIVER_MASK << (slot * RIVER_BITS))
    return (rivers & clear) | (value << (slot * RIVER_BITS))


def get_river_strength(tile_map: TileMap, h: Hex, direction: int) -> int:
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return 0
    return _read_slot(tile.rivers, slot)


def set_river_strength(tile_map: TileMap, h: Hex, direction: int, strength: int) -> None:
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    tile.rivers = _write_slot(tile.rivers, slot, strength)


def add_river_flow(tile_map: TileMap, h: Hex, direction: int, amount: int = 1) -> None:
    """在指定邊上累加流量；上限 RIVER_MAX_STRENGTH (255)。"""
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    cur = _read_slot(tile.rivers, slot)
    tile.rivers = _write_slot(tile.rivers, slot, cur + amount)


def has_river_edge(tile_map: TileMap, h: Hex, direction: int) -> bool:
    return get_river_strength(tile_map, h, direction) > 0


def set_river_edge(tile_map: TileMap, h: Hex, direction: int, value: bool = True) -> None:
    """設邊上有/無河流（強度 1 或 0）。要設特定流量請用 set_river_strength。"""
    set_river_strength(tile_map, h, direction, 1 if value else 0)


def iter_river_edges(tile_map: TileMap) -> Iterator[tuple[Hex, int, int]]:
    """yield 出地圖上所有有河流的 (origin_hex, direction, strength)。

    origin_hex 永遠是 owner，direction 永遠在 0..2。strength > 0。
    """
    for h, tile in tile_map:
        if not tile.rivers:
            continue
        for slot in range(3):
            s = _read_slot(tile.rivers, slot)
            if s > 0:
                yield h, slot, s


def _is_water(t: TerrainType) -> bool:
    return t in WATER


def generate_rivers(
    tile_map: TileMap,
    heightmap: list[list[float]],
    seed: Optional[int] = None,
    source_threshold: float = 0.6,
    source_density: float = 0.15,
    min_river_length: int = 2,
) -> int:
    """從高處取樣源頭，沿最陡下降走到水或局部低點。回傳成功標記的邊數。

    - source_threshold: 高於此高程的陸地才能當源頭
    - source_density:   候選源頭中實際取用的比例 (0~1)
    - min_river_length: 太短的河流會被回收（避免一格小山就出河）
    """
    if not 0.0 <= source_density <= 1.0:
        raise ValueError(f"source_density must be in [0, 1], got {source_density}")
    if min_river_length < 1:
        raise ValueError(f"min_river_length must be >= 1, got {min_river_length}")

    rng = random.Random(seed)
    candidates: list[Hex] = []
    for h, tile in tile_map:
        if _is_water(tile.terrain):
            continue
        if heightmap[h.r][h.q] >= source_threshold:
            candidates.append(h)

    total_edges = 0
    for src in candidates:
        if rng.random() >= source_density:
            continue
        edges = _trace_river(tile_map, heightmap, src, min_river_length)
        total_edges += edges
    return total_edges


def _trace_river(
    tile_map: TileMap,
    heightmap: list[list[float]],
    source: Hex,
    min_river_length: int,
) -> int:
    """從 source 沿最陡下降走；先收集邊，到水或無下坡時收手；長度不足則回滾。"""
    path_edges: list[tuple[Hex, int]] = []
    current = source
    cur_height = heightmap[current.r][current.q]

    while True:
        if _is_water(tile_map.get(current).terrain):
            break
        best_dir = -1
        best_height = cur_height  # 嚴格下降 → 不可能迴圈
        best_neighbor: Hex | None = None
        for d in range(6):
            n = current + DIRECTIONS[d]
            if not tile_map.in_bounds(n):
                continue
            nh = heightmap[n.r][n.q]
            if nh < best_height:
                best_height = nh
                best_dir = d
                best_neighbor = n
        if best_neighbor is None:
            break
        path_edges.append((current, best_dir))
        current = best_neighbor
        cur_height = best_height

    if len(path_edges) < min_river_length:
        return 0
    for h, d in path_edges:
        add_river_flow(tile_map, h, d, 1)
    return len(path_edges)
