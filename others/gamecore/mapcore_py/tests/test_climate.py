import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex
from mapcore.map import Hilliness, TerrainType, TileMap
from mapcore.generation.climate import (
    apply_climate,
    base_temperature_celsius,
    compute_hilliness,
    compute_rainfall_mm,
    compute_temperature_celsius,
    latitude_normalized,
    temperature_reduction_at_elevation,
)


class TestLatitudeNormalized(unittest.TestCase):
    def test_center_is_equator(self):
        # H=11 → 中央列 r=5 → 緯度 0
        self.assertAlmostEqual(latitude_normalized(5, 11), 0.0)

    def test_edges_are_polar(self):
        self.assertAlmostEqual(latitude_normalized(0, 11), 1.0)
        self.assertAlmostEqual(latitude_normalized(10, 11), 1.0)

    def test_symmetric(self):
        self.assertAlmostEqual(latitude_normalized(2, 11), latitude_normalized(8, 11))


class TestTemperatureCurve(unittest.TestCase):
    def test_equator_warm(self):
        # 對齊 AvgTempByLatitudeCurve (0, 30°C)
        self.assertAlmostEqual(base_temperature_celsius(0.0), 30.0)

    def test_polar_cold(self):
        self.assertAlmostEqual(base_temperature_celsius(1.0), -37.0)

    def test_monotonic_decreasing(self):
        prev = base_temperature_celsius(0.0)
        for lat in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]:
            cur = base_temperature_celsius(lat)
            self.assertLessEqual(cur, prev)
            prev = cur

    def test_elevation_reduces_temperature(self):
        low = compute_temperature_celsius(5, 11, 0.0)
        high = compute_temperature_celsius(5, 11, 1.0)
        self.assertGreater(low, high)
        # 最高高程應接近 -10°C（赤道 30 - reduction 40 = -10）
        self.assertAlmostEqual(high, -10.0, delta=0.5)

    def test_reduction_zero_below_threshold(self):
        self.assertEqual(temperature_reduction_at_elevation(0.0), 0.0)
        self.assertEqual(temperature_reduction_at_elevation(0.03), 0.0)


class TestRainfallCurve(unittest.TestCase):
    def test_equator_moister_than_polar_for_same_noise(self):
        # 相同 base_noise 在赤道應該比極地多雨
        eq = compute_rainfall_mm(5, 11, 0.5, 0.8)
        polar = compute_rainfall_mm(0, 11, 0.5, 0.8)
        self.assertGreater(eq, polar)

    def test_zero_noise_has_baseline(self):
        # 對齊 RW _rainfall_squash：0 noise 被推到 0.06 → 對應到一個小 baseline 而非 0
        val = compute_rainfall_mm(5, 11, 0.5, 0.0)
        self.assertGreater(val, 0.0)
        self.assertLess(val, 100.0)

    def test_high_elevation_dries(self):
        low = compute_rainfall_mm(5, 11, 0.2, 0.8)
        high = compute_rainfall_mm(5, 11, 1.0, 0.8)
        self.assertGreater(low, high)

    def test_returns_mm_scale(self):
        # 飽和 noise + 赤道 + 低海拔 → 應接近 4000mm 上限
        wet = compute_rainfall_mm(5, 11, 0.0, 1.0)
        self.assertGreater(wet, 1000.0)
        self.assertLess(wet, 4001.0)


class TestHilliness(unittest.TestCase):
    def test_below_sea_level_flat(self):
        # elev <= sea_level → FLAT（陸地化的低地，apply_climate 上層保證水會在這之前被攔下）
        self.assertEqual(compute_hilliness(0.2, sea_level=0.4), Hilliness.FLAT)
        self.assertEqual(compute_hilliness(0.4, sea_level=0.4), Hilliness.FLAT)

    def test_low_elevation_mostly_flat(self):
        # 沒給 rng → 確定回 FLAT
        self.assertEqual(compute_hilliness(0.5, sea_level=0.4, hill_threshold=0.7), Hilliness.FLAT)

    def test_high_elevation_impassable(self):
        self.assertEqual(
            compute_hilliness(0.98, sea_level=0.4, mountain_threshold=0.85, impassable_threshold=0.95),
            Hilliness.IMPASSABLE,
        )

    def test_ladder_ordering(self):
        # 高度遞增應該對應到 hilliness 等級非遞減
        elevs = [0.45, 0.55, 0.65, 0.75, 0.88, 0.97]
        values = [compute_hilliness(e, rng=None) for e in elevs]
        ints = [int(v) for v in values]
        self.assertEqual(ints, sorted(ints))


class TestApplyClimate(unittest.TestCase):
    def _build(self, W=8, H=8):
        tm = TileMap(W, H, default_terrain=TerrainType.PLAINS)
        for q in range(W):
            tm.set_terrain(Hex(q, 0), TerrainType.OCEAN)
        heightmap = [[0.5] * W for _ in range(H)]
        rainfall_noise = [[0.6] * W for _ in range(H)]
        return tm, heightmap, rainfall_noise

    def test_water_gets_flat_hilliness(self):
        tm, hm, mn = self._build()
        apply_climate(tm, hm, mn, seed=0)
        for q in range(tm.width):
            self.assertEqual(tm.get(Hex(q, 0)).hilliness, Hilliness.FLAT)

    def test_returns_correct_shapes(self):
        tm, hm, mn = self._build()
        temp, rain = apply_climate(tm, hm, mn, seed=0)
        self.assertEqual(len(temp), tm.height)
        self.assertEqual(len(temp[0]), tm.width)
        self.assertEqual(len(rain), tm.height)
        self.assertEqual(len(rain[0]), tm.width)

    def test_deterministic(self):
        tm_a, hm_a, mn_a = self._build()
        tm_b, hm_b, mn_b = self._build()
        ta, ra = apply_climate(tm_a, hm_a, mn_a, seed=42)
        tb, rb = apply_climate(tm_b, hm_b, mn_b, seed=42)
        self.assertEqual(ta, tb)
        self.assertEqual(ra, rb)
        for q in range(tm_a.width):
            for r in range(tm_a.height):
                self.assertEqual(tm_a.get(Hex(q, r)).hilliness, tm_b.get(Hex(q, r)).hilliness)

    def test_shape_validation(self):
        tm = TileMap(4, 4, default_terrain=TerrainType.PLAINS)
        with self.assertRaises(ValueError):
            apply_climate(tm, [[0.5] * 3 for _ in range(4)], [[0.5] * 4 for _ in range(4)])
        with self.assertRaises(ValueError):
            apply_climate(tm, [[0.5] * 4 for _ in range(4)], [[0.5] * 3 for _ in range(3)])


if __name__ == "__main__":
    unittest.main()
