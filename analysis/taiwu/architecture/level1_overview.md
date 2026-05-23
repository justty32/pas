# Level 1：太吾繪卷整體架構初探

> 日期：2026-05-22
> 範圍：對 `~/dev/taiwu-src/` 反編譯產物做命名空間分佈、入口點、依賴與架構模式的全景掃描。
> 目標：為後續 Mod 開發（Level 2 起）建立可信的「地圖」。

---

## 1. 遊戲與檔案結構

- **遊戲名稱**：The Scroll of Taiwu（太吾繪卷）
- **引擎**：Unity（依 `UnityPlayer.dll`、MonoBehaviour 數量、`UnitySourceGeneratedAssemblyMonoScriptTypes_v1.cs` 判斷）
- **安裝位置**：`/home/lorkhan/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/`
- **核心 Managed 組件**（位於 `…/The Scroll of Taiwu_Data/Managed/`）：

| Assembly | 角色 | 反編譯位置 |
|---|---|---|
| `Assembly-CSharp.dll` (22 MB) | 主要遊戲邏輯 | `~/dev/taiwu-src/Assembly-CSharp/` (2738 .cs) |
| `Assembly-CSharp-firstpass.dll` (116 KB) | 第三方/編譯前置（DG 系列、SoftMasking 等） | `~/dev/taiwu-src/Assembly-CSharp-firstpass/` (28 .cs) |
| `TaiwuModdingLib.dll` | **官方 Mod API** | `~/dev/taiwu-src/TaiwuModdingLib/` (6 .cs) |

> 所有反編譯均以 `ilspycmd -p --nested-directories -usepdb` 產出，PDB 變數名保留。

---

## 2. 主要命名空間（依檔案數）

Assembly-CSharp 的頂層分佈如下：

| 目錄 | .cs 檔數 | 角色 |
|---|---:|---|
| `(root)` | 1010 | UI 控制器、根層 MonoBehaviour、入口點 |
| `GameData/` | 821 | **領域層**（DDD 風格，見 §5） |
| `Config/` | 485 | 設定資料表、ConfigCell 系列 |
| `FrameWork/` | 87 | 引擎級基礎設施（含 **`ModSystem/`**） |
| `XLua/` | 63 | XLua 綁定（Lua 腳本層） |
| `EventEditor/` | 53 | 事件編輯器工具 |
| `UICommon/` | 50 | 共用 UI 元件 |
| `AiEditor/` | 42 | AI 行為樹編輯器 |
| `CharacterDataMonitor/` | 24 | 角色資料監看（開發/除錯） |
| `AdventureEditor/` | 22 | 「歷練」（Adventure）模組編輯器 |
| `GearMate/`、`UISkillBreakPlate/`、`GM/`、其他 | <20 | 各小型子系統 |

**重點觀察**：
- `GameData/` 與 `Config/` 兩者加起來 ≈ 1300 個檔案，佔比約一半，顯示遊戲是「資料/規則密集」型態。
- root 層特別肥（1010 檔），大量 `UI_*.cs` 與 controller 散在頂層。前 20 大檔幾乎都是 UI（`UI_Combat.cs` 280 KB、`UI_BuildingManage.cs` 210 KB、`UI_ModPanel.cs` 120 KB 等）與 `LanguageKey.cs`（825 KB，i18n key 常數）。
- 存在 `EventEditor/`、`AiEditor/`、`AdventureEditor/` 三個編輯器 → 官方在執行檔內留了內部編輯工具，這對逆向理解資料模型非常有幫助。

---

## 3. 第三方依賴（重要）

`Managed/` 中非系統 DLL 摘要：

| DLL | 用途 | 對 Mod 開發的意義 |
|---|---|---|
| **`0Harmony.dll`** | Harmony runtime patching | **核心**：mod 用來 patch 任意方法 |
| **`MonoMod.RuntimeDetour.dll`** / `MonoMod.Utils.dll` | 與 Harmony 共生的 detour 後端 | 由 Harmony 使用 |
| **`TaiwuModdingLib.dll`** | 官方 Plugin 基類 | **必須**：mod 入口要繼承這裡的型別 |
| `Mono.Cecil.*` | IL 操作 | Harmony 底層依賴 |
| **`XLua.dll`**（推測，對應 `XLua/` 命名空間） | Lua scripting（Unity 主流方案） | 遊戲內部腳本 |
| **`MoonSharp.Interpreter.dll`** | 另一個 Lua 直譯器 | 可能是給 mod 用的沙箱 Lua |
| `Newtonsoft.Json.dll` | JSON 序列化 | 設定/存檔/Mod manifest 候選 |
| **`NPOI.dll`** + `NPOI.OOXML.*` | 讀寫 Excel | 暗示開發時用 Excel 出表 |
| `DOTween.dll` / `DOTweenPro.dll` / `DemiLib.dll` | Tween 動畫 | UI 動畫 |
| `spine-csharp.dll` / `spine-unity.dll` | Spine 2D 骨骼動畫 | 角色立繪 |
| `Steamworks.NET.dll` + `steam_api64.dll` | Steam SDK | 成就、創意工坊（?） |
| `SingularityGroup.HotReload.*` | C# Hot Reload | 開發期熱重載，**正式版仍含**，可作為 mod debug 入口 |
| `Coffee.SoftMaskForUGUI.dll` / `Coffee.UIParticle.dll` | UGUI 擴充 | UI |
| `ICSharpCode.SharpZipLib.dll` | Zip 解壓 | 資產或存檔解壓 |
| `EasyButtons.dll` | Inspector 工具 | 開發/除錯 |
| `CompDevLib.Interpreter.dll` | 自製/第三方 DSL 直譯器 | 待確認 |
| `Encyclopedia.dll` | 名稱類似遊戲百科子模組 | 待 Level 2 確認 |

**最重要訊號**：`TaiwuModdingLib.dll` + `0Harmony.dll` + `MoonSharp.Interpreter.dll` 三者並存，顯示官方支援的 mod 路線有 **C#（Harmony patching）** 與 **Lua（MoonSharp 沙箱）** 兩條。

---

## 4. 遊戲入口點

主入口位於 `~/dev/taiwu-src/Assembly-CSharp/Game.cs`：

```csharp
// Game.cs:24
public class Game : MonoBehaviour
{
    // Game.cs:39
    public static Game Instance;

    // Game.cs:105
    private void Awake() { ... Instance = this; ... }

    // Game.cs:125
    private void Start() { ... }

    // Game.cs:413
    public void ChangeGameState(EGameState newState, ArgumentBox argsBox = null) { ... }
}
```

對應狀態機（`~/dev/taiwu-src/Assembly-CSharp/EGameState.cs`）：

```csharp
public enum EGameState
{
    None, Login, NewGame, Loading, InGame, Adventure
}
```

`Game.Start()` 中可看到的關鍵初始化序列（節錄自 Game.cs:125 起）：

- `SensitiveWordsSystem.Instance.Init()`（敏感字過濾）
- `AtlasInfo.Instance` 等待就緒
- `SingletonObject.getInstance<DlcManager>()`（DLC 系統）
- `SingletonObject.getInstance<TextureCenter>()`
- `SingletonObject.getInstance<AvatarManager>()`（角色立繪）
- `LuaGame.Instance = new LuaGame(); LuaGame.Instance.LuaStart();`（Game.cs:236-237，**Lua 子系統啟動**）

**重要架構慣例**：`SingletonObject.getInstance<T>()` 是統一的單例容器（出現在主入口、UIManager、AudioManager 等多處），不同於每個類各自寫 `static Instance`。這意味著 mod 想要取得任意子系統實例，幾乎都能用這個入口。

---

## 5. 領域層：`GameData/Domains/`

`GameData/Domains/` 採用近似 DDD（Domain-Driven Design）的目錄組織。子領域：

```
Adventure        歷練系統（遊歷、事件鏈）
Building         建築（門派建設）
Character        角色（屬性、外觀、AvatarSystem）
Combat           戰鬥
CombatSkill      戰鬥技能
Extra            雜項
Global           全域狀態
Information      資訊/情報
Item             物品
LegendaryBook    傳奇之書（成就/名冊）
LifeRecord       人生紀錄
Map              地圖
Merchant         商人
Mod              **Mod 資料層**（含 ModConfigDataManager.cs）
Organization     門派/勢力
SpecialEffect    特殊效果
Taiwu            太吾本人（主角專屬狀態）
TaiwuEvent       事件系統（劇情/隨機事件）
TutorialChapter  教學章節
World            世界狀態
```

每個 Domain 是相對獨立的子目錄，內部通常包含資料模型、Manager、Helper 等。這個切分對 Mod 非常友善：要改某個系統，幾乎可以從對應 Domain 入手再向外追。

**特別注意 `GameData/Domains/Mod/`**：裡面的 `ModConfigDataManager.cs` 是 mod 改寫遊戲設定資料（ConfigCell）的中央入口，預期會與 `FrameWork/ModSystem/ConfigDataModificationUtils.cs` 一起使用。Level 2 會深入。

---

## 6. 設定資料層：`Config/`

```
Config/
├── Common/         共用設定型別
└── ConfigCells/    具體資料表（按領域分子目錄，含 Character/ 等）
```

`ConfigCells/` 是遊戲的「靜態資料表」，配合 `NPOI.dll`（Excel 讀寫）強烈暗示原始資料以 Excel 維護、運行期載入。Mod 改設定（屬性、技能數值、物品數據）的目標多半落在這裡，搭配 `ConfigDataModificationUtils` 動態替換。

---

## 7. 框架層：`FrameWork/`

`~/dev/taiwu-src/Assembly-CSharp/FrameWork/` 共 87 檔，是引擎級基礎設施：

```
AssetBundlePackage/     資產包載入
CommandSystem/          指令系統
Component/              通用元件
ExternalTexture/        外部貼圖（mod 換貼圖的候選入口）
Linq/                   LINQ 擴充
ModSystem/              ★ Mod 子系統
ResManager/             資源管理
Tools/                  工具
UISystem/               UI 系統
AsyncJobSystem.cs       非同步任務
DelayCaller.cs          延遲呼叫
EasyPool.cs             物件池
InternalDlc*.cs         DLC 基礎
```

`FrameWork/ModSystem/` 內容（11 檔）：

```
ConfigDataModificationUtils.cs   修改 ConfigCell 資料的工具
DataMonitorComponent.cs          資料監看元件
SettingEntry.cs                  Mod 設定條目（base）
DropdownSetting.cs               ↑ Dropdown 設定型
InputFieldSetting.cs             ↑ 輸入框
SliderSetting.cs                 ↑ 滑桿
ToggleSetting.cs                 ↑ 開關
ToggleGroupSetting.cs            ↑ 群組開關
ISettingValueWrapper.cs          設定值介面
LuaTableExtensions.cs            XLua 表擴充
MoonSharpTableExtensions.cs      MoonSharp 表擴充
GameObjectCreationUtils.cs       建立 GameObject 工具
```

→ 官方為 mod 預備了完整的「設定 UI」框架，mod 可以自帶可調參數，遊戲會渲染對應的 UI。

---

## 8. 官方 Mod API：`TaiwuModdingLib.dll`

完整檔案清單（`~/dev/taiwu-src/TaiwuModdingLib/TaiwuModdingLib/Core/`）：

```
Plugin/
├── PluginConfig.cs              [Attribute] 標註 Name/CreatorId/Version
├── PluginInfo.cs                internal 載入器（讀 dll、Activator.CreateInstance、呼 Initialize）
├── PluginHelper.cs              工具
├── TaiwuRemakePlugin.cs         抽象基類（純 C# plugin）
└── TaiwuRemakeHarmonyPlugin.cs  繼承 TaiwuRemakePlugin，包 HarmonyInstance
Utils/
└── ReflectionExtensions.cs      反射輔助
```

**Plugin 生命週期介面**（`TaiwuRemakePlugin.cs:30-43`）：

```csharp
public abstract void Initialize();          // 啟動
public abstract void Dispose();             // 卸載
public virtual void OnModSettingUpdate();   // 玩家在 UI 改 mod 設定時呼叫
public virtual void OnEnterNewWorld();      // 進入新存檔
public virtual void OnLoadedArchiveData();  // 存檔資料載入完成
```

**標準 Harmony Plugin 骨架**（`TaiwuRemakeHarmonyPlugin.cs`）：

```csharp
public abstract class TaiwuRemakeHarmonyPlugin : TaiwuRemakePlugin
{
    public Harmony HarmonyInstance { get; }

    public TaiwuRemakeHarmonyPlugin()
    {
        HarmonyInstance = new Harmony(GetGuid());  // Guid = "TaiwuRemake.Plugin.{CreatorId}.{PluginName}"
    }

    public override void Initialize()
    {
        HarmonyInstance.PatchAll(GetType().Assembly);  // 自動掃所有 [HarmonyPatch]
    }

    public override void Dispose()
    {
        HarmonyInstance.UnpatchSelf();
    }
}
```

**Mod 載入流程（推測，待 Level 2 確認）**：
1. 遊戲掃 `Mod/` 子資料夾
2. 對每個資料夾，找其中 `.dll`（檔名規則待查）
3. `PluginInfo.Load()` ＝ `File.ReadAllBytes` → `Assembly.Load(bytes)` → `PluginHelper.GetEntrypointType` 找帶 `[PluginConfig]` attribute 的 class → `Activator.CreateInstance` → `Initialize()`
4. 載入後存於 ModManager（root 1680 行的 `ModManager.cs`）

---

## 9. 統計小結

| 指標 | 數值 |
|---|---:|
| Assembly-CSharp 總 .cs 檔 | 2738 |
| MonoBehaviour 子類（粗估，`^public class.*: MonoBehaviour`） | 174 |
| 一般 public class 總數 | 2285 |
| 比例（MonoBehaviour / 總類別） | ~7.6% |

→ 絕大多數類別是純資料/邏輯類；MonoBehaviour 集中在 UI 與少數系統元件。對 Harmony patching 而言，**目標方法多半是純 C# 方法**（非 Unity 訊息），patch 成功率與穩定度都會比較高。

---

## 10. 對 Mod 開發的初步結論

1. **首選技術路線**：繼承 `TaiwuRemakeHarmonyPlugin` 寫 C# mod，配合 `[HarmonyPatch]` patch 想改的方法。
2. **第二路線**：透過 `ConfigDataModificationUtils` 改 `ConfigCells/` 資料表（純資料 mod，無需 patch）。
3. **第三路線**：Lua 腳本（MoonSharp 沙箱），可能適合輕量化或不想出 dll 的 mod。
4. **必備設定 UI**：用 `FrameWork/ModSystem/SettingEntry` 系列暴露玩家可調參數。
5. **資料層切入點**：絕大多數想改的功能都可從 `GameData/Domains/<領域>/` 找到對應 Manager。
6. **不要碰**：`SingularityGroup.HotReload.*` 是開發期工具，正式 mod 不該依賴。

---

## 11. 待釐清項（→ Level 2）

- [ ] `ModManager.cs`（root, 1680 行）的完整載入流程：什麼時候掃 `Mod/`、有沒有 mod metadata 檔（`mod.json` 之類）、相依性如何處理。
- [ ] `Mod/` 資料夾的標準結構（單 dll？多 dll？子資料夾命名規則？）
- [ ] `UI_ModPanel.cs`（120 KB）對應的 mod 管理 UI 行為。
- [ ] `MoonSharp` Lua 路線是否真給 mod 用，還是只是內建腳本。
- [ ] `ModConfigDataManager.cs`（GameData/Domains/Mod/）與 `ConfigDataModificationUtils.cs`（FrameWork/ModSystem/）的職責分工。
- [ ] Steam 創意工坊整合（`Steamworks.NET.dll` 有，但 mod 載入用本地 `Mod/` 還是工坊？）

---

## 參考檔案（本份報告引用）

- `~/dev/taiwu-src/Assembly-CSharp/Game.cs`
- `~/dev/taiwu-src/Assembly-CSharp/EGameState.cs`
- `~/dev/taiwu-src/Assembly-CSharp/ModManager.cs`（未深入，留 Level 2）
- `~/dev/taiwu-src/Assembly-CSharp/FrameWork/ModSystem/` 全資料夾
- `~/dev/taiwu-src/TaiwuModdingLib/TaiwuModdingLib/Core/Plugin/*.cs` 全部
- `/home/lorkhan/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/The Scroll of Taiwu_Data/Managed/` 的 DLL 清單
