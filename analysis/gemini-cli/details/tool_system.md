# Gemini CLI 工具系統深度剖析 (Level 3 分析)

## 1. 工具架構
Gemini CLI 的工具系統採用宣告式 (Declarative) 的架構，主要組件位於 `packages/core/src/tools/`：

- **`ToolInvocation` 介面**: 定義了工具的生命週期，包括參數驗證、描述生成、核准檢查與執行。
- **`BaseToolInvocation` 類別**: 提供通用邏輯，特別是與 `MessageBus` 的整合。
- **工具實作**: 每個工具（如 `shell`, `edit`, `read-file`）都有專屬的 TS 檔案，封裝其具體行為。

## 2. 工具核准流程 (Confirmation Flow)
為了確保安全，Gemini CLI 實作了嚴謹的核准機制：
1. **策略檢查**: 根據 `policy/` 定義的策略判斷是否需要核准。
2. **Message Bus**: 工具透過 `messageBus.requestConfirmation()` 發送請求。
3. **UI 互動**: `packages/cli` 接收到請求後，渲染 `ToolConfirmationFullFrame` 供使用者操作。
4. **回傳決策**: 使用者的決策（允許、拒絕、以後一律允許等）經由 Message Bus 回傳給工具。

## 3. 特殊工具機制
- **背景執行**: `shell` 工具支援 `is_background` 參數，利用 `pgrep` 等技術在背景管理進程。
- **沙盒環境**: 支援 `macos-seatbelt` 或 Docker 等沙盒，限制工具對系統資源的存取。
- **MCP 整合**: `mcp-tool.ts` 作為橋接器，將 MCP 伺服器的動態工具轉換為 CLI 內部工具格式。

## 4. 錯誤處理
- **`ToolErrorType`**: 統一的錯誤分類。
- **自動摘要**: 長工具輸出會經過 `summarizeToolOutput` 處理，避免 token 溢出。
