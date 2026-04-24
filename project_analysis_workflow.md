# 專案分析與初始化標準作業流程 (SOP)

本文件定義了在使用 AI agent（Claude Code、Gemini CLI、Cursor 或其他）進行陌生專案分析與開發時，如何快速建立結構化的分析環境與上下文。

適用情境：初次接觸一個陌生專案時，需要在幾輪對話內建立可延續、可回復、可跨 agent 搬移的工作空間。

---

## 階段一：環境初始化

### 1. 建立目錄結構

Windows PowerShell：
```powershell
mkdir work/architecture, work/tutorial, work/analysis, work/answer, work/detail, work/other, work/session_temp
```

Bash / zsh：
```bash
mkdir -p work/{architecture,tutorial,analysis,answer,detail,other,session_temp}
```

### 2. 初始化日誌

建立 `work/session_log.md`，在檔案開頭記錄：
- 起始時間
- 作業系統
- 使用的 agent 名稱與版本（例如 `Claude Code (Opus 4.7)`、`Gemini CLI`、`Cursor` …）
- 專案根目錄路徑

往後每段操作以 append 方式留**一句話**紀錄。

---

## 階段二：設定規則與語言

### 1. 輸出語言
所有輸出與留檔一律使用 **繁體中文**。

### 2. 自動留檔機制
回覆任何技術細節、教學或分析時，必須同步寫入 `work/` 下對應的子資料夾：

| 子資料夾 | 內容 |
|---|---|
| `architecture/` | 整體架構分析（依 Level 拆解） |
| `tutorial/` | 「如何做到 X」類型的開發教學 |
| `analysis/` | 特定模組或檔案的深入分析 |
| `answer/` | 一次性問答的具體解答 |
| `detail/` | 單點技術細節（某個 API、某個演算法…） |
| `other/` | 不屬於上述類別的雜項 |
| `session_temp/` | 進度快照、暫存筆記、會話恢復檔 |

### 3. 程式碼標註規範
所有在分析、解答、教程中提到的程式碼片段，**必須標註其在專案中的原始碼位置**：
- 格式：`path/to/file.py:123` 或 `path/to/file.py::function_name`
- 指向行號時，允許「大約行號」但需加註（例：`padog.py:198 附近`）。

### 4. 會話日誌 (session_log.md)
以 append 方式紀錄每一次使用者要求中實際執行的事項：分析了哪些模組、解答了什麼問題、撰寫了哪些教程。每項一句話即可。

### 5. 會話進度保存 (Session Checkpoint)
當使用者說出「我準備要退出了」或類似語句時，必須在 `work/session_temp/session_resume.md` 建立／更新進度保存檔案，彙整：
- 當前的專案理解（一句話摘要）
- 已完成的分析路徑（對應到哪幾個 Level）
- 剩餘的待辦事項
- 核心上下文摘要（讓下一個 agent 冷啟動時能接手）

**Prompt 範例：**
> 「我準備要退出了，請幫我彙整目前的分析進度並留存於 `work/session_temp/session_resume.md`，以便下次我能直接從這個狀態繼續。」

### 6. Agent 指導文件
在根目錄產生當前 agent 對應的指導文件：

| Agent | 指導檔 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Cursor | `.cursor/rules/*.mdc` 或 `.cursorrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| 其他 | 依其官方約定 |

若同一專案會被多個 agent 使用，**各自保留**對應的指導檔（例如同時有 `CLAUDE.md` 與 `GEMINI.md`）。內容可彼此複製，但開頭一句對 agent 的說明應對應調整。

內容基本結構：
- **Project Overview** — 專案目的與高階架構（跨檔案才看得出的「大圖」）
- **Building and Running** — 具體的構建、執行、測試指令
- **Development Conventions** — 編碼規範、架構守則、特殊禁令

---

## 階段三：深度分析與上下文建置

### 1. 辨識專案類型

在進入 Level 3+ 之前，先快速判定專案屬於下列哪一（或哪幾）類，再挑選對應模板：

- **A. 遊戲原始碼分析** — 關注渲染、遊戲迴圈、資源系統、玩法機制
- **B. 機器人 / 嵌入式 / IoT** — 關注硬體抽象、控制迴圈、通訊協定、即時性
- **C. Web 後端 / API 服務** — 關注路由、資料流、認證、持久層
- **D. 前端 / 桌面應用** — 關注元件樹、狀態管理、事件系統、渲染
- **E. CLI 工具 / 函式庫 / SDK** — 關注 API 設計、指令解析、輸入輸出流
- **F. 資料管線 / ML / 分析** — 關注資料源、轉換階段、模型生命週期、部署
- **G. DevOps / 基礎設施 / IaC** — 關注資源定義、部署流程、密鑰管理、可觀測性

跨類型的專案（例：帶 Web UI 的機器人、整合 ML 的後端服務）從相關模板的 Level 中挑選組合即可。

### 2. 標準化分析路徑 (Architecture Analysis Path)

分析過程中所有產出均留存於 `work/architecture/`。Level 1 與 Level 2 通用於所有類型；Level 3 之後依類型替換。

#### Level 1：初始探索與基礎架構（通用）
- README 與 repo 頂層文件
- 目錄與 workspace 結構
- 依賴清單與主要技術棧
- 入口點（`main`、server、`index`、bootloader、`__init__` …）
- 構建、執行、測試指令

#### Level 2：核心模組職責（通用）
- 識別主要模組、元件、package 或 crate
- 模組間的權責劃分
- 模組間耦合點與資料流方向

#### Level 3+：依專案類型選擇模板

<details>
<summary><b>模板 A：遊戲原始碼分析</b></summary>

- **L3 進階機制與模擬**：AI 行為（決策鏈）、地圖生成、城鎮生成、經濟模擬
- **L4 遊戲性與 RPG 系統**：戰鬥（Poise/Combo）、技能樹、背包道具、裝備換裝
- **L5 技術架構與數據流**：網路通訊協定、玩家資料交換、存檔格式、資源定義
- **L6 視覺、動畫與特效**：渲染管線（Shaders）、Mesh、骨架、粒子與投射物
</details>

<details>
<summary><b>模板 B：機器人 / 嵌入式 / IoT</b></summary>

- **L3 控制迴圈與即時任務**：主控制迴圈、步態／動作生成、Timer/ISR、任務排程
- **L4 姿態估計與感測器融合**：IMU、濾波（AvgFilter、Kalman）、狀態觀測、閉迴路控制
- **L5 通訊與配置介面**：串列、HTTP、MQTT、BLE、參數熱更新、持久化設定
- **L6 硬體抽象層**：GPIO、I²C/SPI、PWM、PCA9685 等致動器驅動、pin 映射
</details>

<details>
<summary><b>模板 C：Web 後端 / API 服務</b></summary>

- **L3 路由與控制器層**：endpoint 對應、middleware 鏈、請求生命週期
- **L4 業務邏輯與領域模型**：service 層、aggregate、domain event
- **L5 資料持久層**：ORM/Query Builder、schema、migration、交易邊界
- **L6 橫切關注點**：認證授權、快取、佇列、外部服務整合、可觀測性
</details>

<details>
<summary><b>模板 D：前端 / 桌面應用</b></summary>

- **L3 元件樹與路由**：頁面結構、元件階層、路由配置
- **L4 狀態管理**：Redux / Pinia / Signals / Zustand / Context，以及資料流向
- **L5 與後端通訊**：API client、WebSocket、GraphQL、快取層（React Query 等）
- **L6 呈現層與體驗**：樣式系統、主題、國際化、無障礙、效能優化、建置產物
</details>

<details>
<summary><b>模板 E：CLI 工具 / 函式庫 / SDK</b></summary>

- **L3 指令解析與子指令架構**：CLI framework、flag/arg 解析、子命令分派
- **L4 核心 API 介面設計**：公開 API surface、型別契約、錯誤模型
- **L5 輸入輸出 / 序列化**：stdin/stdout 協定、檔案格式、config 載入
- **L6 擴充與發佈**：plugin 機制、版本策略、打包與發佈流程
</details>

<details>
<summary><b>模板 F：資料管線 / ML / 分析</b></summary>

- **L3 資料源與讀取層**：connector、schema 推斷、資料驗證
- **L4 轉換 / 特徵工程**：pipeline DAG、任務排程、增量 vs 全量
- **L5 模型生命週期**：訓練、評估、版本管理、實驗追蹤
- **L6 推論與部署**：batch/online serving、監控、漂移偵測、回滾策略
</details>

<details>
<summary><b>模板 G：DevOps / 基礎設施 / IaC</b></summary>

- **L3 資源定義**：Terraform/Pulumi/CloudFormation module、環境分層
- **L4 部署流程**：CI/CD pipeline、環境晉升、藍綠/金絲雀
- **L5 組態與密鑰**：config、secret 管理、權限模型
- **L6 可觀測性**：logging、metrics、tracing、alert、SLO
</details>

若現有模板都不完全貼合，以最接近的模板為基底，在 Level 層級補入專案獨有的關注點（並在 `work/architecture/` 註明模板調整理由）。

### 3. 教學文件編寫規範 (Tutorial Framework)

分析完成後，針對開發常見任務產出「如何開發」教學，存放於 `work/tutorial/`：

- **目標導向**：每個教學必須解決一個**具體**問題。依專案類型，目標範例：
  - 遊戲原始碼分析：「如何新增一個戰鬥技能」
  - 機器人：「如何新增一種步態」
  - Web：「如何新增一個需要認證的 API 端點」
  - 前端：「如何新增一個帶全域狀態的頁面」
  - CLI：「如何新增一個子指令」
  - 資料/ML：「如何新增一個資料源並接入訓練流程」
- **結構要求**：
  1. **前置知識**：需要先理解哪些核心模組（附 `work/architecture/` 中的對應連結）
  2. **原始碼導航**：標註必須修改或參考的具體檔案與行號
  3. **實作步驟**：具體的程式碼實作或配置修改
  4. **驗證方式**：如何測試新功能的正確性（單元測試、整合測試、手動驗證步驟）

---

## 快速啟動提示詞 (Copy & Paste)

> 請依照 `project_analysis_workflow.md` 初始化此專案的分析環境：
> 1. 建立 `work/` 資料夾結構並啟動 `session_log.md`（含 agent 名稱與 OS）。
> 2. 所有輸出使用繁體中文；技術內容自動留檔至對應子資料夾；程式碼必附 `檔案:行號`。
> 3. 執行 Level 1-2 通用分析，識別專案類型後挑選 Level 3+ 模板，依序完成深度分析並留檔於 `work/architecture/`。
> 4. 根據目前所用的 agent，在根目錄生成對應的指導文件（Claude Code → `CLAUDE.md`、Gemini → `GEMINI.md`；若同一專案跨 agent 使用則兩者皆產）。
