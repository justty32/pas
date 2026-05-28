class_name SelectionHighlight extends RefCounted

# 通用 3D + 2D outline 套用 helper，不耦合 mapcore demo 結構。
# 與 mapcore demo 端 selection_manager.gd 的差異：
#   - 3D 支援世界空間 / 螢幕空間兩支 shader 切換
#   - 2D 一條路徑直通（sprite material 取代或加 overlay）
#   - 不維護全域選取狀態（單純 apply/remove API），狀態交給呼叫端管理
#   - 「unit」介面更寬：任何 Node3D（找子 MeshInstance3D）或 CanvasItem 都可
#
# 整合進專案時：把這支與 shaders/ 放在 res://addons/godot_selection_highlight/。

# 整合進專案後改路徑常數。
const SHADER_3D_WORLD := "res://addons/godot_selection_highlight/shaders/outline_world.gdshader"
const SHADER_3D_SCREEN := "res://addons/godot_selection_highlight/shaders/outline_screen.gdshader"
const SHADER_2D := "res://addons/godot_selection_highlight/shaders/outline_2d.gdshader"

enum Style3D { WORLD_SPACE, SCREEN_SPACE }
enum Pattern2D { CARDINAL, DIAGONAL, FULL }

# Sprite2D / Node2D 用 meta 存原 material，移除時還原。
const _META_PREV_MATERIAL := &"_sh_prev_material"

static var _cached_world: Shader
static var _cached_screen: Shader
static var _cached_2d: Shader


# ── 3D outline ────────────────────────────────────────────────────────────

static func apply_3d(node: Node3D, color: Color = Color(1.0, 0.85, 0.0),
		width: float = 0.025, style: Style3D = Style3D.WORLD_SPACE) -> ShaderMaterial:
	var mesh := _find_mesh(node)
	if mesh == null:
		return null
	var mat := ShaderMaterial.new()
	mat.shader = _load_3d_shader(style)
	if style == Style3D.WORLD_SPACE:
		mat.set_shader_parameter(&"outline_color", color)
		mat.set_shader_parameter(&"outline_width", width)
	else:
		mat.set_shader_parameter(&"outline_color", color)
		# screen 模式 width 解讀成像素
		mat.set_shader_parameter(&"outline_pixel_width", width if width > 1.0 else width * 100.0)
	mesh.material_overlay = mat
	return mat


static func remove_3d(node: Node3D) -> void:
	var mesh := _find_mesh(node)
	if mesh:
		mesh.material_overlay = null


# 把同一個 outline 套到 node 底下所有 MeshInstance3D（角色由多個 mesh 組成時用）。
static func apply_3d_recursive(root: Node3D, color: Color = Color(1.0, 0.85, 0.0),
		width: float = 0.025, style: Style3D = Style3D.WORLD_SPACE) -> Array[ShaderMaterial]:
	var mats: Array[ShaderMaterial] = []
	for m in _all_meshes(root):
		var mat := ShaderMaterial.new()
		mat.shader = _load_3d_shader(style)
		mat.set_shader_parameter(&"outline_color", color)
		if style == Style3D.WORLD_SPACE:
			mat.set_shader_parameter(&"outline_width", width)
		else:
			mat.set_shader_parameter(&"outline_pixel_width", width if width > 1.0 else width * 100.0)
		m.material_overlay = mat
		mats.append(mat)
	return mats


static func remove_3d_recursive(root: Node3D) -> void:
	for m in _all_meshes(root):
		m.material_overlay = null


# ── 2D outline ────────────────────────────────────────────────────────────

# CanvasItem.material 取代法：把 shader material 直接放上 sprite。
# 適用於沒有額外材質需求的 sprite。
static func apply_2d(sprite: CanvasItem, color: Color = Color(1.0, 0.85, 0.0),
		width: float = 2.0, pattern: Pattern2D = Pattern2D.FULL,
		pulse: float = 0.0) -> ShaderMaterial:
	if not sprite.has_meta(_META_PREV_MATERIAL):
		sprite.set_meta(_META_PREV_MATERIAL, sprite.material)
	var mat := ShaderMaterial.new()
	mat.shader = _load_2d_shader()
	mat.set_shader_parameter(&"outline_color", color)
	mat.set_shader_parameter(&"outline_width", width)
	mat.set_shader_parameter(&"sample_pattern", int(pattern))
	mat.set_shader_parameter(&"pulse_strength", pulse)
	sprite.material = mat
	return mat


static func remove_2d(sprite: CanvasItem) -> void:
	if sprite.has_meta(_META_PREV_MATERIAL):
		sprite.material = sprite.get_meta(_META_PREV_MATERIAL)
		sprite.remove_meta(_META_PREV_MATERIAL)
	else:
		sprite.material = null


# ── 內部 ──────────────────────────────────────────────────────────────────

static func _find_mesh(node: Node3D) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node
	for child in node.get_children():
		if child is MeshInstance3D:
			return child
	return null


static func _all_meshes(root: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	if root is MeshInstance3D:
		out.append(root)
	for child in root.get_children():
		out.append_array(_all_meshes(child))
	return out


static func _load_3d_shader(style: Style3D) -> Shader:
	if style == Style3D.WORLD_SPACE:
		if _cached_world == null:
			_cached_world = load(SHADER_3D_WORLD)
		return _cached_world
	if _cached_screen == null:
		_cached_screen = load(SHADER_3D_SCREEN)
	return _cached_screen


static func _load_2d_shader() -> Shader:
	if _cached_2d == null:
		_cached_2d = load(SHADER_2D)
	return _cached_2d
