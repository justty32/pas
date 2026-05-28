class_name ProcGeometry extends RefCounted

# 共用 mesh 處理工具。純 GDScript（無 C++ 依賴）。
#
# 三大用途：
#   1. flat_normalize() — 把任意 mesh 變成 per-face 獨立頂點 + face normal
#      （low poly flat shading 的關鍵，CONCEPT 強調）
#   2. apply_noise_displacement() — 用 FastNoiseLite 在頂點上加位移
#   3. apply_face_color_jitter() — 給每三角面隨機微調顏色（規避工業感技法之一）


# 把共享頂點 mesh 變成「每個三角面三個獨立頂點 + 面法線」。
# 副作用：頂點數 = 面數 × 3（大幅膨脹，僅適合 low poly）。
static func flat_normalize(mesh: ArrayMesh) -> ArrayMesh:
	if mesh == null or mesh.get_surface_count() == 0:
		return mesh

	var arrays := mesh.surface_get_arrays(0)
	var src_v := arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array
	var src_c := arrays[Mesh.ARRAY_COLOR] as PackedColorArray
	var src_i := arrays[Mesh.ARRAY_INDEX] as PackedInt32Array
	if src_v == null:
		return mesh

	# 若沒 index，視為 verts 已是 per-triangle 排列（每 3 個一面），直接重算法線。
	var face_count := (src_i.size() / 3) if src_i and src_i.size() > 0 else (src_v.size() / 3)

	var out_v := PackedVector3Array()
	var out_n := PackedVector3Array()
	var out_c := PackedColorArray()
	out_v.resize(face_count * 3)
	out_n.resize(face_count * 3)
	if src_c and src_c.size() > 0:
		out_c.resize(face_count * 3)

	for f in face_count:
		var i0: int
		var i1: int
		var i2: int
		if src_i and src_i.size() > 0:
			i0 = src_i[f * 3]
			i1 = src_i[f * 3 + 1]
			i2 = src_i[f * 3 + 2]
		else:
			i0 = f * 3
			i1 = f * 3 + 1
			i2 = f * 3 + 2

		var v0 := src_v[i0]
		var v1 := src_v[i1]
		var v2 := src_v[i2]
		var n := (v1 - v0).cross(v2 - v0).normalized()

		out_v[f * 3] = v0
		out_v[f * 3 + 1] = v1
		out_v[f * 3 + 2] = v2
		out_n[f * 3] = n
		out_n[f * 3 + 1] = n
		out_n[f * 3 + 2] = n
		if src_c and src_c.size() > 0:
			out_c[f * 3] = src_c[i0]
			out_c[f * 3 + 1] = src_c[i1]
			out_c[f * 3 + 2] = src_c[i2]

	var dst_arr := []
	dst_arr.resize(Mesh.ARRAY_MAX)
	dst_arr[Mesh.ARRAY_VERTEX] = out_v
	dst_arr[Mesh.ARRAY_NORMAL] = out_n
	if out_c.size() > 0:
		dst_arr[Mesh.ARRAY_COLOR] = out_c

	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, dst_arr)
	return out


# 對每個頂點加 noise 位移。輸入需是「已 flat_normalize 過的 mesh」否則同頂點會跑開。
# 不太對——其實對共享頂點 mesh 也能跑，但跑完該 mesh 已不再共享頂點。
# 簡化：本函式建議在 flat_normalize 之前對「per-vertex unique mesh」（icosphere 等）用，
# 之後再 flat_normalize 重算法線。
static func apply_noise_displacement(mesh: ArrayMesh, frequency: float = 1.5,
		amplitude: float = 0.15, seed_: int = 0) -> ArrayMesh:
	if mesh == null or mesh.get_surface_count() == 0:
		return mesh

	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX
	noise.seed = seed_
	noise.frequency = frequency

	var arrays := mesh.surface_get_arrays(0)
	var verts := (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).duplicate()

	for i in verts.size():
		var v := verts[i]
		var n := v.normalized() if v.length() > 0.001 else Vector3.UP
		var disp := noise.get_noise_3dv(v) * amplitude
		verts[i] = v + n * disp

	arrays[Mesh.ARRAY_VERTEX] = verts
	# 因為動了頂點，原 normals 失效——清空讓呼叫端決定要不要 flat_normalize
	arrays[Mesh.ARRAY_NORMAL] = PackedVector3Array()

	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return out


# 對 mesh 每個三角面（假設已 flat_normalize）的三頂點染上「base ± jitter」的色。
# CONCEPT 規避工業感技法：面色調抖動。
static func apply_face_color_jitter(mesh: ArrayMesh, base: Color,
		jitter: float = 0.05, seed_: int = 0) -> ArrayMesh:
	if mesh == null or mesh.get_surface_count() == 0:
		return mesh

	var rng := RandomNumberGenerator.new()
	rng.seed = seed_
	var arrays := mesh.surface_get_arrays(0)
	var verts := arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array
	if verts == null:
		return mesh

	var face_count := verts.size() / 3
	var cols := PackedColorArray()
	cols.resize(verts.size())

	for f in face_count:
		var k := 1.0 + rng.randf_range(-jitter, jitter)
		var c := Color(
			clamp(base.r * k, 0.0, 1.0),
			clamp(base.g * k, 0.0, 1.0),
			clamp(base.b * k, 0.0, 1.0),
			base.a
		)
		cols[f * 3] = c
		cols[f * 3 + 1] = c
		cols[f * 3 + 2] = c

	arrays[Mesh.ARRAY_COLOR] = cols
	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return out


# 給定 verts/indices 一鍵建 mesh（colors/normals 可選）。
static func build_mesh(verts: PackedVector3Array,
		indices: PackedInt32Array = PackedInt32Array(),
		normals: PackedVector3Array = PackedVector3Array(),
		colors: PackedColorArray = PackedColorArray()) -> ArrayMesh:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	if indices.size() > 0:
		arrays[Mesh.ARRAY_INDEX] = indices
	if normals.size() > 0:
		arrays[Mesh.ARRAY_NORMAL] = normals
	if colors.size() > 0:
		arrays[Mesh.ARRAY_COLOR] = colors
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh
