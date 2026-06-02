# Others — 設計構想索引

五個子系統的設計構想與 UI 規劃，共 14 份文件。
所有文件均已對照 1.6/Odyssey 源碼核對（核對日期：2026-06-01）。

---

## magic_tattoo/ — 魔紋系統（2 份）

| 文件 | 內容摘要 |
|---|---|
| [magic_tattoo_mod_design.md](magic_tattoo/magic_tattoo_mod_design.md) | 素材→汁液→Hediff 整體流程設計；CompMagicInk、Recipe_ApplyMagicTattoo 設計 |
| [magic_tattoo_ui_design.md](magic_tattoo/magic_tattoo_ui_design.md) | 汁液物品說明、健康面板、鍊藥鍋互動 UI、視覺紋身圖層設計 |

---

## arpg/ — ARPG 化（1 份）

| 文件 | 內容摘要 |
|---|---|
| [arpg_conversion_design.md](arpg/arpg_conversion_design.md) | WASD 移動、Cleave/Mana 機制、技能欄/天賦樹 UI、熱鍵系統整體架構構想 |

---

## outpost/ — 帝國哨站（3 份）

| 文件 | 內容摘要 |
|---|---|
| [military_outpost_extension.md](outpost/military_outpost_extension.md) | 哨站 WorldObject 封存抽象化、屬性映射、空投補給機制構想 |
| [simplified_outpost_logic.md](outpost/simplified_outpost_logic.md) | 簡化版哨站邏輯設計（輕量替代方案） |
| [productivity_profiling_logic.md](outpost/productivity_profiling_logic.md) | 產出採樣方法（移動平均 / 理論產出）、屬性映射、防作弊機制構想 |

---

## geopolitics/ — 地緣 / 世界（5 份）

| 文件 | 內容摘要 |
|---|---|
| [global_influence_extension.md](geopolitics/global_influence_extension.md) | 全球影響力擴散、WorldComponent 全球增益設計 |
| [event_routing_extension.md](geopolitics/event_routing_extension.md) | 事件重定向（轉運站 Hub）、地緣攔截設計 |
| [geopolitical_barrier_extension.md](geopolitics/geopolitical_barrier_extension.md) | 動態派系邊界、邊境長城、影響力衝突機制 |
| [dynamic_world_factions.md](geopolitics/dynamic_world_factions.md) | 派系動態擴張、聚落分級（AoW 模式）、實體行動隊構想 |
| [dynamic_world_activity.md](geopolitics/dynamic_world_activity.md) | 世界在玩家不操作時的自主演化機制 |

---

## life_politics/ — 生活 / 政治（3 份）

| 文件 | 內容摘要 |
|---|---|
| [rpg_quest_system.md](life_politics/rpg_quest_system.md) | 冒險者公會、佈告欄任務系統、QuestPart 自訂設計 |
| [sims_mode_community.md](life_politics/sims_mode_community.md) | Sims 自主社區構想、ThinkTree/FloatMenu 掛鉤設計 |
| [authority_leadership_system.md](life_politics/authority_leadership_system.md) | 基於階級/聲望/職位的動態指揮權系統構想 |

---

*對應實作文件見 `../details/`；對應架構文件見 `../architecture/`。*
