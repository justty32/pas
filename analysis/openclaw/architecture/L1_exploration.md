# Level 1: OpenClaw 初始探索

## 1. 專案基本資訊
- **名稱**: OpenClaw
- **定位**: 個人 AI 助手 (Personal AI Assistant)，強調本地端運行、速度快且始終在線。
- **核心目標**: 提供一個單使用者、跨渠道（WhatsApp, Telegram, Discord 等）的 AI 助手。
- **官方網站**: [openclaw.ai](https://openclaw.ai)
- **技術棧**:
  - **Runtime**: Node.js (推薦 v24+)
  - **語言**: TypeScript
  - **套件管理**: pnpm (Monorepo 結構)
  - **部署**: Docker, Nix, Fly.io, Windows Hub (原生 App)

## 2. 初始目錄分析 (Monorepo)
- `apps/`: 應用程式主體（如 CLI、Hub 或後端服務）。
- `packages/`: 共享的核心邏輯與套件。
- `src/`: 核心原始碼。
- `skills/`: AI 技能定義（可能是與 LLM 互動的工具或腳本）。
- `ui/`: 前端介面（Web 或內嵌 UI）。
- `security/`: 安全相關審核或配置。
- `git-hooks/`: 開發工作流鉤子。

## 3. 關鍵檔案
- `package.json`: 定義依賴與腳本（包含大量 pnpm workspace 配置）。
- `.crabbox.yaml`: 可能是特定的沙盒或容器配置。
- `openclaw.mjs`: CLI 入口點或啟動腳本。
- `VISION.md`: 專案願景與長期目標。
- `AGENTS.md`: 可能定義了 Agent 的行為準則或內建模型。

## 4. 下一步計畫
- **Level 2**: 分析核心模組權責。深入 `packages/` 與 `src/` 尋找 Agent 的執行引擎與閘道 (Gateway) 實作邏輯。
- **探索啟動流程**: 從 `package.json` 的 `scripts` 開始，追蹤 `openclaw onboard` 的執行路徑。
