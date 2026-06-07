# RV with built-in PD 擴充接點（extension_points）

> 目標：在此基礎做 create（衍生）。`<mod>` = `~/.local/share/Steam/steamapps/workshop/content/294100/3342334887`，主源碼 `<mod>/1.6/Src_PocketMapLibBased/src/`。

## 0. 一句話結論

**「再造一台有內建空間的載具」幾乎全是純 XML**：複製 RV 的 `VehicleDef` + `VehicleBuildDef`，掛上現成的 `RVwithPD.CompProperties_RVwitPD`（設定車內地圖長寬），其餘行駛/傳送門/PocketMap 機制全由 VehicleFramework + SimplePortal + RV 既有 C# 自動完成。**要改「車內空間的本質行為」（生成內容、進出規則、收起邏輯、遠端操作）才必須碰 C#。**

## A. 純資料（XML）能做什麼

### A1. 新增「另一台內建 PD 的載具」 —— 完全純 XML ✅（最省力路徑）
複製並改寫兩個 def：
- 車輛：仿 `<mod>/1.6/Defs/RVwithPD/VehicleDefs/RV_VehiclePawn.xml:5`，改 `defName/label/graphicData/components/roles/stats`，**保留 `comps` 裡的**：
  - `<li Class="RVwithPD.CompProperties_RVwitPD">`（`RV_VehiclePawn.xml:507`）→ 用 `mapWidth/mapHeight/stuffDef` 設定車內地圖大小。
  - `Vehicles.CompProperties_FueledTravel`（行駛燃料）。
  - **不需要**手動加 SimplePortal comp：SimplePortal 對 `BaseVehiclePawn` 的 patch 會自動注入（見 01 §2.5）。
- 藍圖：仿 `RV_Buildable.xml:4`（`VehicleBuildDef`），改 `costList/researchPrerequisites/thingToSpawn`。

風險：低。唯一隱含相依＝必須同時啟用 VehicleFramework + SimplePortal（與 RV 同樣的硬相依）。車內地圖共用同一個 `Furia_InteriorSpace` 生成器與 biome，外觀會一樣。

### A2. 改車內空間大小 —— 純 XML ✅
改 `CompProperties_RVwitPD` 的 `mapWidth/mapHeight`（`RV_VehiclePawn.xml:508-509`）。執行時還會疊加玩家設定的偏移（`Settings.widthOffset/heightOffset`）與 `MapEdgePadding(2,2)`（`CompRVwithPD.cs:22,90,94`）。下限硬鎖 7×7。

### A3. 改造價 / 研究 / 速度 / 燃料 / 部件 —— 純 XML ✅
- 行駛/部件/座位：改 `VehicleDef` 內 `vehicleStats / components / roles / properties`（全是 VehicleFramework 欄位）。
- 燃料：改 `CompProperties_FueledTravel`（`RV_VehiclePawn.xml:513`）。
- 造價/研究：`RV_Buildable.xml` + `ResearchProjectDefs/`。

### A4. 改車內地板/牆/屋頂的「材質 def」 —— 半 XML ⚠️
`GenStep_InteriorSpace` 用的是 `InteriorSpaceDefOf` 裡寫死的四個 def（`InteriorSpaceDefOf.cs:16-20`：`Furia_InteriorSpaceSurface/Roof/Wall` + biome）。可改 `TerrainDef.xml` 等 def 的數值/外觀（純 XML），但**換成不同 defName 的地板/牆**需要改 `InteriorSpaceDefOf` 引用（碰 C#）。牆的 stuff 寫死 `Silver`（`GenStep_InteriorSpace.cs:20`）—— 改材質要碰 C#。

### A5. 隔空充電的速率 / 電池容量 —— 純 XML ✅
`<mod>/1.6/Patches/Portal_Patch.xml:9-19`：`CompLinkedFueld` 的 `consumeRate/chargeRate` 與 `CompProperties_Battery` 的 `storedEnergyMax/efficiency`。

### A6. 純 XML 做不到的（必須 C#）
- 改「車內地圖長相不只是空房間」（生成傢俱/預置佈局）。
- 改「進出規則 / 收起時的疏散行為」。
- 新的 RemoteBox / RemoteSeat 類型或其轉發目標。
- 把「車內傳送門端」換成非 `SimplePortal_Square`。

## B. 改碼能做什麼（C# 接點）

### B1. 車內地圖生成內容 —— `GenStep_InteriorSpace.Generate`（`GenStep_InteriorSpace.cs:10`）
目前只鋪地板/牆/屋頂、清肥沃度。想要「出生就有床/儲物/工作台」可在此 `GenSpawn.Spawn` 預置 Thing，或新增自己的 `GenStepDef` 串進 `Furia_InteriorSpace` 的 `genSteps`。風險：中（要注意別擋住中央傳送門位置 `map.Center`）。

### B2. 車內地圖行為 —— `InteriorSpaceMapComponent`（`InteriorSpaceMapComponent.cs:12`）
- 自動拆地圖條件：`MapComponentTick`（`:36-44`）。
- 收起疏散邏輯：`TeleportPawnsClosing`（`:46-105`）、目的地優先序（`:55-71`）。
- 想做「車內可被襲擊」「車內天氣/溫度跟車外」等，從這裡或 `CompRVwithPD.CompTickRare`（`CompRVwithPD.cs:127`，`sourceMap` 同步）切入。風險：中（牽動威脅點補丁 `Patch_Fixer.cs:117`）。

### B3. 對接邏輯 / 多個傳送門 —— `CompRVwithPD.initPD`（`CompRVwithPD.cs:92`）
目前一台車＝一張地圖＋一個中央出口。想做「多出口」「車內再開傳送門到第三地圖」需改這裡的 `linkedPortal` 配對。風險：中高（SimplePortal 的 `linkedPortal` 是一對一指標，多對一要自己管理）。

### B4. 遠端貨艙/座位 —— `RemoteBox/`（見 01 §5）
- 轉發目標層：`RemoteThingOwner.RemoteHolder` setter 展開 holder 清單（`RemoteThingOwner.cs:52-88`）、`HolderIndex`（`:98-105`）。
- 自動換駕駛策略：`RemoteSeat_Building.DriverChanges`（`RemoteSeat_Building.cs:189-261`，挑人排序在 `:225-248`）。
- 深度依賴 VehicleFramework 的 `VehicleRoleHandler / VehicleCaravan / VehicleStatDefOf`（`RemoteThingOwner.cs:124`、`RemoteSeat_Building.cs:207-217`）。風險：高（VehicleFramework 升級時 API 易變，且無源碼難追）。

### B5. 相容性補丁群 —— `Patch_Fixer.cs` / `Patch_FixerVEF.cs` / `VehicleFrameworkFix.dll`
若你的衍生引入新的地圖/載具情境（例如水上載具、空中載具），可能要在 `Patch_Fixer.cs` 增補新的口袋地圖相容判定。`IsInteriorSpace`（`Patch_Fixer.cs:13`）是判別車內地圖的通用工具，沿用它。風險：中。

### B6. mod 設定 —— `Settings.cs`（`Settings.cs:7`）
加新選項：在 `ExposeData`（`:17`）+ `DoWindowContents`（`:30`）成對加欄位。風險：低。

## C. 風險與陷阱速記

| 項目 | 說明 |
|---|---|
| SimplePortal comp 來源 | 車輛的 `CompSimplePortal` 來自 SimplePortal 對 `BaseVehiclePawn` 的 patch，**不在 RV 的 def 裡**。衍生載具若 `ParentName` 不是 `BaseVehiclePawn` 鏈，就拿不到傳送門能力。 |
| 兩份源碼樹 | `Src_PocketMapLibBased`=主邏輯、`Src_VEFFixOnly`=獨立 VEF 熱修，**兩個 DLL 都要保留**（不是二選一）。 |
| 地圖尺寸下限 | 硬鎖 ≥7×7（`CompRVwithPD.cs:22`），且實際還加 padding。 |
| 威脅點/財富 | 預設車內不計威脅、不被襲擊（`sourceMap=null` + `Patch_Fixer.cs:117`）；開 `wealthReflects` 才反映車外財富。 |
| VehicleFramework 無源碼 | B4/B5 觸及的 `Vehicles.*` API 升級易碎，改動前先確認當前 VEF 版本簽名。 |
| Map.Index 複用 | 口袋地圖佔 index，VEF pathing 快取要靠 `VehicleFrameworkFix.dll` 清，移除它會路徑錯亂。 |
