# Project Analysis System (PAS)

本專案是一個基於 LLM（如 Gemini、Claude 等）的結構化工作空間，支援對外部專案進行**深度架構分析、衍生小專案開發與 Patch 製作**。

## 工作模式

| 模式 | 適用情境 | SOP |
|---|---|---|
| **Analysis** | 初次接觸陌生專案，建立結構化分析 | `analysis_workflow.md` |
| **Create** | 基於分析產物建立獨立衍生小專案 | `create_workflow.md` |
| **Patch** | 製作可被 agent 套用至原專案的獨立 Patch 小專案 | `patch_workflow.md` |

外部專案不一定是 git repository。`pas` 本身不使用 git submodule，GitHub 連結以純文字記錄於對應的 Markdown 中。

## 目錄結構

```
pas/
├── projects/           # 克隆的外部專案原始碼（直接 clone，不用 submodule）
├── analysis/           # 各專案的分析產物
│   └── <project_name>/
│       ├── architecture/   # 架構分析（Level 1-6）
│       ├── tutorial/       # 目標導向的開發教學
│       ├── answers/        # 具體問答的解答
│       ├── details/        # 原始碼深度剖析
│       ├── others/         # 雜項（含 patches/ 子目錄）
│       ├── html/           # HTML 導覽層（.md 過多時生成，降低瀏覽認知負擔）
│       ├── gemini_temp/    # 會話進度保存文件
│       └── session_log.md  # Agent 操作日誌
├── derived/            # 衍生小專案（Create 模式產出）
│   └── <project_name>/
│       ├── PROJECT.md      # 衍生目標、參照素材、技術棧
│       ├── session_log.md
│       └── src/, tests/, docs/
├── patches/            # Patch 小專案（Patch 模式產出）
│   └── <patch_name>/
│       ├── PATCH.md        # Patch 目標與分析依據
│       ├── APPLY.md        # Agent 套用操作手冊
│       ├── session_log.md
│       └── src/            # 完整版修改檔案（模擬原專案相對路徑）
├── analysis_workflow.md    # Analysis 模式 SOP
├── create_workflow.md      # Create 模式 SOP
├── patch_workflow.md       # Patch 模式 SOP
├── GEMINI.md               # Gemini Agent 規範
├── CLAUDE.md               # Claude Agent 規範
├── index.md                # 全域專案分析進度清單
└── readme.md               # 本文件
```

## 多 Agent 協作規範

1. **模式隔離**：每個 Agent 在開始工作前，先確認當前工作模式（Analysis / Create / Patch），並僅操作對應目錄。
2. **指令一致性**：`GEMINI.md` 與 `CLAUDE.md` 保持 SOP 邏輯一致，確保產出格式統一。
3. **自動留檔**：任何重要見解必須同步寫入對應 Markdown，嚴禁僅在對話框回覆。
4. **操作日誌**：每次操作後，在對應的 `session_log.md` 留一句話紀錄。

## 如何開始

### Analysis 模式
```
請依照 analysis_workflow.md 初始化此專案的分析環境：
- 專案路徑：projects/<project_name>/
```

### Create 模式
```
請依照 create_workflow.md 初始化此衍生專案：
- 源專案：<source_name>，分析產物：analysis/<source_name>/
- 衍生目標：<一句話>
- 技術棧：<語言/框架>
```

### Patch 模式
```
請依照 patch_workflow.md 建立此 Patch 小專案：
- 目標專案：<source_name>，分析產物：analysis/<source_name>/
- Patch 目標：<一句話>
- 修改類型：<功能增強 / Bug 修正 / 重構 / 實驗>
```

## 授權規範

本專案僅託管分析後的「衍生作品」與「心得筆記」。`projects/` 下的原始碼均受其原專案授權條款約束，預設不提交至本倉庫。
