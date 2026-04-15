# Level 5 Analysis: 技術架構與數據流

## 1. 資源持久化架構 (SaveableResource)
專案的核心數據管理建立在 `SaveableResource` 及其子類上，實現了「數據即資源」的設計哲學。

### 1.1 存檔行為抽象
- **SaveableResource.gd**: 
    - 支援 `FILE` (本地) 與 `STEAM` (雲端) 兩種存儲協議。
    - **序列化機制**: 利用 Godot 內建的 `ResourceSaver` 將 `.tres` 檔案存入 `user://` 目錄。
    - **版本控制**: 具備 `version` 欄位，可用於處理不同版本間的數據遷移。

### 1.2 緩存與重置
- `save_temp()` / `load_temp()`: 允許在不影響硬碟檔案的情況下，暫時修改數據狀態（例如商店預覽或屬性加點預覽）。
- `reset_resource()`: 提供快速恢復預設配置的介面。

## 2. 全域數據中心 (PersistentData)
- **單例職責**:
    - **生命週期管理**: 負責在遊戲初始化時觸發所有關鍵資源的 `load_resource()`。
    - **數據快取**: 提供一個萬用的 `data` 字典，避免了頻繁使用 `get_node()` 或全域變數導致的代碼混亂。

## 3. Steam 整合層 (SteamInit)
- **自動化切換**: 
    - `SteamInit.gd` 會在 `_ready` 時檢測 Steam 環境。
    - 若成功初始化，會調用 `SaveableResource.set_save_type(SaveType.STEAM)`，實現存檔邏輯的無縫切換。
- **Steam 特色支援**: 
    - 自動處理 Steam Callbacks。
    - 支援 Steam Deck 的特定邏輯判定。

## 4. 數據流向示意
1. **遊戲啟動**: `BootPreloader` 啟動 -> `PersistentData` 遍歷 `saveable_list` -> 從磁碟/Steam 加載 `.tres`。
2. **運行時**: 組件透過 `ResourceNode` 獲取 `PersistentData` 中的實例 -> 直接修改屬性。
3. **存檔觸發**: 手動呼叫 `save_resource()` -> `ResourceSaver` 寫入 user 路徑。
