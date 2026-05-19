"""river 邊存儲與生成測試。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation import generate_world
from mapcore.grid import Coord
from mapcore.map import TerrainType, TileMap
from mapcore.rivers import (
    RIVER_MAX_STRENGTH,
    add_river_flow,
    classify_river_strength,
    get_river_strength,
    has_river_edge,
    iter_river_edges,
    set_river_edge,
    set_river_strength,
)


class TestEdgeOwnership(unittest.TestCase):
    """同一條邊不論從哪一側操作都應該得到相同 strength。"""

    def setUp(self):
        self.m = TileMap(5, 5)

    def test_e_w_share_edge(self):
        set_river_strength(self.m, Coord(2, 2), 0, 50)  # E
        # W of (3, 2) = E of (2, 2)
        self.assertEqual(get_river_strength(self.m, Coord(3, 2), 2), 50)

    def test_n_s_share_edge(self):
        set_river_strength(self.m, Coord(2, 2), 1, 80)  # N
        # S of (2, 1) = N of (2, 2)
        self.assertEqual(get_river_strength(self.m, Coord(2, 1), 3), 80)

    def test_independent_slots(self):
        set_river_strength(self.m, Coord(2, 2), 0, 50)  # E
        set_river_strength(self.m, Coord(2, 2), 1, 80)  # N
        self.assertEqual(get_river_strength(self.m, Coord(2, 2), 0), 50)
        self.assertEqual(get_river_strength(self.m, Coord(2, 2), 1), 80)

    def test_clamp_to_max(self):
        set_river_strength(self.m, Coord(2, 2), 0, 999)
        self.assertEqual(get_river_strength(self.m, Coord(2, 2), 0), RIVER_MAX_STRENGTH)

    def test_negative_clamps_to_zero(self):
        set_river_strength(self.m, Coord(2, 2), 0, -10)
        self.assertEqual(get_river_strength(self.m, Coord(2, 2), 0), 0)

    def test_out_of_bounds_safe(self):
        # 邊界外的格子不應 crash
        set_river_strength(self.m, Coord(-1, 0), 0, 50)
        self.assertEqual(get_river_strength(self.m, Coord(-1, 0), 0), 0)

    def test_invalid_direction_raises(self):
        with self.assertRaises(ValueError):
            set_river_strength(self.m, Coord(2, 2), 4, 10)

    def test_add_accumulates(self):
        add_river_flow(self.m, Coord(2, 2), 0, 50)
        add_river_flow(self.m, Coord(2, 2), 0, 30)
        self.assertEqual(get_river_strength(self.m, Coord(2, 2), 0), 80)

    def test_set_river_edge_boolean(self):
        set_river_edge(self.m, Coord(2, 2), 0, True)
        self.assertTrue(has_river_edge(self.m, Coord(2, 2), 0))
        set_river_edge(self.m, Coord(2, 2), 0, False)
        self.assertFalse(has_river_edge(self.m, Coord(2, 2), 0))


class TestIterRiverEdges(unittest.TestCase):
    def test_empty(self):
        m = TileMap(5, 5)
        self.assertEqual(list(iter_river_edges(m)), [])

    def test_yields_set_edges(self):
        m = TileMap(5, 5)
        set_river_strength(m, Coord(1, 1), 0, 10)
        set_river_strength(m, Coord(2, 2), 1, 20)
        edges = list(iter_river_edges(m))
        self.assertEqual(len(edges), 2)
        edges_dict = {(c.x, c.y, d): s for c, d, s in edges}
        self.assertEqual(edges_dict[(1, 1, 0)], 10)
        self.assertEqual(edges_dict[(2, 2, 1)], 20)

    def test_no_duplicate_ownership(self):
        # 同一條邊只會出現一次（由 owner 持有），不會在兩個 tile 上都報
        m = TileMap(5, 5)
        set_river_strength(m, Coord(1, 1), 0, 10)  # E
        # 從 (2, 1) 的 W 角度操作同一條邊
        set_river_strength(m, Coord(2, 1), 2, 30)  # 覆寫到同一條邊
        edges = list(iter_river_edges(m))
        self.assertEqual(len(edges), 1)
        # 後寫的值勝出
        c, d, s = edges[0]
        self.assertEqual(s, 30)


class TestClassify(unittest.TestCase):
    def test_classes(self):
        from mapcore.rivers import RiverClass
        self.assertEqual(classify_river_strength(50), RiverClass.CREEK)
        self.assertEqual(classify_river_strength(100), RiverClass.RIVER)
        self.assertEqual(classify_river_strength(200), RiverClass.LARGE_RIVER)


class TestGenerateRiversIntegration(unittest.TestCase):
    def test_pipeline_produces_some_rivers(self):
        # 用大張地圖才能跑出河流
        result = generate_world(60, 40, seed=42, heightmap_shape="continents")
        edges = list(iter_river_edges(result.tile_map))
        # 不嚴格要求 N，但至少要有
        self.assertGreater(len(edges), 0)

    def test_rivers_on_land(self):
        """河流邊兩側至少要有一側不是海（否則就是純海面的「河」）。"""
        result = generate_world(60, 40, seed=42, heightmap_shape="continents")
        tm = result.tile_map
        ocean_only_edges = 0
        for c, d, s in iter_river_edges(tm):
            from mapcore.grid import DIRECTIONS
            other = c + DIRECTIONS[d]
            cur_tile = tm.get(c)
            other_tile = tm.get(other)
            cur_is_water = cur_tile.terrain in (TerrainType.OCEAN, TerrainType.COAST)
            other_is_water = (other_tile is None) or other_tile.terrain in (TerrainType.OCEAN, TerrainType.COAST)
            if cur_is_water and other_is_water:
                ocean_only_edges += 1
        # 允許少量「入海口邊」連兩格都是水的情況，但不應該佔太多
        total = sum(1 for _ in iter_river_edges(tm))
        if total > 0:
            self.assertLess(ocean_only_edges / total, 0.5)


if __name__ == "__main__":
    unittest.main()
