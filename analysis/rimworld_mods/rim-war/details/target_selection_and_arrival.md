# Rim War 目標選擇與抵達行為鏈（target_selection_and_arrival）

> 深掘「WarObject 怎麼挑目的地、抵達後發生什麼」，作為 npc-outposts-rimwar（Mod 1）與 empire-warfare（Mod 2）兩個衍生 mod 的設計依據。所有行號指 `projects/rimworld_mods/rim-war/decompiled/RimWar.decompiled.cs`。生成分派與戰鬥結算總覽見 `architecture/01_world_simulation.md`，接點總表見 `details/extension_points.md`。

## 0. 先講最重要的結論

1. **`IsValidSettlement`（`:16685`）不在任何「目標查詢」路徑上**。它只把關「聚落註冊」（哪些聚落算 RimWarData 的資產/行動來源）。目標查詢的真正條件是：`is Settlement`＋`FactionUtility.HostileTo`＋**掛有 `RimWarSettlementComp` 且 points>0**＋在掃描範圍內。
2. 因此 **任何 `Settlement` 子類（NpcOutpost、WorldSettlementFC）只要掛上 comp 就會被 warband 選為攻擊目標**，不需要動 `IsValidSettlement`。
3. WarObject **行軍途中不會「順路」打聚落**（`ScanAction :14701` 只交戰 Caravan/RimWarSite/WarObject）；聚落交戰只發生在 `ArrivalAction`（抵達目的地 tile）。
4. `AdjustCaravanTargets`（`:17235`）是**玩家 caravan 追擊 WarObject** 的重導，不是 WarObject 改派；WarObject 自己的目標失效重導在 `TickInterval`（`:14647`–`:14677`）與 `ValidateTargets`（`:14762`）。
5. Empire 附庸（def `FactionBaseGenerator`）**已在 v1.6 白名單內**（`:16690`），且有整套 Vassal 特例：附庸自己不行動（`:17107`）、被打要過 `vassalHeat` 門檻、**抽象戰永遠不會被佔領**（`:11151`）。

---

## 1. 每種 WarObject 的目的地怎麼挑

### 1.1 掃描範圍：SettlementScanRange

```
RimWarSettlementComp.SettlementScanRange (:9214)
  = Clamp( (0.4 × RimWarPoints + 1400) / settlementScanRangeDivider,
           10, maxSettlementScanRange )
```
- `maxSettlementScanRange` 預設 75（`:7631`），玩家滑桿 20–200（`:7398`）；`SettingsRef.maxSettelementScanRange`（`:7577`，注意拼字錯誤）為執行期快照。
- 聚落越強掃越遠 → 戰力與「威脅投射半徑」直接掛鉤。各 Attempt* 再乘上 behavior/動作係數（見 1.3 表）。

### 1.2 候選池的三層來源

| 來源 | 行 | 內容與過濾 | 何時用 |
|---|---|---|---|
| `rwsComp.NearbyHostileSettlements` | `:9393` | 來自 `OtherSettlementsInRange`（`:9326`，cache 週期 `settlementScanDelay`，threaded 時丟背景緒 `:9351`）→ `GetRimWorldSettlementsInRange(parent.Tile, SettlementScanRange)`（`:9354`/`:9370`）。過濾：**comp != null && RimWarPoints>0**（`:9411`）＋ `FactionUtility.HostileTo`，上限 20 筆（`:9406`） | **預設路徑**（warband / launched warband） |
| `rwd.HostileSettlements` / `NonHostileSettlements` | `:1402`/`:1424` | 由 `WorldUtility.UpdateRWDSettlementLists`（`:16130`）全地圖重建：**需 comp != null 且 RWD.behavior != Excluded**（`:16140`），敵我判定 `HostileTo`（`:16142`）。事件迴圈每 `rwdUpdateFrequency` 重整（`:17109`–`:17113`） | 設定 `forceRandomObject` 開啟時 |
| `GetClosestSettlementInRWDTo(rwd,…)` | `:16259` | **自家派系**最近聚落（用 `rwd.WorldSettlements`，即 IsValidSettlement 閘後的註冊清單） | `IsAtWar` 時額外塞入候選（warband 順帶增援自家前線聚落） |

底層幾何查詢（全在 `WorldUtility`）：

| 函式 | 行 | 過濾 | 重要備註 |
|---|---|---|---|
| `GetWorldObjectsInRange` | `:16389` | 距離 ≤ range | **隨機順序、最多取 5 個就停**（`:16415`）→ 上層所有掃描都是「抽樣」不是窮舉 |
| `GetRimWorldSettlementsInRange` | `:16154` | 上者結果中 `is Settlement` | **任何 Settlement 子類都過**，無 def 白名單 |
| `GetRimWarSettlementsInRange` | `:16172` | 走 rwdList，TraversalDistance，最多 3 筆 | |
| `GetHostileSettlementsInRange` | `:16291` | `HostileTo`（`:16299`） | **不要求 comp**；被 `FindHostileSettlement :15019` 使用 |
| `GetNonHostileRimWarSettlementsInRange` | `:16307` | 全部排除敵對 | |
| `GetFriendlySettlementsInRange` | `:16314` | Faction 完全相同 | |
| `GetHostileSettlementsToRWD` | `:16345` | 全地圖 `HostileTo` | 無距離限制 |
| `GetClosestSettlementOfFaction` | `:16221` | 指定派系 `WarSettlementComps` 最近者 | forcePlayerTown 用 |
| `GetHostileWarbandsInRange` / `GetHostileWarObjectsInRange` | `:16482`/`:16501` | `HostileTo` 的單位 | |

### 1.3 六種 WarObject 的目標選擇（逐函式）

每種動作都有三個版本：threaded 的 `*OffMainThread`（查詢）＋`*OnMainThread`（生成）、與 `*_UnThreaded`（單緒合併版，邏輯同）。以下以 UnThreaded 行號為主。

| 動作 | 入口（分派 `:17144`–`:17185`） | 查詢主體 | 候選池 | 範圍 | 生成門檻與 Create* |
|---|---|---|---|---|---|
| **Warband** | `AttemptWarbandActionAgainstTown :18081` | `_UnThreaded :17984`（threaded 拆 `:17882`/`:17914`） | forceRandomObject→`rwd.HostileSettlements`（`:17996`）；forcePlayer→玩家 `WorldSettlements`（`:18000`）；預設→`NearbyHostileSettlements`（`:18004`）；IsAtWar 加自家最近聚落（`:18008`）且範圍×1.5（`:18013`） | `SettlementScanRange` | 隨機抽 1（`:18021`），距離閘（`:18022`）；成本=`CalculateWarbandPointsForRaid`（`:15871`，目標points×1.1~1.8）×behavior（Cautious×1.1/Warmonger×1.25，`:18032`）；需源聚落 points×0.75 ≥ 成本（宣戰中 ×0.85＋成本×1.2，`:18040`–`:18059`）→ `CreateWarband :15467` |
| **LaunchedWarband** | `AttemptLaunchedWarbandAgainstTown :18281`（**源聚落需 ≥1000 points**，`:18283`） | `_UnThreaded :18191`（`:18091`/`:18123`） | 同 Warband | **`SettlementScanRange × 2`**（`:18199`），IsAtWar 再 ×1.5（`:18220`） | 門檻 ×0.6（宣戰 ×0.8，`:18248`/`:18264`）→ `CreateLaunchedWarband :15538` |
| **Scout** | `AttemptScoutMission :18584` | `_UnThreaded :18443`（`:18294`/`:18353`） | **`GetWorldObjectsInRange`（`:18486`）**——目標可以是 Caravan / WarObject / Settlement 三類 | `SettlementScanRange` ×（Expansionist 1.3 / Warmonger 1.2 / Aggressive 1.1，`:18459`–`:18470`） | 過濾 `HostileTo`（`:18492`）；目標強度 ≤ 源(points−damage)×0.5：Caravan 財富/200（`:18508`）、WarObject points（`:18516`）、Settlement comp points（`:18525`）→ `CreateScout :15589`（`:18540`/`:18553`/`:18569`） |
| **Trader** | `AttemptTradeMission :18925` | `_UnThreaded :18871`（`:18808`/`:18830`） | forceRandomObject→`rwd.NonHostileSettlements` 抽 1（`:18881`）；forcePlayer→玩家聚落（`:18885`）；預設→`NearbyFriendlySettlements`（`:18889`，同派系，`:9465`） | `SettlementScanRange`（`:18877`） | 對玩家需 `FactionCanTrade`（`:18896`）；成本=`CalculateTraderPoints`（`:15882` 附近，敵×0.25/玩家×1.0）×behavior；需 points×0.5 ≥ 成本（`:18913`）→ `CreateTrader :15657` |
| **Settler** | `AttemptSettlerMission :18763`（外層另檢查派系聚落數 < `maxFactionSettlements`，`:17167`） | `_UnThreaded :18682`（`:18594`/`:18666`） | **不是聚落而是空 tile**：`TileFinder.TryFindPassableTileWithTraversalDistance(10~num)` 抽 5 次（`:18716`–`:18728`），排除極端生態（`:18723`）、排除 10 tile 內已有 `WorldObjectDefOf.Settlement`（`:18738`–`:18746`） | `Clamp(SettlementScanRange, 11, max)` ×（Expansionist 1.2 / Warmonger 0.8，`:18705`–`:18713`）；**源聚落需 >500 points**（`:18703`） | 固定 Rand(0.4,0.6)×500（`:18757`）→ `CreateSettler :15783`（走 `DestinationTile`；`Settler.UseDestinationTile => true`，`:12310`） |
| **Diplomat** | `AttemptDiplomatMission :19049`（需設定 `createDiplomats`，`:17150`；**源聚落需 >1000 points**，`:19056`/`:19092`） | `_UnThreaded :18997`（`:18936`/`:18956`） | `GetRimWorldSettlementsInRange`（`:19013`）——**敵友皆可**（去調 goodwill） | `SettlementScanRange`（`:19004`） | 成本=`CalculateDiplomatPoints`（`:15895`，100~200）×behavior；需 points×0.5 ≥ 成本（`:19037`）→ `CreateDiplomat :15728` |
| （附）**Reinforcement** | `AttemptReinforcement :19103`（事件迴圈 `:17127`–`:17143`：被圍聚落向 50 tile 內友軍求援，`NearbyFriendlySettlementsWithinRange :9551`） | — | 指定目標聚落 | 50 tile | 0.4×points 的 `CreateTrader`（送點數） |

**共同的對玩家/附庸保護閘**（warband/launched/scout 皆有，行號以 warband UnThreaded 為例）：
- 開局保護：`preventActionsAgainstPlayerUntilTick`（`:18022`；初始化 `:16901`）。
- 熱度：目標是玩家需 `rwsComp.PlayerHeat ≥ minimumHeatForPlayerAction`（`:18022`）；目標是附庸需 `PlayerHeat ≥ 目標comp.vassalHeat`（`:18027`）。出手後 PlayerHeat 歸零、門檻上調（`GetHeatForAction :19126`；附庸 `vassalHeat += 2×heat`，`:18055`/`:18186`/`:18260`/`:18348`/`:18579`）。
- `FactionCanFight(200, …)`（`:18027`；def `:16711`）：派系要有 Combat pawnGroupMaker。

### 1.4 `IsValidSettlement` 的真正呼叫點（全檔僅 4 處）

| 呼叫點 | 行 | 角色 |
|---|---|---|
| `RimWarData.WorldSettlements` getter 重建 | `:1283`（property `:1265`） | **派系資產註冊**：只有白名單 def 進 `WorldSettlements` → 連動 `WarSettlementComps`（`:1294`）、`PointsFromSettlements`（`:1333`）、`GetClosestSettlementInRWDTo`、`RemoveRWDFaction` 的存亡判定 |
| `WorldComponent_PowerTracker.UpdateFactionSettlements` | `:17839`（方法 `:17824`） | 把新聚落補登進 `WorldSettlements` 並呼叫 `CreateRimWarSettlement`（`:17857`→`:15191`，初始化 comp points＋信件）；第二迴圈把消失者移除（`:17860`–`:17879`） |
| `WorldComponentTick` 事件迴圈 | `:17098` | **行動來源閘**：隨機抽到的源聚落必須 valid 才會產生動作 |
| `RimWar_DebugToolsPlanet.UpdateFactionSettlements` | `:5481`（debug 類 `:4390` 起） | 開發工具的複本，僅 dev mode |

白名單本體（`:16690`）：defName ∈ {`Settlement`, `City_Faction`, `City_Citadel`, `FactionBaseGenerator`}（後三者 = RimCities 與 Empire 的相容）。

---

## 2. 抵達後的行為鏈

### 2.1 行軍主迴圈：`WarObject.TickInterval`（`:14586`）

```
TickInterval (:14586)
├─ PointDamage 緩慢自癒+耗損（每1001t，:14594-14599）
├─ EffectivePoints ≤ 0 → 直接 ArrivalAction()（解散，:14600）
├─ 每 NextSearchTick（Rand 180~300t，:14280；排程 :14606）
│   ├─ ValidateParentSettlement (:14609 → :14976)
│   ├─ ScanAction(ScanRange) (:14610 → :14701)        ← 途中遭遇
│   └─ Notify_Player (:14613-14621)                    ← 接近玩家/附庸的警告信
├─ 每 251t → ValidateTargets (:14623 → :14762)         ← 目標失效重導
└─ 每 NextMoveTick（settingsRef.woEventFrequency，:14258）
    ├─ pather.PatherTick + tweener (:14632-14633)
    ├─ DestinationReached（Tile == pather.Destination，:14530）
    │   └─ ValidateParentSettlement → try ArrivalAction()（:14634-14646，NRE 則自毀）
    ├─ 目標還在但移動了 → PathToTargetTile(新tile)（:14647-14656，追擊移動目標）
    ├─ DestinationTarget == null → canReachDestination=false、StopDead（:14657-14661）
    └─ !canReachDestination → 重找母聚落；離家 >250 tile 自毀；
        否則 DestinationTarget=ParentSettlement、PathToTarget（:14663-14677）
```

- `DestinationTarget` getter 在目標 `Destroyed` 時自動歸 null（`:14347`–`:14356`）→ 下一個 move tick 觸發上面的「回家」分支。**這就是「目的地消失」的重導邏輯**。
- `ValidateTargets`（`:14762`）：DestinationTarget 為 null 且非 tile 模式 → 改派回母聚落；母聚落也沒了 → `ReAssignParentSettlement`（`:15011`）→ `FindParentSettlement`（`:14989`，用 `GetClosestSettlementInRWDTo`；全派系無聚落 → **自毀**，`:15001`–`:15008`）。
- `FindHostileSettlement`（`:15019`）：以 `GetHostileSettlementsInRange(tile, 25)` 隨機挑一個敵對聚落改派（少數流程用，如戰場潰退）。

### 2.2 途中遭遇：`ScanAction`（`:14701`）

base 版只對三類出手（**聚落不在其中**）：
- `Caravan` →（若非玩家追擊對象）`EngageNearbyCaravan`；
- `RimWarSite/BattleSite` → `InteractWithSite`（`:14794`，併入戰場）；
- `WarObject` → `EngageNearbyWarObject`。

| 子類 | EngageNearbyWarObject | EngageNearbyCaravan | ScanRange |
|---|---|---|---|
| Warband | `:13374` → 敵對則 `ResolveRimWarBattle` | `:13357` → `DoCaravanAttackWithPoints` | 1（base `:14294`） |
| Scout | `:11850` → 同上；另有 **`ScanAction` override `:11781`**：途中可改鎖更近的玩家 caravan / 友軍 BattleSite / 較弱敵 WarObject | `:11829` | 1 |
| Trader | `:12095` → 遇友方 Trader 互市 `ResolveRimWarTrade :10350` | `:12076` | **1.6**（`:12058`） |
| Settler | （base 空） | `:12471` | 1 |
| Diplomat | （base 空） | （和談 `DoPeaceTalks_Caravan`） | 1 |

### 2.3 抵達分支：各 `ArrivalAction`

**Warband.ArrivalAction（`:13382`）——主鏈**：

```
DestinationTarget != null？
├─ 目標派系 ≠ 自己
│   ├─ HostileTo？
│   │   ├─ 玩家 Settlement → DoRaidWithPoints（:13414/:13418；launched 且允許空投 → Edge/Center/RandomDrop :13403-13413）
│   │   ├─ 玩家 Caravan   → DoCaravanAttackWithPoints（:13427）
│   │   ├─ NPC Settlement → comp != null → ResolveWarObjectAttackOnSettlement（:13443）
│   │   │                    comp == null → 什麼都不做 → 落到 :13496 base.ArrivalAction() 解散 ★
│   │   └─ WarObject      → ResolveWorldEngagement（:13449 → :10237）
│   └─ 非敵對且是玩家聚落 → Warmonger/Aggressive 機率倒戈開打，否則 DoReinforcementWithPoints（:13452-13476）
└─ 目標派系 == 自己（回家/增援）→ 點數回灌母聚落 RimWarPoints += points/2（:13481-13524）
最後 base.ArrivalAction()（:13496 → :14843 ImmediateDestroy）；
若以上都不成立 → 重找母聚落並改派回家（:13525-13528）
```

**其餘子類**：
- **Scout `:11863`**：同構——玩家聚落 raid（`:11882`）/ caravan 攻擊（`:11891`）；NPC 聚落 `ResolveWarObjectAttackOnSettlement`（`:11909`）；WarObject `ResolveWorldEngagement`（`:11915`）；BattleSite 併入（`:11920`）；非敵對 → 點數捐給該聚落（`:11938`）。
- **Trader `:12109`**：敵對玩家→raid（`:12130`）；敵對 NPC 聚落→**也會攻擊**（`:12145`）；友好玩家→開交易對話（`:12160` 起，含 delay/refuse 閉包）；友好 NPC→`ResolveSettlementTrade`（`:12256`→`:10401`）；自家→回灌點數（`:12271`–`:12297`）。
- **Settler `:12500`**：抵達 tile 後看同 tile 物件——敵對玩家→raid（`:12534`）/敵 WarObject→`ResolveRimWarBattle`（`:12543`）/有人佔了→回頭（`:12547`）；**tile 乾淨 → `WorldUtility.CreateSettlement`（`:12574`→`:15248`）建新聚落**。
- **Diplomat `:12803`**：敵對玩家→和談 caravan（`:12828`）；敵對 NPC 聚落→**送點數＋雙向 goodwill +4**（`:12836`–`:12838`）；回家→點數回灌（`:12848`–`:12861`）。
- **LaunchedWarband `:13201`**（基底 `LaunchedWarObject :12865`，直線飛行 `traveledPct`）：落地即 `CreateWarband(..., _launched:true)`（目標還在 `:13209`，否則飛回母聚落 `:13213`）→ `CreateWarband` 裡 `_launched` 為真時**立刻呼叫 `warband.ArrivalAction()`**（`:15495`–`:15498`）→ 等同空降即開打。

### 2.4 聚落攻擊的結算鏈（AI vs AI）

```
ResolveWarObjectAttackOnSettlement (:10340)
  └─ ValidateRimWarAction (:10852，僅判 null/Destroyed)
      → defender.AttackingUnits.Add(attacker)；nextCombatTick = now+2500 (:10345-10346)

RimWarSettlementComp.CompTick (:9585)
  ├─ 閘：RWD!=Player 且 nextCombatTick 到期（:9587），週期 2500（:9591）
  ├─ 聚落無玩家地圖 → 對每個 AttackingUnit：ResolveCombat_Settlement(this, attacker)（:9603）
  └─ 有地圖（玩家正在打）→ UpdateUnitCombatStatus（:9608，用地圖傷兵換算 PointDamage）

ResolveCombat_Settlement (:11018)
  ├─ pointClamp 檔位 200/500/2000/4000（:11020-11032）
  ├─ 雙方擲 Rand×EffectivePoints×combatAttribute，互加 PointDamage（:11078-11079）
  └─ 任一方 EffectivePoints ≤ 0 → ResolveBattle_Settlement (:11082 → :11086)

ResolveBattle_Settlement (:11086)
  ├─ 攻方存活：擲 num（Expansionist×1.1 :11136 / Warmonger×1.5 :11143）
  │   ├─ num>0.5 且【雙方皆非 Vassal】且 EffectivePoints≥pointClamp（:11148-11151）
  │   │   → "captured"（:11155）→ ConvertSettlement（:11168 → :15289）★易主
  │   └─ 否則 "defeated"：守方守住，攻方殘部以 CreateWarObjectOfType 折返母聚落（:11165/:11209）
  └─ 攻方潰滅 → 守方 PointDamage 結算（:11211-:11256）
```

途中對撞（同 tile 多單位）走 `ResolveRimWarBattle`（`:10274`）：同 tile 有玩家聚落→全員 `DoRaidWithPoints`（`:10314`）；有 NPC 聚落→併入 `AttackingUnits`（`:10319`）；無聚落→`CreateNewBattleSite`（`:10325`→`:10941`，BattleSite 自身每 2500t 用 `ResolveCombat_Units` 結算，`:8768`–`:8791`）。

### 2.5 `AdjustCaravanTargets`（`:17235`）的澄清

`caravanTargetData` 記錄的是「**玩家 caravan → 它要追的 WarObject**」（由 Harmony patch `Pather_StartPath_WarObjects :6410` 在玩家選了 `CaravanArrivalAction_AttackWarObject/EngageWarObject` 時 `AssignCaravanTargets :17267` 登記）。每 60 tick：目標不可互動→移除（`:17251`）；目標移動→重新 `StartPath` 追上去（`:17256`–`:17258`）。**與 AI WarObject 的改派無關**——AI 的改派全在 §2.1 的 TickInterval/ValidateTargets。

---

## 3. 設計問題 A：讓 warband 打非白名單的 `NpcOutpost : Settlement`

### 3.1 三個候選接點的評估

**(a) postfix `IsValidSettlement` 放行** —— 影響的是 §1.4 的 4 個呼叫點，全部是「**聚落註冊/行動源**」語意：

| 連帶效果 | 機制 | 要不要？ |
|---|---|---|
| 哨站計入派系 `WorldSettlements` | `:1283` | → 派系滅亡判定改變：`RemoveRWDFaction` 在 `WorldSettlements.Count<=0` 才觸發（`:15303`）——哨站會「吊命」 |
| 哨站開始吃成長 | `IncrementSettlementGrowth :17567` 迭代 `WorldSettlements`（`:17589`） | 哨站點數會自己長 |
| 哨站成為行動源 | `:17098` 抽中後會從哨站派出 warband/trader…（`:17144`） | NPC 哨站主動出兵——可能正是你要的，也可能不是 |
| 計入 `maxFactionSettlements`、`PointsFromSettlements`、`GetClosestSettlementInRWDTo` | `:1294`/`:1333`/`:16259` | 戰力統計與「IsAtWar 增援目標」都會含哨站 |

**但注意：放行 `IsValidSettlement` 對「被選為攻擊目標」毫無作用**——目標查詢根本不查它。

**(b) 行軍/抵達路徑攔截** —— 每 `NextSearchTick`（180~300t）檢查鄰近的是 `ScanAction`（`:14701`），但它**不處理 Settlement**；聚落交戰只在 `ArrivalAction`。可 patch 的點：
- postfix `WarObject.ScanAction` → 自行偵測 1~2 tile 內的 NpcOutpost、改寫 `DestinationTarget`（達成「順路打」）；
- prefix/postfix `Warband.ArrivalAction`（`:13382`）→ 在 `comp == null` 的靜默解散分支（★ `:13434` 判 null 後落到 `:13496`）前接手哨站結算。

**(c) patch 目標查詢函式注入候選** —— 其實**不需要**：`GetRimWorldSettlementsInRange`（`:16154`）只查 `is Settlement`，NpcOutpost 天生就在候選裡；卡住它的只有 `NearbyHostileSettlements` 的 **`comp != null && RimWarPoints > 0`**（`:9411`）。

### 3.2 推薦方案（最小侵入）

1. **第一步（零 C#）：XML `PatchOperationAdd` 把 `WorldObjectCompProperties_RimWarSettlement` 注入 NpcOutpost 的 WorldObjectDef**（仿 `Patches/RimWarCompsx.xml`，extension_points A 類第 3 條）。效果：
   - 哨站立即通過 `NearbyHostileSettlements` 過濾（`:9411`）→ **被 warband / launched warband 自然選為目標**；
   - `CalculateWarbandPointsForRaid`（`:15871`）讀 comp points 算兵力，null-safe 但有 comp 才有意義；
   - 抵達後 `ResolveWarObjectAttackOnSettlement → ResolveCombat_Settlement` 整條抽象戰鏈直接可用；
   - comp 初始 points 需自行設（哨站不走 `CreateRimWarSettlement :15191` 初始化，因為它不在 IsValidSettlement 白名單→不會被 `UpdateFactionSettlements :17824` 補登；可由 npc-outposts mod 生成時直接寫 `comp.RimWarPoints`，public setter）。
2. **第二步（一個小 patch）：prefix `WorldUtility.ConvertSettlement`（`:15289`）攔截 def == NpcOutpost** 的易主：
   - 原版易主會 `Destroy` 後用 `SettlementUtility.AddNewHome`（`:9044`）重建——而 AddNewHome **除 RimCities 外一律忽略 def**（`:9053`–`:9061`），哨站被佔後會「升格」成 vanilla Settlement，多半不是想要的；
   - prefix 改成「抹除」（直接摧毀）或「掠奪」（換 faction、扣點數）並 `return false` skip 原方法。`public static`，乾淨可攔。
3. **不建議** postfix `IsValidSettlement` 全面放行，除非你明確要哨站「算派系資產＋會成長＋會出兵」；若只要其中一部分（如只成長），用 `IncrementSettlementGrowth` postfix 另行加點（見 `_mod_ideas/.../03_rimwar_warband_territories_integration.md` §3.3）更可控。
4. 「專程打」的加強（可選）：postfix `AttemptWarbandActionAgainstTown_UnThreaded`（`:17984`）或干脆自己呼叫 `WorldUtility.CreateWarband`（public static）指定哨站為 destination——extension_points B 類已確認 Create* 可直接外呼，這是最乾淨的「程式化派兵」。

---

## 4. 設計問題 B：Empire 附庸（WorldSettlementFC）會不會被選為目標

### 4.1 RimWar v1.6 對 Empire（FactionColonies）的原生支援

| 機制 | 行 | 內容 |
|---|---|---|
| def 白名單已含 `FactionBaseGenerator` | `:16690` | Empire 附庸聚落的 WorldObjectDef 即此名 → **Empire 的 IsValidSettlement postfix 在 v1.6 很可能已是冗餘**（待實機驗證 def 名）；comp 注入也已在 `Patches/RimWarCompsx.xml` 內建 |
| `ModCheck.Empire.EmpireFaction_ColonyCheck` | `:19148`（`EmpireIsActive :19174`） | tile 上有 def `Colony` 即視為 Empire 殖民地 |
| 附庸派系判定 `IsVassalFaction` | `:16739` | **`faction.def.defName == "PColony"`**（Empire 的玩家附庸派系 def） |
| 附庸 behavior 指派 | `:17781`–`:17793`（debug 複本 `:5425`） | PColony → `RimWarBehavior.Vassal`，不建聚落、不恨玩家 |
| 附庸不主動行動 | `:17107` | 事件迴圈排除 Player 與 Vassal → 附庸聚落永遠不出兵（軍援走 gizmo/通訊台） |
| 附庸點數箝制 | `:9258`–`:9261` | Vassal 或 Empire colony tile 的 RimWarPoints clamp 100–10000 |

### 4.2 哪些目標查詢路徑會把附庸列為候選

只要 **PColony 與 NPC 派系互為敵對**，附庸聚落會出現在：
- `NearbyHostileSettlements`（`:9411`，warband/launched 預設路徑）——comp 已由 XML patch 注入，points>0 成立；
- `UpdateRWDSettlementLists → rwd.HostileSettlements`（`:16142`，forceRandomObject 路徑）；
- Scout 的 `GetWorldObjectsInRange` 路徑（`:18486`＋`:18492` 的 `HostileTo`）；
- `GetHostileSettlementsInRange`（`:16299`，FindHostileSettlement 用）。

但要實際成案還得過 **vassal 專屬閘**：`rwsComp.PlayerHeat ≥ 目標comp.vassalHeat`（warband `:18027`、launched `:18232`、scout `:18497`；threaded 版 `:17935`/`:18142`/`:18402`）。打過一次後 `vassalHeat += 2×GetHeatForAction`（`:18055`/`:18186`/`:18260`/`:18348`/`:18579`）→ 同一附庸被連打的頻率遞減。玩家會收到警告信（scout `Notify_Player :11742` 的 `vassalNotification`；warband `:13318` 僅對玩家本體）。

**結論：會。** warband/launched warband/scout 三條軍事路徑都會把附庸聚落當合法攻擊目標（視熱度節流），抵達後走 `ResolveWarObjectAttackOnSettlement → ResolveCombat_Settlement` 抽象戰、正常損血。

### 4.3 敵對怎麼成立（PColony × NPC 派系）

- 所有敵我判定統一用 **`FactionUtility.HostileTo(a, b)`**（即 vanilla `Faction.HostileTo`，看 FactionRelation goodwill/kind）——`:9411`、`:16142`、`:16299`、`:18492`、交戰側 `:13376`、`:10243` 全同源。
- 關係從哪來：PColony 是 Empire 動態生成的派系；RimWar 的 `ValidateFactions`（`:16581`）發現缺 relations 的派系會用 `CreateFactionRelation`（`:16660`）補建，**baseGoodwill = Rand.Range(-100,100)**（`:16676`）——若 Empire 自己沒鋪好關係，敵對與否近乎擲骰。
- 之後的動態：`DoGlobalRWDAction`（`:17310`）每 60000t 隨機調 goodwill；`RimWarFactionUtility.DeclareWarOn`（`:468`）/同盟連鎖（`:501`/`:520`）；playerVS 模式把全世界對玩家 -80（`:17444`，並對玩家宣戰 `:17459`）。PColony 通常繼承「對玩家敵對的派系也會敵對附庸」的 vanilla 行為（Empire 端設定）。
- **empire-warfare 設計要點**：附庸被打贏也**不會被佔領**——`ResolveBattle_Settlement` 的 captured 條件排除任一方為 Vassal（`:11151`），只會被打殘（PointDamage 累積、points 被箝在 10000 內）。要做「附庸淪陷」必須自己 patch `ResolveBattle_Settlement`（`:11086`）或在 postfix 裡讀 `AttackingUnits`/`PointDamage` 自行判定淪陷並呼叫 Empire 的接管邏輯。

---

## 5. 戰績訊號盤點（供「戰局動態增減」掛 postfix / 讀狀態）

| 訊號 | 方法 / 狀態 | 行 | 可掛性與備註 |
|---|---|---|---|
| 單位 vs 單位開戰路由 | `IncidentUtility.ResolveRimWarBattle` | `:10274` | `public static`；進場即知道交戰雙方與同 tile 聚落歸屬 |
| 聚落被圍攻（開始） | `ResolveWarObjectAttackOnSettlement` | `:10340` | postfix 可拿 attacker/defender comp；或直接讀 `RimWarSettlementComp.AttackingUnits` + `nextCombatTick`（`:9088`） |
| 聚落抽象戰回合 | `ResolveCombat_Settlement` | `:11018` | 每 2500t 一回合；postfix 讀雙方 `PointDamage` 變化 |
| 聚落戰勝負（含佔領）| `ResolveBattle_Settlement` | `:11086` | **最關鍵**：captured 分支 `:11148`–`:11168`；defeated 分支殘部折返 `:11165`/`:11209`；Vassal 不可佔領 `:11151` |
| 單位戰回合/勝負 | `ResolveCombat_Units` / `ResolveBattle_Units` | `:11271` / `:11331` | BattleSite 每 2500t 結算（`:8768`–`:8791`） |
| 商隊互市/聚落貿易 | `ResolveRimWarTrade` / `ResolveSettlementTrade` | `:10350` / `:10401` | 點數轉移＋goodwill ±，可作經濟訊號 |
| 對玩家真實襲擊 | `DoRaidWithPoints` | `:10471` | postfix 知道「多少 points 的襲擊打到哪個玩家聚落」；友軍版 `DoReinforcementWithPoints :10544`；商隊遇襲 `DoCaravanAttackWithPoints :10607` |
| **聚落易主** | `WorldUtility.ConvertSettlement` | `:15289` | `public static`；prefix 可改寫/skip，postfix 可記「誰丟了哪、誰拿了哪、轉移多少點」 |
| **派系滅亡** | `WorldUtility.RemoveRWDFaction` | `:15310` | 清掉該派系全部世界物件＋RimWarData；由 ConvertSettlement 在 `defeated || WorldSettlements<=0` 時觸發（`:15303`） |
| 新聚落誕生（佔領/移民） | `CreateRimWarSettlementWithPoints` / `CreateSettlement` | `:15221` / `:15248` | 佔領重建與 settler 建城都經過這裡 |
| 勝利條件 | `CheckVictoryFactionForDefeat` → `AnnounceVictory` | `:17478` / `:17500` | victoryFaction 聚落數歸零即觸發 |
| 宣戰/結盟 | `RimWarFactionUtility.DeclareWarOn`（含同盟連鎖） | `:468`（`:501`/`:520`） | 讀 `RimWarData.WarFactions :1462` / `AllianceFactions :1484` / `IsAtWar :1506` |
| 傷害狀態（可讀寫） | 聚落 `PointDamage :9216` / `EffectivePoints :9276`；單位 `:14391`/`:14403` | — | 聚落回血優先於成長（`:17616`）；單位每 1001t 自然衰減（`:14594`） |
| 事件流（已聚合） | `RW_LetterMaker.Archive_RWLetter` | `:7851` | 所有戰鬥/貿易/佔領事件都會 Archive 一封 RW_Letter——postfix 此一點即可拿到**全事件流**（含 label/text/relatedFaction/lookTargets），是最省事的「戰局訊號匯流排」 |

> 待驗證：Empire 附庸聚落 def 是否確為 `FactionBaseGenerator`（§4.1）；threaded 模式下 Attempt*OffMainThread 的查詢與 OnMainThread 生成之間的時差是否造成候選失效（純讀碼無法確認）；`Rand` 在背景緒呼叫的安全性。
