"""anim_compose — concat / check-seams / fix-seam 測試。"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_inspector import parse_tres, _extract_tracks, _find_anim
from anim_compose import cmd_concat, cmd_check_seams, cmd_fix_seam
from tests.helpers import FIGHTER, copy_fixture, capture


def _load(path):
    return parse_tres(Path(path).read_text(encoding="utf-8"))


class TestCmdConcat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_basic_concat_creates_animation(self):
        cmd_concat(self.f, "idle_guard", ["idle", "guard"])
        d = _load(self.f)
        self.assertIsNotNone(_find_anim(d, "idle_guard"))

    def test_concat_correct_length(self):
        # idle=1.2s + guard=0.5s = 1.7s
        cmd_concat(self.f, "idle_guard", ["idle", "guard"])
        d = _load(self.f)
        anim = _find_anim(d, "idle_guard")
        self.assertAlmostEqual(float(anim["props"]["length"]), 1.7, places=5)

    def test_concat_with_blend_shorter_length(self):
        # blend 0.2s → 1.2 + 0.5 - 0.2 = 1.5s
        cmd_concat(self.f, "blended", ["idle", "guard"], blend=0.2)
        d = _load(self.f)
        anim = _find_anim(d, "blended")
        self.assertAlmostEqual(float(anim["props"]["length"]), 1.5, places=5)

    def test_concat_merges_tracks(self):
        # idle 有 Torso, guard 有 UpperArm+ForeArm → 合併後應都有
        cmd_concat(self.f, "idle_guard", ["idle", "guard"])
        d = _load(self.f)
        anim = _find_anim(d, "idle_guard")
        tracks = _extract_tracks(anim)
        paths = {t["path"] for t in tracks}
        self.assertIn("Armature/Torso:rotation", paths)
        self.assertIn("Armature/UpperArm:rotation", paths)
        self.assertIn("Armature/ForeArm:rotation", paths)

    def test_concat_torso_keys_offset(self):
        # idle 的 Torso track 在 t=0,0.6,1.2；concat idle+guard 後 Torso keys 應在 0,0.6,1.2
        # (guard 沒有 Torso track，所以只有 idle 段)
        cmd_concat(self.f, "ig", ["idle", "guard"])
        d = _load(self.f)
        anim = _find_anim(d, "ig")
        tracks = _extract_tracks(anim)
        torso = next(t for t in tracks if t["path"] == "Armature/Torso:rotation")
        self.assertAlmostEqual(torso["times"][0], 0.0)
        self.assertAlmostEqual(torso["times"][-1], 1.2, places=5)

    def test_concat_guard_keys_shifted(self):
        # idle=1.2s, guard UpperArm starts at 0 → after concat should start at 1.2
        cmd_concat(self.f, "ig", ["idle", "guard"])
        d = _load(self.f)
        anim = _find_anim(d, "ig")
        tracks = _extract_tracks(anim)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        # guard UpperArm 原 t=[0, 0.25, 0.5]，shift +1.2 → [1.2, 1.45, 1.7]
        self.assertAlmostEqual(upper["times"][0], 1.2, places=5)

    def test_concat_duplicate_name_rejected(self):
        cmd_concat(self.f, "idle_guard", ["idle", "guard"])
        with capture() as out:
            cmd_concat(self.f, "idle_guard", ["idle", "guard"])
        self.assertIn("已存在", out.getvalue())
        # 確保只有一個 sub_resource 有此名（resource_name 行只應出現一次）
        text = Path(self.f).read_text()
        self.assertEqual(text.count('resource_name = "idle_guard"'), 1)

    def test_root_motion_accumulates(self):
        # step_in(0→24) + punch(0→12→0) with root-motion
        # 期望 punch.position 起點從 Vector2(0,0) 偏移到 Vector2(24,0)
        cmd_concat(self.f, "advance_punch", ["step_in", "punch"],
                   root_motion_path=".:position")
        d = _load(self.f)
        anim = _find_anim(d, "advance_punch")
        tracks = _extract_tracks(anim)
        pos = next(t for t in tracks if t["path"] == ".:position")
        # step_in 段最後 key at t=0.4 = Vector2(24,0)
        # punch 段第一 key 原本 Vector2(0,0) → 應累加成 Vector2(24,0)
        punch_start_idx = next(i for i, t in enumerate(pos["times"]) if t > 0.4 - 1e-5)
        self.assertAlmostEqual(pos["comps"][punch_start_idx][0], 24.0, places=4)

    def test_three_clips(self):
        cmd_concat(self.f, "triple", ["idle", "guard", "punch"])
        d = _load(self.f)
        anim = _find_anim(d, "triple")
        # idle=1.2 + guard=0.5 + punch=0.6 = 2.3
        self.assertAlmostEqual(float(anim["props"]["length"]), 2.3, places=5)


class TestCmdCheckSeams(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))
        cmd_concat(self.f, "combo", ["guard", "punch"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_runs_without_crash(self):
        with capture() as out:
            cmd_check_seams(self.f, "combo")
        self.assertIn("combo", out.getvalue())

    def test_specific_timepoint(self):
        with capture() as out:
            cmd_check_seams(self.f, "combo", at_times=[0.5])
        self.assertIn("0.5", out.getvalue())

    def test_clean_animation_no_issues(self):
        # idle 自身 (無組合)，全軌道應無突變
        with capture() as out:
            cmd_check_seams(self.f, "idle")
        self.assertIn("✓", out.getvalue())


class TestCmdFixSeam(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))
        # concat idle+punch: idle 沒有 UpperArm track → 組合後 UpperArm 只在 punch 段
        cmd_concat(self.f, "combo", ["idle", "punch"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_adds_head_key(self):
        # UpperArm 在 combo 中只有 punch 段（從 t=1.2 起）→ t=0 應補 rest=0.0
        cmd_fix_seam(self.f, "combo",
                     [("Armature/UpperArm:rotation", "0.0")])
        d = _load(self.f)
        anim = _find_anim(d, "combo")
        tracks = _extract_tracks(anim)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        # 頭部應有 t=0 的 key
        self.assertAlmostEqual(upper["times"][0], 0.0, places=5)
        self.assertAlmostEqual(upper["comps"][0][0], 0.0, places=5)

    def test_no_op_on_full_coverage(self):
        # idle 本身的 Torso 軌道已覆蓋 [0, 1.2]（即 length），fix-seam 不應增加 key
        d_before = _load(self.f)
        torso_before = next(
            t for t in _extract_tracks(_find_anim(d_before, "idle"))
            if t["path"] == "Armature/Torso:rotation"
        )
        n_before = len(torso_before["times"])
        cmd_fix_seam(self.f, "idle", [("Armature/Torso:rotation", "0.0")])
        d_after = _load(self.f)
        torso_after = next(
            t for t in _extract_tracks(_find_anim(d_after, "idle"))
            if t["path"] == "Armature/Torso:rotation"
        )
        self.assertEqual(len(torso_after["times"]), n_before)


if __name__ == "__main__":
    unittest.main()
