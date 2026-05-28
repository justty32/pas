class_name ProcBuilding extends RefCounted

# 程序生成 Low Poly 建築（落實 CONCEPT 待決事項：聚落/城市）。
# 純 GDScript，不依賴 C++。
#
# 結構：box 主體 + 屋頂（flat / gable / pyramid 三選一）。
# 窗門等細節留待擴充（CONCEPT 點明的「面內縮 vertex offset」可在 Level 2 補）。

enum RoofType { FLAT, GABLE, PYRAMID }


class Params:
	var width: float = 2.0    # X 軸
	var depth: float = 3.0    # Z 軸
	var height: float = 2.5   # Y 軸（屋頂下緣）
	var roof_type: int = RoofType.GABLE
	var roof_height: float = 1.0  # 屋頂額外高度
	var wall_color: Color = Color(0.85, 0.80, 0.70)
	var roof_color: Color = Color(0.55, 0.30, 0.20)
	var color_jitter: float = 0.05
	var seed: int = 0


static func generate(params: Params = null) -> ArrayMesh:
	if params == null:
		params = Params.new()

	var verts := PackedVector3Array()
	var colors := PackedColorArray()
	var rng := RandomNumberGenerator.new()
	rng.seed = params.seed

	# 主體 8 個角點（以建築中心為原點，底面 y=0，頂面 y=height）
	var hw := params.width * 0.5
	var hd := params.depth * 0.5
	var h := params.height

	# 角點別名：底面 b、頂面 t；NE/NW/SE/SW（XZ 平面）
	var b_ne := Vector3(hw, 0.0, -hd)
	var b_nw := Vector3(-hw, 0.0, -hd)
	var b_se := Vector3(hw, 0.0, hd)
	var b_sw := Vector3(-hw, 0.0, hd)
	var t_ne := Vector3(hw, h, -hd)
	var t_nw := Vector3(-hw, h, -hd)
	var t_se := Vector3(hw, h, hd)
	var t_sw := Vector3(-hw, h, hd)

	# 四面牆 + 底面（5 個矩形，每個拆兩三角）
	_push_quad(verts, t_nw, t_ne, b_ne, b_nw)  # 北牆
	_push_quad(verts, t_se, t_sw, b_sw, b_se)  # 南牆
	_push_quad(verts, t_sw, t_nw, b_nw, b_sw)  # 西牆
	_push_quad(verts, t_ne, t_se, b_se, b_ne)  # 東牆
	_push_quad(verts, b_ne, b_se, b_sw, b_nw)  # 底面（朝下）

	# 牆面顏色
	var wall_face_count := 5 * 2
	_push_face_colors(colors, wall_face_count, params.wall_color, params.color_jitter, rng)

	# 屋頂
	match params.roof_type:
		RoofType.FLAT:
			_push_quad(verts, t_nw, t_sw, t_se, t_ne)  # 平頂
			_push_face_colors(colors, 2, params.roof_color, params.color_jitter, rng)
		RoofType.GABLE:
			# 山牆屋頂：頂部沿 Z 軸有條脊線
			var ridge_n := Vector3(0.0, h + params.roof_height, -hd)
			var ridge_s := Vector3(0.0, h + params.roof_height, hd)
			# 東西兩斜面
			_push_quad(verts, t_ne, t_se, ridge_s, ridge_n)
			_push_quad(verts, t_sw, t_nw, ridge_n, ridge_s)
			# 南北兩三角山牆
			_push_tri(verts, t_nw, ridge_n, t_ne)
			_push_tri(verts, t_se, ridge_s, t_sw)
			_push_face_colors(colors, 6, params.roof_color, params.color_jitter, rng)
		RoofType.PYRAMID:
			var apex := Vector3(0.0, h + params.roof_height, 0.0)
			_push_tri(verts, t_nw, t_ne, apex)
			_push_tri(verts, t_ne, t_se, apex)
			_push_tri(verts, t_se, t_sw, apex)
			_push_tri(verts, t_sw, t_nw, apex)
			_push_face_colors(colors, 4, params.roof_color, params.color_jitter, rng)

	# verts 已是每三角面三頂點獨立的排列，可直接 flat_normalize 算法線。
	var mesh := ProcGeometry.build_mesh(verts, PackedInt32Array(), PackedVector3Array(), colors)
	return ProcGeometry.flat_normalize(mesh)


# 變體生成：給定 base params，產 N 種隨機尺寸/屋頂類型的變體。
static func make_variants(base: Params, count: int,
		size_jitter: float = 0.3) -> Array[ArrayMesh]:
	var out: Array[ArrayMesh] = []
	var rng := RandomNumberGenerator.new()
	rng.seed = base.seed
	for i in count:
		var p := Params.new()
		p.width = base.width * (1.0 + rng.randf_range(-size_jitter, size_jitter))
		p.depth = base.depth * (1.0 + rng.randf_range(-size_jitter, size_jitter))
		p.height = base.height * (1.0 + rng.randf_range(-size_jitter * 0.5, size_jitter * 0.5))
		p.roof_type = rng.randi_range(0, 2)
		p.roof_height = base.roof_height * (0.7 + rng.randf() * 0.6)
		p.wall_color = base.wall_color
		p.roof_color = base.roof_color
		p.color_jitter = base.color_jitter
		p.seed = base.seed + i
		out.append(generate(p))
	return out


# ── 內部 ──────────────────────────────────────────────────────────────────

# 四點構成的矩形拆成兩三角，CCW 看面正面。
static func _push_quad(verts: PackedVector3Array,
		a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	verts.append(a); verts.append(b); verts.append(c)
	verts.append(a); verts.append(c); verts.append(d)


static func _push_tri(verts: PackedVector3Array,
		a: Vector3, b: Vector3, c: Vector3) -> void:
	verts.append(a); verts.append(b); verts.append(c)


static func _push_face_colors(colors: PackedColorArray, face_count: int,
		base: Color, jitter: float, rng: RandomNumberGenerator) -> void:
	for f in face_count:
		var k := 1.0 + rng.randf_range(-jitter, jitter)
		var c := Color(
			clamp(base.r * k, 0.0, 1.0),
			clamp(base.g * k, 0.0, 1.0),
			clamp(base.b * k, 0.0, 1.0),
			base.a
		)
		colors.append(c); colors.append(c); colors.append(c)
