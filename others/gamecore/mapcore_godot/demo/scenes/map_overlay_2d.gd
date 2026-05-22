## MapOverlay2D：畫在世界地圖之上的互動視覺層。
##
## 與地圖同一座標空間（cell_px 像素/格、原點對齊），由 WorldMap2D 推入狀態後
## 呼叫 queue_redraw() 重畫。本身不處理輸入，只負責把狀態畫出來。
##
## 疊加內容（由下而上）：feature 邊界輪廓 → 路徑線/起終點 → 選取框 → 懸停框 → feature 標籤。
class_name MapOverlay2D
extends Node2D

var cell_px: int = 8
var map_data: MapCoreMapData

# 懸停 / 選取（Vector2i(-1, -1) 代表「無」）
var hover_cell: Vector2i = Vector2i(-1, -1)
var selected_cell: Vector2i = Vector2i(-1, -1)

# feature 高亮：被選 feature 的邊界線段（成對端點，像素座標；給 draw_multiline 用）
var feature_outline: PackedVector2Array = PackedVector2Array()

# 尋路：起點 / 終點 / 路徑（Array[Vector2i]，含端點）
var path_start: Vector2i = Vector2i(-1, -1)
var path_goal: Vector2i = Vector2i(-1, -1)
var path: Array = []

# 全部 feature 標籤（按 L 切換顯示）：[{ name: String, pos: Vector2i(cell) }]
var labels: Array = []
var show_labels: bool = false

const COL_FEATURE := Color(1.0, 0.6, 0.1, 0.95)
const COL_PATH    := Color(1.0, 1.0, 1.0, 0.95)
const COL_START   := Color(0.2, 1.0, 0.3, 1.0)
const COL_GOAL    := Color(1.0, 0.25, 0.25, 1.0)
const COL_SELECT  := Color(0.1, 1.0, 1.0, 1.0)
const COL_HOVER   := Color(1.0, 1.0, 0.2, 0.85)


func _draw() -> void:
	var cp := float(cell_px)

	# ── feature 高亮：只描邊界輪廓（再大的大陸也只是一圈線，不會整塊填滿）──────
	if feature_outline.size() >= 2:
		draw_multiline(feature_outline, COL_FEATURE, maxf(2.0, cp * 0.3))

	# ── 路徑：連接各格中心的折線 ──────────────────────────────────────────────
	if path.size() >= 2:
		var pts := PackedVector2Array()
		for c in path:
			pts.append(Vector2((c.x + 0.5) * cp, (c.y + 0.5) * cp))
		draw_polyline(pts, COL_PATH, maxf(2.0, cp * 0.25), true)
	if path_start.x >= 0:
		draw_circle(Vector2((path_start.x + 0.5) * cp, (path_start.y + 0.5) * cp), cp * 0.4, COL_START)
	if path_goal.x >= 0:
		draw_circle(Vector2((path_goal.x + 0.5) * cp, (path_goal.y + 0.5) * cp), cp * 0.4, COL_GOAL)

	# ── 選取框（粗）──────────────────────────────────────────────────────────
	if selected_cell.x >= 0:
		draw_rect(Rect2(selected_cell.x * cp, selected_cell.y * cp, cp, cp), COL_SELECT, false, 2.0)

	# ── 懸停框（細；與選取格重疊時不重畫）────────────────────────────────────
	if hover_cell.x >= 0 and hover_cell != selected_cell:
		draw_rect(Rect2(hover_cell.x * cp, hover_cell.y * cp, cp, cp), COL_HOVER, false, 1.0)

	# ── feature 標籤（畫於各區域中心，帶深色陰影增加可讀性）──────────────────
	if show_labels:
		var font := ThemeDB.fallback_font
		var fs := maxi(10, cell_px)
		for label in labels:
			var ltext: String = label["name"]
			var cell: Vector2i = label["pos"]
			var tw := font.get_string_size(ltext, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
			var base := Vector2(cell.x * cp - tw * 0.5, cell.y * cp)
			draw_string(font, base + Vector2(1, 1), ltext, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0, 0, 0, 0.8))
			draw_string(font, base, ltext, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color.WHITE)
