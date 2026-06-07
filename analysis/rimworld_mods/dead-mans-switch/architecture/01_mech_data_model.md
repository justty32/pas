# 核心子系統：機兵資料模型（純 XML × FFF 引擎）

DMS 最關鍵的子系統是「機兵」。本檔釐清一隻機兵在 XML 裡如何被組裝、行為從哪來，以證明「機兵＝純資料 + FFF 程式碼」。

## 機兵的三條 ThingClass 線

`grep <thingClass>` 全部 race Def 只出現三種類別，全部來自 FFF 或原版：

| thingClass | 來源 | 代表 | 意義 |
|---|---|---|---|
| `Pawn`（原版） | RimWorld | 一般 Automatroid 抽象基底 | 走 Biotech 機械體（`<intelligence>ToolUser` + `mechWeightClass`） |
| `Fortified.WeaponUsableMech` | **FFF** | Drone 基底、Automatroid 基底 | **能裝備武器的機兵**（原版機械體不能持槍，FFF 補上） |
| `Fortified.HumanlikeMech` | **FFF** | Synthroid（人形機 `DMS_Mech_Lady` 等） | 人形、能持武器、近人類行為的機兵 |

來源：`1.6/Defs/Things_race/Races_Automatroid_Base.xml`、`Races_Drone_Base.xml`、`Races_Synthroid.xml`。

## 一隻機兵的組裝配方（以游隼 `DMS_Mech_Falcon` 為例）

來源：`1.6/Defs/Things_race/Races_Automatroid_Light.xml`。一隻機兵 = 抽象基底 ThingDef + 具體 ThingDef，全部欄位都是 XML：

- **`statBases`**：MoveSpeed / 三抗（銳鈍能）/ `MaxFlightTime` / `FlightCooldown` — 純資料。
- **`race`**：`body`（自訂 BodyDef `DMS_Chop`）、`baseBodySize`、`baseHealthScale`、`mechWeightClass`（Light/Medium/Heavy）、`flightStartChanceOnJobStart` — 純資料。
- **Biotech 機械師欄位**（`MayRequire="Ludeon.Rimworld.Biotech"` 條件式）：`BandwidthCost`、`WastepacksPerRecharge` — 純資料，缺 Biotech 自動略過。
- **行為 Comp（全 FFF）**：`Fortified.CompProperties_FlyingFleckThrower`（懸停粉塵）等；配 `AnimationDef DMS_Hover`（FFF 的 `AnimationWorker_Keyframes` 驅動的純資料動畫）。
- **`modExtensions`**：`Fortified.MechWeaponExtension`（`EnableWeaponFilter` 決定可裝哪些武器）等。

→ **新增一隻機兵＝複製這段 XML、改 defName/label/貼圖/數值/Comp 列表**，不需碰 C#。

## 機兵能力與 Hediff（也全是資料 + FFF）

- **Abilities**（`1.6/Defs/Abilities`）：自爆 `Fortified.CompProperties_AbilitySelfExplosion`、自修 `…AbilitySelfRepairMode`、投放機兵 `…CompProperties_DropMech`、跳躍 `Fortified.ModExtensionJumper`，以及原版 `CompProperties_AbilityGiveHediff`。全是 `li Class="…"` 的 XML 設定。
- **Hediffs**（`1.6/Defs/Hediffs`）：機兵連結相關（`DMS_MechlinkOverload`/`KillSwitch`/`Rejection`…）用 FFF 的 `Fortified.Hediff_LevelLabel`、`Fortified.Hediff_SeverityByBandwidth`，或原版 `HediffWithComps` + 原版 HediffComp。**這正是 mod 名「Dead Man's Switch（死人開關）」的機制來源**：機兵連結過載/排斥的致命觸發 Hediff。

## 機兵的「生產入口」：Biotech 母體配方

- `1.6/Biotech/Defs/DMS_Recipes_MechGestator_*.xml`：每隻機兵一條 `RecipeDef`（繼承 `DMS_LightMechanoidRecipe` / `DMS_MediumMechanoidRecipe` / `DMS_HeavyMechanoidRecipe`），`<products>` 指向機兵 ThingDef，`<ingredients>` 指定鋼材/元件，`<researchPrerequisite>` 控制解鎖。
- 這是純 XML 的 Biotech 機兵母體（MechGestator）路徑；缺 Biotech 時整個 `1.6/Biotech` 不載入（`LoadFolders.xml`）。

## 武器（機兵特化武器）

- `1.6/Defs/Things_Weapon`：verbClass 多為原版 `Verb_Shoot`，少數用 FFF 的 `Fortified.Verb_ArcSprayProjectile`（弧形噴射，5 處）。武器與機兵的綁定靠 `Fortified.MechWeaponExtension` / `Fortified.HeavyEquippableExtension`（重型可裝備件，31 處）。
- 企劃書另載「機兵特化武器」清單（外連 Google Sheet），屬持續擴充的純資料。

## 小結（給 create 用）

機兵子系統是「**FFF 提供樂高積木（Comp/Verb/Hediff/ModExtension/ThingClass），DMS 用 XML 拼裝**」的典型 data-driven 架構。任何新機兵內容的增量都落在 XML；只有當你要的**行為積木 FFF 沒有**時，才需要寫 C#（且該寫進 FFF 而非 DMS）。
