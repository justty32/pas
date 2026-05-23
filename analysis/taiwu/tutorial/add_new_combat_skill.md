# 教學：為《太吾繪卷》新增一個武功（Linux 開發環境）

> 日期：2026-05-22
> 對象：已讀過 [mod 解剖](../details/martial_arts_mod_anatomy.md) 與 [Config/YAML 規格](../details/config_lua_schema.md) 的開發者。
> 目標：從零做出一個「能在遊戲裡學到、開戰會生效」的新武功 mod，並在本地 `Mod/` 跑起來。
> 平台：Manjaro Linux（遊戲透過 Steam/Proton 跑），.NET SDK 已裝。

---

## 0. 心智模型（一定要先懂）

《太吾繪卷》是 **雙進程**：
- **前端**（Unity，`.NET Framework 4.8` / Mono）：UI、顯示。
- **後端**（獨立 `.NET 6` 進程 `GameData.exe`）：所有戰鬥與遊戲規則。

所以一個武學 mod 要出 **兩個 dll**，**target framework 不同**：

| | Target | 引用來源 | 職責 |
|---|---|---|---|
| Backend dll | **net6.0** | `<遊戲>/Backend/*.dll` | 武功特效的戰鬥邏輯、容量擴張 patch、過月送武功 |
| Frontend dll | **net48** | `<遊戲>/.../Managed/*.dll` | 讓前端 UI 認得新武功（載同一份 YAML） |

兩邊都讀**同一份** `CombatSkills.yml` + `SpecialEffects.yml`（各自進程有自己的 config 單例）。

---

## 1. 專案結構

建議在 `~/repo/pas/projects/taiwu/` 下開你自己的 mod 專案：

```
MySwordMod/
├── MySwordMod.sln
├── Backend/
│   ├── MySwordMod.Backend.csproj
│   ├── Plugin.cs                 # backend 入口 + 容量 patch
│   ├── DataConfigAppender.cs     # 直接從參考 mod 抄
│   ├── DataConfigAppenderHelpers.cs
│   └── Effects/
│       └── MySwordIntent.cs      # 你的特效類別
├── Frontend/
│   ├── MySwordMod.Frontend.csproj
│   └── Plugin.cs                 # frontend 入口（只載 YAML）
└── dist/                         # 打包輸出 → 複製到遊戲 Mod/
    ├── Config.Lua
    ├── CombatSkills.yml
    ├── SpecialEffects.yml
    └── Plugins/
        ├── MySwordMod.Backend.dll
        ├── MySwordMod.Frontend.dll
        └── YamlDotNet.dll
```

> `DataConfigAppender.cs` / `DataConfigAppenderHelpers.cs` 直接從
> `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/` 抄過來改命名空間即可——它們是乾淨可複用的框架（解剖報告 §5 已證）。
> 反編譯產物會有 `//IL_xxxx` 註解與 `((DefaultInterpolatedStringHandler)...)` 這種還原痕跡，抄過來時清理成正常 C#。

---

## 2. Backend .csproj

`Backend/MySwordMod.Backend.csproj`（路徑依你的實際安裝調整 HintPath）：

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>MySwordMod.Backend</AssemblyName>
    <GenerateAssemblyInfo>False</GenerateAssemblyInfo>
    <TargetFramework>net6.0</TargetFramework>
    <PlatformTarget>x64</PlatformTarget>
    <LangVersion>14.0</LangVersion>
    <AllowUnsafeBlocks>True</AllowUnsafeBlocks>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
  </PropertyGroup>

  <!-- 後端 dll 全來自 <遊戲>/Backend/ -->
  <PropertyGroup>
    <BK>$(HOME)/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/Backend</BK>
    <MG>$(HOME)/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/The Scroll of Taiwu_Data/Managed</MG>
  </PropertyGroup>

  <ItemGroup>
    <Reference Include="GameData">              <HintPath>$(BK)/GameData.dll</HintPath>              <Private>false</Private></Reference>
    <Reference Include="GameData.Shared">       <HintPath>$(BK)/GameData.Shared.dll</HintPath>       <Private>false</Private></Reference>
    <Reference Include="GameData.Utilities">    <HintPath>$(BK)/GameData.Utilities.dll</HintPath>    <Private>false</Private></Reference>
    <Reference Include="GameData.Combat.Math">  <HintPath>$(BK)/GameData.Combat.Math.dll</HintPath>  <Private>false</Private></Reference>
    <Reference Include="Redzen">                <HintPath>$(BK)/Redzen.dll</HintPath>                <Private>false</Private></Reference>
    <Reference Include="0Harmony">              <HintPath>$(MG)/0Harmony.dll</HintPath>              <Private>false</Private></Reference>
    <Reference Include="TaiwuModdingLib">       <HintPath>$(MG)/TaiwuModdingLib.dll</HintPath>       <Private>false</Private></Reference>
    <Reference Include="YamlDotNet">            <HintPath>$(MSBuildProjectDirectory)/../libs/YamlDotNet.dll</HintPath> <Private>true</Private></Reference>
  </ItemGroup>
</Project>
```

> `<Private>false</Private>` = 不要把遊戲 dll 複製進輸出（它們已在遊戲裡）。
> `<Private>true</Private>` 只給 `YamlDotNet`（mod 要自帶）。先把 `YamlDotNet.dll` 從參考 mod 的 `Plugins/` 複製到 `MySwordMod/libs/`。

---

## 3. Frontend .csproj

`Frontend/MySwordMod.Frontend.csproj`：

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyName>MySwordMod.Frontend</AssemblyName>
    <GenerateAssemblyInfo>False</GenerateAssemblyInfo>
    <TargetFramework>net48</TargetFramework>
    <PlatformTarget>x64</PlatformTarget>
    <LangVersion>14.0</LangVersion>
    <AllowUnsafeBlocks>True</AllowUnsafeBlocks>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
  </PropertyGroup>
  <PropertyGroup>
    <MG>$(HOME)/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/The Scroll of Taiwu_Data/Managed</MG>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="Assembly-CSharp">  <HintPath>$(MG)/Assembly-CSharp.dll</HintPath>  <Private>false</Private></Reference>
    <Reference Include="GameData.Shared">  <HintPath>$(MG)/GameData.Shared.dll</HintPath>  <Private>false</Private></Reference>
    <Reference Include="GameData.Utilities"><HintPath>$(MG)/GameData.Utilities.dll</HintPath><Private>false</Private></Reference>
    <Reference Include="0Harmony">         <HintPath>$(MG)/0Harmony.dll</HintPath>         <Private>false</Private></Reference>
    <Reference Include="TaiwuModdingLib">  <HintPath>$(MG)/TaiwuModdingLib.dll</HintPath>  <Private>false</Private></Reference>
    <Reference Include="System.Core">      <HintPath>$(MG)/System.Core.dll</HintPath>      <Private>false</Private></Reference>
    <Reference Include="YamlDotNet">       <HintPath>$(MSBuildProjectDirectory)/../libs/YamlDotNet.dll</HintPath> <Private>true</Private></Reference>
  </ItemGroup>
</Project>
```

> ⚠ 在 Linux 上編 `net48` target 需要 `Microsoft.NETFramework.ReferenceAssemblies` NuGet 套件：
> ```
> dotnet add Frontend/MySwordMod.Frontend.csproj package Microsoft.NETFramework.ReferenceAssemblies
> ```
> 否則 `dotnet build` 會抱怨找不到 .NET Framework 4.8 reference assemblies。

---

## 4. Backend 入口（Plugin.cs）

抄參考 mod 的 `FeaturesBoundToFuyuPlugin`，保留兩個關鍵 Harmony patch（解剖報告 §6）：

```csharp
using System.IO;
using Config;
using Config.Common;
using GameData.Domains;
using GameData.Domains.CombatSkill;
using GameData.Domains.SpecialEffect;
using GameData.DomainEvents;
using HarmonyLib;
using TaiwuModdingLib.Core.Plugin;
using MySwordMod.Backend;   // DataConfigAppender 命名空間

namespace MySwordMod.Backend;

[PluginConfig("MySwordModBackend", "你的id", "1.0.0.0")]
public class Plugin : TaiwuRemakePlugin
{
    private Harmony _harmony;

    public override void Initialize()
    {
        _harmony = Harmony.CreateAndPatchAll(typeof(Plugin));
        var dir = DomainManager.Mod.GetModDirectory(ModIdStr);
        DataConfigAppender.LoadSpecialEffectsFromYamlFile(Path.Combine(dir, "SpecialEffects.yml"));
        DataConfigAppender.LoadCombatSkillsFromYamlFile(Path.Combine(dir, "CombatSkills.yml"));
    }

    public override void Dispose() => _harmony?.UnpatchSelf();

    // 過月送武功（不要在 OnEnterNewWorld 直接送，會踩雷）
    public override void OnEnterNewWorld()     => RegisterAdvance();
    public override void OnLoadedArchiveData() => RegisterAdvance();
    private void RegisterAdvance()
    {
        Events.UnRegisterHandler_AdvanceMonthFinish(new OnAdvanceMonthFinish(OnAdvance));
        Events.RegisterHandler_AdvanceMonthFinish(new OnAdvanceMonthFinish(OnAdvance));
    }
    private void OnAdvance(DataContext ctx)
    {
        foreach (var item in DataConfigAppenderHelpers.CombatSkillItems)
        {
            var existing = default(GameData.Domains.Taiwu.TaiwuCombatSkill);
            if (!DomainManager.Taiwu.TryGetElement_CombatSkills(item.TemplateId, ref existing))
                DomainManager.Taiwu.TaiwuLearnCombatSkill(ctx, item.TemplateId, ushort.MaxValue);
        }
    }

    // ---- 容量擴張 patch（直接抄，必須有，否則學技能時越界）----
    [HarmonyPrefix]
    [HarmonyPatch(typeof(CombatSkillDomain), "InitializeOnInitializeGameDataModule")]
    public static bool ResizeEquipDict()
    {
        CombatSkillDomain.EquipAddPropertyDict = new short[32768][];
        foreach (CombatSkillItem item in (System.Collections.Generic.IEnumerable<CombatSkillItem>)CombatSkill.Instance)
        {
            if (item == null || item.TemplateId < 0) continue;
            var list = item.PropertyAddList;
            if (list == null || list.Count == 0) continue;
            var arr = new short[112];
            foreach (var pv in list)
                if (pv.PropertyId >= 0 && pv.PropertyId < arr.Length) arr[pv.PropertyId] = pv.Value;
            CombatSkillDomain.EquipAddPropertyDict[item.TemplateId] = arr;
        }
        AccessTools.Method(typeof(CombatSkillDomain), "InitializeLearnableCombatSkillTemplateIds")?.Invoke(null, null);
        return false;
    }

    // SpecialEffectDomain.Add 反射查 ClassName 的兩個 patch：直接從參考 mod
    // FeaturesBoundToFuyuPlugin.cs:177-260 抄過來（FixAdd 兩個 overload）。
}
```

---

## 5. Frontend 入口（Plugin.cs）

```csharp
using System.IO;
using GameData.Domains.Mod;
using HarmonyLib;
using TaiwuModdingLib.Core.Plugin;
using MySwordMod.Backend;   // 共用同一份 DataConfigAppender（也可前端各放一份）

namespace MySwordMod.Frontend;

[PluginConfig("MySwordModFrontend", "你的id", "1.0.0.0")]
public class Plugin : TaiwuRemakePlugin
{
    private Harmony _harmony;
    public override void Initialize()
    {
        _harmony = Harmony.CreateAndPatchAll(typeof(Plugin));
        var dir = ((ModInfo)ModManager.GetModInfo(ModIdStr)).DirectoryName;
        DataConfigAppender.LoadCombatSkillsFromYamlFile(Path.Combine(dir, "CombatSkills.yml"));
        DataConfigAppender.LoadSpecialEffectsFromYamlFile(Path.Combine(dir, "SpecialEffects.yml"));
    }
    public override void Dispose() => _harmony?.UnpatchSelf();
}
```

> 注意 frontend 的 `DataConfigAppender` 引用的是 **前端的** `CombatSkill.Instance`（在 `Assembly-CSharp` 或 `GameData.Shared` 內）。實務上參考 mod 是前後端各編一份 `DataConfigAppender.cs`（內容幾乎一樣，只是引用的 assembly 不同）。**最簡單做法：兩個專案各自 include 一份 `DataConfigAppender.cs`。**

---

## 6. 特效類別

放在 `Backend/Effects/`，命名空間**必須**以 `GameData.Domains.SpecialEffect.` 開頭：

```csharp
using GameData.Common;
using GameData.DomainEvents;
using GameData.Domains.CombatSkill;
using GameData.Domains.SpecialEffect.CombatSkill;

namespace GameData.Domains.SpecialEffect.MySwordMod;   // ← 對應 YAML 的 ClassName: "MySwordMod.MySwordIntent"

internal class MySwordIntent : CombatSkillEffectBase
{
    private int _stack;
    public MySwordIntent() { }
    public MySwordIntent(CombatSkillKey key) : base(key, /*你的特效EffectId*/ 0, (sbyte)(-1)) { }

    public override void OnEnable(DataContext ctx)
    {
        _stack = 0;
        Events.RegisterHandler_AttackSkillAttackHit(new OnAttackSkillAttackHit(OnHit));
    }
    public override void OnDisable(DataContext ctx)
    {
        Events.UnRegisterHandler_AttackSkillAttackHit(new OnAttackSkillAttackHit(OnHit));
    }
    private void OnHit(DataContext ctx, CombatCharacter atk, CombatCharacter def, short skillId, int idx, bool crit)
    {
        if (atk.GetId() != CharacterId || skillId != SkillTemplateId) return;
        _stack++;
        if (_stack >= 5) { ShowSpecialEffectTips(0); _stack = 0; /* 觸發效果，用 DomainManager.Combat.* */ }
    }
}
```

> 可用事件與 `DomainManager.Combat` 動詞清單見 [backend 事件手冊](../details/backend_combat_events.md)。

---

## 7. 三個資料檔

照 [Config/YAML 規格](../details/config_lua_schema.md) §A/B/C 填好 `Config.Lua`、`CombatSkills.yml`、`SpecialEffects.yml`，放進 `dist/`。

`Config.Lua` 最關鍵欄位：
```lua
return {
  Title = "我的劍法 mod",
  GameVersion = "0.0.79.60-test",         -- ⚠ 換成你遊戲實際版本
  BackendPlugins  = { "MySwordMod.Backend.dll" },
  FrontendPlugins = { "MySwordMod.Frontend.dll" },
  ChangeConfig = true,
  HasArchive = true,
  Source = 0,
}
```

---

## 8. 編譯與打包

```sh
cd ~/repo/pas/projects/taiwu/MySwordMod

# 前端需要 net48 reference assemblies（一次性）
dotnet add Frontend/MySwordMod.Frontend.csproj package Microsoft.NETFramework.ReferenceAssemblies

dotnet build Backend/MySwordMod.Backend.csproj  -c Release -o dist/Plugins
dotnet build Frontend/MySwordMod.Frontend.csproj -c Release -o dist/Plugins

# 確認三個 dll 都在
ls dist/Plugins/   # → MySwordMod.Backend.dll, MySwordMod.Frontend.dll, YamlDotNet.dll
```

---

## 9. 安裝到遊戲

Mod 根目錄 = `<Application.dataPath>/../Mod/`（Level 2 §5），即：

```sh
GAME="$HOME/.local/share/Steam/steamapps/common/The Scroll Of Taiwu"
mkdir -p "$GAME/Mod/MySwordMod"
cp dist/Config.Lua dist/CombatSkills.yml dist/SpecialEffects.yml "$GAME/Mod/MySwordMod/"
cp -r dist/Plugins "$GAME/Mod/MySwordMod/"
```

最終遊戲內：
```
<遊戲>/Mod/MySwordMod/
├── Config.Lua
├── CombatSkills.yml
├── SpecialEffects.yml
└── Plugins/{MySwordMod.Backend.dll, MySwordMod.Frontend.dll, YamlDotNet.dll}
```

啟動遊戲 → 主選單 Mod 面板啟用「我的劍法 mod」→ 開新存檔或讀檔 → **過一個月** → 主角學會新武功。

---

## 10. 驗證與排錯

**前端日誌**（Unity）：Linux 通常在
`~/.config/unity3d/ConchShip/The Scroll of Taiwu/Player.log`
（或遊戲目錄附近）。搜：
- `Start loading mod 我的劍法 mod for frontend ...`
- `Loaded N special effect item(s)`
- `Total N mods loaded into the game.`

**後端日誌**：`Backend/` 進程用 NLog（`NLog.dll`），找 `Backend/` 或存檔目錄下的 log 檔。搜 `AdaptableLog.Info` 印出的字串。

**常見錯誤對照**（解剖報告 §9 / Config 規格）：
| 症狀 | 原因 |
|---|---|
| 開戰即崩 / 學技能崩 | 忘了容量 patch，或只在一端載 YAML |
| `Cannot find type 'GameData.Domains.SpecialEffect.XXX'` | 特效類命名空間不對，或 YAML `ClassName` 拼錯 |
| mod 完全沒載入 | `Config.Lua` 解析失敗（檢查 Lua 語法、檔名大小寫） |
| `Invalid Mod Setting Type` | `DefaultSettings` 的 `SettingType` 不在五種白名單 |
| 新武功學不到 | `OnAdvance` 沒註冊，或 `NewTemplateId` < 原表大小被擋 |
| 後面的 mod 都沒載 | 你的 mod 載入失敗會 break 整串（Level 2 §12），先修自己 |

**改 code 後**：必須重編兩個 dll、覆蓋 `Mod/MySwordMod/Plugins/`、**重啟遊戲**（mod 在啟動時載入，不能熱重載）。

---

## 11. 下一步

- 設計實際武功數值與機制 → 見 [屬性 ID 表](../details/property_ids.md) 與 [backend 事件手冊](../details/backend_combat_events.md)。
- 確定克隆來源（哪把原版劍法當基底）→ 需要列出原版 CombatSkill 清單（待辦：寫個小工具 dump `Config/ConfigCells/`）。
- 上傳工坊 → Steam UGC 流程（Level 2 §10，未深入）。

## 參考檔案
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/MoreFactionCombatSkillsBackend.csproj`（net6.0 + backend refs）
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsFrontend/MoreFactionCombatSkillsFrontend.csproj`（net48 + Managed refs）
- `~/dev/taiwu-src/mods/MoreFactionCombatSkillsBackend/FeaturesBoundToFuyu/`（可複用框架）
