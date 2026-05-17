# Unciv 地圖生成演算法詳解

Unciv 的地圖生成是一個多階段、確定性的過程，主要由 `MapGenerator` 類別控制。它結合了程序化內容生成 (PCG) 的多種技術，如 Perlin 噪聲、區域平衡演算法等。

## 1. 地圖生成總體流程 (The Pipeline)

生成過程嚴格遵循以下步驟：
1.  **Landmass Generation**: 決定陸地與海洋的分佈。
2.  **Climate Simulation**: 計算每個地塊的濕度 (Humidity) 與溫度 (Temperature)。
3.  **Terrain Assignment**: 根據氣候參數分配基本地形（沙漠、草原、苔原等）。
4.  **Elevation Generation**: 提升地形產生山脈與丘陵。
5.  **Feature Spreading**: 分散生成河流、植被（森林、叢林）與特殊地貌（綠洲、沼澤）。
6.  **Region Balancing**: 劃分文明起始區域，並確保資源分配的公平性。
7.  **Resource & Start Placement**: 放置資源、自然奇觀與玩家起始位置。

---

## 2. 陸地生成 (Landmass Generation)
`MapLandmassGenerator.kt` 根據不同的 `MapType` 採用不同策略：
-   **Pangaea/Continents**: 使用 **Perlin Noise** 生成初步海拔，並疊加一個**橢圓衰減函數 (Elliptic Continent function)**。這能確保地圖中心更有可能是陸地，而邊緣則是海洋。
-   **Fractal/Perlin**: 純粹基於分形或噪聲生成，不強制中心陸地。
-   **Water Threshold**: 透過調整一個全域的「水位線」來控制陸地比例。若生成的陸地佔比不符合預期（如太少），系統會自動下調水位線並重試。

---

## 3. 氣候與生物群系 (Climate & Biomes)
地圖的視覺多樣性源於 `applyHumidityAndTemperature` 函數：
-   **溫度 (Temperature)**: 
    -   基礎溫度由**緯度 (Latitude)** 決定（赤道熱，兩極冷）。
    -   疊加一層 Perlin 噪聲來模擬洋流或氣候擾動帶來的局部溫差。
-   **濕度 (Humidity)**: 完全由一組獨立的 Perlin 噪聲生成。
-   **地形匹配 (Terrain Picker)**: 
    -   系統維護一個 `baseTerrainPicker`。
    -   每個地形定義（如沙漠）都有其適合的溫度/濕度區間。例如：高溫低濕 = 沙漠；中溫高濕 = 草原。

---

## 4. 區域平衡與起始點 (`MapRegions.kt`)
這是 4X 遊戲最關鍵的部分，確保玩家起始位置不會過於惡劣：
-   **Impact Map**: 系統會建立一個「影響力地圖」，標註哪些地塊靠近水源、哪些地塊產出高。
-   **Starting Location Filters**: 
    -   起始點必須滿足最小食物 (`minimumFoodForRing`) 與產出 (`minimumProdForRing`) 要求。
    -   使用 `closeStartPenalty` 演算法，確保文明之間有足夠的擴張空間（通常至少 14 格距離）。
-   **偏好偏置 (Bias)**: 某些文明（如俄羅斯偏好苔原，阿拉伯偏好沙漠）會影響其起始點的選擇權重。

---

## 5. 資源分配
資源分配分為兩個層次：
1.  **策略性資源 (Strategic)**: 根據區域需求分配，確保每位玩家附近都有基礎資源（如馬、鐵）。
2.  **奢侈品資源 (Luxury)**: 
    -   採用區域群聚原則。同一區域傾向於擁有相同的奢侈品，以鼓勵玩家間的貿易。
    -   使用 `LuxuryResourcePlacementLogic` 控制資源密度。

## 6. 技術細節總結
-   **確定性**: 給定相同的種子碼 (Seed)，地圖生成結果完全一致。
-   **高度可模組化**: 所有的地形、資源生成條件都定義在 `Ruleset` (JSON) 中，AI 或生成器只是讀取這些條件。
-   **效能優化**: 在處理大量地塊時，大量使用 `asSequence()` 進行延遲計算，並在複雜步驟中加入協程支援以避免介面卡死。
