# CLAUDE.md

## 專案概述 (Project Overview)

此目錄 `pas` (Project Analysis System) 是一個結構化的工作空間，旨在利用 LLM 分析各種 GitHub 專案。它作為克隆倉庫與儲存後續分析結果的中心樞紐。

## 目錄結構與用途 (Intended Structure & Usage)

- `projects/`: 用於克隆外部 GitHub 專案的原始碼。請直接克隆，不要使用 git submodules。
- `analysis/`: 存放所有分析報告、筆記與 LLM 產出的見解。每個專案應有其獨立的子目錄。

### 專案分析子目錄結構
對於每個分析中的專案 `<project_name>`，應在 `analysis/<project_name>/` 下建立以下結構：
- `architecture/`: 存放架構分析、模組職責與技術架構文件。
- `tutorial/`: 存放「如何開發」的目標導向教學文件集。
- `answers/`: 存放針對具體問題的解答。
- `details/`: 存放深入的原始碼剖析與細節紀錄。
- `others/`: 存放不屬於上述分類的其他內容。
- `gemini_temp/`: 存放會話進度保存文件（如 `session_resume.md`）。
- `session_log.md`: 紀錄操作日誌（每項操作簡短的一句話）。

## AI 核心行為準則 (Core Mandates)

### 1. 輸出語言與格式
- **強制使用繁體中文** 進行所有回覆與留檔。
- 所有程式碼片段 **必須標註原始碼位置**（路徑與大約行號或函數名）。

### 2. 自動留檔機制
- 在回覆技術細節、教學或分析時，**必須同步將內容寫入** `analysis/<project_name>/` 下對應的子資料夾。
- 每次操作後，必須以 append 方式在 `analysis/<project_name>/session_log.md` 紀錄具體執行的事項。

### 3. 分析路徑 (Standardized Analysis Path)
在進行新專案分析時，應依序執行以下級別：
- **Level 1**: 初始探索（README、技術棧）。
- **Level 2**: 核心模組職責（入口、權責劃分）。
- **Level 3-6**: 進階機制（如 AI、生成算法、系統邏輯、渲染管線等，視專案性質而定）。

### 4. 會話保存
- 當您（Claude）收到「我要準備退出了」的指令時，必須在 `gemini_temp/` 下建立 `session_resume.md`，彙整當前理解、已完成路徑、剩餘待辦事項與上下文摘要。

## 關鍵檔案
- `readme.md`: 專案的高階概述。
- `index.md`: 追蹤所有已克隆專案的清單與分析狀態。
- `GEMINI.md`: Gemini Agent 的規範文件。
