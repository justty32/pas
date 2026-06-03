# 專案分析標準作業流程 (Analysis SOP)

本文件定義了初次接觸陌生專案時，如何快速建立結構化的分析環境與上下文。

適用情境：需要在幾輪對話內建立可延續、可回復、可跨 agent 搬移的工作空間，並產出供後續 create / patch 階段使用的分析產物。

---

## 階段一：環境初始化

### 1. 建立目錄結構

Windows PowerShell：
```powershell
mkdir work/architecture, work/tutorial, work/analysis, work/answer, work/detail, work/other
```

Bash / zsh：
```bash
mkdir -p work/{architecture,tutorial,analysis,answer,detail,other}
```

### 2. 初始化日誌

建立 `work/session_log.md`，在檔案開頭記錄：
- 起始時間
- 作業系統
- 使用的 agent 名稱與版本（例如 `Claude Code (Sonnet 4.6)`、`Gemini CLI`）
- 專案根目錄路徑

往後每段操作以 append 方式留**一句話**紀錄。

---

## 階段二：規則設定

### 1. 輸出語言
所有輸出與留檔一律使用 **繁體中文**。

### 2. 自動留檔機制

| 子資料夾 | 內容 |
|---|---|
| `architecture/` | 整體架構分析（依 Level 拆解） |
| `tutorial/` | 「如何做到 X」類型的開發教學 |
| `analysis/` | 特定模組或檔案的深入分析 |
| `answer/` | 一次性問答的具體解答 |
| `detail/` | 單點技術細節（某個 API、某個演算法…） |
| `other/` | 不屬於上述類別的雜項 |
| `html/` | HTML 導覽層（.md 過多時生成，降低瀏覽認知負擔；見階段三第 4 節） |

### 3. 程式碼標註規範
所有程式碼片段**必須標註原始碼位置**：
- 格式：`path/to/file.py:123` 或 `path/to/file.py::function_name`
- 允許「大約行號」但需加註（例：`padog.py:198 附近`）

### 4. 會話日誌
以 append 方式紀錄每次實際執行的事項，每項一句話。**`session_log.md` 上限 50 行**：超過時刪除舊紀錄、只保留最新數筆。

### 5. 會話進度保存
當使用者說出「我準備要退出了」或類似語句時，在 `work/session_log.md` 末尾追加一筆進度快照（仍受 50 行上限，舊紀錄可刪），彙整：
- 當前的專案理解（一句話摘要）
- 已完成的分析路徑（對應 Level）
- 剩餘的待辦事項
- 核心上下文摘要（讓下一個 agent 冷啟動時能接手）

### 6. Agent 指導文件

| Agent | 指導檔 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/*.mdc` 或 `.cursorrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| 其他 | 依其官方約定 |

若同一專案會被多個 agent 使用，**各自保留**對應的指導檔。內容基本結構：
- **Project Overview** — 專案目的與高階架構
- **Building and Running** — 構建、執行、測試指令
- **Development Conventions** — 編碼規範、架構守則、特殊禁令

### 7. 圖表呈現規範

**禁止用 ASCII art 畫框線圖**。內容以繁體中文為主，全形字與框線字元寬度不一致，等寬字體也無法對齊，且 Agent 生成時極易算錯字元數導致圖形錯亂。改用語意化（不靠字元對齊）方式：

- **`.md` 內（真相層）**：首選 **Mermaid** 程式碼塊（` ```mermaid `）；簡單關係改用巢狀列點或 Markdown 表格。
- **html 導覽層（呈現層）**：用 **CSS 分層卡片**呈現分層架構，沿用 `analysis/c-mera/html/_shared.css` 的 `.card` / `.card-accent-*` / `.g2`–`.g4` / `.section` 等類別；流程連線於 html 內嵌 Mermaid 或用箭頭元素串接。

---

## 階段三：深度分析

### 1. 辨識專案類型

在進入 Level 3+ 之前，先快速判定專案屬於下列哪一（或哪幾）類：

- **A. 遊戲原始碼分析** — 渲染、遊戲迴圈、資源系統、玩法機制
- **B. 機器人 / 嵌入式 / IoT** — 硬體抽象、控制迴圈、通訊協定、即時性
- **C. Web 後端 / API 服務** — 路由、資料流、認證、持久層
- **D. 前端 / 桌面應用** — 元件樹、狀態管理、事件系統、渲染
- **E. CLI 工具 / 函式庫 / SDK** — API 設計、指令解析、輸入輸出流
- **F. 資料管線 / ML / 分析** — 資料源、轉換階段、模型生命週期、部署
- **G. DevOps / 基礎設施 / IaC** — 資源定義、部署流程、密鑰管理、可觀測性

### 2. 標準化分析路徑

所有產出均留存於 `work/architecture/`。

#### Level 1：初始探索（通用）
- README 與 repo 頂層文件
- 目錄與 workspace 結構
- 依賴清單與主要技術棧
- 入口點（`main`、server、`index`、bootloader、`__init__` …）
- 構建、執行、測試指令

#### Level 2：核心模組職責（通用）
- 識別主要模組、元件、package 或 crate
- 模組間的權責劃分
- 耦合點與資料流方向

#### Level 3+：依專案類型選擇模板

<details>
<summary><b>模板 A：遊戲原始碼分析</b></summary>

- **L3**：AI 行為（決策鏈）、地圖生成、城鎮生成、經濟模擬
- **L4**：戰鬥（Poise/Combo）、技能樹、背包道具、裝備換裝
- **L5**：網路通訊協定、玩家資料交換、存檔格式、資源定義
- **L6**：渲染管線（Shaders）、Mesh、骨架、粒子與投射物
</details>

<details>
<summary><b>模板 B：機器人 / 嵌入式 / IoT</b></summary>

- **L3**：主控制迴圈、步態／動作生成、Timer/ISR、任務排程
- **L4**：IMU、濾波（AvgFilter、Kalman）、狀態觀測、閉迴路控制
- **L5**：串列、HTTP、MQTT、BLE、參數熱更新、持久化設定
- **L6**：GPIO、I²C/SPI、PWM、致動器驅動、pin 映射
</details>

<details>
<summary><b>模板 C：Web 後端 / API 服務</b></summary>

- **L3**：endpoint 對應、middleware 鏈、請求生命週期
- **L4**：service 層、aggregate、domain event
- **L5**：ORM/Query Builder、schema、migration、交易邊界
- **L6**：認證授權、快取、佇列、外部服務整合、可觀測性
</details>

<details>
<summary><b>模板 D：前端 / 桌面應用</b></summary>

- **L3**：頁面結構、元件階層、路由配置
- **L4**：Redux / Pinia / Signals / Zustand / Context，以及資料流向
- **L5**：API client、WebSocket、GraphQL、快取層（React Query 等）
- **L6**：樣式系統、主題、國際化、無障礙、效能優化、建置產物
</details>

<details>
<summary><b>模板 E：CLI 工具 / 函式庫 / SDK</b></summary>

- **L3**：CLI framework、flag/arg 解析、子命令分派
- **L4**：公開 API surface、型別契約、錯誤模型
- **L5**：stdin/stdout 協定、檔案格式、config 載入
- **L6**：plugin 機制、版本策略、打包與發佈流程
</details>

<details>
<summary><b>模板 F：資料管線 / ML / 分析</b></summary>

- **L3**：connector、schema 推斷、資料驗證
- **L4**：pipeline DAG、任務排程、增量 vs 全量
- **L5**：訓練、評估、版本管理、實驗追蹤
- **L6**：batch/online serving、監控、漂移偵測、回滾策略
</details>

<details>
<summary><b>模板 G：DevOps / 基礎設施 / IaC</b></summary>

- **L3**：Terraform/Pulumi/CloudFormation module、環境分層
- **L4**：CI/CD pipeline、環境晉升、藍綠/金絲雀
- **L5**：config、secret 管理、權限模型
- **L6**：logging、metrics、tracing、alert、SLO
</details>

若現有模板都不完全貼合，以最接近的模板為基底，在 Level 層級補入專案獨有的關注點，並在 `work/architecture/` 註明模板調整理由。

### 3. 教學文件編寫規範

分析完成後，針對開發常見任務產出教學，存放於 `work/tutorial/`：

- **目標導向**：每個教學必須解決一個**具體**問題
- **結構要求**：
  1. **前置知識**：需要先理解的核心模組（附 `work/architecture/` 連結）
  2. **原始碼導航**：必須修改或參考的具體檔案與行號
  3. **實作步驟**：具體的程式碼實作或配置修改
  4. **驗證方式**：單元測試、整合測試、手動驗證步驟

### 4. HTML 導覽層（選用）

當 `.md` 數量增多、難以快速綜覽時，於 `work/html/`（實際專案為 `analysis/<project>/html/`）生成一組 HTML 作為**導覽／呈現層**：

- **定位**：HTML 不取代 .md。.md 仍是唯一真實來源，內容更新一律先改 .md，HTML 只負責索引與呈現。
- **結構**：`index.html`（入口頁，含頂部導覽列 + 卡片連結）＋ 各主題 `*.html` ＋ 共用 `_shared.css`。
- **連結**：以相對路徑連回同層或上層的 .md，讓使用者能在導覽頁與原始文件間往返。
- **觸發時機**：使用者要求，或 Agent 判斷 .md 已多到造成認知負擔時主動生成／更新。
- **參考範例**：`analysis/c-mera/html/`。

---

## 快速啟動提示詞

> 請依照 `analysis_workflow.md` 初始化此專案的分析環境：
> 1. 建立 `work/` 資料夾結構並啟動 `session_log.md`（含 agent 名稱與 OS）。
> 2. 所有輸出使用繁體中文；技術內容自動留檔至對應子資料夾；程式碼必附 `檔案:行號`。
> 3. 執行 Level 1-2 通用分析，識別專案類型後挑選 Level 3+ 模板，依序完成深度分析並留檔於 `work/architecture/`。
> 4. 根據目前所用的 agent，在根目錄生成對應的指導文件（Claude Code → `CLAUDE.md`、Gemini → `GEMINI.md`；若同一專案跨 agent 使用則兩者皆產）。
