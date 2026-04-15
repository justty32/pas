# RimWorld 溫控與熱力學 (Temperature)

遊戲透過熱量交換 (Equalization) 來模擬溫度。

## 1. 數據網格：`MapTemperature`
雖然玩家只看見房間溫度，但底層存儲在 `MapTemperature` 網格中。
*   **Outdoor**: 受 `SeasonalCycle` 影響。
*   **Room**: 地圖上的封閉空間。`Room.Temperature` 是計算小人舒適度的核心指標。

## 2. 設備組件：`CompTempControl`
*   ** Heaters & Coolers**: 繼承自 `CompTempControl`。
*   **邏輯**: 在 `CompTick` 中，系統會將電能轉化為熱能 (HeatPush)，並直接修改當前房間的能量總量。
*   **節能**: 當房間溫度達到設定值時，設備會進入低功耗模式。

## 3. 修改建議
*   **自定義散熱器**: 透過 `GenTemperature.PushHeat(cell, map, energy)` 在特定位置手動增加或減少熱量。
*   **極端氣候**: 修改 `MapCondition_HeatWave` 或 `ColdSnap` 的數值倍率。

---
*由 Gemini CLI 分析 Verse.GenTemperature 生成。*
