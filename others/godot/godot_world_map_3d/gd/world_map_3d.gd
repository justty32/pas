class_name WorldMap3D extends Node3D

# 可拆出複用的 3D 世界地圖 controller，不耦合 mapcore demo 場景結構。
#
# 與 mapcore_godot/demo/scenes/map_renderer_3d.gd 的差異：
#   demo 端：節點掛在 @export 屬性，自帶 MapCoreGenerator 訂閱、生成完直接渲染。
#   本檔：   外部準備好 MapCoreMapData 後直接 mount()，不假設怎麼生資料。
#            節點結構由 build_scene() 自動建（外部不必先擺好）。
#            climate 重塗為可選步驟（apply_climate_palette）。
#
# 整合進 Godot 專案時，需要：
#   - 載入 MapCore* GDExtension（mapcore_godot 已編出的 .so/.dll）
#   - 同步引用 ClimatePalette 與 BiomeScatterClimate（本目錄）
#   - 自己決定 mesh 來源：可呼叫 MapCoreTerrainMeshBuilder（C++）或自行 GDScript 生成

signal terrain_ready(data: MapCoreMapData)

@export_group("生成參數")
@export var tile_size: float = 1.0
@export var height_scale: float = 3.0
@export var jitter_amp: float = 0.05
@export var sea_level_y: float = 1.2  # 預設 = sea_level(0.4) × height_scale(3.0)

@export_group("Climate 推導")
## 是否在地形 mesh 上套用 climate 微調（terrain 給粗色、climate 給細色）。
@export var apply_climate_palette: bool = true
## climate 影響強度 [0, 1]。0=完全用 mapcore 原色，1=最強微調。
@export var climate_strength: float = 0.7

@export_group("生態圈散佈")
## 規則表：{name: BiomeScatterClimate.Rule, ...}，外部填入。
## 若留空且 auto_default_rules=true，會在 mount() 時用預設四條規則。
@export var auto_default_rules: bool = true

# ── 場景節點（mount 時自動建立 / 抓現有）──────────────────────────────────
var terrain_mesh_node: MeshInstance3D
var water_plane_node: MeshInstance3D
var biome_layer: Node3D

# ── 狀態 ──────────────────────────────────────────────────────────────────
var map_data: MapCoreMapData

# ── 散佈規則：{name: Rule}。外部可在 mount 前 set/clear。──────────────────
var _scatter_rules: Dictionary = {}

# ── 散佈使用的 mesh：{rule_name: Mesh}。外部 set，未設的會跳過該規則。───
var _scatter_meshes: Dictionary = {}


func _ready() -> void:
	_ensure_children()


# 外部把 mesh 設給每條規則用。範例：set_scatter_mesh("rocks", rock_mesh)
func set_scatter_mesh(rule_name: String, mesh: Mesh) -> void:
	_scatter_meshes[rule_name] = mesh


func set_scatter_rule(rule_name: String, rule: BiomeScatterClimate.Rule) -> void:
	rule.tile_size = tile_size
	rule.height_scale = height_scale
	_scatter_rules[rule_name] = rule


func clear_scatter_rules() -> void:
	_scatter_rules.clear()
	_scatter_meshes.clear()


# 主入口：吃 map_data，建好整張地圖。
func mount(data: MapCoreMapData, terrain_mesh: ArrayMesh) -> void:
	_ensure_children()
	map_data = data
	_build_terrain(data, terrain_mesh)
	_build_water(data)
	if auto_default_rules and _scatter_rules.is_empty():
		_install_default_rules()
	_populate_biomes(data)
	terrain_ready.emit(data)


# ── 內部：節點 ─────────────────────────────────────────────────────────────

func _ensure_children() -> void:
	if terrain_mesh_node == null:
		terrain_mesh_node = _ensure_child("TerrainMesh", MeshInstance3D)
	if water_plane_node == null:
		water_plane_node = _ensure_child("WaterPlane", MeshInstance3D)
	if biome_layer == null:
		biome_layer = _ensure_child("BiomeLayer", Node3D)


func _ensure_child(node_name: String, type) -> Node:
	var existing := get_node_or_null(node_name)
	if existing:
		return existing
	var n: Node = type.new()
	n.name = node_name
	add_child(n)
	return n


# ── 內部：地形 ────────────────────────────────────────────────────────────

func _build_terrain(data: MapCoreMapData, base_mesh: ArrayMesh) -> void:
	var mesh := base_mesh
	if apply_climate_palette:
		mesh = ClimatePalette.recolor_terrain_mesh(mesh, data, tile_size, climate_strength)
	terrain_mesh_node.mesh = mesh

	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED  # mapcore 三角面正面朝下，避免看穿
	terrain_mesh_node.material_override = mat


# ── 內部：水面 ────────────────────────────────────────────────────────────

func _build_water(data: MapCoreMapData) -> void:
	var map_w := data.get_width() * tile_size
	var map_h := data.get_height() * tile_size
	var plane := PlaneMesh.new()
	plane.size = Vector2(map_w, map_h)
	water_plane_node.mesh = plane
	water_plane_node.position = Vector3(map_w * 0.5, sea_level_y, map_h * 0.5)

	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(0.15, 0.40, 0.70, 0.60)
	mat.roughness = 0.1
	mat.metallic_specular = 0.5
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	water_plane_node.material_override = mat


# ── 內部：散佈 ────────────────────────────────────────────────────────────

func _install_default_rules() -> void:
	set_scatter_rule("forest", BiomeScatterClimate.rule_forest())
	set_scatter_rule("shrub", BiomeScatterClimate.rule_shrub())
	set_scatter_rule("rocks", BiomeScatterClimate.rule_rocks())
	set_scatter_rule("cactus", BiomeScatterClimate.rule_cactus())


func _populate_biomes(data: MapCoreMapData) -> void:
	for child in biome_layer.get_children():
		child.queue_free()

	for rule_name in _scatter_rules:
		var mesh: Mesh = _scatter_meshes.get(rule_name)
		if mesh == null:
			continue  # 規則登記但 mesh 沒餵 → 跳過（外部按需提供）
		var rule: BiomeScatterClimate.Rule = _scatter_rules[rule_name]
		var transforms := BiomeScatterClimate.compute(data, rule)
		if transforms.is_empty():
			continue
		var mm_node := MultiMeshInstance3D.new()
		mm_node.name = "Scatter_" + rule_name
		mm_node.multimesh = BiomeScatterClimate.build_multimesh(mesh, transforms)
		var vc_mat := StandardMaterial3D.new()
		vc_mat.vertex_color_use_as_albedo = true
		vc_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mm_node.material_override = vc_mat
		biome_layer.add_child(mm_node)
