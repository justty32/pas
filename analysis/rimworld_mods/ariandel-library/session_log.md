# session_log — ariandel-library 分析

- 讀 About.xml/LoadFolders.xml：確認硬相依僅 Harmony，DLC/前置 mod 走 IfModActive gated 子模組。
- 列 Defs 目錄：發現 4 個自訂 Def 型別資料夾（DialogueDef/PsionicTabDef/ShroudOutcomeDef/SpecialPawnTabDef）。
- 讀 User_Manual_26May2026.md：作者隨附完整框架手冊，18 章逐模組對照源碼。
- 抽樣比對反編譯碼：SpecialPawnExtension 欄位、SpecialPawnRegistry 掃描邏輯與手冊一致。
- 確認 SpecialPawnRegistry 純資料驅動掃 PawnKindDef；Milira 硬編特例以 ModsConfig.IsActive 閘住。
- ilspycmd 反編譯 Royalty/Anomaly 子模組：確認「獨立小 DLL + StaticConstructorOnStartup + PatchAll + 引用主 DLL 型別」gated 模式。
- 讀 Sample mod (Ariandel.UserGuideSCMF, 3668177055)：純 XML 特殊角色完整模板，證明零 C# 可行；DLC 工具用 MayRequire gate。
- 驗證 VoidPawnManager(IThingHolder) 與 Pawn.Kill 前綴：真身 HealAndRecover、冒牌 DiscardFakePawn。
- 產出 architecture/00_overview.md、01_special_character_framework.md、details/extension_points.md、tutorial/01_minimal_special_character.md。
- 留 projects/.../ariandel-library/SOURCE_POINTER.md（主 DLL + 6 個 gated 子模組位置）。
