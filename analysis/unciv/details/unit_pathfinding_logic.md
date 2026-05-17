# Unciv 單位尋路機制深度剖析：AStar 與移動邏輯

Unciv 的尋路系統是一個高度優化的多層次架構，旨在解決六角格地圖上複雜的「跨回合」路徑規劃問題。

---

## 1. 核心組件架構

尋路邏輯主要分佈在以下檔案：
- **`AStar.kt`**: 標準的 A* 演算法實作，用於通用權重圖搜索。
- **`MovementCost.kt`**: 定義單位與地塊間的移動成本計算邏輯（地形、道路、ZOC）。
- **`PathingMap.kt` & `PathingMapAStarPathfinder.kt`**: 針對遊戲專門優化的尋路器，支援「多回合」與「定點數運算 (FixedPoint)」。
- **`RouteNode.kt`**: 使用 bit-packing 將每個地塊的尋路狀態（回合數、剩餘移動力、父節點）壓縮進一個 `Long`。

---

## 2. 移動成本模型 (Movement Cost)

在 `MovementCost.getMovementCostBetweenAdjacentTiles` 中，移動成本被定義為 `Float`，具有以下特點：

### 2.1 基礎地形與道路
- **道路/鐵路**：顯著降低移動成本（例如鐵路僅需 0.1）。
- **地形成本**：從 `Tile.lastTerrain.movementCost` 取得。城市中心固定為 1。
- **雙倍移動 (Double Movement)**：具有特定天賦的單位（如偵察兵在森林）成本減半。

### 2.2 特殊懲罰與限制
- **消耗所有移動力 (100f)**：
    - **河流**：除非有特定科技，否則跨越河流會直接耗盡當前回合移動力。
    - **ZOC (Zone of Control)**：從敵方單位的 ZOC 範圍移動到另一個 ZOC 範圍。
    - **崎嶇地形懲罰**：某些單位進入丘陵/森林會耗盡移動力。
- **敵方懲罰**：如「長城」奇觀會對敵方單位施加額外移動成本。

---

## 3. 多回合尋路演算法 (Multi-turn A*)

Unciv 尋路最精妙之處在於它不是計算「距離」，而是計算「回合數」。

### 3.1 核心邏輯 (PathingMapAStarPathfinder)
演算法在計算鄰居節點時，會判斷是否需要跨越回合：
- **同回合移動**：如果 `當前回合已用 + 移動成本 <= 總移動力`。
- **跨回合移動**：如果成本超過剩餘移動力，演算法會模擬「在當前格結束回合」，並在下一回合以全滿移動力出發。
- **「一格必達」規則**：在《文明》機制中，只要還有移動力（哪怕只有 0.1），就能進入任何合法的相鄰地塊。Unciv 透過將超支的移動力計入下一回合來實作此邏輯。

### 3.2 啟發式函數 (Heuristic)
```kotlin
val minRemainingCost = tileRoadCost(tile) + (minRemainingTiles - 1) * (FASTEST_ROAD_COST)
val underestimatedTotal = movementSoFar + minRemainingCost
```
啟發式函數假設剩餘路徑全部由「鐵路」組成，確保這是一個 **Admissible Heuristic**（絕不高估成本），從而保證 A* 找到的是最優解。

---

## 4. 效能優化手段

### 4.1 定點數運算 (FixedPointMovement)
為了避免浮點數精度導致的跨平台同步問題與效能損耗，Unciv 使用 `FixedPointMovement` 進行計算。
- `FPM_ONE` 代表 1.0 的內部整數表示。
- 鐵路成本 `0.1f` 會轉換為對應的定點數。

### 4.2 狀態壓縮 (RouteNode)
尋路過程中的中間數據（G-score, Parent, Turns）不以對象形式存儲，而是壓縮在一個 `LongArray` 中。
- **低位**：父節點索引。
- **中位**：已用移動力、回合數。
- **高位**：受損狀態（如穿越山脈次數）。

### 4.3 緩存機制 (PathingMapCache)
`PathingMap` 會緩存特定起點的尋路結果。當同一個單位在同一回合內多次請求路徑（例如 AI 評估多個目標）時，可以直接從緩存提取已探索的 `RouteNode`。

---

## 5. 總結：尋路管線

1.  **初始化**：根據單位屬性（海/陸、天賦、ZOC 忽略）建立 `PathingMap`。
2.  **擴張**：A* 從起點開始，優先展開「估計總回合數」最小的節點。
3.  **評估**：對每個鄰居調用 `MovementCost` 計算 FixedPoint 成本，並根據剩餘移動力決定是否 `turn++`。
4.  **回溯**：到達目標後，通過 `RouteNode` 儲存的父節點索引快速回溯出 `List<Tile>`。

---
*原始碼位置參考：*
- `com.unciv.logic.map.AStar`
- `com.unciv.logic.map.mapunit.movement.MovementCost`
- `com.unciv.logic.map.PathingMapAStarPathfinder`
