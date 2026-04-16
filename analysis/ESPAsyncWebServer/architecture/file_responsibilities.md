# ESPAsyncWebServer 原始碼檔案職責分析

## 核心架構 (Core Architecture)
| 檔案名稱 | 職責描述 |
| :--- | :--- |
| `ESPAsyncWebServer.h` | 函式庫主頭文件，定義類別關係與常數。 |
| `WebServer.cpp` | `AsyncWebServer` 核心實作，負責監聽、連線管理與請求分發。 |
| `WebRequest.cpp` | `AsyncWebServerRequest` 實作，解析並儲存 HTTP 請求細節。 |

## 回應系統 (Response System)
| 檔案名稱 | 職責描述 |
| :--- | :--- |
| `WebResponses.cpp` | 實作多種回應類型：靜態文字、檔案、PROGMEM、Stream、Chunked。 |
| `WebResponseImpl.h` | 回應系統的內部實作細節。 |
| `ChunkPrint.cpp/h` | 將資料流（Stream）轉換為 HTTP 分塊（Chunked）格式的工具。 |

## 路由與中間件 (Routing & Middleware)
| 檔案名稱 | 職責描述 |
| :--- | :--- |
| `WebHandlers.cpp` | 路由處理邏輯，包含 Static Handlers 與 Callback Handlers。 |
| `WebHandlerImpl.h` | 處理器介面定義。 |
| `Middleware.cpp` | 中間件機制實作，支援請求前置處理。 |

## 擴展協定 (Protocols)
| 檔案名稱 | 職責描述 |
| :--- | :--- |
| `AsyncWebSocket.cpp/h` | 完整的 WebSocket 伺服器實作，包含連線管理與 Frame 處理。 |
| `AsyncEventSource.cpp/h` | Server-Sent Events (SSE) 實作，支援伺服器推送。 |
| `AsyncJson.cpp/h` | 集成 ArduinoJson，提供非同步 JSON 處理。 |
| `AsyncMessagePack.cpp/h` | 支援 MessagePack 二進位序列化格式。 |

## 安全與工具 (Security & Utilities)
| 檔案名稱 | 職責描述 |
| :--- | :--- |
| `WebAuthentication.cpp/h` | HTTP 認證（Basic/Digest）實作。 |
| `AsyncWebHeader.cpp` | HTTP 標頭物件封裝。 |
| `BackPort_SHA1Builder.cpp/h` | SHA1 加密輔助（用於 WebSocket 握手）。 |
| `literals.h` | 常用字串字面量定義。 |

---
*檔案位置: `analysis/ESPAsyncWebServer/architecture/file_responsibilities.md`*
