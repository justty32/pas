# hermes-agent 架構分析 - Level 2: 核心模組職責

## 1. 核心元件概覽

| 模組 | 職責描述 | 關鍵檔案 |
|---|---|---|
| **對話引擎 (Conversation Engine)** | 驅動 Agent 的主迴圈，負責「模型呼叫 -> 工具分派 -> 結果回傳 -> 狀態更新」。 | `agent/conversation_loop.py` |
| **Agent 初始化 (Initialization)** | 處理複雜的 `AIAgent` 實例初始化，包含模型偵測、憑證解析、環境準備。 | `agent/agent_init.py`, `run_agent.py` |
| **工具執行器 (Tool Executor)** | 負責解析 LLM 產出的工具調用請求，並執行對應的技能腳本。 | `agent/tool_executor.py` |
| **記憶管理 (Memory Management)** | 管理長短期記憶、會話壓縮、跨會話搜尋與回憶。 | `agent/memory_manager.py`, `agent/conversation_compression.py` |
| **提示詞建構 (Prompt Builder)** | 根據當前上下文、記憶、技能與使用者資訊動態合成 System Prompt 與 User Message。 | `agent/prompt_builder.py`, `agent/system_prompt.py` |
| **通訊閘道 (Gateway)** | 將不同通訊平台（如 Telegram）的訊息轉換為 Agent 通用格式，並處理非同步回應與語音轉文字。 | `gateway/`, `hermes_cli/gateway.py` |
| **CLI 系統 (CLI System)** | 提供豐富的子指令與互動介面，管理全域配置與外掛。 | `hermes_cli/main.py`, `hermes_cli/config.py` |

## 2. 核心資料流 (Data Flow)

### 2.1 訊息處理流程 (CLI 模式)
1. **User Input**: `hermes_cli/main.py` 接收使用者輸入。
2. **Context Assembly**: `agent/prompt_builder.py` 彙整歷史紀錄、啟用技能、記憶片段與 System Prompt。
3. **LLM Request**: `agent/chat_completion_helpers.py` 透過 `openai` 庫（或適配器）發送請求。
4. **Tool Call (Optional)**: 
   - LLM 回傳工具調用請求。
   - `agent/tool_executor.py` 執行對應的 `skills/` 或 `plugins/` 腳本。
   - 結果回傳給 LLM 繼續生成。
5. **Response Display**: 透過 `agent/display.py` 將模型回應流式輸出到終端。

### 2.2 閘道通訊流程 (Gateway 模式)
1. **Platform Event**: `gateway/platforms/`（如 `telegram.py`）接收外部訊息。
2. **Gateway Process**: `gateway/` 主程序將訊息派發給對應的 `AIAgent` 實例。
3. **Agent Loop**: 進入 `run_conversation` 處理邏輯。
4. **Callback**: 完成後透過 `status_callback` 回傳訊息至平台。

## 3. 擴充機制 (Extensibility)
- **Skills**: 基於 `SKILL.md` 定義的獨立功能塊，通常包含 Python 腳本，透過 shell 命令調用。
- **Plugins**: 更深層的系統擴充，可以介入對話流、提供自訂 UI 或後端服務。
- **Providers**: 位於 `providers/`，可新增自訂的 LLM 供應商適配器。
