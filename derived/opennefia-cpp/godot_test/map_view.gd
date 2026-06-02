extends Node2D

# F3 地圖場景：輸入 → 核心移動 → Signal 刷新顯示。
# F4 音效框架：hero_bumped_wall / hero_bumped_npc 信號 → AudioStreamPlayer。
# 戰鬥：hero 攻擊 NPC（3 dmg）；NPC 鄰接攻擊 hero（2 dmg）；game_over 偵測。
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

var world: OpenNefiaWorld
const CELL_PX := 16

var _dead := false  # game over 後鎖定輸入

# F4 音效播放器（load 實際 .ogg/.wav 後取消 stream 行的注釋即可）
var sfx_step:     AudioStreamPlayer
var sfx_wall:     AudioStreamPlayer
var sfx_bump_npc: AudioStreamPlayer

func _ready() -> void:
	world = OpenNefiaWorld.new()
	world.name = "OpenNefiaWorld"
	add_child(world)

	# 核心事件信號
	world.world_changed.connect(_on_world_changed)
	world.hero_bumped_wall.connect(_on_hero_bumped_wall)
	world.hero_bumped_npc.connect(_on_hero_bumped_npc)
	world.npc_died.connect(_on_npc_died)
	world.game_over.connect(_on_game_over)
	world.floor_changed.connect(_on_floor_changed)

	_setup_audio()
	_refresh_display()
	_refresh_ui()

	print("F3+F4+戰鬥 ready — WASD/arrow/numpad 移動，. 等待")

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
	if _dead: return
	if not (event is InputEventKey and event.pressed and not event.echo):
		return

	match event.keycode:
		KEY_UP,    KEY_W, KEY_KP_8: world.move( 0, -1)
		KEY_DOWN,  KEY_S, KEY_KP_2: world.move( 0,  1)
		KEY_RIGHT, KEY_D, KEY_KP_6: world.move( 1,  0)
		KEY_LEFT,  KEY_A, KEY_KP_4: world.move(-1,  0)
		KEY_KP_7:                   world.move(-1, -1)
		KEY_KP_9:                   world.move( 1, -1)
		KEY_KP_1:                   world.move(-1,  1)
		KEY_KP_3:                   world.move( 1,  1)
		KEY_PERIOD, KEY_KP_5:       world.wait_turn()
		KEY_R: _do_restart()

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

func _do_restart() -> void:
	_dead = false
	world.restart()
	print("— 重新開始 —")

func _refresh_display() -> void:
	var img := world.generate_map_image(CELL_PX)
	sprite.centered = false
	sprite.position = Vector2.ZERO
	sprite.texture  = ImageTexture.create_from_image(img)
	camera.position = Vector2(world.get_hero_x() + 0.5, world.get_hero_y() + 0.5) * CELL_PX

func _refresh_ui() -> void:
	info_label.text = "F%d  Hero: (%d, %d)  Turn: %d  HP: %d/%d  Enemies: %d" % [
		world.get_current_floor(),
		world.get_hero_x(),
		world.get_hero_y(),
		world.get_turn_count(),
		world.get_hero_hp(),
		world.get_hero_max_hp(),
		world.get_npc_count()
	]
