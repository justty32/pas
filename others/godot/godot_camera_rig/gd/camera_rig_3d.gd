class_name CameraRig3D extends Node3D

# 可拆出複用的 3D 策略相機。與 mapcore demo 版的差異：
#   - CameraArm 與 Camera3D 走 @export 注入（也支援自動建立）
#   - InputMap 動作名稱全部 @export
#   - 補 CONCEPT 待決事項：正交/透視投影切換、shake 鏡頭晃動

signal focus_changed(world_pos: Vector3)

# ── 地圖邊界 ──────────────────────────────────────────────────────────────────
@export_group("地圖邊界")
@export var map_width: float = 64.0
@export var map_depth: float = 48.0
@export var clamp_to_bounds: bool = true

# ── Zoom ──────────────────────────────────────────────────────────────────────
@export_group("Zoom")
@export var zoom_min: float = 5.0
@export var zoom_max: float = 40.0
@export var zoom_speed: float = 5.0
@export var zoom_initial: float = 20.0

# ── 旋轉 ──────────────────────────────────────────────────────────────────────
@export_group("旋轉")
@export var elevation_min: float = 20.0
@export var elevation_max: float = 85.0
@export var elevation_initial: float = 55.0
## 鎖定仰角（Civ 6 風格）。鎖定後 tilt 鍵 / 右鍵拖曳垂直分量不生效。
@export var lock_elevation: bool = false
@export var rotate_speed: float = 90.0

# ── Pan ───────────────────────────────────────────────────────────────────────
@export_group("Pan")
@export var pan_speed: float = 20.0

# ── 投影 ──────────────────────────────────────────────────────────────────────
@export_group("投影")
## true = 正交（棋盤感），false = 透視。切換會即時套用。
@export var use_orthographic: bool = false:
	set(v):
		use_orthographic = v
		if camera_node:
			_apply_projection()
## 正交模式的視野半徑（單位 = 世界座標）。透視模式忽略此值。
@export var orthographic_size_per_unit_zoom: float = 0.8

# ── 邊緣滾動 ──────────────────────────────────────────────────────────────────
@export_group("邊緣滾動")
@export var edge_scroll_enabled: bool = false
@export var edge_scroll_margin: float = 20.0

# ── 滑鼠靈敏度 ────────────────────────────────────────────────────────────────
@export_group("滑鼠靈敏度")
@export var mouse_pan_sensitivity: float = 0.03
@export var mouse_rotate_sensitivity: float = 0.3

# ── InputMap action 名稱 ──────────────────────────────────────────────────────
@export_group("InputMap 動作名稱")
@export var action_pan_forward: StringName = &"cam_forward"
@export var action_pan_back: StringName = &"cam_back"
@export var action_pan_left: StringName = &"cam_left"
@export var action_pan_right: StringName = &"cam_right"
@export var action_rotate_left: StringName = &"cam_rotate_left"
@export var action_rotate_right: StringName = &"cam_rotate_right"
@export var action_tilt_up: StringName = &"cam_tilt_up"
@export var action_tilt_down: StringName = &"cam_tilt_down"
@export var action_zoom_in: StringName = &"zoom_in"
@export var action_zoom_out: StringName = &"zoom_out"

# ── 子節點 ────────────────────────────────────────────────────────────────────
@export_group("子節點")
@export var camera_arm: Node3D
@export var camera_node: Camera3D

# ── 內部狀態 ──────────────────────────────────────────────────────────────────
var _zoom: float
var _elevation: float
var _yaw: float = 0.0
var _dragging_pan: bool = false
var _dragging_rotate: bool = false
var _shake_offset: Vector3 = Vector3.ZERO


func _ready() -> void:
	if camera_arm == null:
		camera_arm = Node3D.new()
		camera_arm.name = "CameraArm"
		add_child(camera_arm)
	if camera_node == null:
		camera_node = Camera3D.new()
		camera_node.name = "Camera3D"
		camera_arm.add_child(camera_node)
	_zoom = zoom_initial
	_elevation = elevation_initial
	_apply_projection()
	_apply_camera_transform()


func _process(delta: float) -> void:
	_handle_keyboard_pan(delta)
	_handle_keyboard_rotate(delta)
	_handle_keyboard_zoom(delta)
	if edge_scroll_enabled:
		_handle_edge_scroll(delta)
	if clamp_to_bounds:
		_clamp_to_map()
	_apply_camera_transform()


func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				_zoom = clamp(_zoom - zoom_speed * 0.5, zoom_min, zoom_max)
			MOUSE_BUTTON_WHEEL_DOWN:
				_zoom = clamp(_zoom + zoom_speed * 0.5, zoom_min, zoom_max)
			MOUSE_BUTTON_MIDDLE:
				_dragging_pan = event.pressed
			MOUSE_BUTTON_RIGHT:
				_dragging_rotate = event.pressed
	elif event is InputEventMouseMotion:
		if _dragging_pan:
			_mouse_pan(event.relative)
		if _dragging_rotate:
			_yaw += event.relative.x * mouse_rotate_sensitivity
			if not lock_elevation:
				_elevation = clamp(
					_elevation - event.relative.y * mouse_rotate_sensitivity,
					elevation_min, elevation_max
				)


# ── 鍵盤 ─────────────────────────────────────────────────────────────────────

func _basis_vectors() -> Array:
	var fwd := Vector3(-sin(deg_to_rad(_yaw)), 0.0, -cos(deg_to_rad(_yaw)))
	var rgt := Vector3(cos(deg_to_rad(_yaw)), 0.0, -sin(deg_to_rad(_yaw)))
	return [fwd, rgt]


func _handle_keyboard_pan(delta: float) -> void:
	var bv := _basis_vectors()
	var fwd: Vector3 = bv[0]
	var rgt: Vector3 = bv[1]
	var speed := pan_speed * (_zoom / 20.0)
	if _action_pressed(action_pan_forward):
		position += fwd * speed * delta
	if _action_pressed(action_pan_back):
		position -= fwd * speed * delta
	if _action_pressed(action_pan_left):
		position -= rgt * speed * delta
	if _action_pressed(action_pan_right):
		position += rgt * speed * delta


func _handle_keyboard_rotate(delta: float) -> void:
	if _action_pressed(action_rotate_left):
		_yaw -= rotate_speed * delta
	if _action_pressed(action_rotate_right):
		_yaw += rotate_speed * delta
	if lock_elevation:
		return
	if _action_pressed(action_tilt_up):
		_elevation = clamp(_elevation + rotate_speed * delta, elevation_min, elevation_max)
	if _action_pressed(action_tilt_down):
		_elevation = clamp(_elevation - rotate_speed * delta, elevation_min, elevation_max)


func _handle_keyboard_zoom(delta: float) -> void:
	if _action_pressed(action_zoom_in):
		_zoom = clamp(_zoom - zoom_speed * delta, zoom_min, zoom_max)
	if _action_pressed(action_zoom_out):
		_zoom = clamp(_zoom + zoom_speed * delta, zoom_min, zoom_max)


func _mouse_pan(relative: Vector2) -> void:
	var bv := _basis_vectors()
	var fwd: Vector3 = bv[0]
	var rgt: Vector3 = bv[1]
	var speed := _zoom * mouse_pan_sensitivity
	position -= rgt * relative.x * speed
	position += fwd * relative.y * speed


func _handle_edge_scroll(delta: float) -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var mouse := get_viewport().get_mouse_position()
	var bv := _basis_vectors()
	var fwd: Vector3 = bv[0]
	var rgt: Vector3 = bv[1]
	var speed := pan_speed * (_zoom / 20.0)
	var m := edge_scroll_margin
	if mouse.x < m:
		position -= rgt * speed * delta
	elif mouse.x > vp_size.x - m:
		position += rgt * speed * delta
	if mouse.y < m:
		position += fwd * speed * delta
	elif mouse.y > vp_size.y - m:
		position -= fwd * speed * delta


func _clamp_to_map() -> void:
	position.x = clamp(position.x, 0.0, map_width)
	position.z = clamp(position.z, 0.0, map_depth)
	position.y = 0.0


# ── Transform 與投影 ─────────────────────────────────────────────────────────

func _apply_camera_transform() -> void:
	camera_arm.rotation.y = deg_to_rad(_yaw)
	var elev_rad := deg_to_rad(_elevation)
	camera_node.position = Vector3(0.0, sin(elev_rad) * _zoom, cos(elev_rad) * _zoom) + _shake_offset
	camera_node.rotation.x = deg_to_rad(-_elevation)
	if use_orthographic:
		camera_node.size = _zoom * orthographic_size_per_unit_zoom


func _apply_projection() -> void:
	camera_node.projection = (
		Camera3D.PROJECTION_ORTHOGONAL if use_orthographic
		else Camera3D.PROJECTION_PERSPECTIVE
	)


# ── 對外統一介面 ─────────────────────────────────────────────────────────────

func focus(world_pos: Vector3, instant: bool = false) -> void:
	var target := Vector3(world_pos.x, 0.0, world_pos.z)
	if instant:
		position = target
	else:
		create_tween() \
			.tween_property(self, "position", target, 0.5) \
			.set_trans(Tween.TRANS_CUBIC)
	focus_changed.emit(target)


func get_focus_point() -> Vector3:
	return Vector3(position.x, 0.0, position.z)


func get_zoom_normalized() -> float:
	return 1.0 - clamp((_zoom - zoom_min) / (zoom_max - zoom_min), 0.0, 1.0)


func shake(amplitude: float = 0.3, duration: float = 0.3) -> void:
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var tween := create_tween()
	tween.tween_method(func(progress: float) -> void:
		var k := 1.0 - progress
		_shake_offset = Vector3(
			rng.randf_range(-1.0, 1.0),
			rng.randf_range(-1.0, 1.0),
			rng.randf_range(-1.0, 1.0)
		) * amplitude * k
	, 0.0, 1.0, duration)
	tween.tween_callback(func() -> void: _shake_offset = Vector3.ZERO)


# ── 小工具 ───────────────────────────────────────────────────────────────────

func _action_pressed(action: StringName) -> bool:
	return InputMap.has_action(action) and Input.is_action_pressed(action)
