# 模塊分析：08_game_world_simulation_deep_dive (世界模擬深度解析)

## 1. 世界模擬架構 (WorldServer vs WorldClient)
OpenStarbound 採用服務器權威架構。
- **WorldServer (權威端)：** 運行在獨立線程。執行物理模擬、AI 更新、瓦片修改驗證與數據持久化。
- **WorldClient (本地預測端)：** 負責渲染、輸入處理與本地移動預測。它接收來自服務器的增量更新（EntityUpdateSet）。

## 2. 模擬循環 (The Simulation Tick)
- **固定時鐘 (Fixed Update)：** 默認每秒 60 次 Tick。
- **更新順序：**
  1. **實體更新：** 調用 `EntityMap::updateAllEntities`，遍歷所有實體執行 `update()`。
  2. **瓦片物理：** 處理瓦片損壞、掉落與自然演化。
  3. **流體模擬：** 調用 `CellularLiquid` 更新水與岩漿的流動。
  4. **環境效果：** 更新天氣、光照與行星背景（Parallax）。

## 3. 世界存儲與持久化 (WorldStorage)
- **區塊管理 (Chunky Storage)：** 星球被劃分為多個區塊，僅加載活躍區域周圍的數據。
- **BTree 索引：** 世界文件後端通常是一個 BTree 數據庫，支持 O(log n) 級別的區域隨機讀寫。
- **生成器 (WorldGenerator)：** 當玩家移動到未開發區域時，生成器會根據星球種子實時計算地形與結構。

## 4. 線程安全與並行
- **RecursiveMutex：** 世界類使用遞歸鎖保護，因為實體邏輯經常會反向回調世界接口（如 `world.spawnProjectile`）。
- **非同步任務：** 將耗時的數據保存與複雜的路徑規劃（A*）交給 `WorkerPool` 異步處理。
