# mapcore_py

`gamecore` 的六角地圖核心 —— **Python 實作版本**。

作為未來遊戲的地圖基底，提供六角座標、地形容器、尋路、地圖生成等基礎能力。先用 Python 把資料結構與演算法跑起來，之後若效能不足再考慮換語言或寫 C 擴充。

---

## 設計來源

本實作的設計參考三個既有專案：Unciv（座標 / 地圖容器 / A*）、Wesnoth（A* 細節）、
RimWorld（河流生成、Hilliness、Feature 命名系統）。

### Unciv（Kotlin → C++ 教學版）
- `analysis/unciv/tutorial/cpp_hex_library.md` — 軸向座標、環形擴張、直線遍歷
- `analysis/unciv/tutorial/cpp_hex_map_structure.md` — `TileMap` 雙層存儲、Tile 結構
- `analysis/unciv/tutorial/cpp_hex_shapes_advanced.md` — 進階形狀運算
- `analysis/unciv/tutorial/cpp_map_shapes.md` — 矩形 / 環形 / 六角形地圖
- `analysis/unciv/details/map_data_structure.md` — `HexCoord`、`InlineHexCoord` 效能優化、距離公式
- `analysis/unciv/details/unit_pathfinding_logic.md` — 單位尋路規則
- `analysis/unciv/details/map_generation_pipeline.md` / `map_generation.md` — 地圖生成管線

原始碼路徑：`projects/Unciv-4.20.6/`

### Wesnoth（C++ 原生實作）
- `analysis/wesnoth/details/tech_encyclopedia_vol1_map_base.md` — 地圖基礎結構
- `analysis/wesnoth/details/tech_encyclopedia_vol2_map_logic.md` — 地圖邏輯
- `analysis/wesnoth/details/tech_encyclopedia_vol5_pathfinding.md` — 尋路核心
- `analysis/wesnoth/details/astar_pathfinding_geometry.md` — A* 幾何細節
- `analysis/wesnoth/details/encyclopedia_vol4_pathfinding.md` — 尋路百科
- `analysis/wesnoth/details/map_generation_algorithms.md` / `map_gen_function_anatomy.md` — 地圖生成演算法
- `analysis/wesnoth/details/encyclopedia_vol1_heightmap.md` / `encyclopedia_vol2_hydrology.md` — 高程與水文

原始碼路徑：`projects/wesnoth-master/`

### RimWorld（C# Assembly-CSharp）
- `projects/rimworld/RimWorld.Planet/WorldGenStep_Rivers.cs` — coastal-seed Dijkstra 反向樹 + flow accumulation + 分主流/支流
- `projects/rimworld/RimWorld.Planet/WorldGenStep_Terrain.cs` — Hilliness 5 級 + 緯度溫度 / 高程降水 curves
- `projects/rimworld/RimWorld.Planet/WorldFeature.cs` + `WorldGenStep_Features.cs` + `FeatureWorker*.cs` — 命名大區域系統
- `analysis/rimworld/` — 二手分析，僅做索引；實作細節以原始碼為準

原始碼路徑：`projects/rimworld/`

---

## 設計決策

- **Hex 不可雜湊 (`__hash__ = None`)**：地圖儲存走 **2D array** 路線，不依賴 hash map / set。
  Python 版這樣設計是為了與未來 C++ 移植的記憶體佈局完全對齊；想用座標查格子請走 `Map.get(q, r)` 之類的索引 API（待實作）。
- **Axial 座標 + 隱含 s 軸**：`s = -q - r`，遇到要做「最大誤差軸由其他兩軸回推」的場景才會浮上來（見 `hex_round`）。
- **方向順序與 Unciv 教學一致**：`DIRECTIONS[0..5]` 對應 `analysis/unciv/tutorial/cpp_hex_library.md` 第 31 行。

---

## 目錄結構

```
mapcore_py/
├── mapcore/                       # 核心模組
│   ├── __init__.py
│   ├── hex.py                     # Hex 座標、距離、環、螺旋、直線
│   ├── map.py                     # TerrainType、Tile、TileMap (2D array)
│   ├── pathfinding.py             # A* (g_score / came_from / closed 全 2D array; 支援河流穿越成本)
│   ├── rivers.py                  # 河流拓撲 + 流量 + 生成 (RimWorld 風 coastal Dijkstra)
│   ├── features.py                # WorldFeature 命名大區域 + FeatureWorker（對齊 RimWorld）
│   └── generation/                # 地圖生成管線
│       ├── __init__.py
│       ├── heightmap.py           # Phase 1: value noise + smoothstep + bilinear
│       ├── classify.py            # Phase 2: heightmap → TileMap (OCEAN/COAST/PLAINS); expand_coast
│       ├── biome.py               # Phase 3: 緯度+高程+濕度 → 生物群系
│       ├── postprocess.py         # Phase 4: 連通性、清小島、填小湖、重標 COAST
│       ├── climate.py             # Phase 5: °C 溫度 / mm 降雨 / Hilliness 5 級（RimWorld curves）
│       └── pipeline.py            # generate_world：Phase 1→6 一站式（含 features）
├── tests/                         # 單元測試 (stdlib unittest)
│   ├── test_hex.py
│   ├── test_map.py
│   ├── test_pathfinding.py
│   ├── test_generation.py
│   ├── test_classify.py
│   ├── test_biome.py
│   ├── test_postprocess.py
│   ├── test_rivers.py
│   ├── test_climate.py
│   ├── test_features.py
│   └── test_pipeline_integration.py
└── examples/                      # 視覺化 / 互動範例
    ├── visualize_hex.py           # 鄰居 / 環 / 螺旋 / 直線
    ├── visualize_map.py           # 地形上色、鄰居 / 可通行鄰居
    ├── visualize_pathfinding.py   # A* 路徑、即時編輯地形
    ├── visualize_heightmap.py     # 高程 noise (Phase 1)
    ├── visualize_classify.py      # 海平面切割 (Phase 2)
    └── visualize_biome.py         # 生物群系 + 4 種視圖 (Phase 3)
```

---

## 執行

```bash
# 測試
cd others/gamecore/mapcore_py
python -m unittest discover -s tests -v

# 互動視覺化範例 (需要 pygame)
pip install pygame
python examples/visualize_hex.py            # 鄰居 / 環 / 螺旋 / 直線
python examples/visualize_map.py            # 地形上色、鄰居 / 可通行鄰居
python examples/visualize_pathfinding.py    # A* 路徑、即時編輯地形
python examples/visualize_heightmap.py      # 高程 noise (Phase 1)
python examples/visualize_classify.py       # 海平面切割 (Phase 2)
python examples/visualize_biome.py          # 生物群系 (Phase 3) + heightmap/moisture/temperature 視圖
```

- `visualize_hex.py`：左鍵設中心、右鍵設直線終點、+/- 或滾輪調半徑、1-4 切換模式。
- `visualize_map.py`：左鍵循環切換地形、右鍵設回 PLAINS、F 整片海洋、R 整片平原、Tab 切換鄰居顯示模式。
- `visualize_pathfinding.py`：左鍵設起點、右鍵設終點、1-7 按鍵在游標位置直接放地形、Shift+左鍵 或 中鍵循環地形、F/R 整片填、C 清除起終點。
- `visualize_heightmap.py`：Space 換 seed、+/- 調 octaves、[/] 調 persistence、,/. 調 base_frequency、G 切換漸層/灰階。
- `visualize_classify.py`：同 heightmap 那組 noise 控制，加上 ↑/↓ 調 sea_level、`;`/`'` 調 coast_depth、H 切換 terrain / heightmap 視圖。HUD 顯示海/海岸/陸地比例。
- `visualize_biome.py`：同上所有控制 + 1~6 切換視圖（terrain / heightmap / moisture / temperature / hilliness / features）+ P 切後處理、9/0 調 island_min_size、O/L 調 lake_max_size、R 切換河流顯示。features 視圖會在每個命名區域重心畫名稱。HUD 顯示島嶼數 / 最大島嶼 / features 總數 / 各地形比例。
- **相機平移**：`visualize_heightmap`、`visualize_classify`、`visualize_biome` 三個大地圖 demo 支援方向鍵 ←→↑↓ 平移視角（持續按住），Home 歸位。`sea_level` 改用 PgUp/PgDn。

---

## 進度

- ✅ **Hex 座標系統**：軸向 (axial)、`s` 推導、鄰居、距離、方向、環形 / 螺旋 / 直線遍歷
- ✅ **地圖容器**：`TerrainType`、`Tile`、`TileMap`（2D array、平行四邊形範圍、邊界檢查、鄰居 / 可通行鄰居、整片填充）
- ✅ **尋路**：`astar`、`path_cost`；`g_score` / `came_from` / `closed` 全 2D array、啟發式 = `hex distance × min_passable_cost`；`river_crossing_cost` 參數可加跨河成本
- ✅ **河流 + 流量**：`Tile.rivers` 是 3 × 8-bit 流量打包（每邊 0~255，多源匯入用 `add_river_flow` 累加）。生成改對齊 `projects/rimworld/.../WorldGenStep_Rivers.cs`（RimWorld 風）：
  - 找 coastal water tiles 當 seeds（鄰接陸地的海/海岸）
  - 反向 Dijkstra 建下游樹：`cost = ElevationChangeCost(elev_st − elev_ed) × factor`，
    `factor = 1` 若 ed 的最低鄰居就是 st，否則 2；非起點水不再擴張
  - DFS 累加 flow = rainfall − evaporation（蒸發用 RW 的 sqrt(flow) × evap_const(temp) × 250 公式）
  - 從 seed 走樹畫 edge：主流走最大 flow child（≥ `degrade_threshold` 才繼續），
    其餘 children 中 flow ≥ `branch_flow_threshold` 者按 `branch_chance` 機率分支
  - flow 經 `flow_strength_scale` 換成 0~255 的邊強度；A* 跨河成本 = `river_crossing_cost × 流量`
- 🚧 **地圖生成**（對齊 `plans/002-world-structure.md` 的管線；河流與 features 改參考 RimWorld）
  - ✅ Phase 1：高程 noise (`generate_heightmap`，多層 value noise + smoothstep + bilinear)
  - ✅ Phase 2：海平面切割 (`heightmap_to_tilemap`，閾值 → OCEAN / COAST / PLAINS；可調 `coast_depth` 控制淺海帶寬度)
  - ✅ Phase 3：生物群系 (`apply_biomes`：MOUNTAIN/HILL 由高程主導；其餘看溫度（緯度+高程）與濕度（獨立 noise）)；一站式 `generate_world` 串接全部
  - ✅ Phase 4：後處理（`find_components`/`remove_small_islands`/`remove_small_lakes`/`relabel_coast`/`post_process`）；`generate_world` 預設啟用
  - ✅ Phase 5：氣候 (`apply_climate`，對齊 `WorldGenStep_Terrain.cs`)：°C 溫度（`AvgTempByLatitudeCurve` + 高程降溫）、mm 降雨（noise × latitude curve × 高程乾燥）、`Hilliness` 5 級 (Flat/SmallHills/LargeHills/Mountainous/Impassable)
  - ✅ Phase 6：命名大區域 (`apply_features`，對齊 `WorldGenStep_Features.cs`)：FeatureWorker 抽象 + 內建 Ocean/MountainRange/BiomeRegion/Island；`tile_map.features` 是 WorldFeatures 容器，每個 Tile 帶 `feature_id` 反查

---

## 與 gamecore 其他部分的關係

- `plans/`：設計藍圖（世界三層架構等）。本模組對應「世界層」的格子地圖基礎。
- `specs/`：規格定稿區。當本模組的某個子系統穩定後，介面規格將移至此處。
- 原 `core/`（C++ GDExtension）：保留為未來效能瓶頸時的替代選項。
