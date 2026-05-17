# 拓樸架構深化：Native 與 Map 座標轉換模型 (源碼剖析)

Freeciv 的地圖系統最硬核的部分在於其支援多種投影與繞回方式。為了讓同一套邏輯能同時跑在「等軸測 45 度視角 (Isometric)」與「平視視角 (Flat)」的地圖上，系統實作了一套極其嚴密的座標轉換矩陣。本文件深入剖析 `common/map.c` 與 `common/map.h` 中的座標轉換模型。

## 1. 三層座標系定義

| 座標系 | 說明 | 存取方式 |
| :--- | :--- | :--- |
| **Native (nat_x, nat_y)** | 記憶體中的實際二維陣列位置，始終是矩形。 | `tiles[nat_y * xsize + nat_x]` |
| **Map (map_x, map_y)** | 邏輯上的世界座標，玩家與 AI 理解的位置。 | 封包傳輸、規則計算用。 |
| **Index (index)** | 一維展開後的絕對索引。 | `tile_index(ptile)` |

---

## 2. 轉換矩陣：`NATIVE_TO_MAP_POS`
這是 Freeciv 中最重要的座標轉換巨集，位於 `common/map.h`。

### 2.1 平視模式 (Flat / Traditional)
在傳統視角下，轉換是恆等映射，但需處理 **繞回 (Wrap)**：
```c
map_x = nat_x;
map_y = nat_y;
/* 處理繞回 */
if (wrap_x) map_x %= xsize;
```

### 2.2 等軸測模式 (Isometric)
這是 Freeciv 為了達成 Civilization II 風格的斜向 45 度視角所引入的數學變換。

**轉換公式解構**:
1. **$45^\circ$ 旋轉**:
   - `map_x = nat_x - (nat_y / 2)`
   - `map_y = nat_x + (nat_y + 1) / 2`
2. **偏移補償**:
   - 為了讓地圖邊界看起來是對齊的，系統會根據 `nat_y` 的奇偶性加入一個 `half-tile` 的偏移量。

**逆轉換 (`MAP_TO_NATIVE_POS`)**:
- `nat_x = (map_y + map_x) / 2`
- `nat_y = map_y - map_x`

---

## 3. 鄰近邏輯與繞回算術 (`map_step`)

當你執行 `mapstep(nmap, ptile, DIR_NORTH)` 時，系統是如何處理的？

### 3.1 抽象方向向量
系統預定義了一個 `dir_offsets[8]` 陣列。對於不同的拓樸，同一個「北方」對應的 $(dx, dy)$ 是不同的：
- **Flat 模式**: 北方 = $(0, -1)$。
- **Isometric 模式**: 北方 = $(-1, -1)$（因為坐標軸旋轉了 45 度）。

### 3.2 座標正規化 (`normalize_map_pos`)
這是防止越界的最後防線：
```c
bool normalize_map_pos(const struct civ_map *nmap, int *x, int *y) {
  /* 1. 處理 Y 軸邊界 (若不繞回，超出則失效) */
  if (*y < 0 || *y >= nmap->ysize) return FALSE;
  
  /* 2. 處理 X 軸繞回 */
  if (nmap->wrap_id & WRAP_X) {
    *x = real_modulo(*x, nmap->xsize);
  }
  return TRUE;
}
```

---

## 4. 特殊拓樸：環面 (Torus) 與圓柱 (Cylinder)
- **圓柱**: `WRAP_X` 開啟，`WRAP_Y` 關閉。這是最常見的模式。
- **環面**: 同時開啟 `WRAP_X` 與 `WRAP_Y`。從南極走下去會從北極出來。
- **數學挑戰**: 在 Isometric 下實作 `WRAP_Y` 極度困難，因為 $y$ 座標的變化會同時影響 $x$。Freeciv 透過在 `native` 空間進行計算，最後才轉回 `map` 空間，優雅地避開了斜向繞回的幾何複雜性。

---

## 5. 工程見解
- **全巨集運算**: 所有的轉換都盡可能使用 `#define` 巨集而非函數。這是因為地圖生成與 AI 尋路每秒需要進行數百萬次座標轉換，巨集內聯化（Inlining）能消除函數呼叫的 Stack 開銷。
- **原生優先原則**: Freeciv 內部的資料儲存（如 `height_map`, `tile_known`）一律使用 **Native 空間**。只有當需要與玩家互動或進行規則判定（如「兩座城市間的距離」）時，才會轉為 Map 空間。這種「存儲與表現分離」的策略是其支援多種拓樸的基石。
- **距離恆定性**: 無論視角如何變化，`real_map_distance()` 函數始終計算最短的邏輯步數，這保證了 AI 在不同圖形介面下的行為是一致的。
