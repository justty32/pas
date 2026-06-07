# Exosuit Framework 分析 — session log

（每項一句話，上限 50 行）

- 讀 About.xml/LoadFolders.xml：確認 1.6 只硬依 Harmony（VEF 僅 1.5），CE/HAR 走 IfModActive。
- 掃反編譯 11405 行 class 清單：定位 namespace Exosuit/Mechsuit 與所有核心型別行號。
- 確認本質：機甲＝Apparel（Exosuit_Core:Apparel :10245），非 Pawn/Building；停放靠 Dummy（Human 衍生）。
- 讀 SlotDef.xml + ModuleApparelBase/ModuleItemBase.xml：插槽純資料，模組分 item/apparel 雙 Def 範本。
- 讀 Exosuit_Core 全文：結構點血量＝Σ模組HP、CheckPreAbsorbDamage 攔傷分攤、爆機生 Wreckage。
- 讀 CompSuitModule:3343 / CompProperties_ExosuitModule:3598：EquipedThingDef/ItemDef/occupiedSlots 是核心接點。
- 讀 ExosuitExt:3949 + 登機門檻 :4951-4984：BodySizeCap/RequireAdult/RequiredApparelTag/RequiredHediff 純資料。
- 讀 Building_MaintenanceBay GearUp:9556/GearDown:9578 + Dummy getter:8863：整備總控確認。
- 讀 BuildingDefs.xml/FuelCellDefs.xml：維護坞鏈完整；燃料電池是唯一具體模組範例（雙 Def 鏡像）。
- 確認框架不含任何具體機甲（只抽象範本）；DMS 鉤子＝research heldByFaction DMS + SpawnHostileAmmoDragoon:5874。
- 既存 00_overview.md（前次 session 寫的）審查通過、保留不動。
- 新增 architecture/01_module_apparel_and_boarding.md（插槽/雙身/血量/Dummy/維護坞/Comp 表）。
- 新增 details/extension_points.md（純 XML vs C# 二分 + 接點清單 + DefModExtension 表）。
- 新增 tutorial/01_add_exosuit_xml.md（純 XML 一核心+一模組最小機甲教學）。
- SOURCE_POINTER.md 已存在於 projects/，內容正確、未改。
