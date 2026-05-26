# GEMINI.md

## 專案概述 (Project Overview)

此目錄 `pas` (Project Analysis System) 是一個結構化的工作空間，旨在利用 LLM 對外部專案進行**分析、衍生開發與 Patch 製作**。支援三種工作模式，各有獨立 SOP 文件。

外部專案不一定是 git repository；`pas` 本身不使用 git submodule，GitHub 連結以純文字記錄於對應的 Markdown 中。

## 工作模式與 SOP

| 模式 | 適用情境 | SOP 文件 |
|---|---|---|
| **Analysis** | 初次接觸陌生專案，建立結構化分析 | `analysis_workflow.md` |
| **Create** | 基於分析產物建立獨立衍生小專案 | `create_workflow.md` |
| **Patch** | 製作可被 agent 套用至原專案的獨立 Patch 小專案 | `patch_workflow.md` |

## 目錄結構與用途 (Intended Structure & Usage)

- `projects/`: 克隆外部專案的原始碼。直接克隆，不使用 git submodule。
- `analysis/`: 所有分析報告、筆記與 LLM 產出的見解。每個專案有獨立子目錄。
- `derived/`: 衍生小專案（Create 模式產出）。
- `patches/`: Patch 小專案（Patch 模式產出）。

### analysis/<project_name>/ 子目錄結構

- `architecture/`: 架構分析、模組職責與技術架構文件。
- `tutorial/`: 目標導向的開發教學文件。
- `answers/`: 具體問題的解答。
- `details/`: 深入的原始碼剖析與細節紀錄。
- `others/`: 雜項（含 `patches/` 子目錄，記錄對應的 Patch 連結）。
- `html/`: HTML 導覽層（.md 過多時生成，降低瀏覽認知負擔；詳見準則 6）。
- `gemini_temp/`: 會話進度保存文件（如 `session_resume.md`）。
- `session_log.md`: 操作日誌（每項操作一句話）。

## AI 核心行為準則 (Core Mandates)

### 0. 專案特異性與自訂化 (Project Specificity)
- **因地制宜**：每個專案的格式、技術棧與架構皆不相同，Agent **必須根據專案特性單獨處理**。
- **優先權限制**：若 `analysis/<project_name>/` 目錄下存在專屬的指令文件（如 `PROJECT_SPEC.md`），其優先級高於此通用規範。
- **彈性調整**：通用的 Level 1-6 分析路徑僅供參考，Agent 應針對專案類型（如：遊戲模組、引擎、Web 框架）自訂最適合的剖析深度與重點。

### 1. 輸出語言與格式
- **強制使用繁體中文** 進行所有回覆與留檔。
- 所有程式碼片段 **必須標註原始碼位置**（路徑與大約行號或函數名）。

### 2. 自動留檔機制
依當前工作模式，將技術細節寫入對應目錄：

| 工作模式 | 留檔位置 |
|---|---|
| Analysis | `analysis/<project>/` 對應子資料夾 |
| Create | `derived/<project>/docs/` |
| Patch | `patches/<patch>/`（代碼在 `src/`，說明在 `PATCH.md`） |

每次操作後，以 append 方式在對應的 `session_log.md` 留一句話紀錄。

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

### 6. HTML 導覽層（降低瀏覽認知負擔）
當某個工作單位的 .md 文件數量增多、難以快速綜覽時，可生成一組 HTML 作為**導覽／呈現層**。

- **定位**：HTML 不取代 .md。.md 仍是內容的唯一真實來源 (source of truth)，HTML 只是索引與呈現，內容更新一律先改 .md。
- **位置**：放在該工作單位下的 `html/` 子目錄，與來源 .md 同層（Analysis → `analysis/<project>/html/`；Create → `derived/<project>/html/`；Patch → `patches/<patch>/html/`）。
- **結構**：`index.html`（入口頁，含頂部導覽列 + 卡片連結）＋ 各主題 `*.html` ＋ 共用 `_shared.css`（同一單位共用一份）。
- **連結**：以相對路徑連回同層或上層的 .md，讓使用者能在導覽頁與原始文件間往返。
- **觸發時機**：使用者要求，或 Agent 判斷 .md 已多到造成認知負擔時主動生成／更新。
- **參考範例**：`analysis/c-mera/html/`（`index.html` + 主題頁 + `_shared.css` 的完整實作）。

### 7. 圖表呈現（架構圖／流程圖）
**禁止用 ASCII art 畫框線圖**。本工作區內容以繁體中文為主，全形字與框線字元（`─│┌┐`）寬度不一致，等寬字體也無法對齊，且 Agent 生成時極易算錯字元數導致圖形錯亂。改用語意化（不靠字元對齊）方式：

- **`.md` 內（真相層）**：首選 **Mermaid** 程式碼塊（` ```mermaid `，以語法描述節點與連線，多數 Markdown 檢視器可渲染）；簡單關係改用**巢狀列點**或 **Markdown 表格**。
- **html 導覽層（呈現層）**：用 **CSS 分層卡片**呈現視覺化分層架構，沿用 `analysis/c-mera/html/_shared.css` 既有類別（卡片 `.card` + `.card-accent-*`、格線 `.g2`/`.g3`/`.g4`、區段 `.section`）；需要流程連線時於 html 內嵌 Mermaid 或用箭頭元素串接卡片。

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
- [x] **Freeciv** (地圖生成與 AI 系統極致深度剖析 Level 6+ 已完成 - 2026-05-17)

---
*註：其餘如 `agent_server`, `arxiv_crawler`, `mylang`, `nlisp` 等非分析類專案已跳過。*
