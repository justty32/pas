# Ancient Urban Ruins 擴充接點（純 XML vs 必須 C#）

> 結論：它建在 CQF 資料模型上。任務串接與內容（對話/派系/商人）純 XML 可做；地圖藍圖雖是 Def 但實務上靠遊戲內工具產生；地圖生成引擎/AI/渲染/ModExtension 行為鎖 C#。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 用既有預製地圖做一個任務 | ✅ 純 XML | `QuestScriptDef` 內用 `QuestNode_GenerateCustomSite` 指向某 `CustomMapDataDef`（仿 `Defs/QuestScriptDefs/QuestScriptDefs.xml`）。**與 CQF 任務寫法相通** |
| 場景對話 | ✅ 純 XML | `DialogTreeDef`（與 CQF 同型，純資料對話樹） |
| 隱藏派系 / 商人種類 / 研究 / 背景故事 | ✅ 純 XML | `Factions_Hidden.xml`、`TraderKinds.xml`、`ResearchProjects.xml`、`Backstorys.xml` |
| 新預製地圖（地堡/避難所/街景） | ⚠️ Def 但靠工具 | `CustomMapDataDef` 是純資料 Def，但逐格 `terrains/roofs/thingDatas/pawns` 座標清單**由遊戲內平面圖匯入/編輯工具產生**，不手寫 |
| 在建築上加傳送/商人/寶箱/虛擬採礦行為 | ⚠️ 半 | 掛 `ModExtension_Portal/Trader/Lootbox/VirutalMiner`（XML 掛載），但行為邏輯在 C# |
| 地圖生成演算法 / 隨機建築拼貼 | ❌ C# | `MapGeneratingUtility`、`GenStep_*`、`ACM_RandomBuildings` |
| 場景 AI / 額外渲染 / 照明 | ❌ C# | `AncientMarketAI_Libraray`、`BuildingExtraRenderer`、`手电筒` |
| CE / Ideology 相容 | ❌ C#（gated） | `CE/BreadMoCEThingSetMaker.dll`、`FukIdeoApparelBreadmoAM.dll` |

## 與 CQF（第一批）的關係——最重要的 create 線索

- 本 mod 核心庫 `AncientMarket_Libraray` **引用 CustomQuestFramework（12 處），共用 `CustomMapDataDef` / `DialogTreeDef` / `QuestNode_GenerateCustomSite`**。
- 因此：
  - 想做「自訂都市場景任務」的衍生，可同時參考 **CQF 的 `.QuestEditor_Library/`＋SKILL.md**（第一批備註）與**本 mod 的成品 CustomMapDataDef 庫**（`Defs/AncientMarket_Libraray.CustomMapDataDef/` 一堆地堡/避難所實例）。
  - 衍生專案 `derived/rimworld_mods/cqf-caravan-redemption` 的四章故事（Ch1 探索 CustomMapDataDef → Ch2 對話 DialogTreeDef）正是這套模型；本 mod 是該設計的現成參照素材。

## 最省力衍生

- **純 XML**：寫一個 `QuestScriptDef`（用 `QuestNode_GenerateCustomSite` 召喚既有預製地圖）＋ `DialogTreeDef` 對話 → 立即得到一個都市探索小任務，零 C#。
- 要做新場景外觀 → 用遊戲內平面圖工具產 `CustomMapDataDef`（非手寫、非 C#）。
- 要改地圖生成/AI/渲染 → C#（且 6 DLL 交錯，門檻高）。
