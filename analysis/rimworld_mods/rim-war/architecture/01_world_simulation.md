# Rim War 世界戰爭模擬迴圈（01_world_simulation）

> 完整迴圈：派系決策 → 生成戰爭物件 → 行軍 → 交戰 → 聚落易主。所有行號指 `projects/rimworld_mods/rim-war/decompiled/RimWar.decompiled.cs`。設定值來自玩家滑桿（`SettingsRef` 快照），非 Def。

## 0. 驅動器：`WorldComponent_PowerTracker.WorldComponentTick`（`:17030`）

唯一的世界級心跳。每 tick 依不同週期觸發（`new SettingsRef()` 每 tick 重抓設定快照，`:17035`）：

| 條件 | 動作 | 行 |
|---|---|---|
| `ticksGame >= 10 && !rwdInitialized` | `Initialize()`：為每個可見派系建 `RimWarData`、指派聚落、套用 playerVS | `:17045` / `:17411` |
| `% 60` | `AdjustCaravanTargets()`：重導行軍中 caravan 的目標 | `:17051` / `:17235` |
| `% heatFrequency` | `UpdatePlayerAggression()`：玩家威脅熱度每次 -1~2 衰減 | `:17055` / `:17555` |
| `% rwdUpdateFrequency` | `CheckForNewFactions()` + `UpdateFactions()`（聚落成長）+ 勝利檢查；**threadingEnabled 時丟 `tasker` 背景執行緒** | `:17059` / `:17560` |
| `% 60000` | `DoGlobalRWDAction()`：全域加分/外交好感調整 | `:17085` / `:17310` |
| `>= nextEvaluationTick`（隨機 0.5~1.5×averageEventFrequency） | **核心：隨機挑一派系一聚落產生一個 RimWarAction** | `:17089` |

`nextEvaluationTick = ticksGame + Rand.Range(0.5×, 1.5× averageEventFrequency)`（`:17091`）。

## 1. 派系決策（哪個聚落、做什麼）

事件評估段（`:17092`–`:17204`）流程：
1. 從 `Active_RWD`（排除 `Excluded` 行為的派系，`:16987`）隨機挑一個 `RimWarData`。
2. 從該派系 `WorldSettlements` 隨機挑一個聚落，取其 `RimWarSettlementComp`。
3. 條件閘：非 Player/Vassal 行為、`nextEventTick <= ticksGame`、且**晝夜符合 `movesAtNight`**（`:17107`）。
4. 呼叫 `RimWarData.GetWeightedSettlementAction()`（`:1688`）擲骰決定動作；若 `IsAtWar` 且擲到非軍事動作會重擲一次（`:17115`）。
5. 依結果分派到 `Attempt*` 方法（`:17144`–`:17185`）。

### 動作機率怎麼來（behavior → 權重）
`GenerateActionWeights`（區段 `:15980`–`:16098`）依 `behavior` 設 6 個原始權重 `num..num6`（settler/warband/scout/launchedWarband/diplomat/caravan），歸一化後寫入 `RimWarData` 的累積機率欄位：
```
settlerChance        = num / 總和
warbandChance        = (num+num2) / 總和
scoutChance          = (num+num2+num3) / 總和
warbandLaunchChance  = (...+num4) / 總和
diplomatChance       = (...+num5) / 總和
caravanChance        = (...+num6) / 總和   (:16093–16098)
```
`GetWeightedSettlementAction`（`:1688`）用一個 `Rand.Value` 對這串累積門檻做階梯比對。各 behavior 權重（節錄 `:15987+`）：

| behavior | settler | warband | scout | launch | diplomat | caravan |
|---|---|---|---|---|---|---|
| Random | 1 | 3 | 4 | 2* | 1** | 3 |
| Aggressive | 2 | 4 | 4 | 4* | 1** | 5 |
| Cautious | 2 | 2 | 4 | 3* | 2** | 5 |
| Expansionist | 3 | 3 | 3 | 1* | 2** | 4 |
| Merchant | 2 | 3 | 3 | 1* | 2** | 6 |
| Warmonger | 3 | 7 | 4 | 5* | 0 | (見碼) |

\* launchedWarband 僅 `CanLaunch`（techLevel≥4，`:1508`）才給權重。\*\* diplomat 僅 `createDiplomats` 設定開啟才給。

## 2. 生成戰爭物件（WorldObject）

`Attempt*` 方法（`WorldComponent_PowerTracker` 內）算出 points 後呼叫 `WorldUtility.Create*`：

| Action | 算 points | 生成 | 目標選擇 |
|---|---|---|---|
| Warband | `CalculateWarbandPointsForRaid`（`:15871`，目標 points×隨機 1.1~1.8，clamp 50~2e6） | `CreateWarband`（`:15467`） | 鄰近敵聚落/單位 |
| Scout | `CalculateScoutMissionPoints`（`:15900`，目標 points×0.9~1.1，Expansionist/Aggressive ×1.15） | `CreateScout`（`:15589`） | 距離 <120 tile 的玩家聚落（全域版） |
| Trader | `CalculateTraderPoints`（`:15882`，敵×0.25 / 玩家×1.0） | `CreateTrader`（`:15657`） | 友善聚落 |
| Settler | `CalculateSettlerPoints`（`:15890`，origin×0.5，clamp 300+），受 `maxFactionSettlements` 上限 | `CreateSettler`（`:15783`） | 空 tile 建新聚落 |
| Diplomat | `CalculateDiplomatPoints`（`:15895`，固定 100~200） | `CreateDiplomat`（`:15728`） | 他派系聚落 |
| LaunchedWarband | warband points×behavior 加成（Cautious×1.1 / Warmonger×1.25） | `CreateLaunchedWarband`（`:15538`） | 僅對敵對玩家、需 `CanLaunch` |

每個 `Create*` 都從來源聚落 `RimWarPoints` **扣掉**對應 points（消耗），生成的 WarObject 帶著這份 points 上路。所有 WarObject 共用 `worldObjectClass`（`RW_WorldObjects.xml`）↔ C# class 對應。

## 3. 行軍（WorldObject 移動）

- `WarObject`（`:14157`）持有 `WarObject_PathFollower`（`:13635`，自訂世界路徑跟隨，`StartPath`）與 `WarObject_Tweener`（`:13584`，平滑插值繪製）。
- `RimWarMod` 用 Harmony patch `Caravan_PathFollower.StartPath`（`:5978`）與 `WorldPathPool.GetEmptyWorldPath`（`:6053`）介入路徑系統。
- 移動中每 tick 檢查鄰近：各子類覆寫 `EngageNearbyWarObject` / `EngageNearbyCaravan`（base 空實作 `:14786`）。例：`Warband.EngageNearbyWarObject`（`:13374`）→ `ResolveRimWarBattle`。

## 4. 交戰（單位 vs 單位 / 單位 vs 聚落）

### 單位 vs 單位
`IncidentUtility.ResolveRimWarBattle(attacker, defender)`（`:10274`）：
1. 收集同 tile 所有 WorldObject，判斷是否含 Settlement（`:10285`）。
2. **無聚落** → `CreateNewBattleSite`（`:10325`）建一個可進入的 `BattleSite`（玩家可去打）。
3. **有聚落且屬玩家** → 對每個 WarObject 跑 `DoRaidWithPoints`（`:10314`），轉成原版地圖襲擊。
4. **有聚落非玩家** → 加進 `SettlementComp.AttackingUnits`、設 `nextCombatTick = +2500`（`:10319`，延後抽象結算）。

### 單位 vs 聚落（抽象戰，AI vs AI）
聚落 comp 到 `nextCombatTick` 結算（區段 `:11130`+，`RimWarSettlementComp` 內）：
- 用 `attacker.EffectivePoints` 對 `Rand.Value`（Expansionist×1.1、Warmonger×1.5）判定（`:11132`）。
- 勝（`num>0.5` 且非 Vassal 且 `EffectivePoints>=pointClamp`）→ **「captured」** → `WorldUtility.ConvertSettlement(...)`（`:11168`）。
- 敗 → 「defeated」信件，attacker 損耗 points（Warmonger×1.2 / Merchant×1.4 / Aggressive×0.8 修正，`:11176`）。
- 戰鬥用 `RW_Damages_Combat.xml` 的傷害 Def。

### 商隊 vs 商隊
`ResolveRimWarTrade`（`:10350`）：雙方 `RimWarPoints × combatAttribute × Rand` 比大小，贏家吃對方一部分 points，並調整 goodwill。

## 5. 聚落易主：`WorldUtility.ConvertSettlement`（`:15289`）

```
摧毀原 Settlement → Find.World.WorldUpdate()
→ SettlementUtility.AddNewHome(tile, 新派系, def)
→ CreateRimWarSettlementWithPoints(新派系, points= max(defender×0.2 + attacker, 0))
→ 若敗方 defeated 或無聚落 → RemoveRWDFaction (:15310)（清掉該派系所有世界物件 + RimWarData）
```
這就是「全球征服」的閉環：聚落數歸零＝派系滅亡，正是勝利條件（`CheckVictoryFactionForDefeat` `:17478`：指定 victoryFaction 無聚落時 `AnnounceVictory`）。

## 6. 聚落成長與消耗（戰力隨時間變化）

`IncrementSettlementGrowth`（`:17567`，每 `rwdUpdateFrequency`）：
- 非 Player/Excluded 派系，每聚落每週期成長：
  ```
  基礎 = Rand(2,3) + 生態圈乘數 GetBiomeMultiplier
  最終 = 基礎 × (rwdUpdateFrequency/10000) × 科技乘數 GetFactionTechLevelMultiplier
         × rwd.growthAttribute × settingsRef.settlementGrowthRate   (:17624)
  clamp 1~100，累加到 RimWarPoints
  ```
- 上限 `num2`（基礎 50000，Citadel +5000、首都 +5000，`:17597`）。
- 有 `PointDamage`（被打過的傷）時優先回血而非成長（`:17616`）。
- 同時累加 `PlayerHeat`（對玩家的敵意熱度，`:17633`）。
- behavior=Expansionist 成長 ×1.1（`:17585`）。

戰力來源彙總見 `00_overview` 與下節。

## 7. 派系戰力模型（一句話＋公式）

**一句話**：派系總戰力 = 旗下所有聚落 points + 在途所有 WarObject 單位 points + 其他世界物件 points（`RimWarData.TotalFactionPoints` `:1510`），points 隨「聚落成長」漲、隨「生成單位/被擊敗/被搶/送禮」跌。

- 三來源 getter（皆有 ~300 tick 快取）：`PointsFromSettlements`（`:1333`）、`PointsFromWarObjects`（`:1351`）、`PointsFromWorldObjects`（`:1368`）。
- 新聚落初始 points：`CalculateSettlementPoints`（`:15840`）= 基礎 100 ÷ 科技乘數 × 生態乘數 ×（City_Faction 1.15 / Abandoned 0.1 / Compromised 0.4 / Citadel 1.25），clamp 100~1000。
- 三個 per-faction 係數 `movementAttribute` / `combatAttribute` / `growthAttribute`（`:1169`）由 `RimWarDef.xml` 的 `movementBonus`/`combatBonus`/`growthBonus` 餵入（`GenerateFactionBehavior` `:17731`，比對 `factionDefname`）。

## 8. 與玩家的互動

| 機制 | 入口 | 說明 |
|---|---|---|
| 被捲入襲擊 | `ResolveRimWarBattle` → `DoRaidWithPoints`（`:10314`）；`IncidentWorker_WarObjectRaid`（`:3359`） | AI warband 抵達玩家聚落 → 轉成真實地圖襲擊 |
| 商隊到訪/勒索 | `IncidentWorker_WarObjectMeeting`（`:4129`）、`IncidentWorker_WarObjectDemand`（`:3610`） | AI trader/warband 觸發原版風格事件 |
| 通訊台請求 | `CommsConsole_RimWarOptions_Patch`（`:5876`）+ `FactionDialogReMaker`（`:2530`） | 玩家可向友方派系**請求商隊、斥候軍援、戰團軍援、空降戰團**；替換原版「Request trade/military aid」選項 |
| 外交/同盟 | `RimWarData.WarFactions`/`AllianceFactions`（`:1462`/`:1484`）；`DoGlobalRWDAction`（`:17310`）調 goodwill；`RimWarFactionUtility.DeclareWarOn` | 派系彼此宣戰/結盟，玩家含其中 |
| 送禮影響戰力 | `FactionGiftUtility.GiveGift` patch（`:6000`）+ `RimpointsPerGift=90`（`:5876` 區） | 送禮 → 對方 RimWarPoints 增加 |
| 玩家面板 | `MainTabWindow_RimWar`（`:688`） | Relations（派系戰力排名）/ Events（信件）/ Performance（圖表） |
| 勝利條件 | `useRimWarVictory` → `GetFactionForVictoryChallenge`（`:17507`）指定對手，滅其全部聚落即勝 | 新增的 winning condition |
| playerVS 模式 | `Initialize`（`:17444`）：開啟後全世界對玩家 -80 goodwill、彼此結盟 | 「全世界與你為敵」開局 |

防護：`preventActionsAgainstPlayerUntilTick`（`:16901`，預設 90000/威脅倍率）與 `minimumHeatForPlayerAction` 提供早期保護期。
