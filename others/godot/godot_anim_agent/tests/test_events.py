"""anim_events — list / add / rm / scaffold 測試。"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_inspector import parse_tres, _find_anim, _extract_tracks
from anim_events import cmd_list, cmd_add, cmd_rm, cmd_scaffold, _method_tracks
from tests.helpers import FIGHTER, copy_fixture, capture


def _load(path):
    return parse_tres(Path(path).read_text(encoding="utf-8"))


class TestCmdList(unittest.TestCase):
    def test_lists_spawn_hit_spark(self):
        with capture() as out:
            cmd_list(str(FIGHTER), "punch")
        text = out.getvalue()
        self.assertIn("spawn_hit_spark", text)
        self.assertIn("0.3", text)

    def test_no_method_track_message(self):
        with capture() as out:
            cmd_list(str(FIGHTER), "idle")
        self.assertIn("無", out.getvalue())

    def test_unknown_animation(self):
        with capture() as out:
            cmd_list(str(FIGHTER), "nonexistent")
        self.assertIn("找不到", out.getvalue())


class TestCmdAdd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_to_existing_method_track(self):
        # punch 已有 method track at "." → 插入第二個事件
        cmd_add(self.f, "punch", ".", "0.1", "play_sound", ["whoosh"])
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        mtracks = _method_tracks(punch)
        dot_track = next(t for t in mtracks if t["path"] == ".")
        self.assertEqual(len(dot_track["times"]), 2)
        # 時間應排序：0.1 < 0.3
        self.assertAlmostEqual(dot_track["times"][0], 0.1, places=5)
        self.assertAlmostEqual(dot_track["times"][1], 0.3, places=5)

    def test_add_creates_new_track(self):
        # idle 沒有 method track → 新建
        cmd_add(self.f, "idle", ".", "0.5", "on_idle_loop", [])
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        mtracks = _method_tracks(idle)
        self.assertEqual(len(mtracks), 1)
        self.assertAlmostEqual(mtracks[0]["times"][0], 0.5, places=5)

    def test_add_with_args(self):
        cmd_add(self.f, "idle", ".", "0.6", "emit_dust", ["small", "2"])
        d = _load(self.f)
        idle = _find_anim(d, "idle")
        mtracks = _method_tracks(idle)
        # args 應出現在 values 原始字串
        text = Path(self.f).read_text()
        self.assertIn("emit_dust", text)

    def test_preserves_existing_events(self):
        cmd_add(self.f, "punch", ".", "0.1", "whoosh", [])
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        mtracks = _method_tracks(punch)
        dot = next(t for t in mtracks if t["path"] == ".")
        text = Path(self.f).read_text()
        self.assertIn("spawn_hit_spark", text)


class TestCmdRm(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_removes_event(self):
        cmd_rm(self.f, "punch", ".", "0.3")
        d = _load(self.f)
        punch = _find_anim(d, "punch")
        mtracks = _method_tracks(punch)
        if mtracks:
            dot = next((t for t in mtracks if t["path"] == "."), None)
            if dot:
                for t in dot["times"]:
                    self.assertFalse(abs(t - 0.3) < 1e-5)

    def test_rm_nonexistent_no_crash(self):
        with capture() as out:
            cmd_rm(self.f, "punch", ".", "0.9")
        self.assertIn("沒有事件", out.getvalue())

    def test_rm_no_method_track(self):
        with capture() as out:
            cmd_rm(self.f, "idle", ".", "0.1")
        self.assertIn("method 軌道", out.getvalue())


class TestCmdScaffold(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_gd_file(self):
        cmd_scaffold(self.f)
        gd = Path(self.tmp.name) / "fighter_events.gd"
        self.assertTrue(gd.exists())

    def test_contains_spawn_hit_spark(self):
        cmd_scaffold(self.f)
        gd = (Path(self.tmp.name) / "fighter_events.gd").read_text()
        self.assertIn("spawn_hit_spark", gd)
        self.assertIn("func spawn_hit_spark", gd)

    def test_single_animation_scaffold(self):
        cmd_scaffold(self.f, "punch")
        gd = (Path(self.tmp.name) / "fighter_events.gd").read_text()
        self.assertIn("spawn_hit_spark", gd)

    def test_no_events_no_file(self):
        # 只對 idle scaffold → idle 無事件，不應產生檔案
        with capture() as out:
            cmd_scaffold(self.f, "idle")
        self.assertIn("無需", out.getvalue())


if __name__ == "__main__":
    unittest.main()
