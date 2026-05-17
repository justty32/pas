# Freeciv 架構分析：地圖與資源資料結構 (Data Structures)

本文件專門解構 Freeciv 地圖與資源系統的底層資料模型。Freeciv 採用 C 語言實作，其資料結構設計的核心目標是 **「極致的查詢效能」** 與 **「高度的規則擴展性」**。

---

## 1. 全域容器：`struct civ_map`
定義於 `common/map_types.h`。它是整個遊戲世界的物理載體。

| 成員變數 | 類型 | 說明 |
| :--- | :--- | :--- |
| `xsize`, `ysize` | `int` | 地圖的原生尺寸（Native Dimensions）。 |
| `tiles` | `struct tile *` | **核心陣列**。採用一維展平佈局，儲存所有地圖方格實例。 |
| `topology_id` | `int` | 定義拓樸形狀（平面、圓柱、環面、六角形等）。 |
| `continent_sizes` | `int *` | 動態陣列，儲存每個大陸（由編號索引）的總面積。 |
| `ocean_sizes` | `int *` | 動態陣列，儲存每個海洋的總面積。 |

**工程細節**：使用一維陣列 `tiles[xsize * ysize]` 而非二維陣列，是為了保證地圖遍歷時的 **CPU 快取局部性 (Cache Locality)**，減少分頁缺失。

---

## 2. 方格實體：`struct tile`
定義於 `common/tile.h`。這是地圖上最細粒度的資料單元，承載了動態變化的狀態。

```c
struct tile {
  int index;                /* 在一維陣列中的絕對索引 */
  Continent_id continent;   /* 大陸編號 (Flood Fill 產出) */
  bv_extras extras;         /* 位元向量：道路、灌溉、礦坑、污染等狀態 */
  struct extra_type *resource; /* 指向靜態資源定義的指標 (如：煤、馬) */
  struct terrain *terrain;  /* 指向靜態地形定義的指標 (如：草原、高山) */
  struct unit_list *units;  /* 該方格上的單位鏈結串列 */
  struct city *worked;      /* 正在開發此格的城市指標 */
  struct player *owner;     /* 領土擁有者 */
  int altitude;             /* 原始高度值 (0-1000) */
};
```

### 關鍵優化：位元向量 `bv_extras`
`bv_extras` 是一個位元陣列（Bitvector）。Freeciv 將所有「方格附加物」編碼為位元位：
- Bit 0: 是否有道路
- Bit 1: 是否有灌溉
- Bit 2: 是否有礦坑
- ...以此類推。
**優點**：判斷一個方格是否具備某種屬性只需要一次 `AND` 運算，且極度節省空間。

---

## 3. 靜態定義：地形與資源 (Ruleset Objects)
定義於 `common/terrain.h`。這些結構代表了遊戲的「規則」，而非具體的方格實例。

### 地形定義：`struct terrain`
這是由 `terrain.ruleset` 加載而來的靜態模板。
- **`output[O_LAST]`**: 儲存基礎 [食物, 產能, 貿易] 產出的整數陣列。
- **`movement_cost`**: 移動此地形所需的移動力點數。
- **`defense_bonus`**: 防禦加成百分比。
- **`irrigation_food_incr`**: 灌溉後增加的食物量。
- **`mining_shield_incr`**: 採礦後增加的產能量。

### 資源定義：`struct resource_type`
代表特定資源點（Specials）的加成規則。
- **`output[O_LAST]`**: 此資源疊加在地形上後產生的**額外**產值。

---

## 4. 資源產出枚舉：`Output_type_id`
定義於 `common/fc_types.h`。統一了全系統的經濟度量衡。

```c
enum output_type_id {
  O_FOOD,      /* 食物 */
  O_SHIELD,    /* 產能/護盾 */
  O_TRADE,     /* 貿易額 (金錢/科學/奢華度的母體) */
  O_GOLD,      /* 金錢 */
  O_LUXURY,    /* 奢華度 */
  O_SCIENCE,   /* 科學點數 */
  O_LAST
};
```

---

## 5. 資料結構間的關聯模型

1.  **多對一映射**：數萬個 `struct tile` 實例會根據其屬性，共同指向同一個 `struct terrain` 靜態定義。這是一種典型的 **享元模式 (Flyweight Pattern)**，節省了大量重複的屬性存儲空間。
2.  **動靜分離**：
    *   **動態資料** (`tile`)：頻繁變動（如：國界、單位移動、蓋路），儲存在 `civ_map` 中。
    *   **靜態資料** (`terrain`, `resource_type`)：遊戲開始後不再變動，儲存在全域的 Ruleset 緩衝區中。
3.  **座標抽象**：透過 `common/map.c` 中的轉換函數，`tile->index` 可以無縫轉換為 `Native (x,y)` 或 `Map (x,y)`，支援了複雜的地圖投影與繞回邏輯。

## 總結
Freeciv 的地圖資料結構是 **「靜態模板 + 享元實例 + 位元向量標記」** 的組合。這種設計讓它在 30 年後的今天，依然在處理大規模策略模擬時擁有極高的效能表現。
