## 2D 選取 / 懸停狀態管理器（策略遊戲版）
##
## 功能：
##   - Hover（懸停）：白色細描邊（outline_width = 1.5 px）
##   - Select 我方：金黃粗描邊（3.0 px）+ 地面選取圓圈
##   - Select 敵方：紅色粗描邊（3.0 px）+ 地面選取圓圈
##   - 多選：select(unit, add=true)
##
## 整合方式：CanvasItem.material
##   - 設定描邊時保存原始 material，移除時還原
##   - 選取圓圈以程序繪製的子節點實現，不需要貼圖
##
## 設置步驟：
##   1. 在場景掛此腳本（Node 或 Autoload）
##   2. Inspector 指定 outline_shader_2d（res://shaders/selection_outline_2d.gdshader）
##
## 使用範例：
##   sel.hover(unit_node)
##   sel.unhover()
##   sel.select(unit_node)
##   sel.select(unit_node, true)          # Shift 多選
##   sel.select(unit_node, false, true)   # 敵方選取
##   sel.deselect(unit_node)
##   sel.clear_selection()
class_name SelectionManager2D
extends Node

# ── 顏色與粗細常數 ───────────────────────────────────────────────────────────

const COLOR_HOVER        := Color(1.00, 1.00, 1.00, 1.0)  ## 懸停：白色
const COLOR_SELECT_ALLY  := Color(1.00, 0.85, 0.00, 1.0)  ## 我方：金黃
const COLOR_SELECT_ENEMY := Color(1.00, 0.20, 0.10, 1.0)  ## 敵方：紅
const WIDTH_HOVER  : float = 1.5   ## 懸停描邊寬（px）
const WIDTH_SELECT : float = 3.0   ## 選取描邊寬（px）

## 選取圓圈半徑（像素）；建議設為單位碰撞半徑或 sprite 半寬
const CIRCLE_RADIUS : float = 24.0
const CIRCLE_THICK  : float = 2.0   ## 圓圈線條寬

# ── Inspector 屬性 ────────────────────────────────────────────────────────────

## 描邊 Shader（指向 res://shaders/selection_outline_2d.gdshader）
@export var outline_shader_2d: Shader

# ── 狀態 ─────────────────────────────────────────────────────────────────────

var selected: Array[Node2D] = []
var hovered: Node2D = null

# ── 快取 ShaderMaterial ───────────────────────────────────────────────────────

var _mat_hover:  ShaderMaterial
var _mat_select: ShaderMaterial
var _mat_enemy:  ShaderMaterial

func _ready() -> void:
	if not outline_shader_2d:
		push_warning("SelectionManager2D: outline_shader_2d 未設定，描邊功能停用")
		return
	_mat_hover  = _make_outline(COLOR_HOVER,        WIDTH_HOVER)
	_mat_select = _make_outline(COLOR_SELECT_ALLY,  WIDTH_SELECT)
	_mat_enemy  = _make_outline(COLOR_SELECT_ENEMY, WIDTH_SELECT)

# ── 公開 API ──────────────────────────────────────────────────────────────────

## 設定懸停目標。
func hover(unit: Node2D) -> void:
	if hovered == unit:
		return
	if hovered and hovered not in selected:
		_remove_outline(hovered)
	hovered = unit
	if unit and unit not in selected:
		_apply_outline(unit, _mat_hover)

## 清除懸停狀態。
func unhover() -> void:
	if hovered and hovered not in selected:
		_remove_outline(hovered)
	hovered = null

## 選取單位。
## [param add]      = true 為追加選取（Shift）。
## [param is_enemy] = true 使用紅色描邊。
func select(unit: Node2D, add: bool = false, is_enemy: bool = false) -> void:
	if not add:
		_clear_all()
	if unit in selected:
		return
	selected.append(unit)
	_apply_outline(unit, _mat_enemy if is_enemy else _mat_select)
	_add_circle(unit, _mat_enemy.get_shader_parameter("outline_color") if is_enemy
		else _mat_select.get_shader_parameter("outline_color"))

## 取消選取單位。
func deselect(unit: Node2D) -> void:
	if unit not in selected:
		return
	selected.erase(unit)
	_remove_outline(unit)
	_remove_circle(unit)
	if unit == hovered:
		_apply_outline(unit, _mat_hover)

## 清除全部選取。
func clear_selection() -> void:
	_clear_all()
	if hovered and hovered not in selected:
		_apply_outline(hovered, _mat_hover)

# ── 內部輔助 ──────────────────────────────────────────────────────────────────

func _clear_all() -> void:
	for u in selected:
		_remove_outline(u)
		_remove_circle(u)
	selected.clear()

## 找 unit 本身或第一個 CanvasItem 子節點（Sprite2D / AnimatedSprite2D 等）。
func _get_canvas_item(unit: Node2D) -> CanvasItem:
	if unit is CanvasItem:
		return unit as CanvasItem
	for child in unit.get_children():
		if child is CanvasItem:
			return child as CanvasItem
	return null

const _ORIG_MAT_META := &"_sel2d_orig_mat"

func _apply_outline(unit: Node2D, mat: ShaderMaterial) -> void:
	if not mat:
		return
	var ci := _get_canvas_item(unit)
	if not ci:
		return
	# 第一次設定時保存原始 material，避免覆蓋遺失
	if not ci.has_meta(_ORIG_MAT_META):
		ci.set_meta(_ORIG_MAT_META, ci.material)
	ci.material = mat

func _remove_outline(unit: Node2D) -> void:
	var ci := _get_canvas_item(unit)
	if not ci:
		return
	# 還原原始 material（可能是 null）
	if ci.has_meta(_ORIG_MAT_META):
		ci.material = ci.get_meta(_ORIG_MAT_META)
		ci.remove_meta(_ORIG_MAT_META)
	else:
		ci.material = null

func _make_outline(color: Color, width: float) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = outline_shader_2d
	mat.set_shader_parameter("outline_color", color)
	mat.set_shader_parameter("outline_width", width)
	return mat

# ── 選取圓圈（程序繪製，不需貼圖） ─────────────────────────────────────────

const _CIRCLE_META := &"_sel2d_circle"

func _add_circle(unit: Node2D, color: Color) -> void:
	if unit.has_meta(_CIRCLE_META):
		return
	var c := _SelectionCircle.new()
	c.color  = color
	c.z_index = -1   # 圓圈在單位圖層之下
	unit.add_child(c)
	unit.set_meta(_CIRCLE_META, c)

func _remove_circle(unit: Node2D) -> void:
	if not unit.has_meta(_CIRCLE_META):
		return
	(unit.get_meta(_CIRCLE_META) as Node).queue_free()
	unit.remove_meta(_CIRCLE_META)

# ── 選取圓圈節點（內部輔助類別）─────────────────────────────────────────────

## 在父節點原點周圍繪製一個弧形選取圓圈。
## 使用 draw_arc() 純程序繪製，不需要任何貼圖。
class _SelectionCircle extends Node2D:
	var color:  Color = Color.YELLOW
	var radius: float = CIRCLE_RADIUS
	var width:  float = CIRCLE_THICK

	func _draw() -> void:
		draw_arc(Vector2.ZERO, radius, 0.0, TAU, 48, color, width, true)
