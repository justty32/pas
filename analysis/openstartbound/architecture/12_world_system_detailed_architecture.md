# 模塊分析：12_world_system_detailed_architecture (世界系統深度架構)

在 OpenStarbound 中，「世界」（World）是物理模擬、實體交互與地形數據的最小完整單元。無論是星球、玩家飛船還是任務副本，在底層都被視為一個 `World` 實例。

## 1. 瓦片數據結構與網格存儲 (Tile Grid)
世界地圖本質上是一個巨大的二維網格。為了平衡訪問速度與內存佔用，引擎採用了 **分區存儲 (Sector-based Storage)**。
- **瓦片層級 (Layers)：** 每個坐標點包含三個主要物理層：
    - **Foreground (前景)：** 具有物理碰撞，阻擋實體與光線。
    - **Background (背景)：** 僅裝飾與阻擋光線，不具備物理碰撞。
    - **Liquid (液體)：** 獨立的液體層，存儲液體類型與壓力。
- **Tile 數據壓縮：** 每個瓦片不是一個重量級對象，而是由幾組 ID 和狀態（如 `MaterialId`, `Variant`, `DamageLevel`）組成的緊湊結構。
- **TileSectorArray：** 地圖被劃分為多個 Sector（通常為 32x32）。只有包含活動實體或玩家的 Sector 會被保留在內存中，其餘部分則交由 `WorldStorage` 換出至磁碟。

## 2. 環面幾何與空間判定 (Torus Geometry)
Starbound 的星球地圖是左右連通的，這在數學上被稱為 **環面 (Torus)** 或 **圓柱投影幾何**。
- **WorldGeometry 封裝：** 所有涉及位置的計算（如 `distance`, `diff`, `rect`）都必須通過 `WorldGeometry` 類進行。
- **邊界處理：** 當實體移動到地圖最右端 $(W, y)$ 時，下一個座標會被修正為 $(0, y)$。這要求物理引擎（碰撞檢測、射線投射）必須支持跨邊界判定，否則會發生嚴重的邏輯錯誤。

## 3. 核心模擬算法 (Core Simulation)
### 3.1 元胞自動機液體模擬 (Cellular Liquid)
- **壓力模型：** 採用基於壓力的流動算法。液體會嘗試向壓力較小的相鄰單元擴散。
- **流動優先級：** 向下 > 兩側 > 向上（僅在壓力足夠時）。
- **性能優化：** 僅對「活躍」的液體單元進行 Tick，靜止的液體（如深海底部）會進入休眠狀態。

### 3.2 元胞光照模擬 (Cellular Lighting)
- **遞歸擴散：** 光照從光源點開始，根據材料的透光率（Opacity）向四周擴散。
- **多線程處理：** 光照計算是 CPU 密集型任務。引擎通常在獨立的工作線程中分塊計算光照圖（Lighting Map），然後提交給渲染器進行平滑插值（Bilinear Interpolation）。

## 4. 世界權威與狀態同步 (World Server/Client)
- **WorldServer (權威端)：** 
    - 負責所有「破壞性」操作（方塊挖掘、液體放置、實體生成）的最終判定。
    - 維護一個 `TileArray` 的主副本。
- **WorldClient (鏡像端)：** 
    - 接收來自服務器的 `TileArrayUpdate` 與 `EntityUpdateSet` 封包。
    - 執行 **移動預測 (Client-side Prediction)**：玩家在本地立即移動，若服務器判定碰撞不符，則執行 **狀態回滾 (Rollback)**。

## 5. 持久化與非同步 I/O (WorldStorage)
- **區塊數據庫：** 世界數據存儲在 `.world` 文件中，本質上是一個 BTree 結構。
- **非同步寫入：** 當瓦片被修改時，`WorldStorage` 不會立即同步磁碟，而是將修改緩存在 `DirtyRects` 中，由背景線程分批寫入。
- **版本遷移：** 加載舊版本星球時，會根據 `VersioningDatabase` 執行 Tile ID 的重新映射，確保 Mod 變更後的兼容性。

## 6. 區域加載邏輯 (Region Loading)
- **活動區域 (Active Region)：** 圍繞玩家的一定半徑區域被標記為 Active。在這個區域內，實體 AI 激活，物理模擬啟動。
- **靜態區域：** 遠離玩家的區域，實體會被「凍結」並存儲到磁碟，直到玩家再次靠近。這確保了在大地圖下引擎仍能保持低內存開銷。
