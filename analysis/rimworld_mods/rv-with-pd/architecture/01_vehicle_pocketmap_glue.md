# 車輛 + PocketMap 車內空間 + pawn 進出 完整管線（01_vehicle_pocketmap_glue）

> 路徑以 `<mod>` = `~/.local/share/Steam/steamapps/workshop/content/294100/3342334887` 代稱，主源碼在 `<mod>/1.6/Src_PocketMapLibBased/src/`。
> VehicleFramework 無源碼，凡 `Vehicles.*` / `VehiclePawn` / `VehicleRoleHandler` 皆為「相依框架 API，RV 只是呼叫端」。
> SimplePortal 有源碼，路徑 `~/.local/share/Steam/steamapps/workshop/content/294100/3325512144/1.6/Src/src/`，下文以 `<SP>` 代稱。

## 0. 三方分工速查

| 能力 | 由誰負責 | 接點 |
|---|---|---|
| 車輛行駛、駕駛座、貨艙、燃料 | **VehicleFramework**（DLL） | `RV_VehiclePawn.xml` 的 `VehicleDef` + comps |
| 車輛取得「傳送門」身份 | **SimplePortal**（patch） | SimplePortal 把 `CompSimplePortal` patch 進 `BaseVehiclePawn` |
| 車內是一張獨立小地圖 | **RimWorld 原生** | `PocketMapUtility.GeneratePocketMap` |
| pawn 進出車內 | **RimWorld 原生 MapPortal** | `SimplePortal_Building : MapPortal`，`GetOtherMap()` |
| 生成/掛載/收起車內地圖、對接兩端 | **RV 本體** | `CompRVwithPD` + `InteriorSpaceMapComponent` |

## 1. 車輛行駛（純相依框架，RV 不碰）

`RV_VehiclePawn.xml:5` 是一個標準 `Vehicles.VehicleDef ParentName="BaseVehiclePawn"`：
- `components`（`:104-503`）：引擎/輪/懸吊/面板等可損壞部件 → VehicleFramework 的部件損傷系統。
- `properties/roles`（`:70-101`）：`driver`(slotsToOperate=1, handlingType=Movement) + `passenger` → VehicleFramework 的座位/操作系統。
- `comps`（`:505`）：`Vehicles.CompProperties_FueledTravel`（`:513`，Chemfuel）→ 行駛耗油，全由 VehicleFramework 處理。

RV 對行駛**唯一的介入**是相容性補丁（非功能）：
- `Patch_FixerVEF.cs:14` patch `Vehicles.PathingHelper.VehicleImpassableInCell`：地圖若無 `VehiclePositionManager`（車內小地圖正是如此）→ 不套用載具阻擋判定。
- `VehicleFrameworkFix.dll`（`Src_VEFFixOnly/src/Patch_Fixer.cs:7`）：生成地圖時清 `MapComponentCache<VehiclePathingSystem>`，避免 `Map.Index` 複用導致 pathing 快取錯亂。

## 2. 車內 PocketMap 的生成與掛載

入口：玩家在選中的車上按「展開 PD」gizmo（`CompRVwithPD.cs:56-64`，僅在 `interiorSpaceMap == null` 時出現）。

`CompRVwithPD.initPD()`（`CompRVwithPD.cs:92-110`）逐步：

1. **算地圖尺寸**：`Props.MapSize`（`CompRVwithPD.cs:22`）＝ `mapWidth/Height + Settings 偏移`，至少 7×7，再加 `MapEdgePadding (2,0,2)`（`:90,94`）。RV 的 def 給 `mapWidth=21, mapHeight=13`（`RV_VehiclePawn.xml:508-509`）。
2. **生成口袋地圖**（原生）：
   ```
   Map map = PocketMapUtility.GeneratePocketMap(mapSize, InteriorSpaceDefOf.Furia_InteriorSpace, null, null);
   ```
   （`CompRVwithPD.cs:95`）。`Furia_InteriorSpace`（`MapGeneratorDef`，`InteriorSpaceMapGenerator.xml:4`）指定：
   - `customMapComponents` 掛 `RVwithPD.InteriorSpaceMapComponent`（`InteriorSpaceMapGenerator.xml:10-12`）；
   - `genSteps` 走 `GenStep_InteriorSpace`（`GenStep_InteriorSpace.cs:6`）：每格鋪 `Furia_InteriorSpaceSurface` 地板 + `Furia_InteriorSpaceRoof` 屋頂、邊緣格放 `Furia_InteriorSpaceWall` 牆、把 elevation/fertility 清零（`:14-30`）；
   - 專屬 `BiomeDef Furia_InteriorSpace`（無動植物、永遠晴天，`InteriorSpaceMapGenerator.xml:28-80`）。
3. **記住擁有者**：`map.GetComponent<InteriorSpaceMapComponent>().ownerThing = this.parent`（`CompRVwithPD.cs:97-99`），車 = owner。
4. **在地圖中央放「出口傳送門」**：`ThingMaker.MakeThing(SimplePortal_Square)` → `GenPlace.TryPlaceThing(... map.Center ...)`（`CompRVwithPD.cs:101-103`）。`SimplePortal_Square` 是 SimplePortal 為載具特製的傳送門 def（`<SP>/.../Defs/SimplePortalDefs/ThingDef_ForVehicle.xml`，label「Vehicle Exit」，`allowConnnectThing = Vehicles.VehiclePawn`）。
5. **兩端對接**（關鍵膠合）：
   ```
   portalExit.Portal.linkedPortal = this.parent;            // 出口端 -> 車輛
   portalEnter.linkedPortal = portalExit;                   // 車輛端 -> 出口
   ```
   （`CompRVwithPD.cs:105-108`）。其中 `portalEnter = this.parent.TryGetComp<CompSimplePortal>()` —— **車輛的 `CompSimplePortal` 由 SimplePortal patch 注入**（`<SP>/.../Patches/Patch_Vehicles.xml`：對 `BaseVehiclePawn/comps` 加 `SimplePortalLib.CompProperties_SimplePortal`）。RV 自己**沒有**在 def 裡宣告這個 comp。

存檔：`interiorSpaceMap` 以 `Scribe_References` 存（`CompRVwithPD.cs:47`），地圖本身由原生 PocketMap 系統序列化。

## 3. pawn / 物品如何進出車內

**完全復用 SimplePortal_Building（= 原生 `MapPortal`）的進入機制**，RV 不寫任何 teleport 程式碼來「進入」。

- `<SP>/.../SimplePortal_Building.cs:18`：`public class SimplePortal_Building : MapPortal, IRenameable`。
- `<SP>/.../SimplePortal_Building.cs:187` `GetOtherMap()` ⇒ `Portal?.linkedPortal?.MapHeld`；`:197` `GetDestinationLocation()` ⇒ 對端 `PositionHeld`。
- 因此「pawn 走進車輛端傳送門」沿用 RimWorld 異常 DLC 的坑道門（pit-gate）那套 `MapPortal` enter job/loader toil，目的地解析為「對端 `MapHeld`」。
  - 從外面進車：對車輛端 `CompSimplePortal` 觸發 enter ⇒ 對端 = 車內地圖中央那個 `SimplePortal_Square` ⇒ pawn 落到車內地圖。
  - 從車內出車：對車內 `SimplePortal_Square` 觸發 enter ⇒ 對端 = 車輛 ⇒ pawn 落回車輛當前所在的地圖（`MapHeld`）。

**收起 / 緊急疏散**（`InteriorSpaceMapComponent.cs`）：
- 每 300 tick，若「沒在收起且(車已毀或沒人擋著拆地圖)」就 `PocketMapUtility.DestroyPocketMap`（`InteriorSpaceMapComponent.cs:41-42`）—— 車內沒人時自動回收地圖。
- 按「收起 PD」gizmo（`CompRVwithPD.cs:67-87`）→ `StartClosing()`（`InteriorSpaceMapComponent.cs:20`）。
- `TeleportPawnsClosing()`（`:46-105`）：逐個（每 6–60 tick 一個）把車內 pawn/物品用 `SkipUtility.SkipTo` 送到目的地圖（優先 `ownerThing.MapHeld`，否則找傳送門對端，否則任一玩家殖民地），全部清空後 `DestroyPocketMap`。

**隨車移動的世界座標同步**（`CompRVwithPD.cs:127-166`，每 250 tick）：
- 把車內地圖的 `Parent.Tile` 設成車輛當前 `Tile`（`:159-161`）——車開到哪，車內地圖的世界座標就跟到哪。
- `pParent.sourceMap`：若 `Settings.wealthReflects` 為真才指向車外地圖，否則 `null`（`:163-164`）。`null` 時配合 `Patch_Fixer.cs:117-131` 讓車內地圖的襲擊威脅點歸零（即「車內財富不算進襲擊強度、也不會被當作可被襲擊的殖民地」）。

## 4. 讓「口袋地圖當車內」不報錯的相容補丁（`Patch_Fixer.cs`）

| Patch 類別（`Patch_Fixer.cs`） | 目標 | 作用 |
|---|---|---|
| `PoketMapNoRoofCollapse`（`:20`） | `RoofCollapseCellsFinder.Notify_RoofHolderDespawned` | 車內屋頂不塌 |
| `PoketMapDrawBuildEdgeLinesNot`（`:31`）/ `...ZoneEdgeLinesNot`（`:38`） | `GenDraw.DrawNoBuild/ZoneEdgeLines` | 不畫「邊緣禁建」線 |
| `PoketMapAllowBuildNearEdge`（`:46`）/ `...ZoneNearEdge`（`:60`） | `GenGrid.InNoBuild/ZoneEdgeArea` | 車內可貼邊建造/劃區 |
| `FindMap_Override`（`:77`）/ `MapParentAt_Override`（`:88`） | `Game.FindMap` / `WorldObjectsHolder.MapParentAt` | 車內地圖在世界地圖層級「不存在」(回 null) |
| `WorldGrid_LongLatOf_Fix`（`:100`） | `WorldGrid.LongLatOf` | 無任何殖民地時影子計算不崩 |
| `StorytellerUtility_DefaultThreatPointsNow_Fix`（`:117`） | `StorytellerUtility.DefaultThreatPointsNow` | `sourceMap==null` 的口袋地圖威脅點＝0 |

判別車內地圖的工具：`PatchUtil.IsInteriorSpace(this Map)`（`Patch_Fixer.cs:13`）＝該地圖是否掛了 `InteriorSpaceMapComponent`。

## 5. RemoteBox / RemoteSeat：隔空操作車輛（進階膠合）

讓玩家在「外部基地」放一個代理建築，透過已對接的傳送門連動讀寫**遠端車輛**的貨艙/座位：

- 建立入口：`CompLinkedFueld.CompGetGizmosExtra`（`CompLinkedFueld.cs:81`）—— 掛在車內傳送門端（`SimplePortal_Square` 經 `Portal_Patch.xml` 加上 `CompLinkedFueld`），若 `portal.linkedPortal is VehiclePawn` 才出現「建立 Cargo/Seat Link」gizmo（`CompLinkedFueld.cs:100-121`）。
- `RemoteThingOwner`（`RemoteThingOwner.cs:15`）：不真的存物，靠 `holderList`（從 `RemoteHolder` 車輛展開出的所有 `IThingHolder`，`:52-88`）+ `HolderIndex` 把 `TryAdd/Remove/GetAt` 全部轉發到遠端車輛某一層（cargo / 各 `VehicleRoleHandler`）。
- `RemoteSeat_Building`（`RemoteSeat_Building.cs:20`）：把 pawn 透過原生 `CompTransporter` 裝載流程送進 VehicleFramework 的 `VehicleRoleHandler`（`DriverChanges()`，`:189-261`），含「依心情/睡眠/時間表自動挑駕駛」+ 定時換班（`FireSchedule()`，`:173-184`）。
- 充電：`CompLinkedFueld.CompTick`（`:44-70`）把連結車輛的 Chemfuel(`CompFueledTravel`) 轉成傳送門端電池(`CompPowerBattery`)的電 —— 即「車當發電機」。

> 這套 RemoteBox 是 RV 自寫、深度耦合 VehicleFramework 的 `VehicleRoleHandler` / `VehicleCaravan` / `VehicleStatDefOf.CargoCapacity`（`RemoteThingOwner.cs:124`）。要動它必碰 C#（見 extension_points）。
