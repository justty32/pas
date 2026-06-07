# Deep And Deeper 分析 session log

- 辨識：Shashlichnik.DeepAndDeeper（3509420021），DRG 風地下採礦遠征；版本走 LoadFolders（共用 Defs/ + v1.6r2）。
- 反編譯 v1.6r2/DeepAndDeeper.dll → projects/.../decompiled/（3820 行）。
- 核心：PocketMap/MapPortal 家族——CaveEntrance:MapPortal、CaveExit:PocketMapExit、CaveMapComponent:UndercaveMapComponent；逐層下探洞窟口袋地圖。
- 興趣點：GenStep_CaveInterest 抽象+約 10 子類（Chemfuel/CorpsePile/Hive/Mushrooms/Mutant/Cryptosleep/LostPawn/Fleshbeasts），Anomaly 內容 MayRequire gate。
- 資料驅動：MapGeneratorDef(Lvl1-4)串 GenStepDef，GenStepDef 餵 worker 參數(mineableModifier/reward/countChances/mutant)。
- 結論：新增/重排/調校洞窟層＝純 XML；新興趣點類型/進出崩塌挖掘機制＝C#。Site/PawnKind/Items/Buildings/CaveStabilizer ext 皆純 XML。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
