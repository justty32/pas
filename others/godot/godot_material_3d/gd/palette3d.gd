class_name Palette3D extends RefCounted

# 集中管理顏色 palette。所有 material tint 都從這裡取色，
# 改一個 palette 就能換整套美術風格（鐵器時代→蒸汽朋克→賽博龐克）。

const WEAPON := {
	"iron":     Color(0.60, 0.60, 0.62),
	"steel":    Color(0.78, 0.82, 0.88),
	"silver":   Color(0.88, 0.90, 0.95),
	"gold":     Color(0.95, 0.78, 0.30),
	"bone":     Color(0.92, 0.88, 0.72),
	"crystal":  Color(0.65, 0.35, 0.95),
	"obsidian": Color(0.12, 0.10, 0.18),
	"jade":     Color(0.30, 0.70, 0.50),
}

const RARITY := {
	"common":    Color(0.85, 0.85, 0.85),
	"uncommon":  Color(0.40, 0.85, 0.40),
	"rare":      Color(0.40, 0.60, 1.00),
	"epic":      Color(0.80, 0.40, 1.00),
	"legendary": Color(1.00, 0.65, 0.20),
}

const BIOME := {
	"grass":  Color(0.42, 0.65, 0.30),
	"desert": Color(0.86, 0.75, 0.45),
	"snow":   Color(0.92, 0.94, 0.98),
	"tundra": Color(0.65, 0.70, 0.65),
	"swamp":  Color(0.35, 0.40, 0.28),
	"rock":   Color(0.50, 0.48, 0.45),
	"water":  Color(0.20, 0.45, 0.70),
}

const SKIN := {
	"human_light":  Color(0.95, 0.78, 0.65),
	"human_tan":    Color(0.78, 0.58, 0.42),
	"human_dark":   Color(0.45, 0.30, 0.22),
	"goblin":       Color(0.45, 0.62, 0.30),
	"orc":          Color(0.40, 0.55, 0.35),
	"undead":       Color(0.72, 0.78, 0.72),
}


static func get_color(category: Dictionary, key: String, fallback: Color = Color.MAGENTA) -> Color:
	return category.get(key, fallback)


static func mix_with_rarity(base: Color, rarity_key: String, strength: float = 0.3) -> Color:
	var rarity_color: Color = RARITY.get(rarity_key, Color.WHITE)
	return base.lerp(rarity_color, strength)
