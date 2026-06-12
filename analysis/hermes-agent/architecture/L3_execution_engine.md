# hermes-agent 架構分析 - Level 3: 對話迴圈與工具執行深度剖析

## 1. 對話驅動引擎 (Conversation Loop)
位於 `agent/conversation_loop.py` 的 `run_conversation` 是 Agent 的心臟。它並非簡單的請求-回應，而是一個具備容錯與中斷機制的狀態機。

### 核心功能：
- **模型互動與流式處理**: 處理與 LLM 的通訊，支援流式輸出與即時中斷（Interrupt）。
- **工具調用循環 (Tool Call Loop)**: 當模型要求調用工具時，進入分派邏輯，並將結果回傳給模型繼續對話，直到模型產出最終回覆。
- **上下文管理**: 在模型請求前，動態計算 token 數，並在必要時觸發記憶壓縮（Compression）。
- **錯誤分類與恢復**: 使用 `agent/error_classifier.py` 判斷 API 錯誤（如 Rate Limit、Auth Fail）並執行對應的退避重試（Backoff）。

## 2. 工具註冊與發現機制 (Registry & Discovery)
專案採用「自註冊」模式，降低了核心模組與具體功能間的耦合。

### 註冊流程：
1. **工具模組**: 位於 `tools/` 下的各個 `.py` 檔案在被載入時，會呼叫 `tools.registry.register()`。
2. **中繼層 (Registry)**: `tools/registry.py` 維護一個 `ToolRegistry` 單例，儲存所有 `ToolEntry`（包含 Schema, Handler, Check 函數等）。
3. **動態發現**: `model_tools.py` 啟動時呼叫兩個不同機制的發現函數：
   - `discover_builtin_tools()`（定義於 `tools/registry.py:57-74`）：掃描 `tools/*.py` 目錄並匯入模組，觸發各模組的自註冊呼叫。
   - `discover_plugins()`（來自 `hermes_cli/plugins.py`）：讀取各來源目錄下的 `plugin.yaml` manifest，與前者的「掃描目錄匯入」機制不同。

## 3. 工具執行器 (Tool Executor)
位於 `agent/tool_executor.py`，負責將 LLM 的調用請求轉化為實際的代碼執行。

### 執行策略：
- **順序執行 (`_execute_tool_calls_sequential`)**: 用於需要嚴格順序或具備副作用的操作。
- **並行執行 (`_execute_tool_calls_concurrent`)**: 使用 `ThreadPoolExecutor`（預設 8 個 Worker）同時執行多個工具調用，顯著提升複雜任務（如多網頁搜尋）的效率。
- **安全護欄 (Guardrails)**: 在執行具備破壞性（Destructive）的命令前，可透過 `ToolCallGuardrailController` 進行攔截或要求使用者確認。

## 4. 同步與非同步橋接 (Sync-Async Bridging)
由於 Agent 主迴圈主要是同步的（以簡化狀態管理），但許多現代庫（如 `httpx`, `OpenAI`）是異步的，`model_tools.py` 實作了關鍵的橋接邏輯：

- **`_run_async`**: 在同步環境中安全執行協程（Coroutine）。
- **持久化 Event Loop**: 為主執行緒與每個 Worker 執行緒維護長效的 `asyncio` Event Loop，避免頻繁開關導致的「Event loop is closed」錯誤。
- **逾時管理**: 支援 300 秒的硬性逾時限制，並在逾時後強制取消協程以防止執行緒洩漏。
