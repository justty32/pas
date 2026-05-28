class_name SpriteMaterial extends RefCounted

# 整合進 Godot 專案後，把以下兩條路徑改成實際擺放位置。
const SHADER_BASIC_PATH := "res://addons/godot_material/shaders/sprite_material.gdshader"
const SHADER_MULTISLOT_PATH := "res://addons/godot_material/shaders/sprite_material_multislot.gdshader"

enum BlendMode { MULTIPLY = 0, ADDITIVE = 1, SCREEN = 2 }

static var _cached_basic: Shader
static var _cached_multislot: Shader


static func apply(node: CanvasItem, material_tex: Texture2D,
		strength: float = 1.0, mode: int = BlendMode.MULTIPLY,
		tint: Color = Color.WHITE) -> ShaderMaterial:
	var sm := _ensure(node, _shader_basic())
	sm.set_shader_parameter(&"material_tex", material_tex)
	sm.set_shader_parameter(&"material_strength", strength)
	sm.set_shader_parameter(&"blend_mode", mode)
	sm.set_shader_parameter(&"tint", tint)
	return sm


static func apply_multislot(node: CanvasItem, mask: Texture2D,
		slot_r: Texture2D = null, slot_g: Texture2D = null, slot_b: Texture2D = null,
		tints: PackedColorArray = PackedColorArray([Color.WHITE, Color.WHITE, Color.WHITE]),
		strengths: Vector3 = Vector3.ONE) -> ShaderMaterial:
	var sm := _ensure(node, _shader_multislot())
	sm.set_shader_parameter(&"mask_tex", mask)
	if slot_r:
		sm.set_shader_parameter(&"slot_r_tex", slot_r)
	if slot_g:
		sm.set_shader_parameter(&"slot_g_tex", slot_g)
	if slot_b:
		sm.set_shader_parameter(&"slot_b_tex", slot_b)
	sm.set_shader_parameter(&"slot_r_tint", tints[0])
	sm.set_shader_parameter(&"slot_g_tint", tints[1])
	sm.set_shader_parameter(&"slot_b_tint", tints[2])
	sm.set_shader_parameter(&"slot_r_strength", strengths.x)
	sm.set_shader_parameter(&"slot_g_strength", strengths.y)
	sm.set_shader_parameter(&"slot_b_strength", strengths.z)
	return sm


static func clear(node: CanvasItem) -> void:
	node.material = null


static func make_solid_texture(color: Color, size: int = 4) -> ImageTexture:
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	img.fill(color)
	return ImageTexture.create_from_image(img)


static func _ensure(node: CanvasItem, shader: Shader) -> ShaderMaterial:
	var existing := node.material as ShaderMaterial
	if existing and existing.shader == shader:
		return existing
	var sm := ShaderMaterial.new()
	sm.shader = shader
	node.material = sm
	return sm


static func _shader_basic() -> Shader:
	if _cached_basic == null:
		_cached_basic = load(SHADER_BASIC_PATH)
	return _cached_basic


static func _shader_multislot() -> Shader:
	if _cached_multislot == null:
		_cached_multislot = load(SHADER_MULTISLOT_PATH)
	return _cached_multislot
