extends SceneTree

# Headless 驗證腳本：godot-mono --headless -s res://verify.gd
# 實際載入 libzone_gd.so，驗證 ZoneCore + ZoneWorld 端到端可用。

var world  # 在 _initialize 建立、加入 root；_ready 要到第一幀才派發，故檢查放 _process

func _initialize() -> void:
	# --- ZoneCore.version()（不依賴 _ready，可即時驗）---
	var core := ZoneCore.new()
	var v: String = core.version()
	print("zone core version: ", v)
	if v == "":
		push_error("version() 為空")

	# --- ZoneWorld：加入 root，_ready→setup_test_world 於下一幀觸發 ---
	world = ZoneWorld.new()
	world.name = "ZoneWorld"
	root.add_child(world)

# step-first 推進：先推一步（消化剛 submit 的指令），再到英雄等待為止。
func _advance(n_max: int = 200) -> void:
	for i in range(n_max):
		world.step_scheduler()
		if world.hero_is_waiting():
			return

func _process(_delta: float) -> bool:
	var failed := 0
	world.set_trace_enabled(false)  # 大量檢查時關閉 trace 噪音，最後再單獨驗

	var w: int = world.get_map_width()
	var h: int = world.get_map_height()
	print("map size: %dx%d  hero=(%d,%d) hp=%d/%d npc=%d floor=%d turn=%d" % [
		w, h, world.get_hero_x(), world.get_hero_y(),
		world.get_hero_hp(), world.get_hero_max_hp(),
		world.get_npc_count(), world.get_current_floor(), world.get_turn_count()])
	if w <= 0 or h <= 0:
		push_error("地圖尺寸異常"); failed += 1
	if world.get_hero_max_hp() <= 0:
		push_error("英雄 HP 未初始化"); failed += 1

	# --- generate_map_image 回傳有效 Image ---
	var img: Image = world.generate_map_image(8)
	if img == null or img.get_width() != w * 8 or img.get_height() != h * 8:
		push_error("generate_map_image 尺寸異常"); failed += 1
	else:
		print("map image: %dx%d px" % [img.get_width(), img.get_height()])

	# --- 推進回合：wait_turn 應使 turn_count 遞增 ---
	var t0: int = world.get_turn_count()
	world.wait_turn()
	if world.get_turn_count() <= t0:
		push_error("wait_turn 未推進回合"); failed += 1
	else:
		print("turn advanced: %d -> %d" % [t0, world.get_turn_count()])

	# --- 移動（往四方各試一次，至少有一次合法移動）---
	var hx0: int = world.get_hero_x()
	var hy0: int = world.get_hero_y()
	for d in [Vector2i(1,0), Vector2i(-1,0), Vector2i(0,1), Vector2i(0,-1)]:
		world.move(d.x, d.y)
	print("hero after moves: (%d,%d) -> (%d,%d)" % [hx0, hy0, world.get_hero_x(), world.get_hero_y()])

	# --- 排程器路徑：A/B/C 三模式 set_mode + submit + step ---
	for mode in [0, 1, 2]:
		world.set_scheduler_mode(mode)
		if world.get_scheduler_mode() != mode:
			push_error("set_scheduler_mode 失敗 mode=%d" % mode); failed += 1
		# 推進直到英雄需要指令
		_advance()
		if not world.hero_is_waiting():
			push_error("mode %d 未停在英雄等待" % mode); failed += 1
		# 送一個移動指令，step-first 推進回英雄等待
		var bx: int = world.get_hero_x()
		var by: int = world.get_hero_y()
		world.submit_hero_move(1, 0)
		_advance()
		if not world.hero_is_waiting():
			push_error("mode %d submit 後未回英雄等待" % mode); failed += 1
		else:
			print("scheduler mode %d OK: hero (%d,%d) -> (%d,%d)" % [
				mode, bx, by, world.get_hero_x(), world.get_hero_y()])

	# --- Cast 詠唱路徑（EnergyChannel）---
	world.set_scheduler_mode(1)
	_advance()
	world.submit_hero_cast(3)
	_advance()
	if not world.hero_is_waiting():
		push_error("cast 後未回英雄等待"); failed += 1
	else:
		print("cast OK: hero hp=%d" % world.get_hero_hp())

	# --- 資料驅動技能（JSON 庫）---
	world.submit_hero_skill("fireball")
	_advance()
	if not world.hero_is_waiting():
		push_error("skill fireball 後未回英雄等待"); failed += 1
	else:
		print("skill OK: fireball 施放, hero hp=%d" % world.get_hero_hp())

	# --- UI 查詢 getters（heal → 回復 buff，狀態/效果字串）---
	world.submit_hero_skill("heal")
	_advance()
	var st: String = world.get_hero_status()
	var ef: String = world.get_hero_effects()
	print("ui OK: status='%s' effects='%s'" % [st, ef])
	if ef == "":
		push_error("heal 後英雄應有回復 buff"); failed += 1
	print("debug dump 首行: %s" % world.get_debug_text().get_slice("\n", 0))

	# --- NPC 追擊：英雄原地等待，NPC 接近並攻擊（半數為施法者）---
	world.set_scheduler_mode(0)
	var hp0: int = world.get_hero_hp()
	for i in range(40):
		world.submit_hero_wait()
		_advance()
		if world.get_hero_hp() <= 0:
			break
	print("chase: hero hp %d -> %d, effects='%s'" % [
		hp0, world.get_hero_hp(), world.get_hero_effects()])

	# --- debug trace：開啟、動一步、檢查有產生 log ---
	world.restart()
	world.set_scheduler_mode(1)
	world.set_trace_enabled(true)
	world.clear_debug_log()
	world.submit_hero_move(0, 1)
	_advance()
	var tlog: String = world.get_debug_log()
	if tlog.strip_edges() == "":
		push_error("trace 未產生任何行"); failed += 1
	else:
		print("trace sample (前數行):")
		for ln in tlog.split("\n"):
			if ln.strip_edges() != "":
				print("  ", ln)
	world.set_trace_enabled(false)

	# --- 存讀檔 round-trip ---
	var save_path := "user://verify_save.bin"
	var ok_save: bool = world.save_game(save_path)
	var exists: bool = world.has_save_game(save_path)
	if not ok_save or not exists:
		push_error("save_game 失敗 (ok=%s exists=%s)" % [ok_save, exists]); failed += 1
	else:
		var saved_turn: int = world.get_turn_count()
		var saved_floor: int = world.get_current_floor()
		world.wait_turn()  # 改變狀態
		var ok_load: bool = world.load_game(save_path)
		if not ok_load:
			push_error("load_game 失敗"); failed += 1
		elif world.get_turn_count() != saved_turn or world.get_current_floor() != saved_floor:
			push_error("讀檔後狀態不符 (turn %d!=%d floor %d!=%d)" % [
				world.get_turn_count(), saved_turn, world.get_current_floor(), saved_floor]); failed += 1
		else:
			print("save/load round-trip OK (turn=%d floor=%d)" % [saved_turn, saved_floor])

	if failed == 0:
		print("VERIFY PASSED")
	else:
		print("VERIFY FAILED: %d 項" % failed)
	quit(failed)
	return true  # 結束主迴圈（單幀驗證）
