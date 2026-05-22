# 策略遊戲 Camera Rig（2D / 3D）

## 目標

實作策略遊戲鏡頭系統，對外暴露統一介面（`focus` / `get_focus_point` / `get_zoom_normalized`），
讓其他系統（minimap 點擊、單位選取、事件通知）不需要知道是 2D 或 3D 鏡頭。

---

## 原始碼位置

- `mapcore_godot/demo/scenes/camera_rig_3d.gd`
- `mapcore_godot/demo/scenes/camera_rig_2d.gd`

---

## 3D Camera Rig

### 節點結構

```
CameraRig3D (Node3D)  ← 腳本掛在此，Pivot 點在 XZ 地面平面移動
└── CameraArm (Node3D)  ← 僅負責 Y 軸旋轉（水平轉向 yaw）
    └── Camera3D          ← 位置與旋轉由腳本計算
```

### 相機位置數學（關鍵）

概念：相機在 arm 局部空間中位於 Pivot 的斜上方，並讓 -Z forward 軸對準 Pivot。

```gdscript
func _apply_camera_transform() -> void:
    $CameraArm.rotation.y = deg_to_rad(_yaw)

    var cam: Camera3D = $CameraArm/Camera3D
    var elev_rad := deg_to_rad(_elevation)

    # 相機位置在 arm 局部空間：沿 (0, sin(e), cos(e)) 方向偏移 _zoom
    # e=55°, zoom=20 → position=(0, 16.4, 11.5)
    cam.position  = Vector3(0.0, sin(elev_rad) * _zoom, cos(elev_rad) * _zoom)

    # 俯視角：讓 -Z forward 指向 arm 原點（= Pivot），驗算：
    # forward = Rx(-e) * (0,0,-1) = (0, -sin(e), -cos(e))
    # 從 cam.position 出發沿此方向，在 t=zoom 時恰好到達 (0,0,0) ✓
    cam.rotation.x = deg_to_rad(-_elevation)
```

**注意**：`cam.position.z = _zoom` 是錯誤的做法（相機會停在地面高度），
正確是用 `sin(e)*zoom` 和 `cos(e)*zoom` 分別設 Y 和 Z。

### Pan 方向補償

Pan 的前後左右必須跟隨 yaw，否則按 W 時鏡頭方向不對：

```gdscript
var forward := Vector3(-sin(deg_to_rad(_yaw)), 0.0, -cos(deg_to_rad(_yaw)))
var right   := Vector3( cos(deg_to_rad(_yaw)), 0.0, -sin(deg_to_rad(_yaw)))
```

Pan 速度也需跟隨 zoom（拉遠時每幀移動更多格子，保持操作感一致）：
```gdscript
var speed := pan_speed * (_zoom / 20.0)
```

### 滑鼠中鍵拖曳 Pan

```gdscript
func _mouse_pan(relative: Vector2) -> void:
    var speed := _zoom * mouse_pan_sensitivity
    position -= right   * relative.x * speed
    position += forward * relative.y * speed
```

`mouse_pan_sensitivity` 預設 `0.03`，依地圖大小調整。
Note: 右鍵拖曳改 `_yaw` 和 `_elevation`：
```gdscript
_yaw       += event.relative.x * mouse_rotate_sensitivity
_elevation  = clamp(_elevation - event.relative.y * mouse_rotate_sensitivity,
                    elevation_min, elevation_max)
```

### 邊界 Clamp

Pivot 永遠在地面（Y=0），XZ 用地圖尺寸限制：
```gdscript
func _clamp_to_map() -> void:
    position.x = clamp(position.x, 0.0, map_width)
    position.z = clamp(position.z, 0.0, map_depth)
    position.y = 0.0
```

---

## 2D Camera Rig

### 節點結構

```
CameraRig2D (Node2D)  ← 腳本掛在此
└── Camera2D
      position_smoothing_enabled = true
      position_smoothing_speed   = 8.0
```

2D 無需手動平滑位置（Camera2D 內建），只需平滑 zoom：
```gdscript
$Camera2D.zoom = $Camera2D.zoom.lerp(
    Vector2(_target_zoom, _target_zoom), delta * zoom_lerp
)
```

### 邊界 Clamp（含 zoom 補償）

2D 需考慮可視半視野大小，避免在地圖邊緣看到黑邊：
```gdscript
func _clamp_to_map() -> void:
    var half_view := get_viewport_rect().size * 0.5 / _target_zoom
    position.x = clamp(position.x, half_view.x, map_width  * tile_size - half_view.x)
    position.y = clamp(position.y, half_view.y, map_height * tile_size - half_view.y)
```

---

## 對外統一介面

| 方法 | 說明 | 2D 型別 | 3D 型別 |
|------|------|---------|---------|
| `focus(pos, instant)` | 移動鏡頭到目標位置 | `Vector2` | `Vector3`（Y忽略） |
| `get_focus_point()` | 當前視野中心 | `Vector2` | `Vector3` |
| `get_zoom_normalized()` | 縮放等級 0.0~1.0 | — | — |

使用範例（minimap 點擊移動鏡頭）：
```gdscript
# 不論 2D 或 3D，呼叫方式相同（只是傳入型別不同）
camera_rig.focus(world_pos)  # 平滑飛過去
```

`get_zoom_normalized()` 供 LOD 系統判斷是否顯示細節：
```gdscript
if camera_rig.get_zoom_normalized() > 0.5:
    detail_layer.visible = true
```

---

## InputMap 設定

在 ProjectSettings → Input Map 中新增以下動作：

| 動作名稱 | 建議按鍵 | 用途 |
|---------|---------|------|
| `cam_forward` | W / Up | 3D 前進 |
| `cam_back` | S / Down | 3D 後退 |
| `cam_left` | A / Left | 左移 |
| `cam_right` | D / Right | 右移 |
| `cam_up` | ↑ | 2D 上移 |
| `cam_down` | ↓ | 2D 下移 |
| `cam_rotate_left` | Q | 3D 左旋 |
| `cam_rotate_right` | E | 3D 右旋 |
| `cam_tilt_up` | R | 3D 仰角+（選用）|
| `cam_tilt_down` | F | 3D 仰角-（選用）|
| `zoom_in` | + / PageUp | 拉近 |
| `zoom_out` | - / PageDown | 拉遠 |

---

## 待決定

- [ ] 正交投影 vs 透視投影（正交更有棋盤感，在 Camera3D Inspector 設定）
- [ ] 邊緣滾動是否預設開啟（目前 `edge_scroll_enabled = false`）
- [ ] `SpringArm3D` 替代 `Node3D` arm（自動防止相機穿入地形）
- [ ] 鏡頭震動效果（`focus()` 後 tween pivot 加 ±0.2 抖動）

---

*記錄時間：2026-05-22*
*狀態：2D + 3D 均已實作；含滑鼠中鍵 Pan、右鍵 Rotate、滾輪 Zoom、邊緣滾動選項*
