import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.heightmap import generate_heightmap


class TestShape(unittest.TestCase):
    def test_dimensions(self):
        hm = generate_heightmap(20, 15, seed=0)
        self.assertEqual(len(hm), 15)
        for row in hm:
            self.assertEqual(len(row), 20)

    def test_small_map(self):
        hm = generate_heightmap(1, 1, seed=0)
        self.assertEqual(len(hm), 1)
        self.assertEqual(len(hm[0]), 1)
        self.assertTrue(0.0 <= hm[0][0] <= 1.0)

    def test_invalid_dims_raise(self):
        with self.assertRaises(ValueError):
            generate_heightmap(0, 5)
        with self.assertRaises(ValueError):
            generate_heightmap(5, -1)


class TestValueRange(unittest.TestCase):
    def test_values_within_unit_interval(self):
        hm = generate_heightmap(40, 30, seed=42, octaves=5)
        for row in hm:
            for v in row:
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_not_all_same(self):
        # 多 octave 不該整張地圖塌成同一個值。
        hm = generate_heightmap(20, 20, seed=7)
        first = hm[0][0]
        self.assertFalse(all(v == first for row in hm for v in row))


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_result(self):
        a = generate_heightmap(15, 10, seed=123)
        b = generate_heightmap(15, 10, seed=123)
        self.assertEqual(a, b)

    def test_different_seed_different_result(self):
        a = generate_heightmap(15, 10, seed=1)
        b = generate_heightmap(15, 10, seed=2)
        self.assertNotEqual(a, b)

    def test_seed_none_is_nondeterministic(self):
        # 不固定種子時兩次理當不同 (機率上）
        a = generate_heightmap(10, 10, seed=None)
        b = generate_heightmap(10, 10, seed=None)
        self.assertNotEqual(a, b)


class TestParameterValidation(unittest.TestCase):
    def test_octaves_must_be_positive(self):
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, octaves=0)

    def test_persistence_range(self):
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, persistence=0.0)
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, persistence=1.5)

    def test_base_frequency_min(self):
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, base_frequency=0)


if __name__ == "__main__":
    unittest.main()
