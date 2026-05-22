## WorldMap2D：2D 俯視世界地圖場景。
##
## 場景結構：
##   WorldMap2D (Node2D)
##   ├── MapCoreGenerator          ← @export generator
##   ├── Camera2D                  ← @onready _camera
##   ├── Sprite2D (centered=false) ← @onready _sprite
##   └── CanvasLayer (layer=1)
##       └── InfoPanel (Label)     ← @onready _info
class_name WorldMap2D
extends Node2D

@export var generator: MapCoreGenerator
## 每格的像素大小（建議 4~16）
@export var cell_px: int = 8

@onready var _camera: Camera2D = $Camera2D
@onready var _sprite: Sprite2D = $Sprite2D
@onready var _info: Label = $CanvasLayer/InfoPanel

var _map_data: MapCoreMapData

const _TERRAIN_NAMES := {
	0: "海洋", 1: "海岸", 2: "平原", 3: "草原",
	4: "沙漠", 5: "凍原", 6: "雪地", 7: "森林",
	8: "丘陵", 9: "山脈", 10: "湖泊",
}

func _ready() -> void:
	_sprite.centered = false
	generator.generation_completed.connect(_on_generated)
	generator.generation_failed.connect(func(msg: String) -> void: push_error(msg))
	generator.generate_async()

# ── 地圖生成完成 ──────────────────────────────────────────────────────────────

func _on_generated(data: MapCoreMapData) -> void:
	_map_data = data
	var renderer := MapCoreWorldMap2DRenderer.new()
	var img := renderer.generate_terrain_image(data, cell_px)
	renderer.draw_rivers(img, data, cell_px)
	_sprite.texture = ImageTexture.create_from_image(img)
	# 鏡頭初始置中
	_camera.position = Vector2(data.get_width(), data.get_height()) * cell_px * 0.5
	print("WorldMap2D: 地圖渲染完成，size=%dx%d  seed=%d" % [
		data.get_width(), data.get_height(), data.get_seed_used()])

# ── 輸入：Pan / Zoom / 點擊查詢 ───────────────────────────────────────────────

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
			_camera.position -= event.relative / _camera.zoom
	elif event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				_camera.zoom = (_camera.zoom * 1.15).clamp(Vector2(0.25, 0.25), Vector2(16.0, 16.0))
			MOUSE_BUTTON_WHEEL_DOWN:
				_camera.zoom = (_camera.zoom / 1.15).clamp(Vector2(0.25, 0.25), Vector2(16.0, 16.0))
			MOUSE_BUTTON_LEFT:
				if event.pressed:
					_on_map_clicked()

func _on_map_clicked() -> void:
	if not _map_data:
		return
	# Sprite2D centered=false 且位於原點，世界座標直接對應像素座標
	var world := get_global_mouse_position()
	var cx := int(world.x) / cell_px
	var cy := int(world.y) / cell_px
	if cx < 0 or cy < 0 or cx >= _map_data.get_width() or cy >= _map_data.get_height():
		_info.text = ""
		return
	var t    := _map_data.get_terrain(cx, cy)
	var h    := _map_data.get_hilliness(cx, cy)
	var temp := _map_data.get_temperature(cx, cy)
	var rain := _map_data.get_rainfall(cx, cy)
	_info.text = "(%d, %d)  %s\n坡度: %d　溫度: %.1f°C　降雨: %.0f mm" % [
		cx, cy, _TERRAIN_NAMES.get(t, "?"), h, temp, rain,
	]
