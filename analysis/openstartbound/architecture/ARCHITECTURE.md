# OpenStarbound 架構分析報告

本文件為 OpenStarbound 引擎架構的深度技術分析，專為資深 C++ 工程師編寫。OpenStarbound 是一個高性能、社區驅動的 Starbound 引擎，強調模組化、數據驅動設計以及強大的 Mod 支持。

---

## 1. 核心設計哲學
引擎採用 **數據驅動架構 (Data-Driven Architecture)**，大部分遊戲邏輯、內容和 UI 均由 JSON 和 Lua 腳本定義。C++ 核心作為高性能基座，提供以下功能：
- 虛擬檔案系統 (具有補丁機制的 Assets 系統)。
- 高度併發的世界模擬。
- 抽象化的渲染/音訊流水線。
- 客戶端-服務器模型的網路同步。

## 2. 模組拆解

### 2.1 `base/` 與 `core/` - 基礎層
這些模組實現了一套針對遊戲開發優化的自定義「標準庫」。
- **內存管理：** 廣泛使用 `std::shared_ptr` (通常別名為 `Ptr`)，並在部分區域使用自定義的 `RefPtr` 進行侵入式引用計數。針對高頻分配，通常透過 `BlockAllocator` 進行管理。
- **字符串與 Unicode：** `StarString` 和 `StarUnicode` 提供強大的 UTF-8/32 處理能力，這對於支持多語言文本的遊戲至關重要。
- **I/O 與序列化：** `DataStream` 抽象層處理不同後端 (文件、內存、Socket) 的二進制序列化。支持 **VLQ (變長整數)** 編碼，以實現高效的網路傳輸。
- **資源系統 (Asset System)：** 
  - **虛擬檔案系統：** 將多個來源 (`DirectoryAssetSource`, `PackedAssetSource`) 聚合到單一命名空間。
  - **JSON 補丁 (類似 RFC 6902)：** 在遊戲加載 JSON 之前，系統會自動應用所有發現的 `.patch` 文件。這允許 Mod 在不覆蓋原始文件的清況下修改核心數據。
  - **TTL 緩存：** 資源根據 TTL (生存時間) 策略進行緩存，平衡內存佔用與加載速度。

### 2.2 `game/` - 模擬引擎
模擬分為 **宇宙 (Universe)** 與 **世界 (World)** 兩個層級。
- **UniverseServer / UniverseClient：** 管理全局狀態，包括玩家在星系中的位置以及跨世界的通訊。
- **WorldServer / WorldClient：** 
  - 每個 `World` (星球、飛船、副本) 運行在獨立的線程 (`WorldServerThread`) 中。
  - **仿真精度 (Fidelity Levels)：** 支持不同的模擬精度 (從 Minimum 到 High)，以優化後台世界的資源消耗。
  - **瓦片系統 (Tile System)：** 用於存儲材質、液體和碰撞的高性能網格系統。使用 `CellularLiquid` 實現類似納維-斯托克斯 (Navier-Stokes) 的液體模擬。
  - **碰撞檢測：** 結合了基於網格的碰撞與針對實體的任意多邊形碰撞。

### 2.3 `game/entities/` - 實體組件體系
Starbound 並非純粹的 ECS，而是使用 **混合層次模型 (Hybrid Hierarchical Model)**：
- **`Entity` 基類：** 定義位置、速度和網路同步的核心接口。
- **核心子類：** `Player`, `Monster`, `Npc`, `Object`, `Projectile`, `ItemDrop`。
- **NetElement 系統：** 一套精密的高級屬性同步系統。類中定義 `NetElement` 成員 (如 `NetElementFloat`)，當其數值改變時，系統會自動追蹤並在服務器與客戶端間同步。

### 2.4 `core/scripting/` - Lua 集成
深度集成 Lua 5.2。
- **綁定機制：** 使用自定義綁定層 (參見 `StarLua.hpp`)，透過 **模板元編程 (Template Metaprogramming)** 將 C++ 類型映射到 Lua 表和函數。
- **沙箱化：** 每個實體或腳本上下文都運行在沙箱環境中，受控地訪問引擎回調 (例如 `world.entityPosition`)。
- **性能優化：** 高頻邏輯 (如移動控制) 通常在 C++ 中實現，並導出至 Lua 以供行為自定義。

### 2.5 `rendering/` 與 `windowing/` - 表現層
- **抽象化：** 渲染器設計為後端無關，目前主要針對 OpenGL。
- **批次處理 (Batching)：** 提供高性能的精靈 (Sprite) 與幾何體合批。`TileDrawer` 負責大規模瓦片地圖的高效渲染。
- **指令系統 (Directives)：** 獨特的「圖像處理指令」系統 (例如 `?replace;ff0000=00ff00`) 允許在不生成磁碟文件的情況下，實時進行圖像操作 (調色板替換、掩碼處理)。

## 3. 併發模型
- **工作線程池 (Worker Pools)：** 全局 `WorkerPool` 用於並行處理獨立任務，如資源加載或世界生成。
- **鎖策略：** 混合使用 `Mutex` 與 `RecursiveMutex`，並配合 RAII 守衛 `MutexLocker`。架構傾向於在世界層級使用粗粒度鎖，在資源緩存等共享資源上使用細粒度鎖。
- **線程局部存儲 (TLS)：** 在部分區域使用 TLS 以減少高頻操作的鎖競爭。

## 4. 網路協議
- **基於封包：** 在 `StarNetPackets.hpp` 中定義自定義二進制封包。
- **狀態同步：** 採用「步進與同步 (Step and Sync)」方法。服務器具有絕對權威，但客戶端會執行 **移動預測 (Movement Prediction)** 以掩蓋延遲。
- **數據壓縮：** 使用 Zstandard (ZSTD) 或 Zlib 壓縮大型數據傳輸 (如世界數據塊)。

## 5. 開發者開發導引
擴展引擎的方法：
1.  **修改內容：** 專注於 `assets/` 目錄下的 JSON 和 Lua。
2.  **添加機制：** 若對性能要求極高，請在 `source/game/` 中實現，並透過新的 `LuaBindings` 類暴露給 Lua。
3.  **底層優化：** 研究 `source/core/` 的容器/數學庫，或 `source/base/` 的資源流水線。

本代碼庫是 **「引擎即平台」 (C++ Engine as a Platform)** 的典範，引擎負責處理所有繁重任務 (I/O, 物理, 渲染)，而遊戲本身由數據定義。
