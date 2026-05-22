## 3D 大世界地圖渲染器
## 從 MapCoreGenerator 取得地圖資料，建立 TerrainMesh + WaterPlane。
## 預期場景結構：
##   WorldMap3D (Node3D)
##   ├── MapCoreGenerator        ← 掛 generator 屬性
##   ├── MapRenderer3D (此腳本)
##   │   ├── TerrainMesh (MeshInstance3D)   ← 掛 terrain_mesh_node 屬性
##   │   ├── WaterPlane  (MeshInstance3D)   ← 掛 water_plane_node 屬性
##   │   └── BiomeLayer  (Node3D)           ← 掛 biome_layer 屬性
##   └── CameraRig               ← 另外放置
class_name MapRenderer3D
extends Node3D

@export var generator: MapCoreGenerator
@export var terrain_mesh_node: MeshInstance3D
@export var water_plane_node: MeshInstance3D
@export var biome_layer: Node3D
@export var biome_scatter: BiomeScatter

@export_group("生成參數")
@export var tile_size: float = 1.0
@export var height_scale: float = 3.0
@export var jitter_amp: float = 0.05
## 水面 Y 高度；預設 = sea_level(0.4) × height_scale(3.0)
@export var sea_level_y: float = 1.2

func _ready() -> void:
	if not generator:
		push_error("MapRenderer3D: generator 未設定")
		return
	generator.generation_completed.connect(_on_generated)
	generator.generation_failed.connect(_on_failed)
	generator.generate_async()

# ── 回呼 ─────────────────────────────────────────────────────────────────────

func _on_generated(data: MapCoreMapData) -> void:
	_build_terrain(data)
	_build_water(data)
	_populate_biomes(data)
	print("MapRenderer3D: 地圖渲染完成，seed=", data.get_seed_used(),
		  "  尺寸=", data.get_width(), "×", data.get_height())

func _on_failed(message: String) -> void:
	push_error("MapRenderer3D: 生成失敗 — ", message)

# ── 地形 mesh ─────────────────────────────────────────────────────────────────

func _build_terrain(data: MapCoreMapData) -> void:
	if not terrain_mesh_node:
		return
	var builder := MapCoreTerrainMeshBuilder.new()
	terrain_mesh_node.mesh = builder.generate_terrain_mesh(
		data, tile_size, height_scale, jitter_amp
	)
	terrain_mesh_node.material_override = MaterialLibrary.make_vertex_color()

# ── 水面 ──────────────────────────────────────────────────────────────────────

func _build_water(data: MapCoreMapData) -> void:
	if not water_plane_node:
		return
	var map_w := data.get_width()  * tile_size
	var map_h := data.get_height() * tile_size

	var plane := PlaneMesh.new()
	plane.size = Vector2(map_w, map_h)
	water_plane_node.mesh = plane
	# PlaneMesh 以原點為中心，需要移到地圖中央
	water_plane_node.position = Vector3(map_w * 0.5, sea_level_y, map_h * 0.5)
	water_plane_node.material_override = MaterialLibrary.make_water()

# ── 生態圈散佈 ───────────────────────────────────────────────────────────────

func _populate_biomes(data: MapCoreMapData) -> void:
	if biome_scatter:
		biome_scatter.scatter(data)
