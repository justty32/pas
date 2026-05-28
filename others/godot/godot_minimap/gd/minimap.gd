class_name Minimap extends Control

# CONCEPT 方案 B 的落地：從 mapcore 資料生 Image，HUD 用 TextureRect 顯示。
#
# 四層堆疊：
#   ├── _terrain_rect (TextureRect)     ← 地形底色（mapcore C++ 渲染或本檔 GDScript 後備）
#   ├── _unit_rect    (TextureRect)     ← 單位點疊加層（陣營色）
#   ├── _fog_rect     (TextureRect)     ← 迷霧遮罩（可選）
#   └── _viewport_rect (自繪 Control)   ← 攝影機視野框（_draw 即時）
#
# 點擊發 signal 由外部呼叫 camera.focus()。

signal map_clicked(world_pos: Vector2)

@export var map_data: MapCoreMapData
## 是否使用 mapcore C++ 端的 MapCoreWorldMap2DRenderer（含河流），否則走 GDScript 後備。
@export var use_mapcore_renderer: bool = true
## 每格邊長像素。1 = 一格一像素（最小 minimap）；4~8 = 看細節。
@export var cell_px: int = 1
## 河流最小強度（搭配 mapcore CREEK_THRESHOLD，僅在 use_mapcore_renderer=true 用）。
@export var river_min_strength: int = 80

@export_group("視野框")
## 提供 get_focus_point() 與 get_zoom_normalized() 的相機（CameraRig2D 或 CameraRig3D）。
@export var camera_rig: Node
@export var viewport_color: Color = Color(1.0, 1.0, 1.0, 0.9)
@export var viewport_width: float = 1.5
## zoom_normalized=0（最遠）對應視野框佔 minimap 寬度的比例。
@export var viewport_frac_far: float = 0.7
## zoom_normalized=1（最近）對應的比例。
@export var viewport_frac_near: float = 0.15

# ── 內部 ──────────────────────────────────────────────────────────────────
var _terrain_rect: TextureRect
var _unit_rect: TextureRect
var _fog_rect: TextureRect

var _terrain_img: Image
var _unit_img: Image
var _fog_img: Image

var _unit_tex: ImageTexture
var _fog_tex: ImageTexture


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP  # minimap 自己吃點擊
	_terrain_rect = _make_rect("Terrain")
	_unit_rect = _make_rect("Unit")
	_fog_rect = _make_rect("Fog")
	if map_data:
		mount(map_data)


# 主入口：map_data 變更時呼叫。
func mount(data: MapCoreMapData) -> void:
	map_data = data
	_build_terrain_layer()
	_build_unit_layer()
	_build_fog_layer()


# ── 單位疊加 ──────────────────────────────────────────────────────────────

# units 形態：Array of {cell: Vector2i, faction: String}
func update_units(units: Array) -> void:
	if _unit_img == null or map_data == null:
		return
	_unit_img.fill(Color(0, 0, 0, 0))
	for unit in units:
		var cell: Vector2i = unit.get("cell")
		var faction_name: String = unit.get("faction", "neutral")
		if cell.x < 0 or cell.x >= map_data.get_width() or cell.y < 0 or cell.y >= map_data.get_height():
			continue
		_paint_cell(_unit_img, cell, MinimapPalette.faction(faction_name))
	_unit_tex.update(_unit_img)


# ── 迷霧 ──────────────────────────────────────────────────────────────────

# visibility 形態：PackedByteArray，長度 = w × h，每格 0=hidden / 1=explored / 2=visible
func update_fog(visibility: PackedByteArray) -> void:
	if _fog_img == null or map_data == null:
		return
	_fog_img.fill(Color(0, 0, 0, 0))
	var w := map_data.get_width()
	var h := map_data.get_height()
	if visibility.size() != w * h:
		push_warning("Minimap.update_fog: visibility 長度 %d 與地圖 %d×%d 不符" % [visibility.size(), w, h])
		return
	for i in visibility.size():
		var x := i % w
		var y := i / w
		var col: Color
		match visibility[i]:
			0: col = Color(0, 0, 0, 1.0)
			1: col = Color(0, 0, 0, 0.55)
			_: continue  # 2 = visible，透明
		_paint_cell(_fog_img, Vector2i(x, y), col)
	_fog_tex.update(_fog_img)


# ── 攝影機視野框 ──────────────────────────────────────────────────────────

func _process(_delta: float) -> void:
	if camera_rig:
		queue_redraw()


func _draw() -> void:
	if camera_rig == null or map_data == null:
		return
	if not camera_rig.has_method(&"get_focus_point") or not camera_rig.has_method(&"get_zoom_normalized"):
		return
	var focus = camera_rig.get_focus_point()
	var zoom_n: float = camera_rig.get_zoom_normalized()

	var map_w := map_data.get_width()
	var map_h := map_data.get_height()
	var focus_xy := _focus_to_grid(focus, map_w, map_h)
	var focus_screen := Vector2(
		focus_xy.x / map_w * size.x,
		focus_xy.y / map_h * size.y
	)
	var frac := lerp(viewport_frac_far, viewport_frac_near, zoom_n)
	var rect_size := size * frac
	var rect := Rect2(focus_screen - rect_size * 0.5, rect_size)
	draw_rect(rect, viewport_color, false, viewport_width)


# 把 Vector2/Vector3 focus 轉成格座標。CameraRig2D 用 tile_size；3D 直接 X/Z。
func _focus_to_grid(focus, map_w: int, map_h: int) -> Vector2:
	if focus is Vector2:
		var ts: float = camera_rig.get("tile_size") if "tile_size" in camera_rig else 1.0
		return Vector2(focus.x / ts, focus.y / ts)
	if focus is Vector3:
		return Vector2(focus.x, focus.z)
	return Vector2(map_w * 0.5, map_h * 0.5)


# ── 點擊 ──────────────────────────────────────────────────────────────────

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			_emit_click(mb.position)


func _emit_click(local_pos: Vector2) -> void:
	if map_data == null:
		return
	var map_w := map_data.get_width()
	var map_h := map_data.get_height()
	var ratio := local_pos / size
	# 回傳「世界座標」：3D 用 (x, z)、2D 用 (x, y)，
	# 兩者皆是 Vector2，呼叫端依相機型別決定怎麼用（Vector3 時補 0 Y）。
	var world := Vector2(ratio.x * map_w, ratio.y * map_h)
	map_clicked.emit(world)


# ── 內部建層 ──────────────────────────────────────────────────────────────

func _make_rect(rect_name: String) -> TextureRect:
	var r := TextureRect.new()
	r.name = rect_name
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE  # 點擊穿透到 Minimap 自己
	add_child(r)
	return r


func _build_terrain_layer() -> void:
	if use_mapcore_renderer and ClassDB.class_exists("MapCoreWorldMap2DRenderer"):
		var renderer := ClassDB.instantiate("MapCoreWorldMap2DRenderer")
		_terrain_img = renderer.generate_terrain_image(map_data, cell_px)
		renderer.draw_rivers(_terrain_img, map_data, cell_px, river_min_strength)
	else:
		_terrain_img = _gdscript_terrain_image()
	_terrain_rect.texture = ImageTexture.create_from_image(_terrain_img)


# GDScript 後備：mapcore C++ 不可用時純 GDScript 渲染（無河流）。
func _gdscript_terrain_image() -> Image:
	var w := map_data.get_width()
	var h := map_data.get_height()
	var img := Image.create(w * cell_px, h * cell_px, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var col := MinimapPalette.terrain(map_data.get_terrain(x, y))
			for dy in cell_px:
				for dx in cell_px:
					img.set_pixel(x * cell_px + dx, y * cell_px + dy, col)
	return img


func _build_unit_layer() -> void:
	var w := map_data.get_width() * cell_px
	var h := map_data.get_height() * cell_px
	_unit_img = Image.create(w, h, false, Image.FORMAT_RGBA8)
	_unit_img.fill(Color(0, 0, 0, 0))
	_unit_tex = ImageTexture.create_from_image(_unit_img)
	_unit_rect.texture = _unit_tex


func _build_fog_layer() -> void:
	var w := map_data.get_width() * cell_px
	var h := map_data.get_height() * cell_px
	_fog_img = Image.create(w, h, false, Image.FORMAT_RGBA8)
	_fog_img.fill(Color(0, 0, 0, 0))
	_fog_tex = ImageTexture.create_from_image(_fog_img)
	_fog_rect.texture = _fog_tex


func _paint_cell(img: Image, cell: Vector2i, color: Color) -> void:
	# cell 是地圖格座標，要乘 cell_px 變 image 像素座標
	var base_x := cell.x * cell_px
	var base_y := cell.y * cell_px
	for dy in cell_px:
		for dx in cell_px:
			img.set_pixel(base_x + dx, base_y + dy, color)
