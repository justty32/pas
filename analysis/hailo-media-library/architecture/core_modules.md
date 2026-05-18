# Hailo Media Library 核心模組職責分析 (Level 2)

## 模組概覽
本專案由三個主要子模組組成，各自承擔媒體處理生命週期的不同階段：

### 1. hailo-media-library (媒體基礎設施)
這是最底層的模組，直接與 Hailo-15 的硬體加速器（如 ISP, Encoder）交互。
- **職責**:
    - **Frontend (ISP)**: 處理攝像頭輸入、圖像縮放、顏色轉換及圖像增強（如 HDR, 降噪）。
    - **Encoder**: 提供 H.264/H.265 硬體編碼。
    - **OSD (On-Screen Display)**: 在影片流上疊加圖形、文字或隱私遮罩 (Privacy Mask)。
    - **Buffer Management**: 透過 `HailoMediaLibraryBuffer` 提供跨模組的高效零拷貝 (Zero-copy) 緩衝區傳遞。
- **關鍵類別**:
    - `MediaLibrary`: 頂層入口，管理前端與編碼器的生命週期。
    - `Frontend`: 抽象硬體輸入與 ISP 功能。
    - `Encoder`: 封裝編碼參數與操作。

### 2. hailo-analytics (AI 流水線管理)
建立在 `hailo-media-library` 之上，提供更高層次的 AI 應用開發框架。
- **職責**:
    - **Pipeline Abstraction**: 使用 `Pipeline` 與 `Stage` 概念構建非同步的推論圖。
    - **Inference Orchestration**: 管理 `HailoRT` 資源，負責模型加載與非同步推論執行。
    - **Graph Building**: 透過 `PipelineBuilder` 根據設定（JSON 或程式碼）自動連結 Source, Inference Stage, Post-process Stage 與 Sink。
- **關鍵類別**:
    - `Pipeline`: 容器類，管理 Stage 的啟動與停止順序（Sink -> General -> Source）。
    - `AIStage`: 核心推論階段，整合模型輸入與輸出。
    - `PipelineBuilder`: 負責解析配置並實例化完整的 AI 處理鏈。

### 3. hailo-postprocess (結果解析與算法)
針對推論產出的 Tensor 數據進行具體的數學處理。
- **職責**:
    - **Tensor Decoding**: 將原始推論數據轉換為結構化對象（如 `Detection`, `Landmark`）。
    - **Common Algorithms**: 提供 NMS (Non-Maximum Suppression)、Softmax、向量點積 (Dot Product) 等通用運算。
    - **Specific Models**: 針對不同模型（YOLO, CLIP, LinkNet 等）實作專屬的後處理邏輯。
- **關鍵文件**:
    - `postprocesses/detection/yolo_postprocess.cpp`: YOLO 偵測後處理。
    - `postprocesses/clip/clip.cpp`: CLIP 文本/圖像特徵匹配處理。

## 模組間協作流程
1.  **數據採集**: `hailo-media-library` 的 `Frontend` 從硬體獲取圖像並放入 `HailoMediaLibraryBuffer`。
2.  **推論觸發**: `hailo-analytics` 的 `FrontendStage` 訂閱前端輸出，將 Buffer 送入 `Pipeline`。
3.  **執行推論**: `AIStage` 呼叫 HailoRT 執行 NPU 推論。
4.  **後處理**: 推論完成後，`AIStage` 呼叫 `hailo-postprocess` 中的函數解析結果。
5.  **輸出與顯示**: 解析後的 Metadata 隨 Buffer 一起傳遞至 `Sink`（如 `OverlayStage` 畫框，或 `UDPSink` 發送）。
