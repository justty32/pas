# session_log — caravan-adventures (Analysis)

- 2026-06-06 讀 About.xml/LoadFolders.xml：確認唯一硬相依 Harmony、Royalty 軟相依、Story/CEPatches/Expansions 用 IfModActive 條件式掛載。
- 2026-06-06 掃反編譯 23944 行命名空間：分出 Camp/Story/Bounty/MechChips/ItemSelection/Incidents/Improvements/Immersion/Patches/Abilities 等子系統。
- 2026-06-06 讀 Story/Defs 18 子目錄 + QuestScriptDefs.xml：發現 5 個 QuestScriptDef 全指向 QuestNode_Temp 空殼。
- 2026-06-06 讀 StoryWC(:9434)/QuestCont(:10982)/WorldComponentTick(:9602)：確認劇情是 storyFlags 字典 + QuestCont_* 控制器的 C# 狀態機。
- 2026-06-06 讀 Expansions namespace + Expansion.xml：確認 Expansions 是 C# 外掛框架（ExpansionDef.assemblyName 偵測第三方 mod 做 reskin）。
- 2026-06-06 產出 architecture/00_overview.md、architecture/01_story_state_machine.md、details/extension_points.md。
- 2026-06-06 在 projects/.../caravan-adventures/ 留 SOURCE_POINTER.md。
