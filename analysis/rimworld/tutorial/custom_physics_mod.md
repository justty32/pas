# 實作自定義物理系統：燃油加熱器 (Fuel Heater)

本教程展示如何結合 RimWorld 的燃料、溫控與物理循環系統。

## 1. 架構思路
在 RimWorld 中，物理系統通常由多個 `ThingComp` 協作完成。
*   **數據獲取**: 在 `PostSpawnSetup` 中使用 `parent.GetComp<T>()` 來獲取同一物體上的其他組件。
*   **物理動作**: 使用 `GenTemperature.PushHeat` 或是 `GenTemperature.ControlTemperatureTempChange` 來修改環境數值。
*   **資源消耗**: 呼叫 `CompRefuelable.ConsumeFuel`。

## 2. 關鍵技術：溫控邏輯
`GenTemperature.ControlTemperatureTempChange` 是一個非常有用的方法：
1.  它會檢查目標單元格的目前溫度。
2.  它會根據你提供的 `energyLimit` 計算本幀應產生的熱量。
3.  它會確保不會讓溫度超過 `targetTemperature`。

## 3. 代碼實作要點
*   **Tick 頻率**: 物理計算通常不需要每幀執行。如果對效能有要求，可以使用 `CompTickRare` (每 250 Ticks 執行一次)。
*   **HashIntervalTick**: 使用 `parent.IsHashIntervalTick(interval)` 可以讓不同物體的 Tick 分散開來，避免在同一幀出現計算高峰。

## 4. XML 配對 (示範)
在 XML 中，你需要為你的建築添加三個組件：
```xml
<comps>
  <li Class="RimWorld.CompProperties_Refuelable">
    <fuelCapacity>50</fuelCapacity>
    <fuelFilter><thingDefs><li>WoodLog</li></thingDefs></fuelFilter>
  </li>
  <li Class="RimWorld.CompProperties_TempControl">
    <energyPerTick>16</energyPerTick>
  </li>
  <li Class="MyMod.CompProperties_FuelHeater" /> <!-- 你的自定義組件 -->
</comps>
```

---
*由 Gemini CLI 分析 RimWorld 溫控與燃料系統生成。*
