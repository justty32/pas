import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex
from mapcore.map import Hilliness, TerrainType, TileMap
from mapcore.features import (
    FeatureWorker_BiomeRegion,
    FeatureWorker_Island,
    FeatureWorker_MountainRange,
    FeatureWorker_Ocean,
    WorldFeatures,
    apply_features,
    default_workers,
)


def _set_block(tm: TileMap, q0: int, r0: int, w: int, h: int, terrain: TerrainType) -> None:
    for r in range(r0, r0 + h):
        for q in range(q0, q0 + w):
            tm.set_terrain(Hex(q, r), terrain)


class TestOceanWorker(unittest.TestCase):
    def test_picks_up_large_water_block(self):
        tm = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        # 右下 5x5 區塊變海
        _set_block(tm, 5, 5, 5, 5, TerrainType.OCEAN)
        features = WorldFeatures()
        worker = FeatureWorker_Ocean("Sea", min_size=10)
        worker.generate_where_appropriate(tm, features)
        # 25 格 >= min_size 10 → 應該產生一個 ocean feature
        self.assertEqual(len(features), 1)
        f = next(iter(features))
        self.assertEqual(f.feature_type, "Ocean")
        self.assertEqual(f.size, 25)

    def test_below_min_size_skipped(self):
        tm = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        _set_block(tm, 0, 0, 2, 2, TerrainType.OCEAN)  # 只有 4 格
        features = WorldFeatures()
        worker = FeatureWorker_Ocean("Sea", min_size=10)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 0)


class TestMountainRangeWorker(unittest.TestCase):
    def test_uses_hilliness_not_terrain(self):
        tm = TileMap(8, 8, default_terrain=TerrainType.PLAINS)
        # 在 (2,2)~(4,4) 設成 LARGE_HILLS
        for q in range(2, 5):
            for r in range(2, 5):
                t = tm.get(Hex(q, r))
                t.hilliness = Hilliness.LARGE_HILLS
        features = WorldFeatures()
        worker = FeatureWorker_MountainRange("Range", min_size=5)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 1)
        f = next(iter(features))
        self.assertEqual(f.size, 9)

    def test_ignores_water(self):
        tm = TileMap(6, 6, default_terrain=TerrainType.OCEAN)
        # 全是海，但 hilliness 給 LARGE_HILLS 也不該被收
        for q in range(6):
            for r in range(6):
                tm.get(Hex(q, r)).hilliness = Hilliness.LARGE_HILLS
        features = WorldFeatures()
        worker = FeatureWorker_MountainRange("Range", min_size=3)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 0)


class TestBiomeRegionWorker(unittest.TestCase):
    def test_finds_two_separate_regions(self):
        tm = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        # 兩塊不相連的森林
        _set_block(tm, 0, 0, 3, 3, TerrainType.FOREST)
        _set_block(tm, 6, 6, 3, 3, TerrainType.FOREST)
        features = WorldFeatures()
        worker = FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=5)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 2)
        for f in features:
            self.assertEqual(f.feature_type, "BiomeRegion:FOREST")
            self.assertEqual(f.size, 9)


class TestIslandWorker(unittest.TestCase):
    def test_max_size_filters_continent(self):
        # 一塊 50 格的大陸 → 不算 island；單獨一塊 5 格 → 算 island
        tm = TileMap(15, 15, default_terrain=TerrainType.OCEAN)
        _set_block(tm, 0, 0, 8, 7, TerrainType.PLAINS)   # 56 格 → 太大
        _set_block(tm, 12, 12, 2, 2, TerrainType.PLAINS) # 4 格 → < min
        _set_block(tm, 11, 0, 4, 2, TerrainType.PLAINS)  # 8 格 → 算島
        features = WorldFeatures()
        worker = FeatureWorker_Island("Island", min_size=5, max_size=20)
        worker.generate_where_appropriate(tm, features)
        # 應該只有 8 格那塊符合 [5, 20]
        self.assertEqual(len(features), 1)
        self.assertEqual(next(iter(features)).size, 8)


class TestApplyFeatures(unittest.TestCase):
    def test_workers_run_in_order_and_mutually_exclusive(self):
        # 一塊 forest 區，包含一個小 hilliness 山脈：MountainRange 先跑 → 搶走山的格子
        tm = TileMap(10, 10, default_terrain=TerrainType.FOREST)
        for q in range(2, 5):
            for r in range(2, 5):
                tm.get(Hex(q, r)).hilliness = Hilliness.LARGE_HILLS
        features = apply_features(
            tm,
            workers=[
                FeatureWorker_MountainRange("Range", min_size=5),
                FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=5),
            ],
        )
        # 應該有 1 個山脈 + 1 個森林（被山切割但仍 ≥ min_size）
        types = sorted(f.feature_type for f in features)
        self.assertIn("MountainRange", types)
        self.assertIn("BiomeRegion:FOREST", types)
        # 山的格子 feature_id 對應 MountainRange
        mountain_id = next(f.id for f in features if f.feature_type == "MountainRange")
        self.assertEqual(tm.get(Hex(3, 3)).feature_id, mountain_id)
        # 山以外的格子不應屬於山脈
        self.assertNotEqual(tm.get(Hex(0, 0)).feature_id, mountain_id)

    def test_reset_on_rerun(self):
        # 跑兩次 apply_features 不會累積殘留
        tm = TileMap(8, 8, default_terrain=TerrainType.OCEAN)
        f1 = apply_features(tm, workers=[FeatureWorker_Ocean("Sea", min_size=20)])
        f2 = apply_features(tm, workers=[FeatureWorker_Ocean("Sea", min_size=20)])
        # 兩次 features 數量應一致
        self.assertEqual(len(f1), len(f2))
        # tile.feature_id 對應第二次的 id（從 0 重新計）
        sample = tm.get(Hex(0, 0))
        self.assertEqual(sample.feature_id, 0)

    def test_default_workers_runs_on_realistic_map(self):
        tm = TileMap(15, 15, default_terrain=TerrainType.OCEAN)
        _set_block(tm, 2, 2, 11, 11, TerrainType.PLAINS)
        # 中間一塊山
        for q in range(5, 9):
            for r in range(5, 9):
                tm.get(Hex(q, r)).hilliness = Hilliness.LARGE_HILLS
        # 邊緣一塊森林
        _set_block(tm, 3, 3, 2, 3, TerrainType.FOREST)
        features = apply_features(tm)
        # 應該至少有 Ocean、MountainRange 兩種
        types = {f.feature_type for f in features}
        self.assertIn("Ocean", types)
        self.assertIn("MountainRange", types)


if __name__ == "__main__":
    unittest.main()
