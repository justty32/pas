# AI 目標驅動系統深度分析

## 1. 目標 (Goal) 邏輯拆解 (參考 `OldSource/java/org/millenaire/common/goal/`)
- **核心基類：** `Goal.java` (定義 `isPossible`, `priority`, `perform` 循環)。
- **建設邏輯：** `GoalConstructionStepByStep.java` (建築的核心推進 AI)。
- **資源採集：** `GoalLumbermanChopTrees.java` (包含掃描樹木與植樹邏輯)。
- **睡眠行為：** `GoalSleep.java` (處理 NPC 在建築內的床鋪定位)。

## 2. NPC 實體數據 (參考 `OldSource/java/org/millenaire/common/entity/EntityMillVillager.java`)
- **數據存儲：** 使用 NBT 儲存職業、家族、背包 (`writeCustomDataToNbt`)。
- **對話系統：** 整合在實體邏輯中，從 `OldSource/todeploy/millenaire/languages/` 讀取。

## 3. 路徑尋找 (Pathfinding)
- **參考實作：** `OldSource/java/org/millenaire/common/pathing/`。
- **1.21.8 挑戰：** 需將 `net.minecraft.entity.ai.pathing.EntityNavigation` 與 Millénaire 的路徑權重（如道路方塊加成）結合。
