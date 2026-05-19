# mapcore_py_square

`gamecore` 的方格地圖核心 —— Python 實作版本（4 鄰居 / JRPG 風）。

`mapcore_py`（六角版）的方格姊妹套件。同樣對齊未來 C++ 移植的 2D array 記憶體佈局，
不依賴 hash map 索引格子。座標範圍 `x ∈ [0, width)`、`y ∈ [0, height)`。

---

## 對應關係（與 `mapcore_py` 對照）

| 六角版 (`mapcore_py`) | 方格版 (`mapcore_py_square`) |
|---|---|
| `Hex(q, r)` axial 座標、隱含 `s = -q - r` | `Coord(x, y)` 直角座標、y 向下 |
| 6 個方向 (E/NE/NW/W/SW/SE) | 4 個方向 (E/N/W/S)，對立方向 = `(i+2)%4` |
| `distance` = cube distance | `distance` = Manhattan |
| `line` = 軸向插值 + hex_round | `line` = 4-connected supercover Bresenham |
| `ring` = 6 邊各 radius 步，總 `6r` 格 | `ring` = 菱形 4 邊各 radius 步，總 `4r` 格 |
| `spiral` 總數 `1 + 3N(N+1)` | `spiral` 總數 `1 + 2N(N+1)` |
| `TileMap._rows[r][q]` | `TileMap._rows[y][x]` |
| A* heuristic = hex distance × min cost | A* heuristic = Manhattan × min cost |

`TerrainDef` / `TerrainRegistry` / `TerrainType`（id 0–10）與六角版完全一致，
方便地形定義跨版本共用。內建地形：`OCEAN, COAST, PLAINS, GRASSLAND, DESERT, TUNDRA, SNOW, FOREST, HILL, MOUNTAIN, LAKE`。

---

## 目錄結構

```
mapcore_py_square/
├── mapcore/
│   ├── __init__.py
│   ├── grid.py            # Coord、4 方向、distance、line、ring、spiral
│   ├── terrain.py         # TerrainDef、TerrainRegistry、gen_default、DEFAULT_REGISTRY
│   ├── map.py             # TerrainType、Hilliness、Tile、TileMap
│   ├── pathfinding.py     # A* (4 鄰居)、path_cost
│   ├── rivers.py          # 邊存儲 (2 slots/tile)、RimWorld 風河流生成
│   ├── features.py        # WorldFeature、FeatureWorker_*、apply_features
│   └── generation/
│       ├── heightmap.py   # Phase 1：fBm + 板塊邊界山脊 + 形狀遮罩
│       ├── classify.py    # Phase 2：sea_level 切割 + COAST 擴張
│       ├── biome.py       # Phase 3：(elev, temp, moist) → 地形分類
│       ├── postprocess.py # Phase 4：清孤島、填小湖、重標 COAST
│       ├── depressions.py # Phase 4.5：Priority-Flood 內陸湖
│       ├── climate.py     # Phase 5：°C / mm / hilliness (RW curves)
│       └── pipeline.py    # generate_world() 一站式串接所有 phase
├── tests/
│   ├── test_grid.py
│   ├── test_map.py
│   ├── test_pathfinding.py
│   ├── test_generation.py  # heightmap / classify / biome / postprocess / depressions / climate / pipeline
│   ├── test_rivers.py      # 邊存儲、整合測試
│   └── test_features.py    # WorldFeatures、FeatureWorker、apply_features
└── examples/
    ├── visualize_map.py          # 地形上色、鄰居 / 可通行鄰居
    ├── visualize_pathfinding.py  # A* 路徑、即時編輯地形
    └── visualize_world.py        # 完整 pipeline：biome / heightmap / rainfall / temperature / hilliness + 河流 + features
```

## 河流邊存儲

`Tile.rivers` 是 16-bit 整數壓縮兩條邊的流量 (0~255 each)：
- slot 0 = E 邊（自己擁有）
- slot 1 = N 邊（自己擁有）
- W / S 兩條邊由鄰居持有（避免雙重儲存）

對應 hex 版的 3 slots (E/NE/NW 自己擁有，W/SW/SE 給鄰居)。方格版 4 方向少一半。
API 在 `mapcore.rivers`：`set_river_strength` / `get_river_strength` / `add_river_flow` /
`has_river_edge` / `iter_river_edges`。

---

## 執行

```bash
cd others/gamecore/mapcore_py_square
python -m unittest discover -s tests -v

# 互動視覺化（需要 pygame）
pip install pygame
python examples/visualize_map.py          # 基本地形 + 鄰居
python examples/visualize_pathfinding.py  # A* 尋路
python examples/visualize_world.py        # 完整 pipeline 世界生成
```

## 一站式生成

```python
from mapcore.generation import generate_world

result = generate_world(
    80, 50,
    seed=42,
    heightmap_shape="continents",     # None / pangaea / continents / island / archipelago / ring_sea / shattered_archipelago
    heightmap_ridge_weight=0.6,        # 0=純 fBm，1=純板塊山脊
    heightmap_num_plates=15,
    climate_rain_shadow_strength=0.3,
    lake_depressions=True,             # Priority-Flood 內陸湖
    river_min_seed_spacing=3,          # 河流合流密度（值越大、平行河越少）
)
# result.tile_map / result.heightmap / result.moisture
# result.temperature_celsius / result.rainfall_mm / result.tile_map.features
```

---

## 設計決策

- **`Coord` 不可雜湊**：`dataclass(eq=True)` 預設行為，禁止當 dict/set 鍵。對齊未來 C++ 版用 2D array 索引地圖的記憶體佈局。
- **y 向下、`_rows[y][x]` 儲存**：對應 screen-space 與 `index = y * width + x` 的線性佈局，方便繪製與 C++ 移植。
- **方向順序鎖死 `E, N, W, S`**：對立方向 = `(i+2)%4`；與六角版「對立 = `(i+3)%6`」結構一致。
- **`line` 用 supercover Bresenham**：每步只動一軸，相鄰格子保證 4-鄰接（不會出現對角跳格）。長度 = `Manhattan + 1`。
- **A* heuristic = Manhattan × MIN_PASSABLE_COST**：所有可通行地形 `move_cost ≥ 1.0`，因此 Manhattan 本身就是 admissible heuristic。

---

## 進度

- ✅ 座標系統：`Coord`、4 鄰居、Manhattan distance、supercover line、菱形 ring/spiral
- ✅ 地形登錄：`TerrainDef`、`TerrainRegistry`、`gen_default()`、`DEFAULT_REGISTRY`（id 0–10 與 hex 版一致）
- ✅ 地圖容器：`TerrainType`、`Hilliness`、`Tile`、`TileMap`（2D array、in_bounds、neighbors、passable_neighbors、fill）
- ✅ 尋路：`astar` (4 鄰居)、`path_cost`
- ✅ Phase 1 heightmap：fBm + 板塊山脊 + 6 種大陸形狀
- ✅ Phase 2 classify：sea_level 切割 + COAST 擴張
- ✅ Phase 3 biome：(elev, temp, moist) 決策樹
- ✅ Phase 4 postprocess：清孤島、填小湖、重標 COAST
- ✅ Phase 4.5 depressions：Priority-Flood 內陸湖
- ✅ Phase 5 climate：RW 風 °C / mm / hilliness curves
- ✅ Phase 6 rivers：邊存儲（2 slots/tile）+ RimWorld 風生成
- ✅ Phase 7 features：FeatureWorker 8 種 + apply_features
- ✅ Pipeline：`generate_world()` 串接所有 phase
- ✅ 視覺化範例：`visualize_map.py`、`visualize_pathfinding.py`、`visualize_world.py`
