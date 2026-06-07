# 擴充接點：純 XML 可做 vs 必須 C#

> 焦點：玩家/modder 不寫 C# 能擴充到哪、哪些行為鎖死在編譯後的 DLL。
> 程式碼位置以核心 DLL `core.cs`（= `decompiled/WarfareAndWarbands/WarfareAndWarbands.decompiled.cs`）為準；QL = `WarbandWarfareQuestline.dll`。

## 總結二分表

| 子系統 | 純 XML 可加新項？ | 行為來源 | 說明 |
|---|---|---|---|
| **可選兵種池** | ✅（間接，最大擴充點） | `WarbandUtil.GetSoldierPawnKinds()` `core.cs:3838` | 任何 mod 新增 `isFighter && Humanlike && 非貴族` 的 `PawnKindDef` **自動**出現在 warband 編組清單。不需碰本 mod。 |
| **FactionTraitDef（派系特性）** | ✅ 完全資料驅動 | QL `FactionTraitDef` 類別 | `TraitDefs.xml` 已示範 10 條；欄位見下。純 XML 加新特性即生效。 |
| **PolicyCategoryDef（政策分類）** | ✅ | QL `PolicyCategoryDef` | `Economy`/`Warfare`，純 defName 容器，可加新分類。 |
| **PolicyDef（同盟政策）** | ⚠️ 半 | QL `PolicyDef`(+`workerClass`) | 數值欄位（taxBonus/cost/prerequisite/equipmentBudgetLimitOffset）純 XML；**特殊效果靠 `workerClass`（C# PolicyWorker_*）**，無 worker 的政策只有數值效果。 |
| **FactionDef（玩家傭兵團派系）** | ✅ | 原版 `FactionDef` | `WarbandBase`/`PlayerWarband` 純 XML；可調 backstory/meme/材質等。 |
| **SitePartDef（warband site）** | ✅ | 原版 `SitePartWorker` | `WAWEmptySite` 純 XML，可改貼圖/tags。 |
| **MapGeneratorDef（迷你聚落地圖）** | ⚠️ 半 | 原版 genSteps + QL `GenStep_MinorSettlement` | genStep 串接純 XML，但 `GenStep_MinorSettlement` 是 QL C#。 |
| **客製兵種（遊戲內）** | ✅（遊戲內 UI，非 XML） | `CustomizationUtil.GenerateDefaultKindDef` `core.cs:10982` | 玩家在遊戲中用 `Window_Customization` 即時造 `PawnKindDef`（外觀/裝備/技能/戰力），存 `GameComponent_Customization`。不需 XML 也不需重啟。 |
| **warband 物件行為**（移動/攻擊/結算/雇用/受傷/戰利品） | ❌ 鎖 C# | `Warband` `core.cs:3192` 及 manager 群 | `worldObjectClass` 指向編譯類別，邏輯全在 DLL。 |
| **warband 升級（Elite/Engineer/Outpost/Psycaster/Vehicle）** | ❌ 鎖 C# | `PlayerWarbandUpgrade` 抽象基類 `core.cs:5986` 的五個硬編子類 | **無 Def 對應**，升級不是 data-driven。新增升級必須繼承 `PlayerWarbandUpgrade` 寫 C# 並在 `PlayerWarbandUpgradeHolder` 註冊。 |
| **JobDef driver** | ❌ | `core.cs:811`/`8928` | driverClass 指向 DLL 類別。 |
| **MainButtonDef 分頁** | ❌（UI 行為） | `Window_WAW` `core.cs:855` | 按鈕本身 XML，內容是 DLL。 |
| **Harmony patch 對象** | ❌ | `WAWHarmony` `core.cs:954` | 補丁目標寫死。 |

## 可純 XML 擴充的 Def 欄位細節

### FactionTraitDef（QL 命名空間，`FactoinTraitDefs/TraitDefs.xml`）— **最乾淨的資料驅動點**
範例（已內建 `WAW_Cautious`/`Merchant`/`Aggressive`/`Strategist`/`Industrialist`/`Militarist`/`Diplomat`/`Expansionist`/`Pacifist`/`Defender`）：
```xml
<WarbandWarfareQuestline.FactionTraitDef>
    <defName>WAW_Merchant</defName>
    <label>Merchant</label>
    <commonality>2</commonality>          <!-- 該特性被抽到的權重 -->
    <supplyBonus>2</supplyBonus>          <!-- 對同盟補給/權力的加成 -->
    <description>…</description>
    <dislikedCategory>Warfare</dislikedCategory>  <!-- 厭惡的 PolicyCategoryDef -->
    <hatedTrait>WAW_Militarist</hatedTrait>        <!-- 互斥/敵對的另一特性 defName -->
</WarbandWarfareQuestline.FactionTraitDef>
```
欄位：`commonality`、`supplyBonus`、`dislikedCategory`（連動 PolicyCategoryDef）、`hatedTrait`（連動另一 trait）。新增新特性純 XML 即可，數值由 QL 引擎讀取。

### PolicyDef（QL，`Policies/PolicyDefs.xml`）
純 XML 欄位：`label`/`description`/`category`(→PolicyCategoryDef)/`cost`/`taxBonus`/`prerequisite`(前置政策 defName)/`equipmentBudgetLimitOffset`。
**效果掛勾**：`workerClass`（如 `PolicyWorker_RoadConstruction`/`TradeAgreement`/`ResourceOptimization`/`InfrastructureDevelopment`/`StartSkirmish`/`EliteForces`/`MilitaryDrills`）——若要全新效果必須寫 C# worker；只想要稅率/預算/前置鏈這類純數值政策則可省略 workerClass，純 XML。

### PolicyCategoryDef（QL）
只有 `defName`（`Economy`/`Warfare`）。純容器，可加新分類供 trait 與 policy 引用。

### 可選兵種池（不碰本 mod 的「隱性擴充」）
不必改 Warband Warfare 的任何檔案：只要任意 mod 定義一個符合 `isFighter==true && race.race.Humanlike==true && 非貴族`（`titleRequired` 無臥室需求）的 `PawnKindDef`，它就會被 `GetSoldierPawnKinds()`（`core.cs:3838`）撈進來，玩家可在編組精靈直接選用、成本依其 `combatPower` 計算。**這是最便宜的內容擴充途徑**（出新兵種＝出新 PawnKindDef）。

## 若要寫 C# 擴充（必須繼承/註冊）
- **新 warband 升級**：繼承 `WarfareAndWarbands.Warband.WarbandComponents.PlayerWarbandUpgrades.PlayerWarbandUpgrade`（`core.cs:5986`），覆寫 `CanAttack/CanMove/CanDroppod/CostsSilver/GearQuality/MaintainDays/ExtraPawns/OnMapLoaded/GetExtraAttackFloatMenuOptions` 等 virtual；並在 `PlayerWarbandUpgradeHolder`（`core.cs:6152`，`GainXxxUpgrade`）加入授予路徑。由於 holder 的 `Gain*` 方法寫死 5 種，外部 mod 實務上需 Harmony 才能塞自己的升級——**升級系統不是開放擴充點**。
- **新 PolicyWorker**：繼承 QL 的 `PolicyWorker`（在 QL DLL，由另一 agent 確認），於 PolicyDef 的 `workerClass` 引用。
- **改 warband 行為**：因 `Warband`/各 manager 為密封實作，多半得 Harmony。

## 與另兩個 DLL 的擴充邊界
- 自訂 Def 型別（FactionTraitDef/PolicyDef/PolicyCategoryDef）的**類別宿主在 QL DLL**，但 XML 都放在核心 mod 的 `Defs/` 下；資料驅動程度由 QL 引擎決定（本檔以 XML 結構推論，QL 內部讀取邏輯交由 QL 分析確認）。
- 領袖能力的 data-driven 程度需看 WAWLeadership DLL（`CompProperties_Leadership` 是否有可 XML 配置欄位），本核心 DLL 只持有 `PlayerWarbandLeader` 包裝。
