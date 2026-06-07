# 擴充接點：純 XML vs 必須 C# 二分 (extension_points)

> 行號指反編譯源 `projects/rimworld_mods/exosuit-framework/decompiled/Exosuit.decompiled.cs`，XML 指 `1.6/Defs/` 與 `1.6/Patches/`。

## 結論先講
**做一台新機甲＋整套常規模組，可以「純 XML」完成。** 框架已把所有結構性邏輯（穿脫、整備、血量、承傷、渲染、移速/負重覆寫、UI）寫死在 DLL 並提供完整抽象範本與功能 Comp。只有在你要**全新的模組行為**（框架沒提供對應 Comp/Verb/Hediff 機制）時才需要 C#。

---

## 純 XML 可做（繼承範本 + 填欄位 + 掛現成 Comp）

| 想做的事 | 怎麼做（純 XML） | 依據 |
|---|---|---|
| **新機甲核心** | 寫 item 形態（`ParentName="ModuleItemCore"`）+ apparel 形態（`ParentName="ModuleApparelCore"`），兩者互掛 `CompProperties_ExosuitModule`（`isCoreFrame` 由 Core SlotDef 決定），apparel 加 `modExtensions` 的 `ExosuitExt` 設駕駛限制 | `ModuleApparelBase.xml:87`、`ExosuitExt :3949`、`CompProperties_ExosuitModule :3598` |
| **新部位模組**（頭/臂/掛架/背包…） | 同上，`ParentName="ModuleItem<部位>"`+`ModuleApparel<部位>"`，`occupiedSlots` 填對應 SlotDef | `FuelCellDefs.xml`（範本） |
| **燃料/動力模組** | 掛 `Exosuit.CompProperties_FuelCell`（`fuelDef`/`fuelCapacity`/`moveSpeedOffset`/`hediffDef`） | `CompFuelCell :2786`、`FuelCellDefs.xml:46` |
| **武器模組**（給駕駛員一把武器） | 掛 `Exosuit.CompProperties_ModuleWeapon`，`weapon` 指向一個帶 `CompApparelForcedWeapon` 的武器 ThingDef | `CompModuleWeapon :2548` / `:2707` |
| **肩砲/自動砲塔模組** | 掛 `Mechsuit.CompProperties_TurretGun`（含 verb/projectile 設定） | `CompTurretGun :108` / `CompProperties_TurretGun :68` |
| **近戰橫掃** | 掛 `Exosuit.CompProperties_MeleeSweep` | `Comp_MeleeSweep :7559` / `:7540` |
| **噴射/特效** | 掛 `CompProperties_LaunchExhaust` / `CompProperties_ProjectileFleckEmitter` | `:3300` / `:3717` |
| **新插槽（部位）** | 新增 `Exosuit.SlotDef`（給 `uiPriority`），並把它加進核心的 `SlotDef.supportedSlots` | `SlotDef :3861`、`SlotDef.xml` |
| **新整備建築 / 不同尺寸維護坞** | 繼承 `MaintanenceBayBase`（`thingClass=Building_MaintenanceBay`），改 `BayExtension`（`canRepair`/`canLoad`/`canStyle`）、`CompAssignableToPawn` 數量 | `BuildingDefs.xml:4`、`BayExtension :3941` |
| **爆機殘骸換成自訂物** | `ExosuitExt.wreckageOverride` 指向一個 `Building_Wreckage` 衍生 ThingDef | `ExosuitExt :3963`、`ExosuitDestory :10485` |
| **登機限制**（成年/體型/需駕駛服/需植入物） | 填核心 apparel 的 `ExosuitExt`：`RequireAdult`/`BodySizeCap`/`RequiredApparelTag`/`RequiredHediff` | `:4951`-`:4984` |
| **移速/負重貢獻** | 在 apparel 形態用 `equippedStatOffsets`（`CarryingCapacity`/`ExosuitMoveSpeed`）；框架的 `StatPart` 已自動把它算進 pawn | `StatPart_MoveSpeed :8164` / `StatPart_CarryingCapacity :8076`、`Patches/Stat_*.xml` |
| **研究前置 / 配方** | 標準 `researchPrerequisites`+`recipeMaker`（用既有 `WG_HeavyExoskeleton` 或自訂研究） | `ResearchProject.xml`、`RecipeDef.xml` |
| **HAR 種族相容** | 加進 HAR 白名單 patch（仿 `HAR_Race_Exosuit_whiteApparelList.xml`） | `1.6/Mods/HAR/Patches/` |
| **彈藥裝填（CE/原版 reloadable）** | item 態的 `EquipedThingDef` 帶 `CompProperties_ApparelReloadable`，`CompSuitModule` 會自動讀（`ammoDef`/`maxCharges`…） | `CompSuitModule.PostSpawnSetup :3568` |

### 純 XML 的「金律」
1. **一個模組 = 兩個 ThingDef**（item 形態 + apparel 形態），兩邊都掛 `CompProperties_ExosuitModule` 且 `ItemDef`/`EquipedThingDef` 互填。
2. **占用插槽 `occupiedSlots` 必填**，且同一機甲內各模組 `SlotDef.uiPriority` 不可撞號（否則 ConfigError `:3621`）。
3. **核心的 SlotDef.supportedSlots 決定這台機甲有哪些格**；模組的 `occupiedSlots` 必須是核心支援的格。

---

## 必須 C#（框架沒提供對應資料接點時）

| 情境 | 為何要 C# | 可繼承/實作的接點 |
|---|---|---|
| **全新模組「行為」**（框架沒有對應 Comp） | 行為邏輯寫死在各 `ThingComp` 子類，無泛用「行為腳本」資料層 | 自寫 `ThingComp`（一般 Comp）或實作 `IExosuitDestructionHandler`（爆機時觸發，見 `:10512`） |
| **自訂核心血量/承傷規則** | `Health`/`CheckPreAbsorbDamage`/`GetPostArmorDamage`/`OnHealthChanged` 是 `virtual`，但要改得 override | 繼承 `Exosuit_Core`（`:10245`，多數方法 `virtual`），新 apparel 的 `thingClass` 指向你的子類 |
| **自訂整備建築行為** | `Building_MaintenanceBay` 的 `GearUp/GearDown` 是 `virtual` | 繼承 `Building_MaintenanceBay`（`:9556`/`:9578` virtual） |
| **新的飛行/位移能力** | `WG_AbilityVerb_QuickJump`/`WG_PawnFlyer`/`Verb_MeleeSweep` 是具體 Verb 類 | 自寫 `Verb_*` / `PawnFlyer` 子類 |
| **新的渲染掛點**（特殊部位疊圖） | RenderNode worker/subworker 是 C# 類 | 自寫 `PawnRenderNodeWorker`/`PawnRenderSubWorker`（仿 `:7826`-`:8075`），在 apparel 的 `renderNodeProperties` 引用 |
| **改原版交互流程** | 走 Harmony | `ExosuitMod`（`:3902`）已建好 Harmony 實例 `instance`，自開 patch class |

### C# 最小骨架（自訂模組 Comp 範例）
```csharp
// 一個「受傷時冒煙」的範例模組 Comp（純資料 Comp 不夠時）
public class CompProperties_MyModule : CompProperties {
    public float threshold = 0.5f;
    public CompProperties_MyModule() { compClass = typeof(Comp_MyModule); }
}
public class Comp_MyModule : ThingComp, Exosuit.IExosuitDestructionHandler {
    CompProperties_MyModule Props => (CompProperties_MyModule)props;
    // 爆機時被 Exosuit_Core.ExosuitDestory 回呼（:10512）
    public void OnExosuitDestroyed(Exosuit.Building_Wreckage wreckage) {
        // 自訂掉落 / 觸發效果
    }
}
```
> 即便寫了自訂 Comp，**模組的「外殼」（item/apparel 雙 Def、占格、整備、穿脫、渲染）仍由 XML + 框架提供**，C# 只補那一塊行為。

---

## 接點清單（可繼承的型別 / 可填的 DefModExtension）

### 抽象 ThingDef 範本（`ParentName`）
- Item：`ModuleItemBase` / `ModuleItemCore|Head|Attachment|MountRight|MountLeft|ArmLeft|ArmRight`（`ModuleItemBase.xml`）
- Apparel：`ModuleApparelBase` / `ModuleApparelCore|Head|Attachment|MountRight|MountLeft|ArmLeft|ArmRight`（`ModuleApparelBase.xml`）
- 建築：`MaintanenceBayBase`、`WG_BaseGantryLinkable`、`WG_BaseScaffold`（`BuildingDefs.xml`）

### 可繼承的 C# 類（thingClass / compClass / workerClass）
- `Exosuit.Exosuit_Core`（核心 apparel，`:10245`，方法多為 virtual）
- `Exosuit.Building_MaintenanceBay`（`:8701`，GearUp/GearDown virtual）
- `Exosuit.Building_Wreckage`（`:10190`）

### DefModExtension（純資料覆寫）
| Ext | 掛在哪 | 欄位 |
|---|---|---|
| `ExosuitExt`（`:3949`） | 核心 apparel | `BodySizeCap`/`RequiredApparelTag`/`RequiredHediff`/`RequireAdult`/`CanGearOff`/`minArmorBreakdownThreshold`/`wreckageOverride`/`bayRenderOffset`/`bayRenderScale` |
| `BayExtension`（`:3941`） | 維護坞建築 | `canRepair`/`canLoad`/`canStyle` |
| `ApparelRenderOffsets`（`:3931`） | apparel | `headData`/`headHideFor`/`rootData`/`equipmentOffsetData` |
| `ModExtForceApparelGen`（`:3969`） | pawnkind 之類 | 強制生成整套機甲（給敵對機甲兵用，`apparels`/`chanceApparels`/`fallbackApparels`/`StructurePointRange`） |
| `ModExtension_Flyer`（`:2413`） | PawnFlyer | `flightRange` |
| `NoGenederApparelExt`（`:3995`） | apparel | 無欄位，標記不分性別渲染 |
| `ModExtension_NoIdeoApparel`（`:4016`） | apparel | 無欄位，標記不受意識形態約束 |

### 可實作的介面
- `IExosuitDestructionHandler.OnExosuitDestroyed(Building_Wreckage)`（爆機回呼，`:10512`）
- `IHealthParms`（健康面板資料，`Exosuit_Core` 實作）
