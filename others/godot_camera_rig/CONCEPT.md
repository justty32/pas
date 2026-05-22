# 策略遊戲 Camera Rig

## 核心需求

策略遊戲鏡頭與動作遊戲不同，需要：
- **Pan**：自由移動視角到地圖任意位置
- **Zoom**：拉近看細節、拉遠看全局
- **Rotate**（3D）：調整觀察角度
- **Boundary Clamping**：不能滑出地圖邊界
- **Smooth Interpolation**：移動有慣性感，不硬切
- **Focus Function**：選中單位 / 事件發生時自動移動到目標

2D 與 3D 的實作差異較大，分開設計，但行為介面對外一致。

---

## 2D Camera Rig

### 節點結構

```
CameraRoot (Node2D)        ← 實際移動的錨點
└── Camera2D
        zoom = Vector2(1, 1)   ← 縮放
        position_smoothing_enabled = true
        position_smoothing_speed = 8.0
```

### 實作要點

```gdscript
class_name CameraRig2D extends Node2D

@export var map_width:  int = 100
@export var map_height: int = 100
@export var tile_size:  float = 64.0

@export var zoom_min: float = 0.3
@export var zoom_max: float = 3.0
@export var zoom_speed: float = 0.1
@export var pan_speed: float = 400.0

var _target_pos:  Vector2
var _target_zoom: float = 1.0

func _process(delta: float) -> void:
    _handle_pan(delta)
    _handle_zoom()
    _clamp_to_map()
    # 平滑插值到目標（Camera2D 的 smoothing 處理位置，zoom 需手動）
    $Camera2D.zoom = $Camera2D.zoom.lerp(Vector2(_target_zoom, _target_zoom), delta * 8.0)

func _handle_pan(delta: float) -> void:
    var dir = Vector2.ZERO
    if Input.is_action_pressed("cam_left"):  dir.x -= 1
    if Input.is_action_pressed("cam_right"): dir.x += 1
    if Input.is_action_pressed("cam_up"):    dir.y -= 1
    if Input.is_action_pressed("cam_down"):  dir.y += 1
    # 縮放越大時 pan 速度需補償（視野越小，同樣速度感覺越快）
    position += dir * pan_speed * delta / _target_zoom

func _handle_zoom() -> void:
    var scroll = Input.get_axis("zoom_out", "zoom_in")
    _target_zoom = clamp(_target_zoom * (1.0 + scroll * zoom_speed), zoom_min, zoom_max)

func _clamp_to_map() -> void:
    var half_view = get_viewport_rect().size * 0.5 / _target_zoom
    position.x = clamp(position.x, half_view.x, map_width * tile_size - half_view.x)
    position.y = clamp(position.y, half_view.y, map_height * tile_size - half_view.y)

func focus(world_pos: Vector2, instant: bool = false) -> void:
    position = world_pos if instant else position  # 平滑移動靠 smoothing 處理
    if not instant:
        create_tween().tween_property(self, "position", world_pos, 0.4).set_trans(Tween.TRANS_CUBIC)
```

---

## 3D Camera Rig

### 節點結構

```
CameraRig (Node3D)          ← Pivot，在 XZ 平面移動
└── CameraArm (Node3D)      ← 繞 Y 軸旋轉（水平轉向）
    └── Camera3D            ← 沿 -Z 方向偏移（距離 = zoom）
                              rotation.x = -elevation_angle（俯視角）
```

Pivot 只在 XZ 平面移動，不改變 Y。Camera 的高度感來自 `elevation_angle`（約 45°–70°）。

### 實作要點

```gdscript
class_name CameraRig3D extends Node3D

@export var map_width:  int = 100
@export var map_depth:  int = 100

@export var zoom_min:       float = 5.0    # 距離 pivot 最近
@export var zoom_max:       float = 40.0   # 距離 pivot 最遠
@export var elevation_min:  float = 30.0   # 度，最平（危險）
@export var elevation_max:  float = 80.0   # 度，最陡（幾乎正上方看）
@export var pan_speed:      float = 20.0
@export var rotate_speed:   float = 90.0   # deg/s
@export var zoom_speed:     float = 5.0

var _zoom:      float = 20.0
var _elevation: float = 55.0   # 度
var _yaw:       float = 0.0    # 度，水平旋轉

func _ready() -> void:
    _apply_camera_transform()

func _process(delta: float) -> void:
    _handle_pan(delta)
    _handle_rotate(delta)
    _handle_zoom(delta)
    _clamp_to_map()
    _apply_camera_transform()

func _handle_pan(delta: float) -> void:
    # Pan 方向跟隨水平旋轉（相機朝向的前/右）
    var forward = Vector3(-sin(deg_to_rad(_yaw)), 0, -cos(deg_to_rad(_yaw)))
    var right   = Vector3( cos(deg_to_rad(_yaw)), 0, -sin(deg_to_rad(_yaw)))
    var speed   = pan_speed * (_zoom / 20.0)   # zoom 越遠 pan 越快
    if Input.is_action_pressed("cam_forward"): position += forward * speed * delta
    if Input.is_action_pressed("cam_back"):    position -= forward * speed * delta
    if Input.is_action_pressed("cam_left"):    position -= right   * speed * delta
    if Input.is_action_pressed("cam_right"):   position += right   * speed * delta

func _handle_rotate(delta: float) -> void:
    if Input.is_action_pressed("cam_rotate_left"):  _yaw       -= rotate_speed * delta
    if Input.is_action_pressed("cam_rotate_right"): _yaw       += rotate_speed * delta
    if Input.is_action_pressed("cam_tilt_up"):      _elevation  = clamp(_elevation + rotate_speed * delta, elevation_min, elevation_max)
    if Input.is_action_pressed("cam_tilt_down"):    _elevation  = clamp(_elevation - rotate_speed * delta, elevation_min, elevation_max)

func _handle_zoom(delta: float) -> void:
    var scroll = Input.get_axis("zoom_out", "zoom_in")
    _zoom = clamp(_zoom - scroll * zoom_speed, zoom_min, zoom_max)

func _clamp_to_map() -> void:
    position.x = clamp(position.x, 0, map_width)
    position.z = clamp(position.z, 0, map_depth)
    position.y = 0  # pivot 永遠在地面高度

func _apply_camera_transform() -> void:
    var arm: Node3D = $CameraArm
    arm.rotation.y = deg_to_rad(_yaw)

    var cam: Camera3D = $CameraArm/Camera3D
    cam.rotation.x  = deg_to_rad(-_elevation)
    # 沿 arm 的 -Z 方向偏移（即攝影機後退，等效 zoom）
    cam.position.z  = _zoom

func focus(world_pos: Vector3, instant: bool = false) -> void:
    var target = Vector3(world_pos.x, 0, world_pos.z)
    if instant:
        position = target
    else:
        create_tween().tween_property(self, "position", target, 0.5).set_trans(Tween.TRANS_CUBIC)
```

---

## 滑鼠操作（補充）

除鍵盤外，策略遊戲通常需要：

| 操作 | 2D | 3D |
|------|----|----|
| 中鍵拖曳 | Pan | Pan |
| 右鍵拖曳 | — | 水平旋轉（_yaw） |
| 滾輪 | Zoom | Zoom |
| 畫面邊緣觸發 | Pan（可選） | Pan（可選） |

```gdscript
func _input(event: InputEvent) -> void:
    if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
        # 2D：直接偏移 position
        # 3D：偏移 pivot（需轉換到世界空間）
        pass
    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP:   _target_zoom ...
        if event.button_index == MOUSE_BUTTON_WHEEL_DOWN: _target_zoom ...
```

---

## 共用行為介面

無論 2D 或 3D，對外暴露相同的函式，其他系統不需要知道是哪種相機：

```gdscript
# 聚焦到某個世界位置（選中單位、事件通知等）
func focus(pos, instant: bool = false) -> void: ...

# 當前視野中心（用於 AI、UI 判斷）
func get_focus_point() -> Variant: ...  # Vector2 or Vector3

# 縮放等級（0.0 = 最遠，1.0 = 最近，用於 LOD 判斷）
func get_zoom_normalized() -> float: ...
```

---

## 待決定

- [ ] 是否支援邊緣滾動（滑鼠移到螢幕邊緣觸發 pan）
- [ ] 3D 是否允許自由仰角或鎖定預設角度（Civ 6 鎖定、Civ 5 允許調）
- [ ] 正交投影（Orthographic）vs 透視投影（Perspective）——正交更有棋盤地圖感
- [ ] 鏡頭晃動效果（戰鬥時輕微震動）—— Tween 在 pivot 上加偏移即可

---

*記錄時間：2026-05-22*
*狀態：概念階段；2D 與 3D 各自獨立實作，對外介面相同*
