# AI 機制深度解構 (AI System Deep Dive)

Millénaire 的 AI 是一個**基於狀態與目標優先級的決策引擎**。

## 1. 決策三部曲
每個村民實體 (`MillVillager`) 在每個行為週期都會執行以下邏輯：

### A. 候選過濾 (`isPossible`)
AI 會遍歷所有已註冊的 `Goal`。
- **特定條件檢查：** 例如 `GoalConstructionStepByStep` 會檢查村莊是否有正在進行的建築工程 (`ConstructionIP`)。
- **資源檢查：** 檢查村民背包是否有所需的材料。
- **時間與環境：** 某些目標僅在白天或特定天氣下觸發。

### B. 優先級競爭 (`priority`)
如果多個目標都可能執行，系統會計算分值：
- **基礎分：** 每個目標有預設權重。
- **動態加成：** 
    - 如果村莊極度缺乏木材，伐木目標的優先級會提升。
    - 如果村民快餓死了，進食目標的優先級會強制置頂。

### C. 行為執行 (`performAction`)
一旦目標被選中，村民會進入 `actionDuration` (動作持續時間)。
- **工具效率影響：** 根據 `OldSource/java/org/millenaire/common/goal/GoalConstructionStepByStep.java`，村民會檢查手中的工具（如鏟子）的等級，從而縮短或延長放置方塊的時間（7 到 16 ticks 不等）。

## 2. 動作的細節
- **持有物同步 (`getHeldItems`)：** 為了視覺效果，AI 會根據當前目標讓村民手中拿起對應的方塊或工具。
- **路徑尋找配置 (`getPathingConfig`)：** 建築 AI 會使用 `JPS_CONFIG_BUILDING`，這比普通行走更精確，且能處理腳手架 (`scaffoldings`)。

## 3. 實作留檔位置
- **核心框架：** `OldSource/java/org/millenaire/common/goal/Goal.java`
- **行為循環：** `OldSource/java/org/millenaire/common/entity/MillVillager.java` 中的 `updateAITasks()` 相關邏輯。
