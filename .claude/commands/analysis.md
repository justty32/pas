---
description: Analysis 模式 — 初次接觸陌生專案，建立結構化分析（Level 1-6）
argument-hint: "[要分析的專案名稱／路徑，可留空]"
---
你現在進入 **Analysis 模式**。根目錄 `CLAUDE.md` 的核心行為準則最高優先；本模式的完整 SOP 以 `analysis_workflow.md` 為**權威來源**，下面是把它濃縮成「進入此模式該做什麼」。

## 對象
$ARGUMENTS

留空則先問使用者要分析哪個專案（`projects/` 下已 clone 的，或外部 URL）。

## 此模式要做的事
1. **環境初始化**：在 `analysis/<project_name>/` 建立 `architecture/ tutorial/ answers/ details/ others/` 與 `session_log.md`（記起始時間、agent 名稱與版本、OS、專案根路徑）。
2. **依序分析**（產物留 `analysis/<project_name>/architecture/`）：
   - **Level 1** 初始探索：README、目錄結構、依賴與技術棧、入口點、build/run/test 指令。
   - **Level 2** 核心模組職責：主要模組、權責劃分、耦合點、資料流方向。
   - **Level 3-6**：先辨識專案類型（A 遊戲／B 嵌入式／C Web 後端／D 前端／E CLI·SDK／F 資料·ML／G DevOps），再套 `analysis_workflow.md` 對應模板；無完全貼合者以最近者為基底並註明調整理由。
3. **教學**（選用）：針對開發常見任務寫目標導向教學至 `tutorial/`（前置知識→原始碼導航→實作步驟→驗證方式）。
4. **指導文件**：依當前 agent 在專案根產生對應指導檔（Claude Code→`CLAUDE.md`、Gemini→`GEMINI.md`）。

## 此模式的鐵則（出自 `CLAUDE.md` 核心準則）
- 全程**繁體中文**。
- 所有程式碼片段**必附原始碼位置**（`path/to/file:line` 或 `::function_name`）。
- 每次操作後 append 一句話到對應 `session_log.md`（**上限 50 行**，超過刪舊留新）。
- 需要架構圖／流程圖時**禁用 ASCII art 框線**，改用 Mermaid 或巢狀列點／表格。
- `.md` 多到難綜覽時，依準則 6 在 `analysis/<project>/html/` 生成 HTML 導覽層（可改用 `/html`）。

完整細節（各 Level 模板、教學結構、HTML 規範）一律回查 `analysis_workflow.md`。
