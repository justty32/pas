import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex
from mapcore.map import (
    TERRAIN_COST,
    TerrainType,
    Tile,
    TileMap,
    is_passable,
    terrain_cost,
)


class TestTerrainCost(unittest.TestCase):
    def test_all_terrains_have_cost(self):
        for t in TerrainType:
            self.assertIn(t, TERRAIN_COST)

    def test_ocean_and_mountain_impassable(self):
        self.assertFalse(is_passable(TerrainType.OCEAN))
        self.assertFalse(is_passable(TerrainType.MOUNTAIN))
        self.assertFalse(is_passable(TerrainType.COAST))

    def test_plains_passable_cost_one(self):
        self.assertTrue(is_passable(TerrainType.PLAINS))
        self.assertEqual(terrain_cost(TerrainType.PLAINS), 1.0)

    def test_impassable_cost_inf(self):
        self.assertTrue(math.isinf(terrain_cost(TerrainType.MOUNTAIN)))


class TestTileMapConstruction(unittest.TestCase):
    def test_invalid_dims_raise(self):
        with self.assertRaises(ValueError):
            TileMap(0, 5)
        with self.assertRaises(ValueError):
            TileMap(5, -1)

    def test_default_terrain_plains(self):
        m = TileMap(4, 3)
        for _, tile in m:
            self.assertEqual(tile.terrain, TerrainType.PLAINS)

    def test_custom_default_terrain(self):
        m = TileMap(2, 2, default_terrain=TerrainType.OCEAN)
        for _, tile in m:
            self.assertEqual(tile.terrain, TerrainType.OCEAN)

    def test_size(self):
        m = TileMap(7, 5)
        self.assertEqual(len(m), 35)
        self.assertEqual(sum(1 for _ in m), 35)


class TestBoundsAndAccess(unittest.TestCase):
    def setUp(self):
        self.m = TileMap(4, 3)

    def test_in_bounds(self):
        self.assertTrue(self.m.in_bounds(Hex(0, 0)))
        self.assertTrue(self.m.in_bounds(Hex(3, 2)))
        self.assertFalse(self.m.in_bounds(Hex(4, 0)))
        self.assertFalse(self.m.in_bounds(Hex(-1, 0)))
        self.assertFalse(self.m.in_bounds(Hex(0, 3)))

    def test_get_out_of_bounds_returns_none(self):
        self.assertIsNone(self.m.get(Hex(99, 99)))
        self.assertIsNone(self.m.get(Hex(-1, 0)))

    def test_set_then_get(self):
        new_tile = Tile(TerrainType.MOUNTAIN)
        self.m.set(Hex(1, 1), new_tile)
        self.assertIs(self.m.get(Hex(1, 1)), new_tile)

    def test_set_out_of_bounds_raises(self):
        with self.assertRaises(IndexError):
            self.m.set(Hex(99, 99), Tile())

    def test_set_terrain_shortcut(self):
        self.m.set_terrain(Hex(2, 1), TerrainType.DESERT)
        self.assertEqual(self.m.get(Hex(2, 1)).terrain, TerrainType.DESERT)

    def test_set_terrain_out_of_bounds_raises(self):
        with self.assertRaises(IndexError):
            self.m.set_terrain(Hex(-1, 0), TerrainType.DESERT)


class TestNeighbors(unittest.TestCase):
    def test_interior_has_six_neighbors(self):
        m = TileMap(5, 5)
        # Hex(2, 2) is interior — all 6 axial neighbors fit in 5x5 parallelogram.
        self.assertEqual(len(m.neighbors(Hex(2, 2))), 6)

    def test_corner_has_fewer_neighbors(self):
        m = TileMap(5, 5)
        self.assertLess(len(m.neighbors(Hex(0, 0))), 6)
        self.assertLess(len(m.neighbors(Hex(4, 4))), 6)

    def test_passable_filter(self):
        m = TileMap(3, 3)
        m.set_terrain(Hex(2, 1), TerrainType.MOUNTAIN)
        m.set_terrain(Hex(1, 2), TerrainType.OCEAN)
        all_n = m.neighbors(Hex(1, 1))
        passable = m.passable_neighbors(Hex(1, 1))
        self.assertEqual(len(all_n) - len(passable), 2)
        for h in passable:
            self.assertNotEqual(m.get(h).terrain, TerrainType.MOUNTAIN)
            self.assertNotEqual(m.get(h).terrain, TerrainType.OCEAN)


class TestIteration(unittest.TestCase):
    def test_all_coords_count(self):
        m = TileMap(6, 4)
        coords = list(m.all_coords())
        self.assertEqual(len(coords), 24)
        # 確認沒重複
        keys = [(h.q, h.r) for h in coords]
        self.assertEqual(len(keys), len(set(keys)))

    def test_iter_yields_pairs(self):
        m = TileMap(2, 2)
        items = list(m)
        self.assertEqual(len(items), 4)
        for h, t in items:
            self.assertIsInstance(h, Hex)
            self.assertIsInstance(t, Tile)


class TestFill(unittest.TestCase):
    def test_fill_replaces_all(self):
        m = TileMap(3, 3)
        m.fill(TerrainType.FOREST)
        for _, t in m:
            self.assertEqual(t.terrain, TerrainType.FOREST)


if __name__ == "__main__":
    unittest.main()
