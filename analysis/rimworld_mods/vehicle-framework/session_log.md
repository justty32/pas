# Vehicle Framework 分析 — 操作日誌

- 讀 About.xml：唯一硬相依＝brrainz.harmony，無 VEF；supportedVersions 1.4/1.5/1.6，modVersion 1.6.2144。
- 確認 mod 純 DLL 無源碼；用 ilspycmd 反編譯 Vehicles.dll(90856 行)+SmashTools.dll(29286 行) 到 projects/.../decompiled/。
- 列舉 Defs：框架只附 Base* 抽象 VehicleDef/VehicleBuildDef，不附具體可玩載具（具體載具來自內容 mod）。
- grep 核心 class：VehiclePawn:Pawn(13103)、VehicleDef:ThingDef(11298)、VehicleBuildDef:ThingDef(5928) 確認「載具是 Pawn」。
- 拆 VehicleProperties(16950)/VehicleRole(17141)/VehicleComponentProperties(8850)/各 CompProperties(Fueled/Turrets/Launcher/UpgradeTree)。
- 確認 VEF 關係：碼中 VanillaExpanded 只出現在選用相容層(Compatibility_VanillaExpandedFishing:73663)＋MayRequire，非相依。
- 確認尋路：VehiclePathingSystem:MapComponent(54564)，每載具獨立 path grid/region/reachability/pathfinder，與原版分離。
- 確認升級樹資料驅動：UpgradeTreeDef(34361)+UpgradeNode(34057)+內建 Upgrade 子類(Stat/Comp/Settings/Sound/Turret/Action/Vehicle)。
- 讀 PatternDefs.xml：新塗裝＝純 XML PatternDef(defName/label/path)。
- 產出 6 份交付：SOURCE_POINTER.md、architecture/00_overview.md、01_vehicle_def_anatomy.md、details/extension_points.md、tutorial/01_add_vehicle_xml.md、本 log。
