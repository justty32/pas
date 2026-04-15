# Level 4: 遊戲性與實體系統分析

## 1. 實體系統 (Active Objects)
Luanti 的實體架構分為兩個層次，確保網路同步與渲染分離：
- **伺服器端實體 (SAO)**：`src/serverobject.h`
    - `PlayerSAO`: 代表玩家的伺服器端實體，處理物理與生命值。
    - `LuaEntitySAO`: 由 Lua 腳本定義行為的通用實體（如怪物、掉落物）。
- **客戶端實體 (CAO)**：`src/client/clientobject.h`
    - `GenericCAO`: 萬用客戶端實體，負責解析來自伺服器的指令（如 `AO_CMD_UPDATE_POSITION`）並進行插值平滑渲染。
- **通訊機制**：透過 `ActiveObjectMessage` 發送可靠或不可靠的狀態更新。

## 2. 物品與背包系統 (Inventory)
- **ItemStack** (`src/inventory.h`)：
    - 結構：`name` (物品名稱), `count` (數量), `wear` (耐久度), `metadata` (自定義資料)。
    - 功能：序列化/反序列化，用於存檔與網路傳輸。
- **Inventory**：
    - 包含多個 `InventoryList`。每個 List 有固定的大小。
    - 常見清單：`main` (玩家主背包), `craft` (合成網格), `armor` (裝備)。

## 3. 合成系統 (Crafting)
- **合成方法** (`src/craftdef.h`)：
    - `CRAFT_METHOD_NORMAL`: 3x3 或 2x2 網格合成。
    - `CRAFT_METHOD_COOKING`: 熔爐烹飪。
    - `CRAFT_METHOD_FUEL`: 燃料消耗。
- **配方管理**：`CraftDefinition` 定義了輸入物品與產出結果。
- **效能優化**：使用 `CraftHashType` (如 `CRAFT_HASH_TYPE_ITEM_NAMES`) 快速過濾可能的配方，避免全量掃描。

## 4. 節點元數據 (Node Metadata)
- **NodeMetadata** (`src/nodemetadata.h`)：
    - 允許在特定的方塊（節點）中存儲額外資訊。
    - 範例：箱子的背包內容、熔爐的剩餘時間、告示牌的文字。
    - 透過 `NodeTimer` 觸發定時事件。
