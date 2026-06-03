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

func _process(_delta: float) -> bool:
	var failed := 0

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
