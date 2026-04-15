# AI 自動建築機制深度解析

這是 Millénaire 最具代表性的功能，由 `GoalConstructionStepByStep` 驅動。

## 1. 建築工程 (`ConstructionIP`)
- **定義：** 當村莊決定升級或新建房屋時，會建立一個 `ConstructionIP` (Construction In Progress) 對象。
- **原始碼：** `OldSource/java/org/millenaire/common/village/ConstructionIP.java`。

## 2. 逐方塊建設邏輯
在 `GoalConstructionStepByStep.java` 中：
1. **獲取下一個方塊：** 透過 `cip.getCurrentBlock()` 從藍圖列表中提取下一個待放置的方塊。
2. **計算路徑：** 村民會移動到該方塊的坐標。
3. **執行動作：**
    - 檢查是否有障礙物（如雜草、泥土）。
    - 如果是空氣，則從背包中扣除材料並放置方塊。
    - **動作時長：** 受工具效率影響（如 Phase 3 實作的 `MillCustomMaterials`）。

## 3. 資源獲取 (`GoalGetResourcesForBuild`)
建築 AI 不會無中生有。
- 村民必須先從村莊金庫 (`TownHall`) 領取藍圖所需的材料。
- 如果金庫沒錢或沒材料，建築工程會停滯，直到玩家提供或採集村民補足。

## 4. 1.21.8 的改良方向
- **分層放置：** 最佳化藍圖的掃描順序，確保建築從地基開始向上生長。
- **粒子效果：** 放置方塊時產生煙塵粒子，增加真實感。
- **原始碼位置：** `OldSource/java/org/millenaire/common/goal/GoalConstructionStepByStep.java`。
