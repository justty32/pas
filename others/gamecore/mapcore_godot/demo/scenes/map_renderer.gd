## MapRenderer：從 MapCoreGenerator 取得生成結果並填充 TileMapLayer。
##
## 使用方式：
##   1. 將此腳本掛在場景中的某個 Node 上
##   2. 在 Inspector 設定 generator（MapCoreGenerator 節點）
##      和 terrain_layer（TileMapLayer 節點）
##   3. 確保 TileMapLayer 使用的 TileSet 包含一個 TileSetAtlasSource (source_id=0)，
##      atlas 第 0 行第 0~10 格依序對應 11 種地形（暫用純色測試 tile）
class_name MapRenderer
extends Node

@export var generator: MapCoreGenerator
@export var terrain_layer: TileMapLayer
@export var source_id: int = 0  ## TileSet 中 TileSetAtlasSource 的 ID

## TerrainType → atlas 座標（對應 TileSet atlas 第 0 行第 N 格）
## 之後換 texture 只需調整 TileSet 資源，這裡的映射不需要改動
const TERRAIN_ATLAS: Dictionary = {
	MapCoreMapData.TERRAIN_OCEAN:     Vector2i(0,  0),
	MapCoreMapData.TERRAIN_COAST:     Vector2i(1,  0),
	MapCoreMapData.TERRAIN_PLAINS:    Vector2i(2,  0),
	MapCoreMapData.TERRAIN_GRASSLAND: Vector2i(3,  0),
	MapCoreMapData.TERRAIN_DESERT:    Vector2i(4,  0),
	MapCoreMapData.TERRAIN_TUNDRA:    Vector2i(5,  0),
	MapCoreMapData.TERRAIN_SNOW:      Vector2i(6,  0),
	MapCoreMapData.TERRAIN_FOREST:    Vector2i(7,  0),
	MapCoreMapData.TERRAIN_HILL:      Vector2i(8,  0),
	MapCoreMapData.TERRAIN_MOUNTAIN:  Vector2i(9,  0),
	MapCoreMapData.TERRAIN_LAKE:      Vector2i(10, 0),
}

func _ready() -> void:
	if not generator or not terrain_layer:
		push_error("MapRenderer: generator 或 terrain_layer 未設定")
		return
	generator.generation_completed.connect(_on_generated)
	generator.generation_failed.connect(_on_failed)
	generator.generate_async()

# ── 回呼 ─────────────────────────────────────────────────────────────────────

func _on_generated(data: MapCoreMapData) -> void:
	_render_terrain(data)
	_render_rivers(data)
	print("MapRenderer: 地圖渲染完成，seed=", data.get_seed_used())

func _on_failed(message: String) -> void:
	push_error("MapRenderer: 地圖生成失敗 — ", message)

# ── 地形渲染 ──────────────────────────────────────────────────────────────────

func _render_terrain(data: MapCoreMapData) -> void:
	terrain_layer.clear()
	var arr: PackedInt32Array = data.get_terrain_array()
	var w: int = data.get_width()
	for i in arr.size():
		var x := i % w
		var y := i / w
		var atlas: Vector2i = TERRAIN_ATLAS.get(arr[i], Vector2i(0, 0))
		terrain_layer.set_cell(Vector2i(x, y), source_id, atlas)

# ── 河流渲染（佔位，需要自訂 Line2D 或 _draw 覆蓋層）───────────────────────

func _render_rivers(data: MapCoreMapData) -> void:
	## TODO: 取得 data.get_all_river_edges() 後，
	## 在 terrain_layer 上方的 Node2D 用 Line2D 或 draw_line() 繪製河流邊。
	## 每條邊的兩端 corner 索引由 mapcore EDGE_CORNERS 定義：
	##   dir=0(E): corners (SE=3, NE=0)  → tile 右邊緣
	##   dir=1(N): corners (NE=0, NW=1)  → tile 上邊緣
	pass
