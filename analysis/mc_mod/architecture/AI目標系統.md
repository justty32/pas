# AI 目標驅動系統

Millénaire 的 NPC 不使用 Minecraft 原生的簡單 Task，而是基於一套高度複雜且互相關聯的「目標」(Goal) 系統。

## 🧠 目標體系 (參考 `OldSource/java/org/millenaire/common/goal/`)
- **`Goal` 基類：** `OldSource/java/org/millenaire/common/goal/Goal.java` (優先級、觸發條件及邏輯)
- **具體目標實作：**
    - **建設類：** `OldSource/java/org/millenaire/common/goal/GoalConstructionStepByStep.java`
    - **採集類：** `OldSource/java/org/millenaire/common/goal/GoalLumbermanChopTrees.java`
    - **生存類：** `OldSource/java/org/millenaire/common/goal/GoalSleep.java`
    - **交易類：** `OldSource/java/org/millenaire/common/goal/GoalBeSeller.java`

## 🚶 NPC 實體與渲染
- **實體註冊：** `src/main/java/me/devupdates/millenaireReborn/common/registry/MillEntities.java`
- **實體邏輯：** `OldSource/java/org/millenaire/common/entity/EntityMillVillager.java` (數據持久化與個體屬性)
- **渲染與模型：** `OldSource/java/org/millenaire/client/render/` (參考舊版渲染與模型定義)

## 📅 移植難點分析
- **實體導航：** 需適應 1.21.8 的 `net.minecraft.entity.ai.pathing` 系統。
- **目標適配：** 將 `OldSource` 中的 `Goal` 邏輯封裝為現代 Fabric 的 AI Task。
