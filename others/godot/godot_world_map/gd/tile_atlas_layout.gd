class_name TileAtlasLayout extends RefCounted

# 三層 TileMapLayer 的 atlas 對映表，集中管理。
#
# 哲學：CONCEPT.md 提到「分層 = 基底地形 + 起伏 + 地物」。本檔把三層各自的
# atlas 座標收斂成 const Dictionary，世代美術換圖時只動這一支。
# TileSet 本身仍由設計師在 Godot 編輯器擺，這支只負責「程式怎麼挑格」。

# ── 基底層：terrain enum → atlas 座標 ─────────────────────────────────────
# 假設一個 TileSetAtlasSource (source_id=0)，第 0 行 11 格依序排對應 terrain 0~10。
# 這個排法與 mapcore_godot demo 端 map_renderer.gd 一致。
const BASE_LAYER := {
	0:  Vector2i(0,  0),   # OCEAN
	1:  Vector2i(1,  0),   # COAST
	2:  Vector2i(2,  0),   # PLAINS
	3:  Vector2i(3,  0),   # GRASSLAND
	4:  Vector2i(4,  0),   # DESERT
	5:  Vector2i(5,  0),   # TUNDRA
	6:  Vector2i(6,  0),   # SNOW
	7:  Vector2i(7,  0),   # FOREST
	8:  Vector2i(8,  0),   # HILL
	9:  Vector2i(9,  0),   # MOUNTAIN
	10: Vector2i(10, 0),   # LAKE
}

# ── 起伏層：hilliness 0~5 → atlas（第 1 行）──────────────────────────────
# mapcore Hilliness: 0=UNDEFINED, 1=FLAT, 2=ROLLING, 3=HILLS, 4=HIGHLANDS, 5=IMPASSABLE
# 0/1 不繪製（透明跳過）；2~5 用半透明紋路 tile 疊在基底之上。
# atlas 第 1 行四格依序：rolling / hills / highlands / impassable
const HILLINESS_LAYER := {
	2: Vector2i(0, 1),   # ROLLING
	3: Vector2i(1, 1),   # HILLS
	4: Vector2i(2, 1),   # HIGHLANDS
	5: Vector2i(3, 1),   # IMPASSABLE
}

# ── 地物層：terrain → atlas（第 2 行，森林/山脈/湖泊 icon）────────────────
# 只有有「特徵」需要疊 icon 的 terrain 才登記；其他 terrain 不放地物。
# 這層稀疏，留給城市 / feature 點等遊戲層自己疊。
const FEATURE_LAYER := {
	7: Vector2i(0, 2),   # FOREST icon
	8: Vector2i(1, 2),   # HILL icon
	9: Vector2i(2, 2),   # MOUNTAIN icon
}


# ── helpers ───────────────────────────────────────────────────────────────

static func base_atlas(terrain_id: int) -> Vector2i:
	return BASE_LAYER.get(terrain_id, Vector2i(0, 0))


# 回傳 null 表示「此格不放起伏 tile」（注意：Dictionary.has + get 寫法）。
static func hilliness_atlas(hilliness_lvl: int) -> Variant:
	if HILLINESS_LAYER.has(hilliness_lvl):
		return HILLINESS_LAYER[hilliness_lvl]
	return null


static func feature_atlas(terrain_id: int) -> Variant:
	if FEATURE_LAYER.has(terrain_id):
		return FEATURE_LAYER[terrain_id]
	return null
