# Gemini CLI MCP 整合深度剖析 (Level 4 分析)

## 1. MCP 客戶端架構
Gemini CLI 作為 Model Context Protocol (MCP) 的客戶端，允許動態整合外部工具伺服器。

- **`McpClientManager`**: 負責發現、連接與管理多個 MCP 伺服器。
- **`McpClient`**: 封裝了與單個 MCP 伺服器的通訊邏輯，支援 stdio 與 HTTP 傳輸協議。
- **`DiscoveredMCPTool`**: 將 MCP 伺服器提供的工具宣告轉換為 Gemini CLI 內部的工具格式。

## 2. 工具命名規範 (FQNs)
為了避免命名衝突，MCP 工具使用完全限定名稱 (Fully Qualified Names)：
- 格式: `mcp_{server_name}_{tool_name}`
- 例如: `mcp_google-workspace_list_emails`
- CLI 支援使用萬用字元（如 `mcp_google-workspace_*`）來配置安全性策略。

### 3. 認證機制 (`McpAuthProvider`)
MCP 整合支援多種認證方式：
- **`GoogleCredentialProvider`**: 專為 Google API 設計，支援 ADC (Application Default Credentials) 與 OAuth2。
- **OAuth 整合**: 提供標準的 OAuth2 流程，包含權杖儲存與自動重新整理。
- **自訂標頭**: 支援在 MCP 配置中直接定義 HTTP 標頭。

## 4. 資源管理 (MCP Resources)
除了工具，MCP 還提供資源讀取能力：
- `list-mcp-resources.ts`: 獲取伺服器提供的資源清單。
- `read-mcp-resource.ts`: 讀取特定 URI 的資源內容，將其注入對話上下文。

## 5. 特殊處理 (Edge Cases)
- **Xcode 修正**: `XcodeMcpBridgeFixTransport` 專門修正了 Xcode 26.3 `mcpbridge` 傳回不符規範回應的問題。
- **名稱清洗**: 透過 `generateValidName` 確保伺服器與工具名稱符合 Gemini API 的規範要求。
