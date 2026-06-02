extends SceneTree

# 程式碼建立一個 AnimationNodeStateMachine，
# 加 idle/punch 兩個狀態 + 3 條轉場，
# 存成 state_machine_reference.tres，讓我們看 Godot 4.6 自己的格式。

func _init():
	var sm := AnimationNodeStateMachine.new()

	# 建兩個 AnimationNodeAnimation 狀態
	var n_idle := AnimationNodeAnimation.new()
	n_idle.animation = &"idle"
	sm.add_node("idle", n_idle, Vector2(200, 160))

	var n_punch := AnimationNodeAnimation.new()
	n_punch.animation = &"punch"
	sm.add_node("punch", n_punch, Vector2(460, 160))

	# 轉場 Start→idle（Start 是內建節點）
	var tr_si := AnimationNodeStateMachineTransition.new()
	sm.add_transition("Start", "idle", tr_si)

	# 轉場 idle→punch（xfade 0.2, sync, auto+cond）
	var tr_ip := AnimationNodeStateMachineTransition.new()
	tr_ip.xfade_time = 0.2
	tr_ip.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_SYNC
	tr_ip.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
	tr_ip.advance_condition = &"do_punch"
	sm.add_transition("idle", "punch", tr_ip)

	# 轉場 punch→idle（xfade 0.15, at_end, auto）
	var tr_pi := AnimationNodeStateMachineTransition.new()
	tr_pi.xfade_time = 0.15
	tr_pi.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_AT_END
	tr_pi.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO
	tr_pi.break_loop_at_end = true
	sm.add_transition("punch", "idle", tr_pi)

	var err = ResourceSaver.save(sm, "res://state_machine_reference.tres")
	if err == OK:
		print("已儲存 state_machine_reference.tres")
	else:
		print("FAIL 儲存失敗：", err)

	print("\n=== 節點清單 ===")
	for n in sm.get_node_list():
		print("  ", n, " → ", sm.get_node(n).get_class())

	print("\n=== 轉場清單（", sm.get_transition_count(), " 條）===")
	for i in sm.get_transition_count():
		var f = sm.get_transition_from(i)
		var t = sm.get_transition_to(i)
		var tr = sm.get_transition(i)
		print("  ", f, " → ", t, "  xfade=", tr.xfade_time)

	quit(0)
