# RimWorld 物品生命週期 (Thing Lifecycle)

物品從數據定義到實體化，再到消亡的全過程。

## 1. 定義與實例
*   **ThingDef**: 靜態配置。
*   **Thing**: 遊戲運行的動態對象。由 `ThingMaker.MakeThing` 創建。

## 2. 三大階段
*   **Spawn (生成)**: 加入 `ListerThings` 與網格。此時觸發 `SpawnSetup`。
*   **Tick (運行)**: 
    *   `Tick`: 逐幀執行。
    *   `TickRare`: 每 250 幀。適合處理腐爛、惡化 (Deterioration) 等慢速邏輯。
*   **Destroy (銷毀)**: 當 `HitPoints <= 0` 時觸發。

## 3. 環境影響：惡化與腐爛
*   **Deterioration**: 當物品在室外、無屋頂且被雨淋時，耐久度會持續下降。
*   **Rotting**: 基於 `CompRottable`。受溫度影響：冰點以下暫停，高溫時加速。

## 4. 修改建議
*   **延緩腐爛**: 給物品增加 `CompRottable` 並設定其 `rotDestructionIfOutside`。
*   **銷毀副作用**: 重寫 `Thing.Destroy()` 方法，在物品被拆解或摧毀時產生物質或效果。

---
*由 Gemini CLI 分析 Verse.Thing 與 Verse.ThingMaker 生成。*
