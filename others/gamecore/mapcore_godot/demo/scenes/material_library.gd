## 3D 材質工廠 + 調色盤
##
## 三大功能：
##   1. 調色盤常數：BIOME_COLORS / RARITY_COLORS / FACTION_COLORS
##   2. 靜態工廠方法（無需 instance）：make_unshaded / make_lit / make_vertex_color 等
##   3. 材質快取：相同參數只建立一份 StandardMaterial3D，共享給多個 MeshInstance3D
##
## 注意：快取材質是「共享」物件。若需要獨立動畫（如閃爍），呼叫後自行 .duplicate()。
##
## 使用範例：
##   mesh.material_override = MaterialLibrary.make_unshaded(MaterialLibrary.RARITY_COLORS["rare"])
##   mesh.material_override = MaterialLibrary.make_vertex_color()
class_name MaterialLibrary
extends RefCounted

# ── 調色盤：地形生態圈（與 terrain_mesh_builder.cpp 顏色映射一致）──────────────
const BIOME_COLORS: Dictionary = {
	"OCEAN":     Color(0.08, 0.25, 0.55),
	"COAST":     Color(0.20, 0.45, 0.70),
	"PLAINS":    Color(0.65, 0.70, 0.35),
	"GRASSLAND": Color(0.30, 0.60, 0.25),
	"DESERT":    Color(0.80, 0.70, 0.38),
	"TUNDRA":    Color(0.60, 0.65, 0.70),
	"SNOW":      Color(0.85, 0.90, 0.95),
	"FOREST":    Color(0.15, 0.40, 0.15),
	"HILL":      Color(0.55, 0.48, 0.35),
	"MOUNTAIN":  Color(0.60, 0.58, 0.55),
	"LAKE":      Color(0.15, 0.40, 0.65),
}

# ── 調色盤：物品稀有度 ─────────────────────────────────────────────────────────
const RARITY_COLORS: Dictionary = {
	"common":    Color(0.75, 0.75, 0.75),
	"uncommon":  Color(0.30, 0.70, 0.30),
	"rare":      Color(0.20, 0.40, 0.85),
	"epic":      Color(0.60, 0.20, 0.80),
	"legendary": Color(0.90, 0.55, 0.10),
}

# ── 調色盤：陣營 ──────────────────────────────────────────────────────────────
const FACTION_COLORS: Dictionary = {
	"player":  Color(0.20, 0.50, 0.90),
	"enemy":   Color(0.85, 0.20, 0.20),
	"neutral": Color(0.60, 0.60, 0.60),
	"ally":    Color(0.20, 0.75, 0.40),
}

# ── 材質快取 ─────────────────────────────────────────────────────────────────
static var _cache: Dictionary = {}

# ── 工廠：無光照 ──────────────────────────────────────────────────────────────
## Unshaded（顏色不受燈光影響）；Low Poly 卡通感首選。
static func make_unshaded(color: Color) -> StandardMaterial3D:
	var key := "u|" + _ck(color)
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color  = color
	_cache[key] = mat
	return mat

# ── 工廠：受光照 PBR ──────────────────────────────────────────────────────────
## 保留 PBR 燈光；搭配 flat shading mesh 可呈現有明暗的 Low Poly。
static func make_lit(
		color:     Color,
		metallic:  float = 0.0,
		roughness: float = 0.8
) -> StandardMaterial3D:
	var key := "l|" + _ck(color) + "|%.2f|%.2f" % [metallic, roughness]
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.albedo_color  = color
	mat.metallic      = metallic
	mat.roughness     = roughness
	_cache[key] = mat
	return mat

# ── 工廠：頂點色 ──────────────────────────────────────────────────────────────
## 讀取 ARRAY_COLOR 通道作為 albedo；用於 C++ 生成的帶色頂點 mesh（如地形）。
static func make_vertex_color(unshaded: bool = true) -> StandardMaterial3D:
	var key := "vc|" + str(unshaded)
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = (
		BaseMaterial3D.SHADING_MODE_UNSHADED if unshaded
		else BaseMaterial3D.SHADING_MODE_PER_PIXEL
	)
	_cache[key] = mat
	return mat

# ── 工廠：半透明 ──────────────────────────────────────────────────────────────
## 通用半透明材質（迷霧 overlay、玻璃等）。
static func make_transparent(color: Color, alpha: float = 0.6) -> StandardMaterial3D:
	var c   := Color(color.r, color.g, color.b, alpha)
	var key := "tr|" + _ck(c)
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color  = c
	mat.roughness     = 0.5
	mat.shading_mode  = BaseMaterial3D.SHADING_MODE_UNSHADED
	_cache[key] = mat
	return mat

# ── 工廠：水面 ────────────────────────────────────────────────────────────────
## 水面專用：半透明 + 低粗糙度 + metallic_specular 增強反射感。
static func make_water(color: Color = Color(0.15, 0.40, 0.70), alpha: float = 0.60) -> StandardMaterial3D:
	var c   := Color(color.r, color.g, color.b, alpha)
	var key := "wa|" + _ck(c)
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.transparency      = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color       = c
	mat.roughness          = 0.1
	mat.metallic_specular  = 0.5
	mat.shading_mode       = BaseMaterial3D.SHADING_MODE_UNSHADED
	_cache[key] = mat
	return mat

# ── 工廠：自發光 ──────────────────────────────────────────────────────────────
## 傳奇物品、特效、高亮圖示；emission_color 建議用 RARITY_COLORS["legendary"] 等。
static func make_emission(
		albedo:   Color,
		emission: Color = Color.WHITE,
		energy:   float = 1.5
) -> StandardMaterial3D:
	var key := "em|" + _ck(albedo) + "|" + _ck(emission) + "|%.2f" % energy
	if _cache.has(key):
		return _cache[key]
	var mat := StandardMaterial3D.new()
	mat.shading_mode               = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color                = albedo
	mat.emission_enabled            = true
	mat.emission                    = emission
	mat.emission_energy_multiplier  = energy
	_cache[key] = mat
	return mat

# ── 工廠：Rim Glow ShaderMaterial ────────────────────────────────────────────
## 邊緣發光效果（選取高亮、特殊單位）；shader 由呼叫方 preload 傳入。
## 範例：
##   var shader := preload("res://scenes/shaders/rim_glow.gdshader")
##   unit.material_override = MaterialLibrary.make_rim(shader, Color(0.2, 0.5, 0.9))
##
## 此方法不快取（per-instance 效果，通常各物件參數不同）。
static func make_rim(
		shader:       Shader,
		albedo:       Color = Color(0.2, 0.5, 0.9),
		rim_color:    Color = Color.WHITE,
		rim_power:    float = 2.0,
		rim_strength: float = 0.8
) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = shader
	mat.set_shader_parameter("albedo",        albedo)
	mat.set_shader_parameter("rim_color",     rim_color)
	mat.set_shader_parameter("rim_power",     rim_power)
	mat.set_shader_parameter("rim_strength",  rim_strength)
	return mat

# ── 快取管理 ──────────────────────────────────────────────────────────────────
## 場景切換或記憶體壓力時呼叫，釋放所有快取的材質物件。
static func clear_cache() -> void:
	_cache.clear()

# ── 私有輔助 ─────────────────────────────────────────────────────────────────

static func _ck(c: Color) -> String:
	return "%.3f,%.3f,%.3f,%.3f" % [c.r, c.g, c.b, c.a]
