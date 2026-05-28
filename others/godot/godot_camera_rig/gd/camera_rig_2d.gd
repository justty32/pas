class_name CameraRig2D extends Node2D

# 可拆出複用的 2D 策略相機。與 mapcore demo 版的差異：
#   - 子節點走 @export 注入而非 $Camera2D 硬編路徑（也支援自動建立）
#   - InputMap 動作名稱全部 @export，外部 InputMap 可自由命名
#   - 補 CONCEPT 待決事項：shake 鏡頭晃動 API

signal focus_changed(world_pos: Vector2)

# ── 地圖邊界 ──────────────────────────────────────────────────────────────────
@export_group("地圖邊界")
@export var map_width: int = 100
@export var map_height: int = 100
@export var tile_size: float = 64.0
## 邊界 clamp 開關。關掉適合小場景或自由視角測試。
@export var clamp_to_bounds: bool = true

# ── Zoom ──────────────────────────────────────────────────────────────────────
@export_group("Zoom")
@export var zoom_min: float = 0.3
@export var zoom_max: float = 3.0
@export var zoom_step: float = 0.12
@export var zoom_lerp: float = 8.0

# ── Pan ───────────────────────────────────────────────────────────────────────
@export_group("Pan")
@export var pan_speed: float = 400.0
@export var mouse_pan_sensitivity: float = 1.0
@export var smoothing_speed: float = 8.0

# ── 邊緣滾動 ──────────────────────────────────────────────────────────────────
@export_group("邊緣滾動")
@export var edge_scroll_enabled: bool = false
@export var edge_scroll_margin: float = 20.0

# ── InputMap action 名稱（可被外部覆寫）──────────────────────────────────────
@export_group("InputMap 動作名稱")
@export var action_pan_left: StringName = &"cam_left"
@export var action_pan_right: StringName = &"cam_right"
@export var action_pan_up: StringName = &"cam_up"
@export var action_pan_down: StringName = &"cam_down"
@export var action_zoom_in: StringName = &"zoom_in"
@export var action_zoom_out: StringName = &"zoom_out"

# ── 子節點（可注入或自動建立）────────────────────────────────────────────────
@export_group("子節點")
@export var camera_node: Camera2D

# ── 內部狀態 ──────────────────────────────────────────────────────────────────
var _target_zoom: float = 1.0
var _dragging_pan: bool = false
var _shake_offset: Vector2 = Vector2.ZERO


func _ready() -> void:
	if camera_node == null:
		camera_node = Camera2D.new()
		camera_node.name = "Camera2D"
		add_child(camera_node)
	camera_node.position_smoothing_enabled = true
	camera_node.position_smoothing_speed = smoothing_speed
	camera_node.zoom = Vector2(_target_zoom, _target_zoom)


func _process(delta: float) -> void:
	_handle_keyboard_pan(delta)
	_handle_keyboard_zoom()
	if edge_scroll_enabled:
		_handle_edge_scroll(delta)
	if clamp_to_bounds:
		_clamp_to_map()
	camera_node.zoom = camera_node.zoom.lerp(
		Vector2(_target_zoom, _target_zoom), delta * zoom_lerp
	)
	camera_node.offset = _shake_offset


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
		position -= event.relative * mouse_pan_sensitivity / _target_zoom


# ── 鍵盤 ─────────────────────────────────────────────────────────────────────

func _handle_keyboard_pan(delta: float) -> void:
	var dir := Vector2.ZERO
	if InputMap.has_action(action_pan_left) and Input.is_action_pressed(action_pan_left):
		dir.x -= 1
	if InputMap.has_action(action_pan_right) and Input.is_action_pressed(action_pan_right):
		dir.x += 1
	if InputMap.has_action(action_pan_up) and Input.is_action_pressed(action_pan_up):
		dir.y -= 1
	if InputMap.has_action(action_pan_down) and Input.is_action_pressed(action_pan_down):
		dir.y += 1
	if dir != Vector2.ZERO:
		position += dir.normalized() * pan_speed * delta / _target_zoom


func _handle_keyboard_zoom() -> void:
	if not InputMap.has_action(action_zoom_in) or not InputMap.has_action(action_zoom_out):
		return
	var scroll := Input.get_axis(action_zoom_out, action_zoom_in)
	if scroll != 0.0:
		_target_zoom = clamp(_target_zoom * (1.0 + scroll * zoom_step), zoom_min, zoom_max)


func _handle_edge_scroll(delta: float) -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var mouse := get_viewport().get_mouse_position()
	var dir := Vector2.ZERO
	var m := edge_scroll_margin
	if mouse.x < m:
		dir.x = -1
	elif mouse.x > vp_size.x - m:
		dir.x = 1
	if mouse.y < m:
		dir.y = -1
	elif mouse.y > vp_size.y - m:
		dir.y = 1
	if dir != Vector2.ZERO:
		position += dir.normalized() * pan_speed * delta / _target_zoom


func _clamp_to_map() -> void:
	var half_view := get_viewport_rect().size * 0.5 / _target_zoom
	position.x = clamp(position.x, half_view.x, map_width * tile_size - half_view.x)
	position.y = clamp(position.y, half_view.y, map_height * tile_size - half_view.y)


# ── 對外統一介面 ─────────────────────────────────────────────────────────────

func focus(world_pos: Vector2, instant: bool = false) -> void:
	if instant:
		position = world_pos
	else:
		create_tween() \
			.tween_property(self, "position", world_pos, 0.4) \
			.set_trans(Tween.TRANS_CUBIC)
	focus_changed.emit(world_pos)


func get_focus_point() -> Vector2:
	return position


func get_zoom_normalized() -> float:
	return clamp((_target_zoom - zoom_min) / (zoom_max - zoom_min), 0.0, 1.0)


# 鏡頭晃動：在 camera.offset 上加衰減的隨機偏移。
# amplitude: 最大像素偏移；duration: 秒。
func shake(amplitude: float = 8.0, duration: float = 0.3) -> void:
	var t := 0.0
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var tween := create_tween()
	tween.tween_method(func(progress: float) -> void:
		var k := 1.0 - progress
		_shake_offset = Vector2(
			rng.randf_range(-1.0, 1.0),
			rng.randf_range(-1.0, 1.0)
		) * amplitude * k
	, 0.0, 1.0, duration)
	tween.tween_callback(func() -> void: _shake_offset = Vector2.ZERO)
