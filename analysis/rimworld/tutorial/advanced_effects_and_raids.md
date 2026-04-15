# 高階視覺效果與動態襲擊觸發 (Advanced Effects & Raids)

如何讓你的 Mod 更有「史詩感」與「生存壓力」？

## 1. 視覺與震動效果 (Screen Shake & Flecks)
RimWorld 提供了內建的相機與粒子系統：
*   **Camera Shake**: `Find.CameraDriver.shaker.DoShake(magnitude)`。幅度 1.0f 已經是非常強烈的震動。
*   **Fleck 系統**: 1.4+ 版本替代 Mote 的高效粒子系統。
    *   `FleckMaker.Static(pos, map, fleckDef, scale)`：在特定位置生成靜態特效。
    *   `FleckDefOf.PsycastAreaEffect`: 一種藍色的擴散光圈。
*   **音效播放**: `SoundDefOf.SoundName.PlayOneShotOnCamera(map)`。

## 2. 定時襲擊觸發器 (`MapComponent`)
當你想在特定的「臨時地圖」中實施生存限制時，`MapComponent` 是最佳載體。
*   **追蹤時間**: 使用 `MapComponentTick` 累加一個 `int ticks` 計數器。
*   **效能優化**: 使用 `IsHashIntervalTick(250)` 每 4 秒左右檢查一次，而不是每一幀。
*   **觸發襲擊**: 手動建構 `IncidentParms` 並呼叫 `IncidentDefOf.RaidEnemy.Worker.TryExecute(parms)`。

## 3. 動態難度縮放
你可以透過 `StorytellerUtility.DefaultThreatPointsNow(map)` 獲取當前地圖的「標準威脅點數」，並乘上一個倍數（如 1.5x），讓襲擊強度隨著玩家的發展而動態調整。

## 4. 數據持久化
當你的 `MapComponent` 包含計時器 (`ticksSinceArrival`) 或標記位 (`raidTriggered`) 時，務必在 `ExposeData` 中保存它們。

---
*由 Gemini CLI 分析 RimWorld 特效系統與事件觸發機制生成。*
