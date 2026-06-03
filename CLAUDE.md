# CLAUDE.md

## 專案概述 (Project Overview)

此目錄 `pas` (Project Analysis System) 是一個結構化的工作空間，用於對外部專案進行**分析、衍生開發與 Patch 製作**。支援三種工作模式，各有獨立的 SOP 文件。

外部專案不一定是 git repository；`pas` 本身也不使用 git submodule 嵌入任何外部專案。GitHub URL 等外部連結以純文字形式記錄於對應的 Markdown 檔案中。

## 工作模式與 SOP

| 模式 | 適用情境 | SOP 文件 |
|---|---|---|
| **Analysis** | 初次接觸陌生專案，建立結構化分析 | `analysis_workflow.md` |
| **Create** | 基於分析產物建立獨立衍生小專案 | `create_workflow.md` |
| **Patch** | 製作可被 agent 套用至原專案的獨立 Patch 小專案 | `patch_workflow.md` |

## 目錄結構 (Directory Structure)

```
pas/
├── projects/       # 克隆的外部專案原始碼（直接 clone，不用 submodule）
├── analysis/       # 各專案的分析產物
├── derived/        # 衍生小專案（Create 模式產出）
├── patches/        # Patch 小專案（Patch 模式產出）
└── *.md            # SOP 文件與工作區索引
```

### analysis/<project_name>/ 結構
- `architecture/`: 架構分析（Level 1-6）
- `tutorial/`: 目標導向的開發教學
- `answers/`: 具體問答的解答
- `details/`: 深入的原始碼剖析
- `others/`: 不屬於上述分類的雜項（含 `patches/` 子目錄，記錄對應的 Patch 連結）
- `html/`: HTML 導覽層（.md 過多時生成，降低瀏覽認知負擔；詳見準則 6）
- `session_log.md`: 操作日誌（每項操作一句話，上限 50 行）

### derived/<project_name>/ 結構
- `PROJECT.md`: 衍生目標、參照素材、技術棧、完成定義
- `session_log.md`: 操作日誌
- `src/`, `tests/`, `docs/`: 依技術棧慣例
- `html/`: HTML 導覽層（選用，詳見準則 6）

### patches/<patch_name>/ 結構
- `PATCH.md`: Patch 目標、修改類型、影響範圍、分析依據
- `APPLY.md`: Agent 套用操作手冊（核心交付物）
- `session_log.md`: 操作日誌
- `src/`: Patch 代碼（模擬原專案相對路徑）
- `tests/`: 驗證腳本或說明
- `html/`: HTML 導覽層（選用，詳見準則 6）

## AI 核心行為準則 (Core Mandates)

### 1. 輸出語言與格式
- **強制使用繁體中文** 進行所有回覆與留檔。
- 所有程式碼片段 **必須標註原始碼位置**（`path/to/file:line` 或 `::function_name`）。

### 2. 自動留檔機制
依當前工作模式，將技術細節寫入對應目錄：

| 工作模式 | 留檔位置 |
|---|---|
| Analysis | `analysis/<project>/` 對應子資料夾 |
| Create | `derived/<project>/docs/` |
| Patch | `patches/<patch>/`（代碼在 `src/`，說明在 `PATCH.md`） |

每次操作後，以 append 方式在對應的 `session_log.md` 記錄一句話。

**`session_log.md` 上限 50 行**：超過時刪除舊紀錄、只保留最新數筆（最舊的可直接放棄）。日誌僅供「接上進度」，非歷史檔案。

### 3. 分析路徑 (Analysis 模式)
進行新專案分析時，依序執行：
- **Level 1**: 初始探索（README、技術棧、入口點）
- **Level 2**: 核心模組職責（權責劃分、耦合點、資料流）
- **Level 3-6**: 依專案類型選擇對應模板（詳見 `analysis_workflow.md`）

### 4. Patch 套用原則 (Patch 模式)
- `src/` 存放完整檔案（非 diff），讓 agent 能直接覆蓋
- `APPLY.md` 必須讓冷啟動的 agent 能獨立套用，不依賴對話上下文
- 原專案不假設有版本控制，一律以檔案操作描述步驟

### 5. 會話保存
收到「我要準備退出了」時，在當前工作模式對應的 `session_log.md` 末尾追加一筆進度快照（仍受 50 行上限，舊紀錄可刪），彙整：
- 當前理解（一句話摘要）
- 已完成項目
- 剩餘待辦事項
- 核心上下文摘要

### 6. HTML 導覽層（降低瀏覽認知負擔）
當某個工作單位的 .md 文件數量增多、難以快速綜覽時，可生成一組 HTML 作為**導覽／呈現層**。

- **定位**：HTML 不取代 .md。.md 仍是內容的唯一真實來源 (source of truth)，HTML 只是索引與呈現，內容更新一律先改 .md。
- **位置**：放在該工作單位下的 `html/` 子目錄，與來源 .md 同層：
  - Analysis → `analysis/<project>/html/`
  - Create → `derived/<project>/html/`
  - Patch → `patches/<patch>/html/`
- **結構**：
  - `index.html`：入口頁，提供總覽與導覽（頂部導覽列 + 卡片連結）
  - 各主題 `*.html`
  - `_shared.css`：同一單位內共用一份樣式
- **連結**：以相對路徑連回同層或上層的 .md，讓使用者能在導覽頁與原始文件間往返
- **觸發時機**：使用者要求，或 AI 判斷 .md 已多到造成認知負擔時主動生成／更新
- **參考範例**：`analysis/c-mera/html/`（`index.html` + 主題頁 + `_shared.css` 的完整實作）

### 7. 圖表呈現（架構圖／流程圖）
**禁止用 ASCII art 畫框線圖**。本工作區內容以繁體中文為主，全形字與框線字元（`─│┌┐`）寬度不一致，等寬字體也無法對齊，且 AI 生成時極易算錯字元數導致圖形錯亂。改用下列語意化（不靠字元對齊）方式：

- **`.md` 內（真相層）**：
  - 首選 **Mermaid** 程式碼塊（` ```mermaid `）——以語法描述節點與連線，多數 Markdown 檢視器（GitHub 等）可直接渲染。
  - 簡單關係改用**巢狀列點**或 **Markdown 表格**。
- **html 導覽層（呈現層）**：用 **CSS 分層卡片**呈現視覺化分層架構，沿用 `analysis/c-mera/html/_shared.css` 既有類別：
  - 卡片：`.card` + `.card-accent-{blue,green,orange,purple,red,cyan}`（以色彩區分層級／類型）
  - 格線分層：`.g2` / `.g3` / `.g4`（響應式自動換行）
  - 區段：`.section` + `.section-title`
  - 需要流程連線時，於 html 內嵌 Mermaid，或用簡單箭頭元素串接卡片。

## 關鍵檔案
- `analysis_workflow.md`: Analysis 模式 SOP
- `create_workflow.md`: Create 模式 SOP
- `patch_workflow.md`: Patch 模式 SOP
- `readme.md`: 工作區高階概述
- `index.md`: 所有已克隆專案的清單與分析狀態
- `GEMINI.md`: Gemini Agent 的規範文件
