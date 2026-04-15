# 模塊分析：03_game_simulation_universe_world (遊戲模擬層)

## 1. 宇宙服務器 (UniverseServer)
`StarUniverseServer.hpp` 是整個後端的中央管理器。
- **多線程架構：** 
  - 每個 `World` 運行在獨立的 `WorldServerThread` 中，實現了星球級別的並行模擬。
  - 使用 `WorkerPool` 處理異步任務（如世界生成、磁碟 I/O）。
- **連接管理：** 透過 `UniverseConnectionServer` 管理多個客戶端，支持 TCP 與本地 Socket。
- **時鐘同步：** 維持全局 `UniverseClock`，確保所有星球的遊戲時間（天數、時刻）保持一致。

## 2. 世界模擬 (WorldServer)
`StarWorldServer.hpp` 負責單個星球的物理與邏輯。
- **Tick 驅動：** 預設頻率為 60Hz。
- **區域加載 (Sector Loading)：** 僅加載有玩家或活動實體的區域，節省資源。
- **鎖機制：** 
  - 使用 `RecursiveMutex` 保護世界狀態。
  - 由於世界涉及大量的實體交互、瓦片更新與腳本回調，鎖的設計旨在防止死鎖的同時保證線程安全。

## 3. 天體數據庫 (CelestialDatabase)
管理星系地圖與星球屬性。
- **隨機生成：** 基於 64 位元種子生成整個星系。
- **數據存儲：** 使用 `BTreeDatabase` 存儲星球的元數據與區塊信息。
