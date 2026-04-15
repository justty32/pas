# RimWorld 角色行為系統深度解析

這份文件深入探討 Pawn 如何「思考」與「行動」，這對於開發行為類 Mod 至關重要。

## 1. 核心流程圖
`Pawn_Tick` -> `Pawn_JobTracker.JobTrackerTick` -> (如果沒事做) -> `ThinkTree` -> `JobGiver` -> `Job` -> `JobDriver` -> `Toils`.

## 2. 深入 JobDriver (執行層)
`JobDriver` 是行為 Mod 的靈魂。它本質上是一個 **狀態機 (State Machine)**。

### 關鍵方法：`MakeNewToils()`
這是你必須重寫的方法。你需要在這裡定義一系列 `Toil` 物件。
```csharp
protected override IEnumerable<Toil> MakeNewToils()
{
    // 1. 預約目標（防止別人搶走）
    yield return Toils_Reserve.Reserve(TargetIndex.A);

    // 2. 走過去
    yield return Toils_Goto.GotoThing(TargetIndex.A, PathEndMode.Touch);

    // 3. 執行動作（例如等待 100 Ticks 並播放動畫）
    Toil work = new Toil();
    work.tickAction = () => {
        pawn.rotationTracker.FaceCell(TargetA.Cell);
        // 這裡可以寫每 Tick 的邏輯
    };
    work.defaultCompleteMode = ToilCompleteMode.Delay;
    work.defaultDuration = 100;
    yield return work;

    // 4. 結束動作
    yield return Toils_General.Do(() => {
        Log.Message("動作完成！");
    });
}
```

## 3. 預約系統 (ReservationManager)
RimWorld 使用預約系統來避免資源競爭。
*   如果你的 JobDriver 沒有呼叫 `Reserve()`，兩個 Pawn 可能會同時走去搬同一個箱子，導致其中一個到達時報錯。
*   **代碼位置**: `Verse.ReservationManager`。

## 4. 工作給予者 (WorkGiver)
`WorkGiver` 負責將「地圖上的某個東西」轉換為一個「Job」。
*   `PotentialWorkThingsGlobal()`: 返回地圖上所有可能的工作對象（效能開銷大）。
*   `HasJobOnThing(pawn, thing)`: 判斷該角色是否能對該物體執行任務（例如：技能等級夠嗎？）。

## 5. 精神狀態 (MentalState)
當 Pawn 崩潰時，`MentalStateHandler` 會推入一個 `MentalState`。這會短路（Short-circuit）正常的思考樹，讓 Pawn 只執行崩潰相關的 Job。

## 6. Mod 開發實戰建議
1.  **想增加新行為？** 寫一個新的 `JobDriver`。
2.  **想讓 Pawn 自動去做某事？** 寫一個 `WorkGiver` 並在 XML 中關聯。
3.  **想修改原版行為？** 使用 **Harmony** 補丁攔截 `JobDriver.MakeNewToils` 並插入你自己的 Toil。

---
*這份文件是由 Gemini CLI 透過分析 Verse.AI 命名空間生成的深度報告。*
