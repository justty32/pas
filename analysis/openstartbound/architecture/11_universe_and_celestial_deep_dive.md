# 模塊分析：11_universe_and_celestial_deep_dive (宇宙與天體系統深度解析)

## 1. 宇宙定址體系 (CelestialCoordinate)
OpenStarbound 的宇宙是一個邏輯上無限、物理上確定性的多維空間。
- **座標結構：** `CelestialCoordinate` 封裝了天體的層次化定址：
    - **Location (x, y)：** 64 位元整數定義的星系座標。
    - **PlanetaryOrbit：** 行星在星系中的軌道序號。
    - **SatelliteOrbit：** 衛星在行星軌道中的序號。
- **座標類型：** 
    - `Coordinate`：普通隨機星球。
    - `Ship`：玩家飛船（以玩家 UUID 作為唯一標識）。
    - `Instance`：副本空間（如任務地圖、前哨站）。

## 2. 天體數據庫與過程生成 (CelestialDatabase)
宇宙的內容並非預先存儲，而是基於 **過程生成 (ProcGen)**。
- **確定性生成：** 通過一個 64 位元的 `UniverseSeed`。給定 $(x, y)$ 座標，算法始終生成相同的星系佈局、星球類型與生態環境。
- **Master/Slave 數據模型：**
    - **MasterDatabase (服務器)：** 負責原始生成與存儲「玩家修改過」的星球元數據。
    - **SlaveDatabase (客戶端)：** 接收來自服務器的導航快照，用於在導航介面（Navigation Console）渲染星系圖。
- **數據摘要 (Digest)：** 服務器會與客戶端校驗資產摘要，確保雙方的生成算法（特別是 Mod 修改過的星球屬性）保持同步。

## 3. 宇宙服務器核心 (UniverseServer)
`UniverseServer` 是管理所有並行世界線程的中央調度器。
- **多線程模型 (Threading Model)：** 
    - **世界隔離：** 每個活躍的世界（有玩家存在的星球或飛船）運行在獨立的 `WorldServerThread` 中。
    - **線程安全：** 透過 `RecursiveMutex` 與 `ReadWriteLocker` 管理跨世界的資源競爭（如玩家組隊信息、全局聊天）。
- **生命週期管理：** 
    - **激活：** 玩家傳送時，若目標世界不在線程池中，則觸發加載或生成。
    - **休眠：** 當世界中無玩家且冷卻時間過期後，保存狀態並關閉線程。
- **全局同步：** `UniverseClock` 負責維持全宇宙統一的遊戲時間（天數與时刻），這對星球晝夜交替至關重要。

## 4. 跨世界傳送機制 (Warping)
這是引擎中最複雜的邏輯之一，涉及實體的跨線程遷移。
- **序列化遷移：** 
    1. 當玩家觸發 Warp，其 `Player` 實體在當前 `WorldServer` 中被序列化。
    2. 實體對象從原世界線程中移除。
    3. `UniverseServer` 接收實體數據流，並將其傳遞給目標 `WorldServer` 線程。
    4. 目標世界在指定傳送點（Warp Action）反序列化並重建實體。
- **WarpAction：** 支持多種傳送目標（如 `ToPlanet`, `ToShip`, `ToInstance`）。

## 5. 宇宙持久化 (Persistence & BTree)
- **`universe.chunks`：** 核心數據庫文件，採用自定義的 BTree 結構。
- **存儲內容：** 
    - **玩家數據：** `.player` 文件（裝備、統計、解鎖項）。
    - **飛船數據：** `.shipworld` 文件。
    - **星球修改：** `.world` 文件（僅存儲與原始生成算法不同的增量數據）。
- **版本控制 (Versioning)：** 透過 `VersioningDatabase` 管理數據遷移。當引擎更新導致數據結構變化時，系統會在加載時運行對應的遷移腳本。

## 6. 宇宙客戶端 (UniverseClient)
- **狀態機：** 管理玩家在宇宙中的狀態（如 `InWorld`, `Warping`, `Teleporting`）。
- **遠程通信：** 透過 `UniverseConnection` 與服務器交換封包，同步跨世界的實體信息與導航數據。
