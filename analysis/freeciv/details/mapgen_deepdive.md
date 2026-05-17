# Freeciv 地圖生成：源碼級極致深度解析

本文件針對 `freeciv/server/generator/mapgen.c` 中的主進入點 `map_fractal_generate()` 以及其呼叫的子流程進行極致詳細的 C 語言原始碼級別追蹤。所有分析皆嚴格基於 Freeciv 的底層實作。

## 1. 進入點：`map_fractal_generate(bool autosize, struct unit_type *initial_unit)`
這是整個地圖生成系統的心臟。

### 1.1 隨機數種子初始化與保存
一開始，系統透過 `RANDOM_STATE rstate;` 保存目前的隨機狀態。這非常關鍵，因為地圖生成中包含了大量 `fc_rand()` 呼叫。
```c
seed_rand = fc_rand(MAX_UINT32);
if (wld.map.server.seed_setting == 0) {
  wld.map.server.seed = seed_rand & (MAX_UINT32 >> 1);
  ...
} else {
  wld.map.server.seed = wld.map.server.seed_setting;
}
rstate = fc_rand_state();
fc_srand(wld.map.server.seed);
```
這確保了只要 `map.seed` 相同，生成的地圖將 100% 相同（確定性生成），這對於多人連線同步與 debug (`FREECIV_TESTMATIC`) 至關重要。

### 1.2 核心生成器分發
在處理完基本參數（如 `adjust_terrain_param()` 調整山脈、森林、河流的生成機率）後，程式會先呼叫 `create_tmap(FALSE)` 創建一個虛擬的溫度圖，然後根據 `wld.map.server.generator` 分發到不同的具體生成函式：
- `MAPGEN_FAIR` (公平島嶼): 呼叫 `map_generate_fair_islands()`。如果失敗，會降級 (Fallback) 到 `MAPGEN_ISLAND`。
- `MAPGEN_ISLAND`: 根據玩家數量呼叫 `mapgenerator2()`, `3()`, 或是 `4()`。
- `MAPGEN_FRACTAL` (預設的高級生成器): 呼叫 `make_pseudofractal1_hmap()`。

---

## 2. 高度圖生成：`make_pseudofractal1_hmap(int extra_div)`
位於 `height_map.c`。這是一個帶有邊界限制的遞歸中點位移法 (Midpoint Displacement)。

### 2.1 記憶體分配與初始化
```c
height_map = fc_malloc(sizeof(*height_map) * MAP_INDEX_SIZE);
INITIALIZE_ARRAY(height_map, MAP_INDEX_SIZE, 0);
```
`height_map` 是一個一維陣列，透過 `tile_index(ptile)` 來存取。

### 2.2 初始網格設定
地圖被分為 `xdiv` $\times$ `ydiv` 的區塊（預設 $5 \times 5$）。
巨集 `do_in_map_pos` 用於遍歷這些初始網格的頂點：
```c
hmap(ptile) = fc_rand(2 * step) - (2 * step) / 2;

if (near_singularity(ptile)) {
  /* Avoid edges (topological singularities) */
  hmap(ptile) -= avoidedge;
}
```
**細節**: `step` 被定義為 `MAP_NATIVE_WIDTH + MAP_NATIVE_HEIGHT`。`avoidedge` 變數會使靠近拓樸奇異點（邊緣）的頂點高度被強制拉低，從而確保大陸不會貼在不能 Wrap 的地圖邊緣。

### 2.3 遞歸分割 (`gen5rec`)
```c
gen5rec(step, x_current * xmax / xdiv, y_current * ymax / ydiv,
        (x_current + 1) * xmax / xdiv, (y_current + 1) * ymax / ydiv);
```
在 `gen5rec` 中，使用了 `val[2][2]` 保存矩形四個角的高度。透過巨集 `#define set_midpoints(X, Y, V)` 來設定中點：
1. 邊界中點高度 = 兩端平均 + `fc_rand(step) - step / 2`。
2. 遞歸呼叫 `gen5rec`，並將 `step` 衰減為 `2 * step / 3` (整數除法)，這決定了地形的分形維度（粗糙度）。
3. **後處理縮放與 Fuzz**: 遞歸結束後，執行 `hmap(ptile) = 8 * hmap(ptile) + fc_rand(4) - 2;`。這將高度值放大 8 倍以增加後續處理的精度，並加入微小的抖動噪音。
4. **歸一化**: 最後呼叫 `adjust_int_map` 將值鎖定在 0-1000 範圍。

---

## 3. 地形映射：`make_land()`
位於 `mapgen.c`。高度圖建立後，呼叫此函式將連續的高度轉換為具體地形。

### 3.1 海平面決定
```c
hmap_shore_level = (hmap_max_level * (100 - wld.map.server.landpercent)) / 100;
```
海平面精準地由玩家設定的 `landpercent` 計算得出。低於此值的皆為海洋。

### 3.2 海洋深度與結冰判定
使用巨集 `whole_map_iterate(&(wld.map), ptile)` 走訪每一個方塊：
```c
if (hmap(ptile) < hmap_shore_level) {
  int depth = (hmap_shore_level - hmap(ptile)) * 100 / hmap_shore_level;
  ... // 計算周遭陸地數量來減少淺灘連接
  bool frozen = HAS_POLES && (tmap_is(ptile, TT_FROZEN) || ...);
  struct terrain *pterrain = pick_ocean(depth, frozen);
  tile_set_terrain(ptile, pterrain);
}
```
這裡會讀取方塊對應的溫度 `tmap_is(ptile, TT_FROZEN)`，決定是否生成冰凍海洋 (`pick_ocean(depth, frozen)`)。

### 3.3 創建真實溫度圖與地形細化
在確定陸地後，呼叫：
```c
destroy_tmap();
create_tmap(TRUE); // 創建真實溫度圖 (考慮海拔降溫與海洋調節)
make_relief(); // 根據高度圖分配山脈與丘陵
make_terrains(); // 根據溫度圖分配叢林、沙漠等
```

---

## 4. 溫度圖生成：`create_tmap(bool real)`
位於 `temperature_map.c`。
```c
int tcn = count_terrain_class_near_tile(&(wld.map), ptile, FALSE, TRUE, TC_OCEAN);
float temperate = (0.15 * (wld.map.server.temperature / 100 - t / MAX_COLATITUDE) * 2 * MIN(50, tcn) / 100);
tmap(ptile) = t * (1.0 + temperate) * (1.0 + height);
```
**細節**: `tcn` 透過 `count_terrain_class_near_tile` 取得周遭海洋板塊數量。如果 `real` 為 true，溫度會加上 `temperate` (海洋調節，最高15%) 與 `height` (海拔降溫，最高降30%)。最後透過 `adjust_int_map` 均勻化，並切分為 `TT_FROZEN`, `TT_COLD`, `TT_TEMPERATE`, `TT_TROPICAL` 四個位元遮罩值。

---

## 5. 河流生成：`make_rivers()` 與 `make_river()`
位於 `mapgen.c`。
河流是一步一步計算出來的，使用 `rd_comparison_val[8]` 陣列評估 8 個方向（雖然實際上只允許基數方向 `cardinal_adjc_dir_iterate`）。

```c
cardinal_adjc_dir_iterate(&(wld.map), ptile, ptile1, dir) {
  if (rd_direction_is_valid[dir]) {
    rd_comparison_val[dir] = (test_funcs[func_num].func)(privermap, ptile1, priver);
    ...
```
`test_funcs` 是一個包含 9 個測試函數的陣列，包含了多種啟發式測試函數（例如 `river_test_blocked` 防止自交, `river_test_adjacent_ocean` 返回 `100 - 海洋數量`, `river_test_height_map` 直接返回 `hmap(ptile)`）。
最後，如果有並列最優的方向，則使用 `fc_rand(num_valid_directions)` 隨機選擇。河流路徑會記錄在 `dbv_set(&privermap->ok, tile_index(ptile))` (動態位元向量) 中，確保不會衝突。

---

## 6. 資源與部落：`add_resources()` 與 `make_huts()`
在地圖生成的尾聲。
```c
struct extra_type *res = pick_resource(pterrain);
if (res != nullptr) {
  tile_set_resource(ptile, res);
}
```
`pick_resource()` 會根據 ruleset 中定義的地形-資源對應表隨機挑選。
對於部落 (`make_huts`)，使用了一個名為 `placed_map` 的距離遮罩。當放置一個 hut 後：
```c
set_placed_near_pos(ptile, 3);
```
這會將周遭 3 格內的方格標記為 `placed`，後續的隨機挑選若選中 `placed` 方格則跳過，藉此實作泊松圓盤採樣 (Poisson Disk Sampling) 的效果，保證村落的均勻散佈。

---

## 總結
Freeciv 的地圖生成演算法高度依賴：
1. **全域與區域性的動態記憶體結構**：如 `height_map` 陣列、`temperature_map` 陣列，以及用於防碰撞的 `dbv` (Dynamic Bit Vector)。
2. **巨集迭代器**：大量使用 `whole_map_iterate`, `adjc_iterate`, `cardinal_adjc_dir_iterate` 確保在各種地圖拓樸 (如 Torus, Cylinder) 下鄰居走訪的正確性。
3. **規則與機率的交織**：幾乎所有的「常數」都會加上一個基於 `fc_rand()` 的微小偏移，造就了其地圖的自然感。
