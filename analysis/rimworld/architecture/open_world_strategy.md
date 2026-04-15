# RimWorld「開放世界 (Open World)」架構策略指南

RimWorld 原本的設計是「封閉地圖 (Local Map) + 宏觀世界 (World Map)」的雙層架構。要將其改造為「開放世界」（例如小人走到地圖邊緣直接無縫進入下一個地圖，或者同時渲染超大地圖），是一個極具挑戰但並非不可能的工程。

這份指南將分析原版架構的限制，並提供幾種可行的 Mod 開發策略。

## 1. 原版地圖與世界的轉換機制
要打破邊界，首先得了解原版是如何處理「離開地圖」的。

*   **ExitMapGrid (地圖邊界網格)**: 
    *   位於 `Verse.ExitMapGrid`。地圖邊緣的格子會被標記為可離開的區域。
*   **JobGiver_ExitMap / LordToil_ExitMap**: 
    *   當小人或商隊需要離開地圖時，AI 會賦予他們走到邊界格子的任務。
*   **CaravanExitMapUtility**: 
    *   當小人抵達邊界後，遊戲會將他們從當前 `Map` 中**銷毀 (De-spawn)**。
    *   然後，將他們封裝進一個 `Caravan` (商隊，屬於 `WorldObject`)，並轉移到 `WorldPawns` (世界虛擬人口) 中進行管理。
    *   在世界地圖上移動時，小人並不存在於任何具體的 `Map` 網格上，他們只是一組數學數據。

## 2. 開放世界改造策略

### 策略 A：無縫相鄰地圖切換 (Seamless Map Transition)
這是最主流且效能較可控的「開放世界」做法。當小人走到地圖東邊邊緣時，不進入世界地圖，而是直接生成/加載東邊相鄰板塊的地圖，並將小人傳送到新地圖的西邊邊緣。

**實作思路**:
1.  **攔截地圖離開邏輯**: 使用 Harmony Patch 攔截 `CaravanExitMapUtility` 或是邊緣走到 (`JobDriver_ExitMap`) 的邏輯。
2.  **查詢相鄰 Tile**: 透過 `Find.WorldGrid` 找出小人所在位置 (Tile ID) 的相鄰 Tile。
3.  **動態生成/加載地圖**: 
    *   呼叫 `MapGenerator.GenerateMap(tile, mapParent, mapSize)` 生成相鄰的地圖。
    *   或者從存檔中喚醒 (Load) 已存在的該板塊地圖。
4.  **跨地圖傳送**: 
    *   將小人從 `Map A` 進行 `De-spawn`。
    *   在 `Map B` 對應邊界的 `IntVec3` 座標呼叫 `GenSpawn.Spawn(pawn, loc, mapB)` 重新實體化小人。
5.  **多地圖並存 (Multi-Map)**: 
    *   遊戲本身就支援多個 Map 同時存在（就像你開啟了多個殖民地一樣）。你可以讓相鄰的地圖保持在 `Find.Maps` 列表中活躍。

### 策略 B：超大地圖擴張 (Mega-Map / Infinite Grid)
不切換地圖，而是直接將單一地圖的邊界無限擴大，或者在生成時就生成一個極大範圍 (例如 1000x1000) 的地圖。

**技術瓶頸與風險**:
*   **單執行緒限制**: RimWorld 的尋路 (`PathFinder`) 和視野計算 (`FogGrid`) 都是單執行緒的。超過 400x400 的地圖會讓遊戲在後期因尋路計算而出現嚴重卡頓（TPS 暴跌）。
*   **記憶體消耗**: 每個地圖的 `TerrainGrid`、`ThingGrid` 都是龐大的二維陣列。地圖面積增加一倍，記憶體消耗和遍歷成本增加四倍。
*   **建議**: **極度不推薦**。RimWorld 的引擎底層並不是為無縫加載的無限大地圖 (如 Minecraft 的 Chunk 系統) 設計的。所有的 `Lister` 和 `Grid` 都是地圖級別的全局陣列。

### 策略 C：區塊化模擬 (Chunk-based Simulation / Z-Levels)
這種類似 Z-Level (地下世界) 的做法。將一個世界拆分為多個互相關聯的「子地圖」。

*   創建一個自定義的 `MapParent` (繼承自 `WorldObject`) 來管理一組相鄰的 Maps。
*   修改 `CameraDriver` 和 UI，讓玩家可以透過按鈕（比如「往北看」）來快速切換當前活動的 Map，而不是進入世界地圖。

## 3. 需要克服的 Mod 開發難點
如果你決定採用 **策略 A (無縫切換)**，你需要解決以下問題：

1.  **跨地圖尋路 (Cross-map Pathfinding)**: 
    *   原版 AI 的 `PathFinder` 只能在單一 `Map` 內尋路。如果你命令一個小人去相鄰地圖拿東西，原版無法規劃路徑。
    *   **解法**: 必須自己寫一個上層的 `RegionPathFinder`，先計算出跨越板塊的大路線，再將其拆解為每個板塊內的 `LocalPath`，並撰寫自定義的 `JobDriver` 來銜接。
2.  **資源與區域的整合**: 
    *   玩家介面頂部的「資源清單」是基於單一地圖的。如果是開放世界，玩家會期望看到相鄰地圖的資源。這需要大幅修改 `ResourceCounter` 和 UI 繪製邏輯。
3.  **效能管理 (Garbage Collection)**: 
    *   當玩家探索了 10 個板塊，記憶體中就會有 10 個 `Map` 實例。
    *   必須實作一個「休眠系統 (Hibernation)」，當某個相鄰地圖沒有小人且玩家沒在看時，將該 `Map` 進行壓縮存檔並從內存中移除，只保留最基礎的模擬運算（類似 `WorldObject` 的 `Tick()`）。

## 結論
要在 RimWorld 中實作開放世界，**最佳切入點是修改「地圖邊界 (ExitMapGrid) 觸發的動作」，將其從「打包成商隊」改為「觸發相鄰 Map 的生成與傳送」**。

你可以參考社群中現有的「Z-Levels」或「Vehicles」等需要處理跨地圖傳送的 Mod 源碼，作為處理 `De-spawn` 和 `Spawn` 的參考範例。

---
*這份文件是由 Gemini CLI 分析 Verse.Map 與 RimWorld.Planet.Caravan 產生的深度策略指南。*
