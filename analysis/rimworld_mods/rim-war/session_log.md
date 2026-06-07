# Rim War 分析 session_log

- 反編譯 v1.6/Assemblies/RimWar.dll → projects/.../rim-war/decompiled/RimWar.decompiled.cs（19176 行，79 type）。
- 讀 About.xml：packageId Torann.RimWar，v1.6 僅依賴 brrainz.harmony（HugsLib 殘留於 1.2-1.5）。
- 確認 namespace RimWar.Planet（:7883-19144）為世界模擬主體。
- 定位驅動器 WorldComponent_PowerTracker.WorldComponentTick（:17030），排程決策/成長/戰鬥/勝利。
- 梳理 RimWarData（:1135）戰力模型＝聚落+單位+世界物件 points 總和（TotalFactionPoints :1510）。
- 釐清 GetWeightedSettlementAction（:1688）＋ behavior→權重歸一化（:15980-16098）。
- 釐清戰鬥：ResolveRimWarBattle（:10274）、聚落抽象戰（:11130+）、ConvertSettlement 易主（:15289）。
- 確認 grep 全檔無 HugsLib：v1.6 改用 vanilla Mod/ModSettings + HistoryAutoRecorderWorker。
- 讀 Patches/RimWarCompsx.xml：PatchOperationAdd 把 RimWarSettlementComp 掛進所有 Settlement。
- 讀 RimWarDef.xml：派系→behavior+movement/combat/growth bonus（純資料可調）。
- 確認玩家互動：CommsConsole patch（:5876）+ FactionDialogReMaker（:2530）請求商隊/軍援。
- 產出 SOURCE_POINTER.md / 00_overview.md / 01_world_simulation.md / details/extension_points.md。
