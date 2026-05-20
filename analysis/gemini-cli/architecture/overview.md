# Gemini CLI 架構概觀 (Level 1 分析)

## 1. 專案基本資訊
- **名稱**: Gemini CLI
- **定位**: 將 Gemini AI 能力帶入終端機的開源代理工具 (AI Agent)。
- **許可證**: Apache-2.0

## 2. 技術棧 (Technical Stack)
- **核心語言**: TypeScript
- **執行環境**: Node.js (>=20.0.0)
- **UI 框架**: [Ink](https://github.com/vadimdemedes/ink) (基於 React 19 的 CLI UI 渲染庫)
- **測試框架**: Vitest
- **打包/編譯**: esbuild
- **套件管理**: npm (Workspaces)
- **程式碼規範**: ESLint, Prettier

## 3. 專案結構 (Monorepo)
專案採用 Monorepo 結構，主要模組位於 `packages/` 目錄下：
- `packages/cli`: 終端機 UI、輸入處理與顯示渲染。
- `packages/core`: 後端邏輯、Gemini API 協調、提示詞構建與工具執行。
- `packages/sdk`: 提供給開發者嵌入 Gemini CLI 能力的 SDK。
- `packages/devtools`: 整合開發工具（網路/控制台檢查器）。
- `packages/test-utils`: 共享的測試工具集。
- `packages/a2a-server`: 實驗性的 Agent-to-Agent 伺服器。
- `packages/vscode-ide-companion`: 與 CLI 配對的 VS Code 擴展。

## 4. 核心功能
- **模型存取**: 直接存取 Gemini 模型（如 Gemini 2.0 Flash/Pro）。
- **工具集成**: 內建 Google Search、檔案系統操作、Shell 執行、Web Fetch 等工具。
- **擴展性**: 支援 MCP (Model Context Protocol) 協議。
- **開發體驗**: 提供沙盒環境、效能與記憶體測試工具。

## 5. 入口點 (Entry Points)
- **開發模式**: `npm run start` (執行 `scripts/start.js`)
- **打包入口**: `bundle/gemini.js` (由 `npm run bundle` 產生)
- **開發測試**: `npm run test` (Vitest)
