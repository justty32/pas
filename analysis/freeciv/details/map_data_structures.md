# Freeciv 地圖資料結構深度分析 (源碼剖析)

Freeciv 的地圖系統採用了高度抽象且效能優化的設計。它不僅儲存地形，還承載了領土、單位、城市工作以及複雜的拓樸邏輯。

## 1. 全域地圖容器：`struct civ_map`
定義於 `common/map_types.h`。這是整個世界的頂層結構。

### 核心成員解析
- **`xsize`, `ysize`**: 地圖的「原生維度 (Native dimensions)」。
- **`tiles`**: `struct tile *` 指標。這是一個**展平的一維陣列**，包含了地圖上所有的方格。這種設計能最大化 CPU 快取效能。
- **拓樸資訊 (`topology_id`, `wrap_id`)**: 決定地圖是平面、圓柱（左右繞回）還是環面。
- **大陸與海洋統計**:
    - `num_continents`, `num_oceans`: 獨立陸塊與水域的數量。
    - `continent_sizes`, `ocean_sizes`: 儲存每個大陸/海洋所佔方格數的動態陣列。這為 AI 評估大陸價值提供了基礎。
- **Server/Client 聯集**:
    - **Server 端**: 儲存生成器設定（種子、陸地百分比、溫度、濕度等）。
    - **Client 端**: 儲存 `adj_matrix`（鄰近矩陣），用於優化渲染與黑幕邊緣計算。

## 2. 核心原子：`struct tile`
定義於 `common/tile.h`。這是地圖上的單一座標點。

### 關鍵欄位深度剖析
- **`index`**: 在一維陣列中的位置。透過巨集 `TILE_XY(ptile)` 與 `index_to_map_pos()` 可以轉換回 2D 座標。
- **`terrain`**: 指向 `struct terrain` 的指標。包含地形的基本屬性（移動消耗、防禦加成、基礎產出）。
- **`extras` (`bv_extras`)**: 一個**位元向量 (Bitvector)**。
    - 用於儲存地圖上的「附加物」，如道路、鐵路、灌溉、礦坑、要塞、污染等。
    - **優點**: 查詢「這格有沒有路」只需一次位元運算，極其快速。
- **`resource`**: 戰略資源指標（如煤、馬、油）。
- **`continent`**: 所屬大陸編號。在地圖生成後透過洪氾填充 (Flood Fill) 決定。
- **`units`**: 指向 `struct unit_list`。由於 Freeciv 支援單位堆疊，這是一個鏈結串列。
- **`owner` & `claimer`**: 處理國界與領土範圍。`owner` 是目前的領土擁有者，`claimer` 是具有爭議的聲索權來源。
- **`altitude`**: 儲存高度圖的高度值 (0-1000)。雖然地圖生成後主要以地形為主，但高度資訊仍被保留用於部分計算。

## 3. 座標系統與拓樸學 (Topology)
Freeciv 最具特色的地方在於它對座標的處理方式：

### 三層座標抽象
1. **原生座標 (Native Coordinates)**: 記憶體中實際儲存的 $(x, y)$。
2. **地圖座標 (Map Coordinates)**: 玩家在 UI 上看到的 $(x, y)$，這會受到拓樸（如等軸測視角 Isometric）的投影影響。
3. **一維索引 (Index)**: 用於陣列存取。

### 鄰居走訪器 (`adjc_iterate`)
Freeciv 大量使用巨集來遍歷鄰居。這些巨集會自動根據 `wrap_id` 處理「邊界穿越」：
```c
/* 示意邏輯 */
#define adjc_iterate(nmap, center_tile, neighbor_tile) \
  for (int i = 0; i < 8; i++) { \
    neighbor_tile = get_neighbor(center_tile, directions[i]); \
    if (neighbor_tile) { ... } \
  }
```
這種設計讓遊戲邏輯（如傳播污染、傳播國界）不需要關心目前地圖是否會「繞回」。

## 4. 工程見解
- **記憶體展平**: 使用一維陣列而非 `tile[y][x]` 減少了指標解引用的層數，且在執行 `whole_map_iterate` 時具備極佳的記憶體連續性。
- **位元遮罩優化**: 幾乎所有頻繁查詢的狀態（地形屬性、附加物、視野）都使用了位元向量 (`bitvector.h`)，這在多人連線且單位眾多的後期遊戲中是效能的關鍵。
- **資料與展示分離**: `struct tile` 只儲存邏輯數據。具體的渲染圖像（Sprites）是在 Client 端根據 `terrain` 指標動態查找對應的圖塊。
- **虛擬方格 (`tile_virtual_new`)**: Freeciv 支援建立虛擬方格。這被 AI 廣泛用於「虛擬試蓋建築」或「模擬戰鬥」而不會影響真實的遊戲狀態。
