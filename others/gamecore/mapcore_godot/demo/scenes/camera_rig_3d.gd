## 策略遊戲 3D Camera Rig
##
## 節點結構（需在場景中手動建立）：
##   CameraRig3D (Node3D) ← 此腳本掛在此節點上
##   └── CameraArm (Node3D)
##       └── Camera3D
##
## 必要的 InputMap 動作（ProjectSettings → Input Map 中定義）：
##   cam_forward / cam_back / cam_left / cam_right  ← WASD 或方向鍵
##   cam_rotate_left / cam_rotate_right             ← Q/E
##   cam_tilt_up / cam_tilt_down                    ← R/F（選用）
##   zoom_in / zoom_out                             ← 滾輪或 +/-
##
## 滑鼠操作（無需額外定義）：
##   中鍵拖曳 → Pan    右鍵拖曳 → 旋轉 / 仰角    滾輪 → Zoom
class_name CameraRig3D
extends Node3D

# ── 地圖邊界 ──────────────────────────────────────────────────────────────────
@export_group("地圖邊界")
@export var map_width: float  = 64.0
@export var map_depth: float  = 48.0

# ── Zoom ──────────────────────────────────────────────────────────────────────
@export_group("Zoom")
@export var zoom_min:   float = 5.0
@export var zoom_max:   float = 40.0
@export var zoom_speed: float = 5.0

# ── 旋轉限制 ──────────────────────────────────────────────────────────────────
@export_group("旋轉")
@export var elevation_min: float = 20.0   # 最平（接近水平）
@export var elevation_max: float = 85.0   # 最陡（幾乎俯視）
@export var rotate_speed:  float = 90.0   # deg/s（鍵盤）

# ── Pan ───────────────────────────────────────────────────────────────────────
@export_group("Pan")
@export var pan_speed: float = 20.0

# ── 邊緣滾動 ──────────────────────────────────────────────────────────────────
@export_group("邊緣滾動")
@export var edge_scroll_enabled: bool  = false
@export var edge_scroll_margin:  float = 20.0  # 螢幕邊緣觸發像素數

# ── 滑鼠靈敏度 ────────────────────────────────────────────────────────────────
@export_group("滑鼠靈敏度")
## 中鍵拖曳 Pan 靈敏度；依地圖大小調整
@export var mouse_pan_sensitivity:    float = 0.03
## 右鍵拖曳旋轉靈敏度（deg/pixel）
@export var mouse_rotate_sensitivity: float = 0.3

# ── 內部狀態 ──────────────────────────────────────────────────────────────────
var _zoom:      float = 20.0
var _elevation: float = 55.0   # degrees
var _yaw:       float = 0.0    # degrees

var _dragging_pan:    bool = false
var _dragging_rotate: bool = false

# ── 初始化 ────────────────────────────────────────────────────────────────────

func _ready() -> void:
	_apply_camera_transform()

# ── 每幀更新 ──────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	_handle_keyboard_pan(delta)
	_handle_keyboard_rotate(delta)
	_handle_keyboard_zoom(delta)
	if edge_scroll_enabled:
		_handle_edge_scroll(delta)
	_clamp_to_map()
	_apply_camera_transform()

# ── 滑鼠輸入 ──────────────────────────────────────────────────────────────────

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
			_yaw       += event.relative.x * mouse_rotate_sensitivity
			_elevation  = clamp(
				_elevation - event.relative.y * mouse_rotate_sensitivity,
				elevation_min, elevation_max
			)

# ── 鍵盤處理 ──────────────────────────────────────────────────────────────────

func _handle_keyboard_pan(delta: float) -> void:
	# Pan 方向跟隨 _yaw，讓 WASD 永遠對應螢幕前後左右
	var forward := Vector3(-sin(deg_to_rad(_yaw)), 0.0, -cos(deg_to_rad(_yaw)))
	var right   := Vector3( cos(deg_to_rad(_yaw)), 0.0, -sin(deg_to_rad(_yaw)))
	# zoom 越遠 pan 越快，保持一致的「格子/秒」感
	var speed   := pan_speed * (_zoom / 20.0)
	if Input.is_action_pressed("cam_forward"): position += forward * speed * delta
	if Input.is_action_pressed("cam_back"):    position -= forward * speed * delta
	if Input.is_action_pressed("cam_left"):    position -= right   * speed * delta
	if Input.is_action_pressed("cam_right"):   position += right   * speed * delta

func _handle_keyboard_rotate(delta: float) -> void:
	if Input.is_action_pressed("cam_rotate_left"):
		_yaw -= rotate_speed * delta
	if Input.is_action_pressed("cam_rotate_right"):
		_yaw += rotate_speed * delta
	if Input.is_action_pressed("cam_tilt_up"):
		_elevation = clamp(_elevation + rotate_speed * delta, elevation_min, elevation_max)
	if Input.is_action_pressed("cam_tilt_down"):
		_elevation = clamp(_elevation - rotate_speed * delta, elevation_min, elevation_max)

func _handle_keyboard_zoom(delta: float) -> void:
	if Input.is_action_pressed("zoom_in"):
		_zoom = clamp(_zoom - zoom_speed * delta, zoom_min, zoom_max)
	if Input.is_action_pressed("zoom_out"):
		_zoom = clamp(_zoom + zoom_speed * delta, zoom_min, zoom_max)

func _mouse_pan(relative: Vector2) -> void:
	# 中鍵拖曳：用 yaw 補償方向，zoom 補償距離，讓拖曳速度感覺一致
	var forward := Vector3(-sin(deg_to_rad(_yaw)), 0.0, -cos(deg_to_rad(_yaw)))
	var right   := Vector3( cos(deg_to_rad(_yaw)), 0.0, -sin(deg_to_rad(_yaw)))
	var speed   := _zoom * mouse_pan_sensitivity
	position -= right   * relative.x * speed
	position += forward * relative.y * speed

func _handle_edge_scroll(delta: float) -> void:
	var vp_size := get_viewport().get_visible_rect().size
	var mouse   := get_viewport().get_mouse_position()
	var forward := Vector3(-sin(deg_to_rad(_yaw)), 0.0, -cos(deg_to_rad(_yaw)))
	var right   := Vector3( cos(deg_to_rad(_yaw)), 0.0, -sin(deg_to_rad(_yaw)))
	var speed   := pan_speed * (_zoom / 20.0)
	var m       := edge_scroll_margin
	if   mouse.x < m:                      position -= right   * speed * delta
	elif mouse.x > vp_size.x - m:          position += right   * speed * delta
	if   mouse.y < m:                      position += forward * speed * delta
	elif mouse.y > vp_size.y - m:          position -= forward * speed * delta

# ── 邊界與 Transform 應用 ─────────────────────────────────────────────────────

func _clamp_to_map() -> void:
	position.x = clamp(position.x, 0.0, map_width)
	position.z = clamp(position.z, 0.0, map_depth)
	position.y = 0.0  # Pivot 永遠在地面

func _apply_camera_transform() -> void:
	var arm: Node3D = $CameraArm
	arm.rotation.y = deg_to_rad(_yaw)

	var cam: Camera3D = $CameraArm/Camera3D
	# 相機位置：在 arm 局部空間中，沿 (0, sin(e), cos(e)) 方向偏移 zoom 距離
	# 使相機位於 pivot 斜上方，並在下一行 rotation.x 後自然對準 pivot
	var elev_rad := deg_to_rad(_elevation)
	cam.position  = Vector3(0.0, sin(elev_rad) * _zoom, cos(elev_rad) * _zoom)
	# 俯視角：讓相機的 -Z 軸（forward）指向 arm 原點（= pivot）
	cam.rotation.x = deg_to_rad(-_elevation)

# ── 對外統一介面（與 CameraRig2D 相同 signature）─────────────────────────────

## 平滑移動到世界位置（Y 分量忽略，pivot 永遠在地面）
func focus(world_pos: Vector3, instant: bool = false) -> void:
	var target := Vector3(world_pos.x, 0.0, world_pos.z)
	if instant:
		position = target
	else:
		create_tween() \
			.tween_property(self, "position", target, 0.5) \
			.set_trans(Tween.TRANS_CUBIC)

## 當前視野中心（XZ 地面座標）
func get_focus_point() -> Vector3:
	return Vector3(position.x, 0.0, position.z)

## 縮放等級 0.0（最遠）~ 1.0（最近），供 LOD 或 UI 判斷
func get_zoom_normalized() -> float:
	return 1.0 - clamp((_zoom - zoom_min) / (zoom_max - zoom_min), 0.0, 1.0)
