# 2D 單位選取高亮：canvas_item Shader + SelectionManager2D

## 目標

在 2D 策略遊戲中，為選取/懸停的單位加上像素精確的描邊效果與程序繪製的選取圓圈，
不需要額外貼圖，純粹透過 GDScript + Shader 實現。

---

## 核心設計

```
SelectionManager2D（GDScript Node）
  ├── hover(unit)
  ├── unhover()
  ├── select(unit, add, is_enemy)
  ├── deselect(unit)
  └── clear_selection()

selection_outline_2d.gdshader（canvas_item）
  對每個透明像素採樣 8 個鄰近像素：
    鄰近有不透明像素 → 填入 outline_color
    否則             → 保持透明（pass-through）
  不透明像素直接 pass-through（保留原 sprite）

_SelectionCircle（Node2D 內部類別）
  draw_arc(Vector2.ZERO, radius, 0, TAU, 48, color, width)
  → z_index = -1，畫在單位圖層之下，不需貼圖
```

**整合方式**：`CanvasItem.material`（2D 版，對應 3D 的 `material_overlay`）
- 設定描邊時保存原始 material，移除時還原

---

## 原始碼位置

- `mapcore_godot/demo/shaders/selection_outline_2d.gdshader`
- `mapcore_godot/demo/scenes/selection_manager_2d.gd`

---

## Shader 原理：8 鄰採樣

```glsl
// TEXTURE_PIXEL_SIZE = vec2(1/width, 1/height)，即一個像素在 UV 空間的大小
vec2 px = TEXTURE_PIXEL_SIZE * outline_width;

float na = 0.0;
// 4 個正交方向
na = max(na, texture(TEXTURE, UV + vec2( px.x,  0.0 )).a);
na = max(na, texture(TEXTURE, UV + vec2(-px.x,  0.0 )).a);
na = max(na, texture(TEXTURE, UV + vec2( 0.0,   px.y)).a);
na = max(na, texture(TEXTURE, UV + vec2( 0.0,  -px.y)).a);
// 4 個對角方向
na = max(na, texture(TEXTURE, UV + vec2( px.x,  px.y)).a);
na = max(na, texture(TEXTURE, UV + vec2(-px.x,  px.y)).a);
na = max(na, texture(TEXTURE, UV + vec2( px.x, -px.y)).a);
na = max(na, texture(TEXTURE, UV + vec2(-px.x, -px.y)).a);

// 若鄰近有不透明像素（na > 0.5），該透明像素就是描邊區域
COLOR = (na > 0.5) ? outline_color : vec4(0.0);
```

為何用 8 個方向：4 個方向在對角邊緣會有缺口（露出空隙），8 個方向可確保描邊閉合。

---

## 描邊狀態對照表

| 狀態 | outline_color | outline_width | 圓圈 |
|------|--------------|---------------|------|
| Hover（懸停） | 白色 (1,1,1) | 1.5 px | 無 |
| Select 我方 | 金黃 (1, 0.85, 0) | 3.0 px | 有（金黃）|
| Select 敵方 | 紅色 (1, 0.2, 0.1) | 3.0 px | 有（紅色）|

---

## GDScript 使用範例

### 最小整合

```gdscript
# 在 GameScene.gd
@onready var sel: SelectionManager2D = $SelectionManager2D

func _on_unit_clicked(unit: Node2D, shift_held: bool) -> void:
    sel.select(unit, shift_held)

func _on_unit_hovered(unit: Node2D) -> void:
    sel.hover(unit)

func _on_mouse_left_unit() -> void:
    sel.unhover()
```

### 搭配 Area2D 的完整滑鼠輸入

```gdscript
# Unit.gd（掛在每個單位上）
extends CharacterBody2D

signal unit_hovered(unit)
signal unit_unhovered(unit)
signal unit_clicked(unit, shift)

func _ready() -> void:
    var area := $ClickArea  # Area2D with CollisionShape2D
    area.mouse_entered.connect(func(): unit_hovered.emit(self))
    area.mouse_exited.connect(func(): unit_unhovered.emit(self))
    area.input_event.connect(_on_area_input)

func _on_area_input(_viewport, event: InputEvent, _shape_idx: int) -> void:
    if event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_LEFT:
            unit_clicked.emit(self, event.shift_pressed)
```

```gdscript
# GameScene.gd
@onready var sel: SelectionManager2D = $SelectionManager2D

func _ready() -> void:
    for unit in $Units.get_children():
        unit.unit_hovered.connect(sel.hover)
        unit.unit_unhovered.connect(sel.unhover.bind())
        unit.unit_clicked.connect(_on_unit_clicked)

func _on_unit_clicked(unit: Node2D, shift: bool) -> void:
    sel.select(unit, shift)

# 點擊空地：清除選取
func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_LEFT:
            sel.clear_selection()
```

---

## 場景結構

```
GameScene (Node2D)
├── SelectionManager2D  ← 掛 selection_manager_2d.gd
│   （Inspector 設 outline_shader_2d）
├── Units (Node2D)
│   ├── Unit_001 (CharacterBody2D)
│   │   ├── Sprite2D           ← selection_manager_2d 自動找到
│   │   ├── ClickArea (Area2D)
│   │   └── CollisionShape2D
│   └── Unit_002 ...
└── TileMapLayer（地圖）
```

### Inspector 設定

| 屬性 | 說明 | 建議值 |
|------|------|--------|
| `outline_shader_2d` | 描邊 Shader 資源 | `res://shaders/selection_outline_2d.gdshader` |

---

## 選取圓圈實作

`_SelectionCircle` 是 `SelectionManager2D` 的內部類別（`class ... extends Node2D`），
無需額外場景或貼圖，直接用 `draw_arc()` 繪製：

```gdscript
class _SelectionCircle extends Node2D:
    var color:  Color = Color.YELLOW
    var radius: float = 24.0    # 建議 = sprite 寬度的一半
    var width:  float = 2.0     # 線條粗細（px）

    func _draw() -> void:
        draw_arc(Vector2.ZERO, radius, 0.0, TAU, 48, color, width, true)
        # 48 個線段 = 足夠圓滑；anti_aliased = true
```

圓圈 `z_index = -1`，畫在單位 sprite 之下。
`queue_free()` 時自動清除（deselect / clear_selection 呼叫）。

---

## CanvasItem.material 保存機制

```
select(unit)
    ↓
_apply_outline(unit, _mat_select)
    ↓
ci.has_meta("_sel2d_orig_mat") == false？
    → ci.set_meta("_sel2d_orig_mat", ci.material)   # 保存（可能是 null）
    → ci.material = _mat_select
                    ↓
deselect(unit)
    ↓
_remove_outline(unit)
    ↓
ci.material = ci.get_meta("_sel2d_orig_mat")         # 還原
ci.remove_meta("_sel2d_orig_mat")
```

這樣即使單位原本有自訂材質（如 ShaderMaterial），`deselect` 後仍會正確還原。

---

## 2D vs 3D 選取系統對照

| 面向 | 3D SelectionManager | 2D SelectionManager2D |
|------|--------------------|-----------------------|
| Shader 類型 | `shader_type spatial` | `shader_type canvas_item` |
| 描邊原理 | 沿法線膨脹 + cull_front | 8 鄰透明像素採樣 |
| 整合屬性 | `material_overlay` | `material`（保存/還原原始）|
| 地面標記 | Decal 節點（需貼圖） | `draw_arc()` Node2D（不需貼圖）|
| 節點型別 | `Node3D` / `MeshInstance3D` | `Node2D` / `CanvasItem` |

---

## 已知限制

- **描邊超出 Sprite 邊界**：`outline_width` 個像素的描邊需要 sprite texture 在邊緣有足夠的透明留白，否則描邊會被裁切。建議在匯入設定中加大 texture padding，或在 CONCEPT 中預留 `outline_width` 個像素的空白邊框。
- **sprite 有自訂 ShaderMaterial**：`material` 只能持有一個材質。若原始 sprite 有動態特效 shader，`_apply_outline` 會暫時蓋掉它（`deselect` 後還原）。需要同時顯示兩個 shader 時，改用 `next_pass` 鏈接。
- **非 CanvasItem 子節點**：`_get_canvas_item()` 只搜尋第一層子節點；深層節點需自訂搜尋邏輯。

---

*記錄時間：2026-05-22*
*狀態：SelectionManager2D（GDScript）+ selection_outline_2d.gdshader 已實作*
