## WorldMap2D：2D 俯視世界地圖場景。
##
## 場景結構：
##   WorldMap2D (Node2D)
##   ├── MapCoreGenerator          ← @export generator
##   ├── Camera2D                  ← @onready _camera
##   ├── Sprite2D (centered=false) ← @onready _sprite
##   └── CanvasLayer (layer=1)
##       └── InfoPanel (Label)     ← @onready _info
## 互動視覺層 MapOverlay2D 於 _ready() 動態加入（疊在 Sprite2D 之上）。
##
## 互動操作：
##   滑鼠移動         懸停高亮 + 資訊面板即時更新
##   左鍵             選取格子 + 高亮所屬 feature + 顯示區域名
##   Shift+左鍵       設路徑起點；再一次設終點 → 畫出 A* 路徑
##   右鍵             清除選取 / 路徑 / 高亮
##   L                切換全地圖 feature 標籤
##   中鍵拖曳 / 滾輪  平移 / 縮放
class_name WorldMap2D
extends Node2D

@export var generator: MapCoreGenerator
## 每格的像素大小（建議 4~16）
@export var cell_px: int = 8
## 河流最小強度：低於此值的細流(creek)不繪製。0=完整水系；80=濾掉 creek（預設）
@export var river_min_strength: int = 80
## feature 標籤只顯示面積 ≥ 此格數的區域（避免小區域標籤過密）
@export var label_min_size: int = 40
## feature 標籤數量上限（取面積最大的前幾個）
@export var label_max_count: int = 24

@onready var _camera: Camera2D = $Camera2D
@onready var _sprite: Sprite2D = $Sprite2D
@onready var _info: Label = $CanvasLayer/InfoPanel

var _map_data: MapCoreMapData
var _overlay: MapOverlay2D
var _feature_grid: PackedInt32Array = PackedInt32Array()  # 每格 feature_id 快取（避免逐格呼叫 C++）
var _mw: int = 0
var _mh: int = 0

var _hover: Vector2i = Vector2i(-1, -1)
var _selected: Vector2i = Vector2i(-1, -1)
var _path_pending_start: Vector2i = Vector2i(-1, -1)  # Shift+左鍵已設起點、待設終點

const _ZOOM_MIN := Vector2(0.25, 0.25)
const _ZOOM_MAX := Vector2(16.0, 16.0)

const _TERRAIN_NAMES := {
	0: "海洋", 1: "海岸", 2: "平原", 3: "草原",
	4: "沙漠", 5: "凍原", 6: "雪地", 7: "森林",
	8: "丘陵", 9: "山脈", 10: "湖泊",
}

const _LEGEND := "左鍵:選取  Shift+左鍵:路徑起/終點  右鍵:清除  L:標籤  中鍵拖曳:平移  滾輪:縮放"


func _ready() -> void:
	_sprite.centered = false
	_overlay = MapOverlay2D.new()
	_overlay.cell_px = cell_px
	add_child(_overlay)  # 加在 Sprite2D 之後 → 疊在地圖之上
	generator.generation_completed.connect(_on_generated)
	generator.generation_failed.connect(func(msg: String) -> void: push_error(msg))
	generator.generate_async()

# ── 地圖生成完成 ──────────────────────────────────────────────────────────────

func _on_generated(data: MapCoreMapData) -> void:
	_map_data = data
	var renderer := MapCoreWorldMap2DRenderer.new()
	var img := renderer.generate_terrain_image(data, cell_px)
	renderer.draw_rivers(img, data, cell_px, river_min_strength)
	_sprite.texture = ImageTexture.create_from_image(img)
	# 鏡頭初始置中
	_mw = data.get_width()
	_mh = data.get_height()
	_camera.position = Vector2(_mw, _mh) * cell_px * 0.5
	_overlay.map_data = data
	_build_feature_grid()
	_build_feature_labels()
	_overlay.queue_redraw()
	_update_info()
	print("WorldMap2D: 地圖渲染完成，size=%dx%d  seed=%d  features=%d" % [
		data.get_width(), data.get_height(), data.get_seed_used(), data.get_feature_count()])

# ── 輸入 ──────────────────────────────────────────────────────────────────────

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
			_camera.position -= event.relative / _camera.zoom
		_update_hover()
	elif event is InputEventMouseButton and event.pressed:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				_camera.zoom = (_camera.zoom * 1.15).clamp(_ZOOM_MIN, _ZOOM_MAX)
			MOUSE_BUTTON_WHEEL_DOWN:
				_camera.zoom = (_camera.zoom / 1.15).clamp(_ZOOM_MIN, _ZOOM_MAX)
			MOUSE_BUTTON_LEFT:
				if event.shift_pressed:
					_on_path_click()
				else:
					_on_select_click()
			MOUSE_BUTTON_RIGHT:
				_clear_interactions()
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_L:
			_overlay.show_labels = not _overlay.show_labels
			_overlay.queue_redraw()

# ── 座標換算 ──────────────────────────────────────────────────────────────────

# Sprite2D centered=false 且位於原點，世界座標直接對應像素座標。
func _cell_at_mouse() -> Vector2i:
	if not _map_data:
		return Vector2i(-1, -1)
	var world := get_global_mouse_position()
	var cx := int(floor(world.x / cell_px))
	var cy := int(floor(world.y / cell_px))
	if cx < 0 or cy < 0 or cx >= _map_data.get_width() or cy >= _map_data.get_height():
		return Vector2i(-1, -1)
	return Vector2i(cx, cy)

# ── 懸停 ──────────────────────────────────────────────────────────────────────

func _update_hover() -> void:
	var c := _cell_at_mouse()
	if c == _hover:
		return  # 只在跨格時重畫
	_hover = c
	_overlay.hover_cell = c
	_overlay.queue_redraw()
	_update_info()

# ── 選取 + feature 高亮 ───────────────────────────────────────────────────────

func _on_select_click() -> void:
	var c := _cell_at_mouse()
	if c.x < 0:
		return
	_selected = c
	_overlay.selected_cell = c
	_highlight_feature(c)
	_overlay.queue_redraw()
	_update_info()

func _highlight_feature(c: Vector2i) -> void:
	var seg := PackedVector2Array()
	var fid := _fid_at(c.x, c.y)
	if fid >= 0:
		var cp := float(cell_px)
		# 走訪整塊 feature，把與「非同 feature 鄰格」相鄰的邊收集成邊界線段
		for y in range(_mh):
			for x in range(_mw):
				if _fid_at(x, y) != fid:
					continue
				if _fid_at(x + 1, y) != fid:  # 右邊界
					seg.append(Vector2((x + 1) * cp, y * cp)); seg.append(Vector2((x + 1) * cp, (y + 1) * cp))
				if _fid_at(x - 1, y) != fid:  # 左邊界
					seg.append(Vector2(x * cp, y * cp)); seg.append(Vector2(x * cp, (y + 1) * cp))
				if _fid_at(x, y - 1) != fid:  # 上邊界
					seg.append(Vector2(x * cp, y * cp)); seg.append(Vector2((x + 1) * cp, y * cp))
				if _fid_at(x, y + 1) != fid:  # 下邊界
					seg.append(Vector2(x * cp, (y + 1) * cp)); seg.append(Vector2((x + 1) * cp, (y + 1) * cp))
	_overlay.feature_outline = seg

# ── 尋路 ──────────────────────────────────────────────────────────────────────

func _on_path_click() -> void:
	var c := _cell_at_mouse()
	if c.x < 0:
		return
	if _path_pending_start.x < 0:
		# 設起點，清掉上一條路徑
		_path_pending_start = c
		_overlay.path_start = c
		_overlay.path_goal = Vector2i(-1, -1)
		_overlay.path = []
	else:
		# 設終點並求路徑
		_overlay.path_goal = c
		var p := _map_data.find_path(_path_pending_start, c, 0.0)
		_overlay.path = p
		_path_pending_start = Vector2i(-1, -1)
		if p.is_empty():
			_info.text = "(%d,%d)→(%d,%d) 找不到路徑（可能被水域阻隔）\n%s" % [
				_overlay.path_start.x, _overlay.path_start.y, c.x, c.y, _LEGEND]
	_overlay.queue_redraw()

# ── 清除 ──────────────────────────────────────────────────────────────────────

func _clear_interactions() -> void:
	_selected = Vector2i(-1, -1)
	_path_pending_start = Vector2i(-1, -1)
	_overlay.selected_cell = Vector2i(-1, -1)
	_overlay.feature_outline = PackedVector2Array()
	_overlay.path_start = Vector2i(-1, -1)
	_overlay.path_goal = Vector2i(-1, -1)
	_overlay.path = []
	_overlay.queue_redraw()
	_update_info()

# ── feature 標籤快取 ──────────────────────────────────────────────────────────

func _fid_at(x: int, y: int) -> int:
	if x < 0 or y < 0 or x >= _mw or y >= _mh:
		return -1
	return _feature_grid[y * _mw + x]

func _build_feature_grid() -> void:
	_feature_grid = PackedInt32Array()
	_feature_grid.resize(_mw * _mh)
	for y in range(_mh):
		for x in range(_mw):
			_feature_grid[y * _mw + x] = _map_data.get_feature_id_at(x, y)

func _build_feature_labels() -> void:
	# 收集夠大的 feature，按面積由大到小取前 label_max_count 個，避免標籤過密
	var big := []
	for fid in range(_map_data.get_feature_count()):
		var info := _map_data.get_feature_info(fid)
		if info.has("name") and info.has("center") and int(info.get("size", 0)) >= label_min_size:
			big.append({ "name": info["name"], "pos": info["center"], "size": int(info["size"]) })
	big.sort_custom(func(a, b): return a["size"] > b["size"])
	var labels := []
	for f in big:
		if labels.size() >= label_max_count:
			break
		labels.append({ "name": f["name"], "pos": f["pos"] })
	_overlay.labels = labels

# ── 資訊面板 ──────────────────────────────────────────────────────────────────

func _update_info() -> void:
	var c := _hover if _hover.x >= 0 else _selected
	if not _map_data or c.x < 0:
		_info.text = _LEGEND
		return
	var t := _map_data.get_terrain(c.x, c.y)
	var h := _map_data.get_hilliness(c.x, c.y)
	var temp := _map_data.get_temperature(c.x, c.y)
	var rain := _map_data.get_rainfall(c.x, c.y)
	var s := "(%d, %d)  %s\n坡度: %d　溫度: %.1f°C　降雨: %.0f mm" % [
		c.x, c.y, _TERRAIN_NAMES.get(t, "?"), h, temp, rain]
	var fid := _fid_at(c.x, c.y)
	if fid >= 0:
		var info := _map_data.get_feature_info(fid)
		if info.has("name"):
			s += "　區域: %s" % info["name"]
	_info.text = s + "\n" + _LEGEND
