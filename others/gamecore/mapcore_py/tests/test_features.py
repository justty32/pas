import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex
from mapcore.map import Hilliness, TerrainType, TileMap
from mapcore.features import (
    FeatureWorker_BiomeRegion,
    FeatureWorker_Coast,
    FeatureWorker_Continent,
    FeatureWorker_Icecap,
    FeatureWorker_Island,
    FeatureWorker_Lake,
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


class TestLakeWorker(unittest.TestCase):
    def test_picks_up_lake_block(self):
        tm = TileMap(8, 8, default_terrain=TerrainType.PLAINS)
        _set_block(tm, 3, 3, 2, 2, TerrainType.LAKE)
        features = WorldFeatures()
        worker = FeatureWorker_Lake("Lake", min_size=2)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 1)
        f = next(iter(features))
        self.assertEqual(f.feature_type, "Lake")
        self.assertEqual(f.size, 4)

    def test_ignores_ocean(self):
        # LAKE 和 OCEAN 都是 is_water=True，但本 worker 只認 LAKE
        tm = TileMap(8, 8, default_terrain=TerrainType.OCEAN)
        features = WorldFeatures()
        worker = FeatureWorker_Lake("Lake", min_size=2)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 0)


class TestOceanLakeInteraction(unittest.TestCase):
    """覆寫 Ocean.is_member 後，內陸湖不再被誤標成 Ocean。"""

    def test_ocean_does_not_eat_lake(self):
        tm = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        # 一塊海，一個獨立的湖
        _set_block(tm, 0, 0, 5, 10, TerrainType.OCEAN)
        _set_block(tm, 7, 3, 2, 2, TerrainType.LAKE)
        features = apply_features(
            tm,
            workers=[
                FeatureWorker_Lake("Lake", min_size=2),
                FeatureWorker_Ocean("Ocean", min_size=10),
            ],
        )
        types = sorted(f.feature_type for f in features)
        self.assertEqual(types, ["Lake", "Ocean"])
        # LAKE 格的 feature_id 應對應 Lake，不是 Ocean
        lake_id = next(f.id for f in features if f.feature_type == "Lake")
        self.assertEqual(tm.get(Hex(7, 3)).feature_id, lake_id)

    def test_ocean_without_lake_worker_still_works(self):
        # 即使沒掛 Lake worker，LAKE 也不該被 Ocean 吃掉（顯式 OCEAN/COAST 判斷）
        tm = TileMap(8, 8, default_terrain=TerrainType.OCEAN)
        _set_block(tm, 3, 3, 2, 2, TerrainType.LAKE)
        features = apply_features(tm, workers=[FeatureWorker_Ocean("Ocean", min_size=10)])
        for f in features:
            self.assertNotEqual(f.feature_type, "Lake")
            self.assertEqual(f.feature_type, "Ocean")
        # LAKE 格 feature_id 應仍是 -1
        self.assertEqual(tm.get(Hex(3, 3)).feature_id, -1)


class TestCoastWorker(unittest.TestCase):
    def test_separates_coast_from_ocean(self):
        # COAST 一條帶 + OCEAN 一大塊。Coast 先跑，搶 COAST tiles，Ocean 只剩 OCEAN
        tm = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        _set_block(tm, 0, 0, 10, 3, TerrainType.OCEAN)
        _set_block(tm, 0, 3, 10, 1, TerrainType.COAST)  # 10 格
        features = apply_features(
            tm,
            workers=[
                FeatureWorker_Coast("Coast", min_size=5),
                FeatureWorker_Ocean("Ocean", min_size=10),
            ],
        )
        types = sorted(f.feature_type for f in features)
        self.assertEqual(types, ["Coast", "Ocean"])
        coast_id = next(f.id for f in features if f.feature_type == "Coast")
        ocean_id = next(f.id for f in features if f.feature_type == "Ocean")
        self.assertEqual(tm.get(Hex(0, 3)).feature_id, coast_id)
        self.assertEqual(tm.get(Hex(0, 0)).feature_id, ocean_id)


class TestIcecapWorker(unittest.TestCase):
    def test_only_picks_polar_snow(self):
        tm = TileMap(10, 20, default_terrain=TerrainType.PLAINS)
        # polar_band=0.15 → ratio < 0.15 或 > 0.85，r in [0..19]，ratio = r/19
        # 北極 (r=0,1,2)，南極 (r=17,18,19) 算極區
        _set_block(tm, 0, 0, 10, 3, TerrainType.SNOW)    # 北極帶 30 格
        _set_block(tm, 0, 8, 10, 4, TerrainType.SNOW)    # 中緯度 40 格（不該被收）
        features = WorldFeatures()
        worker = FeatureWorker_Icecap("Icecap", polar_band=0.15, min_size=5)
        worker.generate_where_appropriate(tm, features)
        # 只該有一塊（北極帶 30 格）；中緯雪不算 icecap
        self.assertEqual(len(features), 1)
        f = next(iter(features))
        self.assertEqual(f.feature_type, "Icecap")
        self.assertEqual(f.size, 30)

    def test_ignores_non_snow(self):
        # 即使在極區，非 SNOW 也不收
        tm = TileMap(10, 10, default_terrain=TerrainType.TUNDRA)
        features = WorldFeatures()
        worker = FeatureWorker_Icecap("Icecap", polar_band=0.5, min_size=5)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 0)


class TestContinentWorker(unittest.TestCase):
    def test_spans_multiple_biomes(self):
        # 大陸：一塊大陸地裡面同時有 forest 和 desert
        tm = TileMap(15, 15, default_terrain=TerrainType.OCEAN)
        _set_block(tm, 2, 2, 11, 11, TerrainType.PLAINS)
        _set_block(tm, 3, 3, 4, 4, TerrainType.FOREST)
        _set_block(tm, 8, 3, 4, 4, TerrainType.DESERT)
        features = apply_features(
            tm,
            workers=[
                FeatureWorker_Ocean("Ocean", min_size=10),
                FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=5),
                FeatureWorker_BiomeRegion(TerrainType.DESERT, "Desert", min_size=5),
                FeatureWorker_Continent("Continent", min_size=20),
            ],
        )
        types = sorted(f.feature_type for f in features)
        self.assertIn("Continent", types)
        self.assertIn("BiomeRegion:FOREST", types)
        self.assertIn("BiomeRegion:DESERT", types)
        # Continent 應該包含整塊陸地 11x11=121 格
        cont = next(f for f in features if f.feature_type == "Continent")
        self.assertEqual(cont.size, 121)

    def test_does_not_overwrite_feature_id(self):
        # 跑 Forest 再跑 Continent：陸地 tile 的 feature_id 應仍指向 Forest，不被 Continent 蓋掉
        tm = TileMap(12, 12, default_terrain=TerrainType.OCEAN)
        _set_block(tm, 2, 2, 8, 8, TerrainType.FOREST)
        features = apply_features(
            tm,
            workers=[
                FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=5),
                FeatureWorker_Continent("Continent", min_size=20),
            ],
        )
        forest_id = next(f.id for f in features if f.feature_type == "BiomeRegion:FOREST")
        # 隨便取一個陸地格驗證
        self.assertEqual(tm.get(Hex(5, 5)).feature_id, forest_id)

    def test_ignores_water(self):
        tm = TileMap(10, 10, default_terrain=TerrainType.OCEAN)
        features = WorldFeatures()
        worker = FeatureWorker_Continent("Continent", min_size=5)
        worker.generate_where_appropriate(tm, features)
        self.assertEqual(len(features), 0)


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
