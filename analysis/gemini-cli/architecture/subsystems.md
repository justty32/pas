# Gemini CLI 子系統職責 (Level 2 分析)

## 1. CLI 表現層 (`packages/cli`)
負責與使用者直接互動，處理終端機渲染與輸入。

- **UI 框架**: 使用 Ink (React) 構建。
- **主要組件**:
  - `gemini.tsx`: 應用程式主入口。
  - `interactiveCli.tsx`: 處理循環互動式對話。
  - `ui/`: 包含各式 UI 元件（如訊息框、狀態列、進度條）。
- **協議處理**: `acp/` 目錄處理 Agent Client Protocol，負責與後端代理通訊。

## 2. 核心邏輯層 (`packages/core`)
專案的後端大腦，負責 AI 邏輯、工具執行與狀態管理。

- **代理管理 (`agent/`, `agents/`)**:
  - `agent-session.ts`: 管理單一對話 Session。
  - `registry.ts`: 註冊並管理可用的代理角色（如 `codebase-investigator`, `generalist`）。
  - `local-executor.ts`: 負責在本地執行代理指令。
- **工具系統 (`tools/`)**:
  - 定義 AI 代理可調用的各類工具，如讀寫檔案、執行 Shell 命令、存取網路等。
- **提示詞工程 (`prompts/`)**:
  - `snippets.ts`: 定義系統提示詞的各個片段。
  - `modelPromptService.ts`: 根據目前上下文與代理角色構建最終的提示詞。
- **模型路由 (`routing/`)**:
  - 根據任務需求與模型可用性選擇最適用的 Gemini 模型（如 Flash 2.0）。
- **配置與策略 (`config/`, `policy/`)**:
  - 管理使用者設定與安全性策略（例如執行危險指令前的確認機制）。

## 3. 擴展與通訊
- **MCP (`mcp/`)**: 支援 Model Context Protocol，允許 CLI 作為 MCP 客戶端連接外部工具伺服器。
- **A2A (`packages/a2a-server`)**: 支援代理間 (Agent-to-Agent) 的通訊與協作。

## 4. 關鍵交互流程
1. **輸入**: 使用者在 `packages/cli` 輸入指令或問題。
2. **路由**: `core` 的路由服務決定處理該請求的代理。
3. **構建**: `prompts` 服務構建包含上下文與工具說明的提示詞。
4. **調用**: 透過 API 調用 Gemini 模型。
5. **執行**: 若模型回傳工具調用請求，`core/tools` 負責執行並回傳結果。
6. **渲染**: 執行結果透過 `cli` 的 Ink 組件渲染回終端機介面。
