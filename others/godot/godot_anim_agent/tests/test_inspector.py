"""anim_inspector — parse_tres / 各 cmd 的確定性測試。"""

import sys
import math
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_inspector import (
    parse_tres, _extract_tracks, _find_anim,
    cmd_summary, cmd_tracks, cmd_set_key, cmd_scale_time, cmd_offset, cmd_scale_value,
)
from tests.helpers import FIGHTER, copy_fixture, capture


def _load(path):
    return parse_tres(Path(path).read_text(encoding="utf-8"))


class TestParseTres(unittest.TestCase):
    def test_header_type(self):
        d = _load(FIGHTER)
        self.assertEqual(d["header"]["type"], "AnimationLibrary")

    def test_four_animations(self):
        d = _load(FIGHTER)
        anims = [r for r in d["sub_resources"] if r["type"] == "Animation"]
        names = {a["props"].get("resource_name", "").strip('"') for a in anims}
        self.assertEqual(names, {"idle", "punch", "guard", "step_in"})

    def test_idle_length(self):
        d = _load(FIGHTER)
        idle = _find_anim(d, "idle")
        self.assertIsNotNone(idle)
        self.assertAlmostEqual(float(idle["props"]["length"]), 1.2)

    def test_punch_track_count(self):
        d = _load(FIGHTER)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        self.assertEqual(len(tracks), 4)  # UpperArm, ForeArm, position, method

    def test_punch_method_track(self):
        d = _load(FIGHTER)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        method_tracks = [t for t in tracks if t["type"] == "method"]
        self.assertEqual(len(method_tracks), 1)
        self.assertAlmostEqual(method_tracks[0]["times"][0], 0.3)

    def test_step_in_vector2_track(self):
        d = _load(FIGHTER)
        si = _find_anim(d, "step_in")
        tracks = _extract_tracks(si)
        pos = next(t for t in tracks if t["path"] == ".:position")
        self.assertEqual(pos["vtype"], "Vector2")
        self.assertEqual(len(pos["comps"]), 2)
        # 最後一個 key = Vector2(24, 0)
        self.assertAlmostEqual(pos["comps"][-1][0], 24.0)
        self.assertAlmostEqual(pos["comps"][-1][1], 0.0)


class TestCmdSummary(unittest.TestCase):
    def test_lists_all_animations(self):
        with capture() as out:
            cmd_summary(str(FIGHTER))
        text = out.getvalue()
        for name in ("idle", "punch", "guard", "step_in"):
            self.assertIn(name, text)

    def test_shows_length(self):
        with capture() as out:
            cmd_summary(str(FIGHTER))
        self.assertIn("1.2", out.getvalue())  # idle length


class TestCmdTracks(unittest.TestCase):
    def test_punch_tracks_output(self):
        with capture() as out:
            cmd_tracks(str(FIGHTER), "punch")
        text = out.getvalue()
        self.assertIn("Armature/UpperArm:rotation", text)
        self.assertIn("Armature/ForeArm:rotation", text)
        self.assertIn(".:position", text)

    def test_idle_values(self):
        with capture() as out:
            cmd_tracks(str(FIGHTER), "idle")
        text = out.getvalue()
        self.assertIn("Armature/Torso:rotation", text)
        self.assertIn("0.05", text)  # peak value at t=0.6


class TestCmdSetKey(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_update_existing_key(self):
        cmd_set_key(self.f, "idle", "Armature/Torso:rotation", "0.6", "0.1")
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        tracks = _extract_tracks(idle)
        torso = next(t for t in tracks if t["path"] == "Armature/Torso:rotation")
        idx = next(i for i, t in enumerate(torso["times"]) if abs(t - 0.6) < 1e-5)
        self.assertAlmostEqual(torso["comps"][idx][0], 0.1)

    def test_insert_new_key_sorted(self):
        cmd_set_key(self.f, "idle", "Armature/Torso:rotation", "0.3", "0.03")
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        tracks = _extract_tracks(idle)
        torso = next(t for t in tracks if t["path"] == "Armature/Torso:rotation")
        self.assertEqual(len(torso["times"]), 4)  # 3 → 4
        # 時間應保持遞增
        for i in range(len(torso["times"]) - 1):
            self.assertLess(torso["times"][i], torso["times"][i + 1])

    def test_insert_vector2_key(self):
        cmd_set_key(self.f, "step_in", ".:position", "0.2", "Vector2(10, 0)")
        d = _load(self.f)
        si = _find_anim(d, "step_in")
        tracks = _extract_tracks(si)
        pos = next(t for t in tracks if t["path"] == ".:position")
        self.assertEqual(len(pos["times"]), 3)  # 2 → 3
        idx = next(i for i, t in enumerate(pos["times"]) if abs(t - 0.2) < 1e-5)
        self.assertAlmostEqual(pos["comps"][idx][0], 10.0)


class TestCmdScaleTime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_scales_length(self):
        cmd_scale_time(self.f, "punch", "0.5")
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        self.assertAlmostEqual(float(punch["props"]["length"]), 0.3, places=5)

    def test_scales_track_times(self):
        cmd_scale_time(self.f, "punch", "2.0")
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        # 原本最後 key 在 0.6 → 應為 1.2
        self.assertAlmostEqual(upper["times"][-1], 1.2, places=5)

    def test_does_not_affect_other_animations(self):
        cmd_scale_time(self.f, "punch", "0.5")
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        self.assertAlmostEqual(float(idle["props"]["length"]), 1.2)


class TestCmdOffset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_float_offset(self):
        cmd_offset(self.f, "idle", "Armature/Torso:rotation", "0.1")
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        tracks = _extract_tracks(idle)
        torso = next(t for t in tracks if t["path"] == "Armature/Torso:rotation")
        # 原來 [0.0, 0.05, 0.0] → [0.1, 0.15, 0.1]
        self.assertAlmostEqual(torso["comps"][0][0], 0.1)
        self.assertAlmostEqual(torso["comps"][1][0], 0.15)

    def test_vector2_offset(self):
        cmd_offset(self.f, "step_in", ".:position", "Vector2(5, 2)")
        d = _load(self.f)
        si = _find_anim(d, "step_in")
        tracks = _extract_tracks(si)
        pos = next(t for t in tracks if t["path"] == ".:position")
        # 原來 [Vector2(0,0), Vector2(24,0)] → [Vector2(5,2), Vector2(29,2)]
        self.assertAlmostEqual(pos["comps"][0][0], 5.0)
        self.assertAlmostEqual(pos["comps"][0][1], 2.0)
        self.assertAlmostEqual(pos["comps"][-1][0], 29.0)


class TestCmdScaleValue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_scale_float_track(self):
        cmd_scale_value(self.f, "punch", "Armature/UpperArm:rotation", "2.0")
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        # 原 [-0.4, 1.6] at idx 1,2 → [-0.8, 3.2]
        idx1 = next(i for i, t in enumerate(upper["times"]) if abs(t - 0.15) < 1e-5)
        self.assertAlmostEqual(upper["comps"][idx1][0], -0.8)

    def test_does_not_change_times(self):
        original_times = list(_extract_tracks(_find_anim(_load(self.f), "punch"))[0]["times"])
        cmd_scale_value(self.f, "punch", "Armature/UpperArm:rotation", "2.0")
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        tracks = _extract_tracks(punch)
        upper = next(t for t in tracks if t["path"] == "Armature/UpperArm:rotation")
        for a, b in zip(original_times, upper["times"]):
            self.assertAlmostEqual(a, b)


if __name__ == "__main__":
    unittest.main()
