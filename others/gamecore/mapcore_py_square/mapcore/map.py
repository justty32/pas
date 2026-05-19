"""地圖容器：以 2D array 儲存 Tile 的矩形方格地圖。

對應 mapcore_py/mapcore/map.py，但用 (x, y) 直角座標、4 鄰居拓樸。
座標範圍 x ∈ [0, width)、y ∈ [0, height)；儲存順序 self._rows[y][x] 讓同一列在記憶體連續。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterator

from .grid import Coord
from .terrain import DEFAULT_REGISTRY


class TerrainType(IntEnum):
    # id 與 mapcore_py hex 版完全對齊（OCEAN=0..LAKE=10），這樣兩個套件可以共用同一份地形定義。
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
    LAKE = 10


class Hilliness(IntEnum):
    """地勢起伏 5 級。與 terrain 是獨立軸。"""
    UNDEFINED = 0
    FLAT = 1
    SMALL_HILLS = 2
    LARGE_HILLS = 3
    MOUNTAINOUS = 4
    IMPASSABLE = 5


def terrain_cost(terrain_id: int) -> float:
    return DEFAULT_REGISTRY.move_cost(terrain_id)


def is_passable(terrain_id: int) -> bool:
    return DEFAULT_REGISTRY.is_passable(terrain_id)


@dataclass(slots=True)
class Tile:
    terrain: int = TerrainType.PLAINS
    # hilliness 5 級；保留欄位讓後續 climate phase 可以填入，core only 階段預設 UNDEFINED。
    hilliness: Hilliness = Hilliness.UNDEFINED
    # feature_id：所屬命名大區域。core only 階段不會被填入，預設 -1。
    feature_id: int = -1
    # water_depth：水體深度，由 classify phase 填入；core only 階段保持 0.0。
    water_depth: float = 0.0
    # rivers：壓縮儲存 2 條邊的河流強度（8-bit each）。
    # slot 0 = E 邊 (direction 0)、slot 1 = N 邊 (direction 1)。
    # W/S 兩條邊由鄰居存。詳見 mapcore.rivers._edge_owner。
    rivers: int = 0


class TileMap:
    """直角座標 (x, y) 的矩形地圖；2D array 儲存。"""

    __slots__ = ("width", "height", "_rows", "features")

    def __init__(self, width: int, height: int, default_terrain: TerrainType = TerrainType.PLAINS):
        if width <= 0 or height <= 0:
            raise ValueError(f"width and height must be > 0, got ({width}, {height})")
        self.width = width
        self.height = height
        # [y][x] 順序：對應 screen-space（y 向下）、跟 C++ std::vector<Tile> + index = y*width + x 對齊
        self._rows: list[list[Tile]] = [
            [Tile(default_terrain) for _ in range(width)] for _ in range(height)
        ]
        self.features = None

    def in_bounds(self, c: Coord) -> bool:
        return 0 <= c.x < self.width and 0 <= c.y < self.height

    def get(self, c: Coord) -> Tile | None:
        if not self.in_bounds(c):
            return None
        return self._rows[c.y][c.x]

    def set(self, c: Coord, tile: Tile) -> None:
        if not self.in_bounds(c):
            raise IndexError(f"Coord({c.x}, {c.y}) out of bounds for {self.width}x{self.height}")
        self._rows[c.y][c.x] = tile

    def set_terrain(self, c: Coord, terrain: int) -> None:
        if not self.in_bounds(c):
            raise IndexError(f"Coord({c.x}, {c.y}) out of bounds for {self.width}x{self.height}")
        self._rows[c.y][c.x].terrain = terrain

    def neighbors(self, c: Coord) -> list[Coord]:
        """c 的 4 鄰居中位於地圖範圍內者（邊格 3 個、角格 2 個）。"""
        return [n for n in c.neighbors() if self.in_bounds(n)]

    def passable_neighbors(self, c: Coord) -> list[Coord]:
        out: list[Coord] = []
        for n in c.neighbors():
            if self.in_bounds(n) and is_passable(self._rows[n.y][n.x].terrain):
                out.append(n)
        return out

    def all_coords(self) -> Iterator[Coord]:
        for y in range(self.height):
            for x in range(self.width):
                yield Coord(x, y)

    def __iter__(self) -> Iterator[tuple[Coord, Tile]]:
        for y in range(self.height):
            for x in range(self.width):
                yield Coord(x, y), self._rows[y][x]

    def __len__(self) -> int:
        return self.width * self.height

    def fill(self, terrain: int) -> None:
        for row in self._rows:
            for tile in row:
                tile.terrain = terrain
