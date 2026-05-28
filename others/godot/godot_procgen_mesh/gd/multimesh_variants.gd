class_name MultiMeshVariants extends RefCounted

# 散佈大量同類物件（樹/岩石/建築）的 helper。
#
# 流程：
#   1. make_variants(generator, count)：給 N 個 seed 各跑一次 generator，產 N 種 mesh
#   2. distribute(transforms, variants)：把 transforms 隨機分配到各變體
#   3. build_multimeshes(buckets)：每個變體一個 MultiMesh，回傳 MultiMeshInstance3D 陣列
#
# 設計重點：
#   - 變體與散佈解耦：variants 可重用（同一森林裡多個聚落共用 4 種樹 mesh）
#   - 不寫死材質：呼叫端在拿到 MultiMeshInstance3D 後自己設 material_override


# 給 generator Callable 跑 N 次，回傳變體 mesh 陣列。
# generator: Callable(seed: int) -> Mesh
static func make_variants(generator: Callable, count: int,
		base_seed: int = 0) -> Array[Mesh]:
	var out: Array[Mesh] = []
	for i in count:
		out.append(generator.call(base_seed + i))
	return out


# 把 transforms 平均（但隨機）分配到 variant_count 個桶。
# 回傳：Array of Array[Transform3D]，長度 = variant_count
static func distribute(transforms: Array[Transform3D], variant_count: int,
		seed_: int = 0) -> Array:
	var buckets: Array = []
	buckets.resize(variant_count)
	for i in variant_count:
		buckets[i] = [] as Array[Transform3D]
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_
	for t in transforms:
		var idx := rng.randi_range(0, variant_count - 1)
		(buckets[idx] as Array[Transform3D]).append(t)
	return buckets


# 給每個變體建一個 MultiMeshInstance3D。
# 回傳的 instance 尚未 add_child，呼叫端自行擺到場景樹。
static func build_instances(variants: Array[Mesh], buckets: Array,
		material: Material = null) -> Array[MultiMeshInstance3D]:
	var out: Array[MultiMeshInstance3D] = []
	for i in variants.size():
		var transforms: Array[Transform3D] = buckets[i]
		if transforms.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.mesh = variants[i]
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.instance_count = transforms.size()
		for j in transforms.size():
			mm.set_instance_transform(j, transforms[j])

		var mm_node := MultiMeshInstance3D.new()
		mm_node.multimesh = mm
		mm_node.name = "Variant_" + str(i)
		if material:
			mm_node.material_override = material
		out.append(mm_node)
	return out


# 一鍵 pipeline：generator + transforms → Array[MultiMeshInstance3D]
static func scatter(generator: Callable, variant_count: int,
		transforms: Array[Transform3D], material: Material = null,
		seed_: int = 0) -> Array[MultiMeshInstance3D]:
	var variants := make_variants(generator, variant_count, seed_)
	var buckets := distribute(transforms, variant_count, seed_)
	return build_instances(variants, buckets, material)
