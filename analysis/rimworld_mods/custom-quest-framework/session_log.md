# session_log — custom-quest-framework

- 起始：2026-06-06，Linux，Claude Code (Opus 4.8 1M)，目標 mod = HaiLuan.CustomQuestFramework（CQF），workshop 2978572782，目的：Analysis 後續做 create 擴充。
- 讀 About.xml／LoadFolders.xml：相依 brrainz.harmony；支援 1.4/1.5/1.6；以 IfModActive 掛載 Odyssey/AllsparkCrisis/HCF/Bill 子模組目錄。
- 反編譯 4 個 DLL 到 projects/.../decompiled/：主體 QuestEditor_Library（36433 行、403 class），及 3 個範例子 mod（CQFBillLibrary/CQFAndRS/HCFWithCQF）。
- 發現 mod 內 `.QuestEditor_Library/` 含作者原始碼 + 4 份作者寫的 SKILL.md（overview/def-catalog/action-condition-dev/map-dev），為一手權威資料。
- 確認框架本質：遊戲內視覺化 QuestEditor，把內容序列化成 QuestScriptDef + 自訂 Def（存進 mod RootDir/Quests），執行期用 QuestNode_DoCQFActions 把 CQFAction 腳本接進原版任務鏈。
- 確認擴充二分：純 XML（CustomMapDataDef/DialogTreeDef/GroupDataDef + CQFAction 組合，覆蓋絕大多數）vs C#（新增 CQFAction_Target/DialogCondition 子類，僅在需要新副作用/判定時）。
- 範例 C# 擴充樣板＝CQFAndRS::CQFAction_InfectTarget、HCFWithCQF::CQFAction_JoinHiveGroup：override Draw/RealWork/ExposeData。
- 完成 architecture/00_overview.md、architecture/01_framework_lifecycle.md、tutorial/01_add_custom_quest.md。
