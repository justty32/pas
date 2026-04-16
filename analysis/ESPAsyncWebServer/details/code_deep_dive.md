# ESPAsyncWebServer 深入剖析：核心調度與範例導覽

## 1. WebServer.cpp 核心邏輯剖析

### 1.1 請求生命週期 (Request Lifecycle)
在 `WebServer.cpp` 中，伺服器透過 `_server.onClient` 監聽底層 TCP 連線。當新用戶端連線時：
1.  **建立 Request 物件**: 實例化 `AsyncWebServerRequest`。
2.  **綁定事件**: 將 TCP 的 `onData`, `onDisconnect` 等事件與 Request 物件綁定。
3.  **URL 重寫**: 執行 `_rewriteRequest`（處理 `addRewrite` 註冊的規則）。
4.  **處理器分發**: 執行 `_attachHandler`。

### 1.2 處理器分發機制 (`_attachHandler`)
這是伺服器的路由核心。它會遍歷 `_handlers` 列表（由 `addHandler` 或 `server.on` 註冊）：
```cpp
void AsyncWebServer::_attachHandler(AsyncWebServerRequest* request) {
  for (auto& h : _handlers) {
    if (h->filter(request) && h->canHandle(request)) {
      request->setHandler(h.get());
      return;
    }
  }
  request->setHandler(_catchAllHandler); // 預設 404
}
```
*   **Filter**: 允許基於特定條件（如 Host, Method）進行初步篩選。
*   **canHandle**: 檢查 URL 是否匹配（例如 `/api/data`）。
*   **優先權**: 先註冊的 Handler 優先級更高。

## 2. 範例導覽 (Examples Walkthrough)

### 2.1 `SimpleServer` (基礎用法)
這是入門必看範例，展示了：
-   **靜態內容傳送**: `server.on("/", ...)` 配合 `request->send(200, "text/plain", "...")`。
-   **PROGMEM 回應**: 傳送存在 Flash 中的大型 HTML（不佔用 RAM）。
-   **參數處理**: 使用 `request->hasParam("message")` 讀取 GET/POST 參數。
-   **錯誤處理**: 註冊 `onNotFound` 處理 404 情況。

### 2.2 `StreamFiles` (進階 IO)
展示了如何高效地從檔案系統 (`LittleFS`/`SPIFFS`) 傳送大檔案：
-   **非同步檔案讀取**: 避免在傳送大檔案時阻塞整個 Web 伺服器。
-   **Chunked Encoding**: 支援分塊傳輸，適合檔案大小未知或動態生成的場景。

### 2.3 `Filters` (高階路由)
展示了如何使用 `HandlerFilter`：
-   可以限制某些路徑僅能由特定的網域或 IP 訪問。
-   在 `_attachHandler` 階段就會進行攔截。

## 3. 實戰建議：這東西的「精髓」如何應用？

1.  **善用 Lambda**: 就像 `SimpleServer` 中展示的，使用 Lambda 表達式可以讓路由定義與邏輯緊密結合，非常直覺。
2.  **避免在 Handler 中阻塞**: 既然是非同步伺服器，絕對不要在 `onRequest` 回呼中執行 `delay()` 或長時間的循環，否則會破壞整個非同步機制。
3.  **記憶體管理**: 注意 `AsyncWebServerRequest` 是由伺服器管理的，當回應發送完畢後會被自動銷毀。若需保留數據，請務必進行複製。

---
*檔案位置: `analysis/ESPAsyncWebServer/details/code_deep_dive.md`*
