# 模組深度分析 1：Lua API 綁定機制 (Node Registration)

## 流程概述
Luanti 的強大之處在於其 Lua Modding API。當 Modder 呼叫 `minetest.register_node` 註冊一個新方塊時，這個指令是如何被 C++ 引擎解析並儲存的？本文件將追蹤其完整生命週期。

## 階段 1：Lua 層的包裝與攔截
**原始碼位置：** `builtin/game/register.lua` (行號約 323)

1. **包裝器：** `core.register_node` 其實是呼叫 `make_register_item_wrapper("node")` 所產生的函數。
2. **強制轉型：** 它會強制將傳入的參數表格（Table）加上 `type = "node"` 屬性。
3. **統一收口：** 接著呼叫底層的 `core.register_item(name, itemdef)`，這進一步呼叫 `register_item_raw(itemdef)`，正式跨越邊界進入 C++。

## 階段 2：C++ 層的接收與解析
**原始碼位置：** `src/script/lua_api/l_item.cpp` (行號 566-650，`ModApiItem::l_register_item_raw`)

當 `register_item_raw` 被呼叫時，C++ 端的 `l_register_item_raw` 接手處理：
1. **獲取管理器**：透過 `getServer(L)` 取得伺服器的兩個核心管理器：
    - `IWritableItemDefManager` (處理所有物品共通屬性)
    - `NodeDefManager` (專門處理方塊特有屬性，如碰撞、光照)
2. **讀取基礎物品屬性**：呼叫 `read_item_definition()`，將 Lua Table 轉換為 C++ 的 `ItemDefinition` 結構體。
    - *細節：* 這裡會處理如 `node_placement_prediction` 等客戶端預測邏輯。
3. **註冊為物品**：將解析後的定義寫入 `idef->registerItem(def)`。這意味著**在 Luanti 中，所有方塊本質上都是物品**。

## 階段 3：方塊特有屬性處理
**原始碼位置：** 延續 `l_register_item_raw` 內部邏輯。

如果被註冊的類型是方塊 (`def.type == ITEM_NODE`)：
1. **讀取方塊特徵**：呼叫 `read_content_features(L, f, table)`，將 Lua 表格中關於方塊的獨特設定（如 `drawtype`, `paramtype`）解析至 `ContentFeatures` 結構體。
2. **分配 ID 與儲存**：
    - 呼叫 `ndef->set(f.name, f)`，將方塊儲存進註冊表。
    - **核心機制：** 每個註冊的方塊都會被分配一個 `content_t id` (一個 16 位元的無號整數，上限約為 65535)。這個 ID 才是資料庫儲存與網路傳輸時所使用的真正標籤，而非字串名稱，這極大地優化了效能。
3. **容量檢查**：如果 `id >= MAX_REGISTERED_CONTENT`，會拋出 `LuaError`，阻止遊戲繼續執行。

## 結論
Luanti 的 Lua 綁定採用了非常嚴謹的**資料轉換分離原則**：腳本只負責提供定義（字串與表），而 C++ 引擎在載入階段便將這些定義全部轉換並扁平化為連續記憶體陣列（透過 `content_t` 索引），確保遊戲運行時的超高效能。
