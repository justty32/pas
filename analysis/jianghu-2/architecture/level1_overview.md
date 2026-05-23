# Level 1 — 初始探索總結

> 日期：2026-05-22

## 1. 引擎與執行環境

| 項目 | 值 | 來源 |
|---|---|---|
| 遊戲引擎 | Unity **2021.2.2f1** | `下一站江湖Ⅱ_Data/globalgamemanagers`（strings） |
| Scripting backend | **Mono**（非 IL2CPP） | `下一站江湖Ⅱ_Data/Managed/` 內存在 `mscorlib.dll`、`Mono.Posix.dll`、`Mono.Security.dll` 等 mono profile assemblies |
| 目標 .NET | mono 4.x equivalent | 同上推斷 |
| Bundle identifier | `inmotiongame` | globalgamemanagers strings |
| Game DLL | `Assembly-CSharp.dll` (7.8MB)、`Assembly-CSharp-firstpass.dll` (146KB) | `../下一站江湖Ⅱ_Data/Managed/` |

**Mono 是好消息**：BepInEx + Harmony 對 Mono runtime 的 hook 成熟可靠，不需要走 IL2CPP 的繁瑣流程。

## 2. 主要 namespace（按檔案數排序）

頂層 `Assembly-CSharp/` 下：

| Namespace | 檔案數 | 性質 |
|---|---:|---|
| **(global / 無 namespace)** | 1548 | **遊戲主要程式碼都在這層**：所有 `*Manager`、`*Item`、`*Slot`、`*View`、戰鬥、任務、UI |
| **`SweetPotato/`** | 684 | 工作室自家命名空間，含 `Tools`、`GameSaving`、`JsonWriterWrap`，以及大量子系統（`MiniGames/`、`JingMai/`、`SpellEdit/`、`AuctionHouse/` 等 20+ 子目錄） |
| **`ModSpace/`** | 184 | **不是** mod API，是遊戲內 mod/資料定義 namespace（`AttriType`、`BuffInfo`、`ConditionPrototype`、`DataMgr` 等資料/UI 類別） |
| `ProceduralWorlds/` | 115 | 第三方：地形 / 世界生成插件 |
| `TriangleNet/` | 90 | 第三方：三角網格 |
| `KWS/` | 51 | 第三方：水體 shader |
| `ZenFulcrum/` | 51 | 第三方：嵌入式瀏覽器 |
| `Your/` | 49 | 第三方：UI 框架 (?) |
| `WorldStreamer2/` | 35 | 第三方：場景串流 |
| `BrainFailProductions/` | 34 | 第三方：減面工具 |
| `TMPro/` | 31 | 第三方：TextMesh Pro |
| `Runemark/` | 30 | 第三方 |
| `GameScript/` | 30 | 推測：遊戲腳本系統 |
| `CTS/` | 24 | 第三方：Complete Terrain Shader |
| `Excalibur/` | 13 | 第三方/自家：含 `Singleton<T>` 等基礎類別 |
| 其他 | ~30 | TheVegetationEngine、HighlightingSystem、UnityWebSocket … |

**關鍵推論**：mod 開發要關注的真正只有 **global + `SweetPotato/` + `Excalibur/` + `GameScript/`**，其餘是第三方資產。

## 3. 第三方執行時函式庫（值得知道）

- **LitJson** — 主要的 JSON 序列化（`JsonMapper`、`JsonWriter`），存檔系統大量使用
- **Newtonsoft.Json** — 另一套 JSON 庫，看 namespace 看哪邊用
- **DOTween / DOTweenPro** — 動畫補間
- **Cinemachine** — 攝影機
- **Steamworks.NET** (`com.rlabrecque.steamworks.net.dll`) — Steam SDK，意味著有 **Steam Workshop**
- **NPOI / NPOI.OOXML** — Excel I/O（推測：策劃表 → 程式碼資料）
- **ICSharpCode.SharpZipLib** — zlib 壓縮
- **mysql.data.dll** — 古怪，單機遊戲帶 MySQL 客戶端（推測：開發期工具殘留，或某外掛依賴）
- **MagicaClothV2** — 布料模擬

## 4. 入口與啟動流程

主入口：`AppGame.cs`（2297 行）— 單一 MonoBehaviour，掛在 boot scene 的 root，是全域單例（`AppGame.Instance`）。

關鍵生命週期（`AppGame.cs`）：
1. **`Awake()` (line 587)**
   - `UnityEngine.Debug.Log("AppGame Awake")` ← BepInEx log 抓這行可確認載入順序
   - `base.gameObject.GetOrAddComponent<ResourceManager>()`（line 598）
   - **`GameSaving.InitLocalFileCheck()`**（line 609）— 本地檔/設定初始化
   - 寫死 `CultureInfo` 為 `en-US`（避免中文 locale 解析數字出問題）
   - 讀取 `<persistentDataPath>/Local/config.txt` 設定畫質
   - `InitSetting()` 設定品質、抗鋸齒、動態解析度
   - 設定 `_instance = this`（單例）
2. **`Start()` (line 810)**
   - `Singleton<WorksShopManager>.Instance.Init()` ← **Steam Workshop mod 系統初始化**
   - `StartGame()` → `ResourceManager.PreLoadAssetBundle()` → `BeginGame()`
3. **`StartGame()` (line 824)** — 註冊 `SceneManager.sceneLoaded += LoadFinishedScene`、初始化 `FormManager`、`GetNewAppUrl()`、`BeginGame()`

**Mod 介入點建議**：
- `AppGame.Awake` postfix Harmony patch — 可拿到最早的單例引用，但要小心其他 Manager 還沒初始化
- `AppGame.Start` postfix — Workshop 已起來、大部分 Manager 已 ready
- `GameSaving.InitLocalFileCheck` 是存檔系統 hot path

## 5. Manager 類別（核心系統清單）

頂層 namespace 共 **51 個 `*Manager.cs`**，按職能分類：

### 遊戲世界 / 場景
- `LoadSceneManager`、`MySceneManager`、`MapManager`、`PatchManager`、`SnowManager`

### 玩家進度 / 系統
- `AchieveManager`（成就 — 已知存檔 key `"achieve"`）
- `RelationShipManager`、`StuntManager`（武功絕學）、`GrowManager`
- `MailManager`、`GameManualManager`（圖鑑）

### 任務 / 事件
- `VirtualEventManager`（虛擬事件，**有 `[GameSaveKey]` 標記**）
- `XuanShangManager`（懸賞）、`EntrustGlobalManager`（委託）
- `XiaYunLuManager`、`MPEventManager`、`WayPointEventManager`、`MenPaiQuestManager`

### 門派 / 戰鬥
- `MenPaiAttriManager`、`MenPaiSoldierManager`、`MenPaiWarManager`
- `SpellEventManager`、`TargetManager`

### NPC / AI
- `AIDialogManager` ← **真 AI 聊天功能**
- `NpcConditionalDialogueManager`、`NPCBubblingBoxManager`、`RandomNpcManager`
- `ListenerSpellManager`、`EmojiManager`

### 系統服務
- `SteamManager`、`HttpRequestManager`、`DownloadResManager`、`VersionChangeManager`
- `GmManager`（GM 工具）、`AutomatManager`、`CinematicManager`、`TimelineManager`

### 其他
- `BuYeJingManager`（不夜京）、`JailManager`（牢獄）、`QingLouManager`（青樓）、`QianXingManager`、`FlyManager`、`BuildManager`、`Ren4Wu4SkuManager`、`RefreshManager`、`TriggerTipManager`

`SweetPotato/EntrustManager.cs`、`SweetPotato/FuBenManager.cs` 也有 `[GameSaveKey]`，是子系統 manager。

## 6. Mod 框架兩條路

| 路徑 | 已配置 | 機制 | 適用情境 |
|---|---|---|---|
| **BepInEx** | ✅ `../BepInEx/`、`../winhttp.dll` doorstop hook | Harmony patch、執行外部 plugin DLL | 任意行為修改、新功能、UI 注入 |
| **Steam Workshop**（官方） | ✅ `WorksShopManager` 在 `AppGame.Start` 被初始化、`GameSaving.ModID { ulong platformModId; bool isNative; int modId }` | 遊戲自帶 mod 框架，從 Workshop 下載 mod 包 | 資料/資產類 mod（要看 mod loader 開放哪些介入點才知道能改什麼） |

下一步應該 **同時調查兩條路徑**，看哪條更符合最終想做的 mod 類型。

## 7. 即時可用的 mod 開發資源（旁路）

- `../MyFirstMod.cs` — 使用者既有的 mod 雛形範本
- `../classes.txt` — 510KB 的型別清單，作為 quick lookup 用
- `../SourceCode/Assembly-CSharp/` — 全部反編譯 .cs，可直接 `grep -rn`
- `../下一站江湖Ⅱ_Data/Managed/Assembly-CSharp.dll` — mod build 要 reference 的目標 DLL

## 8. 後續路徑

- **Level 2**（待）：核心系統職責劃分 — Save/Load 完整流程、AI 系統深入、Workshop mod loader 機制
- 接下來會做的兩個專題：
  1. `details/save_load.md` — 存檔格式、檔案位置、序列化路徑、加密與否
  2. `details/ai_system.md` — AIDialogManager（真 AI）+ NPC 對話/行為決策
