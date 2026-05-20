# Gemini CLI 代理生命週期與子代理機制 (Level 4 分析)

## 1. 代理註冊與載入 (`AgentRegistry`)
`AgentRegistry` 是管理所有 AI 代理的核心：
- **內建代理**: 預先載入 `codebase_investigator`, `cli_help`, `generalist` 等。
- **動態載入**: 支援從使用者目錄 (`~/.gemini/agents/`) 與專案目錄 (`.gemini/agents/`) 載入代理定義。
- **代理類型**:
  - `local`: 直接在 CLI 進程中執行的代理。
  - `remote`: 透過 A2A (Agent-to-Agent) 協議連接的遠端代理。

## 2. 子代理執行流程 (`LocalAgentExecutor`)
當主代理調用一個子代理工具時：
1. **環境隔離**: `LocalAgentExecutor` 為子代理建立獨立的 `ToolRegistry`、`PromptRegistry` 與 `MessageBus`。
2. **工具限制**: 子代理通常只被授予特定工具的權限（例如 `codebase_investigator` 只能讀取檔案，不能修改）。
3. **循環執法**: 子代理進入自己的 `AgentLoop`，持續思考與調用工具，直到調用 `complete_task`。
4. **結果回報**: 子代理生成的 JSON 報告會傳回給主代理作為工具執行結果。

## 3. 案例分析：`Codebase Investigator`
- **目標**: 建立程式碼的心智模型與架構映射。
- **權限**: 僅限讀取型工具 (`ls`, `read_file`, `glob`, `grep`)。
- **策略**: 採用「思考鏈 (CoT)」與「刮刮板 (Scratchpad)」機制，要求代理在每一步紀錄觀察與待解決問題。
- **模型選擇**: 優先選用支援現代功能的模型（如 Gemini 2.0 Flash），以利用其強大的推理能力。

## 4. 安全與核准
- **層級化核准**: 子代理的工具請求會透過衍生出的 `MessageBus` 傳回主代理。
- **自動化標籤**: 子代理調用的工具會被標註來源，以便使用者識別是哪個代理在操作。
