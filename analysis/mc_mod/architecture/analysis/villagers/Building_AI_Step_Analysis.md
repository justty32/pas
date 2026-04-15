# 自動建築 AI 的原子步驟分析

本分析解構 `GoalConstructionStepByStep.java` 中的關鍵方法，展示村民如何「一磚一瓦」地蓋出建築。

## 1. 動作時長計算 (`actionDuration` 方法)
建築速度不是固定的，而是受「工具等級」與「方塊硬度」影響：
- **工具效率：** 獲取 `getBestShovel()` 的挖掘速度。
- **對照表：** 
    - 效率 > 8 (金/鑽石): 7-8 ticks。
    - 效率 < 2 (木): 16 ticks。
- **特殊方塊加成：** 若目標是空氣、泥土或沙子，動作時長會縮短為原來的 1/4。這模擬了清理地基比砌牆更快的真實感。

## 2. 方塊放置邏輯 (`performAction` 方法)
這是建築 AI 的核心循環：
- **跳躍邏輯：** 如果目標方塊在村民頭頂且距離過近，AI 會嘗試 `setPosition` 讓村民「跳上」建築層級。它會掃描四個方向的空位 (`isBlockFullCube`) 來決定落腳點。
- **建立與遞增：** 
    - 調用 `bblock.build()` 執行實際的 `world.setBlockState`。
    - **自動跳過已完成部分：** 如果 `build()` 失敗（例如方塊已存在），AI 會進入 `while` 循環，調用 `cip.incrementBblockPos()` 尋找藍圖中的下一個待放置點，直到成功放置為止。
- **資源消耗：** 當 `!cip.areBlocksLeft()` (建築完成) 時，才會一次性從村民背包中扣除總材料量。

## 3. 容錯處理 (`stuckAction` 與 `unreachableDestination`)
- **遠程放置：** 如果村民卡住且距離目標點 < 30 格，`stuckAction` 會強行調用 `performAction` 進行「遠程放置」，防止因為路徑尋找微小誤差導致建築永久停滯。
- **路徑失效：** `unreachableDestination` 同樣會嘗試在當前位置完成動作，確保建築工程的連續性。

## 4. 持有物同步 (`getHeldItemsOffHandTravelling`)
- 為了視覺化建設過程，當村民移動到工地時，AI 會解析藍圖中即將放置的 `BuildingBlock`，將其轉換為 `ItemStack` 並顯示在村民副手上，讓玩家能看到村民「搬著磚頭」走動。
