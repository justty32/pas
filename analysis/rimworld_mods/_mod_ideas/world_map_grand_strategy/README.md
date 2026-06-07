# 世界地圖動態派系政治 + 經濟據點 大戰略整合層（可行性報告群）

使用者構想 4–8 不是獨立 mod，而是**同一個大願景**：在 RimWorld 世界地圖上疊一層騎砍/十字軍之王風格的動態派系政治與經濟據點系統，建在既有 **Rim War + Vanilla Outposts Expanded + Faction Territories + Warband Warfare + 自寫輕量 WorldObject** 之上。

## 願景全貌（使用者原始構想 4–8 彙整）

- **idea 4**：讓 NPC 勢力也能建造 outpost（VOE 目前只有玩家能建）。
- **idea 5**：Rim War 各 NPC 據點的戰力成長公式（目前是簡單公式）改成與 outpost 資源點關聯；因 outpost 會很多，考慮自寫輕量 WorldObject（只圖標+指標）省效能；NPC outpost 不常駐小人，玩家襲擊/訪問時才 lazy 生成臨時 NPC。
- **idea 6**：visit settlement 能否用在 NPC outpost；Faction Territories 聯動（NPC 僅在領土內建 outpost、outpost 擴張領土）；Rim War 大地圖部隊接 Warband 記錄兵種組成（騎砍式）；大地圖臨時性物件（玩家部隊周圍十格刷巡邏隊/小型臨時聚居地，與 Territories 聯動影響互動）；臨時性事件（傷獸、旅商）。
- **idea 7**：上千勢力 + Rim War/Diplomacy 類頻繁計算的 mod 之效能（含原版/他 mod 為勢力生成首領與人物的成本）；遊戲途中新增/滅亡 NPC 勢力可行性；遊戲途中大地圖生成 NPC 據點可行性（Rim War 在場時）；目標＝勢力分裂/反叛/同盟/合併。
- **idea 8**：用原版生成勢力首領 NPC 的機制，生成其他勢力內的具名 NPC，遊戲途中定期更新其狀態；終極目標＝王國內除國王外有反叛者 NPC，定期計算進展，達閾值分裂出新勢力，大地圖據點/outpost 隨之易主；且 visit settlement 時能在特定據點找到這些 NPC（故生成時須計算其所在）。
- **idea 9**：襲擊或訪問 NPC 據點時，希望據點地圖是一個**完整的聚居點**——原版只隨便生成幾個房間 + 圍牆/防禦/農田/倉庫，使用者要更完善：議事廳、各 NPC 家族的房子、工坊等；且 outpost 也要支援這套地圖生成。
- **idea 10**（接續 9）：訪問/襲擊 NPC 據點時，NPC 也有**自己的生活**——會在議事廳討論、在工坊工作、處理農務（活的聚居點行為，而非只是站立/防守）。**並含玩家側互動**：玩家角色能在 NPC 據點的酒館與特定 NPC 對話、取得房間（租房/留宿），甚至在告示牌接本地工作（如幫忙收穫作物）。連回 idea 1（Talk 對話）與 idea 3（任務告示牌）。

## 三份報告

| 報告 | 涵蓋構想 | 主題 |
|---|---|---|
| `01_faction_scale_and_lifecycle.md` | 7、8 | 派系規模效能 + 動態派系生命週期（新增/滅亡/分裂/合併/結盟）+ 勢力內具名 NPC 政治演進 + 據點易主 + NPC 定位 |
| `02_outposts_and_world_objects.md` | 4、5(效能)、6(臨時) | VOE outpost 效能實測 + NPC 勢力擁有 outpost + 自寫輕量 WorldObject + lazy 臨時 NPC + visit settlement + 臨時巡邏隊/聚居地/事件 |
| `03_rimwar_warband_territories_integration.md` | 5、6(整合) | Rim War 擋襲擊與戰力公式 + 改綁 outpost + Warband 兵種 roster 接 Rim War 部隊 + Faction Territories 領土門檻/擴張橋接 |
| `04_settlement_map_generation.md` | 9 | NPC 據點/outpost 訪問/襲擊時的完整聚居點地圖生成（議事廳/家族房舍/工坊）；VBGE(KCSG) + RimCities + 原版 SymbolResolver 對比 |
| `05_settlement_npc_life_and_interaction.md` | 10 | NPC 活的聚居點行為（議事廳討論/工坊工作/農務，Lord/Duty 系統）+ 玩家側互動（酒館對話租房、本地工作板接任務） |
| `06_colony_archival_to_outpost.md` | （舊構想重啟） | 玩家「採樣殖民地產出→封存→當 outpost 持續抽象產出」；採樣借 RecordsTracker、抽象產出借 VOE、**同圖還原借 Faction Manager（自帶源碼）**；兩半各借一現成 mod |

## 權威源（工作目錄 /home/lorkhan/repo/pas）
- 本體：`projects/rimworld/`（`RimWorld/Faction.cs`/`FactionManager.cs`/`FactionGenerator.cs`、`RimWorld.Planet/WorldObject.cs`/`Settlement.cs`/`WorldPawns.cs` 等）
- 群組 mod 反編譯：`projects/rimworld_mods/{rim-war,faction-territories,warband-warfare}/`、VOE 引擎 `projects/rimworld_mods/vanilla-outposts-expanded/decompiled-framework/Outposts.decompiled.cs`
- 群組 mod 分析：`analysis/rimworld_mods/{rim-war,vanilla-outposts-expanded,faction-territories,warband-warfare}/`
- 注意：「Diplomacy」類 mod 未 clone，效能評估以「每派系逐 tick 計算」通則處理並標明未實裝量測。

## 先前構想對照（`analysis/rimworld/others/`）

`analysis/rimworld/` 核心分析下有一批**設計願景級**舊稿（14 份，2026-06-01 對 1.6 核對）＋可行性覆核 `analysis/rimworld/answers/mod_feasibility_review.md`（2026-05-23）。與本叢集主題幾乎全覆蓋，但兩者層級不同、**互補非重複**：

| 舊稿（設計願景，部分 API 未驗證；設定「原版白手起家」） | 對應本叢集（源碼可行性；設定「疊既有 mod」） |
|---|---|
| `outpost/simplified_outpost_logic.md`、`military_outpost_extension.md` | `02`（自寫輕量 WorldObject） |
| `geopolitics/dynamic_world_factions.md`、`dynamic_world_activity.md` | `01` + `03`（動態派系/世界模擬） |
| `geopolitics/{event_routing,geopolitical_barrier,global_influence}_extension.md` | `03` + `02`(臨時事件) |
| `life_politics/authority_leadership_system.md` | idea 8（具名 NPC 政治，見 `01`） |
| `life_politics/sims_mode_community.md` | `05`（NPC 自主生活） |
| `life_politics/rpg_quest_system.md` | idea 3（傭兵告示牌，見 `../03_mercenary_missions.md`）+ `05` B-2(本地工作板) |

**可直接複用的舊覆核硬傷警告**（`mod_feasibility_review.md`）：
- 哨站封存**無官方快照 API**，只能「抽象化（銷毀地圖留數值，如 Oskar Outposts）」或自序列化（極重，但 **Faction Manager mod 已做到同圖還原**，自帶源碼——見 `06` §4.5）→ 印證本叢集 `02` 的 lazy 生成、不持久化地圖。
- 事件重定向：`IncidentWorker.TryExecute` 別用 `ref`；普通 `WorldObject` 未實作 `IIncidentTarget`（要自己補 8 成員）；很多 worker 內部 `parms.target as Map` 會崩 → 只能對「能脫離地圖結算」的事件白名單重定向。
- `WorldRoutePlanner.GetRoute` **杜撰**（它是互動式 UI）；世界尋路走 `WorldPath`/`WorldPathing`（或 `Layer.Pather.FindPath`）。
- `map.resourceCounter.AllCountedAmounts` 只統計**儲存格**內物品（漏地上物/背包/作物/動物）→ 算產能別當「全圖快照」。

**框架轉變**：舊稿要在原版上**從零**打造帝國/世界層；本叢集改為**疊在 Rim War（世界模擬）+ VOE（哨站）+ Faction Territories（領土）+ Warband（部隊）上整合**——把舊藍圖最重的地基外包給既有 mod，工程量可能更小，代價是相依與相容。

## 狀態
- 2026-06-07：建立六份整合可行性報告（R1–R5 idea 4–10 + `06` 殖民地封存→outpost）＋與 `analysis/rimworld/others/` 舊願景稿 cross-reference。`02` §2.5/§3.3、`06` §4.5 補入本日源碼查證：VOE outpost 永不生成地圖（Map 恆 null）、Faction Manager（2878135150，自帶源碼）做到同圖序列化還原但卸載期不產出。此叢集規模遠大於 idea 1/2/3，預期需再拆成數個子 mod / 分階段 spec。**中樞＝idea 8 具名 NPC/家族資料層**。待使用者讀後界定優先序。
