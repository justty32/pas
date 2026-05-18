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

    def test_ridge_mode_invalid(self):
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, seed=0, ridge_weight=0.5, ridge_mode="bogus")

    def test_num_plates_too_small(self):
        with self.assertRaises(ValueError):
            generate_heightmap(
                10, 10, seed=0, ridge_weight=0.5, ridge_mode="plates", num_plates=1
            )

    def test_plate_boundary_width_must_be_positive(self):
        with self.assertRaises(ValueError):
            generate_heightmap(
                10, 10, seed=0, ridge_weight=0.5,
                ridge_mode="plates", plate_boundary_width=0.0,
            )


class TestPlateRidge(unittest.TestCase):
    """ridge_mode='plates' 把山脊鎖在 Voronoi 邊界帶，山脈長度有限。"""

    def test_plate_mode_in_unit_interval(self):
        hm = generate_heightmap(
            40, 30, seed=42, ridge_weight=1.0,
            ridge_mode="plates", num_plates=8, plate_boundary_width=0.1,
        )
        for row in hm:
            for v in row:
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_plate_mode_deterministic(self):
        kw = dict(seed=7, ridge_weight=0.8, ridge_mode="plates",
                  num_plates=6, plate_boundary_width=0.1)
        a = generate_heightmap(30, 30, **kw)
        b = generate_heightmap(30, 30, **kw)
        self.assertEqual(a, b)

    def test_plate_mode_differs_from_global(self):
        # 同 seed 下，plates 與 global 應產生不同結果（plate field 對山脊空間調制）
        kw = dict(seed=7, ridge_weight=1.0)
        gp = generate_heightmap(30, 30, ridge_mode="plates", num_plates=6, **kw)
        gg = generate_heightmap(30, 30, ridge_mode="global", **kw)
        self.assertNotEqual(gp, gg)

    def test_plate_mode_no_ridge_when_weight_zero(self):
        # ridge_weight=0 時不該觸發 plate field 計算路徑差異：
        # 兩種模式輸出必須完全一致（純 fBm）
        kw = dict(seed=3, ridge_weight=0.0)
        a = generate_heightmap(20, 20, ridge_mode="plates", **kw)
        b = generate_heightmap(20, 20, ridge_mode="global", **kw)
        self.assertEqual(a, b)

    def test_ridge_power_invalid(self):
        with self.assertRaises(ValueError):
            generate_heightmap(10, 10, seed=0, ridge_weight=0.5, ridge_power=0.0)

    def test_ridge_multifractal_gain_negative(self):
        with self.assertRaises(ValueError):
            generate_heightmap(
                10, 10, seed=0, ridge_weight=0.5, ridge_multifractal_gain=-0.5
            )

    def test_ridge_power_sharpens(self):
        # power=4 對折疊取 4 次方，把 [0,1] 值大幅往 0 推（fold⁴ 均值≈0.2 vs fold¹≈0.5），
        # 整體高度均值應顯著下降。取 ridge_weight=1.0 全套用、無多分形，純比較銳化效果。
        kw = dict(seed=11, ridge_weight=1.0, ridge_mode="plates",
                  num_plates=6, plate_boundary_width=0.1,
                  ridge_multifractal_gain=0.0)
        flat = generate_heightmap(40, 40, ridge_power=1.0, **kw)
        sharp = generate_heightmap(40, 40, ridge_power=4.0, **kw)

        def mean(grid):
            n = 0
            s = 0.0
            for row in grid:
                for v in row:
                    s += v
                    n += 1
            return s / n

        self.assertGreater(mean(flat), mean(sharp))

    def test_multifractal_carry_differs(self):
        # gain>0 vs gain=0 應產生不同輸出（多分形 carry 才會有差）
        kw = dict(seed=5, ridge_weight=1.0, ridge_mode="plates",
                  num_plates=6, plate_boundary_width=0.1, ridge_power=2.0)
        no_mf = generate_heightmap(30, 30, ridge_multifractal_gain=0.0, **kw)
        mf = generate_heightmap(30, 30, ridge_multifractal_gain=2.0, **kw)
        self.assertNotEqual(no_mf, mf)

    def test_plate_mode_localizes_ridges(self):
        # 局部化驗證：plates 模式下，地圖內陸有大面積接近 fBm（低 ridge 貢獻），
        # 而 global 模式下所有 tile 都受 ridge fold 影響。
        # 取「ridge_weight=1 與 ridge_weight=0 的差」絕對值最大值作指標：
        # plates 應產生大量接近 0 的 tile（板塊內部），global 不會。
        seed = 11
        w, h = 50, 50
        base = generate_heightmap(w, h, seed=seed, ridge_weight=0.0)
        plates = generate_heightmap(
            w, h, seed=seed, ridge_weight=1.0,
            ridge_mode="plates", num_plates=6, plate_boundary_width=0.05,
        )
        glob = generate_heightmap(
            w, h, seed=seed, ridge_weight=1.0, ridge_mode="global",
        )

        def near_base_ratio(grid):
            # 比例：本格與純 fBm 相差不到 0.02 的 tile 數
            n = 0
            for r in range(h):
                for q in range(w):
                    if abs(grid[r][q] - base[r][q]) < 0.02:
                        n += 1
            return n / (w * h)

        # plates：板塊內部佔多數，"接近 fBm" 的格子應佔相當比例（>20%）
        # global：每格都被 ridge 改動，幾乎沒有接近 fBm 的格子（<10%）
        self.assertGreater(near_base_ratio(plates), 0.20)
        self.assertLess(near_base_ratio(glob), 0.10)


if __name__ == "__main__":
    unittest.main()
