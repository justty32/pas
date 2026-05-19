"""WorldFeature 命名大區域系統（方格 4 鄰居版）。

對齊 mapcore_py 的 hex 版 features.py（同樣參考 RimWorld FeatureWorker_*）；
本檔僅把 Hex(q,r) 換成 Coord(x,y)、6 鄰居換成 4 鄰居。

每個 Feature 對應一塊連通的 tile 集合，有一個命名標籤；玩家在地圖上看到
「Atlantic Ocean」「Sahara」這類標籤就是 Feature。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional

from .grid import Coord
from .map import Hilliness, TerrainType, Tile, TileMap
from .terrain import DEFAULT_REGISTRY


@dataclass(slots=True)
class WorldFeature:
    """一個命名大區域。對齊 RW WorldFeature.cs:8-67。"""
    id: int
    feature_type: str
    name: str
    tiles: list[Coord]
    center: Coord
    size: int


class WorldFeatures:
    """所有 features 的容器；用 list 順序索引（順序 == Tile.feature_id）。"""

    __slots__ = ("_features",)

    def __init__(self) -> None:
        self._features: list[WorldFeature] = []

    def add(
        self,
        feature_type: str,
        name: str,
        tiles: list[Coord],
        center: Coord,
    ) -> WorldFeature:
        f = WorldFeature(
            id=len(self._features),
            feature_type=feature_type,
            name=name,
            tiles=list(tiles),
            center=center,
            size=len(tiles),
        )
        self._features.append(f)
        return f

    def get(self, feature_id: int) -> Optional[WorldFeature]:
        if 0 <= feature_id < len(self._features):
            return self._features[feature_id]
        return None

    def __iter__(self) -> Iterator[WorldFeature]:
        return iter(self._features)

    def __len__(self) -> int:
        return len(self._features)


def _centroid(tiles: list[Coord]) -> Coord:
    """平均後取最近 integer Coord。標籤定位用，不需精確。

    凹形 feature 的數學重心可能落在 feature 外面，所以 fallback 用「離平均最近的成員」。
    """
    if not tiles:
        return Coord(0, 0)
    x_avg = sum(c.x for c in tiles) / len(tiles)
    y_avg = sum(c.y for c in tiles) / len(tiles)
    cand = Coord(round(x_avg), round(y_avg))
    if cand in tiles:
        return cand
    best = tiles[0]
    best_d = abs(best.x - x_avg) + abs(best.y - y_avg)
    for t in tiles[1:]:
        d = abs(t.x - x_avg) + abs(t.y - y_avg)
        if d < best_d:
            best = t
            best_d = d
    return best


class FeatureWorker(ABC):
    """抽象基類：對應 RimWorld FeatureWorker。"""

    feature_type: str = "Unknown"

    def __init__(self, name_prefix: str, min_size: int = 5, max_size: int = 10_000) -> None:
        self.name_prefix = name_prefix
        self.min_size = min_size
        self.max_size = max_size

    @abstractmethod
    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        """這個 tile 是否可加入本 worker 主導的 feature。"""

    def generate_where_appropriate(
        self,
        tile_map: TileMap,
        features: WorldFeatures,
    ) -> int:
        """對齊 RW FeatureWorker_FloodFill.cs:43-159 GenerateWhereAppropriate。"""
        W, H = tile_map.width, tile_map.height
        # visited 與 feature_id 雙重保護：visited 是本 worker 自己的掃描狀態，
        # feature_id >= 0 是「被前面跑過的 worker 搶走了」
        visited = [[False] * W for _ in range(H)]
        produced = 0
        counter = 1
        for c, tile in tile_map:
            if visited[c.y][c.x]:
                continue
            if tile.feature_id >= 0:
                visited[c.y][c.x] = True
                continue
            if not self.is_member(tile_map, c, tile):
                visited[c.y][c.x] = True
                continue
            group = self._flood_fill(tile_map, c, visited)
            if len(group) < self.min_size or len(group) > self.max_size:
                continue
            name = f"{self.name_prefix} #{counter}"
            center = _centroid(group)
            f = features.add(self.feature_type, name, group, center)
            for g in group:
                tile_map.get(g).feature_id = f.id
            produced += 1
            counter += 1
        return produced

    def _flood_fill(
        self,
        tile_map: TileMap,
        root: Coord,
        visited: list[list[bool]],
    ) -> list[Coord]:
        group: list[Coord] = []
        stack: list[Coord] = [root]
        while stack:
            cur = stack.pop()
            if not tile_map.in_bounds(cur):
                continue
            if visited[cur.y][cur.x]:
                continue
            t = tile_map.get(cur)
            if t.feature_id >= 0:
                visited[cur.y][cur.x] = True
                continue
            if not self.is_member(tile_map, cur, t):
                visited[cur.y][cur.x] = True
                continue
            visited[cur.y][cur.x] = True
            group.append(cur)
            for nb in cur.neighbors():
                stack.append(nb)
        return group


# ---------------------------------------------------------------------------
# 內建 Worker 子類
# ---------------------------------------------------------------------------

class FeatureWorker_Ocean(FeatureWorker):
    """大塊海洋 (OCEAN + COAST)。"""
    feature_type = "Ocean"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return tile.terrain == TerrainType.OCEAN or tile.terrain == TerrainType.COAST


class FeatureWorker_Lake(FeatureWorker):
    """內陸湖泊（terrain == LAKE）。必須排在 Ocean 之前。"""
    feature_type = "Lake"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return tile.terrain == TerrainType.LAKE


class FeatureWorker_Coast(FeatureWorker):
    """海岸線（terrain == COAST）。排在 Ocean 之前可讓海岸帶獨立命名。"""
    feature_type = "Coast"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return tile.terrain == TerrainType.COAST


class FeatureWorker_Icecap(FeatureWorker):
    """極地冰原：限定地圖南北極帶的 SNOW 連通分量。"""
    feature_type = "Icecap"

    def __init__(
        self,
        name_prefix: str,
        polar_band: float = 0.15,
        min_size: int = 8,
        max_size: int = 10_000,
    ) -> None:
        super().__init__(name_prefix, min_size, max_size)
        self.polar_band = polar_band

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        if tile.terrain != TerrainType.SNOW:
            return False
        ratio = c.y / max(tile_map.height - 1, 1)
        return ratio < self.polar_band or ratio > 1.0 - self.polar_band


class FeatureWorker_MountainRange(FeatureWorker):
    """hilliness 起伏的連通陸塊（LARGE_HILLS 以上）。"""
    feature_type = "MountainRange"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        if DEFAULT_REGISTRY.is_water(tile.terrain):
            return False
        return tile.hilliness >= Hilliness.LARGE_HILLS


class FeatureWorker_BiomeRegion(FeatureWorker):
    """特定 terrain id 的連通分量。"""
    feature_type = "BiomeRegion"

    def __init__(
        self,
        target_terrain: int,
        name_prefix: str,
        min_size: int = 8,
        max_size: int = 10_000,
    ) -> None:
        super().__init__(name_prefix, min_size, max_size)
        self.target_terrain = target_terrain
        terrain_name = DEFAULT_REGISTRY.get(target_terrain).name
        self.feature_type = f"BiomeRegion:{terrain_name}"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return tile.terrain == self.target_terrain


class FeatureWorker_Island(FeatureWorker):
    """相對小的陸塊（含 HILL/MOUNTAIN 等所有陸地），用 max_size 限制大小。"""
    feature_type = "Island"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return not DEFAULT_REGISTRY.is_water(tile.terrain)


class FeatureWorker_Continent(FeatureWorker):
    """大陸：跨 biome 的連通陸塊標籤。不寫 tile.feature_id，與其他 worker 重疊共存。"""
    feature_type = "Continent"

    def is_member(self, tile_map: TileMap, c: Coord, tile: Tile) -> bool:
        return not DEFAULT_REGISTRY.is_water(tile.terrain)

    def generate_where_appropriate(
        self,
        tile_map: TileMap,
        features: WorldFeatures,
    ) -> int:
        W, H = tile_map.width, tile_map.height
        visited = [[False] * W for _ in range(H)]
        produced = 0
        counter = 1
        for c, tile in tile_map:
            if visited[c.y][c.x]:
                continue
            if not self.is_member(tile_map, c, tile):
                visited[c.y][c.x] = True
                continue
            group = self._flood_fill_landmass(tile_map, c, visited)
            if len(group) < self.min_size or len(group) > self.max_size:
                continue
            name = f"{self.name_prefix} #{counter}"
            center = _centroid(group)
            features.add(self.feature_type, name, group, center)
            # 刻意不寫 tile.feature_id，保留給其他 worker 用
            produced += 1
            counter += 1
        return produced

    def _flood_fill_landmass(
        self,
        tile_map: TileMap,
        root: Coord,
        visited: list[list[bool]],
    ) -> list[Coord]:
        """跟基類 _flood_fill 唯一差異：不檢查 tile.feature_id（允許重疊既有 feature）。"""
        group: list[Coord] = []
        stack: list[Coord] = [root]
        while stack:
            cur = stack.pop()
            if not tile_map.in_bounds(cur):
                continue
            if visited[cur.y][cur.x]:
                continue
            t = tile_map.get(cur)
            if not self.is_member(tile_map, cur, t):
                visited[cur.y][cur.x] = True
                continue
            visited[cur.y][cur.x] = True
            group.append(cur)
            for nb in cur.neighbors():
                stack.append(nb)
        return group


def default_workers() -> list[FeatureWorker]:
    """預設工作清單；越「特殊」的 feature 排越前面（先 claim tiles）。

    順序：
      水域：Lake (LAKE) → Coast (COAST) → Ocean (剩下 OCEAN)
      陸地特殊：MountainRange → Icecap → BiomeRegion×5
      剩餘：Island
      最後：Continent (不搶 tile，純標籤層)
    """
    return [
        FeatureWorker_Lake("Lake", min_size=2),
        FeatureWorker_Coast("Coast", min_size=8),
        FeatureWorker_Ocean("Ocean", min_size=20),
        FeatureWorker_MountainRange("Range", min_size=5),
        FeatureWorker_Icecap("Icecap", polar_band=0.15, min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.SNOW, "Snowfield", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.TUNDRA, "Tundra", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.DESERT, "Desert", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.GRASSLAND, "Plains", min_size=8),
        FeatureWorker_Island("Island", min_size=3, max_size=40),
        FeatureWorker_Continent("Continent", min_size=100),
    ]


def apply_features(
    tile_map: TileMap,
    workers: Optional[list[FeatureWorker]] = None,
) -> WorldFeatures:
    """跑所有 worker 在 tile_map 上產出 features。

    對齊 RW WorldGenStep_Features.cs:11-26 GenerateFresh：按 worker 順序處理，
    後跑的 worker 不能搶已被先前 worker 佔用的 tile（透過 Tile.feature_id 互斥）。
    """
    if workers is None:
        workers = default_workers()
    for _, tile in tile_map:
        tile.feature_id = -1
    features = WorldFeatures()
    for worker in workers:
        worker.generate_where_appropriate(tile_map, features)
    return features
