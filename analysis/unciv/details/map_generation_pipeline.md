# Unciv 地圖生成：終極技術白皮書 (源碼級深度解析)

這份文件是對 Unciv 地圖生成管線的極致深度剖析，涵蓋了從 `MapGenerator.kt` 到 `MapRegions.kt` 的所有核心邏輯、隱藏常數與演算法細節。

---

## 0. 全域常數與初始化 (Initialization)
地圖生成受 `MapParameters` 控制，種子碼 (Seed) 如果未指定，則預設使用 `System.currentTimeMillis()`。

*   **關鍵組件**:
    *   `randomness`: 負責提供 Perlin 噪聲與確定性隨機數。
    *   `terrainConditions`: 從 Ruleset 中預加載，依據是否受限 (`isConstrained`) 排序。
    *   `baseTerrainPicker`: 用於分配陸地與海洋的候選地形列表。

---

## 1. 陸地生成深潛 (Landmass Generation Deep Dive)
`MapLandmassGenerator` 負責決定基礎地形的分布。

### 1.1 水位線重試機制 (`retryLoweringWaterLevel`)
如果生成的地圖海洋佔比過高（預設 > 70%），演算法會嘗試最多 **30 次** 重試。
*   **動態調整公式**: 
    每次重試會下調 `waterThreshold`：
    `waterThreshold -= 0.02 * (waterPercent / 0.7).coerceAtLeast(1.0) * sqrt(retryCount)`
    這是一個具備加速效果的負反饋循環。

### 1.2 地圖類型專屬邏輯
*   **Pangaea (盤古大陸)**:
    *   **判定標準**: 必須存在一個「大於 `largeContinentThreshold`」的單一陸塊。
    *   `largeContinentThreshold` 計算: `max(25, min(totalTiles / 4, totalTiles^0.333))`。
    *   **混合公式**: `elevation = (PerlinNoise * 0.75) + (EllipticContinent * 0.25)`。
*   **Fractal (分形)**:
    *   比例尺度 (`scale`) 會隨地圖尺寸調整：`scale = (max(W, H) / 32.0) * 30.0`。
    *   六角形地圖下 scale 會減半，避免過於集中。
*   **Flat Earth (平心論)**:
    *   特殊處理：地圖邊緣（冰牆處）與中心（北極）會強制生成 **3-4 格寬的海洋帶**，防止生成關鍵資源被冰牆覆蓋。

---

## 2. 氣候模擬詳解 (Climate Simulation)
`applyHumidityAndTemperature` 決定了地形的顏色與生物群系。

### 2.1 溫度與緯度公式
*   **地球模式 (Globe)**: 
    `baseTemp = 1.0 - 2.0 * abs(tile.latitude) / maxLatitude` (赤道 1, 兩極 -1)。
*   **平心模式 (Flat Earth)**: 
    溫度基於到中心的半徑距離計算。
*   **最終溫度計算**: 
    `finalTemp = (5.0 * baseTemp + PerlinNoise) / 6.0` (緯度權重佔 5/6)。
    之後套用 `temperatureIntensity` 冪次轉換，增強或減弱溫帶區域。

### 2.2 濕度生成
純粹由 Perlin 噪聲生成，`scale` 取決於 `tilesPerBiomeArea` (預設為每個生物群系區域的大小)。

---

## 3. 海拔與元胞自動機 (Elevation & Cellular Automata)
`MapElevationGenerator` 處理山脈與丘陵。

### 3.1 初次分配 (Initial Pass)
*   `elevation > 0.7` $\rightarrow$ 山脈候選。
*   `elevation > 0.5` $\rightarrow$ 丘陵候選。
*   其餘 $\rightarrow$ 平原/草原。

### 3.2 山脈鏈優化 (Cellular Mountain Ranges)
進行 **5 輪** 迭代優化：
1.  **判定規則**:
    *   `adjMountains == 0`: 如果是山但沒鄰居，**1/4** 機率變平原（移除碎石）。
    *   `adjMountains == 1`: 如果不是山但有 1 個山鄰居，**1/10** 機率變山（延長山鏈）。
    *   `adjImpassible > 3`: 太多阻擋物時，強制變回平原（防止山脈過於臃腫）。
2.  **數量補償**: 演算法會追蹤 `totalMountains` 並與 `targetMountains` (初始值的 2 倍) 比較，確保山脈不會消失。

### 3.3 丘陵優化 (Cellular Hills)
同樣進行 **5 輪** 迭代：
*   **聚集規則**: 如果周圍有 2-3 個山脈/丘陵，平原 **1/2** 機率變成丘陵。
*   **孤立規則**: 丘陵鄰居 $\le 1$ 且無山脈，**1/2** 機率變平原。

---

## 4. 河流工程學 (River Engineering)
河流在六角格的**邊界頂點**上運行。

### 4.1 尋找源頭
1.  **優先級**: 山脈 (遠離海) $>$ 丘陵 (遠離海) $>$ 陸地 (遠離海)。
2.  **間距要求**: 起點必須距離海洋至少 `minRiverLength` 個地塊。

### 4.2 頂點遍歷 (`RiverCoordinate`)
河流移動不是格子到格子，而是頂點到頂點。
*   **頂點選擇機制**:
    每個頂點有 3 個相鄰頂點候選。
    演算法會評估 3 個候選點周圍 6 個地塊的「到海最近距離」。
*   **貪婪選擇**: 選擇能讓「剩餘距離」最小化的頂點。
*   **死路處理**: 如果所有路徑都遠離海洋，或者河流達到 `maxRiverLength`，則停止生成。

---

## 5. 區域平衡與評分表 (Region Balancing)
`MapRegions` 是地圖生成的「公正官」。

### 5.1 肥沃度評分 (Fertility)
這是 `Region` 劃分的基礎：
*   **基礎地形**: 由 Ruleset 中的 `AddFertility` unique 定義。
*   **淡水加成**: 鄰近河流 $+1$，鄰近淡水湖 $+1$ (累加可達 $+2$)。
*   **海岸加成**: 鄰近海岸 $+2$ (僅在 `checkCoasts` 為 true 時)。

### 5.2 區域劃分演算法 (`divideRegion`)
這是一個遞迴演算法：
1.  計算整個大陸的 `totalFertility`。
2.  **二分法**: 根據需要分配的人數比例（例如 $50\%/50\%$），尋找一條最能平均分割肥沃度的線（水平或垂直）。
3.  **重複遞迴**: 直到每個區域只剩下一個文明的名額。

### 5.3 起始點評分表 (The Scoring Tables)
系統會對起始點周圍三環進行嚴格審核：

| 評分項 | 第一環 (Ring 1) | 第二環 (Ring 2) | 第三環 (Ring 3) |
| :--- | :--- | :--- | :--- |
| **最小食物要求** | 1 | 4 | 4 |
| **最小生產要求** | 0 | 0 | 2 |
| **總價值要求** | 3 | 6 | 8 |

**分數權重表**:
*   `firstRingFoodScores`: `[0, 8, 14, 19, 22, 24, 25]` (隨食物產出遞增)。
*   `firstRingProdScores`: `[0, 10, 16, 20, 20, 12, 0]` (生產力 3-4 時最高，過高會扣分，因為可能被山脈包圍)。

### 5.4 起始位置懲罰 (`closeStartPenalty`)
為了拉開玩家距離，地圖會生成一個懲罰矩陣：
*   $0$ 格: $-99$ 分 (禁止重疊)
*   $5$ 格: $-69$ 分 (太擠)
*   $10$ 格: $-12$ 分
*   $14$ 格: $0$ 分 (理想距離，兩座城市擴張三環後剛好不重疊)

---

## 6. 資源與自然奇觀放置
### 6.1 影響力地圖 (`Impact Map`)
為了防止資源分布過於密集或不均：
*   當放置一個**城市國家 (Minor Civ)** 時，會在其周圍 6 格範圍內放置一個 `MinorCiv Impact` (分數 99 $\rightarrow$ 遞減)。
*   奢侈品放置時會避開高 Impact 區域。

### 6.2 自然奇觀 (Natural Wonders)
*   **數量公式**: `num = mapRadius * naturalWonderCountMultiplier + addedConstant`。
*   **候選排序**: 將所有候選奇觀按「可用地塊數量」由少到多排序，**先放稀有奇觀**，防止其地塊被普通奇觀佔用。
*   **黑名單區域**: 每個奇觀生成後，其周圍 `height / 5` 距離內的格點會進入黑名單，禁止生成另一個奇觀。

---

## 7. 最終規範化 (`TileNormalizer`)
這是最後一道保險，用於解決以下衝突：
*   **淡水修復**: 如果一條河穿過沙漠，標記該沙漠為「有水源」。
*   **特徵清理**: 如果生成了自然奇觀，移除其格點上原有的森林、資源或改善設施。
*   **山脈修正**: 確保山脈地塊上沒有不該出現的植被（除非 Mod 特別定義）。

---

## 8. 虛擬碼：核心生成迴圈
```kotlin
fun generateMap() {
    // 1. 創世紀
    MapLandmassGenerator.generate() 
    
    // 2. 注入氣候與植被
    applyHumidityAndTemperature()
    spawnVegetation() // Perlin 基於濕度分配森林/叢林
    
    // 3. 塑造山河
    MapElevationGenerator.raise()
    RiverGenerator.spawn()
    
    // 4. 公義的審判 (區域劃分)
    regions = MapRegions.generate(numPlayers)
    for (r in regions) {
        r.startPosition = findBestStartWithScoringTables(r)
    }
    
    // 5. 資源點綴
    placeNaturalWonders()
    LuxuryResourcePlacementLogic.place()
    StrategicResourcePlacementLogic.place()
    
    // 6. 最終整理
    TileNormalizer.normalize()
}
```
