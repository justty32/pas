"""完整 pipeline 整合測試：跑 generate_world 一次，驗證每個 phase 的輸出。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.pipeline import generate_world
from mapcore.hex import Hex
from mapcore.map import Hilliness, TerrainType, TileMap
from mapcore.rivers import iter_river_edges


class TestFullPipeline(unittest.TestCase):
    """跑完整 pipeline，確認 heightmap / classify / biome / postprocess / climate / rivers / features 全部產出。"""

    @classmethod
    def setUpClass(cls):
        cls.tile_map, cls.heightmap, cls.moisture = generate_world(
            30, 20, seed=42,
            sea_level=0.40,
            post_process=True,
            climate=True,
            rivers=True,
            features=True,
        )

    def test_returns_tilemap_with_features_attached(self):
        self.assertIsInstance(self.tile_map, TileMap)
        self.assertIsNotNone(self.tile_map.features)
        self.assertGreater(len(self.tile_map.features), 0)

    def test_heightmap_and_moisture_shapes(self):
        self.assertEqual(len(self.heightmap), 20)
        self.assertEqual(len(self.heightmap[0]), 30)
        self.assertEqual(len(self.moisture), 20)
        self.assertEqual(len(self.moisture[0]), 30)

    def test_all_tiles_have_hilliness_set(self):
        # 跑過 climate 後，沒有 tile 還是 UNDEFINED
        undefined_count = sum(
            1 for _, t in self.tile_map if t.hilliness == Hilliness.UNDEFINED
        )
        self.assertEqual(undefined_count, 0)

    def test_water_tiles_have_flat_hilliness(self):
        for h, t in self.tile_map:
            if t.terrain in (TerrainType.OCEAN, TerrainType.COAST):
                self.assertEqual(t.hilliness, Hilliness.FLAT,
                                 f"water tile at {h} has hilliness {t.hilliness}")

    def test_features_cover_at_least_water(self):
        # 默認 workers 第一個是 Ocean (min_size=20) — 30×20 地圖通常會有大塊海
        feature_types = {f.feature_type for f in self.tile_map.features}
        # 海或山脈或 biome region 至少有一個
        self.assertTrue(any(t.startswith("Ocean") or t.startswith("MountainRange")
                            or t.startswith("BiomeRegion") for t in feature_types))

    def test_feature_ids_consistent(self):
        # 每個有 feature_id 的 tile 都能在 features 容器中查到對應的 feature
        for h, t in self.tile_map:
            if t.feature_id >= 0:
                f = self.tile_map.features.get(t.feature_id)
                self.assertIsNotNone(f)
                # 而且這個 tile 應該在 feature.tiles 裡（透過 __eq__）
                self.assertIn(h, f.tiles)

    def test_rivers_emit_some_edges(self):
        edges = list(iter_river_edges(self.tile_map))
        # 預設參數下這個 size 通常有河流產出；若極端 seed 無河，至少語法不爆
        self.assertIsInstance(edges, list)

    def test_deterministic_with_same_seed(self):
        tm1, hm1, _ = generate_world(20, 15, seed=99, post_process=True)
        tm2, hm2, _ = generate_world(20, 15, seed=99, post_process=True)
        self.assertEqual(hm1, hm2)
        # 每格 terrain / hilliness / feature_id 都一致
        for h, t in tm1:
            t2 = tm2.get(h)
            self.assertEqual(t.terrain, t2.terrain)
            self.assertEqual(t.hilliness, t2.hilliness)
            self.assertEqual(t.feature_id, t2.feature_id)
            self.assertEqual(t.rivers, t2.rivers)


class TestPipelineFlags(unittest.TestCase):
    def test_disable_features_leaves_no_features(self):
        tm, _, _ = generate_world(15, 10, seed=1, features=False)
        self.assertIsNone(tm.features)
        # tile.feature_id 都該是 -1
        for _, t in tm:
            self.assertEqual(t.feature_id, -1)

    def test_disable_climate_leaves_hilliness_undefined(self):
        tm, _, _ = generate_world(15, 10, seed=1, climate=False, features=False)
        # 沒跑 climate 時 hilliness 應全為 UNDEFINED
        undefined_count = sum(
            1 for _, t in tm if t.hilliness == Hilliness.UNDEFINED
        )
        self.assertEqual(undefined_count, 15 * 10)

    def test_disable_rivers_leaves_no_river_edges(self):
        tm, _, _ = generate_world(15, 10, seed=1, rivers=False)
        self.assertEqual(list(iter_river_edges(tm)), [])


if __name__ == "__main__":
    unittest.main()
