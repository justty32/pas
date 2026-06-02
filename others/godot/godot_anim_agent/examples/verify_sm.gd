extends SceneTree

func _init():
	var ok := true

	print("=== AnimationNodeStateMachine 格式驗證 ===\n")

	# ── 1. 載入 AnimationNodeStateMachine ───────────────────────────────────────
	var sm = load("res://state_machine_sample.tres")
	if sm == null or not sm is AnimationNodeStateMachine:
		print("FAIL [1] state_machine_sample.tres 無法載入或型別錯誤")
		ok = false
	else:
		print("OK   [1] state_machine_sample.tres 載入成功（AnimationNodeStateMachine）")

		# ── 2. 狀態清單 ─────────────────────────────────────────────────────────
		var nodes: Array = sm.get_node_list()
		print("     狀態清單：", nodes)

		for expected in ["Start", "End", "idle", "punch"]:
			if sm.has_node(expected):
				print("OK   [2] 狀態存在：", expected)
			else:
				print("FAIL [2] 找不到狀態：", expected)
				ok = false

		# ── 3. 轉場 ─────────────────────────────────────────────────────────────
		var tc: int = sm.get_transition_count()
		print("     轉場數量：", tc)
		if tc == 3:
			print("OK   [3] 轉場數 = 3")
		else:
			print("FAIL [3] 期望 3 條轉場，實際 ", tc)
			ok = false

		var expected_transitions = [
			["Start", "idle"],
			["idle", "punch"],
			["punch", "idle"],
		]
		for pair in expected_transitions:
			if sm.has_transition(pair[0], pair[1]):
				print("OK   [3] 轉場存在：", pair[0], " → ", pair[1])
			else:
				print("FAIL [3] 找不到轉場：", pair[0], " → ", pair[1])
				ok = false

		# ── 4. idle→punch 的 xfade_time ─────────────────────────────────────────
		var tr_ip: AnimationNodeStateMachineTransition = null
		for i in sm.get_transition_count():
			if sm.get_transition_from(i) == &"idle" and sm.get_transition_to(i) == &"punch":
				tr_ip = sm.get_transition(i)
				break
		if tr_ip != null and abs(tr_ip.xfade_time - 0.2) < 0.001:
			print("OK   [4] idle→punch xfade_time = 0.2")
		else:
			print("FAIL [4] idle→punch xfade_time 期望 0.2，實際 ", tr_ip.xfade_time if tr_ip else "N/A")
			ok = false

		# ── 5. punch→idle 的 switch_mode (at_end=2) ─────────────────────────────
		var tr_pi: AnimationNodeStateMachineTransition = null
		for i in sm.get_transition_count():
			if sm.get_transition_from(i) == &"punch" and sm.get_transition_to(i) == &"idle":
				tr_pi = sm.get_transition(i)
				break
		if tr_pi != null and tr_pi.switch_mode == AnimationNodeStateMachineTransition.SWITCH_MODE_AT_END:
			print("OK   [5] punch→idle switch_mode = at_end")
		else:
			print("FAIL [5] punch→idle switch_mode 期望 at_end(2)，實際 ", tr_pi.switch_mode if tr_pi else "N/A")
			ok = false

		# ── 6. 回存（讓 Godot 用自己的格式序列化）─────────────────────────────
		var save_err = ResourceSaver.save(sm, "res://state_machine_godot_saved.tres")
		if save_err == OK:
			print("\nOK   [6] 回存成功 → state_machine_godot_saved.tres")
			print("     可用 diff state_machine_sample.tres state_machine_godot_saved.tres 確認格式差異")
		else:
			print("\nWARN [6] 回存失敗（錯誤碼 ", save_err, "）")

	# ── 7. 載入完整場景 ──────────────────────────────────────────────────────────
	var scene = load("res://fighter_tree.tscn")
	if scene == null:
		print("\nFAIL [7] fighter_tree.tscn 無法載入")
		ok = false
	else:
		var inst = scene.instantiate()
		var anim_tree: AnimationTree = inst.get_node("AnimationTree")
		if anim_tree == null:
			print("\nFAIL [7] 找不到 AnimationTree 節點")
			ok = false
		elif not anim_tree.tree_root is AnimationNodeStateMachine:
			print("\nFAIL [7] AnimationTree.tree_root 不是 AnimationNodeStateMachine")
			ok = false
		else:
			print("\nOK   [7] fighter_tree.tscn 載入，AnimationTree.tree_root 型別正確")
		inst.free()

	print()
	if ok:
		print("=== VERIFY PASSED ===")
	else:
		print("=== VERIFY FAILED ===")

	quit(0 if ok else 1)
