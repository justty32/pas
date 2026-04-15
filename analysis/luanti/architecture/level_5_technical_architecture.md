# Level 5: 技術架構與數據流分析

## 1. 資料持久化 (Database System)
Luanti 的資料存儲採模組化設計，主要處理三類數據：
- **地圖數據 (Map Database)**：
    - 核心類別：`MapDatabase` (`src/database/database.h`)
    - 單位：`MapBlock` (16x16x16 節點)。
    - 索引：使用 `getBlockAsInteger(v3s16)` 將三維座標壓縮為 64 位元整數。
    - 後端支援：SQLite3 (預設), PostgreSQL, LevelDB, Redis, Dummy (不保存)。
- **玩家數據 (Player Database)**：
    - 核心類別：`PlayerDatabase`
    - 職責：保存玩家背包、位置、生命值與權限。
- **驗證數據 (Auth Database)**：管理密碼雜湊與權限。

## 2. 配置管理 (Settings)
- **類別**：`Settings` (`src/settings.h`)
- **機制**：
    - 支援多層級配置（全域、世界特定、命令列覆蓋）。
    - 觀察者模式：透過 `registerChangedCallback` 讓其他模組監聽配置變動。
    - 檔案格式：自定義的 `key = value` 格式 (`minetest.conf`)。

## 3. 序列化協定 (Serialization)
Luanti 擁有高度優化的二進位序列化格式：
- **演進歷史**：從 Ver 0 (1-byte nodes) 到 Ver 29 (zstd 壓縮)。
- **壓縮策略**：
    - 舊版使用 zlib。
    - 新版 (Ver 29+) 預設使用 **zstd** 以獲得更好的效能比。
- **數據完整性**：序列化過程包含元數據、靜態物件 (Static Objects) 與節點定時器 (Node Timers)。

## 4. 數據流向
1. **讀取**：啟動時從 `minetest.conf` 載入配置 -> 初始化資料庫連接。
2. **運行**：`EmergeManager` 非同步從資料庫讀取 `MapBlock` -> 傳送至客戶端。
3. **寫入**：伺服器定期或關閉時呼叫 `beginSave()` / `endSave()` 將變動寫回資料庫。
