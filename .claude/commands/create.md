---
description: Create 模式 — 基於分析產物建立獨立衍生小專案
argument-hint: "[衍生專案名稱，可留空]"
---
你現在進入 **Create 模式**。根目錄 `CLAUDE.md` 的核心行為準則最高優先；本模式的完整 SOP 以 `create_workflow.md` 為**權威來源**，下面是濃縮版。

## 對象
$ARGUMENTS

留空則先與使用者敲定：衍生專案名稱、源專案、衍生目標。
**前置條件**：`analysis/<source_project>/` 下已有 Level 1-2 以上的分析產物。

## 此模式要做的事
1. **定義衍生目標**：在 `derived/<project_name>/PROJECT.md` 回答——源專案、衍生目標（要解決／驗證什麼）、參照素材（哪些 `analysis/<source>/` 文件）、技術棧、完成定義。
2. **環境初始化**：建 `derived/<project_name>/`，含 `PROJECT.md src/ tests/ docs/ session_log.md` 與 agent 指導檔；`session_log.md` 開頭記起始時間、agent 版本、源專案、一句話目標。
3. **骨架建置**：依技術棧初始化（Rust `cargo init`／Node `npm init`／Go `go mod init`／Python `uv init` 或 venv／C·C++ `CMake`·`Makefile`），並記入日誌。
4. **實作與追溯連結**：重要設計決策寫 `docs/decisions/`，標明**參照來源**（`analysis/<source>/...`）、借鑒概念、實作方式。每個功能點完成更新 `session_log.md`，里程碑更新 `PROJECT.md`。
5. **外部 Repo（選用）**：另推 GitHub 由使用者自行操作，`pas` 內只記文字連結（不用 submodule），並在 `analysis/<source>/session_log.md` 反向附記。

## 此模式的鐵則（出自 `CLAUDE.md` 核心準則）
- 全程**繁體中文**。
- 程式碼片段**必附原始碼位置**；引用源專案者附源專案路徑。
- 技術細節自動留檔到 `derived/<project_name>/docs/`；每次操作 append 一句話到 `session_log.md`（**上限 50 行**）。
- 圖表禁用 ASCII art 框線，改 Mermaid／列點／表格。

完整細節回查 `create_workflow.md`。
