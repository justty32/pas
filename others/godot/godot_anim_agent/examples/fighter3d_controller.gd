extends Node3D

@onready var anim_player: AnimationPlayer = $AnimationPlayer
@onready var anim_tree: AnimationTree    = $AnimationTree
@onready var camera: Camera3D = $Camera3D

var _tree_active := true

# Camera orbit
var _target  := Vector3(0.15, 0.85, 0.0)   # 角色中心（Fighter 本地空間）
var _radius  := 2.2
var _yaw     := 0.0     # 水平角（繞 Y 軸）
var _pitch   := 0.0     # 垂直角
var _dragging := false
var _last_mouse := Vector2.ZERO

const ORBIT_SPEED := 0.005
const ZOOM_SPEED  := 0.2
const PITCH_MIN   := -1.3   # ~-74°，避免 gimbal
const PITCH_MAX   :=  1.3

func _ready() -> void:
	anim_tree.active = true
	_update_camera()
	print("=== Fighter3D 動畫預覽 ===")
	print("左鍵拖曳   → orbit 旋轉鏡頭")
	print("滾輪       → 縮放")
	print("Space（按住）→ do_punch（state machine）")
	print("1/2/3/4    → AnimationPlayer 直播 idle/punch/guard/step_in")
	print("T          → 關 AnimationTree，切到 AnimationPlayer 模式")

func _process(_delta: float) -> void:
	if _tree_active:
		anim_tree["parameters/conditions/do_punch"] = Input.is_action_pressed("ui_accept")
	_update_camera()

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_LEFT:
				_dragging = event.pressed
				if _dragging:
					_last_mouse = event.position
			MOUSE_BUTTON_WHEEL_UP:
				_radius = maxf(0.4, _radius - ZOOM_SPEED)
			MOUSE_BUTTON_WHEEL_DOWN:
				_radius = minf(10.0, _radius + ZOOM_SPEED)

	elif event is InputEventMouseMotion and _dragging:
		var d := event.position - _last_mouse
		_last_mouse = event.position
		_yaw   -= d.x * ORBIT_SPEED
		_pitch -= d.y * ORBIT_SPEED
		_pitch  = clampf(_pitch, PITCH_MIN, PITCH_MAX)

	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	match event.keycode:
		KEY_1: _play_direct("idle")
		KEY_2: _play_direct("punch")
		KEY_3: _play_direct("guard")
		KEY_4: _play_direct("step_in")
		KEY_T:
			_tree_active = false
			anim_tree.active = false
			print("AnimationTree 已關，切到 AnimationPlayer 模式")

func _update_camera() -> void:
	var dir := Vector3(sin(_yaw) * cos(_pitch), sin(_pitch), cos(_yaw) * cos(_pitch))
	camera.position = _target + dir * _radius
	camera.look_at(to_global(_target), Vector3.UP)

func spawn_hit_spark() -> void:
	print("💥 hit spark (3D)")

func _play_direct(anim: String) -> void:
	_tree_active = false
	anim_tree.active = false
	anim_player.play(anim)
	print("▶ AnimationPlayer: ", anim)
