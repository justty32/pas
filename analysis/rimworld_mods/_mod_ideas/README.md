# RimWorld Mod 構想可行性報告（create 規劃）

使用者陸續提出 **11 個** mod 構想，要求逐一出可行性報告。本目錄為**規劃/可行性層**（非實作）：每份報告對 `projects/rimworld/`（1.6 本體反編譯權威源）與已分析的群組 mod 落實機制，給出架構草案、純 XML vs C# 拆分、風險坑、開放設計問題。

> 留檔依據：本體源 `projects/rimworld/`（權威，CLAUDE.md memory「analysis 非權威、對比演算法讀 projects 源」）；群組 mod 分析 `analysis/rimworld_mods/<mod>/`；RimTalk 為外部未 clone mod，經網路調查（見 `02` 報告）。

## 報告地圖

**社交/對話軌（3 個獨立 mod，2 條軌道）**

| | mod | 軌道 | 規模 | 報告 |
|---|---|---|---|---|
| **A** | 「Talk」強制社交動作 | 社交/對話 | 小（可能免 Harmony） | `01_talk_action.md` |
| **B** | 情境化對話內容（參考 RimTalk） | 社交/對話 | 中（模板 vs LLM） | `02_contextual_dialogue.md` |
| **C** | 宇宙僱傭兵任務系統（參考 Warband） | 戰役玩法 | 大 | `03_mercenary_missions.md` |
| **D** | 與 NPC 對話驅動的互動（任務/分支對話/交易/委託，idea 11） | 社交/對話 | 中（純 XML 為主，建在 CQF） | `04_npc_dialogue_interactions.md` |

A+B 同軌天生組合（A 觸發、B 內容、Bubbles 顯示，即 RimTalk 拆法）；C 獨立。D 建在 **CQF（Custom Quest Framework）** 的 DialogTreeDef 上，與 A（Talk 觸發）共用 1.6 FloatMenuOptionProvider 機制、可並存；服務世界叢集 idea 10（據點酒館/租房併入對話樹）。

**世界地圖大戰略叢集（idea 4–10，互相依賴的大整合）** → 見 `world_map_grand_strategy/`（R1–R5 + README），**中樞＝idea 8 具名 NPC/家族資料層**。

## 建置策略：盡量別重造輪子（使用者原則 2026-06-07）

> 原則：有現成 mod 就用，優先「疊/擴/接」既有 mod，自建只留在沒有現成 or 現成是錯工具之處。

| 構想 | 可借力的現成 mod / 原版 | 必須自建（無現成 or 現成不適用） | 借力程度 |
|---|---|---|---|
| 1 Talk | 原版 `FloatMenuOptionProvider`+`TryInteractWith`（免 Harmony）；Bubbles/SpeakUp 自動接顯示與文本 | 1 個 provider 子類 + 自訂 InteractionDef/JobDriver（極小） | 高（純疊原版 API） |
| 2 對話 | **RimTalk**（LLM＋`ContextHookRegistry` 公開注入 API）／**SpeakUp**（模板）／**Bubbles**（顯示） | 幾乎零——做成 RimTalk 的 context-hook/內容包即可；只有「自走後端（ai_core）」才需自建 | **最高（建議當 RimTalk 內容包）** |
| 3 傭兵 | 原版穿梭機(Royalty)＋`CaravansBattlefield`（敵清/撤離）；Warband（同型範本） | 告示牌 UI、MissionDef、調度膠水 | 中高（原版機制重用） |
| 4 NPC outpost | 原版 `Settlement`（lazy 守軍）；Faction Territories 認 outpost | ⚠️**自寫輕量 WorldObject**——VOE 是現成但**錯工具**（綁玩家+常駐 pawn 太重，R2） | 中（**這是「現成不適用」例外**） |
| 5 Rim War 戰力綁 outpost | **Rim War**（擴其公式，Harmony postfix `IncrementSettlementGrowth`） | outpost→戰力耦合（薄 postfix） | 高（擴既有，不重建世界模擬） |
| 6 領土/部隊/臨時物件 | **Faction Territories**（public API，低）／**Warband**（roster 模型）／原版 `TimeoutComp`（臨時物件）＋ incident（傷獸/旅商） | 三者間的橋接（Warband↔RimWar 最重，需橋接 DLL） | 高 |
| 7 派系規模/動態 | **Rim War**（派系模擬/佔領） | 動態分裂/合併/反叛 + 派系生命週期管理（**原版無安全滅亡 API**，無現成 mod） | 中（模擬借 Rim War，動態層自建） |
| 8 具名 NPC 政治（**中樞**） | 原版 world pawn / 首領生成 / `previouslyGeneratedInhabitants`（定位） | **具名 NPC/家族資料層 + 定期演進 + 分裂觸發**（無現成 mod，核心自建投資） | 低（建在原版機制上，但邏輯自建） |
| 9 聚居點地圖 | **VBGE/KCSG**（手繪佈局純 XML，需 VFE Core）／RimCities（程序）／AUR（預製） | C# 後處理 GenStep 把家族 NPC 綁進房舍（無論哪條都需） | 高（KCSG 當外觀層） |
| 10 NPC 生活+玩家互動 | **RimCities `LordJob_LiveInCity`** 範式（duty 樹純 XML）；原版 `JobDriver_SingleInteraction`（對話） | 薄 `LordJob_SettlementLife`、假動作 JobDriver；**租房/留宿原版無資料模型→全自建（最大缺口）**、本地工作板 | 中高 |
| 11 NPC 對話互動（任務/分支對話/交易/委託） | **CQF `DialogTreeDef`**（對話樹純 XML，`DialogResult.actions` 掛任意 CQFAction）＋自帶 `FloatMenuOptionProvider_Dialog`（免 Harmony 觸發）；啟動任務=`CQFAction_Quest`、巢狀對話=`CQFAction_StartDialog`、以物易物=`DialogOption.requiredThings`、固定配方委託=`CQFAction_DelayExecute`（皆純 XML，~80%） | 兩個小 CQFAction 子類：①開原版交易視窗（CQF 零 trade，須 `TradeSession.SetupWith`+`Dialog_Trade`）②委託含品質 RecipeDef | 高（建在 CQF，僅委託服務自建） |

**收斂結論**：在「別重造輪子」原則下，真正必須**重投入自建**的只有四塊——**idea 8 具名 NPC/家族層（中樞）**、idea 7 動態派系生命週期（原版無安全滅亡 API）、idea 10 租房資料模型（原版沒有）、idea 4 輕量 WorldObject（VOE 是錯工具）。其餘大多能靠疊既有 mod + 原版機制達成。idea 2 甚至可幾乎不自建（當 RimTalk 內容包）。

## 跨報告共同發現
- **強制互動 API**：`Pawn_InteractionsTracker.TryInteractWith(...)`（`projects/rimworld/RimWorld/Pawn_InteractionsTracker.cs:176`）。
- **1.5+ 浮動選單**：`FloatMenuOptionProvider` 抽象類自動收集子類，加右鍵選項可能**免 Harmony**。
- **穿梭機體系**（Royalty）能脫離 Quest 直接生成調度（`RoyalTitlePermitWorker_CallShuttle` 範本）。
- **RimTalk**：provider-agnostic LLM，輸出 re-route 進 Bubbles，公開 `ContextHookRegistry`；可改接使用者 `ai_core`。

## 狀態
- 2026-06-07：11 構想可行性報告完成（社交軌 `01-04` + 世界叢集 `world_map_grand_strategy/R1-R5`），與 `analysis/rimworld/others/` 舊願景稿 cross-reference，並依「別重造輪子」原則收斂出建置策略表。待使用者選定先 brainstorm 哪一個成完整 spec → 再進 writing-plans。
- 更正：`derived/.../cqf-caravan-redemption` **實際只用 QuestScriptDef、未用 DialogTreeDef**；手寫 DialogTree 無本地範例，建議用 CQF 遊戲內 QuestEditor 視覺化編輯後導出。`.QuestEditor_Library/Skill/*/SKILL.md` 不在 projects 樹中，CQF 結論以反編譯源 `QuestEditor_Library.decompiled.cs` 為準。
