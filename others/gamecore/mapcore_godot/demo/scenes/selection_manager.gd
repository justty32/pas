## 選取 / 懸停狀態管理器（策略遊戲版）
##
## 功能：
##   - Hover（滑鼠懸停）：白色細描邊
##   - Select（點擊選取，我方）：黃色粗描邊 + 地面 Decal
##   - Select（點擊選取，敵方）：紅色粗描邊 + 地面 Decal
##   - 多選：Shift 點擊 add=true
##
## 整合描邊方式：GeometryInstance3D.material_overlay
##   不需要 mesh 有第二個 surface；overlay 在原本材質上額外渲染一次。
##
## 設置步驟：
##   1. 在場景掛此腳本（Node 或 Autoload 均可）
##   2. Inspector 指定 outline_shader（res://shaders/selection_outline.gdshader）
##   3. 可選：指定 decal_texture（選取圓圈 PNG，留空則不顯示 Decal）
##
## 使用範例：
##   selection_manager.hover(unit_node)
##   selection_manager.unhover()
##   selection_manager.select(unit_node)                     # 我方單選
##   selection_manager.select(unit_node, true)               # 我方多選（Shift）
##   selection_manager.select(unit_node, false, true)        # 敵方選取
##   selection_manager.deselect(unit_node)
##   selection_manager.clear_selection()
class_name SelectionManager
extends Node

# ── 顏色與粗細常數 ───────────────────────────────────────────────────────────

const COLOR_HOVER       := Color(1.00, 1.00, 1.00, 1.0)  ## 懸停：白色
const COLOR_SELECT_ALLY := Color(1.00, 0.85, 0.00, 1.0)  ## 選取（我方）：金黃
const COLOR_SELECT_ENEMY:= Color(1.00, 0.20, 0.10, 1.0)  ## 選取（敵方）：紅
const WIDTH_HOVER       := 0.015                          ## 懸停描邊寬（m）
const WIDTH_SELECT      := 0.030                          ## 選取描邊寬（m）

# ── Inspector 屬性 ────────────────────────────────────────────────────────────

## 描邊 Shader（指向 res://shaders/selection_outline.gdshader）
@export var outline_shader: Shader
## 地面選取圓圈貼圖（留空則不顯示 Decal）
@export var decal_texture:  Texture2D
## Decal 大小（XZ 平面，Y 為投影深度）
@export var decal_size: Vector3 = Vector3(2.0, 1.0, 2.0)
## Decal Y 偏移（避免 z-fighting）
@export var decal_y_offset: float = 0.05

# ── 狀態 ─────────────────────────────────────────────────────────────────────

## 目前所有選取中的單位
var selected: Array[Node3D] = []
## 目前懸停中的單位（null = 無懸停）
var hovered: Node3D = null

# ── 快取 ShaderMaterial ───────────────────────────────────────────────────────

var _mat_hover:  ShaderMaterial
var _mat_select: ShaderMaterial
var _mat_enemy:  ShaderMaterial

func _ready() -> void:
	if not outline_shader:
		push_warning("SelectionManager: outline_shader 未設定，描邊功能停用")
		return
	_mat_hover  = _make_outline(COLOR_HOVER,        WIDTH_HOVER)
	_mat_select = _make_outline(COLOR_SELECT_ALLY,  WIDTH_SELECT)
	_mat_enemy  = _make_outline(COLOR_SELECT_ENEMY, WIDTH_SELECT)

# ── 公開 API ──────────────────────────────────────────────────────────────────

## 設定懸停目標。若已懸停同一個單位則不重複操作。
func hover(unit: Node3D) -> void:
	if hovered == unit:
		return
	# 移除上一個懸停（若不在選取中）
	if hovered and hovered not in selected:
		_remove_outline(hovered)
	hovered = unit
	# 只在不在選取中才套用懸停描邊（選取描邊優先）
	if unit and unit not in selected:
		_apply_outline(unit, _mat_hover)

## 清除懸停狀態。
func unhover() -> void:
	if hovered and hovered not in selected:
		_remove_outline(hovered)
	hovered = null

## 選取單位。
## [param add]      = true 時追加選取（Shift 點擊），false 時先清除全選。
## [param is_enemy] = true 時使用紅色描邊。
func select(unit: Node3D, add: bool = false, is_enemy: bool = false) -> void:
	if not add:
		_clear_all()
	if unit in selected:
		return
	selected.append(unit)
	_apply_outline(unit, _mat_enemy if is_enemy else _mat_select)
	if decal_texture:
		_add_decal(unit)

## 取消選取單位。若該單位仍在懸停中，改回懸停描邊。
func deselect(unit: Node3D) -> void:
	if unit not in selected:
		return
	selected.erase(unit)
	_remove_outline(unit)
	_remove_decal(unit)
	if unit == hovered:
		_apply_outline(unit, _mat_hover)

## 清除所有選取（不影響懸停狀態）。
func clear_selection() -> void:
	_clear_all()
	# 若當前懸停單位被清除選取，補回懸停描邊
	if hovered and hovered not in selected:
		_apply_outline(hovered, _mat_hover)

# ── 內部輔助 ──────────────────────────────────────────────────────────────────

func _clear_all() -> void:
	for u in selected:
		_remove_outline(u)
		_remove_decal(u)
	selected.clear()

## 在 unit 本身或其第一個 MeshInstance3D 子節點上套用 material_overlay。
func _apply_outline(unit: Node3D, mat: ShaderMaterial) -> void:
	if not mat:
		return
	var mesh := _get_mesh(unit)
	if mesh:
		mesh.material_overlay = mat

func _remove_outline(unit: Node3D) -> void:
	var mesh := _get_mesh(unit)
	if mesh:
		mesh.material_overlay = null

## 找 unit 下第一個 MeshInstance3D（包含 unit 本身）。
func _get_mesh(unit: Node3D) -> MeshInstance3D:
	if unit is MeshInstance3D:
		return unit as MeshInstance3D
	for child in unit.get_children():
		if child is MeshInstance3D:
			return child as MeshInstance3D
	return null

# ── Decal（地面選取圓圈） ────────────────────────────────────────────────────

const _DECAL_META := &"_sel_decal"

func _add_decal(unit: Node3D) -> void:
	if unit.has_meta(_DECAL_META):
		return
	var d := Decal.new()
	d.texture_albedo = decal_texture
	d.size           = decal_size
	d.position       = Vector3(0.0, decal_y_offset, 0.0)
	unit.add_child(d)
	unit.set_meta(_DECAL_META, d)

func _remove_decal(unit: Node3D) -> void:
	if not unit.has_meta(_DECAL_META):
		return
	(unit.get_meta(_DECAL_META) as Node).queue_free()
	unit.remove_meta(_DECAL_META)

func _make_outline(color: Color, width: float) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = outline_shader
	mat.set_shader_parameter("outline_color", color)
	mat.set_shader_parameter("outline_width", width)
	return mat
