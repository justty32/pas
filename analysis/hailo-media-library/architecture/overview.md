# Hailo Media Library 架構分析 (Level 1)

## 專案概述
Hailo Media Library 是專為 Hailo-15 晶片設計的媒體控制與處理庫，整合了影片擷取、編碼、OSD（螢幕顯示）與圖像增強功能。它提供了一套統一的 C++ API，並可與 GStreamer 整合。

## 核心模組
1.  **hailo-media-library**:
    *   負責底層媒體處理（ISP, Encoder, OSD）。
    *   API 定義於 `api/include/media_library/`。
    *   核心類：`MediaLibrary` (管理整體流程), `Frontend` (處理輸入與 ISP), `Encoder` (處理編碼)。
2.  **hailo-analytics**:
    *   提供 AI 推論流水線 (Pipeline) 管理。
    *   封裝了對 HailoRT 的呼叫，支持多階段非同步推論。
    *   示例應用：CLIP, Object Detection, Face Landmark 等。
3.  **hailo-postprocess**:
    *   針對 AI 推論結果進行後處理（如 NMS, CLIP Embedding 處理, OCR 等）。
    *   部分邏輯在 CPU 上以 C++ 實現（例如 CLIP 的向量點積與 Softmax）。

## C++ API 關鍵特性
- **非同步推論**: 使用 `HailortAsyncStage` 進行高效推論。
- **自定義流水線**: 透過 `PipelineBuilder` 組合不同階段（Source, Stage, Sink）。
- **緩衝區管理**: 提供 `HailoMediaLibraryBuffer` 進行跨模組緩衝傳遞。

## 關於 MLP (Multi-Layer Perceptron)
- 目前在 codebase 中未發現名為 "MLP" 的獨立模組。
- 在 `hailo-analytics/apps/clip` 中發現了 C++ 實現的線性投影層 (`apply_text_projection`)，這本質上是 MLP 的基本組成部分（全連接層）。
- 推測使用者的需求是：**如何使用 C++ 在該框架下實現自定義的 MLP 推論與訓練邏輯**。
