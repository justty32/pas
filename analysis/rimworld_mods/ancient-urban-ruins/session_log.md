# Ancient Urban Ruins 分析 session log

- 辨識：XMB.AncientUrbanrUins.MO（3316062206），都市探索內容+工具 mod，6 DLL（核心 AncientMarket_Libraray + ACM_RandomBuildings/AI/Renderer/手电筒/FukIdeoApparel + CE gated）。
- 反編譯核心 AncientMarket_Libraray.dll(4751 行) + ACM_RandomBuildings → projects/.../decompiled/。
- 關鍵發現：核心庫含 CustomMapDataDef/DialogTreeDef/CQFThingDefCount/QuestNode_GenerateCustomSite，12 處引用 CustomQuestFramework → 建在第一批 CQF 的資料模型上。
- CustomMapDataDef:Def 是逐格預製地圖藍圖(size/fogged/terrains/roofs/thingDatas/pawns/routes/tags/extraDataByDirection 可組合)，靠遊戲內平面圖工具產生。
- 任務接點：QuestNode_GenerateCustomSite 可在純 XML QuestScriptDef 用(QuestScriptDefs.xml 實例)；SitePartWorker_CustomMap+MapGeneratingUtility 攤開地圖；ModExtension_Portal/Trader/Lootbox/VirutalMiner。
- 結論：任務串接/對話/派系/商人純 XML；地圖藍圖是 Def 但靠工具產；生成引擎/AI/渲染/ModExtension 行為 C#。與 CQF＋cqf-caravan-redemption 衍生直接相關。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
