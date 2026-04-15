# 伺服器持久化與網路通訊深度分析 (Analysis)

## 1. 角色存檔持久化 (`server/src/persistence/character_updater.rs`)
Veloren 如何保證玩家數據的安全存儲。

### 核心邏輯拆解：
- **非同步寫入 (`CharacterUpdater`)**：
    - **位置**：`server/src/persistence/character_updater.rs` (約 80 行)
    - **邏輯**：所有的 SQL 操作（Update, Create, Edit）都發生在一個獨立的執行緒中。透過 `BatchUpdate` 訊息將多個玩家的存檔合併，減少資料庫 IO 負擔。
- **數據映射 (`json_models.rs`)**：
    - **位置**：`server/src/persistence/json_models.rs` (約 115 行)
    - **邏輯**：將 Rust 的 Complex Enums（如 `AuxiliaryAbility`）轉換為簡單的字串格式（如 `Main Weapon:index:0`）以便存儲。

## 2. 網路流管理 (`server/src/client.rs`)
### 核心邏輯拆解：
- **多流傳輸 (`Client`)**：
    - **位置**：`server/src/client.rs` (約 15-200 行)
    - **邏輯**：將數據拆分為 `terrain_stream`, `in_game_stream` 等流。這確保了巨大的地形封包不會阻塞關鍵的戰鬥與位置同步封包。

---
*本文件由分析任務自動生成。*
