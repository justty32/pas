"""地圖容器：以 2D array 儲存 Tile 的平行四邊形地圖。

設計理念：對齊未來 C++ 移植，內部走 `self._rows[r][q]` 的 2D array，
不依賴 hash map 索引格子。座標範圍 q ∈ [0, width)、r ∈ [0, height)。

對齊 analysis/unciv/tutorial/cpp_hex_map_structure.md 第 75-106 行的 TileMap 設計。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterator

from .hex import Hex


class TerrainType(IntEnum):
    # 排序刻意把水（OCEAN/COAST）放最前面，可以用 `terrain <= COAST` 快速判水
    # 用 IntEnum 是為了 C++ 移植時對應 enum class，也方便序列化
    OCEAN = 0
    COAST = 1
    PLAINS = 2
    GRASSLAND = 3
    DESERT = 4
    TUNDRA = 5
    SNOW = 6
    FOREST = 7
    HILL = 8
    MOUNTAIN = 9


class Hilliness(IntEnum):
    """地勢起伏 5 級。對齊 projects/rimworld/.../Hilliness.cs。

    跟 TerrainType 是兩個獨立軸：例如「丘陵森林」= terrain=FOREST + hilliness=SMALL_HILLS。
    OCEAN/COAST 通常 hilliness=UNDEFINED 或 FLAT。
    """
    UNDEFINED = 0
    FLAT = 1
    SMALL_HILLS = 2
    LARGE_HILLS = 3
    MOUNTAINOUS = 4
    IMPASSABLE = 5


# 每地形的基礎移動成本。math.inf 表示不可通行。
# 給未來 A* 尋路用；要改規則改這裡，不必改 Tile 結構。
TERRAIN_COST: dict[TerrainType, float] = {
    TerrainType.OCEAN: math.inf,
    TerrainType.COAST: math.inf,
    TerrainType.PLAINS: 1.0,
    TerrainType.GRASSLAND: 1.0,
    TerrainType.DESERT: 1.5,
    TerrainType.TUNDRA: 1.0,
    TerrainType.SNOW: 2.0,
    TerrainType.FOREST: 2.0,
    TerrainType.HILL: 2.0,
    TerrainType.MOUNTAIN: math.inf,
}


def terrain_cost(terrain: TerrainType) -> float:
    return TERRAIN_COST[terrain]


def is_passable(terrain: TerrainType) -> bool:
    return math.isfinite(TERRAIN_COST[terrain])


@dataclass(slots=True)
class Tile:
    terrain: TerrainType = TerrainType.PLAINS
    # rivers：3 × 8-bit 流量打包進一個 int。
    # bits 0-7   = DIRECTIONS[0] (E)  的流量 (0~255)
    # bits 8-15  = DIRECTIONS[1] (NE) 的流量
    # bits 16-23 = DIRECTIONS[2] (NW) 的流量
    # 反向 (W/SW/SE) 由鄰居儲存，避免一條邊被兩個 tile 重複記錄。
    # 流量 0 表示無河流；>0 表示有河流且代表匯流量。
    # 查詢設定請走 rivers.has_river_edge / get/set_river_strength / add_river_flow，自動找到正確的 owner。
    # C++ 移植時對應 uint32_t（其中只用 24 bit）。
    rivers: int = 0
    # hilliness：5 級地勢，跟 terrain 獨立。對齊 RimWorld Tile.hilliness。
    # 由 generation.climate 階段填入；UNDEFINED 表示尚未計算。
    hilliness: Hilliness = Hilliness.UNDEFINED
    # feature_id：所屬命名大區域（WorldFeatures 索引）。-1 表示不屬於任何 feature。
    # 對齊 RimWorld Tile.feature（reference），但我們存 int id 以維持 dataclass slot 效能。
    feature_id: int = -1


class TileMap:
    """軸向座標 (q, r) 的平行四邊形地圖；2D array 儲存。

    features 屬性：本地圖跑過 features.apply_features() 後的命名大區域容器（WorldFeatures）。
    沒跑時為 None。掛在這裡方便 visualize / UI 直接從 tile_map 拿。
    """

    __slots__ = ("width", "height", "_rows", "features")

    def __init__(self, width: int, height: int, default_terrain: TerrainType = TerrainType.PLAINS):
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be > 0, got ({width}, {height})")
        self.width = width
        self.height = height
        # 儲存順序刻意 [r][q]（先 row 再 column），讓同一列的格子在記憶體連續，
        # 符合大多數遍歷模式（for r: for q），快取友善。C++ 版會用 std::vector<Tile> 線性陣列。
        self._rows: list[list[Tile]] = [
            [Tile(default_terrain) for _ in range(width)] for _ in range(height)
        ]
        # features 故意在這裡初始化而非從 .features import WorldFeatures，避免循環 import
        self.features = None

    def in_bounds(self, h: Hex) -> bool:
        return 0 <= h.q < self.width and 0 <= h.r < self.height

    def get(self, h: Hex) -> Tile | None:
        if not self.in_bounds(h):
            return None
        return self._rows[h.r][h.q]

    def set(self, h: Hex, tile: Tile) -> None:
        if not self.in_bounds(h):
            raise IndexError(f"Hex({h.q}, {h.r}) out of bounds for {self.width}x{self.height}")
        self._rows[h.r][h.q] = tile

    def set_terrain(self, h: Hex, terrain: TerrainType) -> None:
        if not self.in_bounds(h):
            raise IndexError(f"Hex({h.q}, {h.r}) out of bounds for {self.width}x{self.height}")
        self._rows[h.r][h.q].terrain = terrain

    def neighbors(self, h: Hex) -> list[Hex]:
        """h 的鄰居中位於地圖範圍內者（角落格只會回 2~3 個）。"""
        return [n for n in h.neighbors() if self.in_bounds(n)]

    def passable_neighbors(self, h: Hex) -> list[Hex]:
        """neighbors() 再過濾掉不可通行地形；給尋路用。"""
        out: list[Hex] = []
        for n in h.neighbors():
            if self.in_bounds(n) and is_passable(self._rows[n.r][n.q].terrain):
                out.append(n)
        return out

    def all_coords(self) -> Iterator[Hex]:
        for r in range(self.height):
            for q in range(self.width):
                yield Hex(q, r)

    def __iter__(self) -> Iterator[tuple[Hex, Tile]]:
        for r in range(self.height):
            for q in range(self.width):
                yield Hex(q, r), self._rows[r][q]

    def __len__(self) -> int:
        return self.width * self.height

    def fill(self, terrain: TerrainType) -> None:
        """整片重設地形。給地圖生成的初始階段用。"""
        for row in self._rows:
            for tile in row:
                tile.terrain = terrain
