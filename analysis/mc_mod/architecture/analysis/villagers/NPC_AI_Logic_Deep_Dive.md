# 村民 AI 實作邏輯深度分析

本分析直接取自 `OldSource/java/org/millenaire/common/entity/MillVillager.java` 的核心方法，揭示了村民如何處理戰鬥與社會化邏輯。

## 1. 戰鬥決策系統 (`attackEntity` 方法)
村民的戰鬥邏輯具備多樣性，會根據手持武器動態調整：
- **遠程行為：**
    - **條件：** 職業為 `isArcher` 且距離目標 > 5 格並持有弓。
    - **邏輯：** AI 會計算 `distanceFactor` (距離因子，0.1-1.0)，並傳遞給 `attackEntityWithRangedAttack`。
    - **武器增益：** `attackEntityWithRangedAttack` 會檢查 `ItemMillenaireBow` 的 `speedFactor` (拉弓速度) 與 `damageBonus` (傷害加成) 來調整箭矢的初速與威力。
- **近戰行為：**
    - **條件：** 距離目標 < 2 格。
    - **邏輯：** 使用 `DamageSource.causeMobDamage` 造成傷害，冷卻時間為 20 ticks (1秒)。

## 2. 聲望連動邏輯 (`attackEntityFrom` 方法)
村民被玩家攻擊時，會觸發動態的社會回應：
- **聲望懲罰：** 如果攻擊者是玩家且村民非敵對 (`!isRaider`)，會立即根據傷害量調整玩家在村莊的聲望值 (`serverProfile.adjustReputation`)。
- **求救機制：** 如果生命值低於 10 點，村民會調用 `getTownHall().callForHelp()`，這會觸發周圍所有衛兵 AI 的優先級變更，轉向保護該村民。

## 3. 人口成長邏輯 (`attemptChildConception` 方法)
Millénaire 的人口成長並非隨機，而是受資源與空間嚴格控制：
- **密度檢查：** 先掃描 `getHouse()` 內的兒童數量（若 > 1 則停止）以及全村兒童總量（受 `maxChildrenNumber` 設定限制）。
- **空間預檢：** 系統會遍歷全村所有建築，檢查是否有其他房屋有空餘位置 (`canChildMoveIn`) 供新出生的孩子居住。
- **配偶尋找：** 使用 `WorldUtilities.getEntitiesWithinAABB` 在 4 格範圍內尋找異性配偶，並檢查其性別與成長狀態。

## 4. 物品存取 (`addToInv` 方法)
- **Lazy Update：** 每次加入物品後，會調用 `updateVillagerRecord()` 同步數據至村莊中心，並調用 `updateClothTexturePath()` 檢查是否需要因為獲得新衣服而更新渲染層級。
