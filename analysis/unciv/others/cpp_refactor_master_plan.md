# Unciv C++ 重構主計畫 (Master Plan)

## 1. 核心願景
利用 C++ 的底層控制能力，徹底解決 Unciv 在後期地圖（如極大地圖、多文明）中的性能卡頓問題，並為未來可能的視覺增強與高頻率模擬打下基礎。

## 2. 階段性任務 (Phases)

### Phase 1: 記憶體與資料佈局 (Cache-Friendly Architecture) [進行中]
- **現狀痛點**: `Tile.kt` 是一個巨大的物件，內含多個物件引用，導致地圖遍歷時快取命中率極低。
- **重構方案**: 
    - 採用 **SoA (Structure of Arrays)** 或壓縮後的 **AoS (Array of Structures)**。
    - 使用 `std::vector<uint32_t>` 儲存地圖基本屬性，利用 Bitfields 壓縮 Terrain, Feature, Improvement。
    - 實作 **Arena Allocator** 用於處理回合內的臨時 AI 運算，避免 `new/delete` 碎片。

### Phase 2: 高並發尋路與戰略計算引擎
- **重構方案**: 
    - 實作多線程 A*，利用 C++20 Coroutines 處理非同步的路徑規劃請求。
    - 針對六角格座標進行指令級優化 (SIMD)。

### Phase 3: AI 決策框架重組 (Utility AI)
- **重構方案**: 
    - 將 `UnitAutomation.kt` 的邏輯解讀並轉化為「行動空間評分矩陣」。
    - 引入行為樹 (Behavior Trees) 或效用系統 (Utility System) 取代硬編碼的 if-else。

### Phase 4: 規則引擎與 Modding (Data-Driven Design)
- **重構方案**: 
    - 建立零拷貝 (Zero-copy) 的數據讀取系統（如 Flatbuffers）。
    - 實作高效的數據查詢索引 (Perfect Hashing) 用於處理數千個 Ruleset 項目。

### Phase 5: 驗證與定點數運算
- **重構方案**: 
    - 嚴格實作 `FixedPoint` 類別，確保與 Kotlin 的 `com.unciv.logic.multiplayer.FixedPointMovement` 行為一致。
    - 實作自動化單元測試，比對 Kotlin 與 C++ 的戰鬥傷害結果。

## 3. 當前執行事項
- 分析 `Tile.kt` 欄位佔用情況。
- 產出 C++ `HexMap` 容器與 `TileStore` 的設計方案。
- 記錄於 `analysis/unciv/architecture/cpp_memory_layout.md`。
