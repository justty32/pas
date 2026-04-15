# 模塊分析：06_networking_protocol (網絡協議)

## 1. 封包架構 (StarNetPackets)
`StarNetPackets.hpp` 定義了客戶端與服務器通訊的所有邏輯單元。
- **層次化設計：** 
  - **Universe 級別：** 處理握手、聊天、跨星系移動（`FlyShip`, `PlayerWarp`）。
  - **World 級別：** 處理瓦片更新（`TileArrayUpdate`）、實體同步（`EntityCreate`, `EntityUpdateSet`）。
- **序列化：** 每個 Packet 類都繼承自 `Packet` 接口，並實現 `read` 與 `write` 方法，利用 `DataStream` 進行轉換。

## 2. 握手與連接 (Handshake)
- **版本校驗：** `ProtocolRequest` 包含協議版本號，確保客戶端與服務器版本一致。
- **數據摘要 (Digest)：** 服務器會與客戶端校驗 Assets 文件的摘要值，確保兩者的 Mod 列表與內容一致。
- **挑戰-響應：** 用於身份驗證的安全握手機制。

## 3. 世界同步邏輯
- **增量瓦片更新：** 為了節省帶寬，系統通常只發送玩家附近的瓦片數據，或發生變更的單個瓦片封包。
- **實體追蹤：** 服務器根據玩家的視距範圍，動態地向客戶端發送 `EntityCreate` 與 `EntityDestroy` 封包，維持客戶端實體地圖的準確性。
