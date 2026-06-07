# Empire Refactored 擴充接點（extension_points）

> 目標：在 Empire 上 create（衍生 submod）。本文分 **A 純資料（XML）** 與 **B 改碼（C#）** 兩類列接點與風險。
> 路徑相對 `<root>`，源碼相對 `1.6/Source/Core/FactionColonies/`。

## A. 純資料接點（只寫 XML，免 C#、免 Harmony）

README 明示：「basic resources and settlements can be created in XML alone... Adding new events or policies is possible through XML, too!」

| 想新增的東西 | 寫哪個 Def | 範例檔 | 風險/限制 |
|---|---|---|---|
| **新據點類型** | `FactionColonies.WorldSettlementDef`（C# 類在 `Defs/SettlementDef.cs:13`） | `1.6/Defs/WorldObjectDefs/Settlements.xml`（含 Surface/Orbital） | 繼承 `WorldSettlementDefBase`；設 `resources`/`defaultResources`/`workersMax*`/`allowedBiomes`/`statModifiers`/`maxSettlementLevel`/`maxBuildingCount`；掛 `<modExtensions><li Class="FactionColonies.SettlementTypeExtension"/>`。**只用內建 SettlementTypeExtension 時純 XML 即可**；要改建立/驗證/升級曲線就得 B（自訂 extension 子類）。 |
| **新資源類型** | `FactionColonies.ResourceTypeDef`（`Defs/ResourceTypeDef/ResourceTypeDef.cs:11`） | `1.6/Defs/FCResourceDefs/Resources.xml` | 設 `isDefaultResource`/`canTithe`/`isPoolResource`/tech/research 限制/`productionAdditiveStat`/`titheMax*`。產量綁既有 `FCStatDef` 即純 XML；要非線性產量公式或特殊過濾需 B（`ResourceProductionExtension`/`ResourceFilterExtension` 子類）。 |
| **新據點建築** | `FactionColonies.BuildingFCDef`（`Defs/BuildingFCDef.cs:20`） | `1.6/Defs/FCBuildingDefs/*.xml`（Neolithic/Industrial/Spacer/Ultra/Orbital 分檔） | 設 `cost`/`upkeep`/`constructionDuration`/`statModifiers`/`upgrades`（升級樹）/`requiredBuildings`（前置）/`settlementTypeAllowList`/biome·hilliness·tileMutator 限制。**升級樹與依賴皆 XML 表達**，純資料。要建築有主動行為需 B（`BuildingFCExtension`）。 |
| **新事件** | `FactionColonies.FCEventDef`（`Defs/FCEventDef.cs:7`） + `FCEventCategoryDef` | `1.6/Defs/FCEventDefs/` | 設觸發權重/時間、影響聚落數、四維狀態門檻、tech/research/resource 需求。**有選項抉擇/特殊效果的事件需 B**（`FCEventHandlerExtension` 子類，`Defs/ModExtensions/FCEventHandlerExtension.cs`）。 |
| **新敕令/政策** | `FactionColonies.FCPolicyDef`（`Defs/FCPolicyDef.cs:10`） | `1.6/Defs/FCPoliciesDefs/` | 設 `category`(Social/Tax/Military)/等級·tech 需求/`statModifiers`/`blocked·enabledActions`/`blocked·enabledMilitaryJobs`/`upkeepSilver`。**純增益/減益/禁用動作 → 純 XML**；要每稅期主動行為需 B（`FCPolicyBehavior` 子類）。 |
| 生物群落產出 | `BiomeResourceDef`（`Defs/BiomeResourceDef.cs`） | `1.6/Defs/FCBiomeResourceDefs/` | 純資料，定義各 biome 的資源 additive/multiplier。 |
| 事件獎勵物品池 | `ResourceEventRewardDef`（`Defs/ResourceEventRewardDef.cs`） | `1.6/Defs/FCResourceDefs/EventRewards.xml` | 純資料，`thingCategoryAllowList`/品質/數量。 |
| 軍事工作類型 | `MilitaryJobDef`（`Defs/MilitaryJobDef.cs`） | `1.6/Defs/MilitaryJobDefs/` | 工作的數值/UI 純 XML；行為由既有 `MilitaryJobHandler_*` 處理，**全新行為需 B**。 |
| stat 定義 | `FCStatDef`（`Defs/FCStatDef.cs`） | `1.6/Defs/FCStatDefs/` | 純資料，自訂 stat 軸供建築/聚落/敕令的 `statModifiers` 引用。 |

> A 類整體風險最低：不改 DLL、不破壞存檔、不衝突 Harmony。最大限制＝**只能組合既有「行為原語」**（stat modifier、解鎖條件、升級樹）；任何「主動發生的事」都需要 B。

## B. 改碼接點（C#）— 兩條子路徑

### B-1（推薦）：實作核心介面 + 註冊 Registry / 掛 DefModExtension（**免 Harmony**）

核心 `Comps/Interfaces/FCInterfaces.cs` 提供 20+ 介面，配 `Util/Registries/`（15 個靜態註冊表）。**這是 refactored 版主打的擴充面**——submod 自己的型別實作介面、開機註冊，核心在對應時機回呼，無需 patch。

| 想做的事 | 介面（`FCInterfaces.cs`） | 註冊表 / 掛載點 | 回呼時機 |
|---|---|---|---|
| 加帝國主視窗分頁 | `IMainTabWindowOverview`（`:11`） | `MainTableRegistry.Register`（`Util/Registries/MainTableRegistry.cs:10`） | UI 開啟 |
| 加聚落視窗分頁 | `ISettlementWindowOverview`（`:23`） | 聚落 WorldObjectComp 實作 | UI 開啟 |
| 改稅務 | `ITaxTickParticipant`（`:110`） | `TaxTickRegistry.Register`（`:11`） | `AddTax` 前/後、每聚落造稅前/後（可 `ref silverAmount`） |
| 改戰鬥戰力 | `IBattleModifier`（`:149`） | `BattleModifierRegistry.Register`（`:10`） | 結算戰鬥（RimWar compat 即用此，見 02 文件） |
| 自訂建立驗證 | `ISettlementFoundingValidator`（`:187`） | `FoundingValidatorRegistry.Register`（`:14`） | 建立聚落前 + `OnSettlementFounded` |
| 攔截白銀支付 | `ISilverPaymentModifier`（`:231`） | `SilverPaymentRegistry.Register`（`:27`） | 付款前可改 context |
| 自訂掠奪目標 | `IRaidTarget`（`:261`） | `RaidTargetRegistry.Register`（`:11`） | 派遣選目標（核心 `FactionFC.cs:690-703` 已混合內建聚落 + 外部目標） |
| 威脅縮放 | `IThreatScalingContributor`（`:213`） | `ThreatScalingRegistry.Register`（`:14`） | 加/乘敵方威脅 |
| 防守驗證 / 自動防守 | `IDefenseValidator`（`:162`）/`IAutoDefender`（`:280`） | `DefenseValidatorRegistry` / `AutoDefenderRegistry` | 防守流程 |
| squad 指派驗證 | `ISquadAssignmentValidator`（`:174`） | `SquadAssignmentRegistry.Register`（`:10`） | 派遣編成 |
| 掠奪權重 | `IRaidWeightProvider`（`:245`） | `RaidWeightRegistry.Register`（`:11`） | AI 選擊打目標 |
| **生命週期全事件** | `ILifecycleParticipant`（`:128`，或繼承 `LifecycleParticipantBase` 免實作全部） | `LifecycleRegistry.Register`（`:11`） | 聚落建立/移除/升級/換型/建築建造拆除/squad 派遣召回/戰鬥結算/研究完成/傭兵死亡（15 個 Invoke，`LifecycleRegistry.cs`） |
| 聚落型別行為 | DefModExtension `SettlementTypeExtension`（`Defs/ModExtensions/Settlements/SettlementTypeExtension.cs:15`） | XML `<modExtensions>` 掛子類 | 建立/驗證/升級成本/建築槽數/PostCreation/PreDestruction |
| 資源產量/過濾 | `ResourceProductionExtension`/`ResourceFilterExtension`（`Defs/ModExtensions/Resources/`） | XML 掛子類 | 產量計算 / ThingFilter |
| 建築主動行為 | `BuildingFCExtension`（`Defs/ModExtensions/Buildings/BuildingFCExtension.cs`） | XML 掛子類 | 建築特殊效果（如 `BuildingFCExtension_Shuttles`） |
| 敕令主動行為 | `FCPolicyBehavior` + `FCPolicyBehaviorExtension`（`Settlements/FCPolicyBehavior.cs`、`Defs/ModExtensions/Policies/`） | XML 掛子類 | `OnTaxCollected` 等（`FactionFC.cs:1666`） |
| 事件選項/效果 | `FCEventHandlerExtension`（`Defs/ModExtensions/FCEventHandlerExtension.cs`） | XML 掛子類 | 事件觸發處理 |

註冊慣例：`[StaticConstructorOnStartup]` 靜態建構子內 `XxxRegistry.Register(new MyImpl())`（參 `Patch-RW/RimWarCompatInit.cs:28`）。

風險：
- Registry 全在執行期記憶體、**不序列化**——每次開機要重新註冊（靠 StaticConstructorOnStartup）。
- 註冊表多用 try/catch 包住單一參與者（如 `BattleModifierRegistry.cs:20-23`），單一 submod 拋例外不會炸全鏈，但仍要自行避免回呼內做重活。
- DefModExtension 子類的 `ResolveReferences` 必須容忍 parent 非預期型別（核心 `SettlementTypeExtension.cs:20-32` 即有 fallback）。

### B-2（最後手段）：自帶 compat DLL + Harmony patch（引用第三方 mod 時）

當要對 **第三方 mod 的型別** 互動、且核心沒提供現成接點時，照 02 文件第 3 節「風格 A/B」做：
1. `LoadFolders.xml` 加 `IfModActive` 行（`<root>/LoadFolders.xml`）。
2. 新 `Patch-MyX` 專案，`ProjectReference` Core + `Reference` 對方 DLL（HintPath，參 `Patch-VF/VehicleFrameworkCompat.csproj`）。
3. 優先：實作核心 bridge 介面（如 `ICombatExtendedBridge`）或註冊 Registry；不得已才 `new Harmony(...).PatchAll()`。

風險：直接 Harmony patch 核心或第三方 method 最易隨版本失效；patch 對方 private method 需 `Traverse`/`AccessTools`，脆弱。**能用 B-1 就別用 B-2。**

## 擴充最省力路徑（建議順序）

1. 能用 **A（純 XML def）** 達成 → 就停在 A（新據點類型/資源/建築/事件/敕令）。
2. 需要「主動行為」但只碰 Empire 自己 → **B-1**：先找對應 DefModExtension 子類（聚落/建築/資源/敕令/事件各有一條），再找對應 Registry+Interface。
3. 必須碰第三方 mod 型別 → **B-2**：新 compat DLL + LoadFolders 閘門，內部仍優先 bridge/registry。
