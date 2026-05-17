import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex, distance
from mapcore.map import TerrainType, TileMap
from mapcore.pathfinding import astar, path_cost


def _is_connected(path):
    for i in range(len(path) - 1):
        if distance(path[i], path[i + 1]) != 1:
            return False
    return True


class TestTrivial(unittest.TestCase):
    def test_same_start_and_goal(self):
        m = TileMap(3, 3)
        self.assertEqual(astar(m, Hex(1, 1), Hex(1, 1)), [Hex(1, 1)])

    def test_adjacent(self):
        m = TileMap(3, 3)
        path = astar(m, Hex(0, 0), Hex(1, 0))
        self.assertEqual(path, [Hex(0, 0), Hex(1, 0)])

    def test_oob_returns_none(self):
        m = TileMap(3, 3)
        self.assertIsNone(astar(m, Hex(-1, 0), Hex(1, 1)))
        self.assertIsNone(astar(m, Hex(0, 0), Hex(99, 99)))


class TestPathProperties(unittest.TestCase):
    def test_path_is_connected(self):
        m = TileMap(8, 8)
        path = astar(m, Hex(0, 0), Hex(7, 7))
        self.assertIsNotNone(path)
        self.assertTrue(_is_connected(path))

    def test_endpoints_correct(self):
        m = TileMap(6, 6)
        path = astar(m, Hex(1, 1), Hex(4, 4))
        self.assertEqual(path[0], Hex(1, 1))
        self.assertEqual(path[-1], Hex(4, 4))

    def test_plains_optimal_length_equals_hex_distance(self):
        m = TileMap(10, 10)
        start, goal = Hex(0, 0), Hex(6, 3)
        path = astar(m, start, goal)
        self.assertEqual(len(path) - 1, distance(start, goal))


class TestBlockedAndDetour(unittest.TestCase):
    def test_wall_blocks_all(self):
        m = TileMap(5, 5)
        for r in range(5):
            m.set_terrain(Hex(2, r), TerrainType.MOUNTAIN)
        self.assertIsNone(astar(m, Hex(0, 0), Hex(4, 0)))

    def test_detour_around_obstacle(self):
        m = TileMap(5, 5)
        m.set_terrain(Hex(2, 1), TerrainType.MOUNTAIN)
        path = astar(m, Hex(0, 0), Hex(4, 2))
        self.assertIsNotNone(path)
        self.assertTrue(_is_connected(path))
        for h in path:
            self.assertNotEqual(m.get(h).terrain, TerrainType.MOUNTAIN)

    def test_goal_surrounded_by_ocean_unreachable(self):
        m = TileMap(5, 5)
        goal = Hex(2, 2)
        for n in goal.neighbors():
            if m.in_bounds(n):
                m.set_terrain(n, TerrainType.OCEAN)
        self.assertIsNone(astar(m, Hex(0, 0), goal))

    def test_start_on_impassable_can_still_leave(self):
        m = TileMap(4, 4)
        m.set_terrain(Hex(0, 0), TerrainType.MOUNTAIN)
        path = astar(m, Hex(0, 0), Hex(2, 2))
        self.assertIsNotNone(path)
        self.assertEqual(path[0], Hex(0, 0))


class TestTerrainCostBias(unittest.TestCase):
    def test_prefers_cheap_terrain(self):
        # 在直線上鋪森林 (cost 2.0)，繞行可走草原 (cost 1.0)，A* 應選擇繞行。
        m = TileMap(6, 4)
        for q in range(1, 5):
            m.set_terrain(Hex(q, 1), TerrainType.FOREST)
        path = astar(m, Hex(0, 1), Hex(5, 1))
        self.assertIsNotNone(path)
        forest_steps = sum(1 for h in path if m.get(h).terrain == TerrainType.FOREST)
        # 直線會經過 4 格森林；繞行只會碰到 0 或 1 格。
        self.assertLessEqual(forest_steps, 1)


class TestPathCost(unittest.TestCase):
    def test_empty_and_single(self):
        m = TileMap(3, 3)
        self.assertEqual(path_cost(m, []), 0.0)
        self.assertEqual(path_cost(m, [Hex(1, 1)]), 0.0)

    def test_plains_cost_equals_steps(self):
        m = TileMap(5, 5)
        path = astar(m, Hex(0, 0), Hex(3, 0))
        self.assertEqual(path_cost(m, path), 3.0)

    def test_mixed_terrain(self):
        m = TileMap(5, 1)
        m.set_terrain(Hex(1, 0), TerrainType.FOREST)  # 2.0
        m.set_terrain(Hex(2, 0), TerrainType.DESERT)  # 1.5
        path = [Hex(0, 0), Hex(1, 0), Hex(2, 0)]
        self.assertEqual(path_cost(m, path), 2.0 + 1.5)


if __name__ == "__main__":
    unittest.main()
