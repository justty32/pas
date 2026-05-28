class_name MinimapPalette extends RefCounted

# Minimap 用色票。與 godot_world_map_3d/ClimatePalette 的 BASE_BIOME 故意不同：
# minimap 視覺要求是「在小尺寸下高對比、易辨識」，與場景渲染色獨立調整。
# CONCEPT 強調「minimap 顏色可以和實際 3D 場景完全獨立設計（更清晰）」。

const TERRAIN := {
	0:  Color(0.10, 0.30, 0.60),  # OCEAN     深藍
	1:  Color(0.30, 0.60, 0.80),  # COAST     淺藍
	2:  Color(0.75, 0.78, 0.40),  # PLAINS    淺黃綠
	3:  Color(0.30, 0.65, 0.25),  # GRASSLAND 草綠
	4:  Color(0.88, 0.78, 0.40),  # DESERT    沙黃
	5:  Color(0.55, 0.60, 0.65),  # TUNDRA    冷灰
	6:  Color(0.92, 0.95, 0.98),  # SNOW      雪白
	7:  Color(0.15, 0.40, 0.15),  # FOREST    深綠
	8:  Color(0.60, 0.50, 0.35),  # HILL      棕黃
	9:  Color(0.50, 0.45, 0.40),  # MOUNTAIN  暗棕
	10: Color(0.20, 0.45, 0.70),  # LAKE      湖藍
}

# 陣營色（與 mapcore demo MaterialLibrary.FACTION_COLORS 對齊但獨立常數）
const FACTION := {
	"player":  Color(0.20, 0.60, 1.00),
	"enemy":   Color(1.00, 0.25, 0.20),
	"neutral": Color(0.80, 0.80, 0.80),
	"ally":    Color(0.25, 0.85, 0.45),
}


static func terrain(terrain_id: int) -> Color:
	return TERRAIN.get(terrain_id, Color.MAGENTA)


static func faction(name: String) -> Color:
	return FACTION.get(name, Color.WHITE)
