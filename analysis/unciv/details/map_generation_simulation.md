# Unciv 深度剖析專題四：地圖生成的生物與地質模擬

## 1. 創世流水線 (The Generation Pipeline)
Unciv 的地圖生成遵循一套嚴謹的順序，每一步都為下一步奠定物理基礎。

1.  **陸塊生成 (MapLandmassGenerator)**: 確定陸地與海洋的初步輪廓。
2.  **氣候模擬 (applyHumidityAndTemperature)**: 為每個地塊分配溫度與濕度數值。**這是核心步奏。**
3.  **地勢抬升 (MapElevationGenerator)**: 根據地質邏輯生成山脈與丘陵。
4.  **水文模擬 (Lakes, Coasts, Rivers)**: 生成湖泊、海岸線與河流系統。
5.  **植被覆蓋 (Vegetation)**: 根據氣候參數種植森林與叢林。
6.  **資源分佈 (Resources)**: 在最後階段進行平衡與資源投放。

---

## 2. 氣候矩陣：溫度與濕度 (The Climate Matrix)
Unciv 不直接隨機生成「沙漠」或「草原」，而是透過 `TerrainOccursRange` 進行氣候模擬。

### A. 溫度模擬 (Temperature)
- **緯度影響**: 溫度隨緯度變化（從赤道到兩極）。
- **隨機擾動**: 引入 Perlin 噪聲模擬洋流與局地氣候差異。
- **海拔修正**: 高海拔地塊（山脈）會強制降低溫度。

### B. 濕度模擬 (Humidity)
- **水源距離**: 靠近海洋、湖泊或河流的地塊具有更高的濕度值。
- **地形阻擋**: 雖然 Unciv 簡化了雨影效應，但依然透過噪聲模擬降水分佈。

### C. 氣候匹配邏輯
每個地形（Terrain）在 `UniqueType.TileGenerationConditions` 中定義了其「適存範圍」。
- **範例**: 森林可能要求 `溫度 [-0.5, 0.5]` 且 `濕度 [0.4, 1.0]`。
- **雪地**: 當 `溫度 <= -0.5` 且 `濕度 >= -0.1` 時，系統會優先判定為雪地。

---

## 3. 地質抬升與水文 (Geology & Hydrology)
### A. 山脈生成 (Elevation)
- **鏈式與組群**: 透過 `UniqueType.OccursInChains` 模擬褶皺山脈，`OccursInGroups` 模擬高原。
- **火山與稀有地形**: 透過 `spawnRareFeatures` 投放，通常具有嚴格的地質限制。

### B. 河流系統 (RiverGenerator)
- **路徑尋優**: 河流從高海拔流向低海拔，利用簡單的侵蝕模型決定路徑。
- **地塊加權**: 鄰近河流的地塊會獲得額外的「淡水」標記，進而影響後續的 `StartNormalizer`。

---

## 4. 資源投放與區域平衡 (Regional Balancing)
當地圖「實體」生成完成後，`MapRegions` 開始介入。

- **文明分佈**: 根據玩家數量將地圖劃分為「區域 (Regions)」。
- **資源聚合**: 奢侈資源不會隨機散佈，而是「成簇 (Clustered)」分佈。每個區域通常被分配 1-2 種主導奢侈品，以鼓勵玩家間的貿易。
- **戰略平衡**: 透過 `placeResourcesAndMinorCivs` 確保鐵、煤、石油等關鍵資源在各區域間具有統計學上的公平性。

---

## 5. 總結：數據驅動的地理學
Unciv 的地圖生成本質上是一個 **「約束滿足系統」**。
- **靈活性**: 所有的氣候參數都寫在 `UniqueType.kt` 的描述符中，這意味著 Mod 創作者可以輕易定義「炎熱多雨的荒漠」或「極寒的熱帶雨林」。
- **穩定性**: 透過固定 Seed 與 `randomness` 物件，保證了地圖生成在不同平台間的可重現性。

*本報告完成了對 Unciv 四大核心專題的深度剖析。*
