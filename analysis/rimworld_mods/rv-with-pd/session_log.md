# session_log — rv-with-pd（Analysis 模式）

- 讀 About.xml：packageId flammpfeil.rv，硬相依 VehicleFramework + SimplePortal（同作者）。
- 列出 25 個 .cs：主源碼 Src_PocketMapLibBased/ + VEF 熱修 Src_VEFFixOnly/ + Geological compat。
- 讀 CompRVwithPD.cs：車內空間＝PocketMapUtility.GeneratePocketMap，車輛端 CompSimplePortal ↔ 車內 SimplePortal_Square 互設 linkedPortal。
- 讀 InteriorSpaceMapComponent.cs：無人自動拆地圖、收起時 SkipUtility 疏散 pawn/物。
- 讀 RemoteBox/：RemoteThingOwner 轉發到遠端車輛 holder；RemoteSeat 自動換駕駛 + 排程。
- 確認 RV 的 VehicleDef 無 SimplePortal comp，是 SimplePortal 的 Patch_Vehicles.xml patch 進 BaseVehiclePawn 注入。
- 確認 SimplePortal_Building : MapPortal，GetOtherMap()=linkedPortal.MapHeld → pawn 進出復用原生 MapPortal 機制。
- VehicleFrameworkFix.dll 只修一處：生成地圖時清 MapComponentCache<VehiclePathingSystem>（Map.Index 複用 bug）。
- 產出 00_overview / 01_vehicle_pocketmap_glue / details/extension_points / SOURCE_POINTER。

## 進度快照
- 當前理解：RV＝VehicleFramework 載具 + 原生 PocketMap 車內空間 + SimplePortal 對接，C# 只做生成/對接/相容補丁/遠端操作。
- 已完成：四份分析交付物 + 指標檔，全繁中含行號。
- 剩餘待辦：（如需）做 create 衍生載具時，最省力＝純 XML 複製 VehicleDef+BuildDef 並保留 CompProperties_RVwitPD。
- 核心上下文：純 XML vs C# 二分見 details/extension_points.md；機制圖見 architecture/。
