extends Node2D

# F3 地圖場景：輸入 → 核心移動 → Signal 刷新顯示。
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

func _ready() -> void:
    world = OpenNefiaWorld.new()
    world.name = "OpenNefiaWorld"
    add_child(world)

    world.world_changed.connect(_on_world_changed)

    _refresh_display()
    _refresh_ui()

    # 鏡頭置中
    camera.position = Vector2(world.get_map_width(), world.get_map_height()) \
                      * CELL_PX * 0.5

    print("F3 smoke test ready — use WASD / arrow keys / numpad to move, . to wait")

func _unhandled_input(event: InputEvent) -> void:
    if not (event is InputEventKey and event.pressed and not event.echo):
        return

    var moved := false
    match event.keycode:
        KEY_UP,    KEY_W, KEY_KP_8: moved = world.move( 0, -1)
        KEY_DOWN,  KEY_S, KEY_KP_2: moved = world.move( 0,  1)
        KEY_RIGHT, KEY_D, KEY_KP_6: moved = world.move( 1,  0)
        KEY_LEFT,  KEY_A, KEY_KP_4: moved = world.move(-1,  0)
        KEY_KP_7:                   moved = world.move(-1, -1)
        KEY_KP_9:                   moved = world.move( 1, -1)
        KEY_KP_1:                   moved = world.move(-1,  1)
        KEY_KP_3:                   moved = world.move( 1,  1)
        KEY_PERIOD, KEY_KP_5:
            world.wait_turn()
            moved = true

    if not moved and event.keycode in [
        KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
        KEY_W, KEY_A, KEY_S, KEY_D
    ]:
        print("blocked (wall)")

func _on_world_changed() -> void:
    _refresh_display()
    _refresh_ui()

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
