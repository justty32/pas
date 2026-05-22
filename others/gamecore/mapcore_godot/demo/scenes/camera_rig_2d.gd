## 策略遊戲 2D Camera Rig
##
## 節點結構（需在場景中手動建立）：
##   CameraRig2D (Node2D) ← 此腳本掛在此節點上
##   └── Camera2D
##         position_smoothing_enabled = true
##         position_smoothing_speed   = 8.0
##
## 必要的 InputMap 動作：
##   cam_left / cam_right / cam_up / cam_down  ← 方向鍵或 WASD
##   zoom_in / zoom_out                        ← 滾輪或 +/-
##
## 滑鼠操作：
##   中鍵拖曳 → Pan    滾輪 → Zoom
class_name CameraRig2D
extends Node2D

# ── 地圖邊界 ──────────────────────────────────────────────────────────────────
@export_group("地圖邊界")
@export var map_width:  int   = 100
@export var map_height: int   = 100
@export var tile_size:  float = 64.0

# ── Zoom ──────────────────────────────────────────────────────────────────────
@export_group("Zoom")
@export var zoom_min:   float = 0.3
@export var zoom_max:   float = 3.0
## 每次滾輪觸發的縮放倍率增量（例如 0.1 = 10%）
@export var zoom_step:  float = 0.12
## 縮放平滑速度（lerp 係數，越高越快）
@export var zoom_lerp:  float = 8.0

# ── Pan ───────────────────────────────────────────────────────────────────────
@export_group("Pan")
@export var pan_speed:              float = 400.0
@export var mouse_pan_sensitivity:  float = 1.0

# ── 邊緣滾動 ──────────────────────────────────────────────────────────────────
@export_group("邊緣滾動")
@export var edge_scroll_enabled: bool  = false
@export var edge_scroll_margin:  float = 20.0

# ── 內部狀態 ──────────────────────────────────────────────────────────────────
var _target_zoom:     float = 1.0
var _dragging_pan:    bool  = false

# ── 初始化 ────────────────────────────────────────────────────────────────────

func _ready() -> void:
	$Camera2D.zoom = Vector2(_target_zoom, _target_zoom)

# ── 每幀更新 ──────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	_handle_keyboard_pan(delta)
	_handle_keyboard_zoom()
	if edge_scroll_enabled:
		_handle_edge_scroll(delta)
	_clamp_to_map()
	# Zoom 平滑插值（Camera2D 的 position_smoothing 處理位置插值）
	$Camera2D.zoom = $Camera2D.zoom.lerp(
		Vector2(_target_zoom, _target_zoom), delta * zoom_lerp
	)

# ── 滑鼠輸入 ──────────────────────────────────────────────────────────────────

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				_target_zoom = clamp(_target_zoom * (1.0 + zoom_step), zoom_min, zoom_max)
			MOUSE_BUTTON_WHEEL_DOWN:
				_target_zoom = clamp(_target_zoom * (1.0 - zoom_step), zoom_min, zoom_max)
			MOUSE_BUTTON_MIDDLE:
				_dragging_pan = event.pressed

	elif event is InputEventMouseMotion and _dragging_pan:
		# 中鍵拖曳：以 zoom 補償確保拖曳量與畫面移動量一致
		position -= event.relative * mouse_pan_sensitivity / _target_zoom

# ── 鍵盤處理 ──────────────────────────────────────────────────────────────────

func _handle_keyboard_pan(delta: float) -> void:
	var dir := Vector2.ZERO
	if Input.is_action_pressed("cam_left"):  dir.x -= 1
	if Input.is_action_pressed("cam_right"): dir.x += 1
	if Input.is_action_pressed("cam_up"):    dir.y -= 1
	if Input.is_action_pressed("cam_down"):  dir.y += 1
	# zoom 越大（越近）pan 越慢，保持一致的「格子/秒」感
	if dir != Vector2.ZERO:
		position += dir.normalized() * pan_speed * delta / _target_zoom

func _handle_keyboard_zoom() -> void:
	var scroll := Input.get_axis("zoom_out", "zoom_in")
	if scroll != 0.0:
		_target_zoom = clamp(_target_zoom * (1.0 + scroll * zoom_step), zoom_min, zoom_max)

func _handle_edge_scroll(delta: float) -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var mouse   := get_viewport().get_mouse_position()
	var dir     := Vector2.ZERO
	var m       := edge_scroll_margin
	if   mouse.x < m:                dir.x = -1
	elif mouse.x > vp_size.x - m:    dir.x =  1
	if   mouse.y < m:                dir.y = -1
	elif mouse.y > vp_size.y - m:    dir.y =  1
	if dir != Vector2.ZERO:
		position += dir.normalized() * pan_speed * delta / _target_zoom

# ── 邊界 ──────────────────────────────────────────────────────────────────────

func _clamp_to_map() -> void:
	# 確保相機不超出地圖邊界（考慮當前 zoom 的可視半視野大小）
	var half_view := get_viewport_rect().size * 0.5 / _target_zoom
	position.x = clamp(position.x, half_view.x, map_width  * tile_size - half_view.x)
	position.y = clamp(position.y, half_view.y, map_height * tile_size - half_view.y)

# ── 對外統一介面（與 CameraRig3D 相同概念，型別不同）────────────────────────

## 平滑移動到世界位置
func focus(world_pos: Vector2, instant: bool = false) -> void:
	if instant:
		position = world_pos
	else:
		create_tween() \
			.tween_property(self, "position", world_pos, 0.4) \
			.set_trans(Tween.TRANS_CUBIC)

## 當前視野中心（世界座標）
func get_focus_point() -> Vector2:
	return position

## 縮放等級 0.0（最遠）~ 1.0（最近）
func get_zoom_normalized() -> float:
	return clamp((_target_zoom - zoom_min) / (zoom_max - zoom_min), 0.0, 1.0)
