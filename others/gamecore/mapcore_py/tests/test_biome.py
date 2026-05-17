import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.biome import apply_biomes
from mapcore.generation.classify import heightmap_to_tilemap
from mapcore.generation.pipeline import generate_world
from mapcore.hex import Hex
from mapcore.map import TerrainType, TileMap


def _flat(w, h, v):
    return [[v] * w for _ in range(h)]


def _land_tilemap(w, h):
    tm = TileMap(w, h, default_terrain=TerrainType.PLAINS)
    return tm


class TestElevationOverrides(unittest.TestCase):
    def test_mountain_threshold(self):
        tm = _land_tilemap(3, 3)
        hm = _flat(3, 3, 0.9)
        moi = _flat(3, 3, 0.5)
        apply_biomes(tm, hm, moi, mountain_threshold=0.85, hill_threshold=0.70)
        for _, t in tm:
            self.assertEqual(t.terrain, TerrainType.MOUNTAIN)

    def test_hill_band(self):
        tm = _land_tilemap(3, 3)
        hm = _flat(3, 3, 0.75)
        moi = _flat(3, 3, 0.5)
        apply_biomes(tm, hm, moi)
        for _, t in tm:
            self.assertEqual(t.terrain, TerrainType.HILL)


class TestOceanCoastUntouched(unittest.TestCase):
    def test_ocean_and_coast_not_modified(self):
        # 用整套切割產出 OCEAN/COAST，再跑 biome；OCEAN/COAST 應保留。
        hm = _flat(5, 5, 0.1)
        hm[2][2] = 0.9
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=1)
        moi = _flat(5, 5, 0.5)
        apply_biomes(tm, hm, moi)
        self.assertEqual(tm.get(Hex(0, 0)).terrain, TerrainType.OCEAN)
        self.assertEqual(tm.get(Hex(1, 2)).terrain, TerrainType.COAST)
        # 中央陸地被改成 MOUNTAIN (elev=0.9)
        self.assertEqual(tm.get(Hex(2, 2)).terrain, TerrainType.MOUNTAIN)


class TestTemperatureClassification(unittest.TestCase):
    def test_polar_rows_become_cold(self):
        # 高度 0.5（陸地）、極端緯度（r=0 與 r=H-1）→ 應為 SNOW 或 TUNDRA。
        H = 11
        tm = _land_tilemap(3, H)
        hm = _flat(3, H, 0.5)
        moi = _flat(3, H, 0.5)
        apply_biomes(tm, hm, moi)
        for q in range(3):
            self.assertIn(
                tm.get(Hex(q, 0)).terrain,
                (TerrainType.SNOW, TerrainType.TUNDRA),
            )
            self.assertIn(
                tm.get(Hex(q, H - 1)).terrain,
                (TerrainType.SNOW, TerrainType.TUNDRA),
            )

    def test_equator_warm(self):
        H = 11
        tm = _land_tilemap(3, H)
        hm = _flat(3, H, 0.5)
        moi = _flat(3, H, 0.5)
        apply_biomes(tm, hm, moi)
        # 中央列（赤道）moisture=0.5 → 落在 dry/wet 之間，視 hot/temperate 分流
        # 應為 GRASSLAND 或 PLAINS。不該是 SNOW/TUNDRA。
        for q in range(3):
            t = tm.get(Hex(q, H // 2)).terrain
            self.assertNotIn(t, (TerrainType.SNOW, TerrainType.TUNDRA))


class TestMoistureClassification(unittest.TestCase):
    def test_hot_dry_becomes_desert(self):
        # 赤道、不高、moisture 很低 → DESERT。
        H = 5
        tm = _land_tilemap(3, H)
        hm = _flat(3, H, 0.5)
        moi = _flat(3, H, 0.05)  # 很乾
        apply_biomes(tm, hm, moi)
        self.assertEqual(tm.get(Hex(1, H // 2)).terrain, TerrainType.DESERT)

    def test_wet_becomes_forest(self):
        H = 5
        tm = _land_tilemap(3, H)
        hm = _flat(3, H, 0.5)
        moi = _flat(3, H, 0.95)  # 很濕
        apply_biomes(tm, hm, moi)
        self.assertEqual(tm.get(Hex(1, H // 2)).terrain, TerrainType.FOREST)


class TestValidation(unittest.TestCase):
    def test_shape_mismatch_raises(self):
        tm = _land_tilemap(3, 3)
        with self.assertRaises(ValueError):
            apply_biomes(tm, _flat(3, 2, 0.5), _flat(3, 3, 0.5))
        with self.assertRaises(ValueError):
            apply_biomes(tm, _flat(3, 3, 0.5), _flat(2, 3, 0.5))


class TestPipeline(unittest.TestCase):
    def test_generate_world_basic(self):
        tm, hm, moi = generate_world(20, 12, seed=42)
        self.assertEqual(tm.width, 20)
        self.assertEqual(tm.height, 12)
        self.assertEqual(len(hm), 12)
        self.assertEqual(len(moi), 12)

    def test_generate_world_deterministic(self):
        tm_a, hm_a, moi_a = generate_world(15, 10, seed=7)
        tm_b, hm_b, moi_b = generate_world(15, 10, seed=7)
        self.assertEqual(hm_a, hm_b)
        self.assertEqual(moi_a, moi_b)
        terrains_a = [t.terrain for _, t in tm_a]
        terrains_b = [t.terrain for _, t in tm_b]
        self.assertEqual(terrains_a, terrains_b)

    def test_generate_world_height_and_moisture_decorrelated(self):
        _, hm, moi = generate_world(20, 12, seed=42)
        # 兩張噪聲不該完全相同（決定性 OK，但內容應不同）。
        self.assertNotEqual(hm, moi)


if __name__ == "__main__":
    unittest.main()
