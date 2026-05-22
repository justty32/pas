# 單位選取高亮：兩 Pass Outline + Decal

## 目標

在 Low Poly 3D 策略遊戲中，為選取/懸停的單位加上描邊效果與地面圓圈，
不需要改動 mesh 結構，純粹透過 GDScript + Shader 實現。

---

## 核心設計

```
SelectionManager（GDScript Node）
  ├── hover(unit)         — 懸停：白色細描邊（0.015 m）
  ├── unhover()
  ├── select(unit, add, is_enemy)
  │     — 我方：金黃粗描邊（0.030 m）+ 地面 Decal
  │     — 敵方：紅色粗描邊（0.030 m）+ 地面 Decal
  ├── deselect(unit)
  └── clear_selection()

selection_outline.gdshader（Spatial Shader）
  render_mode: cull_front + unshaded + depth_draw_always
  vertex: VERTEX += NORMAL * outline_width   // 沿法線膨脹
  fragment: ALBEDO = outline_color.rgb
```

**整合方式**：`GeometryInstance3D.material_overlay`
- 不修改原始材質，不需要 mesh 有第二個 surface
- overlay 在原材質渲染後額外執行一次 outline pass

---

## 原始碼位置

- `mapcore_godot/demo/shaders/selection_outline.gdshader`
- `mapcore_godot/demo/scenes/selection_manager.gd`

---

## Shader 原理：為何用 `cull_front`

```
一般渲染：cull_back（預設）
→ 只畫正面，背面剔除

Outline Pass：cull_front
→ 只畫背面，正面剔除
→ 但頂點已沿法線膨脹一圈
→ 從正面看：中央被正常 Pass 遮住，只看得到外圍的背面 → 描邊！
```

```glsl
// selection_outline.gdshader 關鍵部分
void vertex() {
    VERTEX += NORMAL * outline_width;   // 膨脹（世界空間，單位：m）
}
void fragment() {
    ALBEDO = outline_color.rgb;         // 純色，不受燈光
}
```

`depth_draw_always`：確保描邊在有其他物件局部遮擋時仍完整顯示（適合策略遊戲）。
若希望被遮擋的部分隱藏，改用 `depth_draw_opaque_prepass`。

---

## 描邊狀態對照表

| 狀態 | outline_color | outline_width | Decal |
|------|--------------|---------------|-------|
| Hover（懸停） | 白色 (1,1,1) | 0.015 m | 無 |
| Select 我方 | 金黃 (1, 0.85, 0) | 0.030 m | 有 |
| Select 敵方 | 紅色 (1, 0.2, 0.1) | 0.030 m | 有 |
| 移動目標格 | — | — | 只有 Decal（另外處理）|

---

## GDScript 使用範例

### 最小整合

```gdscript
# 在 WorldMap3D 或 GameManager 內
@onready var selection: SelectionManager = $SelectionManager

# 點擊事件（Raycast 命中後）
func _on_unit_clicked(unit: Node3D, shift_held: bool) -> void:
    selection.select(unit, shift_held)

# 滑鼠移動事件（Raycast 命中後）
func _on_unit_hovered(unit: Node3D) -> void:
    selection.hover(unit)

func _on_mouse_left_unit() -> void:
    selection.unhover()
```

### 搭配 CameraRig3D 的完整 Raycast

```gdscript
# 在 WorldMap3D.gd
@onready var camera_rig: CameraRig3D = $CameraRig
@onready var selection: SelectionManager = $SelectionManager

var _hovered_unit: Node3D = null

func _input(event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        _update_hover(event.position)
    elif event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_LEFT:
            _handle_click(event.position, event.shift_pressed)

func _update_hover(screen_pos: Vector2) -> void:
    var unit := _raycast_unit(screen_pos)
    if unit != _hovered_unit:
        _hovered_unit = unit
        if unit:
            selection.hover(unit)
        else:
            selection.unhover()

func _handle_click(screen_pos: Vector2, add: bool) -> void:
    var unit := _raycast_unit(screen_pos)
    if unit:
        selection.select(unit, add)
    elif not add:
        selection.clear_selection()

func _raycast_unit(screen_pos: Vector2) -> Node3D:
    var cam := get_viewport().get_camera_3d()
    var from := cam.project_ray_origin(screen_pos)
    var to   := from + cam.project_ray_normal(screen_pos) * 500.0
    var space := get_world_3d().direct_space_state
    var query := PhysicsRayQueryParameters3D.create(from, to)
    query.collision_mask = 0b10  # 第 2 層 = 單位碰撞層
    var result := space.intersect_ray(query)
    if result.is_empty():
        return null
    return result["collider"].get_parent() as Node3D
```

---

## 場景結構

```
WorldMap3D (Node3D)
├── MapCoreGenerator
├── MapRenderer3D
│   ├── TerrainMesh
│   ├── WaterPlane
│   └── BiomeScatter
├── SelectionManager  ← 掛 selection_manager.gd
│   （Inspector 設 outline_shader / decal_texture）
├── CameraRig
└── Units (Node3D)    ← 存放所有單位節點
    ├── Unit_001 (Node3D)
    │   ├── Mesh (MeshInstance3D)   ← selection_manager 自動找到
    │   └── CollisionShape3D
    └── Unit_002 ...
```

### Inspector 設定

| 屬性 | 說明 | 建議值 |
|------|------|--------|
| `outline_shader` | 描邊 Shader 資源 | `res://shaders/selection_outline.gdshader` |
| `decal_texture` | 地面圓圈貼圖 | `res://textures/selection_circle.png`（留空 = 不顯示）|
| `decal_size` | Decal 投影範圍 | `Vector3(2, 1, 2)` |
| `decal_y_offset` | Decal 離地高度（防 z-fighting）| `0.05` |

---

## material_overlay vs set_surface_override_material

| 方法 | 需要第二個 surface | 影響原材質 | 適合情境 |
|------|------------------|-----------|---------|
| `material_overlay` | ✗ | ✗ | **本系統採用**：最乾淨 |
| `set_surface_override_material(1, mat)` | ✓ | ✗ | mesh 有 surface 1 時 |
| 修改 `material.next_pass` | ✗ | ✓（共享材質問題）| 非共享材質時可用 |

`material_overlay` 是 `GeometryInstance3D` 的屬性（`MeshInstance3D` 繼承），
在原材質渲染後執行額外一次 Pass，不需要改動 mesh 或原材質。

---

## 已知限制

- **世界空間描邊**：鏡頭縮放後描邊視覺粗細會改變。螢幕空間版本需在 vertex shader 中用 `VIEWPORT_SIZE` 換算，較複雜，暫未實作。
- **尖銳邊缺口**：Low Poly 的 flat shading 使用非共享頂點，法線方向不連續，沿法線膨脹後尖銳邊可能有缺口。解法是預先計算 smooth normal 存入 UV2，本系統未實作。
- **深層節點**：`_get_mesh()` 只找第一層子節點；若單位 mesh 在更深層，需自訂搜尋邏輯。
- **敵我判斷**：`is_enemy` 參數需由呼叫方決定，SelectionManager 本身不存儲陣營資料。
- **框選（Drag Select）**：尚未實作；需要 2D 矩形框 + PhysicsOverlapBoxQuery 查詢。

---

## 與 MaterialLibrary 整合

如果單位使用 `MaterialLibrary.make_rim()` 等特殊材質，
`material_overlay` 仍然有效——overlay 在原材質 + rim 之後再加一層描邊，
兩者可以同時存在。

---

*記錄時間：2026-05-22*
*狀態：SelectionManager（GDScript）+ selection_outline.gdshader 已實作*
