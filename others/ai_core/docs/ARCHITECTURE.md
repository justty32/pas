# AI Core — 架構設計

> 詳細設計已切分至 `docs/architectures/`，以 `index.md` 導覽。
>
> **請直接閱讀：[docs/architectures/index.md](architectures/index.md)**

---

## 快速概覽

ai_core 把 LLM 呼叫視為**函式**，再把所有支援設施（queue 管理、shell 包裝、metadata 發現）疊在這個基礎概念上。四個核心元件：

| 元件 | CLI | 說明 |
|---|---|---|
| LLM Entry Manager | `ai-core-server` + `ai-core-call` | 統一管理多個 LLM 後端，queue + rate limit |
| Function Hub | `ai-core-hub` / `ai-core-hub-server` | 掃描函式集，產生 AI 可用的 skill 清單 |
| Small Function Center | `ai-core-sfc` | 把大量微型函式集中到一個 dispatcher，避免清單膨脹 |
| ai-core-author | `ai-core-author` | 一站式產生新函式（generate → dry-run → register） |

**唯一跨元件硬規則**：每個函式支援 `--metadata`，回傳合法 JSON。

---

## 文件索引

| 主題 | 檔案 |
|---|---|
| 設計原則、技術選型、整體架構圖 | [architectures/01_overview.md](architectures/01_overview.md) |
| metadata 協議、錯誤處理慣例 | [architectures/02_protocol.md](architectures/02_protocol.md) |
| LLM Entry Manager 完整設計 | [architectures/03_entry_manager.md](architectures/03_entry_manager.md) |
| Function Hub 設計 | [architectures/04_hub.md](architectures/04_hub.md) |
| ai-core-author + SFC 設計 | [architectures/05_author_sfc.md](architectures/05_author_sfc.md) |
| 目錄結構、CLI、config、里程碑 | [architectures/06_project.md](architectures/06_project.md) |
| Agent 整合與文檔策略 | [architectures/07_agents.md](architectures/07_agents.md) |
| 變更紀錄 | [architectures/08_changelog.md](architectures/08_changelog.md) |
