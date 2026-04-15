# 模塊分析：07_game_root_and_databases (全局容器與數據庫)

## 1. 全局容器：Root (StarRoot.hpp)
`Root` 是 OpenStarbound 的心臟，作為一個全局單例，它持有所有長期存活的數據庫與管理器。
- **懶加載機制：** 數據庫（如 `ItemDatabase`, `ObjectDatabase`）並非在啟動時全部加載，而是在首次訪問時通過 `Root` 初始化，這優化了啟動時間與內存佔用。
- **維護線程 (Maintenance Thread)：** 定期執行 `cleanup()`，清理過期的資源緩存與 Assets 引用。
- **重載支持 (Reload)：** 支持在運行時重載 Assets，這要求 `Root` 必須精確控制各個數據庫的依賴順序，以防止指針失效。

## 2. 數據驅動的數據庫系統 (Databases)
### ItemDatabase (道具數據庫)
- **ItemDescriptor：** 道具的輕量級標識符，包含 `name`, `count` 與自定義 JSON `parameters`。這是系統中傳遞道具的主要方式。
- **多態道具類：** 根據 `.item` 配置文件，實例化為 `ConsumableItem`, `ArmorItem`, `ActiveItem` 等具體子類。
- **配方掃描 (Recipe Scanning)：** 在加載時掃描所有 `.recipe` 文件，並構建一個高效的查詢索引，支持根據材料搜索配方。

### ObjectDatabase (物件數據庫)
- **靜態屬性與動態實例：** 區分物件的配置（如 `orientations`, `lightColor`）與世界中的實例。
- **瓷磚集成：** 管理物件與世界網格的碰撞框（Bounding Box）與佔位逻辑。

## 3. 實體工廠 (EntityFactory)
- **序列化橋接：** 負責將實體在 `ByteArray` (網路傳輸) 或 `Json` (磁碟存儲) 與 C++ 對象之間轉換。
- **版本控制：** 通過 `VersioningDatabase` 確保舊版本的實體數據在加載時能夠正確遷移（Migration）到當前版本。
