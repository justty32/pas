# Faction Territories and Vassalage 分析 session log

- 辨識：jaeger972.factionterritories（3626725895），依賴 Map Mode Framework（繪圖引擎，使用者指示不特別分析）；版本無分層（Assemblies/Defs 置頂）。
- 反編譯 FactionTerritories.dll → projects/.../faction-territories/decompiled/（16317 行單檔）。
- 結構掃描：兩命名空間 FactionTerritories（領土/事件/設定）＋ FactionTerritories.Vassalise（附庸），另有 Invasions/Expansion。
- 讀 4 個 Def：Regions(MapModeDef)、CaravanIncidents(CaravanIncidentEntryDef 純資料)、Invasions/VassalOutposts(WorldObjectDef)。
- 釐清領土演算法：確定性 region 成長、邊權重＝移動難度＋丘陵偏移＋道路乘數，爭議格畫 Voronoi 混色，canCache。
- 釐清附庸：VassaliseUtility 三動作（附庸化/割讓/轉交毀城）＋藩屬點數＋VassalOutpost WorldObject＋攔截毀城信件。
- 結論：重 C# mod；純 XML 接點僅 CaravanIncidentEntryDef（領土感知事件表）＋ Map Mode Framework 的 MapModeDef。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
