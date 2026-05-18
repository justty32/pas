# Hailo AI 流水線與元數據流機制 (Level 3)

## 核心設計哲學
Hailo Media Library 的 AI 框架 (`hailo-analytics`) 採用了 **非同步流水線 (Asynchronous Pipelining)** 與 **共享對象元數據 (Shared Object Metadata)** 的設計模式。這使得系統能在 NPU 執行推論的同時，CPU 進行上一幀的後處理或下一幀的前處理。

## 流水線組件 (Pipeline Components)
典型的 AI 處理鏈由以下 `ThreadedStage` 組成：
1.  **AIStage (`HailortAsyncStage`)**: 負責 NPU 推論。
2.  **PostprocessStage**: 負責解析推論結果 (Tensors)。
3.  **OverlayStage**: 負責將結果繪製到圖像上。

## 元數據流動過程 (Metadata Lifecycle)

### 1. 推論階段 (AIStage)
- **輸入**: 原始圖像 Buffer。
- **操作**: 
    - 呼叫 `hailort::ConfiguredInferModel::run_async`。
    - 在非同步回調 (Callback) 中，獲取推論產出的 Tensor 數據。
    - 將 `HailoTensor` 對象加入 Buffer 的 `HailoROI` (Region of Interest) 容器中。
- **輸出**: 帶有原始 Tensor 數據的 Buffer。

### 2. 後處理階段 (PostprocessStage)
- **輸入**: 帶有 `HailoTensor` 的 Buffer。
- **操作**:
    - 透過 `dlopen` 動態載入算法庫（如 `yolo_postprocess.so`）。
    - 執行算法函數，從 `HailoROI` 中讀取 `HailoTensor`。
    - 將解析後的結果（如 `HailoDetection`, `HailoLandmarks`）轉換為結構化對象，並**再次存回**該 Buffer 的 `HailoROI` 中。
- **輸出**: 帶有結構化 AI 結果的 Buffer。

### 3. 疊加顯示階段 (OverlayStage)
- **輸入**: 帶有結構化 AI 結果的 Buffer。
- **操作**:
    - 獲取圖像數據的 DMA 句柄並進行 `dmabuf_sync_start`（確保 CPU 可見）。
    - 從 `HailoROI` 中提取 `HailoDetection` 等對象。
    - 使用 OpenCV 或專屬繪圖庫在圖像上繪製邊界框 (Bounding Box) 或點。
    - 執行 `dmabuf_sync_end`。
- **輸出**: 圖像內容已被修改（已畫框）的 Buffer。

## 關鍵技術點

### 非同步與並發 (Concurrency)
每個 `ThreadedStage` 運行在獨立的執行緒中，並擁有自己的輸入隊列。
- **AIStage** 的非同步性最為關鍵：它不會等待推論結束才返回 `process()`，而是立即釋放 Slot 讓下一幀進入。真正的元數據添加是在 HailoRT 的背景回調中完成的。
- 這種設計最大化了 NPU 的吞吐量 (Throughput)，代價是增加了處理延遲 (Latency)，因為流水線中同時存在多幀數據。

### 零拷貝緩衝區管理 (Zero-copy Buffer Management)
- 使用 **DMABUF** 在 ISP, NPU 與 CPU (OpenCV) 之間傳遞圖像。
- 只有在 `OverlayStage` 需要修改圖像內容時，CPU 才真正接觸圖像像素。
- AI 推論直接讀取 DMA 緩衝區，無需內存拷貝。

### 插件化後處理 (Pluggable Post-processing)
- `PostprocessStage` 不與特定模型綁定。
- 透過動態鏈接庫 (.so) 實現算法解耦。這允許開發者在不重新編譯核心框架的情況下，快速更換 YOLOv8, YOLOv10 或自定義模型。
