# SCMF Sample 分析 session log

- 列出 mod 全部檔案，`find -name "*.dll"` 確認零 DLL（純資料範例）。
- 讀 About.xml：硬相依僅 Ariandel.AriandelLibrary，loadAfter 含米莉拉/萌螈/面部動畫。
- 讀 LoadFolders.xml：用 IfModActive gate 種族專屬內容於 1.6/Mods/<packageId>/。
- 讀 Backstory/Trait 共用 Defs：TraitDef 掛 4 個 AL 特質級 modExtension。
- 讀 Ingefrid PawnKindDef（~325 行全註解）：框架三件套 FixedIdentity/NPCKindTag/SpecialPawn + 十餘選用 AL_*_Extension。
- 讀 GuanJu PawnKindDef：對照組，註解掉 Kill_Manager 等，示範可繁衍/可被煉的取捨。
- 讀 ShroudOutcomeDef×2、Hediff_GuanJu（HediffCompProperties_WearApparel）、FA Unique*×6、Keyed/Name.xml。
- 對照 decompiled AriandelLibrary.cs：確認 14 個引用 class 全部存在，欄位名比對通過。
- 產出 architecture/00_overview.md、details/extension_points.md、tutorial/01_make_special_character_xml.md。
- 在 projects/rimworld_mods/scmf-sample/ 留 SOURCE_POINTER.md。
