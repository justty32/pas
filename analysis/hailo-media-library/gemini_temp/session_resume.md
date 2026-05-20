# Hailo Media Library 分析進度彙整 (2026-05-12)

## 當前理解摘要
- **架構核心**: 採用的「媒體基礎設施 (Media Lib) + AI 流水線 (Analytics) + 動態後處理 (Post-process)」三層架構。
- **推論機制**: 高度依賴 HailoRT 的非同步 API，透過 `AIStage` 的回調機制在原始 Buffer 的 `HailoROI` 中注入 `HailoTensor`。
- **解耦設計**: 後處理邏輯以 `.so` 插件形式存在，透過 `dlopen` 加載，實現了模型與框架的完全解耦。
- **GStreamer**: 提供豐富的元件（frontend, multi_resize, encoder 等）封裝，支持標準的媒體開發流程。

## 已完成分析
- [x] **Level 1**: 初始探索與專案結構確認。
- [x] **Level 2**: 核心模組職責劃分 (`architecture/core_modules.md`)。
- [x] **Level 3**: AI 流水線與元數據流動深層機制 (`details/pipeline_metadata_flow.md`)。
- [x] **Level 4 (部分)**: GStreamer 元件庫概覽與單元測試架構探索。

## 剩餘待辦事項 (建議後續路徑)
1.  **Level 4 深化**: 詳細剖析 `hailomedialibfrontend` 與 `hailomedialibencoder` 的 GStreamer 實現細節。
2.  **Level 5 (自定義整合)**: 實作一個「自定義 MLP 後處理庫」的完整範例，模擬如何從 Tensor 提取結果並注入自定義元數據。
3.  **Level 6 (效能調優)**: 探索 `ConfigManager` 的具體參數如何影響 ISP 與 AI 效能（如熱限制下的 Profile 切換）。

## 上下文摘要 (Context for Next Session)
當前正停留在對 GStreamer 元件實現與單元測試範例的觀察。`hailo-analytics` 中的 `ocr_pipeline_tests.cpp` 是一個極佳的複雜流水線參考範例。關於 MLP 的需求，核心框架中雖無內建，但可透過擴充 `PostprocessStage` 輕易實現。
