# RimWorld 1.6 / Odyssey — 分析資料夾說明

核對基準：`projects/rimworld/`（1.6/Odyssey 反編譯源碼）。
分析目標：五個子系統 Mod 的可行性驗證、API 正確性、C# 實作細節。

---

## 快速入口

| 情境 | 去哪裡 |
|---|---|
| 瀏覽全部文件 | [`html/index.html`](html/index.html)（導覽層，暗色系卡片介面） |
| 了解 Mod 五個子系統可行性 | [`answers/mod_feasibility_review.md`](answers/mod_feasibility_review.md) |
| 了解引擎架構 | [`architecture/overview.md`](architecture/overview.md) |
| 想寫 Def / XML 系統 | [`architecture/def_system.md`](architecture/def_system.md) |
| 想寫哨站封存 | [`architecture/outpost_archiving_strategy.md`](architecture/outpost_archiving_strategy.md) |

---

## 目錄結構

```
analysis/rimworld/
├── architecture/   # 引擎子系統架構（11 份，含 Def 載入管線）
├── tutorial/       # 目標導向開發教學（29 份，Harmony/Pawn/世界/UI/...）
├── details/        # 五個 Mod 子系統 C# 實作細節（15 份）
├── others/         # 設計構想與 UI 規劃（14 份）
├── answers/        # 具體問答：可行性審查（1 份）
├── html/           # HTML 導覽層（index.html + 5 分類頁 + _shared.css）
├── gemini_temp/    # 會話進度快照
└── session_log.md  # 操作日誌（每項操作一句話，append-only）
```

---

## 五個 Mod 子系統索引

| 子系統 | 構想（others/） | 實作（details/） |
|---|---|---|
| **魔紋** | `magic_tattoo_mod_design`, `magic_tattoo_ui_design` | `magic_tattoo_implementation` |
| **ARPG 化** | `arpg_conversion_design` | `arpg_core_mechanics`, `ui_system_design`, `talent_skill_integration`, `hotkey_system_design`, `mod_settings_integration` |
| **帝國哨站** | `advanced_outpost_system`, `simplified_outpost_logic`, `productivity_profiling_logic` | `military_outpost_implementation`, `optimized_outpost_core` |
| **地緣 / 世界** | `geopolitical_barrier_extension`, `global_influence_extension`, `event_routing_extension`, `dynamic_world_factions`, `dynamic_world_activity` | `geopolitical_influence_implementation`, `event_routing_implementation`, `world_faction_system` |
| **生活 / 政治** | `rpg_quest_system`, `sims_mode_community`, `authority_leadership_system` | `rpg_quest_system_implementation`, `sims_mode_community_implementation`, `leadership_system_implementation` |

---

## 核對狀態

所有文件均已對照 1.6/Odyssey 源碼核對（核對日期：2026-06-01）。
發現的 API 錯誤、杜撰方法、型別問題均已回寫至各原始 .md 的 ⚠️ 核對 行內注解。
