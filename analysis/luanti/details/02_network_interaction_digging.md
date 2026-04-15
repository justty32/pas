# 模組深度分析 2：網路同步與玩家行為 (方塊挖掘流程)

## 流程概述
在體素遊戲中，「挖掘方塊」或「攻擊實體」是最高頻率的操作。本文件追蹤從客戶端發出請求到伺服器端驗證並執行的完整過程。

## 階段 1：封包解析與基礎驗證
**原始碼位置：** `src/network/serverpackethandler.cpp` (`Server::handleCommand_Interact`, 約 885 行起)

當伺服器接收到 `TOSERVER_INTERACT` 封包時，首先進行以下解析：
1. **提取核心資料**：
    - `action`: 定義行為類型 (例如 `INTERACT_START_DIGGING`, `INTERACT_DIGGING_COMPLETED`)。
    - `item_i`: 玩家目前手持物品在快捷鍵列 (Hotbar) 的索引。
    - `PointedThing`: 玩家指標所指的目標 (可能是一個方塊 `POINTEDTHING_NODE` 或一個實體 `POINTEDTHING_OBJECT`)。
2. **狀態驗證**：
    - 檢查玩家 (`PlayerSAO`) 是否存在且存活。若玩家在死亡狀態下發送互動封包，伺服器會將其標記為作弊 (`interacted_while_dead`) 並忽略該請求。
    - 檢查手持物品索引是否越界。

## 階段 2：權限與反作弊檢查 (Anti-Cheat)
為了防止外掛或延遲導致的錯誤操作，伺服器會進行嚴格的檢查：
1. **權限檢查 (`checkPriv`)**：確認玩家是否擁有 `interact` 權限。若無，伺服器會主動回傳原本的方塊資料給客戶端 (`client->SetBlockNotSent(blockpos)`)，強制作廢客戶端的本地預測挖掘。
2. **距離檢查 (`checkInteractDistance`)**：
    - 取得玩家眼睛位置 (`playersao->getEyePosition()`) 與目標位置。
    - 計算歐幾里得距離。若距離超過合法範圍（通常是 4 到 5 個方塊），該操作會被攔截。

## 階段 3：行為分派 (Action Dispatch)
通過所有驗證後，根據 `action` 進入不同的處理邏輯：

### 情境 A：開始挖掘 (`INTERACT_START_DIGGING`)
- **指向方塊**：
    - 嘗試從地圖獲取方塊。若該方塊所在的 `MapBlock` 尚未載入記憶體，會觸發 `m_emerge->enqueueBlockEmerge` 強制載入。
    - 觸發 Lua 回呼函數：`m_script->node_on_punch`。這讓 Mod 可以攔截挖掘行為（例如敲擊某個方塊會觸發機關）。
    - 呼叫 `playersao->noCheatDigStart` 記錄挖掘起始時間，用於後續計算挖掘耗時是否合理。
- **指向實體**：
    - 計算武器/工具的攻擊力與磨損 (`ToolCapabilities`)。
    - 呼叫 `pointed_object->punch` 執行傷害結算。
    - 更新手持工具的耐久度。

### 情境 B：完成挖掘 (`INTERACT_DIGGING_COMPLETED`)
- 伺服器會比對從 `INTERACT_START_DIGGING` 到現在的時間差，結合玩家手持工具的挖掘速度 (`ToolCapabilities`) 與方塊的硬度。
- 若時間合理，則真正從地圖中移除該節點 (`removeNode`)，並計算掉落物 (`get_drops`)，將其生成為新的掉落物實體 (`LuaEntitySAO`)。
- 若時間過短（可能是加速外掛），伺服器會拒絕挖掘並復原客戶端畫面。

## 結論
Luanti 採用了**強伺服器驗證架構**。客戶端雖然可以進行「預測性挖掘」（立刻在畫面上消除方塊），但真正的邏輯結算（掉落物、耐久度、實際地圖改變）全部由伺服器掌控。任何違規操作都會被伺服器悄無聲息地復原。
