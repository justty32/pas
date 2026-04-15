# RimWorld AI 系統 (Jobs, Toils & ThinkTrees)

RimWorld 的 AI 採用了「思考樹 (ThinkTree)」與「任務隊列 (Job Queue)」相結合的模式。

## 1. 思考層級 (ThinkTree)
Pawn 決定要做什麼的過程是由 `ThinkTree` 驅動的。
*   **ThinkNode**: 思考樹的節點。
*   **JobGiver**: 特殊的 ThinkNode，負責在滿足條件時返回一個 `Job`。
*   **優先級**: 思考樹從上到下掃描，第一個返回有效 Job 的節點將被執行（例如：先檢查「是否在著火」，再檢查「是否飢餓」，最後才是「休閒工作」）。

## 2. 任務與執行 (Job & JobDriver)
一旦 `ThinkTree` 決定了 Job，就需要 `JobDriver` 來執行它。
*   **Job**: 數據容器，包含 `JobDef`、目標 (LocalTargetInfo) 和配置。
*   **JobDriver**: 邏輯執行器。負責將一個複雜的 Job 拆解為多個原子化的 **Toils**。
    *   例如 `JobDriver_Mine` 會拆解為：`Goto` -> `Wait (挖掘動畫)` -> `完成/循環`。

## 3. 原子動作 (Toil)
`Toil` 是 Pawn 行為的最小單位。
*   **屬性**:
    *   `initAction`: 開始時執行一次。
    *   `tickAction`: 每 Tick 執行。
    *   `defaultCompleteMode`: 如何結束此步驟（如 `PatherArrival`, `Delay`, `Instant`）。
*   **Toil 工廠**: `Toils_Goto`, `Toils_Haul`, `Toils_General` 等靜態類別提供了大量預設的 Toils。

## 4. 群體行為 (Lord)
當多個 Pawn 需要協同工作時（如襲擊、商隊、派對），遊戲會創建一個 `Lord`（領主）。
*   **LordJob**: 定義群體的目標。
*   **LordToil**: 群體的當前狀態（如「正在聚集」、「正在進攻」）。
*   **Transition**: 狀態切換的條件（如「一半人受傷時撤退」）。

## 5. Mod 開發建議
*   **添加新工作**: 
    1.  XML 定義 `JobDef` 和 `WorkGiverDef`。
    2.  C# 撰寫 `WorkGiver` 類別（用於發現 Job）。
    3.  C# 撰寫 `JobDriver` 類別（用於執行 Job）。
*   **修改 AI 優先級**: 透過 XML Patch 修改 `ThinkTreeDef`。

---
*這份文件是由 Gemini CLI 透過分析 Verse.AI 產生的分析報告。*
