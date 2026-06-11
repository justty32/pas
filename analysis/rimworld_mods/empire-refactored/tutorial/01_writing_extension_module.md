# 教學：為 Empire Refactored 寫第三方擴展模組（01_writing_extension_module）

> 目標導向教學：從零建立一個能同時與 **Empire Refactored**（`Matathias.Empire`, v1.3.74）及（選配）**Rim War**（`Torann.RimWar`）互動的獨立擴展 mod，直到在遊戲 log 驗證載入成功。
>
> **路徑基準聲明**：
> - `<mod>` ＝ `~/.local/share/Steam/steamapps/workshop/content/294100/3701480464/`（Empire Refactored）
> - Empire 核心源碼相對 `<mod>1.6/Source/Core/FactionColonies/`；官方橋接範本相對 `<mod>1.6/Source/`
> - 深度依據：`../details/bridge_module_walkthrough.md`（Patch-RW 走讀＋完整 API 清單，本文簡稱「走讀」）、`../details/extension_points.md`（XML 接點總表）

## 0. 前置知識

| 需要會 | 用在哪 | 不會的話 |
|---|---|---|
| RimWorld mod 基本結構（About.xml、Assemblies、Defs、Patches） | 全程 | 先做一個純 XML mod |
| C# / .NET Framework 4.8、SDK 風格 csproj | 步驟 2-4 | 純 XML 接點也能做不少事（見 extension_points.md §A） |
| Harmony（Prefix/Postfix/Transpiler、`__instance`/`__result`、參數名配對） | 只有鉤第三方 mod 時需要 | 只擴展 Empire 本身可完全不用 Harmony |
| Empire 的擴展架構：FCInterfaces ＋ 15 個 Registry | 步驟 5 | 讀走讀 §6-7 |

核心心法（從官方 Patch-RW 歸納，走讀 §1）：**對 Empire 走契約層（介面＋Registry），對沒有擴展 API 的 mod（如 Rim War）才走 Harmony**；資料層問題（comp 掛載、def 調整）用條件載入的 XML patch。

## 1. 原始碼導航：要改什麼，先去哪裡看

| 想做的事 | 先讀 | 關鍵檔 |
|---|---|---|
| 加 UI（主分頁/聚落分頁/聚落按鈕/軍事卡片） | 走讀 §6 對應介面列 | `Comps/Interfaces/FCInterfaces.cs:11,23,309,354` |
| 改經濟（稅、產量、收支、付款） | extension_points.md §B-1 | `FCInterfaces.cs:51,82,110,231,388`；呼叫點 `Worldobjects/WorldSettlementFC.cs:1895,1917`、`Util/PaymentUtil.cs:180` |
| 改軍事（戰力、防守、目標、自有單位參戰） | 走讀 §4.0、§6 | `FCInterfaces.cs:149,162,245,261,280`；`Military/SimulateBattleFC.cs:14-15` |
| 監聽事件（聚落/建築/戰鬥/研究生命週期） | 走讀 §6 `ILifecycleParticipant` 列 | `FCInterfaces.cs:128`、`Util/Registries/LifecycleRegistry.cs`、`Comps/Interfaces/LifecycleParticipantBase.cs` |
| 與 Rim War 互動 | 走讀 §2、§4 全部 | `<mod>1.6/Source/Patch-RW/`（8 檔全讀，420 行） |
| 鉤其他第三方 mod | 走讀 §5 模式表 | 對照 Patch-WD/KCSG/VF/FTV 挑同型模式 |
| 純 XML（新聚落型別/資源/建築/事件/政策） | extension_points.md §A | `<mod>1.6/Defs/` 各範例檔 |

## 2. 步驟一：mod 骨架

獨立擴展是一個**自己的 mod**（不是塞檔案進 Empire 目錄）。最小結構：

```
EmpireMyExt/
├── About/About.xml
├── LoadFolders.xml            ← 只有「對第三個 mod 也要條件載入」才需要
├── 1.6/
│   ├── Assemblies/EmpireMyExt.dll
│   ├── Defs/                  ← 自己的 def
│   └── Patches/               ← 對 Empire def 的 XML patch
└── Source/EmpireMyExt/EmpireMyExt.csproj + *.cs
```

`About/About.xml` 要點（仿 `<mod>About/About.xml:6-31`）：

```xml
<ModMetaData>
  <name>Empire MyExt</name>
  <packageId>yourname.EmpireMyExt</packageId>
  <supportedVersions><li>1.6</li></supportedVersions>
  <modDependencies>
    <li><packageId>brrainz.harmony</packageId><displayName>Harmony</displayName></li>
    <li><packageId>Matathias.Empire</packageId><displayName>Empire Refactored</displayName></li>
  </modDependencies>
  <loadAfter>
    <li>Matathias.Empire</li>
    <li>Torann.RimWar</li>   <!-- 若也鉤 Rim War -->
  </loadAfter>
</ModMetaData>
```

**硬依賴 Empire 就宣告 modDependencies；Rim War 若是選配**，照官方做法用 LoadFolders.xml 條件載入（仿 `<mod>LoadFolders.xml:9`）：把鉤 Rim War 的程式碼編成第二個 dll 放 `Compat/1.6/RimWar/Assemblies/`，加 `<li IfModActive="Torann.RimWar">Compat/1.6/RimWar</li>`。單一目標時可省略此層，直接把全部放 `1.6/`。

## 3. 步驟二：csproj（引用兩邊 dll）

逐段抄改官方範本 `Patch-RW/Empire.RW.csproj`（走讀 §3.1 有逐段解析）：

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <PlatformTarget>x64</PlatformTarget>
    <AssemblyName>EmpireMyExt</AssemblyName>
    <RootNamespace>EmpireMyExt</RootNamespace>
    <OutputPath>..\..\1.6\Assemblies</OutputPath>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <CopyLocalLockFileAssemblies>false</CopyLocalLockFileAssemblies>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Krafs.Rimworld.Ref" Version="1.6.*-*" />
    <PackageReference Include="Lib.Harmony" Version="2.3.6" />
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="All" />
  </ItemGroup>
  <ItemGroup>
    <Reference Include="Empire">
      <HintPath>$(HOME)/.local/share/Steam/steamapps/workshop/content/294100/3701480464/1.6/Assemblies/Empire.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="RimWar"> <!-- 選配 -->
      <HintPath>(Rim War 工作坊目錄)/Assemblies/RimWar.dll</HintPath>
      <Private>False</Private>
    </Reference>
  </ItemGroup>
</Project>
```

三條鐵則（皆出自官方範本）：
1. **所有外部 Reference 一律 `<Private>False</Private>`**（`Empire.RW.csproj:24,30,34` 等）——絕不把別人的 dll 複製進自己的 Assemblies。
2. 版本要對準**實裝版** Empire dll（官方用 ProjectReference 因為有源碼，`Empire.RW.csproj:22-26`；第三方用 HintPath 指工作坊實檔最不會錯）。
3. OutputPath 直指 mod 的 Assemblies，編譯即部署（`Empire.RW.csproj:8`）。

## 4. 步驟三：Init 類（含穩健註冊）

照官方共通骨架（走讀 §5 末），但補上官方範本自己都缺的 **ClearCaches 防護**（陷阱詳見走讀 §7.2：`Game.ClearCaches` 在每次開新局/讀檔時觸發 `EmpireCacheUtil.InvalidateAll` 清空全部 registry，`HarmonyPatches/CachePatches.cs:36-50,72-86`）：

```csharp
using FactionColonies;
using HarmonyLib;
using System.Reflection;
using Verse;

namespace EmpireMyExt
{
    [StaticConstructorOnStartup]
    public static class MyExtInit
    {
        private static readonly MyLifecycleHooks hooks = new MyLifecycleHooks();

        static MyExtInit()
        {
            new Harmony("yourname.EmpireMyExt").PatchAll(Assembly.GetExecutingAssembly());
            RegisterAll();
            // registry 被 InvalidateAll 清空後自動重註冊：
            // invalidator 字典不會被清，且回呼在 ClearAll 之後執行（CachePatches.cs:55-59）
            EmpireCacheUtil.RegisterCacheInvalidator("yourname.EmpireMyExt", RegisterAll);
            LogUtil.MessageForce("EmpireMyExt loaded.");   // ← 驗證錨點，必出現在 log
        }

        private static void RegisterAll()
        {
            LifecycleRegistry.Register(hooks);
            // 其他 XxxRegistry.Register(...) 都放這裡
        }
    }

    // 範例：監聽聚落生命週期。繼承 LifecycleParticipantBase（全空虛擬方法）只覆寫需要的
    public class MyLifecycleHooks : LifecycleParticipantBase
    {
        public override void OnSettlementCreated(WorldSettlementFC settlement)
        {
            LogUtil.Message($"MyExt: settlement {settlement.Name} created");
        }
    }
}
```

依據：Harmony ID 慣例與 MessageForce 錨點＝`Patch-RW/RimWarCompatInit.cs:25-30`；`LifecycleParticipantBase`＝`Comps/Interfaces/LifecycleParticipantBase.cs:9-23`；重註冊必要性＝核心自身的 `FactionFC.cs:524-527`（「Re-register ... in case ClearCaches ran」）。

回呼內可以放心拋例外——所有 registry 的 Invoke 對每個參與者單獨 try/catch（如 `Util/Registries/LifecycleRegistry.cs:25-26`），但壞了只會默默記 `LogUtil.Error`，自己要盯 log。

## 5. 步驟四：選接點（決策順序）

由淺入深，能停在淺層就停：

1. **純 XML 能不能做到？**（新聚落型別/資源/建築/事件/政策＝def；給 Empire 聚落掛 comp＝PatchOperationAdd）→ extension_points.md §A。
2. **Empire 有沒有現成介面？** → 查走讀 §6 的 22 個介面表。常用首選：
   - 事件監聽 → `ILifecycleParticipant`（11 個事件，覆蓋聚落/建築/軍事/研究/傭兵）
   - 改戰鬥 → `IBattleModifier`（攻防配對技巧見走讀 §4.0）
   - 自己的 world object 參與襲擊/防衛體系 → `IRaidTarget` + `IAutoDefender` + `IMilitaryTabEntry` 三件套
   - 加 UI → `ISettlementWindowButton`（最便宜）或 `IMainTabWindowOverview`/`ISettlementWindowOverview`
   - 改錢 → `ITaxTickParticipant`（可 `ref silverAmount`）/ `ISilverPaymentModifier`
   - 聚落掛資料 → 自訂 `WorldObjectComp`（XML patch 掛上）＋按需實作 `IStatModifierProvider`/`IResourceProductionModifier`/`IProfitContributor`/`ISettlementPostLoadInit`
3. **都沒有才 Harmony**。鉤 Empire：先確認真的沒接點（核心介面有 22 個，多半有）。鉤 Rim War 等第三方：照走讀 §5 的 12 個模式表挑同型範本抄，守則「非自家物件一律 return true」（`Patch_RimWarPoints.cs:25-28` 等全部 patch 同此形）。

針對 Rim War 的具體鉤點（已由官方驗證可行）：聚落可見性 `WorldUtility.IsValidSettlement`、點數漏斗 `RimWarSettlementComp.RimWarPoints` getter、攻擊入口 `IncidentUtility.ResolveWarObjectAttackOnSettlement`、奪城 `WorldUtility.ConvertSettlement`、存檔行為 `WorldComponent_PowerTracker.ExposeData`——各自的原始碼行號與 patch 寫法見走讀 §4.1-4.7。

## 6. 步驟五：XML patch（如需給 Empire 聚落掛 comp）

放 `1.6/Patches/MyComp.xml`，照官方範本 `<mod>Compat/1.6/RimWar/Patches/RimWarSettlementComp.xml` 打抽象基底：

```xml
<Patch>
  <Operation Class="PatchOperationAdd">
    <xpath>Defs/FactionColonies.WorldSettlementDef[@Name="WorldSettlementDefBase"]</xpath>
    <value><comps><li Class="EmpireMyExt.WorldObjectCompProperties_MyComp" /></comps></value>
  </Operation>
</Patch>
```

注意 xpath 的元素名是 **`FactionColonies.WorldSettlementDef`**（不是 `WorldObjectDef`）——Rim War 自己就是踩了這個坑才需要 Empire 補刀（該 XML 檔頭註解）。

## 7. 步驟六：部署與載入驗證

部署（本機慣例：mod 實體放 `~/rimworld_mods/`，遊戲只掃 `install/Mods`、Workshop、Data，所以要建 symlink）：

```bash
ln -s ~/rimworld_mods/EmpireMyExt "<RimWorld安裝目錄>/Mods/EmpireMyExt"
```

驗證清單（依序，缺一不可）：

1. **Mod 列表**：遊戲內 Mods 介面看得到、排序在 Empire（與 Rim War）之後。
2. **ModsConfig 有列 ≠ 真載入**——以 log 字串為準。本機走 Proton 跑 Windows 版時，真 log 在 compatdata prefix 下（不是 `~/.config/unity3d`）。
3. **錨點字串**：log 搜 `EmpireMyExt loaded.`（`LogUtil.MessageForce` 不受 verbose 設定抑制，`Util/LogUtil.cs:25`；對照官方錨點「RimWar compatibility module loaded.」`RimWarCompatInit.cs:29`）。
4. **Harmony 失敗即紅字**：`PatchAll` 找不到目標方法會在 log 炸 HarmonyException——沒紅字＋有錨點＝patch 全數命中。
5. **回呼煙霧測試**：開新局建一個 Empire 聚落，確認步驟四範例的 `OnSettlementCreated` log 出現；**再存檔→讀檔→重複一次**，驗證 §4 的重註冊防護生效（這一步正是官方 Patch-RW 自己會掛的點，走讀 §7.2）。
6. **XML patch 驗證**：開發者模式 → Debug inspector 看任一 Empire 聚落的 comps 有沒有你的 comp；或 log 無 `Patch operation ... failed`。

## 8. 陷阱備忘（全部踩過源碼確認）

| 陷阱 | 後果 | 解法（依據） |
|---|---|---|
| 只在 StaticConstructorOnStartup 註冊 registry | 第一次讀檔/開新局後擴展靜默失效 | `EmpireCacheUtil.RegisterCacheInvalidator` 重註冊（`CachePatches.cs:21-24,55-59`；走讀 §7.2-7.3） |
| Reference 沒設 `Private=False` | 重複攜帶 Empire/RimWar/Harmony dll → 型別衝突 | 全部 `<Private>False</Private>`（`Empire.RW.csproj` 全檔慣例） |
| 頂層 using 選配 mod 的命名空間但無條件載入 | 對方不在場時 TypeLoadException | 選配目標的程式碼放條件載入 dll（`LoadFolders.xml:9`）；packageId 不穩時用 NoInlining 延遲解析（`Patch-FTV/FactionTerritoriesCompat.cs:122-135`） |
| Prefix 對非自家物件也 return false | 毀掉原 mod 與其他相容 mod | 一律「非自家型別 return true」（`Patch_RimWarPoints.cs:25-28`） |
| 判斷 PColony 用 defName 字串 | 與 Rim War 同樣的脆弱判斷 | 用 `FactionCache.IsPlayerColonyFaction`（`Util/FactionCache.cs:54`；官方在 `Patch_ForceVassalBehavior.cs:47` 特地棄用 RimWar 的判斷改用此） |
| 在 `OnSettlementFounded` 假設聚落已存在 | NRE | 該回呼時聚落尚未生成（`FCInterfaces.cs:203-207` 註解） |
| comp 載入期初始化放 `PostExposeData` | 讀到未重建的 stat | 改實作 `ISettlementPostLoadInit`（`FCInterfaces.cs:96-106`） |
| 用 `LogUtil.Message` 當驗證錨點 | verbose 關閉時看不到 | 用 `MessageForce`（`Util/LogUtil.cs:25`） |
