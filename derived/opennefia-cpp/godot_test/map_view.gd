extends Node2D

# F3 地圖場景：輸入 → 核心移動 → Signal 刷新顯示。
# F4 音效框架：hero_bumped_wall / hero_bumped_npc 信號 → AudioStreamPlayer。
#
# 建議場景結構：
#   MapView (Node2D)          ← 此腳本
#   ├── Sprite2D              ← 地圖圖片
#   ├── Camera2D
#   └── CanvasLayer (layer=1)
#       └── InfoLabel (Label) ← 左上角 UI（hero 座標 + 回合數）

@onready var sprite: Sprite2D   = $Sprite2D
@onready var camera: Camera2D   = $Camera2D
@onready var info_label: Label  = $CanvasLayer/InfoLabel

var world: OpenNefiaWorld
const CELL_PX := 16

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

    _setup_audio()
    _refresh_display()
    _refresh_ui()

    # 鏡頭置中
    camera.position = Vector2(world.get_map_width(), world.get_map_height()) \
                      * CELL_PX * 0.5

    print("F3+F4 ready — WASD/arrow/numpad 移動，. 等待")

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

func _on_world_changed() -> void:
    _refresh_display()
    _refresh_ui()
    # 正常移動音效（wait_turn 也會觸發，可依需求拆分信號）
    if sfx_step.stream:
        sfx_step.play()
    else:
        pass  # 無音效檔時靜默

func _on_hero_bumped_wall() -> void:
    if sfx_wall.stream:
        sfx_wall.play()
    else:
        print("* 碰牆 *")

func _on_hero_bumped_npc(npc_id: String) -> void:
    if sfx_bump_npc.stream:
        sfx_bump_npc.play()
    else:
        print("* 碰到 %s *" % npc_id)

func _refresh_display() -> void:
    var img := world.generate_map_image(CELL_PX)
    sprite.centered = false
    sprite.position = Vector2.ZERO
    sprite.texture  = ImageTexture.create_from_image(img)

func _refresh_ui() -> void:
    info_label.text = "Hero: (%d, %d)  Turn: %d" % [
        world.get_hero_x(),
        world.get_hero_y(),
        world.get_turn_count()
    ]
