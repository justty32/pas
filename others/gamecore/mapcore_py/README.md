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
- `projects/rimworld/Verse/TerrainDef.cs` + `RimWorld/TerrainPatchMaker.cs` — 平坦 TerrainDef 設計、tag 系統、Overlay 機制
- `analysis/rimworld/` — 二手分析，僅做索引；實作細節以原始碼為準

原始碼路徑：`projects/rimworld/`

---

## 設計決策

- **Hex 不可雜湊 (`__hash__ = None`)**：地圖儲存走 **2D array** 路線，不依賴 hash map / set。
  Python 版這樣設計是為了與未來 C++ 移植的記憶體佈局完全對齊；想用座標查格子請走 `Map.get(q, r)` 之類的索引 API（待實作）。
- **Axial 座標 + 隱含 s 軸**：`s = -q - r`，遇到要做「最大誤差軸由其他兩軸回推」的場景才會浮上來（見 `hex_round`）。
- **方向順序與 Unciv 教學一致**：`DIRECTIONS[0..5]` 對應 `analysis/unciv/tutorial/cpp_hex_library.md` 第 31 行。
- **TerrainDef 平坦設計（對齊 RimWorld）**：`TerrainDef` 是純資料 dataclass，沒有 class 繼承；地形分類靠 **tag 系統**（`frozenset[str]`）而非型別階層。水域判斷從 `terrain <= COAST` 改為 `registry.is_water(terrain_id)`，不再依賴 IntEnum 數值排序的隱式假設。
- **`Tile.terrain` 儲存 int id**：對應 C++ 側 `uint16_t`；內建地形 id 0–9 與 `TerrainType` IntEnum 數值相同（向下相容），使用者自定義地形從 id 100 起分配。所有地形屬性查詢透過 `TerrainRegistry` 而非 hardcode dict。
- **`generate_world()` 回傳 `WorldGenResult`**：對應 C++ 側的 `WorldData` struct，所有中間產物（heightmap / moisture / temperature / rainfall / extra\_noise）集中在同一個物件，方便 overlay phase 直接接收。

---

## 目錄結構

```
mapcore_py/
├── mapcore/                       # 核心模組
│   ├── __init__.py
│   ├── hex.py                     # Hex 座標、距離、環、螺旋、直線
│   ├── terrain.py                 # TerrainDef、TerrainRegistry、gen_default()、DEFAULT_REGISTRY
│   ├── map.py                     # TerrainType (id 常數)、Tile (terrain: int)、TileMap (2D array)
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
│       ├── pipeline.py            # generate_world：Phase 1→6 一站式；回傳 WorldGenResult
│       └── overlay.py             # Phase 7: TerrainPatch + apply_terrain_patches()（衍生地形 overlay）
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
- ✅ **地形登錄系統**：`TerrainDef`（平坦資料類別，對齊 RimWorld）、`TerrainRegistry`（id / name 雙索引）、`gen_default()`（建立含內建 10 種地形的登錄表）；`Tile.terrain` 儲存 `int` id，水域判斷走 `registry.is_water()`
- ✅ **地圖容器**：`TerrainType`（id 常數）、`Tile`、`TileMap`（2D array、平行四邊形範圍、邊界檢查、鄰居 / 可通行鄰居、整片填充）
- ✅ **尋路**：`astar`、`path_cost`；`g_score` / `came_from` / `closed` 全 2D array、啟發式 = `hex distance × min_passable_cost`；`river_crossing_cost` 參數可加跨河成本
- ✅ **河流 + 流量**：`Tile.rivers` 是 3 × 8-bit 流量打包（每邊 0~255，多源匯入用 `add_river_flow` 累加）。生成對齊 `projects/rimworld/.../WorldGenStep_Rivers.cs`（RimWorld 風）：
  - 找 coastal water tiles 當 seeds（鄰接陸地的海/海岸）
  - 反向 Dijkstra 建下游樹：`cost = ElevationChangeCost(elev_st − elev_ed) × factor`，
    `factor = 1` 若 ed 的最低鄰居就是 st，否則 2；非起點水不再擴張
  - DFS 累加 flow = rainfall − evaporation（蒸發用 RW 的 sqrt(flow) × evap_const(temp) × 250 公式）
  - 從 seed 走樹畫 edge：主流走最大 flow child（≥ `degrade_threshold` 才繼續），
    其餘 children 中 flow ≥ `branch_flow_threshold` 者按 `branch_chance` 機率分支
  - flow 經 `flow_strength_scale` 換成 0~255 的邊強度；A* 跨河成本 = `river_crossing_cost × 流量`
- ✅ **地圖生成**（對齊 `plans/002-world-structure.md` 的管線；河流與 features 改參考 RimWorld）
  - ✅ Phase 1：高程 noise (`generate_heightmap`，多層 value noise + smoothstep + bilinear)
  - ✅ Phase 2：海平面切割 (`heightmap_to_tilemap`，閾值 → OCEAN / COAST / PLAINS；可調 `coast_depth` 控制淺海帶寬度)
  - ✅ Phase 3：生物群系 (`apply_biomes`：MOUNTAIN/HILL 由高程主導；其餘看溫度（緯度+高程）與濕度（獨立 noise）)
  - ✅ Phase 4：後處理（`find_components`/`remove_small_islands`/`remove_small_lakes`/`relabel_coast`/`post_process`）；`generate_world` 預設啟用
  - ✅ Phase 5：氣候 (`apply_climate`，對齊 `WorldGenStep_Terrain.cs`)：°C 溫度（`AvgTempByLatitudeCurve` + 高程降溫）、mm 降雨（noise × latitude curve × 高程乾燥）、`Hilliness` 5 級 (Flat/SmallHills/LargeHills/Mountainous/Impassable)
  - ✅ Phase 6：命名大區域 (`apply_features`，對齊 `WorldGenStep_Features.cs`)：FeatureWorker 抽象 + 內建 Lake/Coast/Ocean/MountainRange/Icecap(極區 SNOW)/BiomeRegion×5/Island/Continent；`tile_map.features` 是 WorldFeatures 容器，每個 Tile 帶 `feature_id` 反查（Continent 例外：純標籤層，與其他 feature 共存）
  - ✅ Phase 7：衍生地形 overlay (`apply_terrain_patches`，對齊 RimWorld `TerrainPatchMaker`)：`TerrainPatch` 定義生成條件（noise 閾值、氣候範圍、鄰接地形、hilliness、feature 類型、機率），`generate_world` 透過 `extra_noise_specs` 參數產生命名 noise 圖供條件使用；`generate_world` 回傳 `WorldGenResult`（包含所有中間產物與 registry）

---

## 自定義地形（Terrain Registry）

`TerrainDef` 是平坦資料類別（對齊 RimWorld），沒有 class 繼承；「衍生」是使用者在定義 def 時自行決定要複製哪些父屬性。

```python
from mapcore.terrain import TerrainDef, DEFAULT_REGISTRY
from mapcore.generation import generate_world, TerrainPatch, apply_terrain_patches

# 1. 登錄衍生地形（id ≥ 100）
MAGICAL_FOREST = 100
DEFAULT_REGISTRY.register(TerrainDef(
    id=MAGICAL_FOREST,
    name="MAGICAL_FOREST",
    move_cost=2.0,
    is_water=False,
    tags=frozenset({"land", "forest", "magic"}),
))

# 2. 生成世界（帶一張 "magic" noise 圖）
result = generate_world(80, 60, seed=42, extra_noise_specs=[("magic", 1)])

# 3. 套用 overlay：只有 FOREST 格子且 magic noise ≥ 0.72 才會變成魔法森林
apply_terrain_patches(result, [
    TerrainPatch(
        derived_terrain=MAGICAL_FOREST,
        base_terrain_tags=frozenset({"forest"}),
        noise_channel="magic",
        noise_min=0.72,
        min_patch_size=3,   # 連通塊至少 3 格，避免孤立單格
        probability=0.9,
    ),
])
```

`TerrainPatch` 支援的條件類型：

| 參數 | 說明 |
|---|---|
| `base_terrain_ids` / `base_terrain_tags` | 基底地形篩選（id 集合或 tag；兩者皆空 = 接受全部）|
| `noise_channel` / `noise_min` / `noise_max` | 指定 extra\_noise 圖的閾值範圍 |
| `min_patch_size` | 連通塊最小大小（對齊 RimWorld `TerrainPatchMaker.minSize`）|
| `temp_min` / `temp_max` | °C 溫度範圍（需 `climate=True`）|
| `rainfall_min` / `rainfall_max` | mm 降雨範圍（需 `climate=True`）|
| `near_terrain_tags` / `near_radius` | N 格內必須有指定 tag 的地形 |
| `hilliness_filter` | 限定 Hilliness 等級集合 |
| `feature_types` | 限定 feature\_type 字串集合 |
| `probability` | 隨機套用機率（0~1）|

patches 按定義順序執行，後面的 patch 可以把前面套用的衍生地形當作 base（串聯）。

---

## 與 gamecore 其他部分的關係

- `plans/`：設計藍圖（世界三層架構等）。本模組對應「世界層」的格子地圖基礎。
- `specs/`：規格定稿區。當本模組的某個子系統穩定後，介面規格將移至此處。
- 原 `core/`（C++ GDExtension）：保留為未來效能瓶頸時的替代選項。

---

## 待實作演算法備忘

以下為規劃中但尚未實作的地圖生成技術，依類別整理備用。

### 山脈生成

#### 脊狀多分形噪聲 (Ridged Noise / Ridged Multi-fractal)

純數學方法，最常見的精確山脊生成方式。普通柏林噪聲波峰圓滑，對噪聲取絕對值後翻轉，可強制製造鋒利的山脊線。

**核心公式：**
```
RidgedNoise(x, y) = 1.0 - |Noise(x, y)|
MountainStrength(x, y) = (1.0 - |Noise(x, y)|) ^ p
```
冪次 `p` 通常設 2.0～4.0；次方越高，山脈越陡峭、越窄。

**實作邏輯：**
1. 獨立生成一張高頻率的脊狀噪聲圖（與主 heightmap 分開）
2. 與陸地遮罩相乘，確保山脈只出現在陸地上
3. 設定門檻：`MountainStrength > 0.85` → 山脈格；`0.70～0.85` → 丘陵格

結果：地圖上自然出現像閃電或血管般彼此相連的蜿蜒山脈帶。

**整合注意事項（環境壓制）：**
靠近海岸線的格子，山脈權重應漸漸壓低（離岸 3 格內線性壓制），避免山脈緊貼海岸導致船隻無法登陸或視覺突兀。

---

#### ✅ 斷層線板塊構造法 (Fault Line / Tectonic Plates)

**已實作於 `mapcore/generation/heightmap.py:_make_plate_field`，是 `ridge_mode="plates"`（預設）的核心算法。**

Civ5 在地球或大型地圖偏好此法，因為真實山脈由板塊擠壓形成，結果具備大局觀，能將大陸自然切分成數個地理區塊。

**實作細節（與一般描述的差異）：**
1. 隨機撒 `num_plates`（預設 12）個 Voronoi 種子；對每格 tile 找最近與第二近的種子 (d1, d2)。
2. 到 perpendicular bisector 的距離 = (d2 − d1) / 2；不需顯式建邊界線。
3. `boundary_strength = smoothstep(1 − bd / plate_boundary_width_pixels)`，邊界中心為 1、遠端為 0。
4. 走向：山脊沿邊界 = perpendicular 到 plate1→plate2 連線；推導出 `ca = -vy/|v|, sa = vx/|v|` 直接餵旋轉矩陣，繞過 heading 度數轉換。
5. 主迴圈 inner 用 `local_w = ridge_weight × boundary_strength` 代替全域 ridge_weight；板塊內部 local_w≈0 自動回到純 fBm。

**參數：**
- `num_plates` (int, 預設 20) — 越多 → 邊界越密、山脈越短
- `plate_boundary_width` (float, 預設 0.05) — 邊界帶寬度（以 min(W,H) 為 1）；調小讓山脈線變細
- `ridge_power` (float, 預設 2.0) — 折疊冪次，對應 Musgrave RidgedNoise^p；1=線性、2~4 越尖銳
- `ridge_multifractal_gain` (float, 預設 2.0) — Musgrave 多分形增益。每 octave carry = clamp(fold × gain, 0, 1)，下一 octave 折疊乘 carry，讓主脊延伸、支脈分支；0=關閉多分形

**對照舊行為：**
若要回到「整張地圖橫貫條紋」風格，傳 `ridge_mode="global"`；`ridge_direction` / `ridge_direction_variation` 僅在 global 模式生效。回到單尺度折疊：`ridge_power=1.0, ridge_multifractal_gain=0.0`。

---

### 特殊地圖佈局：Voronoi 圖

當需要精準控制整體佈局（內海、大平原、高地等官方地圖腳本），單靠噪聲難以做到，引入 Voronoi 圖（泰森多邊形）。

**內海地圖實作：**
- 先用數學公式畫一個大型中空橢圓遮罩（中心強制為海、四周為陸）
- 用 Voronoi 圖將外圍陸地分割成 6～8 個板塊區域
- 每個區域隨機分配不同的噪聲權重（例如偏多山或偏多沼澤），確保大框架固定但內部細節每次不同

**群島優化（防止孤立單格島嶼）：**
- 以 Voronoi 胞格作為島嶼核心骨架，確保每個胞格內至少有 3～5 格相連陸地
- 演算法檢查島嶼間的最短海路距離；若過遠，自動在中間補「踏腳石」小島，確保早期船隻能通行

---

### 地貌精緻化：水力侵蝕演算法 (Hydraulic Erosion)

讓地形從「看起來是數學運算出的」昇華到「看起來像真實大自然」的進階技術。在基礎地形（山脈、平原）生成後執行。

**流程：**
1. 在地圖上隨機降下數千個「虛擬水滴」
2. 水滴依坡度向下滾動
3. 滾動過程中侵蝕 (Erode) 高處土壤（降低該格高程），帶走泥沙
4. 流速變慢或停下時，將泥沙沉積 (Deposit)（提高該格高程）
5. 經過數萬次水滴迭代，山脈邊緣出現自然的「沖積扇」，山谷趨於平緩

---

### 陸海識別：洪水填充連通分量 (Flood Fill / Connected-Component Labeling)

heightmap 切割後，電腦只有 0/1 矩陣，不知道哪塊是大陸、哪塊是孤立小島。Flood Fill 從某個格子開始「潑水式」擴散到所有相連的同類格子，並記錄連通分量 ID 與格子總數。

**在地圖生成中的應用（對齊 Civ5）：**
- **湖泊 vs. 海洋**：水域連通分量格數 < 閾值（例如 10 格）→ 標記為湖泊 (Lake) 而非海洋 (Ocean)。湖泊可提供農田淡水加成，海洋不行。
- **小島清除**：陸地連通分量格數 < 閾值 → 視為噪點小島，填回海洋（已在 Phase 4 後處理實作）

> **目前狀態**：`postprocess.py` 的 `find_components` 已實作 BFS 連通分量，但尚未做「格數計算後依大小分流到不同地形類別」的完整版本。

---

### 資源與植被聚集：隨機漫步 (Random Walk / Drunkard's Walk)

純機率刷資源（例如每格有 20% 機率變成森林）會導致分布零散、視覺不自然。隨機漫步讓資源成片聚集，形狀有機。

**流程（以森林為例）：**
1. 依氣候與緯度條件選定一個適合的「種子格」
2. 將該格設為森林
3. 隨機往周圍 6 個方向（六角）踏一步
4. 在新格種下森林
5. 重複 N 次（N 決定此片森林的大小）

結果：形狀不規則、邊緣有機蔓延的森林或沼澤區塊。

> **實作提示**：可在 `generation/overlay.py` 的 `TerrainPatch` 條件命中後，用隨機漫步取代現在的「per-tile 機率」方式，讓 patch 形狀更像真實地貌。
