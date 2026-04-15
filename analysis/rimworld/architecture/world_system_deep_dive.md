# RimWorld 大地圖系統深度解析 (World Map & WorldObjects)

RimWorld 的大地圖 (World Map) 是一個球體網格系統，負責管理宏觀層面的遊戲邏輯，如商隊移動、派系據點、任務地點以及全球性事件。

## 1. 世界網格 (WorldGrid)
大地圖並非平面，而是一個由六邊形（及少數五邊形）組成的球體網格。
*   **Tile (地塊)**：世界的最小單位。每個 Tile 都有一個唯一的 ID。
*   **Tile 數據**：包含地形 (Biome)、海拔 (Elevation)、降雨量 (Rainfall)、溫度 (Temperature) 以及是否可通行。
*   **座標系統**：使用 `WorldGrid` 進行 ID 與 3D 空間座標 (Vector3) 的轉換。
*   **Traversability (通行性)**：決定了商隊是否能進入或穿過該地塊。

## 2. 大地圖物件 (WorldObject)
所有在大地圖上顯示的實體都是 `WorldObject` (位於 `RimWorld.Planet`)。

### A. 核心類別層次
*   **WorldObject**: 最基礎的類別。處理座標 (Tile)、派系 (Faction) 以及在大地圖上的渲染。
*   **MapParent**: 具備「連結局部地圖」能力的 `WorldObject`。
    *   如果一個地點可以被玩家進入（如玩家基地、任務地點），它必須繼承自 `MapParent`。
    *   它持有一個 `Map` 引用。當 `Map` 為 null 時，表示該地點尚未生成或已銷毀。
*   **Settlement (據點)**：永久性的派系基地。
*   **Site (地點)**：臨時性的任務目標（如遠古遺跡、敵方前哨站）。通常由 `SitePart` 組成。
*   **Caravan (商隊)**：動態移動的物件。它並不直接包含小人實體，而是將小人封裝在 `WorldPawns` 中。

### B. 重要機制
1.  **Tick 系統**: 
    *   與地圖上的 `Thing` 不同，`WorldObject` 的 `Tick()` 是由 `World` 全局管理的。
    *   頻率：大地圖物件通常每 Tick 都會更新，但耗時邏輯建議使用 `IsHashIntervalTick` 進行優化。
2.  **渲染 (Rendering)**:
    *   **DrawGraphic**: 返回在大地圖上顯示的 `Texture2D`。
    *   **ExpandingIcon**: 當玩家縮小大地圖時，物件會變成一個圓形圖示。可以透過 `ExpandingIconTexturePath` 自定義。
3.  **交互 (Interaction)**:
    *   **GetFloatMenuOptions**: 當選中商隊並右鍵點擊該物件時顯示的菜單。
    *   **GetInspectString**: 顯示在左下角面板的文字資訊。
4.  **數據持久化 (Scribe)**:
    *   必須實現 `ExposeData()`。大地圖數據與地圖數據是分開存儲的。

## 3. 地圖生成與進入流程 (The Map Connection)
這是 `MapParent` 最關鍵的功能：將「世界座標」轉換為「局部網格」。

1.  **觸發進入**: 玩家點擊「進入」按鈕或商隊抵達目的地。
2.  **檢查地圖**: 呼叫 `HasMap`。
3.  **生成地圖 (GetOrGenerateMap)**:
    *   如果 `Map` 為 null，則呼叫 `MapGenerator.GenerateMap()`。
    *   此時會讀取該 `WorldObject` 關聯的 `MapGeneratorDef`。
4.  **傳送實體**: 使用 `CaravanEnterMapUtility.Enter()` 將小人從商隊包裝中解出，並放置在地圖邊緣。

## 4. 世界組件 (WorldComponent)
類似於 `MapComponent`，這是存儲全球性數據的最佳位置。
*   **用途**：管理全球性計時器（如祭壇任務觸發）、追蹤跨派系的統計數據。
*   **生命週期**：隨存檔加載而實例化，隨世界銷毀而移除。

## 5. Mod 開發實戰建議
*   **自定義地點**：繼承 `Site` 並定義自定義的 `SitePart`。這樣可以利用原版的任務生成系統，而不需要手動處理複雜的地圖生成邏輯。
*   **動態物件**：如果你想做一個「移動的城市」或「巡邏隊」，請繼承 `WorldObject` 並在 `Tick()` 中修改 `this.Tile`。
*   **效能優化**：大地圖上有成千上萬個 Tile，查詢 `Find.WorldGrid` 是廉價的，但遍歷 `Find.WorldObjects` 是昂貴的。

---
*這份文件是由 Gemini CLI 透過分析 RimWorld.Planet 命名空間產生的技術架構報告。*
