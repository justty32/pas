class_name Material3D extends RefCounted

# 整合進專案後，把這條路徑改成實際擺放位置。
const RIM_SHADER_PATH := "res://addons/godot_material_3d/shaders/rim_highlight.gdshader"

enum Shading { FLAT_UNSHADED, FLAT_LIT, SMOOTH_LIT }

static var _cached_rim: Shader


static func tint(color: Color, shading: Shading = Shading.FLAT_LIT,
		emission: float = 0.0) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	_apply_shading(mat, shading)
	if emission > 0.0:
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = emission
	return mat


static func vertex_color(shading: Shading = Shading.FLAT_LIT) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	_apply_shading(mat, shading)
	return mat


static func textured(albedo_tex: Texture2D, tint_color: Color = Color.WHITE,
		shading: Shading = Shading.FLAT_LIT) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = albedo_tex
	mat.albedo_color = tint_color
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST  # low poly / pixel 偏好
	_apply_shading(mat, shading)
	return mat


static func apply(mesh_instance: MeshInstance3D, mat: Material,
		surface_idx: int = -1) -> void:
	if surface_idx < 0:
		mesh_instance.material_override = mat
	else:
		mesh_instance.set_surface_override_material(surface_idx, mat)


static func apply_per_surface(mesh_instance: MeshInstance3D,
		mats: Array[Material]) -> void:
	for i in mats.size():
		mesh_instance.set_surface_override_material(i, mats[i])


static func make_rim(color: Color = Color.WHITE, rim_power: float = 2.0,
		rim_strength: float = 1.0) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	sm.shader = _rim_shader()
	sm.set_shader_parameter(&"albedo", color)
	sm.set_shader_parameter(&"rim_color", color)
	sm.set_shader_parameter(&"rim_power", rim_power)
	sm.set_shader_parameter(&"rim_strength", rim_strength)
	return sm


static func _apply_shading(mat: StandardMaterial3D, shading: Shading) -> void:
	match shading:
		Shading.FLAT_UNSHADED:
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		Shading.FLAT_LIT:
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
			# 真正 flat 視覺要靠 mesh 的法線（每面獨立頂點 + face normal），
			# StandardMaterial3D 沒有 flat shading 開關。
		Shading.SMOOTH_LIT:
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL


static func _rim_shader() -> Shader:
	if _cached_rim == null:
		_cached_rim = load(RIM_SHADER_PATH)
	return _cached_rim
