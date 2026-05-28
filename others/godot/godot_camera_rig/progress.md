# godot_camera_rig — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的 2D + 3D 策略相機。

## 一句話：這是什麼

策略遊戲相機：pan / zoom / rotate / boundary clamp / focus / shake，2D 與 3D 兩套，
對外行為介面一致（`focus()` / `get_focus_point()` / `get_zoom_normalized()`）。

## 真相校準

mapcore_godot demo 端已有 `camera_rig_2d.gd` 與 `camera_rig_3d.gd`，並真機驗證過
（含中鍵 pan、右鍵 rotate、鍵盤 pan/zoom、邊緣滾動可選）。本目錄做的是
**抽出可拆出複用、不耦合 mapcore demo 場景結構的版本**：

| 差異點 | demo 版 | 本檔版 |
|--------|---------|--------|
| 子節點路徑 | `$Camera2D` / `$CameraArm/Camera3D` 硬編 | `@export camera_node` / `camera_arm` 注入，未設則 _ready 自建 |
| InputMap 動作名 | 硬編 `"cam_left"` 等 | 全部 `@export StringName`，外部可改 |
| 缺 action 處理 | 直接 Input.is_action_pressed 會報 warning | `InputMap.has_action()` 守門，未定義靜默跳過 |
| 正交 / 透視（3D） | 透視寫死 | `@export use_orthographic` 開關，setter 即時切換 |
| 鎖定仰角（Civ 6 風） | 無 | `@export lock_elevation` 開關 |
| Shake 鏡頭晃動 | 無 | `shake(amplitude, duration)` API（兩版皆有） |

## 檔案清單

```
godot_camera_rig/
├── gd/
│   ├── camera_rig_2d.gd        # 2D 策略相機 Node2D
│   └── camera_rig_3d.gd        # 3D 策略相機 Node3D
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| 2D pan / zoom / clamp / smoothing | 鍵盤 + 中鍵拖曳 + 滾輪 + 邊緣滾動 | ✅ 完成 |
| 2D focus / shake | Tween position + offset shake | ✅ 完成 |
| 3D pan / rotate / zoom / clamp | 鍵盤 + 中鍵 pan + 右鍵旋轉 + 滾輪 | ✅ 完成 |
| 3D 正交/透視切換 | `use_orthographic` 開關 + `orthographic_size_per_unit_zoom` | ✅ 完成 |
| 3D 鎖定仰角 | `lock_elevation` 開關 | ✅ 完成 |
| 3D focus / shake | Tween + 3D offset shake | ✅ 完成 |
| 真機驗證 | Godot 4 編輯器跑兩版場景 | ⏸ **待真機驗證** |

## 設計重點

### 1. 子節點注入優先、自建後備
`@export var camera_node` 允許外部在編輯器擺好節點再綁；若留空，`_ready()` 自建。
兩條路徑都通。整合進真實專案時通常會走編輯器擺節點路線（方便調 inspector）。

### 2. InputMap action 名稱全部 @export
不寫死 `"cam_left"`。專案如果已有自己的命名（例如 `"camera/pan_left"`），
inspector 改一改就接通。`_action_pressed()` 守門：未定義的 action 直接靜默跳過，
不報 warning。

### 3. 正交 / 透視即時切換（3D）
CONCEPT 待決事項。`use_orthographic` 是有 setter 的屬性，編輯器改了或執行期改了
都會立刻套用到 `Camera3D.projection`。正交模式下 `Camera3D.size = _zoom × factor`
讓滾輪縮放也能控正交視野，沒有特殊操作分歧。

### 4. Shake 用 Tween + camera offset
不動 rig 的 `position`，避免干擾 `focus()` 進行中的 tween 或鍵盤 pan。
2D 在 `camera_node.offset`、3D 在 `camera_node.position` 上加偏移（後者已用於 zoom 距離，
所以晃動偏移與 zoom 偏移加法疊加）。完成後歸零。

### 5. 對外介面三件套
不論 2D / 3D，外部都這樣呼叫：

```gdscript
camera.focus(world_pos)               # 平滑移動到目標
var p = camera.get_focus_point()      # 當前視野中心
var z = camera.get_zoom_normalized()  # 0(最遠)~1(最近)，給 LOD 用
camera.shake(amplitude, duration)     # 鏡頭晃動
```

2D `world_pos` 是 `Vector2`、3D 是 `Vector3`，型別不同但 signature 對應。

## 用法範例

### 2D

```gdscript
var cam := CameraRig2D.new()
cam.map_width = 100
cam.map_height = 100
cam.tile_size = 32.0
add_child(cam)

# 戰鬥震動
cam.shake(12.0, 0.4)
# 聚焦到目標單位
cam.focus(unit.global_position)
```

### 3D

```gdscript
var cam := CameraRig3D.new()
cam.map_width = 64
cam.map_depth = 48
cam.use_orthographic = true        # 棋盤地圖感
cam.lock_elevation = true          # Civ 6 風格鎖視角
add_child(cam)
cam.focus(Vector3(map.center.x, 0, map.center.y))
```

## 待決事項（從 CONCEPT.md 帶過來）

- [x] **邊緣滾動**：兩版都有 `edge_scroll_enabled` 開關。預設關（避免測試時手抖觸發）。
- [x] **正交 vs 透視（3D）**：`use_orthographic` 即時切換。
- [x] **鎖定仰角 vs 自由仰角**：`lock_elevation` 開關。
- [x] **鏡頭晃動**：`shake()` API。
- [ ] **觸控板手勢**（trackpad pinch）：未涵蓋。Godot 4 有 `InputEventPanGesture` /
      `InputEventMagnifyGesture`，等需要時補。

## 必要的 InputMap 設定

整合進專案時，需要在 ProjectSettings → Input Map 定義對應動作（或改 `@export` 用既有名稱）：

**共用**：`cam_left` / `cam_right` / `zoom_in` / `zoom_out`

**2D 額外**：`cam_up` / `cam_down`

**3D 額外**：`cam_forward` / `cam_back` / `cam_rotate_left` / `cam_rotate_right` /
`cam_tilt_up` / `cam_tilt_down`

## 下一步（按需）

1. **真機驗證**：把 .gd 拖入 Godot 4 專案，掛 `CameraRig2D` 或 `CameraRig3D` 節點，
   設好 InputMap，跑一輪確認 pan/zoom/rotate/shake/正交切換都符合預期。
2. **與 world_map 整合**：地圖鋪好後把這個 rig 加進場景樹，`focus()` 接到「點選單位」等
   事件即可立即實用。
3. **觸控板手勢**：等使用者真的在 Mac/筆電上需要時補。
