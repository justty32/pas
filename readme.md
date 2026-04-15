# Project Analysis System (PAS)

本專案是一個基於 LLM (如 Gemini, Claude 等) 的結構化工作空間，旨在對 GitHub 上的開源專案進行深度架構分析、原始碼剖析與開發教學編寫。

## 🚀 專案願景

透過標準化的 SOP，讓不同的 AI Agent 能夠並行分析多個專案，並產出一致、高品質且可視化的分析報告，最終託管於 GitHub 供社群參考。

## 📂 目錄結構

```text
pas/
├── projects/           # (Git Ignore) 存放克隆的專案原始碼
├── analysis/           # 核心分析結果輸出目錄
│   └── <project_name>/ # 特定專案的分析空間
│       ├── architecture/ # 架構分析與模組職責
│       ├── tutorial/     # 目標導向的開發教學
│       ├── answers/      # 特定技術問題解答
│       ├── details/      # 原始碼深度剖析
│       └── session_log.md# Agent 操作日誌
├── GEMINI.md           # Gemini Agent 的核心指令與規範
├── CLAUDE.md           # Claude Agent 的核心指令與規範 (待建立)
├── index.md            # 全域專案分析進度清單
└── readme.md           # 本文件
```

## 🤖 多 Agent 協作規範

本工作空間設計支援多個 Agent (Gemini, Claude, etc.) 同時運作，請遵守以下規範以避免衝突：

1.  **專案隔離**：每個 Agent 在開始工作前，必須確認其工作範圍僅限於 `analysis/<特定專案>/` 子目錄。
2.  **指令一致性**：`GEMINI.md` 與 `CLAUDE.md` 應保持 SOP 邏輯一致，確保產出的文件格式統一。
3.  **自動留檔**：Agent 產出的任何重要見解必須同步寫入對應的 Markdown 文件，嚴禁僅在對話框回覆。
4.  **操作日誌**：每次操作後，必須在該專案的 `session_log.md` 留下簡短的一句話紀錄，以便其他 Agent 或人類快速追蹤進度。

## 🛠️ 如何開始

1.  **克隆目標專案**：將專案克隆至 `projects/` 目錄。
    ```bash
    git clone <url> projects/<project_name>
    ```
2.  **初始化分析環境**：
    告訴 Agent：「請依照 `GEMINI.md` (或 `CLAUDE.md`) 的 SOP，為 `projects/<project_name>` 初始化分析環境。」
3.  **開始深度分析**：
    Agent 將依照 Level 1 至 Level 6 的路徑進行分析，並將結果存儲於 `analysis/`。

## 📄 授權規範

本專案僅託管分析後的「衍生作品」與「心得筆記」。所有在 `projects/` 下的原始碼均受其原專案授權條款約束，且預設不會被提交至本倉庫。
