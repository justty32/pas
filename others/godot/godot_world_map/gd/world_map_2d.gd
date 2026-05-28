class_name WorldMap2D extends Node2D

# 分層 TileMapLayer 版的 2D 世界地圖渲染器。
#
# CONCEPT.md 的方向一（多 TileMapLayer 堆疊）。三層：
#   ├── BaseLayer    (TileMapLayer) ← terrain 純色基底（與 mapcore demo MapRenderer 一致）
#   ├── HillLayer    (TileMapLayer) ← hilliness ≥ 2 才疊紋路 tile（半透明 tile 由 TileSet 給）
#   └── FeatureLayer (TileMapLayer) ← FOREST / HILL / MOUNTAIN icon（疏疏放）
#
# 河流走獨立 Node2D 用 _draw() 畫線（mapcore 提供 get_all_river_edges()）。
#
# 與 mapcore_godot demo 端 map_renderer.gd 的差異：demo 端只渲染基底層；
# 本檔把 CONCEPT 提到的三層全鋪好，並補河流 _draw。

signal map_ready(data: MapCoreMapData)

@export var base_layer: TileMapLayer
@export var hill_layer: TileMapLayer
@export var feature_layer: TileMapLayer
@export var river_overlay: Node2D  # 自繪 Node2D，由本腳本控制其 _draw

@export_group("TileSet 設定")
## 三層共用的 atlas source_id（簡單情境下都用 0）。
@export var source_id: int = 0
## 是否繪製起伏層（小地圖 / 簡化版可關掉）。
@export var enable_hill_layer: bool = true
## 是否繪製地物 icon。
@export var enable_feature_layer: bool = true

@export_group("河流")
## 過濾掉小於此 strength 的河流邊（對齊 mapcore rivers.hpp CREEK_THRESHOLD）。
@export var river_min_strength: int = 80
@export var river_color: Color = Color(0.20, 0.45, 0.70, 0.95)
## tile 像素邊長（與 TileSet 設定一致）。
@export var tile_px: int = 16


var map_data: MapCoreMapData


# 外部餵入 MapCoreMapData 後一鍵渲染。
func mount(data: MapCoreMapData) -> void:
	map_data = data
	_render_base(data)
	if enable_hill_layer:
		_render_hill(data)
	else:
		hill_layer.clear() if hill_layer else null
	if enable_feature_layer:
		_render_feature(data)
	else:
		feature_layer.clear() if feature_layer else null
	_request_river_redraw()
	map_ready.emit(data)


# ── 基底層 ────────────────────────────────────────────────────────────────

func _render_base(data: MapCoreMapData) -> void:
	if base_layer == null:
		push_error("WorldMap2D: base_layer 未綁定")
		return
	base_layer.clear()
	var w := data.get_width()
	var h := data.get_height()
	for y in h:
		for x in w:
			var terrain := data.get_terrain(x, y)
			base_layer.set_cell(Vector2i(x, y), source_id, TileAtlasLayout.base_atlas(terrain))


# ── 起伏層 ────────────────────────────────────────────────────────────────

func _render_hill(data: MapCoreMapData) -> void:
	if hill_layer == null:
		return
	hill_layer.clear()
	for y in data.get_height():
		for x in data.get_width():
			var hill := data.get_hilliness(x, y)
			var atlas: Variant = TileAtlasLayout.hilliness_atlas(hill)
			if atlas != null:
				hill_layer.set_cell(Vector2i(x, y), source_id, atlas as Vector2i)


# ── 地物層 ────────────────────────────────────────────────────────────────

func _render_feature(data: MapCoreMapData) -> void:
	if feature_layer == null:
		return
	feature_layer.clear()
	for y in data.get_height():
		for x in data.get_width():
			var terrain := data.get_terrain(x, y)
			var atlas: Variant = TileAtlasLayout.feature_atlas(terrain)
			if atlas != null:
				feature_layer.set_cell(Vector2i(x, y), source_id, atlas as Vector2i)


# ── 河流 ──────────────────────────────────────────────────────────────────

func _request_river_redraw() -> void:
	if river_overlay == null or map_data == null:
		return
	# 用 set_script 動態給 _draw 是 over-engineering；外部 river_overlay
	# 自己寫 _draw 呼叫 WorldMap2D.draw_rivers_into(self) 即可。
	river_overlay.queue_redraw()


# 由 river_overlay 的 _draw() 呼叫：draw_rivers_into(self) 把線畫到自己上。
# 寫成 static 是因為要從別的 Node 的 _draw 呼叫，又要拿 WorldMap2D 的設定。
func draw_rivers_into(canvas: CanvasItem) -> void:
	if map_data == null:
		return
	var edges := map_data.get_all_river_edges()
	for edge in edges:
		var strength: int = edge.get("strength", 0)
		if strength < river_min_strength:
			continue
		var pos: Vector2i = edge.get("pos")
		var dir: int = edge.get("dir", 0)
		var seg := _edge_pixel_segment(pos, dir)
		# 寬度依 strength 分級：CREEK(<80 篩掉) / STREAM(80~) / RIVER(160~) / MAJOR(240~)
		var width := 1.0
		if strength >= 240:
			width = 3.0
		elif strength >= 160:
			width = 2.0
		canvas.draw_line(seg[0], seg[1], river_color, width)


# 把 (cell, dir) 換成像素座標的兩個端點。
# mapcore: dir 0=E 1=N 2=W 3=S；河流邊在格子的對應邊上。
func _edge_pixel_segment(cell: Vector2i, dir: int) -> Array:
	var x0 := cell.x * tile_px
	var y0 := cell.y * tile_px
	var x1 := x0 + tile_px
	var y1 := y0 + tile_px
	match dir:
		0:  # E
			return [Vector2(x1, y0), Vector2(x1, y1)]
		1:  # N
			return [Vector2(x0, y0), Vector2(x1, y0)]
		2:  # W
			return [Vector2(x0, y0), Vector2(x0, y1)]
		3:  # S
			return [Vector2(x0, y1), Vector2(x1, y1)]
		_:
			return [Vector2(x0, y0), Vector2(x0, y0)]
