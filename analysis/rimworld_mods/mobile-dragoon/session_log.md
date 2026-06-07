# session_log — mobile-dragoon

- 讀 About.xml / LoadFolders.xml / TODO（在 mod 根目錄非 1.6/）/ Base.xml，確認硬相依 Exosuit Framework + DMS Core。
- 核對檔案清單：無 Assemblies、無 .dll → 確認純內容包。
- 讀 PV8.xml（框架）、ModuleWeapon.xml、Modules_ShoulderLeft.xml、Modules_Pack.xml、Pawnkinds.xml、Building.xml、ResearchProject.xml、ThingCategoryDef.xml、Structure.xml。
- 讀 Patches：PatchPawnGroup / PatchHeavyEquippable / VFEP / DMSAC_CE，理解注入手法（pawnGroupMakers / EquippableWithApparel / FindMod 聯動）。
- 對照上游反編譯：確認 CompProperties_ExosuitModule(:3598)、ModExtForceApparelGen(:3969)、ApparelRenderOffsets(:3931)、Building_EjectorBay(:1383) 等均屬 framework。
- 核心模型：每模塊＝Item⇄Apparel 雙生 def，由 CompProperties_ExosuitModule(EquipedThingDef/ItemDef/occupiedSlots) 綁定。
- 產出 architecture/00_overview.md、details/extension_points.md、tutorial/01_clone_a_new_mecha_xml.md。
- 在 projects/rimworld_mods/mobile-dragoon/ 留 SOURCE_POINTER.md（標明無 DLL、純資料）。
