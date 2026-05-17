# Unciv 地圖資料結構深度解析

這份文件詳盡剖析了 Unciv 的地圖與座標系統，從底層的座標數學到高層的地圖容器。

---

## 1. 座標系統：六角格座標 (Hexagonal Coordinates)
Unciv 使用的是 **軸向座標系 (Axial Coordinates)**，但在內部計算時會靈活切換到不同的表示法。

### 1.1 座標定義 (`HexCoord`)
*   **基礎變量**: `x`, `y` (Int)。
*   **方向定義**:
    *   $x$ 軸：指向 **10 點鐘** 方向。
    *   $y$ 軸：指向 **2 點鐘** 方向。
*   **座標變換公式**:
    *   **緯度 (Latitude)**: $x + y$ (與赤道的距離)。
    *   **經度 (Longitude)**: $x - y$。
    *   **行 (Row)**: $(x + y) / 2$。
    *   **列 (Column)**: $y - x$。
*   **距離計算**: 
    ```kotlin
    fun getDistance(originX, originY, destX, destY): Int {
        val dx = originX - destX
        val dy = originY - destY
        return if (dx * dy >= 0) max(abs(dx), abs(dy))
               else abs(dx) + abs(dy)
    }
    ```

### 1.2 效能優化：`InlineHexCoord`
為了避免大量的小型對象分配（Allocation），Unciv 實作了 `value class InlineHexCoord`：
*   將 $x$ 與 $y$ 各用 16 bits 存儲，打包進一個 32 bits 的 `Int` 中。
*   範圍支援 $-32768$ 到 $32767$，足以應付任何超大型地圖。

---

## 2. 地圖容器：`TileMap`
`TileMap` 是整個遊戲世界的集合點，處理序列化與快速存取。

### 2.1 雙層存儲結構
*   **序列化層 (`tileList`)**: 
    `var tileList = ArrayList<Tile>()`
    這是持久化（存檔）時使用的線性列表。
*   **存取層 (`tileMatrix`)**: 
    `@Transient var tileMatrix = ArrayList<ArrayList<Tile?>>()`
    這是一個二維矩陣（由 Row/Column 索引），用於遊戲執行時的高效查詢。源碼註釋指出，這比 `HashMap` 快得多。

### 2.2 地圖索引 (`zeroBasedIndex`)
為了進一步提升效能（例如使用 `BitSet`），系統會將 $(x, y)$ 座標映射到一個唯一整數：
*   $0$ 是中心點。
*   第一環是 $1-6$，第二環是 $7-18$，依此類推。
*   這使得地圖可以被視為一個緊湊的陣列。

---

## 3. 地塊結構：`Tile`
`Tile` 是承載遊戲邏輯的核心對象。

### 3.1 序列化內容 (核心資料)
*   **地形與特徵**: `baseTerrain` (String), `terrainFeatures` (List<String>)。
*   **資源與奇觀**: `resource`, `resourceAmount`, `naturalWonder`。
*   **單位層**: 
    *   `militaryUnit`: 軍事單位。
    *   `civilianUnit`: 民用單位。
    *   `airUnits`: 航空單位列表。
*   **河流表示法**: 
    河流是在邊界上流動的。`Tile` 儲存了三個布林值來標記與鄰居間的邊界是否有河流：
    *   `hasBottomRightRiver`, `hasBottomRiver`, `hasBottomLeftRiver`。
*   **所有權**: `owningCity` (Transient)。

### 3.2 效能優化：鄰居快取
```kotlin
val neighbors: Sequence<Tile> by lazy { getTilesAtDistance(1).toList().asSequence() }
```
由於地圖是靜態的（六角形的結構不會變），`Tile` 對象在初始化時會 **Lazy 加載** 鄰居列表，大幅減少了搜尋路徑 (Pathfinding) 時的運算量。

---

## 4. 座標與螢幕空間的轉換
`HexMath` 提供了將六角座標轉換為 LibGDX 世界座標的方法：
*   **邊長**: 預設使用 $\sqrt{3}$ 作為間距單位。
*   **10 點鐘方向向量**: `sin(angle), cos(angle)` 其中 angle 為 $\frac{10}{12} \times 2\pi$。
*   **換算**: 世界座標由 $x$ 與 $y$ 兩個方向向量的加權和決定。
