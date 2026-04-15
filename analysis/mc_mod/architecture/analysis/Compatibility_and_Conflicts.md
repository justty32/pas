# 模組相容性與潛在衝突分析 (Compatibility & Conflicts)

Millénaire Reborn 是一個功能密集的模組，它在世界生成、NPC AI 以及實體渲染等方面都有獨特的實作。在 1.21.8 Fabric 環境下，與其他模組可能發生的衝突主要集中在以下四個領域。

## 1. 世界生成衝突 (World Gen Conflicts)
這是 Millénaire 最容易與其他模組發生摩擦的地方。
- **結構重疊：**
    - **衝突對象：** *Better Villages*, *Repurposed Structures*, *Towns and Towers*。
    - **原因：** 這些模組同樣會在世界中生成村莊或大型結構。雖然 1.21.8 的結構標記系統 (Structure Tags) 有助於避免物理上的重疊，但若兩個模組同時偵測到同一塊平坦地形，仍可能發生結構「交錯」的現象。
- **生物群落 (Biomes) 限制：**
    - **衝突對象：** *Terralith*, *Tectonic* 等地形改造模組。
    - **原因：** Millénaire 的 `VillageType` 高度依賴原版生物群落的標籤。如果地形模組刪除或大幅重命名了生物群落，Millénaire 可能找不到合適的生成點。

## 2. Mixin 注入衝突 (Mixin Injection Conflicts)
隨著 Phase 5-8 的開發，模組將會開始使用 Mixin 修改 Vanilla 代碼。
- **實體路徑尋找 (Pathfinding)：**
    - **衝突對象：** *Lithium*, *Entity Culling*。
    - **原因：** 為了實現複雜的村莊導航，Millénaire 可能需要對 `MobEntity` 或 `EntityNavigation` 進行 Mixin。如果其他效能優化模組也修改了相同的方法，可能導致崩潰或 NPC 行為異常。
- **物品欄與 GUI：**
    - **衝突對象：** *REI (Roughly Enough Items)*, *EMI*, *JEI*。
    - **原因：** 村民的貿易 GUI 是高度自定義的。雖然現代 API (ScreenHandler) 很強大，但自定義的 NBT 讀寫或錢幣（Deniers）的自動拆分邏輯可能會導致與這些配方查詢模組的互動不順。

## 3. 效能與系統負荷 (Performance & Overhead)
- **AI 運算量：**
    - **衝突對象：** 任何大量增加實體 AI 的模組（如某些地牢模組）。
    - **原因：** Millénaire 的每個村民都在進行 A* 路徑尋找與決策循環。在 1.21.8 中，如果不使用異步路徑尋找，伺服器的 TPS 可能會因為 NPC 數量過多而大幅下降。
- **記憶體占用：**
    - Millénaire 載入大量的藍圖 (Building Plans) 與文化配置 (Cultures)，這對於記憶體較小的伺服器來說是一筆不小的負擔。

## 4. 特殊機制衝突 (Gameplay Mechanics)
- **聲望系統：**
    - 如果玩家安裝了其他「聲望」或「派系」模組（如某些 RPG 類模組），這兩套系統可能互不相干，導致玩家在一個模組中是英雄，但在另一個模組中是被村莊通緝的罪犯。
- **方塊替換邏輯：**
    - **衝突對象：** *WorldEdit* 或其他快速建築模組。
    - **原因：** 村民建設時會逐步放置方塊，如果此時有其他模組強制清理區域或更改方塊狀態，可能導致村莊數據與世界現實不匹配，造成「幽靈建築」。

## 💡 緩解建議
1. **使用 Structure Tags：** 確保所有的村莊生成都正確標記，讓其他結構模組能夠偵測到。
2. **優先使用 Fabric API：** 盡量使用標準的事件鉤子 (Hooks)，減少對底層代碼的 `Overwrite` Mixin。
3. **異步計算：** 所有的 A* 計算應移至非同步線程。
4. **Data Pack 驅動：** 將文化與藍圖配置開放給 Data Pack，允許玩家手動調整生物群落標籤以適應地形模組。
