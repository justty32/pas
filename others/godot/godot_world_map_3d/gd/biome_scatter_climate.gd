class_name BiomeScatterClimate extends RefCounted

# 落實 memory 提到的「純 GDScript 從 climate 推導生態」的散佈面。
#
# 與 mapcore demo 端 biome_scatter.gd 的差異：
#   demo 端：terrain == FOREST → 放樹；terrain == MOUNTAIN → 放岩石。
#            純依離散 enum，沒有「乾燥森林比較稀疏」「高溫沙漠長仙人掌」這種細節。
#   本檔：   給每種散佈物件一條 climate predicate（傳入 terrain/temp/rain 回傳放置機率），
#            外部呼叫端決定 mesh / multimesh 怎麼建。這支只回傳 transform 陣列。
#
# 故意「不直接持有 MultiMeshInstance3D」——decouple 程度比 demo 高，
# 給外部組裝。回傳 Array[Transform3D] 比較好複用（測試也好寫）。

const TerrainID := {
	OCEAN = 0, COAST = 1, PLAINS = 2, GRASSLAND = 3, DESERT = 4, TUNDRA = 5,
	SNOW = 6, FOREST = 7, HILL = 8, MOUNTAIN = 9, LAKE = 10,
}


class Rule:
	# predicate(terrain_id:int, temperature:float, rainfall:float) -> float [0..1]
	#   回傳每格放置物件的「期望數量倍率」。0=不放，1=每格一個，2=每格兩個。
	var predicate: Callable

	# 每格內部位置擾動範圍（tile 比例），0~0.5。
	var jitter: float = 0.3

	# 縮放範圍（min, max）。
	var scale_range: Vector2 = Vector2(0.65, 1.35)

	# 隨機 Y 軸旋轉。
	var random_yaw: bool = true

	# 對應到的 terrain Y 高度乘以這個倍率（一致於 mapcore demo 的 height_scale）。
	var height_scale: float = 3.0

	# 物件擺位的 tile 大小。
	var tile_size: float = 1.0

	# RNG seed（同 seed 同地圖 → 同擺位，方便 debug 與儲存）。
	var seed: int = 0

	func _init(p: Callable, s: int = 0) -> void:
		predicate = p
		seed = s


# 內建：森林規則（潮濕、不太冷的 FOREST 才密集；乾燥的 FOREST 稀疏）
static func rule_forest(seed_: int = 7777) -> Rule:
	return Rule.new(func(terrain: int, t: float, r: float) -> float:
		if terrain != TerrainID.FOREST:
			return 0.0
		# 基礎 1.0，溫度太低／太高、降雨太少 → 降密度
		var density := 1.0
		if r < 600.0:
			density *= clamp(r / 600.0, 0.2, 1.0)
		if t < -5.0:
			density *= 0.4  # 北方針葉林邊緣
		elif t > 30.0:
			density *= 0.6  # 熱帶邊緣
		return density
	, seed_)


# 內建：草原灌木（GRASSLAND + 中等降雨稀疏放灌木）
static func rule_shrub(seed_: int = 3333) -> Rule:
	var rule := Rule.new(func(terrain: int, t: float, r: float) -> float:
		if terrain != TerrainID.GRASSLAND and terrain != TerrainID.PLAINS:
			return 0.0
		if r < 200.0:
			return 0.0
		return 0.25 * clamp((r - 200.0) / 600.0, 0.0, 1.0)
	, seed_)
	rule.scale_range = Vector2(0.4, 0.8)
	return rule


# 內建：山脈岩石（MOUNTAIN 多顆 + HILL 偶爾）
static func rule_rocks(seed_: int = 999) -> Rule:
	var rule := Rule.new(func(terrain: int, _t: float, _r: float) -> float:
		match terrain:
			TerrainID.MOUNTAIN:
				return 2.5
			TerrainID.HILL:
				return 0.3
			_:
				return 0.0
	, seed_)
	rule.scale_range = Vector2(0.45, 1.55)
	return rule


# 內建：沙漠仙人掌（乾燥 DESERT + 一定溫度）
static func rule_cactus(seed_: int = 4242) -> Rule:
	return Rule.new(func(terrain: int, t: float, r: float) -> float:
		if terrain != TerrainID.DESERT:
			return 0.0
		if r > 300.0:
			return 0.0
		if t < 10.0:
			return 0.0
		return 0.15
	, seed_)


# 主 API：依規則對全圖計算放置 transforms。
static func compute(data: MapCoreMapData, rule: Rule) -> Array[Transform3D]:
	var out: Array[Transform3D] = []
	var rng := RandomNumberGenerator.new()
	rng.seed = rule.seed

	for z in data.get_height():
		for x in data.get_width():
			var terrain := data.get_terrain(x, z)
			var t := data.get_temperature(x, z)
			var r := data.get_rainfall(x, z)
			var density: float = rule.predicate.call(terrain, t, r)
			if density <= 0.0:
				continue
			# density>=1 整數部分必放、小數部分機率
			var whole := int(density)
			var frac := density - whole
			var count := whole + (1 if rng.randf() < frac else 0)

			var h := data.get_height_value(x, z) * rule.height_scale
			for _i in count:
				var jit := rule.jitter
				var xof := rng.randf_range(-jit, jit) * rule.tile_size
				var zof := rng.randf_range(-jit, jit) * rule.tile_size
				var pos := Vector3(
					(x + 0.5 + xof) * rule.tile_size,
					h,
					(z + 0.5 + zof) * rule.tile_size
				)
				var yaw := (rng.randf() * TAU) if rule.random_yaw else 0.0
				var sc := lerp(rule.scale_range.x, rule.scale_range.y, rng.randf())
				var basis := Basis.from_euler(Vector3(0.0, yaw, 0.0)).scaled(Vector3.ONE * sc)
				out.append(Transform3D(basis, pos))
	return out


# 給定 mesh + transforms 一鍵建出 MultiMeshInstance3D 用的 MultiMesh。
static func build_multimesh(mesh: Mesh, transforms: Array[Transform3D]) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.mesh = mesh
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.instance_count = transforms.size()
	for i in transforms.size():
		mm.set_instance_transform(i, transforms[i])
	return mm
