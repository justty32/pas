"""WorldFeature 命名大區域系統。

對齊 projects/rimworld/RimWorld.Planet/：
  WorldFeature.cs (命名實例的資料結構)
  WorldGenStep_Features.cs (跑所有 FeatureWorker)
  FeatureWorker_FloodFill.cs / FeatureWorker_Cluster.cs (基礎演算法)
  FeatureWorker_Biome.cs / FeatureWorker_MountainRange.cs / FeatureWorker_Island.cs

每個 Feature 對應一塊連通的 tile 集合，有一個命名標籤；玩家在地圖上看到
「Atlantic Ocean」「Sahara」這類標籤就是 Feature。

對應到我們：
- WorldFeature dataclass：id / type / name / tiles / center / size
- WorldFeatures 容器：用 list 索引（feature_id 直接 = list index）
- FeatureWorker 抽象基類 + 內建子類（Ocean / MountainRange / BiomeRegion / Island）

每個 tile 透過 Tile.feature_id (int) 反查 features[id]；-1 = 不屬於任何 feature。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

from .hex import Hex
from .map import Hilliness, TerrainType, Tile, TileMap


@dataclass(slots=True)
class WorldFeature:
    """一個命名大區域。

    對齊 projects/rimworld/.../WorldFeature.cs:8-67：
    - id：與 Tile.feature_id 對應
    - feature_type：分類字串，例如 "Ocean" / "MountainRange" / "BiomeRegion:FOREST"
    - name：顯示用名稱（暫時用 "<type> #N" placeholder，未來可接 grammar）
    - tiles：屬於此 feature 的所有 hex
    - center：tiles 的 axial 重心，供地圖標籤定位
    - size：tiles 數，方便排序與 UI 字級
    """
    id: int
    feature_type: str
    name: str
    tiles: list[Hex]
    center: Hex
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
        tiles: list[Hex],
        center: Hex,
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


def _centroid(tiles: list[Hex]) -> Hex:
    """axial 平均後取最近 integer hex。標籤定位用，不需精確。

    凹形 feature（如 L 形山脈、環形海岸）的數學重心可能落在 feature 外面，
    導致地圖上看到標籤飄在無關區域，所以 fallback 用「離平均最近的成員」確保標籤一定在 feature 上。
    曼哈頓距離已足夠（標籤定位不需 hex distance 那麼精確）。
    """
    if not tiles:
        return Hex(0, 0)
    q_avg = sum(h.q for h in tiles) / len(tiles)
    r_avg = sum(h.r for h in tiles) / len(tiles)
    cand = Hex(round(q_avg), round(r_avg))
    if cand in tiles:
        return cand
    best = tiles[0]
    best_d = abs(best.q - q_avg) + abs(best.r - r_avg)
    for t in tiles[1:]:
        d = abs(t.q - q_avg) + abs(t.r - r_avg)
        if d < best_d:
            best = t
            best_d = d
    return best


class FeatureWorker(ABC):
    """抽象基類：對應 RimWorld FeatureWorker。

    子類覆寫 is_member 決定 tile 是否屬於這個 worker 的某個 feature；
    generate_where_appropriate 對未被佔用的 tile 做 flood-fill 收集連通分量。
    """

    feature_type: str = "Unknown"

    def __init__(self, name_prefix: str, min_size: int = 5, max_size: int = 10_000) -> None:
        self.name_prefix = name_prefix
        self.min_size = min_size
        self.max_size = max_size

    @abstractmethod
    def is_member(self, tile_map: TileMap, h: Hex, tile: Tile) -> bool:
        """這個 tile 是否可加入本 worker 主導的 feature。"""

    def generate_where_appropriate(
        self,
        tile_map: TileMap,
        features: WorldFeatures,
    ) -> int:
        """對齊 FeatureWorker_FloodFill.cs:43-159 的 GenerateWhereAppropriate。

        Flood-fill 找連通分量，size 落在 [min_size, max_size] 才註冊為 feature。
        已被其他 feature 佔用（tile.feature_id >= 0）的 tile 直接跳過。
        """
        W, H = tile_map.width, tile_map.height
        # visited 跟 feature_id 是雙重保護：visited 是本 worker 自己的掃描狀態，
        # feature_id >= 0 是「被前面跑過的 worker 搶走了」。後者讓 worker 順序變成優先序
        visited = [[False] * W for _ in range(H)]
        produced = 0
        counter = 1
        for h, tile in tile_map:
            if visited[h.r][h.q]:
                continue
            if tile.feature_id >= 0:
                visited[h.r][h.q] = True
                continue
            if not self.is_member(tile_map, h, tile):
                visited[h.r][h.q] = True
                continue
            group = self._flood_fill(tile_map, h, visited)
            # min_size 過濾掉太小的雜訊（孤立 1-2 格），max_size 防止「整個大陸算一塊森林」
            # 不符的 group 直接丟棄，這些 tile 仍標 visited 但 feature_id 保持 -1，後續 worker 可能會接收
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
        root: Hex,
        visited: list[list[bool]],
    ) -> list[Hex]:
        group: list[Hex] = []
        stack: list[Hex] = [root]
        while stack:
            cur = stack.pop()
            if not tile_map.in_bounds(cur):
                continue
            if visited[cur.r][cur.q]:
                continue
            t = tile_map.get(cur)
            if t.feature_id >= 0:
                visited[cur.r][cur.q] = True
                continue
            if not self.is_member(tile_map, cur, t):
                visited[cur.r][cur.q] = True
                continue
            visited[cur.r][cur.q] = True
            group.append(cur)
            for nb in cur.neighbors():
                stack.append(nb)
        return group


# ---------------------------------------------------------------------------
# 內建 Worker 子類
# ---------------------------------------------------------------------------

_WATER = (TerrainType.OCEAN, TerrainType.COAST)


class FeatureWorker_Ocean(FeatureWorker):
    """對齊 FeatureWorker_OuterOcean：找大塊海洋（含 COAST）。"""
    feature_type = "Ocean"

    def is_member(self, tile_map: TileMap, h: Hex, tile: Tile) -> bool:
        return tile.terrain in _WATER


class FeatureWorker_MountainRange(FeatureWorker):
    """對齊 FeatureWorker_MountainRange.cs：hilliness 起伏的連通陸塊。

    收 LARGE_HILLS 以上（含 MOUNTAINOUS / IMPASSABLE）。
    """
    feature_type = "MountainRange"

    def is_member(self, tile_map: TileMap, h: Hex, tile: Tile) -> bool:
        if tile.terrain in _WATER:
            return False
        return tile.hilliness >= Hilliness.LARGE_HILLS


class FeatureWorker_BiomeRegion(FeatureWorker):
    """對齊 FeatureWorker_Biome.cs：找特定 terrain 的連通分量。"""
    feature_type = "BiomeRegion"

    def __init__(
        self,
        target_terrain: TerrainType,
        name_prefix: str,
        min_size: int = 8,
        max_size: int = 10_000,
    ) -> None:
        super().__init__(name_prefix, min_size, max_size)
        self.target_terrain = target_terrain
        # 用 terrain 名稱當後綴，方便 UI 過濾
        self.feature_type = f"BiomeRegion:{target_terrain.name}"

    def is_member(self, tile_map: TileMap, h: Hex, tile: Tile) -> bool:
        return tile.terrain == self.target_terrain


class FeatureWorker_Island(FeatureWorker):
    """對齊 FeatureWorker_Island.cs：相對小的陸塊（含 HILL / MOUNTAIN 等所有陸地）。

    跟 MountainRange 不同，這裡接受所有陸地 terrain，但用 max_size 限制大小，
    讓真正的「大陸」不會被誤標成島。
    """
    feature_type = "Island"

    def is_member(self, tile_map: TileMap, h: Hex, tile: Tile) -> bool:
        return tile.terrain not in _WATER


def default_workers() -> list[FeatureWorker]:
    """預設工作清單；越「特殊」的 feature 排越前面（先 claim tiles）。

    name_prefix 統一用英文，避免 pygame 預設字體缺 CJK glyph 變問號；
    要中文時呼叫端可以自行替換 workers 清單。
    """
    return [
        FeatureWorker_Ocean("Ocean", min_size=20),
        FeatureWorker_MountainRange("Range", min_size=5),
        FeatureWorker_BiomeRegion(TerrainType.SNOW, "Icecap", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.TUNDRA, "Tundra", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.DESERT, "Desert", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=8),
        FeatureWorker_BiomeRegion(TerrainType.GRASSLAND, "Plains", min_size=8),
        FeatureWorker_Island("Island", min_size=3, max_size=40),
    ]


def apply_features(
    tile_map: TileMap,
    workers: Optional[list[FeatureWorker]] = None,
) -> WorldFeatures:
    """跑所有 worker 在 tile_map 上產出 features。

    對齊 WorldGenStep_Features.cs:11-26 的 GenerateFresh：按 worker 順序處理，
    後跑的 worker 不能搶已被先前 worker 佔用的 tile（透過 Tile.feature_id 互斥）。
    """
    if workers is None:
        workers = default_workers()
    # 重置 feature_id（避免重複呼叫累積殘留）
    for _, tile in tile_map:
        tile.feature_id = -1
    features = WorldFeatures()
    for worker in workers:
        worker.generate_where_appropriate(tile_map, features)
    return features
