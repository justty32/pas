# AI Core — 架構文件導覽

> 詳細設計文件已按主題切分，各檔案獨立可讀。以下為各章節索引。

---

| 檔案 | 涵蓋章節 | 內容摘要 |
|---|---|---|
| [01_overview.md](01_overview.md) | 定位 + §1–§3 | 設計原則、Singleton Pattern 兩種亞型、整體架構圖、技術選型 |
| [02_protocol.md](02_protocol.md) | §4–§5 | metadata 協議（io / examples / errors / entrydata）、錯誤處理慣例、`--json-errors` |
| [03_entry_manager.md](03_entry_manager.md) | §6 | LLM Entry Manager：queue 流程、rate limit、timeout、streaming、token 認證 |
| [04_hub.md](04_hub.md) | §7 | Function Hub：one-shot + server 雙形態、掃描策略、SFC 展開、LLM 摘要自舉 |
| [05_author_sfc.md](05_author_sfc.md) | §8–§9 | ai-core-author（generate→dry-run→register）、Small Function Center 設計 |
| [06_project.md](06_project.md) | §10–§14 | 目錄結構、CLI 入口、config 範例、開發里程碑（M0–M6）、跨平台注意事項 |
| [07_agents.md](07_agents.md) | §15 | Agent 整合策略、文檔分層、AGENTS.md 模板、export 格式、Self-Sufficiency 演進路徑 |
| [08_changelog.md](08_changelog.md) | §16 | 所有版本變更紀錄 |

---

## 快速定位

**「某個 CLI 旗標是什麼意思？」** → [02_protocol.md](02_protocol.md)（metadata 相關）或 [03_entry_manager.md](03_entry_manager.md)（ai-core-call / server）

**「要實作新元件，從哪個 pattern 套？」** → [01_overview.md](01_overview.md) §1 Singleton Resource Manager Pattern

**「ai-core-author 怎麼運作？」** → [05_author_sfc.md](05_author_sfc.md) §8

**「hub 怎麼掃 function？」** → [04_hub.md](04_hub.md) §7.5

**「怎麼接 Claude Code / Cursor / MCP？」** → [07_agents.md](07_agents.md) §15

**「現在做到哪了？」** → [06_project.md](06_project.md) §13 里程碑

**「config.json 怎麼寫？」** → [06_project.md](06_project.md) §12
