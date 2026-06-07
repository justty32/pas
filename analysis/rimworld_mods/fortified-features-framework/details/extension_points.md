# 擴充接點：純 XML vs 必須 C# 二分

FFF 是「函式庫型」框架——絕大多數價值都是**讓你用 XML 引用它已寫好的 C# 型別**。判斷準則：

> 若你的需求能對應到一個既有的 `CompProperties_*` / `DefModExtension` / data `Def`（`AirSupportDef`、`SymbolDef` 等），就是純 XML；
> 若需要「新的行為演算法」（新 Comp 邏輯、新 QuestNode、新狀態機、新 Verb），就必須 C#。

## A. 純 XML 即可（直接引用 FFF 型別）

| 想做的事 | XML 掛載方式 | FFF 型別（行號） |
|---|---|---|
| 建築/機兵可上色＋迷彩 | `<comps><li Class="Fortified.CompProperties_Paintable">` | `CompProperties_Paintable` 10942 |
| 新增迷彩花紋 | 新 `Fortified.FFF_CamoDef`（給 `texPath`） | `FFF_CamoDef` 12823（範例 `Defs/CamoDefs.xml`） |
| 陣營預設配色 | `Fortified.FFF_FactionPaintDef` | 10980 |
| 一棟建物佈局 | `Fortified.StructureLayoutDef` ＋ `Fortified.SymbolDef` 字典 | 36915 / 37031 |
| 一座聚落（多棟＋路＋防禦） | `Fortified.FFF_CompoundStructureDef` | 33982 |
| 在地圖/世界生成放結構 | `GenStepDef`(class `Fortified.Structures.GenStep_FFF*`) / `WorldGenStepDef` | 36555 / 36821 |
| 召喚空襲/砲擊/照明彈 | `Fortified.AirSupportDef`（內含 `AirSupportComp_*` / `AirSupportData_*` 組件清單） | 15067 + 14141/14616 |
| 切換彈種武器/砲塔 | `<comps>` 加 `CompProperties_AmmoSwitch` / `CompProperties_SwitchableAmmo` | 16059 / 16628 |
| 錐形/集束/沿途/複合爆炸彈 | `ThingDef` projectile class `Projectile_ConeExplosive`/`_ClusterBomb`/`_AlongWayDamage`，或掛 `CompProperties_ExplosiveWithComposite`＋`ModExtension_*` | 28457/28204/27525/28009/28146 |
| 重武器需特定體型/義肢才能拿 | `Fortified.HeavyEquippableDef`＋武器掛 `HeavyEquippableExtension` | 17684 / 17696（範例 `Defs/HeavyEquippableDef/FFF_EquippableDef.xml`） |
| 偽裝/匿蹤＋被偵測 | `CompProperties_Camouflage` / `CompProperties_PerimeterScanner` | 3206 / 16943 |
| 可拾取再放置的砲塔（minified deployable） | 繼承 `FFF_MinifiedTurret` / `FFF_BaseDeployableBuilding` 範本 | `Defs/FT_Security_Deployable.xml`；`MinifiedThingDeployable` 25079 |
| 王權點數呼叫空援/機兵/商隊 | `RoyalTitlePermitDef` worker = `RoyalTitlePermitWorker_CallAirSupport`/`_MechJoin`/`_Trader`／`_Bandwidth`＋對應 extension | 15921/33039/33449/32536 |
| 自爆/方向爆炸/自我修復/掃射 等異能 | `AbilityDef` 掛 `CompProperties_AbilitySelfExplosion`/`_AbilityDirectionalExplosion`/`_AbilitySelfRepairMode`/`_AbilityStrafing` | 48/489/881/1077 |
| 受擊掉/補的防彈板 | `CompProperties_BulletproofPlate` | 19414 |
| 多種雜項 Comp | `CompFloating`(浮空)、`CompCauseGameConditionAdjustable`、`CompIncidentMaker`、`CompFueledSpawner`、`CompSignalTower`、`CompCommandRelay`、`CompPerimeterScanner` … | 各見 00_overview 子系統表 |
| 強制陣營好感（劇本） | `ScenPart_ForcedFactionGoodwill` | 37645 |
| 開局帶結構 | `ScenPart_AddStartingStructure` | 37575 |
| 依體型計算傷害 | `DamageDef` worker = `DamageWorker_CountByBodysize` | 4243 |

> 紋理/迷彩 png、塗裝 shader（`fortified_shaders`）已內建在 FFF；下游 mod 只需引用，不必自帶資產。

## B. 部分 XML、行為仍靠 FFF C#（你只填資料，邏輯不可改）

| 子系統 | XML 能調的 | 邏輯鎖在 C# 之處 |
|---|---|---|
| 偵察突襲 ScoutedRaid | `IncidentDef` 掛 `IncidentExtension_ScoutedRaid`（撤退條件、屋頂分級、權重清單） | 兩階段流程＝`ScoutedRaidStateMachine` 21243、`IncidentWorker_FFF_ScoutedRaid` 20956、`LordJob_FFFScoutAssault` 21054 全在 C# |
| 機兵膠囊 MechCapsule | ThingDef 範本（`Defs/MechCapsule.xml`）＋`ModExtension_MechCapsule`/`ModExtension_DeactivatedMech` | 駭入/空投/封存邏輯在 `Building_MechCapsule` 26228、`MechCapsuleUtility` 26835 |
| 自動工作台 Autofacturer | ThingDef＋`ModExtension_AutoWorkTable`/`ModExtension_RecipeInheritance`/`ModExtension_QualityChance` | `Building_WorkTableAutonomous` 23451、`WorkGiver_DoAutonomousBill` 24120 |
| 環境限定配方 | `RecipeDef` 掛 `ModExt_EnvironmentalBill`（真空/潔淨/微重力需求） | `Bill_Production_Environmental` 17190、`EnvironmentUtility` 17372 |
| 護盾/改裝 Modification | `HediffDef` 掛 `HediffCompProperties_ProtectiveShield`/`_Modification` | `HediffComp_ProtectiveShield` 18045、`ModificationUtility` 18350 |
| 容器/物流 | ThingDef 範本＋`ModExtension_Container`/`_Lootbox`/`CompProperties_ListedContainer`/`_LogisticTerminal` | `Building_ListedContainer` 24750、`Building_LogisticTerminal` 25464 |
| 結構生成任務 | symbol/element 觸發既有 task | 新「放置後行為」需新 `IFFF_GenerationTask` 子類（C#） |

## C. 必須 C#（FFF 不開放純 XML）

| 需求 | 為何必須 C# | 對應 FFF 例子 |
|---|---|---|
| 人型機兵能換武/穿甲/被指揮的核心 | 涉及 `Pawn` 子類與大量 Harmony patch（指揮範圍、繪製、工作標籤） | `HumanlikeMech` 7930、`MechApparelGenerator` 8500、`Patch_InMechanitorCommandRange` 11745 等十餘 patch |
| 新的潛入任務節點 | QuestNode 是 C# 型別 | `QuestNode_FFF_MapCovertOp` 13739、`QuestNode_FFF_PawnCovertOp` 13866、`QuestPart_FFF_SiteRaidController` 13909 |
| 改寫遊戲既有行為 | 需新 Harmony patch | `HarmonyEntry` 13028＋全部 `Patch_*` 群 |
| 新空襲效果原語 | `AirSupportComp_*` / `AirSupportData_*` 是 C# 組件（雖然由 AirSupportDef 組裝） | 14141 / 14616 |
| 新 Verb（多重射擊、近戰橫掃、彈種切換射擊） | Verb 是 C# | `Verb_MultiShoot` 31516、`Verb_MeleeSweep` 31341、`Verb_LaunchProjectile_AmmoSwitch` 16788 |
| 多管/載人砲塔的射擊與容量邏輯 | C# Building/Comp | `Building_TurretCapacity` 24335、`CompMultipleTurretGun` 18419 |
| CE 相容（彈藥/爆炸對接 CombatExtended） | 需編譯對 CE 的相容 DLL | `1.6/CE/Assemblies/FortifiedCE.dll`（`CompExplosiveWithCompositeCE`、`Verb_ShootCE` 等） |

## 關鍵：FFF 沒有單一「主 Def 型別」

不同於某些框架有一個 `XxxDef` 當核心，FFF 的擴充接點是**散在十幾個子系統各自的 `CompProperties` / `DefModExtension` / data `Def`**。擴充時的正確心法：先確認需求屬於哪個子系統（見 `architecture/00_overview.md` 子系統表），再查該子系統的掛載型別。
