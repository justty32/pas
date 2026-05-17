# Hailo Media Library C++ API 設計詳解

## 1. 核心設計理念
Hailo Media Library 的 C++ API 採用了 **非同步 (Asynchronous)** 與 **流水線 (Pipeline)** 的設計模式，旨在最大化 Hailo-15 硬體加速器的吞吐量。

## 2. 關鍵組件架構

### A. MediaLibrary (媒體管理器)
位於 `hailo-media-library/api/include/media_library/media_library.hpp`。
- **職責**: 作為最高層級的入口，管理 `Frontend` (輸入) 與 `Encoder` (輸出)。
- **操作流程**:
  1. `create()`: 建立實例。
  2. `initialize()`: 載入 JSON 配置文件。
  3. `subscribe_to_frontend_output()`: 註冊回呼函數以獲取處理後的圖像。
  4. `start_pipeline()`: 啟動底層驅動與 ISP 流程。

### B. Pipeline & Stage (分析流水線)
位於 `hailo-analytics` 模組中。
- **Pipeline**: 代表一個完整的 AI 處理流程（如：偵測 -> 追蹤 -> 辨識）。
- **Stage**: 流水線中的單一環節。
  - `SourceStage`: 數據來源（通常接 MediaLibrary 的輸出）。
  - `ThreadedStage`: 擁有獨立執行緒的處理環節，適合執行 CPU 密集的計算（如自定義 MLP）。
  - `HailortAsyncStage`: 專門用於調用 Hailo NPU 進行推論。
  - `SinkStage`: 數據出口（如寫入資料庫或 UDP 串流）。

## 3. 數據流與緩衝區管理
- 使用 `HailoMediaLibraryBufferPtr` 進行跨模組緩衝傳遞。
- 數據透過 `BufferPtr` 在 Stage 之間流動，內部包含原始圖像數據與相關聯的 `HailoROI` (Region of Interest)。
- **Metadata 附加**: AI 的推論結果（Bounding Box, Classifications）會動態附加到 `HailoROI` 物件上。

## 4. 自定義擴充性
開發者可以透過繼承 `ThreadedStage` 並重寫 `process()` 函數，在 Pipeline 的任何位置插入自定義的 C++ 邏輯。這也是實現自定義 MLP 推論或在線訓練的關鍵切入點。
