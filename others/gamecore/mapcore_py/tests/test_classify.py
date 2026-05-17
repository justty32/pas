import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.classify import heightmap_to_tilemap
from mapcore.generation.heightmap import generate_heightmap
from mapcore.hex import Hex
from mapcore.map import TerrainType


def _flat(w, h, value):
    return [[value] * w for _ in range(h)]


class TestClassifyBasics(unittest.TestCase):
    def test_dimensions_match(self):
        hm = _flat(7, 4, 0.5)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        self.assertEqual(tm.width, 7)
        self.assertEqual(tm.height, 4)

    def test_all_below_threshold_all_ocean(self):
        hm = _flat(5, 5, 0.1)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for _, t in tm:
            # 全是海，沒有陸地 → 也不會有海岸
            self.assertEqual(t.terrain, TerrainType.OCEAN)

    def test_all_above_threshold_all_plains(self):
        hm = _flat(5, 5, 0.9)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for _, t in tm:
            self.assertEqual(t.terrain, TerrainType.PLAINS)

    def test_at_threshold_is_ocean(self):
        hm = _flat(2, 2, 0.4)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for _, t in tm:
            self.assertEqual(t.terrain, TerrainType.OCEAN)


class TestCoastDetection(unittest.TestCase):
    def test_island_in_ocean_has_surrounding_coast(self):
        # 5x5 全海，中央一格高 → 中央陸地，四鄰應該是 COAST。
        hm = _flat(5, 5, 0.1)
        hm[2][2] = 0.9
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        self.assertEqual(tm.get(Hex(2, 2)).terrain, TerrainType.PLAINS)
        for n in Hex(2, 2).neighbors():
            self.assertEqual(tm.get(n).terrain, TerrainType.COAST)

    def test_coast_only_adjacent_to_land(self):
        # 中央陸地一格，距離 2 以外的海格仍是 OCEAN，沒被誤標為 COAST。
        hm = _flat(7, 7, 0.1)
        hm[3][3] = 0.9
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for h, tile in tm:
            if tile.terrain != TerrainType.COAST:
                continue
            # 每個 COAST 至少有一個非海鄰居
            has_land = any(
                tm.get(n).terrain not in (TerrainType.OCEAN, TerrainType.COAST)
                for n in tm.neighbors(h)
            )
            self.assertTrue(has_land, f"COAST {h} 應該鄰接陸地")

    def test_no_coast_when_no_land(self):
        hm = _flat(6, 6, 0.0)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for _, t in tm:
            self.assertNotEqual(t.terrain, TerrainType.COAST)

    def test_no_coast_when_no_water(self):
        hm = _flat(6, 6, 1.0)
        tm = heightmap_to_tilemap(hm, sea_level=0.4)
        for _, t in tm:
            self.assertNotEqual(t.terrain, TerrainType.COAST)


class TestSeaLevelTuning(unittest.TestCase):
    def test_higher_sea_level_yields_more_ocean(self):
        hm = generate_heightmap(20, 20, seed=7)
        low = heightmap_to_tilemap(hm, sea_level=0.3)
        high = heightmap_to_tilemap(hm, sea_level=0.7)

        def count_ocean(tm):
            return sum(
                1 for _, t in tm if t.terrain in (TerrainType.OCEAN, TerrainType.COAST)
            )

        self.assertGreater(count_ocean(high), count_ocean(low))


class TestCoastDepth(unittest.TestCase):
    def test_depth_zero_means_no_coast(self):
        hm = _flat(5, 5, 0.1)
        hm[2][2] = 0.9
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=0)
        for _, t in tm:
            self.assertNotEqual(t.terrain, TerrainType.COAST)
        self.assertEqual(tm.get(Hex(2, 2)).terrain, TerrainType.PLAINS)

    def test_depth_two_extends_one_ring_further(self):
        # 中央陸地 1 格，coast_depth=1 只有第 1 環是海岸，
        # coast_depth=2 第 1、2 環都是海岸。
        hm = _flat(9, 9, 0.1)
        hm[4][4] = 0.9
        tm1 = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=1)
        tm2 = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=2)
        coast1 = [h for h, t in tm1 if t.terrain == TerrainType.COAST]
        coast2 = [h for h, t in tm2 if t.terrain == TerrainType.COAST]
        self.assertEqual(len(coast1), 6)        # 一圈
        self.assertEqual(len(coast2), 6 + 12)   # 一圈 + 兩圈

    def test_large_depth_eventually_consumes_all_ocean(self):
        # 海是有限的，coast_depth 夠大時應全部被吞掉。
        hm = _flat(5, 5, 0.1)
        hm[2][2] = 0.9
        tm = heightmap_to_tilemap(hm, sea_level=0.4, coast_depth=99)
        for _, t in tm:
            self.assertNotEqual(t.terrain, TerrainType.OCEAN)

    def test_negative_depth_raises(self):
        with self.assertRaises(ValueError):
            heightmap_to_tilemap(_flat(3, 3, 0.5), coast_depth=-1)


class TestValidation(unittest.TestCase):
    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            heightmap_to_tilemap([])
        with self.assertRaises(ValueError):
            heightmap_to_tilemap([[]])

    def test_ragged_raises(self):
        with self.assertRaises(ValueError):
            heightmap_to_tilemap([[0.1, 0.2], [0.3]])

    def test_sea_level_range(self):
        hm = _flat(3, 3, 0.5)
        with self.assertRaises(ValueError):
            heightmap_to_tilemap(hm, sea_level=-0.1)
        with self.assertRaises(ValueError):
            heightmap_to_tilemap(hm, sea_level=1.5)


if __name__ == "__main__":
    unittest.main()
