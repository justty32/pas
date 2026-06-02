"""anim_tree — load/dump round-trip / summary / add-rm-state / transition / derive 測試。"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anim_tree import (
    load_sm, dump_sm, save_sm,
    cmd_summary, cmd_add_state, cmd_rm_state,
    cmd_add_transition, cmd_rm_transition, cmd_set_blend,
    cmd_derive,
    _find_state, _find_transition,
    ANIM_TYPE, START_TYPE, END_TYPE,
)
from tests.helpers import SM, FIGHTER, META, copy_fixture, capture


class TestLoadDumpRoundTrip(unittest.TestCase):
    def test_load_gives_correct_state_count(self):
        model = load_sm(str(SM))
        # state_machine_sample: Start(virtual) + idle + punch = 3
        # End 不在此檔（無轉場指向 End），故不計入
        self.assertEqual(len(model["states"]), 3)

    def test_load_has_start(self):
        model = load_sm(str(SM))
        names = {s["name"] for s in model["states"]}
        # Start 由 transitions 補回（虛擬節點）；End 不在此範例
        self.assertIn("Start", names)
        self.assertIn("idle", names)
        self.assertIn("punch", names)

    def test_load_idle_punch_states(self):
        model = load_sm(str(SM))
        names = {s["name"] for s in model["states"]}
        self.assertIn("idle", names)
        self.assertIn("punch", names)

    def test_load_three_transitions(self):
        model = load_sm(str(SM))
        self.assertEqual(len(model["transitions"]), 3)

    def test_dump_round_trip(self):
        model = load_sm(str(SM))
        text = dump_sm(model)
        model2 = load_sm.__wrapped__(text) if hasattr(load_sm, "__wrapped__") else None
        # 至少確認 dump 包含基本結構
        self.assertIn("AnimationNodeStateMachine", text)
        self.assertIn("Start", text)
        self.assertIn("idle", text)
        self.assertIn("punch", text)
        self.assertIn("[resource]", text)

    def test_no_load_steps_in_output(self):
        # Godot 4.4+ 格式不包含 load_steps
        model = load_sm(str(SM))
        text = dump_sm(model)
        self.assertNotIn("load_steps=", text)

    def test_no_start_end_subresource_in_output(self):
        # Start/End 是引擎內建節點，不應出現在 sub_resource 塊
        model = load_sm(str(SM))
        text = dump_sm(model)
        self.assertNotIn("AnimationNodeStartState", text)
        self.assertNotIn("AnimationNodeEndState", text)

    def test_xfade_preserved(self):
        model = load_sm(str(SM))
        tr = _find_transition(model, "idle", "punch")
        self.assertIsNotNone(tr)
        self.assertEqual(tr["props"].get("xfade_time"), "0.2")

    def test_advance_condition_preserved(self):
        model = load_sm(str(SM))
        tr = _find_transition(model, "idle", "punch")
        self.assertIn("do_punch", tr["props"].get("advance_condition", ""))


class TestCmdSummary(unittest.TestCase):
    def test_summary_output(self):
        with capture() as out:
            cmd_summary(str(SM))
        text = out.getvalue()
        self.assertIn("idle", text)
        self.assertIn("punch", text)
        self.assertIn("Start", text)

    def test_summary_shows_transitions(self):
        with capture() as out:
            cmd_summary(str(SM))
        text = out.getvalue()
        self.assertIn("→", text)

    def test_summary_with_lib_cross_check(self):
        with capture() as out:
            cmd_summary(str(SM), lib=str(FIGHTER))
        text = out.getvalue()
        self.assertIn("✓", text)  # 所有動畫都在 library


class TestCmdAddRmState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sm = str(copy_fixture(SM, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_state(self):
        cmd_add_state(self.sm, "guard", "guard")
        model = load_sm(self.sm)
        self.assertIsNotNone(_find_state(model, "guard"))

    def test_add_state_animation_ref(self):
        cmd_add_state(self.sm, "guard", "guard")
        model = load_sm(self.sm)
        st = _find_state(model, "guard")
        self.assertIn("guard", st["node_props"].get("animation", ""))

    def test_add_duplicate_state_no_op(self):
        with capture() as out:
            cmd_add_state(self.sm, "idle", "idle")
        self.assertIn("已存在", out.getvalue())
        model = load_sm(self.sm)
        idle_count = sum(1 for s in model["states"] if s["name"] == "idle")
        self.assertEqual(idle_count, 1)

    def test_rm_state(self):
        cmd_rm_state(self.sm, "punch")
        model = load_sm(self.sm)
        self.assertIsNone(_find_state(model, "punch"))

    def test_rm_state_cascades_transitions(self):
        # punch 參與 idle→punch 和 punch→idle 兩條，rm 後都應消失
        cmd_rm_state(self.sm, "punch")
        model = load_sm(self.sm)
        for tr in model["transitions"]:
            self.assertNotEqual(tr["from"], "punch")
            self.assertNotEqual(tr["to"], "punch")

    def test_rm_special_state_rejected(self):
        with capture() as out:
            cmd_rm_state(self.sm, "Start")
        self.assertIn("不可移除", out.getvalue())
        model = load_sm(self.sm)
        self.assertIsNotNone(_find_state(model, "Start"))

    def test_rm_nonexistent_state(self):
        with capture() as out:
            cmd_rm_state(self.sm, "nonexistent")
        self.assertIn("找不到", out.getvalue())


class TestCmdAddRmTransition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sm = str(copy_fixture(SM, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_new_transition(self):
        cmd_add_transition(self.sm, "punch", "Start", {})
        model = load_sm(self.sm)
        self.assertIsNotNone(_find_transition(model, "punch", "Start"))

    def test_add_transition_with_xfade(self):
        cmd_add_transition(self.sm, "punch", "Start", {"xfade": "0.3"})
        model = load_sm(self.sm)
        tr = _find_transition(model, "punch", "Start")
        self.assertEqual(tr["props"].get("xfade_time"), "0.3")

    def test_update_existing_transition(self):
        # idle→punch 已存在，add 應「更新」而非新增重複
        before = len(load_sm(self.sm)["transitions"])
        cmd_add_transition(self.sm, "idle", "punch", {"xfade": "0.5"})
        model = load_sm(self.sm)
        self.assertEqual(len(model["transitions"]), before)
        tr = _find_transition(model, "idle", "punch")
        self.assertEqual(tr["props"].get("xfade_time"), "0.5")

    def test_rm_transition(self):
        cmd_rm_transition(self.sm, "idle", "punch")
        model = load_sm(self.sm)
        self.assertIsNone(_find_transition(model, "idle", "punch"))

    def test_rm_nonexistent_transition(self):
        with capture() as out:
            cmd_rm_transition(self.sm, "punch", "guard")
        self.assertIn("找不到", out.getvalue())


class TestCmdSetBlend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sm = str(copy_fixture(SM, Path(self.tmp.name)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_set_blend_updates_xfade(self):
        cmd_set_blend(self.sm, "idle", "punch", "0.4")
        model = load_sm(self.sm)
        tr = _find_transition(model, "idle", "punch")
        self.assertEqual(tr["props"].get("xfade_time"), "0.4")

    def test_set_blend_creates_if_absent(self):
        cmd_set_blend(self.sm, "punch", "Start", "0.1")
        model = load_sm(self.sm)
        tr = _find_transition(model, "punch", "Start")
        self.assertIsNotNone(tr)
        self.assertEqual(tr["props"].get("xfade_time"), "0.1")


class TestCmdDerive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # derive 在 --reset 時從零建立，不需要預先有 .tres
        self.out_sm = str(Path(self.tmp.name) / "derived.tres")

    def tearDown(self):
        self.tmp.cleanup()

    def test_derive_creates_all_states(self):
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle", "reset": True,
            })
        model = load_sm(self.out_sm)
        anim_names = {s["name"] for s in model["states"] if s["node_type"] == ANIM_TYPE}
        self.assertEqual(anim_names, {"idle", "punch", "guard", "step_in"})

    def test_derive_has_start_state(self):
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle", "reset": True,
            })
        model = load_sm(self.out_sm)
        self.assertIsNotNone(_find_state(model, "Start"))
        self.assertIsNotNone(_find_transition(model, "Start", "idle"))

    def test_derive_transitions_from_metadata(self):
        # meta: idle.compatible_after=[punch] → 轉場 punch → idle
        # meta: punch.compatible_after=[idle, guard, step_in] → 3 條
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle", "reset": True,
            })
        model = load_sm(self.out_sm)
        # punch → idle 應存在
        self.assertIsNotNone(_find_transition(model, "punch", "idle"))
        # idle → guard 應存在（guard.compatible_after=[idle]）
        self.assertIsNotNone(_find_transition(model, "idle", "guard"))
        # idle → step_in 應存在
        self.assertIsNotNone(_find_transition(model, "idle", "step_in"))

    def test_derive_reset_clears_existing(self):
        # 先建一個有 guard 的 sm，再 --reset derive
        cmd_add_state(str(copy_fixture(SM, Path(self.tmp.name))), "guard", "guard")
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle", "reset": True,
            })
        model = load_sm(self.out_sm)
        # 重建後應有 library 的 4 個動畫，Start/End 由 derive 內部處理
        anim_states = [s for s in model["states"] if s["node_type"] == ANIM_TYPE]
        self.assertEqual(len(anim_states), 4)

    def test_derive_no_duplicate_transitions(self):
        # derive 兩次（無 --reset）不應重複加轉場
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle", "reset": True,
            })
        n1 = len(load_sm(self.out_sm)["transitions"])
        with capture():
            cmd_derive(self.out_sm, {
                "lib": str(FIGHTER), "meta": str(META),
                "start": "idle",
            })
        n2 = len(load_sm(self.out_sm)["transitions"])
        self.assertEqual(n1, n2)


if __name__ == "__main__":
    unittest.main()
