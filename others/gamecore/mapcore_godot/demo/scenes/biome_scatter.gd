## 依 mapcore 地圖資料在地形上散佈程序生成物件（岩石、樹木）。
## 使用 MultiMesh 實現 GPU instancing，大量物件不影響 draw call 數。
##
## 場景結構範例：
##   BiomeScatter（此腳本）
##   ├── RocksMultiMesh (MultiMeshInstance3D)  ← 掛 rocks_multi_node
##   └── TreesMultiMesh (MultiMeshInstance3D)  ← 掛 trees_multi_node
##
## 使用方式：
##   biome_scatter.scatter(map_data)
class_name BiomeScatter
extends Node3D

@export var rocks_multi_node: MultiMeshInstance3D
@export var trees_multi_node: MultiMeshInstance3D

@export_group("岩石參數")
@export var rock_radius:    float = 0.55   ## 代表性岩石半徑（instance 會再 ×0.5~1.5 縮放）
@export var rock_roughness: float = 0.25
@export var rock_per_cell:  int   = 3      ## MOUNTAIN 每格最多幾顆岩石

@export_group("樹木參數")
@export var tree_cone_count:  int   = 3    ## 樹冠錐形數
@export var trunk_height:     float = 1.1
@export var trunk_radius:     float = 0.07
@export var foliage_radius:   float = 0.55

@export_group("地圖參數")
@export var tile_size:    float = 1.0
@export var height_scale: float = 3.0

# ── 公開 API ──────────────────────────────────────────────────────────────────

func scatter(data: MapCoreMapData) -> void:
	_scatter_rocks(data)
	_scatter_trees(data)

# ── 岩石 ──────────────────────────────────────────────────────────────────────

func _scatter_rocks(data: MapCoreMapData) -> void:
	if not rocks_multi_node:
		return

	var builder := MapCoreProcGenMeshBuilder.new()
	var rock_mesh: ArrayMesh = builder.generate_rock(rock_radius, rock_roughness, 42)

	var transforms: Array[Transform3D] = []
	var rng := RandomNumberGenerator.new()
	rng.seed = 999

	for z in data.get_height():
		for x in data.get_width():
			if data.get_terrain(x, z) != MapCoreMapData.TERRAIN_MOUNTAIN:
				continue
			var h    := data.get_height_value(x, z) * height_scale
			var count := rng.randi_range(1, rock_per_cell)
			for _i in count:
				var ry  := rng.randf() * TAU
				var sc  := 0.45 + rng.randf() * 1.1  # 0.45x~1.55x，讓大小差異明顯
				var xof := rng.randf_range(-0.35, 0.35) * tile_size
				var zof := rng.randf_range(-0.35, 0.35) * tile_size
				var pos := Vector3(
					(x + 0.5 + xof) * tile_size,
					h,
					(z + 0.5 + zof) * tile_size
				)
				var basis := Basis.from_euler(Vector3(0.0, ry, 0.0)).scaled(Vector3.ONE * sc)
				transforms.append(Transform3D(basis, pos))

	if transforms.is_empty():
		return

	var mm := MultiMesh.new()
	mm.mesh             = rock_mesh
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.instance_count   = transforms.size()
	for i in transforms.size():
		mm.set_instance_transform(i, transforms[i])
	rocks_multi_node.multimesh = mm
	# C++ 生成的 mesh 帶頂點色，需要讀 ARRAY_COLOR 的材質才會上色
	rocks_multi_node.material_override = MaterialLibrary.make_vertex_color()

# ── 樹木 ──────────────────────────────────────────────────────────────────────

func _scatter_trees(data: MapCoreMapData) -> void:
	if not trees_multi_node:
		return

	var builder := MapCoreProcGenMeshBuilder.new()
	var trunk_mesh   : ArrayMesh = builder.generate_tree_trunk(trunk_height, trunk_radius, 1234)
	var foliage_mesh : ArrayMesh = builder.generate_tree_foliage(foliage_radius, tree_cone_count, 5678)

	# 樹冠放在樹幹頂端（略微往下 15% 以避免縫隙）
	var foliage_offset := Transform3D(Basis(), Vector3(0.0, trunk_height * 0.85, 0.0))
	var tree_mesh := _merge_meshes(trunk_mesh, foliage_mesh, Transform3D(), foliage_offset)

	var transforms: Array[Transform3D] = []
	var rng := RandomNumberGenerator.new()
	rng.seed = 7777

	for z in data.get_height():
		for x in data.get_width():
			if data.get_terrain(x, z) != MapCoreMapData.TERRAIN_FOREST:
				continue
			var h  := data.get_height_value(x, z) * height_scale
			var ry := rng.randf() * TAU
			var sc := 0.65 + rng.randf() * 0.70  # 0.65x~1.35x
			var xof := rng.randf_range(-0.20, 0.20) * tile_size
			var zof := rng.randf_range(-0.20, 0.20) * tile_size
			var pos := Vector3(
				(x + 0.5 + xof) * tile_size,
				h,
				(z + 0.5 + zof) * tile_size
			)
			var basis := Basis.from_euler(Vector3(0.0, ry, 0.0)).scaled(Vector3.ONE * sc)
			transforms.append(Transform3D(basis, pos))

	if transforms.is_empty():
		return

	var mm := MultiMesh.new()
	mm.mesh             = tree_mesh
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.instance_count   = transforms.size()
	for i in transforms.size():
		mm.set_instance_transform(i, transforms[i])
	trees_multi_node.multimesh = mm
	# C++ 生成的 mesh 帶頂點色，需要讀 ARRAY_COLOR 的材質才會上色
	trees_multi_node.material_override = MaterialLibrary.make_vertex_color()

# ── 合併兩個 ArrayMesh 的第一個 surface（純 GDScript，不需 C++）─────────────

static func _merge_meshes(
	mesh_a: ArrayMesh, mesh_b: ArrayMesh,
	xform_a: Transform3D, xform_b: Transform3D
) -> ArrayMesh:
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols  := PackedColorArray()

	for pair in [[mesh_a, xform_a], [mesh_b, xform_b]]:
		var m  : ArrayMesh    = pair[0]
		var xf : Transform3D  = pair[1]
		if m == null or m.get_surface_count() == 0:
			continue
		var arr := m.surface_get_arrays(0)
		var sv  := arr[Mesh.ARRAY_VERTEX] as PackedVector3Array
		var sn  := arr[Mesh.ARRAY_NORMAL] as PackedVector3Array
		var sc  := arr[Mesh.ARRAY_COLOR]  as PackedColorArray
		if sv == null:
			continue
		for i in sv.size():
			verts.append(xf * sv[i])
			# 只有旋轉/縮放影響法線，位移不影響
			norms.append((xf.basis * sn[i]).normalized() if sn else Vector3.UP)
			cols.append(sc[i] if (sc and i < sc.size()) else Color.WHITE)

	var combined_arr := Array()
	combined_arr.resize(Mesh.ARRAY_MAX)
	combined_arr[Mesh.ARRAY_VERTEX] = verts
	combined_arr[Mesh.ARRAY_NORMAL] = norms
	combined_arr[Mesh.ARRAY_COLOR]  = cols

	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, combined_arr)
	return out
