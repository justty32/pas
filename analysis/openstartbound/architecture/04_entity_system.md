# 模塊分析：04_entity_system (實體系統)

## 1. 實體容器 (EntityMap)
`StarEntityMap.hpp` 提供了高效的實體管理與查詢。
- **空間雜湊 (Spatial Hashing)：** 實體按位置存儲在網格中。
- **查詢優化：** 
  - `entityQuery`：範圍查詢（矩形）。
  - `entitiesAt`：點查詢。
  - `entityLineQuery`：線段相交查詢（用於射線檢測）。
- **唯一標識：** 每個實體具有全局唯一的 `EntityId` 與可選的 `uniqueId`（如 `player`）。

## 2. 網路同步 (Networked Entity)
實體狀態同步的核心在於 `NetElement`。
- **屬性組：** 實體定義多個同步組（如 `m_netGroup`）。
- **自動同步：** 當 C++ 層修改了標記為 NetElement 的成員時，系統會自動在下一個 Tick 生成 Delta 封包。

## 3. 實體行為與腳本
實體邏輯是 C++ 與 Lua 的高度結合。
- **C++ 核心：** 負責處理重物理運算、碰撞檢測與底層網路協議。
- **Lua 擴展：** 實體具有 `ScriptComponent`，允許通過 Lua 編寫 AI、交互邏輯與動畫控制。
- **主從同步 (Master/Slave)：** 
  - `Master` 實體運行完整邏輯（通常在服務器）。
  - `Slave` 實體僅接收同步數據並執行插值顯示（在客戶端）。
