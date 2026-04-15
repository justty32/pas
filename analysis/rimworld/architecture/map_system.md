# RimWorld 地圖系統與網格架構 (Map & Grids)

RimWorld 的地圖 (Map) 是一個複雜的空間管理系統。它並非單純的一個場景，而是一組高度優化的 2D 數據網格 (Grids)。

## 1. 地圖的本質 (The Map Object)
`Map` 類別 (位於 `Verse.Map`) 是地圖上所有數據與邏輯的容器。
*   **Map Size**: 地圖的大小 (例如 250x250) 決定了所有數據網格的維度。
*   **Cell**: 地圖的最小單位，由 `IntVec3` 座標表示（y 軸通常在地表為 0）。
*   **CellIndices**: 核心輔助工具，負責將 2D 座標 (x, z) 轉換為一維陣列索引，以極大地提高查詢效能。

## 2. 數據網格系統 (Grids)
為了提高效能，地圖數據被拆分到了多個並行的網格中：
*   **TerrainGrid**: 存儲地板資訊（如泥土、大理石地板）。
*   **ThingGrid**: 存儲該格子上存在哪些物體 (`Thing`)。
*   **RoofGrid**: 存儲該格子是否有屋頂。
*   **FogGrid**: 存儲迷霧（戰爭迷霧）狀態。
*   **GlowGrid**: 存儲光照強度與顏色。
*   **PathGrid**: 存儲路徑規劃成本（例如沼澤比地板更難走）。

## 3. 快速掃描器與過濾器 (Listers)
遍歷整個地圖上的物體是非常耗時的。因此遊戲使用 `Lister`：
*   **ListerThings**: 維護所有 `Thing` 的快速查找表，支援按 `ThingDef` 或類別過濾。
*   **ListerBuildings**: 專門管理所有建築物。
*   **MapPawns**: 管理地圖上所有的生物，並按派系 (Faction) 進行分類（如：玩家的小人、敵對海盜）。

## 4. 地圖組件 (MapComponent)
這對 Mod 開發者最為重要。如果你想給地圖增加額外的數據或邏輯（例如：地圖範圍內的特殊污染系統）：
*   繼承 `MapComponent`。
*   在構造函數中呼叫 `base(map)`。
*   遊戲會在加載地圖時自動實例化該組件。
*   `MapComponentTick()`: 每 Tick 執行地圖級邏輯。
*   `ExposeData()`: 將地圖級數據存入存檔。

## 5. 地圖渲染流程 (Rendering)
*   **靜態網格 (MapDrawer)**: 渲染不常變動的內容（地形、部分靜態物體）。地圖被拆分為多個 Section（17x17 的區塊），只有當區塊內容改變時才會重新生成 Mesh。
*   **動態繪製 (DynamicDrawManager)**: 渲染每一幀都可能移動或變動的物體（Pawn、掉落物）。

## 6. Mod 開發建議
*   **擴展數據**: 使用 `MapComponent` 存儲你的全局數據。
*   **地圖遍歷**: 永遠不要遍歷整個 `map.AllThings`。應優先使用 `map.listerThings` 或 `map.thingGrid.ThingsListAt(cell)`。
*   **修改地圖**: 透過 `map.terrainGrid.SetTerrain()` 或 `GenSpawn.Spawn()` 進行操作。

---
*這份文件是由 Gemini CLI 透過分析 Verse.Map 與 Verse.Grids 產生的分析報告。*
