extends Node2D

# F3 地圖場景：輸入 → 核心移動 → Signal 刷新顯示。
# F4 音效框架：hero_bumped_wall / hero_bumped_npc 信號 → AudioStreamPlayer。
# 戰鬥：hero 攻擊 NPC（3 dmg）；NPC 鄰接攻擊 hero（2 dmg）；game_over 偵測。
# 存讀檔：F5 存檔（user://zone_save.bin），F9 讀檔。
#   兩者皆可在 game_over 後操作（不受 _dead 限制）。
#
# 建議場景結構：
#   MapView (Node2D)          ← 此腳本
#   ├── Sprite2D              ← 地圖圖片
#   ├── Camera2D
#   └── CanvasLayer (layer=1)
#       └── InfoLabel (Label) ← 左上角 UI（hero 座標 + 回合數 + HP）

@onready var sprite: Sprite2D   = $Sprite2D
@onready var camera: Camera2D   = $Camera2D
@onready var info_label: Label  = $CanvasLayer/InfoLabel

var world: ZoneWorld
const CELL_PX := 16
const SAVE_PATH := "user://zone_save.bin"

var _dead := false  # game over 後鎖定輸入

# 排程器路徑（A/B/C 可切換）。TAB 鍵循環。
var _sched_mode := 1   # 0=EnergyInstant 1=EnergyChannel 2=TickRemaining
const SCHED_NAMES := ["A:能量瞬發", "B:能量+channel", "C:純tick"]

# 計時器驅動推進（與渲染解耦）。channel 多回合與即時打斷靠此體現。
var _advance_timer: Timer
var _pending_input := false   # 玩家剛下指令、待下次 tick 消化
var _tick_sec := 0.2          # 每步間隔；[ ] 調慢/快
const CAST_TURNS := 3         # C 鍵詠唱回合數

# F4 音效播放器（load 實際 .ogg/.wav 後取消 stream 行的注釋即可）
var sfx_step:     AudioStreamPlayer
var sfx_wall:     AudioStreamPlayer
var sfx_bump_npc: AudioStreamPlayer

func _ready() -> void:
	world = ZoneWorld.new()
	world.name = "ZoneWorld"
	add_child(world)

	# 核心事件信號
	world.world_changed.connect(_on_world_changed)
	world.hero_bumped_wall.connect(_on_hero_bumped_wall)
	world.hero_bumped_npc.connect(_on_hero_bumped_npc)
	world.npc_died.connect(_on_npc_died)
	world.game_over.connect(_on_game_over)
	world.floor_changed.connect(_on_floor_changed)
	world.item_picked_up.connect(_on_item_picked_up)

	_setup_audio()
	world.set_scheduler_mode(_sched_mode)

	# 計時器驅動推進（不綁渲染幀）
	_advance_timer = Timer.new()
	_advance_timer.wait_time = _tick_sec
	_advance_timer.one_shot = false
	_advance_timer.timeout.connect(_on_advance_tick)
	add_child(_advance_timer)
	_advance_timer.start()

	_refresh_display()
	_refresh_ui()

	print("ready — WASD移動 .等待 C火球/H治療/M隕石(r2)/V毒 TAB排程器 [ ]調速 L開關trace K清log (%s)" % SCHED_NAMES[_sched_mode])

func _setup_audio() -> void:
	sfx_step     = AudioStreamPlayer.new()
	sfx_wall     = AudioStreamPlayer.new()
	sfx_bump_npc = AudioStreamPlayer.new()
	add_child(sfx_step)
	add_child(sfx_wall)
	add_child(sfx_bump_npc)
	# 換成真實音效時，取消以下注釋：
	# sfx_step.stream     = load("res://sounds/step.ogg")
	# sfx_wall.stream     = load("res://sounds/bump.ogg")
	# sfx_bump_npc.stream = load("res://sounds/hit.ogg")

func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed and not event.echo):
		return

	# 存讀檔不受 _dead 限制（game over 後仍可存 / 讀）
	match event.keycode:
		KEY_F5: _do_save(); return
		KEY_F9: _do_load(); return

	if event.keycode == KEY_TAB:
		_cycle_scheduler(); return
	if event.keycode == KEY_BRACKETLEFT:
		_set_tick(_tick_sec * 1.5); return     # 調慢
	if event.keycode == KEY_BRACKETRIGHT:
		_set_tick(_tick_sec / 1.5); return     # 調快
	if event.keycode == KEY_L:
		var en := not world.get_trace_enabled()
		world.set_trace_enabled(en)
		print("— debug trace %s —" % ("ON" if en else "OFF")); return
	if event.keycode == KEY_K:
		world.clear_debug_log(); return        # 清 log

	if _dead: return

	match event.keycode:
		KEY_UP,    KEY_W, KEY_KP_8: _queue_move( 0, -1)
		KEY_DOWN,  KEY_S, KEY_KP_2: _queue_move( 0,  1)
		KEY_RIGHT, KEY_D, KEY_KP_6: _queue_move( 1,  0)
		KEY_LEFT,  KEY_A, KEY_KP_4: _queue_move(-1,  0)
		KEY_KP_7:                   _queue_move(-1, -1)
		KEY_KP_9:                   _queue_move( 1, -1)
		KEY_KP_1:                   _queue_move(-1,  1)
		KEY_KP_3:                   _queue_move( 1,  1)
		KEY_PERIOD, KEY_KP_5:       _queue_wait()
		KEY_C:                      _queue_skill("fireball")
		KEY_H:                      _queue_skill("heal")
		KEY_M:                      _queue_skill("meteor")   # 大範圍(r2)
		KEY_V:                      _queue_skill("venom")    # 中毒 DoT
		KEY_R: _do_restart()

# 玩家下指令：寫進英雄的收件匣，等下一個計時器 tick 消化（不在這裡推進）。
func _queue_move(dx: int, dy: int) -> void:
	world.submit_hero_move(dx, dy)
	_pending_input = true

func _queue_wait() -> void:
	world.submit_hero_wait()
	_pending_input = true

func _queue_skill(skill_name: String) -> void:
	world.submit_hero_skill(skill_name)
	_pending_input = true
	print("施放技能 %s（JSON 資料驅動，多回合可被移動打斷）" % skill_name)

# 計時器每 tick 推進一步；英雄 idle 且無新指令時不推進（世界阻塞、等輸入）。
func _on_advance_tick() -> void:
	if _dead: return
	if world.hero_is_waiting() and not _pending_input:
		return
	world.step_scheduler()
	_pending_input = false

func _set_tick(sec: float) -> void:
	_tick_sec = clampf(sec, 0.03, 2.0)
	_advance_timer.wait_time = _tick_sec
	print("— 步調 %.2fs/步 —" % _tick_sec)

func _cycle_scheduler() -> void:
	_sched_mode = (_sched_mode + 1) % SCHED_NAMES.size()
	world.set_scheduler_mode(_sched_mode)
	_pending_input = false
	print("— 排程器切換為 %s —" % SCHED_NAMES[_sched_mode])
	_refresh_ui()

func _on_world_changed() -> void:
	_refresh_display()
	_refresh_ui()
	if sfx_step.stream:
		sfx_step.play()

func _on_hero_bumped_wall() -> void:
	if sfx_wall.stream:
		sfx_wall.play()
	else:
		print("* 碰牆 *")

func _on_hero_bumped_npc(npc_id: String) -> void:
	if sfx_bump_npc.stream:
		sfx_bump_npc.play()
	else:
		print("* 攻擊 %s（未致死）*" % npc_id)

func _on_npc_died(npc_id: String) -> void:
	print("* %s 倒下了！*" % npc_id)

func _on_game_over() -> void:
	_dead = true
	print("★ GAME OVER ★  你被 NPC 擊倒了。")
	info_label.text += "\n[GAME OVER]"

func _on_floor_changed(floor_num: int) -> void:
	print("★ 下降至第 %d 層 ★" % floor_num)

func _on_item_picked_up(item_name: String, heal_amount: int) -> void:
	print("★ 拾取 %s（回復 %d HP）" % [item_name, heal_amount])

func _do_restart() -> void:
	_dead = false
	world.restart()
	print("— 重新開始 —")

func _do_save() -> void:
	var real_path := ProjectSettings.globalize_path(SAVE_PATH)
	if world.save_game(real_path):
		print("★ 存檔成功（F%d，第 %d 回合）" % [world.get_current_floor(), world.get_turn_count()])
		_refresh_ui()
	else:
		print("★ 存檔失敗（地圖或英雄未初始化）")

func _do_load() -> void:
	var real_path := ProjectSettings.globalize_path(SAVE_PATH)
	if not world.has_save_game(real_path):
		print("★ 找不到存檔，請先按 F5 存檔")
		return
	if world.load_game(real_path):
		_dead = false
		print("★ 讀檔成功（F%d，第 %d 回合）" % [world.get_current_floor(), world.get_turn_count()])
	else:
		print("★ 讀檔失敗")

func _refresh_display() -> void:
	var img := world.generate_map_image(CELL_PX)
	sprite.centered = false
	sprite.position = Vector2.ZERO
	sprite.texture  = ImageTexture.create_from_image(img)
	camera.position = Vector2(world.get_hero_x() + 0.5, world.get_hero_y() + 0.5) * CELL_PX

func _refresh_ui() -> void:
	# 詳細診斷 dump（世界 + 逐 actor 全狀態）+ 最近 trace log，供測試系統機制時觀察
	var t := world.get_debug_text()
	var log: String = world.get_debug_log()
	if log != "":
		t += "\n—— trace ——\n" + log
	info_label.text = t
