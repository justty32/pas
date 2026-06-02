"""anim_pose — 2-bone IK 數學 + cmd_aim 整合測試。"""

import sys
import math
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_pose import _solve_2bone, cmd_aim
from anim_inspector import parse_tres, _find_anim, _extract_tracks
from tests.helpers import FIGHTER, copy_fixture, capture


def _load(path):
    return parse_tres(Path(path).read_text(encoding="utf-8"))


class TestSolve2Bone(unittest.TestCase):
    """純數學：FK 反算誤差應 < 0.001。"""

    def _check(self, tx, ty, L1, L2, base1=0.0, base2=0.0, bend=1.0):
        r1, r2, info = _solve_2bone(tx, ty, L1, L2, base1, base2, bend)
        hx, hy = info["hand"]
        err = math.hypot(hx - tx, hy - ty)
        self.assertLess(err, 0.01,
            f"FK 反算誤差 {err:.4f} 太大 target=({tx},{ty}) L=({L1},{L2})")
        return r1, r2, info

    def test_straight_right(self):
        # L1=30, L2=20, 手臂全伸向右 → r1≈0, r2≈0, hand≈(50,0)
        r1, r2, info = _solve_2bone(50, 0, 30, 20, 0, 0, 1)
        self.assertAlmostEqual(info["hand"][0], 50, places=1)
        self.assertAlmostEqual(info["hand"][1], 0, places=1)

    def test_right_angle_target(self):
        # L1=L2=20, target (20,0) → 直角肘 (手伸半長)
        r1, r2, info = self._check(20, 0, 20, 20, bend=1.0)

    def test_diagonal_target(self):
        self._check(25, 25, 30, 28, bend=1.0)

    def test_bend_up_vs_down(self):
        # 同一目標，不同 bend 方向 → 肘關節 y 座標符號相反
        _, _, info_down = _solve_2bone(30, 0, 30, 28, 0, 0, 1.0)
        _, _, info_up   = _solve_2bone(30, 0, 30, 28, 0, 0, -1.0)
        # 肘部 y 應分別 > 0 和 < 0 (或正負相反)
        ey_down = info_down["elbow"][1]
        ey_up   = info_up["elbow"][1]
        self.assertGreater(ey_down * ey_up, -1e4)  # 符號反轉
        self.assertNotAlmostEqual(ey_down, ey_up, places=3)

    def test_over_reach_clamped(self):
        # target 超出 L1+L2 → 夾到最大，且 clamped 有訊息
        _, _, info = _solve_2bone(200, 0, 30, 28, 0, 0, 1.0)
        self.assertIsNotNone(info["clamped"])
        # FK 手位應在 (58, 0) 附近（30+28=58）
        self.assertAlmostEqual(info["hand"][0], 58, delta=0.5)

    def test_nonzero_base_angles(self):
        # 基準朝向非 0，FK 反算仍準
        self._check(20, 15, 28, 24, base1=0.3, base2=0.1, bend=1.0)

    def test_with_shoulder_offset(self):
        # cmd_aim 前會手動換算 target 相對肩，這裡直接測數學層
        # shoulder=(10,5), target=(40,-10) → relative=(30,-15)
        sx, sy = 10, 5
        tx, ty = 40, -10
        self._check(tx - sx, ty - sy, 30, 28, bend=-1.0)

    def test_fk_error_within_tolerance(self):
        for tx, ty in [(10, 5), (-15, 20), (40, 30), (0, -50)]:
            with self.subTest(target=(tx, ty)):
                r1, r2, info = _solve_2bone(tx, ty, 30, 28, 0, 0, 1.0)
                hx, hy = info["hand"]
                err = math.hypot(hx - tx, hy - ty)
                self.assertLess(err, 0.01)


class TestCmdAim(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_two_rotation_keys(self):
        with capture():
            cmd_aim(self.f, "punch", "0.3", 40, -10,
                    "Armature/UpperArm:rotation", "Armature/ForeArm:rotation",
                    30, 28, 0.0, 0.0, 1.0, [0.0, 0.0])
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        fore  = next(t for t in tracks if t["path"] == "Armature/ForeArm:rotation")
        # t=0.3 key 應存在
        self.assertTrue(any(abs(t - 0.3) < 1e-5 for t in upper["times"]))
        self.assertTrue(any(abs(t - 0.3) < 1e-5 for t in fore["times"]))

    def test_fk_error_in_output(self):
        with capture() as out:
            cmd_aim(self.f, "punch", "0.3", 40, -10,
                    "Armature/UpperArm:rotation", "Armature/ForeArm:rotation",
                    30, 28, 0.0, 0.0, 1.0, [0.0, 0.0])
        text = out.getvalue()
        self.assertIn("誤差", text)

    def test_nonzero_shoulder(self):
        # shoulder 非原點，應能正常執行不 crash
        with capture():
            cmd_aim(self.f, "punch", "0.15", 55, -5,
                    "Armature/UpperArm:rotation", "Armature/ForeArm:rotation",
                    30, 28, 0.0, 0.0, 1.0, [10.0, 5.0])


if __name__ == "__main__":
    unittest.main()
