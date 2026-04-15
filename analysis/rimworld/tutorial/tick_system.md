# RimWorld Tick 系統：遊戲的心跳 (Tick System)

Tick 是 RimWorld 所有模擬與 AI 運行的基礎引擎。

## 1. 時間換算表
*   **1 Tick**: 1/60 秒 (正常速度)。
*   **2,500 Ticks**: 遊戲內 1 小時。
*   **60,000 Ticks**: 遊戲內 1 天。
*   **60,000,000 Ticks**: 現實世界 277 小時。

## 2. 三種頻率的 `CompTick`
在編寫 `ThingComp` 時，你可以重寫三種不同的 Tick 方法：
*   **`CompTick`**: 每幀呼叫。用於處理即時物理、動畫或導彈。
*   **`CompTickRare`**: 每 250 幀呼叫。最推薦的場景：溫度、腐爛、需求檢查。
*   **`CompTickLong`**: 每 2,000 幀呼叫。用於處理電力網合並、大地圖位置更新。

## 3. 效能優化秘訣：`IsHashIntervalTick`
永遠不要在 `CompTick` 裡手動寫 `if (counter % 60 == 0)`。
使用 `parent.IsHashIntervalTick(60)`，它會根據物體的 ID 自動分散計算幀，保證遊戲 TPS (Ticks Per Second) 的穩定。

## 4. 關鍵類別
*   **`Verse.TickManager`**: 控制遊戲暫停、快進與跳幀。
*   **`Find.TickManager.TicksGame`**: 獲取從開局到現在的總 Ticks。

---
*由 Gemini CLI 分析 Verse.TickManager 生成。*
