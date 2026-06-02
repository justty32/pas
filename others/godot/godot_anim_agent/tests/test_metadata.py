"""anim_metadata — init / set-tag / rm-tag / compat 測試。"""

import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_metadata import cmd_init, cmd_set_tag, cmd_rm_tag, cmd_compat, _meta_path, _load_meta
from tests.helpers import FIGHTER, copy_fixture, capture


class TestCmdInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_all_four_entries(self):
        cmd_init(self.f)
        meta = _load_meta(self.f)
        self.assertSetEqual(set(meta.keys()), {"idle", "punch", "guard", "step_in"})

    def test_empty_tags_on_init(self):
        cmd_init(self.f)
        meta = _load_meta(self.f)
        for entry in meta.values():
            self.assertIsInstance(entry["tags"], list)

    def test_idempotent_does_not_overwrite(self):
        cmd_init(self.f)
        # 手動設 tag 後再 init，不應被清空
        meta = _load_meta(self.f)
        meta["idle"]["tags"] = ["custom"]
        mp = _meta_path(self.f)
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        cmd_init(self.f)
        meta2 = _load_meta(self.f)
        self.assertIn("custom", meta2["idle"]["tags"])


class TestCmdSetTag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))
        cmd_init(self.f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_adds_tag(self):
        cmd_set_tag(self.f, "punch", "attack")
        meta = _load_meta(self.f)
        self.assertIn("attack", meta["punch"]["tags"])

    def test_does_not_duplicate(self):
        cmd_set_tag(self.f, "punch", "attack")
        cmd_set_tag(self.f, "punch", "attack")
        meta = _load_meta(self.f)
        self.assertEqual(meta["punch"]["tags"].count("attack"), 1)

    def test_multiple_tags(self):
        cmd_set_tag(self.f, "idle", "ground")
        cmd_set_tag(self.f, "idle", "loopable")
        meta = _load_meta(self.f)
        self.assertIn("ground", meta["idle"]["tags"])
        self.assertIn("loopable", meta["idle"]["tags"])


class TestCmdRmTag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))
        cmd_init(self.f)
        cmd_set_tag(self.f, "punch", "attack")
        cmd_set_tag(self.f, "punch", "upper_body")

    def tearDown(self):
        self.tmp.cleanup()

    def test_removes_tag(self):
        cmd_rm_tag(self.f, "punch", "attack")
        meta = _load_meta(self.f)
        self.assertNotIn("attack", meta["punch"]["tags"])

    def test_keeps_other_tags(self):
        cmd_rm_tag(self.f, "punch", "attack")
        meta = _load_meta(self.f)
        self.assertIn("upper_body", meta["punch"]["tags"])

    def test_rm_nonexistent_tag_no_crash(self):
        with capture() as out:
            cmd_rm_tag(self.f, "punch", "nonexistent")
        self.assertIn("找不到", out.getvalue())


class TestCmdCompat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = str(copy_fixture(FIGHTER, Path(self.tmp.name)))
        cmd_init(self.f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_compatible_after(self):
        cmd_compat(self.f, "idle", "after", "punch")
        meta = _load_meta(self.f)
        self.assertIn("punch", meta["idle"]["compatible_after"])

    def test_compatible_before(self):
        cmd_compat(self.f, "punch", "before", "guard")
        meta = _load_meta(self.f)
        self.assertIn("guard", meta["punch"]["compatible_before"])

    def test_no_duplicate_compat(self):
        cmd_compat(self.f, "idle", "after", "punch")
        cmd_compat(self.f, "idle", "after", "punch")
        meta = _load_meta(self.f)
        self.assertEqual(meta["idle"]["compatible_after"].count("punch"), 1)

    def test_after_and_before_independent(self):
        cmd_compat(self.f, "idle", "after", "punch")
        cmd_compat(self.f, "idle", "before", "guard")
        meta = _load_meta(self.f)
        self.assertIn("punch", meta["idle"]["compatible_after"])
        self.assertIn("guard", meta["idle"]["compatible_before"])
        self.assertNotIn("guard", meta["idle"]["compatible_after"])


if __name__ == "__main__":
    unittest.main()
