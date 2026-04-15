# 動態世界物件與環境控制 (Dynamic World & Environment)

如何讓你的 Mod 對整個遊戲世界產生實質性的「動態影響」？

## 1. 動態圖示切換 (`DrawGraphic`)
在大地圖上，`WorldObject` 的外觀並不是靜態的。
*   **重寫 `DrawGraphic`**: 你可以根據物件內部的數據（如：能量、損壞程度、時間）來決定返回哪張 `Texture2D`。
*   **用途**: 顯示一個正在建造的據點、一個逐漸發光的傳送門、或是一個正在冒煙的火山。

## 2. 全域環境控制 (`GameCondition`)
如果你想改變天氣、溫度或光照，應使用 `GameCondition`。
*   **定義**: `GameConditionMaker.MakeCondition(def, duration)`。
*   **範圍**: 
    *   `Map.gameConditionManager`: 只影響特定地圖。
    *   遍歷 `Find.Maps`: 影響所有當前玩家載入的地圖（實現「全球性事件」）。

## 3. 數據驅動的變動 (`Tick`)
*   **WorldObject.Tick**: 在大地圖上執行慢速計算（如：每隔幾天改變一次狀態）。
*   **ThingComp.CompTick**: 在本地地圖上執行即時計算（如：祭壇的發光特效）。

## 4. 數據持久化
當你的 `WorldObject` 具有動態狀態（如：`energyLevel`）時，務必在 `ExposeData` 中進行保存，否則存檔後數據會重置。

---
*由 Gemini CLI 分析 RimWorld 世界物件與遊戲環境系統生成。*
