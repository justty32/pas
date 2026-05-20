# Gemini CLI 提示詞建構機制 (Level 3 分析)

## 1. 核心設計理念
Gemini CLI 的 System Prompt 是動態組合而成的，旨在根據當前的代理角色、任務上下文與安全性設定，提供最精簡且高效的指令。

## 2. 組件化組合 (`prompts/snippets.ts`)
提示詞由多個 `render` 函數組合：
- `renderPreamble`: 定義 AI 的身份與當前模式（如：Interactive, Plan, YOLO）。
- `renderCoreMandates`: 定義核心規範，如安全準則、Context 效率、工程標準。
- `renderSubAgents`: 列出可用的子代理及其專長。
- `renderPrimaryWorkflows`: 定義研發、策略、執行的標準作業流程。
- `renderOperationalGuidelines`: 提供關於 Tone, Style 與工具使用的細部指引。

## 3. 模式切換 (Approval Modes)
- **Interactive**: 一般模式，每一步都與使用者互動。
- **Plan**: 專注於生成開發計畫。
- **YOLO (Autonomous)**: 最小化中斷，主動決策。
- **Auto-Edit**: 自動應用程式碼修改。

## 4. 階層式記憶 (Hierarchical Memory)
提示詞中會注入記憶內容：
- **Global Memory**: 使用者的跨專案偏好。
- **Project Memory**: 專案特定的筆記（`MEMORY.md`）。
- **Project Instructions**: 專案內部的 `GEMINI.md` 或 `PROJECT_SPEC.md`。

## 5. 提示詞版本控制
- **Legacy Snippets**: 專案保留了 `snippets.legacy.ts` 作為舊版提示詞的快照，確保舊有機制的穩定性。
