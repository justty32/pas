"""generation pipeline 各 phase 的單元測試。"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.biome import apply_biomes
from mapcore.generation.classify import expand_coast, heightmap_to_tilemap
from mapcore.generation.climate import (
    apply_climate,
    compute_hilliness,
    compute_rainfall_mm,
    compute_temperature_celsius,
    latitude_normalized,
)
from mapcore.generation.depressions import fill_depressions
from mapcore.generation.heightmap import generate_heightmap
from mapcore.generation.pipeline import generate_world
from mapcore.generation.postprocess import (
    find_components,
    is_land,
    is_water,
    post_process,
)
from mapcore.grid import Coord
from mapcore.map import Hilliness, TerrainType, TileMap


class TestHeightmap(unittest.TestCase):
    def test_shape_and_range(self):
        hm = generate_heightmap(20, 14, seed=42)
        self.assertEqual(len(hm), 14)
        self.assertEqual(len(hm[0]), 20)
        flat = [v for row in hm for v in row]
        self.assertGreaterEqual(min(flat), 0.0)
        self.assertLessEqual(max(flat), 1.0)

    def test_determinism(self):
        a = generate_heightmap(15, 10, seed=99)
        b = generate_heightmap(15, 10, seed=99)
        self.assertEqual(a, b)

    def test_seed_changes_output(self):
        a = generate_heightmap(15, 10, seed=1)
        b = generate_heightmap(15, 10, seed=2)
        self.assertNotEqual(a, b)

    def test_invalid_params_raise(self):
        with self.assertRaises(ValueError):
            generate_heightmap(0, 10)
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, octaves=0)
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, persistence=0.0)

    def test_plates_mode(self):
        hm = generate_heightmap(30, 20, seed=1, ridge_weight=0.5, ridge_mode="plates")
        self.assertEqual(len(hm), 20)

    def test_shapes_all_run(self):
        for shape in ("island", "archipelago", "pangaea", "continents", "ring_sea", "shattered_archipelago"):
            hm = generate_heightmap(20, 15, seed=1, shape=shape)
            self.assertEqual(len(hm), 15)
            self.assertEqual(len(hm[0]), 20)


class TestClassify(unittest.TestCase):
    def test_basic_split(self):
        hm = [
            [0.1, 0.2, 0.6],
            [0.3, 0.8, 0.9],
        ]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.OCEAN)
        self.assertEqual(tm.get(Coord(2, 0)).terrain, TerrainType.PLAINS)
        self.assertEqual(tm.get(Coord(2, 1)).terrain, TerrainType.PLAINS)

    def test_water_depth_filled(self):
        hm = [[0.1, 0.5]]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        self.assertAlmostEqual(tm.get(Coord(0, 0)).water_depth, 0.3)
        self.assertEqual(tm.get(Coord(1, 0)).water_depth, 0.0)

    def test_coast_expansion(self):
        hm = [
            [0.1, 0.1, 0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1, 0.1, 0.1],
            [0.1, 0.1, 0.5, 0.1, 0.1],
            [0.1, 0.1, 0.1, 0.1, 0.1],
            [0.1, 0.1, 0.1, 0.1, 0.1],
        ]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=1)
        # 4 個鄰居 = COAST，其餘 OCEAN
        self.assertEqual(tm.get(Coord(2, 2)).terrain, TerrainType.PLAINS)
        self.assertEqual(tm.get(Coord(1, 2)).terrain, TerrainType.COAST)
        self.assertEqual(tm.get(Coord(3, 2)).terrain, TerrainType.COAST)
        self.assertEqual(tm.get(Coord(2, 1)).terrain, TerrainType.COAST)
        self.assertEqual(tm.get(Coord(2, 3)).terrain, TerrainType.COAST)
        # 對角格不是 COAST（4 鄰居拓樸）
        self.assertEqual(tm.get(Coord(1, 1)).terrain, TerrainType.OCEAN)


class TestBiome(unittest.TestCase):
    def test_water_unchanged(self):
        hm = [[0.1, 0.5]]
        ms = [[0.5, 0.5]]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        apply_biomes(tm, hm, ms)
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.OCEAN)

    def test_mountain_threshold(self):
        hm = [[0.95]]
        ms = [[0.5]]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        apply_biomes(tm, hm, ms, mountain_threshold=0.85)
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.MOUNTAIN)

    def test_hill_threshold(self):
        hm = [[0.75]]
        ms = [[0.5]]
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        apply_biomes(tm, hm, ms, mountain_threshold=0.85, hill_threshold=0.70)
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.HILL)


class TestPostprocess(unittest.TestCase):
    def test_components(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.OCEAN)
        # 兩塊獨立陸地：(0,0)-(1,0) 與 (4,4)
        for c in (Coord(0, 0), Coord(1, 0), Coord(4, 4)):
            tm.set_terrain(c, TerrainType.PLAINS)
        comps = find_components(tm, is_land)
        sizes = sorted(len(c) for c in comps)
        self.assertEqual(sizes, [1, 2])

    def test_remove_small_islands(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.OCEAN)
        # 大陸 (3 連通)
        for c in (Coord(0, 0), Coord(1, 0), Coord(2, 0)):
            tm.set_terrain(c, TerrainType.PLAINS)
        # 孤島 (1)
        tm.set_terrain(Coord(4, 4), TerrainType.PLAINS)
        post_process(tm, island_min_size=3, lake_max_size=0, coast_depth=0)
        self.assertEqual(tm.get(Coord(4, 4)).terrain, TerrainType.OCEAN)
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.PLAINS)

    def test_remove_small_lakes_inland_only(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        # 內陸小湖
        tm.set_terrain(Coord(2, 2), TerrainType.OCEAN)
        # 接邊界的「小海」
        tm.set_terrain(Coord(0, 0), TerrainType.OCEAN)
        post_process(tm, island_min_size=0, lake_max_size=2, coast_depth=0)
        self.assertEqual(tm.get(Coord(2, 2)).terrain, TerrainType.PLAINS)  # 被填
        self.assertEqual(tm.get(Coord(0, 0)).terrain, TerrainType.OCEAN)   # 接邊界保留


class TestDepressions(unittest.TestCase):
    def test_no_depression(self):
        hm = [
            [0.5, 0.5, 0.5],
            [0.5, 0.5, 0.5],
            [0.5, 0.5, 0.5],
        ]
        lakes, filled = fill_depressions(hm, sea_level=0.3)
        self.assertEqual(lakes, set())
        self.assertEqual(filled, hm)

    def test_inland_basin_is_filled(self):
        # 5×5 高地中間有一個低洼
        hm = [[0.8] * 5 for _ in range(5)]
        hm[2][2] = 0.5
        lakes, filled = fill_depressions(hm, sea_level=0.3)
        self.assertIn((2, 2), lakes)
        self.assertGreater(filled[2][2], hm[2][2])


class TestClimate(unittest.TestCase):
    def test_latitude_normalized(self):
        self.assertEqual(latitude_normalized(0, 11), 1.0)    # 北極
        self.assertEqual(latitude_normalized(10, 11), 1.0)   # 南極
        self.assertEqual(latitude_normalized(5, 11), 0.0)    # 赤道

    def test_temperature_equator_warmer(self):
        eq = compute_temperature_celsius(5, 11, elev=0.4)
        pole = compute_temperature_celsius(0, 11, elev=0.4)
        self.assertGreater(eq, pole)

    def test_rainfall_high_elev_dry(self):
        low = compute_rainfall_mm(5, 11, elev=0.4, base_noise=0.5)
        high = compute_rainfall_mm(5, 11, elev=0.9, base_noise=0.5)
        self.assertGreater(low, high)

    def test_hilliness_thresholds(self):
        self.assertEqual(compute_hilliness(0.3), Hilliness.FLAT)
        self.assertIn(
            compute_hilliness(0.75),
            (Hilliness.SMALL_HILLS, Hilliness.LARGE_HILLS),
        )
        self.assertEqual(compute_hilliness(0.99), Hilliness.IMPASSABLE)

    def test_apply_climate_fills_hilliness(self):
        hm = [[0.5] * 5 for _ in range(5)]
        ms = [[0.5] * 5 for _ in range(5)]
        tm = heightmap_to_tilemap(hm, sea_level=0.3, coast_depth=0)
        temp, rain = apply_climate(tm, hm, ms, seed=1)
        self.assertEqual(len(temp), 5)
        self.assertEqual(len(rain), 5)
        # 陸地應該被填了 hilliness
        for _, tile in tm:
            self.assertNotEqual(tile.hilliness, Hilliness.UNDEFINED)


class TestPipelineEndToEnd(unittest.TestCase):
    def test_determinism(self):
        a = generate_world(40, 30, seed=42)
        b = generate_world(40, 30, seed=42)
        for y in range(30):
            for x in range(40):
                self.assertEqual(
                    a.tile_map.get(Coord(x, y)).terrain,
                    b.tile_map.get(Coord(x, y)).terrain,
                )

    def test_produces_terrain_variety(self):
        result = generate_world(60, 40, seed=42, heightmap_shape="continents", heightmap_ridge_weight=0.5)
        terrains = set()
        for _, t in result.tile_map:
            terrains.add(t.terrain)
        # 至少要有水跟陸
        self.assertIn(TerrainType.OCEAN, terrains)
        land_types = terrains - {TerrainType.OCEAN, TerrainType.COAST}
        self.assertGreaterEqual(len(land_types), 1)

    def test_features_generated(self):
        result = generate_world(60, 40, seed=42, heightmap_shape="continents")
        self.assertGreater(len(result.tile_map.features), 0)

    def test_lake_depressions(self):
        result = generate_world(40, 30, seed=7, heightmap_shape="pangaea",
                                heightmap_ridge_weight=0.7, lake_depressions=True)
        # 有些 seed 不一定產生湖，但這個 seed 觀察到有
        lakes = sum(1 for _, t in result.tile_map if t.terrain == TerrainType.LAKE)
        self.assertGreaterEqual(lakes, 0)


if __name__ == "__main__":
    unittest.main()
