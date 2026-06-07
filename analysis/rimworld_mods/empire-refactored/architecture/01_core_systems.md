# Empire Refactored 核心系統（01_core_systems）

> 路徑相對 `<root>/1.6/Source/Core/FactionColonies/`。行號為實檔行號。

## 0. 入口與生命週期

| 階段 | 程式碼位置 | 說明 |
|---|---|---|
| Mod 載入 | `FactionColonies.cs:811`（`FactionColoniesMod : Mod`） | 載 `FCSettings`、印版本；設定 UI 走 `DoSettingsWindowContents`（`:835`） |
| Harmony 啟動 | `HarmonyPatches/HarmonyPatcher.cs:11`（`[StaticConstructorOnStartup]`） | `new Harmony("com.Matathias.Empire").PatchAll()`；含 Linux harmony 崩潰修補 `FixLinuxHarmonyCrash`（`:31`） |
| 帝國狀態建立 | `FactionFC.cs:250`（`FactionFC(World)`） | 唯一 `WorldComponent`，遊戲存檔內自動建立 |
| 載入完成 | `FactionFC.cs:409`（`FinalizeInit`） | 清空 null 聚落、重建 filter、註冊 LifecycleRegistry |
| **主迴圈** | `FactionFC.cs:596`（`WorldComponentTick`） | 見下 |

`WorldComponentTick`（`FactionFC.cs:596`）的分層排程：
- 每 tick：`FireSupportTick()`（`:609`）、`TickActions()`（`:613`，分派給 interface/registry）。
- 每 250 tick（rare）：`FCEventMaker.ProcessEvents()`、`BillUtility.ProcessBills()`、敕令啟用檢查、`roadBuilder.RoadTick()`（`:617-625`）。
- 每小時：傭兵治療 `TickMercenaryHealing`（`:628`）。
- 每日：校驗派遣清單、領袖補位、`StatTick()`（`:634-644`）。
- 變動週期（各自 tick guard）：`TaxTick`（`:647`）、`MilitaryTick`（`:648`）、`threatAdaptation.Tick()`（`:649`）。

## 1. 帝國資料模型（持久化）

**單一真相＝`FactionFC : WorldComponent, ILifecycleParticipant`（`FactionFC.cs:12`）**，隨存檔序列化（`ExposeData`，`FactionFC.cs:278`）。它持有整個帝國的狀態：

| 欄位 | 行號 | 內容 |
|---|---|---|
| `settlements` | `:81` | `List<WorldSettlementFC>`——所有聚落（**以 `LookMode.Reference` 序列化**，`:310`；聚落本身是 WorldObject，由 `Find.WorldObjects` 持有真身） |
| `policies` / `factionTraits` | `:156-157` | 敕令與派系特性（`FCPolicy`） |
| `events`（→ `eventManager`） | `:183-188` | 事件清單 |
| `Bills` / `OldBills` | `:192-193` | 待結算稅單 |
| `resourcePools` / `factionResources` | `:197-200` | 派系級資源池（如電力/研究） |
| `capitalLocation` / `TaxMap` | `:32-75` | 首都與「稅金落地的本地地圖」 |
| `name`/`title`/`factionColor…` | `:17-23` | 可自訂派系名稱/頭銜/顏色 |
| 計時 `taxTimeDue`/`militaryTimeDue` | `:84-87` | 稅/軍事到期 tick |

**每個聚落＝`WorldSettlementFC : Settlement`（`Worldobjects/WorldSettlementFC.cs:19`）**，本身是世界地圖 WorldObject，獨立 `ExposeData`（`:481`）。關鍵欄位：
- 四維狀態：`unrest`/`loyalty`/`happiness`/`prosperity`（`:78-94`）。
- `settlementLevel`（`:41`）、升級狀態 `isUpgrading`/`startUpgradeTick`/`finishUpgradeTick`（`:125-127`）。
- `settlementDef => def as WorldSettlementDef`（`:280`）——聚落「類型」由 def 決定。
- 收益快取 `totalIncome`/`totalUpkeep`/`totalProfit`（`:132-140`，lazy cache）。
- 資源 `Resources => resources`（`:153`）、稅金物品 `tithe`（`:119`）、囚犯 `prisonerList`（`:116`）。
- 升級邏輯：`UpgradeSettlement`（`:696`）。

> 模型要點：帝國「多據點」不是塞進一個自訂清單序列化欄位，而是**每個據點都是一個正規 RimWorld WorldObject**（可在世界地圖上看到、有 Map），`FactionFC.settlements` 只是 by-reference 索引。

## 2. 聚落建立（Found a settlement）

入口 `ColonyUtil.CreateSettlement`（`Util/ColonyUtil.cs:30`）：
1. `WorldObjectMaker.MakeWorldObject(DefDatabase<WorldSettlementDef>.GetNamed(...))` 依「聚落類型 def」造物件（`:30`）。
2. `settlement.PostPostMake(tile)` → `SetFaction` → `Find.WorldObjects.Add`（`:31-34`）。
3. `worldcomp.AddSettlement(settlement)`（`:36`）登記進帝國。
4. `settlementType.GetSettlementTypeExtension().PostCreation(settlement)`（`:40`）——**型別專屬後處理走 DefModExtension**。
5. `LifecycleRegistry.InvokeOnSettlementCreated(settlement)`（`:42`）——**通知所有生命週期參與者**。

費用由 `SettlementTypeExtension.GetFoundingCost`（`Defs/ModExtensions/Settlements/SettlementTypeExtension.cs:186-190`）計算：基礎 `FCSettings.silverToCreateSettlement` + 每既有聚落 500。UI 在 `Windows/CreateColonyWindowFC.cs`。

## 3. 徵稅 / 資源系統

排程：`TaxTick`（`FactionFC.cs:651`）在 `Find.TickManager.TicksGame >= taxTimeDue` 時呼叫 `AddTax()`，再把 `taxTimeDue += FCSettings.timeBetweenTaxes`（`:656-657`）。

`AddTax()`（`FactionFC.cs:1635`）流程：
1. `TaxTickRegistry.InvokePreTaxResolution(this)`（`:1637`）——擴充前置鉤。
2. 重置「每稅期歸零」的資源池（`:1638-1644`）。
3. 對每個聚落：`settlement.CreateTax(out int silver)`（實物稅，`WorldSettlementFC.cs`，見 `CreateTax`/`CreateResourcePools:1803`）+ `CreateResourcePools()` → 包成 `BillFC`（稅單）加入 `Bills`（`:1650-1664`）；並 `ForEachBehavior(b => b.OnTaxCollected(...))`（敕令行為鉤，`:1666`）。
4. 發信件 `FCTaxesBilledShort`（`:1672`）。
5. 扣敕令維護費 `GetEdictUpkeep`（`:1679-1694`）；付不起則 `RevokeAllEdicts`。
6. `TaxTickRegistry.InvokePostTaxResolution(this)`（`:1696`）——擴充後置鉤。

稅單最終由 `PaymentUtil.AutoresolveBills`（`TaxTick:660`，啟用 autoResolve 時）或玩家手動結算，物品送到 `TaxMap`（`FactionFC.cs:36`）。

**資源「類型」由 `ResourceTypeDef : Def`（`Defs/ResourceTypeDef/ResourceTypeDef.cs:11`）定義**（純資料）：含 `isDefaultResource`（`:64`，自動加進 `defaultResources=true` 的聚落）、`canTithe`（`:69`）、`isPoolResource`（`:60`，如電力/研究不可繳稅）、tech/research 限制（`:38-55`）、`productionAdditiveStat`/`productionMultiplierStat`（`:86-91`，產量綁 `FCStatDef`）、tithe 數量參數（`:97-107`）。產量/過濾的進階行為走 `ResourceProductionExtension` / `ResourceFilterExtension`（`Defs/ModExtensions/Resources/`）DefModExtension。

## 4. 敕令（Edicts / Policies）

README 的新機制：舊 policy 重做成 **Social / Tax / Military 三類敕令**，各隨派系等級解鎖、提供全派系增益/減益。

- def：`FCPolicyDef : Def`（`Defs/FCPolicyDef.cs:10`）——純資料：`category`、`techLevelRequirement`/`factionLevelRequirement`、`statModifiers`（`FCStatModifier`）、`blockedActions`/`enabledActions`、`blockedMilitaryJobs`/`enabledMilitaryJobs`、`upkeepSilver`（維護費）。
- 行為：`FCPolicyBehavior`（`Settlements/FCPolicyBehavior.cs`）+ 13 個具體子類（`Settlements/Behaviors/FCPolicyBehavior_*.cs`，如 Authoritarian/Egalitarian/Militaristic/Pacifist…），透過 DefModExtension `FCPolicyBehaviorExtension`（`Defs/ModExtensions/Policies/`）掛行為。`AddTax` 對每個敕令呼叫 `OnTaxCollected` 等鉤（`FactionFC.cs:1666`）。

## 5. 事件系統

- def：`FCEventDef : Def`（`Defs/FCEventDef.cs:7`）——純資料：觸發時間/權重、影響聚落數 `rangeSettlementsAffected`、四維狀態門檻（happiness/loyalty/unrest/prosperity 的 min/max）、`requiredResource`/`requiredResearch`/`minTechLevel`。
- 處理：`FCEventMaker.ProcessEvents()`（每 250 tick，`FactionFC.cs:619`），`MakeRandomEvent()`（每日 `StatTick`，`FactionFC.cs:675`）。事件處理器可走 DefModExtension `FCEventHandlerExtension`（`Defs/ModExtensions/FCEventHandlerExtension.cs`）。README：「Adding new events or policies is possible through XML, too!」

## 6. 派遣 / 軍事系統

- 每聚落掛 `WorldObjectComp_SettlementMilitary : WorldObjectComp, ISettlementPostLoadInit`（`Comps/SettlementMilitary.cs:32`）——負責派遣 squad、`CaravanDefend`（`:439`）防守。
- 軍事資料在 `Military/`（23 檔）：`MilitaryForce`（戰力）、`MercenarySquadFC`/`MilSquadFC`/`MilUnitFC`（傭兵編成）、`SimulateBattleFC`（自動結算戰鬥）、`MilitaryFireSupport`（砲擊支援，`FireSupportTick`）、`EmpireThreatAdaptation`/`ThreatScalingUtil`（敵方威脅縮放）。
- 軍事工作類型＝`MilitaryJobDef`（`Defs/MilitaryJobDef.cs`，XML 定義）+ handler `MilitaryJobHandler_{Raid,Capture,Enslave}`（`Military/`）。
- 排程：`MilitaryTick`（`FactionFC.cs:678`），敵方主動軍事行動受 `FCSettings.disableHostileMilitaryActions` 與「開局一季保護期」控管（`:682-684`）。
- README 的「Manual Battles」＝玩家可上本地地圖手動打（標記為歷史上脆弱的功能，`supportsManualBattle` 在 `WorldSettlementDef`，見 Settlements.xml）。

## 7. 升級系統

- 聚落升級：`WorldSettlementFC.UpgradeSettlement`（`:696`），費用/耗時由 `SettlementTypeExtension.GetUpgradeCost`/`GetUpgradeTime`（`WorldSettlementFC.cs:53-60` 轉呼 extension）決定，等級上限受 `WorldSettlementDef.maxSettlementLevel` 與 `FCSettings.settlementMaxLevel` 雙重夾限（`:43-45`）。
- 建築：`BuildingFCDef : Def`（`Defs/BuildingFCDef.cs:20`）有 `upgrades`（升級樹，`:43`）、`requiredBuildings`（前置依賴，`:47`）、`settlementTypeAllowList`/`BlockList`（`:30-31`）、biome/hilliness/tileMutator 限制。每聚落的建築槽由 `WorldObjectComp_SettlementBuildings`（`Comps/SettlementBuildings.cs`）管理，槽數 = `SettlementTypeExtension.GetBuildingSlots`（`WorldSettlementFC.cs:49`）。

## 8. 道路系統（重構新增）

README：以 **Minimum Spanning Tree** 取代舊「蛛網式」道路。實作在 `Settlements/Roads/`，由 `roadBuilder.RoadTick()`（`FactionFC.cs:624`）驅動，`FlagUpdateRoadQueues`（`ColonyUtil.cs:37`）在聚落變動時觸發重算。

---
帝國資料模型一句話：**`FactionFC` 這個唯一 `WorldComponent` 是帝國真相，持 `List<WorldSettlementFC>`（每聚落本身是正規 WorldObject by-reference），其餘狀態（敕令/事件/稅單/資源池）皆掛在 `FactionFC` 上隨存檔序列化。**
