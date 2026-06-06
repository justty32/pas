# session_log — Vanilla Outposts Expanded 分析

- 2026-06-06 識別來源 mod：VOE（workshop 2688941031，1.6），相依 Harmony + VEF。
- 反編譯 VOE.dll → projects/rimworld_mods/vanilla-outposts-expanded/decompiled/（只含 VOE.Outpost_* 具體子類）。
- 發現框架引擎不在 VOE：在 VEF 內 Outposts.dll（workshop 2023507013）→ 反編譯到 decompiled-framework/。
- 確認 OutpostBase 抽象 def 在 VEF Defs/WorldObjectDefs/Base.xml，預設 worldObjectClass=Outposts.Outpost。
- 核心結論：產資源型 outpost＝純 XML（Outpost_Logging/Trading 為證）；互動服務型＝需 C# 子類。
- 留檔 architecture/00_overview, 01_framework_lifecycle；tutorial/01_add_outpost_xml；details/outpost_extension_fields。
- 回答襲擊問題：框架現行不對 outpost 發動襲擊；raidPoints/raidFaction 是死欄位；About 描述過時。
- 真正的「襲擊設計」是反向：Outpost_Defensive 用 Harmony 削減打主基地的 raid + 投送增援；Outpost_Artillery 對外砲擊。留檔 details/raid_and_attack_design.md。
- 待辦：使用者要「在此基礎做一些 outpost」→ 進入 create（brainstorm 要做哪些 outpost），歸 derived/rimworld_mods/ 或 rimworld_mods 群組。
- 並行：另派 2 個 subagent 分析 Custom Quest Framework（2978572782）與 SpeakUp+Bubbles（3445623063/1516158345）。
