# GEMINI.md

## 專案概述 (Project Overview)

此目錄 `pas` (Project Analysis System) 是一個結構化的工作空間，旨在利用 LLM 分析各種 GitHub 專案。它作為克隆倉庫與儲存後續分析結果的中心樞紐。

## 目錄結構與用途 (Intended Structure & Usage)

- `projects/`: 用於克隆外部 GitHub 專案的原始碼。請直接克隆，不要使用 git submodules。
- `analysis/`: 存放所有分析報告、筆記與 LLM 產出的見解。每個專案應有其獨立的子目錄。

### 工作範圍限制 (Scope)
- **僅限 GitHub 專案分析**：此工作空間專為分析開源 GitHub 專案而設計。
- **排除非分析類專案**：若遇到個人工具、內部實驗性專案、爬蟲程式、自創語言或非針對特定 GitHub 倉庫的分析紀錄，**應予以跳過，不進行遷移、初始化或 SOP 化處理**。
- **辨識方式**：優先檢查目錄內是否有指向 GitHub 倉庫的說明、README 或原始碼連結。若性質不明，應先詢問使用者。

### 專案分析子目錄結構

對於每個分析中的專案 `<project_name>`，應在 `analysis/<project_name>/` 下建立以下結構：
- `architecture/`: 存放架構分析、模組職責與技術架構文件。
- `tutorial/`: 存放「如何開發」的目標導向教學文件。
- `answers/`: 存放針對具體問題的解答。
- `details/`: 存放深入的原始碼剖析與細節紀錄。
- `others/`: 存放不屬於上述分類的其他內容。
- `gemini_temp/`: 存放會話進度保存文件（如 `session_resume.md`）。
- `session_log.md`: 紀錄操作日誌（每項操作簡短的一句話）。

## AI 核心行為準則 (Core Mandates)

### 0. 專案特異性與自訂化 (Project Specificity)
- **因地制宜**：每個專案的格式、技術棧與架構皆不相同，Agent **必須根據專案特性單獨處理**。
- **優先權限制**：若 `analysis/<project_name>/` 目錄下存在專屬的指令文件（如 `PROJECT_SPEC.md`），其優先級高於此通用規範。
- **彈性調整**：通用的 Level 1-6 分析路徑僅供參考，Agent 應針對專案類型（如：遊戲模組、引擎、Web 框架）自訂最適合的剖析深度與重點。

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

### 4. 執行流程與品質標準 (Workflow & Quality Standards)
- **主動規劃**：Agent 必須展現高度主動性（主觀能動性）。在開始分析前，必須先擬定完整的計畫並主動執行，而非被動等待細碎指令。
- **拒絕淺層概論**：嚴禁交差了事或僅提供簡短摘要。所有技術剖析必須達到「完整、嚴謹、全面」的標準，提供具備深度工程見解的詳細分析。
- **專題深度剖析**：針對核心機制（如 AI、演算法、底層架構），應採用「高保真技術專題」形式，深入解構原始碼邏輯與數學模型。

### 5. 會話保存
- 當使用者表示要退出時，必須在 `gemini_temp/` 下建立 `session_resume.md`，彙整當前理解、已完成路徑、剩餘待辦事項與上下文摘要。
## 專案遷移與分析進度表 (Migration & Analysis Progress)

- [x] **RimWorld** (已遷移 - 2026-04-15)
- [x] **Skyrim Mod** (已遷移 - 2026-04-15)
- [x] **Veloren** (已遷移 - 2026-04-15)
- [x] **OpenNefia** (已遷移 - 2026-04-15)
- [x] **Luanti (Minetest)** (已遷移 - 2026-04-15)
- [x] **VCMI** (已遷移 - 2026-04-15)
- [x] **Taisei** (已遷移 - 2026-04-15)
- [x] **T-Engine** (已遷移 - 2026-04-15)
- [x] **OpenStartbound** (已遷移 - 2026-04-15)
- [x] **Slay-the-Robot** (已遷移 - 2026-04-15)
- [x] **ASC-HQ** (已遷移 - 2026-04-15)
- [x] **Godot** (已遷移 - 2026-04-15)
- [x] **MC Mod (Millenaire-Reborn)** (已遷移 - 2026-04-15)
- [x] **Hy (Lisp-Python)** (已遷移 - 2026-04-15)
- [x] **LispC** (已遷移 - 2026-04-15)
- [x] **C-mera (Lisp-to-C++ Generator)** (已遷移 - 2026-04-15)
- [ ] **godot-cpp** (正在進行 Level 1 分析 - 2026-04-15)
- [ ] **ESPAsyncWebServer** (正在進行 Level 1 分析 - 2026-04-16)
- [ ] **godot-open-rpg** (Level 1-2 已完成 - 2026-04-18)
- [x] **Unciv** (核心系統與 AI 深度剖析 Level 6 已完成 - 2026-05-17)
- [x] **Wesnoth** (基礎分析 Level 1-6 已完成 - 2026-05-17)
    - [ ] **Level 7: 多人連線與同步機制** (網路協議、確定性模擬、重播系統)
    - [ ] **Level 8: GUI2 與渲染管線** (Pango/Cairo 整合、動態佈局引擎、動畫層)
    - [ ] **Level 9: WML 預處理與元程式設計** (宏展開、條件編譯深探、WML-to-Config 性能限制)
    - [ ] **Level 10: 技術債與現代化專題** (C++ 遺留代碼、Boost 模組依賴優化、內存管理)

---
*註：其餘如 `agent_server`, `arxiv_crawler`, `mylang`, `nlisp` 等非分析類專案已跳過。*
