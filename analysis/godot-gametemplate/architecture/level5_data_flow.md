# Level 5 Analysis: 技術架構與數據流

> 核對於 2026-05-25（Claude Code, Opus 4.7）：SaveableResource、PersistentData、SteamInit 大致正確；本次補上路徑/行號，並澄清 STEAM 後端目前仍為 TODO（與 FILE 走同一檔案實作）。

## 1. 資源持久化架構 (SaveableResource)
專案的核心數據管理建立在 `SaveableResource` 及其子類上，實現了「數據即資源」的設計哲學。

### 1.1 存檔行為抽象
- **檔案路徑**: `addons/great_games_library/resources/SaveableResource/SaveableResource.gd`
    - 以 `static var save_type:SaveType{FILE, STEAM}`（`SaveableResource.gd:20-23`）切換存儲協議。**但目前 STEAM 分支只是 TODO，實作上仍呼叫 `_save_resource_file()` / `_load_resource_file()`**（`:68-71,93-94`）——尚未接上真正的 Steam 雲端 API。
    - **序列化機制**: 利用 Godot 內建的 `ResourceSaver.save()` 將 `.tres` 存入 `user://`，路徑由 `get_save_file_path()` 以 `resource_name` 組成（`SaveableResource.gd:50-53,111-117`）。
    - **版本控制**: 具備 `version:int` 欄位（`:11`），可用於處理不同版本間的數據遷移。
    - **覆寫點**: 子類覆寫 `prepare_save()` / `prepare_load()` / `reset_resource()` 客製序列化與重置（`:32-42`）。`is_loaded` 旗標避免重複載入（`:78-80`）；載入失敗則 `reset_resource()` 回預設（`:96-99`）。

### 1.2 緩存與重置
- `save_temp()` / `load_temp()` + `is_temporary` 旗標: 當 `is_temporary` 為真時，`save_resource()`/`load_resource()` 改走記憶體中的 `temporary_data`，不觸碰硬碟（`SaveableResource.gd:25-26,44-48,59-61,85-87`），適用於商店預覽或屬性加點預覽。
- `not_saved`: 標記為不存檔、改以 `reset_resource()` 重置的資源（`:14,58,82-83`）。

## 2. 全域數據中心 (PersistentData)
- **檔案路徑**: `addons/top_down/scripts/game/PersistentData.gd`（autoload 場景 `scenes/autoloads/persistent_data.tscn`）。腳本本身極精簡，僅 `saveable_list:Array[SaveableResource]` 與 `data:Dictionary` 兩個 export（`PersistentData.gd:3-6`）。
- **單例職責**:
    - **生命週期管理**: `BootPreloader.start()` 在啟動時走訪 `saveable_list` 觸發各資源 `load_resource()`（`BootPreloader.gd:41-42`）。
    - **數據快取**: `data` 字典作萬用記憶體保存（例：`BootPreloader.gd:38` 把 `PreloadResource` 釘在 `data["preload_resource"]` 跨關卡保留），避免頻繁 `get_node()` 或全域變數導致的代碼混亂。

## 3. Steam 整合層 (SteamInit)
- **檔案路徑**: `addons/great_games_library/autoload/SteamInit.gd`（autoload，無 class_name）。
- **自動化切換**: 
    - `_ready()` 先以 `Engine.has_singleton("Steam")` 檢測 GodotSteam 是否存在，不存在則直接 `set_process(false)` 返回（`SteamInit.gd:18-21`）。
    - 初始化成功（且擁有遊戲）後呼叫 `SaveableResource.set_save_type(SaveableResource.SaveType.STEAM)`（`SteamInit.gd:49`）。
- **Steam 特色支援**: 
    - `_process()` 中 `run_callbacks()` 處理 Steam Callbacks（`SteamInit.gd:53-54`）。
    - 透過 `isSteamRunningOnSteamDeck()` 判定 Steam Deck（`:39`），並記錄 `is_online`/`is_owned`/`steam_id`/`steam_username`。未擁有遊戲則 `get_tree().quit()`（`:45-47`）。預設測試 app_id 為 480（Spacewar，`:4`）。

## 4. 數據流向示意
1. **遊戲啟動**: `BootPreloader` 啟動 -> `PersistentData` 遍歷 `saveable_list` -> 從磁碟/Steam 加載 `.tres`。
2. **運行時**: 組件透過 `ResourceNode` 獲取 `PersistentData` 中的實例 -> 直接修改屬性。
3. **存檔觸發**: 手動呼叫 `save_resource()` -> `ResourceSaver` 寫入 user 路徑。
