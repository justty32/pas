# 劇情驅動：任務與大地圖點位的動態生成

如何製作一個像原版「飛船降落」或「尋寶任務」那樣的功能？

## 1. 核心流程
1.  **計時器 (`WorldComponent`)**: 監聽遊戲時間。
2.  **尋址 (`TileFinder`)**: 在玩家基地附近尋找合適的地塊。
3.  **發布任務 (`QuestGen`)**: 使用 C# 將參數傳入 XML 腳本並啟動。
4.  **生成點位 (`SpawnWorldObject`)**: 在指定地塊生成大地圖物件。

## 2. 尋找鄰近地塊的技巧
使用 `TileFinder.TryFindPassableTileWithTraversalDistance` 是最推薦的做法：
*   它保證了找到的地塊是 **可抵達的** (Passable)。
*   它允許設定距離範圍（例如：距離基地 2 到 10 格）。
*   比起隨機選點，這能保證任務地點不會出現在海洋或無法逾越的山脈中。

## 3. C# 與 XML 任務的串聯
*   **Slate**: C# 中的 `Slate.Set("variableName", value)` 對應 XML 中的 `[variableName]`。
*   這是將「動態計算結果」傳遞給「靜態腳本」的橋樑。

## 4. 數據保存與一次性執行
*   使用 `WorldComponent.ExposeData` 儲存一個 `bool questFired` 標籤。
*   這能防止玩家每次讀檔後，任務都會重新觸發一次。

---
*由 Gemini CLI 分析 RimWorld 任務與世界物件系統生成。*
