# Level 1 初始探索 - ESPAsyncWebServer

## 專案概述 (Project Overview)
`ESPAsyncWebServer` 是一個專為 ESP32、ESP8266 與 RP2040 開發的非同步 HTTP 與 WebSocket 伺服器函式庫。它是對原始 `me-no-dev/ESPAsyncWebServer` 的分支（Fork），包含了大量的錯誤修復與現代化功能（如 Middleware 支援、ArduinoJson 7 相容性）。

## 技術棧 (Tech Stack)
- **程式語言**: C++
- **框架**: Arduino Framework, ESP-IDF (相容性)
- **平台支援**: ESP32, ESP8266, RP2040
- **構建系統**: PlatformIO, CMake (ESP-IDF)
- **依賴項**: 
  - `AsyncTCP` (ESP32) 或 `ESPAsyncTCP` (ESP8266)
  - `ArduinoJson` (可選，用於 JSON 處理)

## 核心目錄結構 (Core Directory Structure)
- `src/`: 核心原始碼
  - `ESPAsyncWebServer.h`: 函式庫入口
  - `WebServer.cpp`: 伺服器主邏輯
  - `WebRequest.cpp`: 請求處理
  - `WebResponses.cpp`: 回應處理
  - `WebHandlers.cpp`: 請求分發與處理器
  - `Middleware.cpp`: 中間件機制
  - `AsyncWebSocket.h/cpp`: WebSocket 支援
  - `AsyncEventSource.h/cpp`: Server-Sent Events (SSE) 支援
- `examples/`: 範例程式碼，包含 HTTP, WebSocket, Middleware 等用法。
- `docs/`: 相關說明文件。

## 關鍵特性
1. **非同步架構**: 基於事件驅動，不阻塞主迴圈。
2. **中間件 (Middleware)**: 支援預處理請求（如認證、速率限制、CORS）。
3. **WebSockets & SSE**: 內建支援實時雙向通信與單向事件流。
4. **Resumable Downloads**: 支援 HTTP 範圍請求（Range requests）。
5. **多平台支援**: 統一的 API 介面支援多種晶片。

---
*檔案位置: `analysis/ESPAsyncWebServer/architecture/level1_exploration.md`*
