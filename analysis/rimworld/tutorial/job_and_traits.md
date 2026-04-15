# 任務系統與特性干涉 (Job & Traits)

## 1. 任務執行四部曲
1.  **Job (數據)**: `targetA`, `count` 等數據容器。
2.  **JobDriver (邏輯)**: 定義 `MakeNewToils()`，將任務拆解為步驟。
3.  **Toil (動作)**: 最小執行單位，包含 `initAction` (開始) 和 `tickAction` (持續)。
4.  **JobTracker (調度)**: 負責驅動 `DriverTick()` 並處理 `ThinkTree` 發出的中斷請求。

## 2. 特性 (Traits) 如何影響 Job
*   **硬性攔截**: 透過 `disabledWorkTags` 讓 `WorkGiver` 找不到工作（例如：抗拒暴力）。
*   **效率修正**: 透過 `StatModifier` 影響 `Toil` 的執行速度（例如：勤奮增加工作速度）。
*   **行為觸發**: 透過 `MentalStateGiver` 強制插入 Job（例如：縱火狂觸發放火任務）。

---
*由 Gemini CLI 分析 Verse.AI 與 RimWorld.TraitDef 生成。*
