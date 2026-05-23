# RimWorld Mod 構想：可實現性檢視 (Feasibility Review)

> 對照基準：`projects/rimworld/` 反編譯源（**版本判定為 1.6 / Odyssey**，依據 `RimWorld.Planet/WorldObject.cs:93` 的 `Tile` 已是 `PlanetTile` struct、且存在 `RimWorld.Planet/Gravship.cs`、`PlanetLayer`）。
> 方法：把 `others/` 各構想中**寫死的 API 呼叫**逐一拿原始碼驗證，標出成立 / 需改寫 / 杜撰，並列隱藏的坑。

## 0. 全域前提（影響所有「帝國」系列）

### 0.1 「哨站封存→隨時解封還原同一張地圖」是最大架構難點
- 移除地圖確實有官方 API：`Verse/Game.cs:723 DeinitAndRemoveMap(Map, bool)`，並被「放棄聚落」流程使用（`RimWorld.Planet/MapParent.cs:115, :320`）。
- **但 `DeinitAndRemoveMap` 是「銷毀」，沒有任何快照/還原機制。** 一旦移除，地圖即不存在；想「重新生成同一張地圖」只有兩條路：
  1. 自行序列化整張地圖（極重、易與其他 Mod 衝突）；或
  2. 把 `Map` 物件留在記憶體、移出 `Current.Game.Maps` 的 tick 清單（佔記憶體、生命週期脆弱）。
- 現實參照：知名的 **Outposts (Oskar)** Mod 走的是「抽象化」路線——銷毀地圖、只保留數值，**不還原原貌**。`military_outpost_extension.md` 寫的「根據封存的地圖快照暫時重新生成地圖」與此衝突，需降級為「重生成一張**新**戰場圖」或接受巨大序列化成本。

### 0.2 1.6 的 `PlanetTile`（**更正：這不算硬傷**）
- 1.6 起 `Tile` 是 `PlanetTile` struct（`WorldObject.cs:93`、`IIncidentTarget.cs`）。先前一度把「所有 `.Tile` 當 int」列為需全面遷移的硬傷，**這是高估**。
- `PlanetTile` 與 `int` **有雙向隱式轉換**（`RimWorld.Planet/PlanetTile.cs:89` `implicit operator int`、`:94` `implicit operator PlanetTile`），所以舊構想的 pseudocode 在**單一星球層**下大多照樣編譯、照樣跑。
- 真正要注意的只有**多星球層（`PlanetLayer`）**情境：尋路、`WorldObjectAt`、距離計算等要沿用同一 `tile.Layer`，不能把不同 layer 的 tileId 混算。屬「正確性提醒」而非「需重寫」。

---

## 1. 逐項判定

### ✅ 可行（標準作法，低風險）

| 構想 | 判定依據 |
| :--- | :--- |
| **C. 魔紋 Mod**（`magic_tattoo_mod_design.md`） | `HediffDef` + `stages/statOffsets` + `Recipe_Surgery`/`addsHediff` 是所有義體/植入物 Mod 的標準路徑；Scribe（`IExposable`）做存檔正確。文件**自己已正確指出** `MaxHitPoints` 是物品屬性、強化 Pawn 生存應走減傷/`Pawn_HealthTracker`——這個自覺很對。 |
| **C. 魔紋 UI**（`magic_tattoo_ui_design.md`） | `Verse.Window` + `GetGizmos()` + `FloatMenu` + `Hediff.TipStringExtra` 全是公開 API，雛形可行。`map.resourceCounter.AllCountedAmounts` 確實存在（`ResourceCounter.cs:17`），但見 §2 範圍坑。 |
| **B. ARPG 化**（`arpg_conversion_design.md`） | 浮動技能欄（自訂 Window）、用 `Hediff` 給屬性而非點數、熱鍵施法+冷卻環，皆為純 UI/Comp 層，技術上成立。難點不在 API 而在**工程量**（多角色記憶、目標選取、與原版 Job 系統共存）。 |
| **A④ 產能：理論產出版**（`productivity_profiling_logic.md` §1B） | 記錄採樣期「收穫營養值/挖礦量/工作台完成價值」反而比抓庫存準確，可掛各 `JobDriver`/`RecordsTracker` 完成事件，可行。 |

### ⚠️ 可行但需重寫關鍵點

| 構想 | 問題與正解 |
| :--- | :--- |
| **A⑤ 事件重定向**（`event_routing_extension.md`） | (1) `IncidentWorker.TryExecute(IncidentParms parms)` 是**傳值的參考型別**（`IncidentWorker.cs:183`），文件的 Harmony `Prefix(ref IncidentParms parms)` 用 `ref` **會比對失敗**——去掉 `ref`，直接改 `parms.target` 欄位即可。 (2) **更嚴重**：`parms.target` 型別是 `IIncidentTarget`（`IncidentParms.cs:10`），而**普通 `WorldObject`/`MapParent` 並未實作 `IIncidentTarget`**（`WorldObject.cs:11` 只有 `IExposable, ILoadReferenceable, ISelectable`）。實作者的 `OutpostWorldObject` 必須**自己實作 `IIncidentTarget` 的 8 個成員**（`IIncidentTarget.cs`：`Tile/StoryState/GameConditionManager/PlayerWealthForStoryteller/...`）。 (3) 即便如此，許多 `IncidentWorker` 內部直接 `parms.target as Map` 取地圖，把 target 換成非-Map 物件**會讓那些 worker 崩潰**——只能對「能脫離地圖結算」的事件做重定向，且要逐一白名單測試。 |
| **A② 軍事哨站誘敵**（`military_outpost_extension.md`） | `incidentParms.target = outpost` 同上 §IIncidentTarget 限制。「嘲諷值改寫襲擊目標」可行（在 incident 生成期攔截），但「手動進入戰場重生成快照地圖」受 §0.1 限制。 |

### ❌ API 杜撰 / 需整段換掉

| 構想 | 問題 |
| :--- | :--- |
| **A② 地緣攔截**（`geopolitical_barrier_extension.md`） | 文件的 `Find.WorldRoutePlanner.GetRoute(source.Tile, target.Tile)` **不存在**。`WorldRoutePlanner` 是**玩家互動式路線規劃 UI**（`WorldRoutePlanner.cs` 只有 `Start/Stop/WorldRoutePlannerUpdate/TryAddWaypoint/...`，**無 `GetRoute`**）。真正的世界尋路在 `RimWorld.Planet/WorldPath.cs` + `WorldPathing.cs`（取得 `WorldPath` 後走 `NodesReversed`）。整段 `GetInterceptingOutpost` 需改用世界尋路 API 重寫。`WorldObjectAt<T>(PlanetTile)` 本身存在（`WorldObjectsHolder.cs:380`），但參數型別是 `PlanetTile`。 |

### 🟡 設計可行、屬「重型功能」（API 不是瓶頸，工作量才是）

- **A③ 動態世界/行動隊**（`dynamic_world_factions.md` / `dynamic_world_activity.md`）：實體軍隊用 `WorldObject` + `WorldObjectComp` 在大地圖移動、季度結算擴張，全是抽象數值運算，技術可行；但這等於自建一套大戰略模擬層，是整個藍圖工程量最大的部分。文件 §5「抽象運算/事件驅動」的方向正確。
- **A④ Sims 模式 / 權威系統**（`sims_mode_community.md` / `authority_leadership_system.md`）：NPC 自主生活可掛 ThinkTree/Lord（`Verse.AI.Group`），指揮權分級用 Hediff/狀態旗標控制 `Drafted` 權限——可行，但要大量改寫 Pawn 控制權判定，且與原版「玩家擁有全 colony」假設衝突，邊界情況多。
- **A⑤ 全球影響力**（`global_influence_extension.md`）：文化滲透/物流網/氣候塔/數據中心皆為哨站數值 buff，掛在 `WorldObjectComp` 的定期 tick 即可，低 API 風險、純設計取捨。

---

## 2. 兩份產能文件共同的隱藏坑：`ResourceCounter` 的真實範圍

兩份都靠 `map.resourceCounter.AllCountedAmounts` 做「全地圖快照」，但原始碼顯示它**只統計**：
- 來源僅限**儲存格** `haulDestinationManager.AllGroupsListForReading` 的 `HeldThings`（`ResourceCounter.cs:130-141`）；
- 且需 `def.CountAsResource == true`；
- 且 `ShouldCount`：非腐壞、非霧化（`ResourceCounter.cs:158-168`）；
- 更新頻率：每 204 tick 一次（`ResourceCounterTick`，`:120`）。

**因此它漏掉**：地上未入庫物、Pawn 背包、站立作物、活體動物、已安裝建築、`CountAsResource=false` 的物品。
→ `simplified_outpost_logic.md` 自稱「全地圖資產快照（Inventory Delta）」其實是「**儲存區 Delta**」，名實不符；想真做全圖須改掃 `map.listerThings`。諷刺的是 §0.1 提到的「理論產出（工作量）」版本反而更貼近真實產能。

---

## 3. 一句話結論

- **獨立、即可動工**：魔紋 Mod（C）、ARPG 化（B，工程量大但無 API 障礙）。
- **核心可行但要先解難題**：整個帝國藍圖（A）的地基「哨站封存還原」沒有官方快照 API，必須先選定「抽象化(推薦) vs 自序列化」路線（§0.1）。
- **必須改寫的硬傷**：地緣攔截的 `WorldRoutePlanner.GetRoute`（杜撰，§1❌）、事件重定向的 `ref` 與 `IIncidentTarget` 三連坑（§1⚠️）、產能快照的範圍誤解（§2）。
- **非硬傷、僅提醒**：`PlanetTile` 因有 int 隱式轉換，單層下不必改；只在多星球層要留意 layer（§0.2 已更正）。

> 修正紀錄 (2026-05-23)：上述硬傷已回寫各 `others/` 構想文件——`geopolitical_barrier_extension.md`（改用 `Layer.Pather.FindPath`）、`event_routing_extension.md`（去 `ref`＋IIncidentTarget/as-Map 警告＋抽象結算）、`military_outpost_extension.md`（封存改「保留 Map 或重生成新圖」）、`simplified_outpost_logic.md`（改稱「儲存區 Delta」並標 ResourceCounter 範圍）。

---
*文件路徑: analysis/rimworld/answers/mod_feasibility_review.md*
*檢視日期: 2026-05-23 — 對照 projects/rimworld (1.6/Odyssey)*
