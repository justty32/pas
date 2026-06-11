# hermes-agent 架構分析 - Level 1: 初始探索

## 1. 專案概述
`hermes-agent` 是由 Nous Research 開發的「自我改進型 AI Agent」。其核心特色在於內建的學習迴圈：能從經驗中建立技能、在使用中改進技能、跨會話搜尋過往對話，並建立深度的使用者模型。

## 2. 技術棧 (Tech Stack)
- **語言**: Python 3.11+ (主要), Node.js (部分組件如 Dashboard)
- **套件管理**: `uv` (推薦), `pip`
- **核心庫**:
    - `openai`: LLM 互動（支援多種相容後端）
    - `pydantic`: 資料驗證與型別定義
    - `prompt_toolkit`: 互動式 CLI 介面 (TUI)
    - `fastapi`, `uvicorn`: Web 控制台與 API
    - `croniter`: 排程任務執行
    - `psutil`: 跨平台行程管理

## 3. 目錄結構
- `agent/`: 核心邏輯，包含對話迴圈、記憶管理、工具執行、模型適配器。
- `hermes_cli/`: CLI 指令實作、設定檔管理、安裝精靈。
- `gateway/`: 外部通訊平台（Telegram, Discord, Slack, Matrix 等）的適配層。
- `skills/`: 模組化的 Agent 技能庫（如 Google Workspace, GitHub, 媒體處理等）。
- `plugins/`: 系統擴充套件（如 瀏覽器、記憶系統、看板等）。
- `providers/`: 不同 LLM 供應商的適配邏輯。
- `tools/`: 內部工具輔助指令。
- `web/`: 網頁端 Dashboard。

## 4. 入口點 (Entry Points)
- `hermes`: `hermes_cli.main:main` - 主要的互動式 CLI。
- `hermes-agent`: `run_agent:main` - 執行 Agent 實例的核心腳本。
- `hermes-acp`: `acp_adapter.entry:main` - Agent Client Protocol 適配器。

## 5. 構建與執行指令
- **安裝**: `pip install -e .` 或使用官方提供的 install 腳本。
- **啟動對話**: `hermes`
- **設定模型**: `hermes model`
- **啟動閘道**: `hermes gateway`
- **診斷**: `hermes doctor`
