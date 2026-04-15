# 位置與座標系統深度分析 (Point System)

在 Millénaire 中，幾乎所有的邏輯（建築、路徑尋找、任務、貿易）都圍繞著一個核心類別：`Point`。

## 1. 核心職責
- **標識唯一性**：村莊中的每個建築都以其「中心點」(`Point`) 作為唯一的 Key 存儲在 `MillWorldData` 中。
- **距離計算**：提供了優化的 `distanceTo` 與 `distanceToSq` 方法，用於 AI 判斷目標是否在可及範圍內。
- **序列化**：`Point` 實作了簡單的序列化，方便存儲在 NBT 或透過網路封包傳送。

## 2. 座標轉換
- **相對座標與絕對座標**：建築藍圖 (`BuildingPlan`) 使用相對座標 (0,0,0)，而 `Point` 負責將其與村莊中心結合，轉換為 Minecraft 的絕對世界座標。
- **IntPoint 與精確度**：模組通常使用整數座標 (`IntPoint`) 來定位方塊，但在處理 NPC 移動時會使用精確的雙精度浮點數。

## 3. 原始碼與移植位置
- **1.12.2 位置**：`OldSource/java/org/millenaire/common/utilities/Point.java`
- **1.21.8 位置**：`src/main/java/me/devupdates/millenaireReborn/common/util/Point.java`
    - *註：新版已實作基礎的 3D 座標與距離計算。*
