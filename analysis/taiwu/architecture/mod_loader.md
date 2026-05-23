# Level 2：Mod 載入機制分析

> 日期：2026-05-22
> 範圍：完整描繪 mod 從磁碟到掛上 Harmony patch 的流程，並產出可直接拿去寫第一個 mod 的「資料夾結構＋manifest」規格。
> 主要原始碼：`~/dev/taiwu-src/Assembly-CSharp/ModManager.cs`（1680 行）、`~/dev/taiwu-src/Assembly-CSharp/Game.cs`、`~/dev/taiwu-src/TaiwuModdingLib/TaiwuModdingLib/Core/Plugin/PluginHelper.cs`、`~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/*.cs`。

---

## 1. 結論先行：Mod 資料夾骨架

```
<game install>/Mod/
└── MyFirstMod/                       ← 資料夾名 = mod 內部識別碼之一
    ├── Config.Lua                    ★ 必要：Mod manifest（MoonSharp Lua 表）
    ├── Settings.Lua                  選用：玩家側已設定值
    ├── Cover.png                     選用：mod 封面（Config.Lua 內 Cover 欄位指向它）
    ├── Plugins/                      ★ 放主 .dll、相依 .dll、可選 .pdb
    │   ├── MyFirstMod.dll
    │   └── MyFirstMod.pdb            選用：保留即可顯示原始檔名/行號
    ├── LegacyPlugins/                舊版插件（遊戲版本 < 0.0.70 才走這條）
    ├── Config/                       選用：mod 攜帶的 ConfigCell 覆寫資料
    ├── ModResources/
    │   ├── Textures/                 mod 內貼圖（PathKeyTextureGroup）
    │   └── Graphics/                 mod 內圖像（NameKeyTextureGroup）
    └── (其他自帶資產)
```

> 來源：`ModManager.cs:64-68`（常數 `PluginsDirectoryName="Plugins"`, `LegacyPluginsDirectoryName="LegacyPlugins"`, `ConfigDirectoryName="Config"`, `ModConfigFile="Config.Lua"`, `ModSettingsFile="Settings.Lua"`）；`ModManager.cs:723-724`（讀 Config.Lua + Settings.Lua）；`ModManager.cs:1121-1125`（`ModResources/Textures`、`ModResources/Graphics` 自動載入）。

---

## 2. 結論先行：最小 `Config.Lua` 範本

`Config.Lua` 是 **MoonSharp 反序列化得到的 Lua 表**（在 ModManager 內以 `LuaGame.Instance.ReadMoonSharpTable` 讀取，見 `ModManager.cs:188-192`）。常見欄位（自 `ReadModInfoFromTable` 反推，`ModManager.cs:859-1026`）：

```lua
return {
    -- 識別
    Title          = "我的第一個 Mod",
    Source         = 0,              -- 0=External(本地), 1=Steam, 2=DLC （見 ModSource.cs）
    FileId         = 1234567890,     -- Steam 工坊 PublishedFileId；本地時可省略，會自動分配 temp
    Version        = "1.0.0.0",      -- 或直接給 ulong；走 VersionStringToUlong 轉 4×16-bit pack
    GameVersion    = "V0.1.5.0",     -- 對應的遊戲版本，影響 legacy 判定（見 §6）

    -- Plugins（DLL 檔名，相對於 Plugins/）
    FrontendPlugins       = { "MyFirstMod.dll" },    -- Unity 端（UI/前端）
    BackendPlugins        = { },                     -- Backend 端（GameData 執行緒）
    FrontendPluginsLegacy = { },                     -- 同上，舊版相容
    BackendPluginsLegacy  = { },
    FrontendPatches       = { },                     -- 純資料修正描述（用途待查）
    BackendPatches        = { },

    EventPackages         = { },     -- 事件編輯器產出包

    -- 顯示
    Author          = "lorkhan",
    Description     = "示範用 mod。",
    Cover           = "Cover.png",                 -- 相對於此資料夾
    WorkshopCover   = "WorkshopCover.png",
    DetailImageList = { "screen1.png" },
    TagList         = { "Gameplay" },

    -- 相依與環境
    Dependencies                  = { 9876543210 }, -- 其他 mod 的 FileId 清單
    Visibility                    = 0,
    ChangeConfig                  = false,          -- 是否會改 ConfigCell
    HasArchive                    = false,          -- 是否帶存檔資料
    NeedRestartWhenSettingChanged = false,

    -- 玩家可調設定（會被遊戲渲染成 UI）
    DefaultSettings = {
        {
            SettingType = "Toggle",      -- Toggle / ToggleGroup / InputField / Slider / Dropdown
            -- 各 SettingEntry 子型別自己定義欄位（見 FrameWork/ModSystem/）
        },
    },

    UpdateLogList = {
        -- { Version = "1.0.0.0", LogList = { "首版" } },
    },
}
```

> 欄位來源全列：`ModManager.cs:859-1026`（`ReadModInfoFromTable`）對照 `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/ModInfo.cs:22-101`（`ModInfo` 公開欄位）。

---

## 3. 結論先行：最小 C# Plugin 骨架

```csharp
using HarmonyLib;
using TaiwuModdingLib.Core.Plugin;

[PluginConfig("MyFirstMod", "lorkhan", "1.0.0.0")]   // name, creatorId, version
public class Entry : TaiwuRemakeHarmonyPlugin
{
    // 基類已實作 Initialize() → HarmonyInstance.PatchAll(GetType().Assembly)
    // 基類已實作 Dispose()    → HarmonyInstance.UnpatchSelf()
    // 需要時覆寫以下生命週期：
    public override void OnModSettingUpdate()  { /* 玩家動了 mod 設定 */ }
    public override void OnEnterNewWorld()     { /* 開新存檔 */ }
    public override void OnLoadedArchiveData() { /* 存檔資料就緒 */ }
}

// 接著用一般 Harmony pattern 寫 patch
[HarmonyPatch(typeof(SomeGameType), nameof(SomeGameType.SomeMethod))]
internal static class SomeGameType_SomeMethod_Patch
{
    [HarmonyPrefix]
    static bool Prefix(SomeGameType __instance) { /* ... */ return true; }
}
```

**進入點識別規則**（極重要）：見 `PluginHelper.cs:12-26`，遊戲找 plugin 進入點的條件是「`BaseType == TaiwuRemakePlugin` 或 `BaseType == TaiwuRemakeHarmonyPlugin`」——是 **直接基類**，不接受間接繼承。這代表：

- 不要在你的 Entry class 與基類之間插入抽象層。
- 一個 dll 內**只能有一個** plugin 進入點（找到第一個就回傳，見 `GetEntrypointType` 的 foreach 在找到時 return）。
- Entry class 必須是 `public`（用 `assembly.GetExportedTypes()`）。
- Entry class 必須帶 `[PluginConfig(...)]` attribute，否則 `TaiwuRemakePlugin` 的建構子會丟 exception（`TaiwuRemakePlugin.cs:20-23`）。

**Plugin 內部命名規則**：`GetGuid() = "TaiwuRemake.Plugin.{CreatorId}.{PluginName}"`（`TaiwuRemakePlugin.cs:46-49`）。這個字串會作為該 plugin 的 Harmony instance id（見 `TaiwuRemakeHarmonyPlugin.cs:11`），同一個 `{CreatorId, PluginName}` 不要重複。

---

## 4. 啟動序列：mod 何時被載入？

主入口 `Game.cs:234 InitGameRes()` 是個 coroutine，序列摘錄（`Game.cs:236-275`）：

| 步驟 | 動作 |
|---|---|
| 236-238 | `LuaGame` 啟動，等 Lua VM 就緒 |
| 240-242 | `GlobalSettings.LoadSettings()` |
| 245 | `CommandKitBase.Init()`（熱鍵） |
| 249 | `AvatarAtlasAssets.Init()` |
| 253-256 | `DlcManager`、`TextureCenter` 取單例 |
| **257** | **`ModManager.Init()`** |
| 258-259 | `GameObjectCreationUtils.Initialize()` 並等就緒 |
| **260** | **`ModManager.LoadAllEnabledMods()`** |
| 264-273 | 等 `GameDataBridge` 連線（前端 ↔ 後端 IPC） |
| 277-278 | `AvatarManager.InitAvatarCore()` |

→ **Frontend mods 在 GameDataBridge 連線前就已 PatchAll**。因此 mod 在 `Initialize()` 內**不能呼叫**任何需要 backend 資料的 API；要等 `OnEnterNewWorld` 或 `OnLoadedArchiveData` 才能碰存檔狀態。

---

## 5. `ModManager.Init()` → 掃 mod → 載入的完整流程

```
Game.InitGameRes()
   │
   ├── ModManager.Init()                                     [ModManager.cs:134]
   │     ├── 配置內部容器（_localMods、EnabledMods、_loadedPlugins…）
   │     ├── InitPath()                                      [ModManager.cs:1403]
   │     │     └── _workingModName = PlayerPrefs.GetString("LastWorkingModName", "FirstMod")
   │     └── UpdateModList()                                 [ModManager.cs:176]
   │           ├── SteamManager.ReadSubscribedItems(...)     ← Steam 工坊已訂閱
   │           ├── 讀 <Archive>/ModSettings.Lua（全域啟用狀態）
   │           │     ├─ 找不到：直接 ReadLocalMods()
   │           │     └─ 找得到：LoadEnabledModsFromLuaTable() → ReadLocalMods()
   │           └── ReadLocalMods()                           [ModManager.cs:714]
   │                 ├── 列舉 GetModRootFolder() 下的所有子目錄
   │                 ├── 對每個 dir：讀 Config.Lua + Settings.Lua → ReadModInfo()
   │                 │     └─ 無 Config.Lua 的資料夾直接跳過
   │                 └─ 結果寫入 _localMods 與 ExternalMods
   │
   └── ModManager.LoadAllEnabledMods()                       [ModManager.cs:562]
         ├── UnloadAllMods()  ← 安全起見先卸載
         ├── HandleDependencyOrder(modId)  ← DFS 依 Dependencies 排序
         └── foreach ordered modId:
               LoadMod(modInfo)                              [ModManager.cs:1109]
                 ├── _modConfigDataManager.LoadModConfig(modInfo)
                 ├── TextureCenter.LoadTextureGroupFromPath<PathKeyTextureGroup>(
                 │     "ModTexture_" + modId,
                 │     <modDir>/ModResources/Textures)
                 ├── TextureCenter.LoadTextureGroupFromPath<NameKeyTextureGroup>(
                 │     "ModGraphicsTexture_" + modId,
                 │     <modDir>/ModResources/Graphics)
                 └── foreach pluginName in modInfo.FrontendPlugins:
                       pluginInstance = PluginHelper.LoadPlugin(
                          <modDir>/Plugins, pluginName, modIdStr)
                       └─ PluginHelper.LoadPlugin                [PluginHelper.cs:28]
                            ├── File.ReadAllBytes(<dir>/<dll>) + 可選 .pdb
                            ├── Assembly.Load(rawAssembly, rawSymbolStore?)
                            ├── 對 GetReferencedAssemblies()：
                            │     若 <dir> 內有同名 dll → 也 Load 進來
                            │     ★這是相依 dll 的標準放法
                            ├── GetEntrypointType(assembly)      ← BaseType 比對
                            ├── Activator.CreateInstance(entrypointType)
                            ├── plugin.ModIdStr = modIdStr
                            └── plugin.Initialize()              ← Harmony.PatchAll(assembly)
                     plugin.OnModSettingUpdate()  ← 灌入玩家當前的設定
                       _loadedPlugins[modId].Add(plugin)
```

**路徑常數**：
- Mod 根目錄：`<Application.dataPath>/..` + `Mod/`，即 `<遊戲安裝>/Mod/`（`GetModRootFolder` 見 `ModManager.cs:1397`）。在你的環境就是 `/home/lorkhan/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/Mod/`。
- Mod 工廠根目錄（in-game 編輯器用）：`<安裝>/ModFactory/<workingModName>/WorkSpace/...`（`GetModFactoryRootFolder` 見 `ModManager.cs:1423`）。

---

## 6. Frontend vs Backend：兩條獨立載入鏈

Mod 同時支援 **frontend plugin** 與 **backend plugin** 兩種：

| 類別 | 載入位置 | 適合做的事 |
|---|---|---|
| **FrontendPlugins** | Unity 主執行緒（`ModManager.LoadMod` 內呼叫 `PluginHelper.LoadPlugin`，見 `ModManager.cs:1126-1133`） | UI、輸入、貼圖、Unity 物件操作、任何 `UnityEngine.*` API |
| **BackendPlugins** | 後端執行緒（`GameData/GameDataBridge/` 之另一側，本層 Assembly-CSharp 不直接載；推測載入位於 `Encyclopedia.dll` 或反編譯中尚未涵蓋的 backend 程式），透過 `VnPipe` 與前端 IPC | 純資料/規則邏輯：戰鬥計算、屬性、AI、事件處理 |

**重要實作細節**：
- `BackendPlugins` 的 manifest 欄位、`ModInfo.BackendPlugins`、序列化都齊全，但 Assembly-CSharp 內找不到呼叫 `PluginHelper.LoadPlugin(...BackendPlugins...)` 的點（全文 grep `BackendPlugins` 僅見於 ModManager 讀/寫 manifest、UI_ModPanel、ModInfo 序列化）。
- 結論：backend plugin 載入點在 GameData 端（另一個 .NET assembly，可能是 `Encyclopedia.dll` 或 backend 自帶 runtime）。要做 backend mod 之前需再反編譯 `Encyclopedia.dll` 並追蹤該端的對應 `LoadPlugin` 呼叫。**這列為 Level 3 待辦**。
- 對第一個 mod，建議**只用 FrontendPlugins**——比較單純，且大部分 UI/視覺改動就足夠。

**Legacy 機制**（`ModManager.cs:295-339` `IsModUseLegacy`、`ParseGameVersion`）：
- 若 manifest 的 `GameVersion < CutVersion (0.0.70)`，或主版號/次版號不同，遊戲會走 `*PluginsLegacy` 路徑（從 `../LegacyPlugins/` 載 dll，見 `GetLegacyPluginsPathList` `ModManager.cs:1320`）。
- 新寫 mod 時把 `GameVersion` 寫成當前遊戲版本，正常用 `Plugins/`，**不要碰** `LegacyPlugins/`。

---

## 7. ModId 的真實組成

```csharp
// GameData/Domains/Mod/ModId.cs:6
public struct ModId(ulong fileId, ulong version, byte source)
{
    public ulong FileId;     // Steam 工坊 PublishedFileId，本地時是自動分配的 uint
    public ulong Version;    // 4×16-bit packed (Major/Minor/Build/Revision)
    public byte  Source;     // 0=External, 1=Steam, 2=DLC  (ModSource.cs)
    public override string ToString() => $"{Source}_{FileId}";
}
```

ToString 出來形如 `0_1234567890`（本地）或 `1_2345678901`（Steam 工坊）。`ModManager` 內以 `modId.ToString()` 當作 `_localMods` 的字典 key、和 mod 貼圖群組的 key（`GetTextureGroupKey()` 回 `"ModTexture_" + modId`）。

**本地 mod 不需要在 Config.Lua 寫 `FileId`**：`ModManager.cs:870-903` 處理三種情況：
1. 手動帶 initModId 旗標 → 一律建 temp ModId。
2. Config.Lua 有 `FileId` 且 `Source=0`：檢查衝突，重複/為 0 則重建 temp ModId。
3. Config.Lua 完全沒 `FileId` 且 `loadOnRead`：呼叫 `CreateTempModId(modName)`（`ModManager.cs:697`），從 1 開始找一個沒被佔用的 ulong。

→ 本地開發時 Config.Lua 可不寫 `FileId`；遊戲首次掃描會幫你補上並存回。

---

## 8. 設定（Settings.Lua）與 mod 內 UI

- `Config.Lua` 內的 `DefaultSettings = { {SettingType="Toggle",...}, ... }` 會在 `ReadModInfoFromTable` 階段被反序列化成具體 `SettingEntry` 子類（見 `ModManager.cs:982-1012` 的 switch）：
  - `"Toggle"` → `ToggleSetting`
  - `"ToggleGroup"` → `ToggleGroupSetting`
  - `"InputField"` → `InputFieldSetting`
  - `"Slider"` → `SliderSetting`
  - `"Dropdown"` → `DropdownSetting`
  - 其他值會丟 `InvalidOperationException("Invalid Mod Setting Type")`。
- 玩家在 UI 改完設定後寫到 `<modDir>/Settings.Lua`（檔名見 `ModSettingsFile = "Settings.Lua"`）；下一次 `ReadModInfo` 會把 settings 蓋到 `modInfo`，並呼叫 `modInfo.ApplySettings()`（`ModManager.cs:835-855`）。
- Runtime 中玩家改設定 → `UpdateModSettingsInGame(modId)`（`ModManager.cs:631`）：對該 mod 已載入的每個 plugin 呼叫 `OnModSettingUpdate()`，並透過 `ModDomainHelper.MethodCall.UpdateModSettings` 同步到 backend。
- 程式內讀單一設定：`ModManager.GetSetting(modIdStr, settingName, ref val)`（`ModManager.cs:1391`）。

→ 第一個 mod 若只是 PoC，可以**完全不放 `DefaultSettings`**，等需要時再加。

---

## 9. 相依性（Dependencies）

- `Config.Lua` 內 `Dependencies = { <FileId1>, <FileId2>, ... }`，使用其他 mod 的 `FileId`（ulong）作為相依識別。
- `LoadAllEnabledMods` 內以 DFS 把每個 mod 的相依先壓進 queue 才壓自己（`ModManager.cs:591-613` 的 `HandleDependencyOrder`），確保載入順序。
- 注意：相依 mod 必須**已啟用**（在 `EnabledMods` 內）才會排序；沒啟用就被略過、不會自動啟用相依。
- **DLL 級相依**（你 mod 的 dll 引用另一個 dll）走另一條路：`PluginHelper.LoadPlugin` 會掃 `assembly.GetReferencedAssemblies()`，在**同一個 Plugins 目錄**內找同名 dll 並 `Assembly.Load`。所以小型相依直接打包進自己的 `Plugins/` 即可，不必走 mod-level dependency。

---

## 10. Steam Workshop 整合

`ModManager` 與 `SteamManager`（在 `SteamManager` 類別中）緊密整合：
- `UpdateModList()` 開頭就呼叫 `SteamManager.ReadSubscribedItems(PlatformMods, _localMods)`（`ModManager.cs:181`）。
- `SubscribeItem(modId)`：`SteamUGC.SubscribeItem` + `DownloadItem`（`ModManager.cs:1187`）。
- `SyncCoverLocalMod`：把工坊下載到的資料夾複製到本地 `<Mod>/<title>/` 並重讀 Config.Lua（`ModManager.cs:1247-1318`）。
- 上傳：`DeleteUploadedMod` 等顯示官方有完整 publish/sync workflow，但本份分析不展開。

→ **本地開發**：完全不必碰 Steam，直接放在 `<安裝>/Mod/MyFirstMod/` 即可。

---

## 11. 啟用狀態與存檔

全域啟用狀態存於：

```
<Archive>/ModSettings.Lua
```

`<Archive>` 由 `Game.GetArchiveDirPath()` 提供（推測位於 `<安裝>/StreamingAssets/..` 或 OS 標準存檔路徑，未深挖）。其格式由 `LoadEnabledModsFromLuaTable`（`ModManager.cs:342`）讀。

`SaveModSettings()` 在每次啟用/停用 mod、刪除、同步工坊後被呼叫。

存檔層面：
- `ModInfo` 自己是 `ISerializableGameData`，會被序列化進存檔（`ModInfo.cs` 內 `Serialize/Deserialize`）。
- `WorldInfo.ModIds` 紀錄該存檔啟用過的 mod 清單。`ModManager.CheckModDiff(worldInfo, removed, newEnabled)`（`ModManager.cs:1171`）比對：存檔有但目前沒載入 → `removedMods`；目前載入但存檔沒紀錄 → `newEnabledMods`。
- `HasArchive=true` 的 mod 表示「我會塞自己的資料進存檔」。

→ **第一個 mod 把 `HasArchive=false` 即可**，避免要實作 mod 自己的 serializer。

---

## 12. 失敗模式（給 mod 開發者排錯用）

- Config.Lua 解析失敗 → `AdaptableLog.AppendPredefinedWarning(2, ...)`，**該 mod 被完全略過**（`ModManager.cs:813-816`）。
- 進入點型別找不到 → `PluginHelper.LoadPlugin` 拋 `Exception("Failed to create entrypoint instance...")`，**該 plugin 不載入但其他 plugin 還會繼續**。
- `LoadMod` 任一 plugin 出錯 → catch 後印 LogError、把該 mod 從 `EnabledMods` 移除、`SaveModSettings()`、**整個迴圈 break**（`ModManager.cs:580-587`）。**這代表一個壞 mod 會擋掉它後面所有 mod 的載入**，排序錯誤要小心。
- 設定型別字串不在 5 種白名單 → `InvalidOperationException("Invalid Mod Setting Type")`，整個 ReadModInfo 失敗（mod 被略過）。
- `[PluginConfig]` 沒帶 → `TaiwuRemakePlugin` 建構子直接拋（`TaiwuRemakePlugin.cs:20-23`），plugin 該 dll 不載入。

排錯日誌：遊戲標準輸出（Linux 通常在 `~/.config/unity3d/...Player.log`），ModManager 內大量 `Debug.Log`/`Debug.LogError`，搜 `"Start loading mod"`、`"Loading - "`、`"Total N mods loaded"`。

---

## 13. 「Hello, Taiwu」最短可運作 mod（給後續實作參考）

**檔案結構**：

```
Mod/HelloTaiwu/
├── Config.Lua
└── Plugins/
    └── HelloTaiwu.dll
```

**Config.Lua**：

```lua
return {
    Title = "Hello Taiwu",
    Source = 0,
    Version = "1.0.0.0",
    GameVersion = "V0.1.5.0",        -- ⚠ 上線前需確認當下實際版本
    Author = "lorkhan",
    Description = "PoC mod。",
    FrontendPlugins = { "HelloTaiwu.dll" },
    BackendPlugins = { },
    FrontendPluginsLegacy = { },
    BackendPluginsLegacy = { },
    FrontendPatches = { },
    BackendPatches = { },
    EventPackages = { },
    TagList = { "Test" },
    Dependencies = { },
    ChangeConfig = false,
    HasArchive = false,
    NeedRestartWhenSettingChanged = false,
    DefaultSettings = { },
    UpdateLogList = { },
}
```

**HelloTaiwu.cs**（編譯成 HelloTaiwu.dll，target `netstandard2.1` 或 Unity 對應，引用 `0Harmony.dll` + `TaiwuModdingLib.dll` + `Assembly-CSharp.dll`）：

```csharp
using HarmonyLib;
using TaiwuModdingLib.Core.Plugin;
using UnityEngine;

namespace HelloTaiwu;

[PluginConfig("HelloTaiwu", "lorkhan", "1.0.0.0")]
public class Entry : TaiwuRemakeHarmonyPlugin
{
    public override void OnEnterNewWorld()
    {
        Debug.Log("[HelloTaiwu] OnEnterNewWorld 觸發");
    }
}
```

期待行為：載入時遊戲日誌出現 `Start loading mod Hello Taiwu for frontend ...`、`Total N mods loaded`；玩家開新存檔時 Player.log 多一行 `[HelloTaiwu] OnEnterNewWorld 觸發`。

---

## 14. 對 Level 1 待釐清項的回應

| Level 1 待釐清 | 本份結果 |
|---|---|
| `ModManager.cs` 完整載入流程 | §5 已畫出完整流程圖 |
| Mod/ 資料夾標準結構 | §1 明確列出 |
| metadata 檔格式 | §2，是 `Config.Lua`（MoonSharp Lua 表） |
| 相依性處理 | §9（mod 級 + dll 級 雙軌） |
| `UI_ModPanel.cs` 行為 | 確認其只是管理 UI（呼叫 `UpdateModList`/`LoadAllEnabledMods`），不參與載入邏輯，本份不深入 |
| MoonSharp Lua 是否給 mod 用 | 確認用於**讀 manifest 與 settings**，不是 mod 腳本沙箱（mod 腳本沙箱可能由 `FrameWork/ModSystem/LuaTableExtensions` / `MoonSharpTableExtensions` 暴露，留 Level 3） |
| `ModConfigDataManager` 與 `ConfigDataModificationUtils` 分工 | 已定位但本份未深挖：`LoadMod` 內呼 `_modConfigDataManager.LoadModConfig(modInfo)`（`ModManager.cs:1119`），具體做什麼留 Level 3 |
| Steam 工坊整合 | §10 已釐清，工坊與本地 `Mod/` 並存 |

---

## 15. Level 2 留下的待辦（→ Level 3）

- [ ] **Backend plugin 載入點**：在 `Encyclopedia.dll` 或 backend 端 assembly 找對應 `LoadPlugin` 呼叫；釐清 frontend/backend 間如何透過 `VnPipe` 通訊。
- [ ] **`ModConfigDataManager.LoadModConfig` 細節**：mod 怎麼覆寫 `ConfigCells`？是直接讀 `<modDir>/Config/` 還是另一條路？
- [ ] **`ConfigDataModificationUtils`** 對外 API：mod 在 runtime 改 ConfigCell 的標準呼叫方式。
- [ ] **MoonSharp 腳本沙箱**：`LuaTableExtensions` / `MoonSharpTableExtensions` 是給遊戲內部用還是給 mod 用？是否有「純 Lua mod」一條路。
- [ ] **`GetArchiveDirPath()`**：玩家存檔實際路徑。
- [ ] **AssetBundle 加載**：`FrameWork/AssetBundlePackage/` + `Mod/<x>/ModResources/` 之外 mod 是否能塞 AssetBundle？
- [ ] **Event System**：mod 顯然能透過 `EventPackages` 注入事件，與 `EventEditor/`、`EventScript/` 配合，留 Level 3 專題。

---

## 參考檔案

- `~/dev/taiwu-src/Assembly-CSharp/ModManager.cs`（全文）
- `~/dev/taiwu-src/Assembly-CSharp/Game.cs:234-275`
- `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/ModInfo.cs`
- `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/ModId.cs`
- `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/ModSource.cs`
- `~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Mod/ModConfigDataManager.cs`（淺嘗）
- `~/dev/taiwu-src/Assembly-CSharp/FrameWork/ModSystem/SettingEntry.cs` 系列
- `~/dev/taiwu-src/TaiwuModdingLib/TaiwuModdingLib/Core/Plugin/*.cs`（全部）
