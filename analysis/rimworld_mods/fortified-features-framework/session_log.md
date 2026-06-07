# session_log — fortified-features-framework

- 讀 About.xml/LoadFolders.xml：硬相依僅 Harmony，CE 以 IfModActive 條件載入 1.6/CE/FortifiedCE.dll。
- 掃反編譯源 38881 行：命名空間 Fortified / Fortified.Structures；409 個型別。
- 列出全部 class/struct/enum/interface 宣告與行號，交叉 Languages/Keyed 檔名歸納子系統。
- 讀關鍵 Def：CamoDefs / HeavyEquippableDef / StatDef / MechCapsule / FT_Security_Deployable。
- 讀 HarmonyEntry(13028)、FFF_AssetLoader(4190)、CompProperties_Paintable/Camouflage。
- 深入結構生成：FFF_StructureDef(34112)/StructureLayoutDef(36915)/SymbolDef(37031)/FFF_CompoundStructureDef(33982)/IFFF_GenerationTask(37769)。
- 確認 FortifiedCE.dll 僅是 CE 版彈藥/爆炸 Comp 相容層，可略。
- 產出 architecture/00_overview.md（定位＋相依鏈 Mermaid＋子系統分類表）。
- 產出 architecture/01_structure_generation.md（最核心可純 XML 擴充子系統）。
- 產出 details/extension_points.md（純 XML / 部分 / 必須 C# 三區二分表）。
- 產出 tutorial/01_minimal_paintable_building.md（純 XML 塗裝＋結構入門）。
- 產出 projects/.../SOURCE_POINTER.md。
