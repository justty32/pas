extends Node2D

# 將此腳本掛在根節點（Node2D）。
# 場景結構：
#   MapView (Node2D)         ← 此腳本
#   ├── OpenNefiaWorld       ← 動態建立的 C++ Node
#   ├── Sprite2D             ← 顯示地圖圖片
#   └── Camera2D             ← 置中鏡頭

@onready var sprite: Sprite2D = $Sprite2D
@onready var camera: Camera2D = $Camera2D

var world: OpenNefiaWorld
var cell_px := 16

func _ready() -> void:
    # 建立並加入 OpenNefiaWorld（_ready 在 add_child 後被立即呼叫）
    world = OpenNefiaWorld.new()
    add_child(world)

    var w := world.get_map_width()
    var h := world.get_map_height()
    print("map size: %d x %d" % [w, h])
    print("center walkable: ", world.is_walkable(w / 2, h / 2))
    print("corner walkable: ", world.is_walkable(0, 0))

    # 生成地圖圖片並設為 Sprite2D 的貼圖
    var img := world.generate_map_image(cell_px)
    sprite.centered = false
    sprite.position = Vector2.ZERO
    sprite.texture  = ImageTexture.create_from_image(img)

    # 鏡頭置中
    camera.position = Vector2(w, h) * cell_px * 0.5

    print("F2 map render smoke test PASSED")
