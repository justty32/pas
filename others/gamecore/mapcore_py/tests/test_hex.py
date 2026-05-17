import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import (
    DIRECTIONS,
    Hex,
    direction,
    distance,
    hex_round,
    line,
    ring,
    spiral,
)


class TestHexBasics(unittest.TestCase):
    def test_s_axis(self):
        self.assertEqual(Hex(2, -5).s, 3)
        self.assertEqual(Hex(0, 0).s, 0)

    def test_equality_by_value(self):
        self.assertEqual(Hex(1, 2), Hex(1, 2))
        self.assertNotEqual(Hex(1, 2), Hex(1, 3))

    def test_unhashable(self):
        # 刻意設計：對齊未來 C++ 2D array 方案，禁止把 Hex 當 dict/set 鍵。
        self.assertIsNone(Hex.__hash__)
        with self.assertRaises(TypeError):
            {Hex(0, 0)}

    def test_mutable_fields(self):
        h = Hex(0, 0)
        h.q = 5
        self.assertEqual(h, Hex(5, 0))

    def test_arithmetic(self):
        self.assertEqual(Hex(1, 2) + Hex(3, 4), Hex(4, 6))
        self.assertEqual(Hex(5, 5) - Hex(2, 1), Hex(3, 4))
        self.assertEqual(Hex(1, -1) * 3, Hex(3, -3))


class TestDirectionsAndNeighbors(unittest.TestCase):
    def test_six_directions_unique(self):
        keys = [(d.q, d.r) for d in DIRECTIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_directions_sum_to_zero(self):
        total = Hex(0, 0)
        for d in DIRECTIONS:
            total = total + d
        self.assertEqual(total, Hex(0, 0))

    def test_direction_wraps_modulo_6(self):
        self.assertEqual(direction(7), DIRECTIONS[1])
        self.assertEqual(direction(-1), DIRECTIONS[5])

    def test_neighbors(self):
        center = Hex(5, -3)
        neighbors = center.neighbors()
        self.assertEqual(len(neighbors), 6)
        for n in neighbors:
            self.assertEqual(distance(center, n), 1)


class TestDistance(unittest.TestCase):
    def test_self_distance_zero(self):
        self.assertEqual(distance(Hex(7, -4), Hex(7, -4)), 0)

    def test_neighbor_distance_one(self):
        for d in DIRECTIONS:
            self.assertEqual(distance(Hex(0, 0), d), 1)

    def test_known_distances(self):
        self.assertEqual(distance(Hex(0, 0), Hex(3, 0)), 3)
        self.assertEqual(distance(Hex(0, 0), Hex(3, -3)), 3)
        self.assertEqual(distance(Hex(-2, 1), Hex(2, -1)), 4)


class TestHexRound(unittest.TestCase):
    def test_exact_integers(self):
        self.assertEqual(hex_round(3.0, -2.0), Hex(3, -2))

    def test_near_center_snaps(self):
        self.assertEqual(hex_round(0.1, 0.1), Hex(0, 0))

    def test_round_preserves_cube_constraint(self):
        for qf, rf in [(1.4, -0.7), (-2.6, 1.3), (0.5, 0.4)]:
            h = hex_round(qf, rf)
            self.assertEqual(h.q + h.r + h.s, 0)


class TestLine(unittest.TestCase):
    def test_line_length(self):
        a, b = Hex(0, 0), Hex(4, -2)
        path = line(a, b)
        self.assertEqual(len(path), distance(a, b) + 1)
        self.assertEqual(path[0], a)
        self.assertEqual(path[-1], b)

    def test_line_single_point(self):
        self.assertEqual(line(Hex(2, 3), Hex(2, 3)), [Hex(2, 3)])

    def test_line_steps_are_adjacent(self):
        path = line(Hex(0, 0), Hex(5, -3))
        for i in range(len(path) - 1):
            self.assertEqual(distance(path[i], path[i + 1]), 1)


class TestRingAndSpiral(unittest.TestCase):
    def test_ring_zero_is_center(self):
        self.assertEqual(ring(Hex(7, 2), 0), [Hex(7, 2)])

    def test_ring_size(self):
        for radius in range(1, 6):
            self.assertEqual(len(ring(Hex(0, 0), radius)), 6 * radius)

    def test_ring_all_at_correct_distance(self):
        center = Hex(-1, 2)
        for radius in range(1, 5):
            for h in ring(center, radius):
                self.assertEqual(distance(center, h), radius)

    def test_spiral_total_count(self):
        for n in range(0, 5):
            tiles = list(spiral(Hex(0, 0), n))
            expected = 1 + 3 * n * (n + 1)
            self.assertEqual(len(tiles), expected)

    def test_spiral_no_duplicates(self):
        tiles = list(spiral(Hex(3, -1), 4))
        keys = [(t.q, t.r) for t in tiles]
        self.assertEqual(len(keys), len(set(keys)))

    def test_negative_radius_raises(self):
        with self.assertRaises(ValueError):
            ring(Hex(0, 0), -1)
        with self.assertRaises(ValueError):
            list(spiral(Hex(0, 0), -1))


if __name__ == "__main__":
    unittest.main()
