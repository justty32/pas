# GDExtension：2D 俯視世界地圖場景

## 目標

從 C++ mapcore 資料直接生成 `Image`，在獨立的 2D 場景呈現整張島嶼世界地圖。
支援滑鼠中鍵 Pan、滾輪 Zoom、左鍵點選格子查詢地形資訊。

---

## 核心架構

```
MapCoreGenerator（已有）
    → generate_async() → emit generation_completed(data)
MapCoreWorldMap2DRenderer（新增 C++ class）
    → generate_terrain_image(data, cell_px) → Image
    → draw_rivers(image, data, cell_px)     → 就地修改
WorldMap2D（新增 GDScript）
    → 接收 signal → ImageTexture → Sprite2D
    → Camera2D pan/zoom + 點擊查詢
```

---

## 新增 C++ 類別：`MapCoreWorldMap2DRenderer`

### 原始碼位置

- Header: `mapcore_godot/src/world_map_2d_renderer.h`
- Impl:   `mapcore_godot/src/world_map_2d_renderer.cpp`
- 已在:   `mapcore_godot/src/register_types.cpp` 中 `GDREGISTER_CLASS`

### 類別設計

繼承 `RefCounted`（直接 `.new()` 使用，不掛場景樹）。

```gdscript
var renderer := MapCoreWorldMap2DRenderer.new()
var img := renderer.generate_terrain_image(data, 8)   # 每格 8px
renderer.draw_rivers(img, data, 8)                    # 就地疊加河流
sprite.texture = ImageTexture.create_from_image(img)
```

### `generate_terrain_image(data, cell_px=8) -> Image`

回傳 `FORMAT_RGB8` Image，尺寸 = `(w*cell_px) × (h*cell_px)`。

每格用 `Image::fill_rect()` 填滿對應地形顏色：

| 地形常數 | 顏色（linear RGB） |
|---------|------------------|
| OCEAN     | (0.10, 0.25, 0.55) 深藍 |
| COAST     | (0.25, 0.50, 0.75) 中藍 |
| PLAINS    | (0.70, 0.80, 0.40) 淺黃綠 |
| GRASSLAND | (0.35, 0.65, 0.30) 草綠 |
| DESERT    | (0.85, 0.78, 0.45) 土黃 |
| TUNDRA    | (0.65, 0.70, 0.75) 灰藍 |
| SNOW      | (0.90, 0.93, 0.97) 近白 |
| FOREST    | (0.18, 0.42, 0.18) 深綠 |
| HILL      | (0.60, 0.55, 0.40) 棕 |
| MOUNTAIN  | (0.50, 0.45, 0.40) 深棕灰 |
| LAKE      | (0.20, 0.45, 0.70) 湖藍 |

### `draw_rivers(image, data, cell_px=8)`

呼叫 `data.get_all_river_edges()` 取得所有河流邊，
每條邊依方向在格子邊界畫 `thick`（= `clamp(cell_px/4, 1, 3)`）像素的藍色線段：

```
dir=0 (East)  → 右邊界：Rect2i(x+cp-thick, y, thick, cp)
dir=1 (North) → 上邊界：Rect2i(x, y, cp, thick)
dir=2 (West)  → 左邊界：Rect2i(x, y, thick, cp)
dir=3 (South) → 下邊界：Rect2i(x, y+cp-thick, cp, thick)
```

---

## GDScript 場景：`WorldMap2D`

### 原始碼位置

`mapcore_godot/demo/scenes/world_map_2d.gd`

### 場景節點結構

```
WorldMap2D (Node2D)          ← world_map_2d.gd
├── MapCoreGenerator
├── Camera2D
├── Sprite2D  (centered=false, position=(0,0))
└── CanvasLayer (layer=1)
    └── InfoPanel (Label)    ← 左上角地形資訊
```

> `Sprite2D.centered = false`：讓像素座標 (px, py) 直接對應世界座標 (px, py)，
> 簡化滑鼠位置 → 格子座標的轉換。

### Inspector 設定

| 屬性 | 說明 |
|------|------|
| `generator` | 場景中的 MapCoreGenerator 節點 |
| `cell_px`   | 每格像素大小（預設 8，建議 4~16）|

### 控制方式

| 操作 | 效果 |
|------|------|
| 中鍵拖曳 | Pan（移動鏡頭） |
| 滾輪 | Zoom（0.25x ~ 16x） |
| 左鍵點擊地圖 | 顯示該格地形/坡度/溫度/降雨 |

### 點擊查詢邏輯

```gdscript
# Sprite2D centered=false + 位於原點 → 世界座標 = 圖片像素座標
var world := get_global_mouse_position()
var cx := int(world.x) / cell_px
var cy := int(world.y) / cell_px
var t    := _map_data.get_terrain(cx, cy)
var temp := _map_data.get_temperature(cx, cy)
var rain := _map_data.get_rainfall(cx, cy)
```

### 鏡頭初始置中

```gdscript
_camera.position = Vector2(data.get_width(), data.get_height()) * cell_px * 0.5
```

---

## 完整使用範例

```gdscript
# world_map_2d.gd（掛在 WorldMap2D Node2D 根節點）
func _ready() -> void:
    _sprite.centered = false
    generator.generation_completed.connect(_on_generated)
    generator.generate_async()

func _on_generated(data: MapCoreMapData) -> void:
    _map_data = data
    var renderer := MapCoreWorldMap2DRenderer.new()
    var img      := renderer.generate_terrain_image(data, cell_px)
    renderer.draw_rivers(img, data, cell_px)
    _sprite.texture = ImageTexture.create_from_image(img)
    _camera.position = Vector2(data.get_width(), data.get_height()) * cell_px * 0.5
```

---

## 與 3D 地圖的關係

| | 2D 世界地圖（此文件）| 3D Low Poly（gdextension_3d_world_map.md）|
|--|---|---|
| 目的 | 全局俯視、資訊查詢 | 遊戲主場景、美術視覺 |
| 渲染單元 | `Image` pixel | `ArrayMesh` 頂點 |
| 顏色 | 2D 清晰色盤 | 3D vertex color（含 jitter） |
| 河流 | Image 上的像素線 | 待實作（3D curve mesh）|
| 互動 | pan/zoom/查詢 | 鏡頭旋轉/縮放/選取 |

---

*記錄時間：2026-05-22*
