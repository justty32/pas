# Ancient Urban Ruins 架構總覽（00_overview）

> 目標導向：analysis→create。核心釐清「純 XML 可做 vs 必須 C#」與擴充接點。

## 1. 一句話定位

`XMB.AncientUrbanrUins.MO`（workshop 3316062206）是一個**都市探索內容＋工具 mod**：提供大量建築/瓦礫美術素材、一批預製的都市廢墟地圖（地堡、避難所、街景），以及一套**「平面圖匯入 → 生成任務地圖」系統**。玩家可探索預製場景、打任務。

**關鍵架構事實：它的核心庫 `AncientMarket_Libraray.dll` 建在 Custom Quest Framework（CQF）的資料模型之上**——反編譯內含 `CustomMapDataDef`、`DialogTreeDef`、`CQFThingDefCount : LootThingData`、`QuestNode_GenerateCustomSite`，並有 12 處引用 `CustomQuestFramework`。這正是第一批分析的 **CQF（`HaiLuan.CustomQuestFramework`）** 與衍生專案 `derived/rimworld_mods/cqf-caravan-redemption`（其四章故事設計即用 `CustomMapDataDef`/`DialogTreeDef`）所用的同一套詞彙。**做都市場景任務時，本 mod 是 CQF 之外最值得參照的 CustomMapDataDef 實戰範例庫。**

## 2. DLL 組成（6 個）

| DLL | 角色 |
|---|---|
| `AncientMarket_Libraray.dll`（核心 4751 行） | CustomMapDataDef 地圖資料模型、地圖生成、任務節點、ModExtension 群 |
| `ACM_RandomBuildings (1).dll` | 隨機建築/廢墟拼貼生成 |
| `AncientMarketAI_Libraray.dll` | 場景 NPC/敵人 AI |
| `BuildingExtraRenderer.dll` | 建築額外渲染層（多層/裝飾） |
| `手电筒.dll`（手電筒） | 手電筒/照明機制 |
| `FukIdeoApparelBreadmoAM.dll` | 繞過 Ideology 服裝限制的小補丁 |
| （`CE/BreadMoCEThingSetMaker.dll`） | CE 戰利品相容（gated） |

> 注意反編譯檔內另有 `WalkerGear` 命名空間殘塊（與 Exosuit Framework 舊名同名的工具碼），非本 mod 主體。

## 3. 核心資料模型：CustomMapDataDef（預製地圖藍圖）

`CustomMapDataDef : Def`（`AncientMarket_Libraray.decompiled.cs:939`）逐格描述一整張預製地圖：

| 欄位 | 意義 |
|---|---|
| `size` (IntVec3) / `fogged` / `commonality` / `generationLimit` / `faction` | 尺寸、起霧、抽取權重、上限、歸屬派系 |
| `terrains` / `terrainsRect` (Dict<地形, 座標/矩形>) | 地形鋪設 |
| `roofs` / `roofRects` (Dict<RoofDef, …>) | 屋頂 |
| `thingDatas` (List<ThingData>) | 建築/物件逐個擺放 |
| `pawns` (List<PawnKindDefCount>) | 預置 pawn |
| `routes` (Dict<string, 座標>) | 命名路徑（巡邏/動線） |
| `tags` | 鬆耦合標籤（抽取/組合用） |
| `disgenerate` / `disdestroy` | 禁生成/禁破壞格 |
| `extraDataByDirection` / `extraDataByOrigin` (Dict→CustomMapDataDef) | **可組合**：依方向/原點掛子地圖（拼接大場景） |

> 這些逐格座標清單**由遊戲內的平面圖匯入/編輯工具產生**（mod 賣點之一），不適合手寫。

## 4. 與任務系統的接點

- `QuestNode_GenerateCustomSite : QuestNode:4121` — **可在純 XML 的 `QuestScriptDef` 裡用**，從 `CustomMapDataDef` 生成一個自訂地圖 Site（`Defs/QuestScriptDefs/QuestScriptDefs.xml` 即實例）。
- `SitePartWorker_CustomMap : SitePartWorker:4424`、`MapGeneratingUtility:1371`、`GenStep_GenerateData/SetFog/SetTerrain` — 把 CustomMapDataDef 攤開成真實地圖。
- `DialogTreeDef : Def:1738` — 場景對話樹（與 CQF 同型）。
- ModExtension 群：`ModExtension_Portal:3589`（傳送）、`ModExtension_Trader:3810`、`ModExtension_Lootbox:3826`、`ModExtension_VirutalMiner:2754`、`ModExtension_Map:3820`。

詳見 `details/extension_points.md`。
