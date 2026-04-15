# 村民行為 AI 深度分析 (NPC Behavior & AI)

Millénaire 的 AI 系統是其靈魂所在。它不依賴 Minecraft 原生的 AI 任務隊列，而是使用一套自定義的「目標驅動」系統。以下分析基於 `OldSource/java/org/millenaire/common/goal/Goal.java`。

## 1. 目標 (Goal) 的核心邏輯
每個 `Goal` 類別都必須實作以下三個關鍵方法：
- **`isPossible(MillVillager villager)`**: 
    - 邏輯判斷：現在是白天嗎？村民有工具嗎？村莊需要這個資源嗎？
    - 如果返回 `false`，該目標將被排除。
- **`priority(MillVillager villager)`**:
    - 動態權重：例如，如果村民快餓死了，`GoalEat` 的優先級會變得極高；如果村莊正在建設，搬運建材的優先級會提升。
- **`perform(MillVillager villager)`**:
    - 執行行為：包括移動、播放動畫、操作方塊、音效觸發。

## 2. 決策循環 (Decision Cycle)
村民每隔一段時間（通常是 2 秒，即 `STANDARD_DELAY`）會執行一次決策：
1. **收集候選目標**: 從該村民職業可執行的目標池中，篩選出所有 `isPossible()` 為真的目標。
2. **計算最高優先級**: 比較候選目標的 `priority()`。
3. **切換目標**: 如果新目標不同於當前目標，則執行切換並重置行為計數器。

## 3. 行為執行細節
- **`GoalInformation`**: 封裝了行為所需的目標點 (`dest`)、目標建築 (`destBuildingPos`) 與目標實體 (`targetEnt`)。
- **路徑尋找 (Pathfinding)**: 
    - 使用 A* 算法，但針對不同場景有不同的配置 (`AStarConfig`)。
    - `JPS_CONFIG_BUILDING`: 用於室內精確定位。
    - `JPS_CONFIG_CHOPLUMBER`: 用於戶外寬泛範圍尋找樹木。
- **動畫與互動**: 透過發送封包 (`MillNetworking`) 同步行為動畫（如敲打方塊的聲音與動作）。

## 4. 移植到 1.21.8 的挑戰
- **Fabric AI**: 需要決定是將這套系統嵌入到 Minecraft 的 `Brain` 系統，還是完全獨立運行。
- **效能控制**: 大規模村莊中的 A* 計算非常消耗資源，需要實作異步路徑尋找或分時段計算。
- **狀態同步**: 1.21.8 的網路載荷比舊版更嚴格，需要為每個 Goal 的行為設計專屬的 Payload。
