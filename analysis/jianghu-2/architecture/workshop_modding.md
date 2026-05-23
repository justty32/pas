# Steam Workshop / 官方 Mod 框架剖析

> 來源：`ModSpace/WorksShopManager.cs` (941 行)、`ModSpace/ModPack.cs`、`ModSpace/ModelData.cs`、`SweetPotato/DataMgr.cs`  
> 日期：2026-05-22

## TL;DR

- 遊戲內建 **官方 mod 框架**，**完全跑在資料層**（不是 plugin DLL）。
- 一個 mod 由兩個檔案組成：`workshop.json`（metadata）+ `db1_Mod.txt`（資料表覆蓋/新增，CSV 格式）。
- 可改的 **資料表多達 21 種**（物品、招式、NPC、任務、對話、商店、掉落、屬性公式、字串本地化…）。
- **不能改的**：行為邏輯、戰鬥決策、UI 結構 — 這些走 BepInEx 才能改。
- 支援 **Steam Workshop + WeGame Rail**（雙平台中文遊戲標準）。

## 1. 整體架構

```
                  ┌──────────────────────────────┐
                  │  AppGame.Start()              │
                  │  └─ WorksShopManager.Init()   │
                  └──────────────────────────────┘
                                 │
                  ┌──────────────┴─────────────────┐
                  │  WorksShopManager (Singleton)  │
                  │  basePath = persistent/Mod/    │
                  │  localModels: Dict<id, Data>   │
                  │  helper: Rail or Steamworks    │
                  └──────────────┬─────────────────┘
                                 │
       ┌─────────────────────────┼──────────────────────────┐
       │                         │                          │
       v                         v                          v
┌────────────────┐       ┌────────────────┐       ┌──────────────────┐
│ LocalModData() │       │ Steam UGC API  │       │ Rail UserSpace   │
│ 掃 Mod/ 子資料夾│       │ Query/Upload/  │       │ (WeGame)         │
│ 找 workshop.json│       │ Subscribe/Vote │       │                  │
└───────┬────────┘       └────────┬───────┘       └────────┬─────────┘
        │                         │                        │
        └────────────┬────────────┴────────────────────────┘
                     │
                     v
        ┌──────────────────────────────────┐
        │  GameSaving.Instance.useModels   │
        │  (List<ModID>, 從存檔讀)         │
        └──────────────┬───────────────────┘
                       │
                       v
        ┌──────────────────────────────────────────────┐
        │  WorksShopManager.LoadModel() →              │
        │  DataMgr.LoadPlayerMod(modId, path)          │
        │   └─ 讀 path/db1_Mod.txt → CSV parse →       │
        │      呼叫各 prototype.loadCSV(modId, row)    │
        └──────────────────────────────────────────────┘
```

## 2. 檔案/路徑佈局

### 2.1 Mod 基礎目錄

`WorksShopManager.cs:55 Init()`：
```csharp
basePath = $"{DataMgr.GetPersistentPath()}Mod";
```

`DataMgr.GetPersistentPath()`（`ModSpace/DataMgr.cs:235`）：

| 平台 | 解析結果 |
|---|---|
| Windows | `<Application.dataPath>/StreamingAssets/Mod/` ＝ 遊戲安裝目錄下 |
| 其他平台 / **Proton 跑這版遊戲** | `<persistentDataPath>/StreamingAssets/Mod/` |

本機（Linux + Proton）實際應該是：
```
~/.local/share/Steam/steamapps/compatdata/1606180/pfx/drive_c/users/steamuser/AppData/LocalLow/inmotiongame/下一站江湖Ⅱ/StreamingAssets/Mod/
```

（玩家還沒裝過 mod 所以這目錄目前不存在。）

### 2.2 單一 mod 的目錄結構

```
Mod/
└── <modName>/
    ├── workshop.json        # metadata（必要）
    ├── db1_Mod.txt          # 資料表覆蓋/新增（必要）
    ├── preview.png          # 預覽圖（推測，由 previewUrl 指向）
    └── …                    # 其他資產（圖片、字串檔等）
```

## 3. `workshop.json` 格式

由 `ModSpace/ModPack.cs` 寫入。注意：**格式是「`BinaryWriter.Write(string)` 包一層 length-prefixed UTF-8 後再寫一段 pretty-printed JSON 字串」**（跟主存檔 binary header 同樣機制）。

```json
{
    "publishedFileId": 0,        // Steam Workshop / Rail 上的 ID，未上傳前是 0
    "fileName": "/full/path/to/workshop.json",
    "title": "New Title",
    "contentFolder": "",         // 內容資料夾路徑
    "changeNote": "Version 1.0",
    "description": "no description",
    "previewUrl": "",            // 預覽圖路徑
    "metadata": "",
    "visibility": 0,             // EWorkshopFileVisibility (public=0/friends=1/private=2/unlisted=3)
    "modId": 1748000000,         // 自動產生：DateTimeOffset.UtcNow.ToUnixTimeSeconds()
    "tags": "[\"tag1\",\"tag2\"]" // tags 自己是 JSON-encoded 字串
}
```

`modId` = **mod 建立時的 Unix timestamp**（`ModPack.GenerateModId()` @ `ModPack.cs:113`）。整個系統用這個 ID 給 mod 加入的資料條目做命名空間。

PrettyPrintJson 是手刻的縮排器（`ModPack.cs:128`，每層 4 space）。

## 4. `db1_Mod.txt` 格式（資料表）

跟原版 `db1.txt`（`StreamingAssets/DB/db1.txt`）格式相同：

```
<tableName1>|<count1>
<row1_field1>#<row1_field2>#<row1_field3>...
<row2_field1>#<row2_field2>#<row2_field3>...
...
<tableNameN>|<countN>
<row1...>
```

- 每個區段：表名 `|` 行數
- 每列：欄位以 `#` 分隔
- 載入器：`SweetPotato/DataMgr.cs:373 LoadPlayerMod(int modId, string dataName)`

載入流程：
1. 讀整個 `db1_Mod.txt` 到 `byte[]`
2. 對每個區段：找 `RegisterDir[tableName]` 取得對應 `LoadCSV` delegate
3. 對每列呼叫 `value.loadCSV(modId, row_array)`
4. `modId` 被傳進每個 prototype 的 LoadCSV，用來標記資料來源（之後可用 `DataMgr.GetModId(entityId)` 反查是不是 mod 加的）

### 4.1 可改/可新增的 21 個資料表

| 表名 / 類別 | id 範圍 (原版預留) | 用途 |
|---|---:|---|
| `SpawnPointPrototype` | 0+ | NPC 刷新點 |
| `QuestPrototype` | 10,000,000+ | 任務 |
| `ClientScriptsDef` | 10,000,000+ | 客戶端腳本定義 |
| `NpcPrototype` | 1,000,000+ | NPC 原型 |
| `ConditionPrototype` | 10,200,000+ | 條件 DSL |
| `Stringlang` | 1,300,000,000+ | **本地化字串** |
| `NpcInteract` | 1,200,000,000+ | NPC 互動 |
| `FormulaBaseAttri` | 5,000,000+ | **屬性公式** |
| `MiJiPage` | 500,000+ | 秘籍頁 |
| `MiJi_graph` | 500,000,000+ | 秘籍圖 |
| `MiJi_node` | 20,000,000+ | 秘籍節點 |
| `SpellPrototype` | 50,000,000+ | **招式** |
| `ItemPrototype` | 10,000,000+ | **物品** |
| `ItemEquip` | 10,000,000+ | **裝備** |
| `WordEntry` | 300,000,000+ | 詞條 |
| `Areatrigger` | 400,000+ | 區域觸發 |
| `ShopProto` | 300,000,000+ | **商店** |
| `NpcAttriDynamic` | 1,000,000+ | NPC 動態屬性 |
| `NpcFight` | 1,000,000+ | **NPC 戰鬥配置** |
| `Dialoguelist` | 1,300,000,000+ | **對話** |
| `Loot_items` | 300,000,000+ | **掉落** |

來源：`SweetPotato/DataMgr.cs:174-194`（`RegisterDir.Add` 共 **21 筆**）。**這就是官方 mod 框架的「能力邊界」**。

#### 白名單機制（2026-05-23 補充驗證）

- 可改表的權威清單 = `SweetPotato/DataMgr.cs:85` 的 `RegisterDir`（`Dictionary<string, RegisterType>`），在 `Init()` 的 `:174-194` 填入，**正好 21 筆**。
- `LoadPlayerMod`（`:373`）讀 `db1_Mod.txt` 時，逐段比對表名：`if (!RegisterDir.TryGetValue(text, out value) || result == 0)` → **不在白名單就讀掉該段 N 行後 `continue`（靜默丟棄，無報錯）**（`:410-417`）。所以「表名打錯」或「表不在白名單」的效果一樣：完全沒作用。
- **對照組**：本體全量 DB（`db1.txt`）由另一個 master 表載入（`:940+` 的 `dictionary`，~100+ 張表，含 `way_point`/`way_point_event`/`npc_environmentsound`/`npc_xiuxiananim`/`NpcTeam`/`JingMai_*` 等）。**這些表本體會載，但不對 mod 開放**。
- 另有第三個登記表：`ModSpace/DataMgr.cs:75-100` 的 `registerType`（22 筆，Type-keyed，帶 `isLoadModOnlyDB` 旗標），用於 **mod 編輯器 / `IsModReserve` ID 命名空間判定**。與執行期 21 表大致重疊但不完全相同（多了 `NpcPrototypeBase`/`SpellEffect`/`WordEntryType`/`YedScript`/`LootItem`；少了 `SpawnPointPrototype`/`ClientScriptsDef`）。**它也不含上述四張環境行為表**。

→ **結論**：NPC 自主環境行為的四張表（`npc_xiuxiananim`、`npc_environmentsound`、`way_point`、`way_point_event`）**確定不能透過 Workshop 改**，只能 BepInEx。詳見 `details/npc_environment_interaction.md` 第六節。

### 4.2 能力邊界（2026-05-23 拆 5 個實際 mod 後修正）

> ⚠️ 原本此節寫「不能改邏輯 / 不能載資產」，拆 mod 後證實**太絕**。詳見 `answers/mod_db1_schema_validation.md`。

**mod 其實做得到（資料驅動）：**
- 改 21 張白名單表（數值/物品/裝備/商店/NPC/對話/任務/掉落/屬性公式/字串）。
- **行為腳本 / 劇情演出序列**：透過 `scriptsclient` 表（ClientScriptsDef）+ `Graphml/Bin/<檔名>.bytes`（編譯後 yEd graphML 圖）。載入路徑 `Automat.cs:79-82`：腳本 ID 屬 mod 範圍時直接 `File.ReadAllBytes(modPath + "/Graphml/Bin/" + name + ".bytes")` 執行。函式庫 = `AutomatManager.handlerMap`（如 `AutoFindPath`、`ShowBlackScreen`、`SetNpcPostion`、`IsMoveFinished`、`EnterXiuXian`…）。
- **資產目錄**：`ModSpace/ResourcePath.cs:9-15` 預留 `Graphml/` `SFX/` `Gui/` `Scene/` 四種。Graphml 已確認實際使用；SFX/Gui/Scene 待實測。

**mod 仍做不到（必須 BepInEx）：**
- 任意 C# 程式碼、新增引擎/腳本函式（只能用既有 `handlerMap` 詞彙）。
- 改戰鬥決策核心、改既有 UI 佈局結構、hook 網路。
- 改不在 21 表白名單的資料表（如 NPC 自主環境行為的 `way_point`/`npc_xiuxiananim`/`npc_environmentsound`/`way_point_event`）。
- Manager singleton 行為、Save/Load 流程。

→ 精準說法：官方框架給「**用固定函式庫拼裝行為**」的 DSL 能力，不是「寫新程式碼」的能力。

## 5. Mod 管理 API

`WorksShopManager` 提供的玩家可見功能（從方法名解讀）：

| 方法 | 功能 |
|---|---|
| `LocalModData()` | 掃本地 `basePath` 找已安裝 mod |
| `LoadModel()` | 依 `GameSaving.useModels` 載入啟用的 mod 進資料表 |
| `QueryItem(page)` | Steam Workshop 列表分頁查詢 |
| `QueryUserItem(page)` | 我發佈的 mod 列表 |
| `CheckItemSubscribed(id)` | 是否已訂閱 |
| `UnsubscribeItem(id)` | 退訂 |
| `Vote(id, voteUp)` | 投票 |
| `GetVoteResult(id)` | 拿投票結果 |
| `CreateMod(path, name, desc)` | 在本地建立新 mod 雛形 |
| `UploadItem(path, editPack?)` | 上傳/更新 |
| `UpdateWorkshop(fileId)` | 對既有 Workshop item 推送更新 |
| `ValidateModPack(path)` | 驗證 workshop.json 格式 |
| `SetRawImage(url, image, w, h)` | 用 URL/path 載預覽圖 |

對應的 Steam UGC API（`Steamworks.SteamUGC.*`）：
- `CreateItem` (line 348)
- `SubmitItemUpdate` (line 433, 741)
- 各種 CallResult<T>：CreateItemResult_t、SubmitItemUpdateResult_t、SteamUGCQueryCompleted_t、SteamUGCRequestUGCDetailsResult_t、Remote(Un)SubscribePublishedFile、(G/S)etUserItemVote

WeGame 走 `rail.IRailUserSpaceHelper`，事件透過 `RailCallBackHelper.Instance.RegisterCallback` 註冊。

## 6. 玩家如何啟用 mod

從 `LoadModel()` (line 145) 推：

1. 玩家在主選單/設定裡選 mod 訂閱（產生 `GameSaving.useModels: List<ModID>`）
2. 存進存檔 JSON（key 大概是 `SteamWorksManager.useModels` 或 `RailWorksManager.useModels` — 見 `WorksShopManager.Load@173`）
3. 載入存檔時 `WorksShopManager.LoadModel()` 把訂閱的 mod 餵給 `DataMgr.LoadPlayerMod`

**結論：mod 是 per-save 啟用，而非全域**。換存檔時 mod 配置可不同。

## 7. 與 BepInEx 路線的對比

| 維度 | 官方 Workshop | BepInEx |
|---|---|---|
| 載入機制 | 遊戲內建 DataMgr CSV pipeline | winhttp.dll doorstop → BepInEx → Harmony patch |
| 修改範圍 | **資料表（21 種）** | **任意 IL 程式碼** |
| 修改深度 | 不能改邏輯 | 能改邏輯（含 AI、戰鬥、UI） |
| 玩家安裝 | 訂閱 Workshop，無痛 | 手動放 plugin DLL 進 `BepInEx/plugins/` |
| 玩家分享 | Workshop 上架，付費可能 | 第三方平台（NexusMods 等） |
| 跨存檔 | per-save 設定 | 全域 |
| 防毒誤判 | 無 | DLL 可能被掃 |
| 開發體驗 | 改 CSV / 用遊戲內編輯器 | 寫 C# + 編譯 + iterate |

**理想做法：兩條都用**。資料/平衡改動 → Workshop；行為/UI/AI 改動 → BepInEx。

## 8. 對你的 mod 設計的啟示

回顧前面 AI 分析，幾個 mod 構想對應到框架的可行性：

| 構想 | 推薦路徑 | 為什麼 |
|---|---|---|
| 改某 NPC 的招式組 | **Workshop** (`NpcFight`) | 純資料改動 |
| 新增武功秘籍 | **Workshop** (`MiJiPage` + `MiJi_node` + `MiJi_graph` + `SpellPrototype`) | 純資料 |
| 新增物品 / 裝備 | **Workshop** (`ItemPrototype` + `ItemEquip`) | 純資料 |
| 新增任務 | **Workshop** (`QuestPrototype` + `Dialoguelist` + `ConditionPrototype`) | 純資料 |
| 新增 NPC + 對話 | **Workshop** | 純資料 |
| 重新平衡屬性公式 | **Workshop** (`FormulaBaseAttri`) | 純資料 |
| 換 AIDialog endpoint 接 LLM | **BepInEx** | 改 C# 邏輯 |
| LLM 動態對白 | **BepInEx** + 可能配 Workshop 註冊 hook 條件 | 程式行為改動 |
| 更聰明的戰鬥 AI | **BepInEx** | 改 UnitController |
| 自訂 UI (新面板) | **BepInEx** | 改 UI 必須走 plugin |
| 存檔編輯器（外掛） | 獨立工具（不需 mod 框架） | 直接讀寫 JSON |

## 9. 待深入

- [ ] `RailUserSpaceHelper` 細節（WeGame 平台）— 若你不上 WeGame 可略
- [ ] `WorksShopManager.Save` / `Load`（與存檔系統的整合）
- [ ] `DataMgr.GetModId(id)` 與 mod 範圍計算公式（如何避免條目 ID 衝突）
- [~] 是否能透過 mod 載入額外的 AssetBundle — 框架預留 `SFX/`/`Gui/`/`Scene/` 目錄（`ModSpace/ResourcePath.cs`），Graphml 已證實可用；其餘 3 種待實測（見 `answers/mod_db1_schema_validation.md`）
- [x] 既有的 Workshop mod 範例下載拆檔驗證 schema — **完成**，5 個 mod 全部符合，13/21 表實際使用，ID offset 吻合（見 `answers/mod_db1_schema_validation.md`）
- [x] 拉出 `AutomatManager.handlerMap` 完整函式清單 = mod 腳本可用 API 全集 — **完成**：963 個函式，分類整理於 `answers/automat_script_api.md`，全清單 `others/automat_script_functions.txt`
