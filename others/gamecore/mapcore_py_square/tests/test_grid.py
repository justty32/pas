import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.grid import (
    DIRECTIONS,
    Coord,
    direction,
    distance,
    line,
    ring,
    spiral,
)


class TestCoordBasics(unittest.TestCase):
    def test_equality_by_value(self):
        self.assertEqual(Coord(1, 2), Coord(1, 2))
        self.assertNotEqual(Coord(1, 2), Coord(1, 3))

    def test_unhashable(self):
        # 對齊 hex 版設計：禁止把 Coord 當 dict/set 鍵
        self.assertIsNone(Coord.__hash__)
        with self.assertRaises(TypeError):
            {Coord(0, 0)}

    def test_mutable_fields(self):
        c = Coord(0, 0)
        c.x = 5
        self.assertEqual(c, Coord(5, 0))

    def test_arithmetic(self):
        self.assertEqual(Coord(1, 2) + Coord(3, 4), Coord(4, 6))
        self.assertEqual(Coord(5, 5) - Coord(2, 1), Coord(3, 4))
        self.assertEqual(Coord(1, -1) * 3, Coord(3, -3))


class TestDirectionsAndNeighbors(unittest.TestCase):
    def test_four_directions_unique(self):
        keys = [(d.x, d.y) for d in DIRECTIONS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(DIRECTIONS), 4)

    def test_directions_sum_to_zero(self):
        total = Coord(0, 0)
        for d in DIRECTIONS:
            total = total + d
        self.assertEqual(total, Coord(0, 0))

    def test_opposite_directions(self):
        # 對立方向 = (i + 2) % 4
        for i in range(4):
            opp = DIRECTIONS[(i + 2) % 4]
            self.assertEqual(DIRECTIONS[i] + opp, Coord(0, 0))

    def test_direction_wraps_modulo_4(self):
        self.assertEqual(direction(5), DIRECTIONS[1])
        self.assertEqual(direction(-1), DIRECTIONS[3])

    def test_neighbors(self):
        center = Coord(5, -3)
        neighbors = center.neighbors()
        self.assertEqual(len(neighbors), 4)
        for n in neighbors:
            self.assertEqual(distance(center, n), 1)


class TestDistance(unittest.TestCase):
    def test_self_distance_zero(self):
        self.assertEqual(distance(Coord(7, -4), Coord(7, -4)), 0)

    def test_neighbor_distance_one(self):
        for d in DIRECTIONS:
            self.assertEqual(distance(Coord(0, 0), d), 1)

    def test_manhattan(self):
        self.assertEqual(distance(Coord(0, 0), Coord(3, 0)), 3)
        self.assertEqual(distance(Coord(0, 0), Coord(3, -3)), 6)
        self.assertEqual(distance(Coord(-2, 1), Coord(2, -1)), 6)


class TestLine(unittest.TestCase):
    def test_line_length(self):
        a, b = Coord(0, 0), Coord(4, -2)
        path = line(a, b)
        self.assertEqual(len(path), distance(a, b) + 1)
        self.assertEqual(path[0], a)
        self.assertEqual(path[-1], b)

    def test_line_single_point(self):
        self.assertEqual(line(Coord(2, 3), Coord(2, 3)), [Coord(2, 3)])

    def test_line_steps_are_4_adjacent(self):
        path = line(Coord(0, 0), Coord(5, -3))
        for i in range(len(path) - 1):
            self.assertEqual(distance(path[i], path[i + 1]), 1)

    def test_line_straight_axis(self):
        # 純水平線：步距全是 (1, 0)
        path = line(Coord(0, 0), Coord(3, 0))
        self.assertEqual(path, [Coord(0, 0), Coord(1, 0), Coord(2, 0), Coord(3, 0)])

    def test_line_reverse_direction(self):
        path = line(Coord(3, 2), Coord(0, 0))
        self.assertEqual(path[0], Coord(3, 2))
        self.assertEqual(path[-1], Coord(0, 0))
        self.assertEqual(len(path), distance(Coord(3, 2), Coord(0, 0)) + 1)


class TestRingAndSpiral(unittest.TestCase):
    def test_ring_zero_is_center(self):
        self.assertEqual(ring(Coord(7, 2), 0), [Coord(7, 2)])

    def test_ring_size(self):
        for radius in range(1, 6):
            self.assertEqual(len(ring(Coord(0, 0), radius)), 4 * radius)

    def test_ring_all_at_correct_distance(self):
        center = Coord(-1, 2)
        for radius in range(1, 5):
            for c in ring(center, radius):
                self.assertEqual(distance(center, c), radius)

    def test_ring_no_duplicates(self):
        for radius in range(1, 6):
            tiles = ring(Coord(0, 0), radius)
            keys = [(t.x, t.y) for t in tiles]
            self.assertEqual(len(keys), len(set(keys)))

    def test_spiral_total_count(self):
        for n in range(0, 5):
            tiles = list(spiral(Coord(0, 0), n))
            # 1 + 4*1 + 4*2 + ... + 4*n = 1 + 4 * n(n+1)/2 = 1 + 2n(n+1)
            expected = 1 + 2 * n * (n + 1)
            self.assertEqual(len(tiles), expected)

    def test_spiral_no_duplicates(self):
        tiles = list(spiral(Coord(3, -1), 4))
        keys = [(t.x, t.y) for t in tiles]
        self.assertEqual(len(keys), len(set(keys)))

    def test_negative_radius_raises(self):
        with self.assertRaises(ValueError):
            ring(Coord(0, 0), -1)
        with self.assertRaises(ValueError):
            list(spiral(Coord(0, 0), -1))


if __name__ == "__main__":
    unittest.main()
