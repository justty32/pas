"""WorldFeatures / FeatureWorker 測試。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.features import (
    FeatureWorker_BiomeRegion,
    FeatureWorker_Lake,
    FeatureWorker_Ocean,
    WorldFeatures,
    apply_features,
    default_workers,
)
from mapcore.generation import generate_world
from mapcore.grid import Coord
from mapcore.map import Hilliness, TerrainType, TileMap


class TestWorldFeatures(unittest.TestCase):
    def test_add_assigns_id(self):
        wf = WorldFeatures()
        f1 = wf.add("Ocean", "A", [Coord(0, 0)], Coord(0, 0))
        f2 = wf.add("Forest", "B", [Coord(1, 1)], Coord(1, 1))
        self.assertEqual(f1.id, 0)
        self.assertEqual(f2.id, 1)
        self.assertEqual(len(wf), 2)

    def test_get_oob_returns_none(self):
        wf = WorldFeatures()
        self.assertIsNone(wf.get(99))


class TestBiomeRegionWorker(unittest.TestCase):
    def test_finds_connected_forest(self):
        m = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        # 一塊森林
        for c in (Coord(1, 1), Coord(1, 2), Coord(2, 1), Coord(2, 2)):
            m.set_terrain(c, TerrainType.FOREST)
        worker = FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=2)
        wf = WorldFeatures()
        for _, tile in m:
            tile.feature_id = -1
        produced = worker.generate_where_appropriate(m, wf)
        self.assertEqual(produced, 1)
        self.assertEqual(len(wf), 1)
        self.assertEqual(wf.get(0).size, 4)

    def test_separates_disconnected(self):
        m = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        # 兩塊互不相連的森林
        m.set_terrain(Coord(0, 0), TerrainType.FOREST)
        m.set_terrain(Coord(1, 0), TerrainType.FOREST)
        m.set_terrain(Coord(4, 4), TerrainType.FOREST)
        m.set_terrain(Coord(4, 3), TerrainType.FOREST)
        worker = FeatureWorker_BiomeRegion(TerrainType.FOREST, "Forest", min_size=2)
        wf = WorldFeatures()
        for _, tile in m:
            tile.feature_id = -1
        worker.generate_where_appropriate(m, wf)
        self.assertEqual(len(wf), 2)


class TestApplyFeatures(unittest.TestCase):
    def test_pipeline_features(self):
        result = generate_world(50, 35, seed=42, heightmap_shape="continents")
        self.assertGreater(len(result.tile_map.features), 0)
        # 應該至少包含 Ocean
        types = {f.feature_type for f in result.tile_map.features}
        self.assertIn("Ocean", types)


class TestWorkerExclusion(unittest.TestCase):
    """Lake worker 排在 Ocean 之前，LAKE tile 不會被吃成 Ocean。"""

    def test_lake_before_ocean(self):
        m = TileMap(10, 10, default_terrain=TerrainType.OCEAN)
        # 內陸湖 (周圍是 ocean 也沒關係，重點是 LAKE terrain)
        for c in (Coord(4, 4), Coord(4, 5), Coord(5, 4), Coord(5, 5)):
            m.set_terrain(c, TerrainType.LAKE)
        features = apply_features(m, workers=[
            FeatureWorker_Lake("Lake", min_size=2),
            FeatureWorker_Ocean("Ocean", min_size=20),
        ])
        types = {f.feature_type for f in features}
        self.assertIn("Lake", types)
        self.assertIn("Ocean", types)


if __name__ == "__main__":
    unittest.main()
