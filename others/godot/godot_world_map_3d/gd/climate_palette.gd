class_name ClimatePalette extends RefCounted

# 落實「純 GDScript 從 climate 推導生態」的最小解鎖（不改 C++）。
#
# 背景：mapcore C++ 端的 terrain enum 是離散 11 類，
# 同一 enum 在「赤道沙漠」與「極地凍土邊緣」可能用同一顏色，視覺扁平。
# climate（temperature / rainfall）由 mapcore 一併輸出，但 demo 端的 MaterialLibrary
# 只依 terrain 上色。這層做的是「terrain 給粗色，climate 給細色」。
#
# 因為地形 mesh 已是 C++ 烘好的 vertex color，這裡的微調必須在 GDScript 端
# 「事後重塗」：抓 ArrayMesh 的 ARRAY_COLOR 陣列、依每頂點對應的格座標查 climate，
# 算 delta 後寫回。terrain_mesh_builder 用非共享頂點（每三角面三頂點獨立），
# 重塗成本只是 cells × 6 個 Color 寫入，地圖 64×64 約 24k 個寫入，可接受。

const BASE_BIOME := {
	# 與 mapcore terrain_mesh_builder.cpp 顏色映射一致；改這裡 = 改基底色票。
	0:  Color(0.08, 0.25, 0.55),  # OCEAN
	1:  Color(0.20, 0.45, 0.70),  # COAST
	2:  Color(0.65, 0.70, 0.35),  # PLAINS
	3:  Color(0.30, 0.60, 0.25),  # GRASSLAND
	4:  Color(0.80, 0.70, 0.38),  # DESERT
	5:  Color(0.60, 0.65, 0.70),  # TUNDRA
	6:  Color(0.85, 0.90, 0.95),  # SNOW
	7:  Color(0.15, 0.40, 0.15),  # FOREST
	8:  Color(0.55, 0.48, 0.35),  # HILL
	9:  Color(0.60, 0.58, 0.55),  # MOUNTAIN
	10: Color(0.15, 0.40, 0.65),  # LAKE
}

# 溫度錨點（攝氏 → 色調偏移）。
# 冷的偏藍 / 熱的偏黃。中性帶 [5°C, 20°C] 不偏。
const TEMP_COOL_THRESHOLD := 5.0
const TEMP_WARM_THRESHOLD := 20.0
const TEMP_COOL_TINT := Color(0.85, 0.92, 1.05)  # 帶冷感
const TEMP_WARM_TINT := Color(1.08, 1.02, 0.85)  # 帶暖感

# 降雨錨點（mm → 飽和度偏移）。
# 乾燥區降飽和、潮濕區提飽和。中性帶 [400, 1200] mm 不調。
const RAIN_DRY_THRESHOLD := 400.0
const RAIN_WET_THRESHOLD := 1200.0
const SAT_DRY_FACTOR := 0.85
const SAT_WET_FACTOR := 1.10


static func base_color(terrain_id: int) -> Color:
	return BASE_BIOME.get(terrain_id, Color.MAGENTA)


# 對單一頂點顏色加上 climate 微調。strength=0 退回基底色；strength=1 完整套用。
static func adjust(base: Color, temperature: float, rainfall: float,
		strength: float = 1.0) -> Color:
	if temperature <= -990.0 or rainfall < 0.0:
		return base  # 未生成氣候資料時退回基底
	var c := base

	# 溫度：低於 cool / 高於 warm 才偏色
	if temperature < TEMP_COOL_THRESHOLD:
		var t := clamp((TEMP_COOL_THRESHOLD - temperature) / 20.0, 0.0, 1.0) * strength
		c = _tint(c, TEMP_COOL_TINT, t)
	elif temperature > TEMP_WARM_THRESHOLD:
		var t := clamp((temperature - TEMP_WARM_THRESHOLD) / 15.0, 0.0, 1.0) * strength
		c = _tint(c, TEMP_WARM_TINT, t)

	# 降雨：乾／濕修飽和度
	if rainfall < RAIN_DRY_THRESHOLD:
		var k := clamp((RAIN_DRY_THRESHOLD - rainfall) / 400.0, 0.0, 1.0) * strength
		c = _saturate(c, lerp(1.0, SAT_DRY_FACTOR, k))
	elif rainfall > RAIN_WET_THRESHOLD:
		var k := clamp((rainfall - RAIN_WET_THRESHOLD) / 800.0, 0.0, 1.0) * strength
		c = _saturate(c, lerp(1.0, SAT_WET_FACTOR, k))

	return c


# 對整個 mesh 的頂點色就地重塗。回傳新的 ArrayMesh（原 mesh 不動）。
# tile_size / map_width 需要與 MapCoreTerrainMeshBuilder 生成參數一致，
# 否則頂點對不回正確的格座標。
static func recolor_terrain_mesh(mesh: ArrayMesh, data: MapCoreMapData,
		tile_size: float = 1.0, strength: float = 1.0) -> ArrayMesh:
	if mesh == null or mesh.get_surface_count() == 0:
		return mesh

	var arrays := mesh.surface_get_arrays(0)
	var verts := arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array
	var cols := arrays[Mesh.ARRAY_COLOR] as PackedColorArray
	if verts == null or cols == null or cols.size() != verts.size():
		push_warning("ClimatePalette.recolor_terrain_mesh: mesh 缺 vertex color，跳過")
		return mesh

	var w := data.get_width()
	var h := data.get_height()

	for i in cols.size():
		var x := int(verts[i].x / tile_size)
		var z := int(verts[i].z / tile_size)
		x = clamp(x, 0, w - 1)
		z = clamp(z, 0, h - 1)
		var t := data.get_temperature(x, z)
		var r := data.get_rainfall(x, z)
		cols[i] = adjust(cols[i], t, r, strength)

	arrays[Mesh.ARRAY_COLOR] = cols
	var out := ArrayMesh.new()
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return out


static func _tint(c: Color, tint: Color, k: float) -> Color:
	return Color(
		lerp(c.r, c.r * tint.r, k),
		lerp(c.g, c.g * tint.g, k),
		lerp(c.b, c.b * tint.b, k),
		c.a
	)


# factor < 1 降飽和，> 1 提飽和。簡化版（不用 HSV 轉換，速度優先）。
static func _saturate(c: Color, factor: float) -> Color:
	var gray := c.r * 0.299 + c.g * 0.587 + c.b * 0.114
	return Color(
		clamp(lerp(gray, c.r, factor), 0.0, 1.0),
		clamp(lerp(gray, c.g, factor), 0.0, 1.0),
		clamp(lerp(gray, c.b, factor), 0.0, 1.0),
		c.a
	)
