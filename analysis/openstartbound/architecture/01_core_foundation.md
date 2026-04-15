# 模塊分析：01_core_foundation (核心基礎層)

## 1. 網路同步系統 (NetElement System)
`StarNetElement.hpp` 定義了引擎的核心同步機制。
- **版本控制 (NetElementVersion)：** 使用單調遞增的 64 位元整數追蹤狀態變更。
- **增量同步 (Delta Sync)：** `writeNetDelta` 與 `readNetDelta` 支持僅傳輸自上次版本以來的差異，極大地節省了帶寬。
- **插值與預測：** `enableNetInterpolation` 提供平滑處理，允許客戶端在接收到延遲數據時進行插值。

## 2. 序列化架構 (DataStream)
`StarDataStream.hpp` 提供了統一的二進制接口。
- **VLQ 編碼：** 針對整數使用變長編碼，減少冗餘。
- **容器支持：** 內置對 `std::vector`, `std::map`, `StarVariant` 等複雜容器的遞歸序列化支持。

## 3. Lua 綁定層 (StarLua)
基於模板元編程的綁定機制。
- **自動推導：** 能夠根據 C++ 函數簽名自動生成 Lua 棧操作代碼。
- **安全性：** 提供了強類型的錯誤檢查，確保 Lua 調用 C++ 接口時的參數正確性。
- **沙箱環境：** 每個 LuaContext 具有獨立的全局表，實現了嚴格的邏輯隔離。
