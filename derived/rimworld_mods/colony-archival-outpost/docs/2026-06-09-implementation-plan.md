# 殖民地封存哨站 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓玩家採樣一座殖民地的儲存區淨增長、把它封存成一個按該率持續送資源回主基地的抽象 VOE outpost。

**Architecture:** 路線 A 純抽象。子類化 VOE `Outpost`：override `ResultOptions`＝採樣 snapshot 的**正成長**（VOE 預設 `Produce/Deliver` 投遞回主基地，同普通 VOE 哨站）、override `Produce()` 先扣**負成長**（從封存帶來的 `containedItems` 緩衝）再 `base.Produce()`。採樣＝`ResourceCounter.AllCountedAmounts` 期初/期末快照相減（有號，`MapComponent` 保存）。封存＝建 outpost→搬玩家 pawn(囚犯保留身分)→把儲存區物資塞 `containedItems` 當緩衝→`DeinitAndRemoveMap`。觸發＝Harmony postfix `Settlement.GetGizmos` 加兩個 gizmo。

**Tech Stack:** C# net48；RimWorld 1.6 API；VEF 內 `Outposts.dll`（`Outpost`/`ResultOption`/`OutpostExtension`）；Harmony；XML Def＋Keyed。

> **權威源**：`projects/rimworld/`、VOE 反編譯 `projects/rimworld_mods/vanilla-outposts-expanded/decompiled-framework/Outposts.decompiled.cs`。spec：`docs/2026-06-09-design.md`。
>
> **測試現實**：RimWorld mod 無法 pytest 式 TDD（型別需遊戲 runtime）。每個 code 任務的驗證＝① `dotnet build` 0 警告 0 錯誤 ② `healthcheck.py` 靜態檢查通過。**行為驗證集中在 Task 9 實機端到端**。每個任務結束 commit。
>
> **commit 規則**：只 `git add` 本 mod 自己的檔（明確路徑），勿 `-A`（使用者常有並行未提交改動）。

---

## 檔案結構

```
derived/rimworld_mods/colony-archival-outpost/
├── About/About.xml                         # 名稱/作者/相依(VEF+VOE+Harmony)/loadAfter
├── LoadFolders.xml                         # 1.6 版本資料夾
├── Defs/WorldObjectDefs/Outpost_Sampled.xml# WorldObjectDef + OutpostExtension(空ResultOptions)
├── Languages/English/Keyed/CAO.xml         # 英文字串
├── Languages/ChineseTraditional/Keyed/CAO.xml # 繁中字串
├── Source/
│   ├── ColonyArchivalOutpost.csproj        # net48, refs 遊戲/Harmony/Outposts.dll
│   ├── Properties/AssemblyInfo.cs
│   ├── CAOMod.cs                            # Mod 入口 + Harmony.PatchAll
│   ├── ProductivitySnapshot.cs             # IExposable: Dictionary<ThingDef,float>
│   ├── Outpost_Sampled.cs                  # : Outpost, override ResultOptions + ExposeData
│   ├── ColonyArchivalTracker.cs            # : MapComponent, 採樣狀態 + ExposeData
│   ├── ArchivalService.cs                  # static: 算率/建outpost/搬pawn/搬物資/銷毀/邊界
│   └── Settlement_GetGizmos_Patch.cs       # Harmony postfix, 加兩 gizmo
├── 1.6/Assemblies/                         # 編譯輸出(csproj OutputPath)
└── tests/healthcheck.py                    # 靜態健檢
```

每檔一個職責：snapshot＝資料、tracker＝採樣狀態、service＝封存轉換、patch＝UI 注入、outpost＝產出。

---

## Task 0：專案骨架 + 建置管線打通

**Files:**
- Create: `About/About.xml`, `LoadFolders.xml`, `Source/ColonyArchivalOutpost.csproj`, `Source/Properties/AssemblyInfo.cs`, `Source/CAOMod.cs`

- [ ] **Step 1：寫 `About/About.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
  <name>Colony Archival Outpost</name>
  <author>justty32</author>
  <packageId>pas.colonyarchival.outpost</packageId>
  <supportedVersions><li>1.6</li></supportedVersions>
  <description>採樣一座殖民地的儲存區淨增長，封存成持續產出的抽象 outpost。需要 VEF + VOE。</description>
  <modDependencies>
    <li><packageId>brrainz.harmony</packageId><displayName>Harmony</displayName><steamWorkshopUrl>steam://url/CommunityFilePage/2009463077</steamWorkshopUrl></li>
    <li><packageId>OskarPotocki.VanillaFactionsExpanded.Core</packageId><displayName>Vanilla Expanded Framework</displayName><steamWorkshopUrl>steam://url/CommunityFilePage/2023507013</steamWorkshopUrl></li>
    <li><packageId>vanillaexpanded.outposts</packageId><displayName>Vanilla Outposts Expanded</displayName><steamWorkshopUrl>steam://url/CommunityFilePage/2688941031</steamWorkshopUrl></li>
  </modDependencies>
  <loadAfter>
    <li>brrainz.harmony</li>
    <li>OskarPotocki.VanillaFactionsExpanded.Core</li>
    <li>vanillaexpanded.outposts</li>
  </loadAfter>
</ModMetaData>
```

- [ ] **Step 2：寫 `LoadFolders.xml`**

```xml
<loadFolders>
  <v1.6><li>/</li></v1.6>
</loadFolders>
```

- [ ] **Step 3：寫 `Source/ColonyArchivalOutpost.csproj`**（路徑已對本機 workshop 驗證存在）

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <LangVersion>latest</LangVersion>
    <AssemblyName>ColonyArchivalOutpost</AssemblyName>
    <RootNamespace>ColonyArchivalOutpost</RootNamespace>
    <Configuration Condition=" '$(Configuration)' == '' ">Release</Configuration>
    <OutputPath>..\1.6\Assemblies\</OutputPath>
    <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    <AppendRuntimeIdentifierToOutputPath>false</AppendRuntimeIdentifierToOutputPath>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <DebugType>none</DebugType><DebugSymbols>false</DebugSymbols>
    <Deterministic>true</Deterministic>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <CopyLocalLockFileAssemblies>false</CopyLocalLockFileAssemblies>
  </PropertyGroup>
  <PropertyGroup>
    <RimWorldManaged Condition=" '$(RimWorldManaged)' == '' ">$(HOME)/.local/share/Steam/steamapps/common/RimWorld/RimWorldWin64_Data/Managed</RimWorldManaged>
    <HarmonyDll Condition=" '$(HarmonyDll)' == '' ">$(HOME)/.local/share/Steam/steamapps/workshop/content/294100/2009463077/Current/Assemblies/0Harmony.dll</HarmonyDll>
    <OutpostsDll Condition=" '$(OutpostsDll)' == '' ">$(HOME)/.local/share/Steam/steamapps/workshop/content/294100/2023507013/1.6/Assemblies/Outposts.dll</OutpostsDll>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="Properties\AssemblyInfo.cs" />
    <Compile Include="CAOMod.cs" />
    <Compile Include="ProductivitySnapshot.cs" />
    <Compile Include="Outpost_Sampled.cs" />
    <Compile Include="ColonyArchivalTracker.cs" />
    <Compile Include="ArchivalService.cs" />
    <Compile Include="Settlement_GetGizmos_Patch.cs" />
  </ItemGroup>
  <ItemGroup>
    <Reference Include="Assembly-CSharp"><HintPath>$(RimWorldManaged)/Assembly-CSharp.dll</HintPath><Private>false</Private></Reference>
    <Reference Include="UnityEngine"><HintPath>$(RimWorldManaged)/UnityEngine.dll</HintPath><Private>false</Private></Reference>
    <Reference Include="UnityEngine.CoreModule"><HintPath>$(RimWorldManaged)/UnityEngine.CoreModule.dll</HintPath><Private>false</Private></Reference>
    <Reference Include="0Harmony"><HintPath>$(HarmonyDll)</HintPath><Private>false</Private></Reference>
    <Reference Include="Outposts"><HintPath>$(OutpostsDll)</HintPath><Private>false</Private></Reference>
  </ItemGroup>
</Project>
```

> 注意：先在開頭只 Compile 真正存在的檔。Task 0 只建 `AssemblyInfo.cs` + `CAOMod.cs`；其餘 5 個 `<Compile>` 行會在後續任務各自建檔時生效——若 Task 0 要先 build 過，暫時註解掉尚不存在檔案的 Compile 行，建完該檔再解開。

- [ ] **Step 4：寫 `Source/Properties/AssemblyInfo.cs`**

```csharp
using System.Reflection;
[assembly: AssemblyTitle("ColonyArchivalOutpost")]
[assembly: AssemblyProduct("ColonyArchivalOutpost")]
[assembly: AssemblyVersion("1.0.0.0")]
```

- [ ] **Step 5：寫 `Source/CAOMod.cs`**（Mod 入口，PatchAll）

```csharp
using HarmonyLib;
using Verse;

namespace ColonyArchivalOutpost
{
    public class CAOMod : Mod
    {
        public CAOMod(ModContentPack content) : base(content)
        {
            var harmony = new Harmony("pas.colonyarchival.outpost");
            harmony.PatchAll();
            Log.Message("[ColonyArchivalOutpost] Harmony patches applied");
        }
    }
}
```

- [ ] **Step 6：build（暫時註解掉尚不存在的 Compile 行）**

Run: `dotnet build Source/ColonyArchivalOutpost.csproj -c Release`
Expected: Build succeeded, 0 Warning(s) 0 Error(s)；產出 `1.6/Assemblies/ColonyArchivalOutpost.dll`。
若 `Outpost` ref 解析失敗→確認 `$(OutpostsDll)` 路徑（見 spec §3）。

- [ ] **Step 7：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/About derived/rimworld_mods/colony-archival-outpost/LoadFolders.xml derived/rimworld_mods/colony-archival-outpost/Source
git commit -m "feat(cao): project skeleton + build pipeline"
```

---

## Task 1：ProductivitySnapshot（採樣資料容器）

**Files:** Create: `Source/ProductivitySnapshot.cs`

- [ ] **Step 1：寫 `ProductivitySnapshot.cs`**

```csharp
using System.Collections.Generic;
using Verse;

namespace ColonyArchivalOutpost
{
    // 採樣結果：每種資源的「每日有號淨流」(正=產出累積, 負=消耗庫存)。封存當下算好、隨 outpost 存檔。
    public class ProductivitySnapshot : IExposable
    {
        public Dictionary<ThingDef, float> dailyRates = new Dictionary<ThingDef, float>();

        public ProductivitySnapshot() { }

        public ProductivitySnapshot(Dictionary<ThingDef, float> rates)
        {
            dailyRates = rates ?? new Dictionary<ThingDef, float>();
        }

        public bool IsEmpty => dailyRates == null || dailyRates.Count == 0;

        public void ExposeData()
        {
            Scribe_Collections.Look(ref dailyRates, "dailyRates", LookMode.Def, LookMode.Value);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && dailyRates == null)
                dailyRates = new Dictionary<ThingDef, float>();
        }
    }
}
```

- [ ] **Step 2：解開 csproj 對應 Compile 行（若 Task 0 註解過），build**

Run: `dotnet build Source/ColonyArchivalOutpost.csproj -c Release`
Expected: 0/0。

- [ ] **Step 3：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/Source/ProductivitySnapshot.cs derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalOutpost.csproj
git commit -m "feat(cao): ProductivitySnapshot data holder"
```

---

## Task 2：Outpost_Sampled + WorldObjectDef

**Files:** Create: `Source/Outpost_Sampled.cs`, `Defs/WorldObjectDefs/Outpost_Sampled.xml`

> 驗證自 VOE 反編譯：`Outpost`(:731) `public virtual List<ResultOption> ResultOptions`(:826)；`ResultOption`{`ThingDef Thing`,`int BaseAmount`,`int AmountPerPawn`,`List<AmountBySkill> AmountsPerSkills`}(:2050)；`TicksPerProduction`(:775 預設 900000)。

- [ ] **Step 1：寫 `Source/Outpost_Sampled.cs`**

```csharp
using System.Collections.Generic;
using System.Linq;
using Outposts;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    public class Outpost_Sampled : Outpost
    {
        private ProductivitySnapshot snapshot = new ProductivitySnapshot();

        public void SetSnapshot(ProductivitySnapshot s) => snapshot = s ?? new ProductivitySnapshot();

        // 正成長：日均率 × 每產出週期天數 = 該週期產出量(VOE 預設 Produce/Deliver 投遞回主基地)
        public override List<ResultOption> ResultOptions
        {
            get
            {
                var list = new List<ResultOption>();
                if (snapshot == null || snapshot.IsEmpty) return list;
                float daysPerCycle = TicksPerProduction / 60000f; // GenDate.TicksPerDay
                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value <= 0f) continue; // 只有正成長走 ResultOptions
                    int amount = Mathf.RoundToInt(kv.Value * daysPerCycle);
                    if (amount <= 0) continue;
                    list.Add(new ResultOption { Thing = kv.Key, BaseAmount = amount, AmountPerPawn = 0, AmountsPerSkills = null });
                }
                return list;
            }
        }

        // 負成長：每週期從 containedItems 緩衝扣，扣到 0 為止(不負庫存)；再 base.Produce() 產出正成長並投遞回主基地。
        public override void Produce()
        {
            if (snapshot != null && !snapshot.IsEmpty)
            {
                float daysPerCycle = TicksPerProduction / 60000f;
                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value >= 0f) continue; // 只處理負成長
                    int want = Mathf.RoundToInt(-kv.Value * daysPerCycle);
                    DrainContained(kv.Key, want);
                }
            }
            base.Produce();
        }

        // 從 containedItems 移除最多 want 個 def 物；扣到 0 為止。
        // ⚠️ containedItems 的型別/移除 API 待 dnSpy 對 Outpost(:743 附近) 坐實——
        //    若為 ThingOwner，逐一找同 def thing 以 stackCount 抵扣後 thing.SplitOff/Destroy。
        private void DrainContained(ThingDef def, int want)
        {
            if (want <= 0) return;
            var items = containedItems; // 待驗：欄位名/型別
            for (int i = items.Count - 1; i >= 0 && want > 0; i--)
            {
                var t = items[i];
                if (t.def != def) continue;
                int take = Mathf.Min(want, t.stackCount);
                want -= take;
                if (take >= t.stackCount) { t.Destroy(); }
                else { t.stackCount -= take; }
            }
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Deep.Look(ref snapshot, "snapshot");
            if (Scribe.mode == LoadSaveMode.PostLoadInit && snapshot == null)
                snapshot = new ProductivitySnapshot();
        }
    }
}
```

> ⚠️ **待 dnSpy 坐實再定稿**：`containedItems` 的確切型別與 enumeration/移除 API（反編譯 Outpost :743 附近）；`Destroy()`/`stackCount` 抵扣對 `ThingOwner` 內物件是否正確（可能需 `items.Take(t, take)` 之類 `ThingOwner` API）。`base.Produce()` 預設確實投遞回主基地（spec §8 待驗，同普通 VOE 哨站，無需設 Store）。

- [ ] **Step 2：寫 `Defs/WorldObjectDefs/Outpost_Sampled.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <WorldObjectDef>
    <defName>pas_archival_Outpost</defName>
    <label>archived outpost</label>
    <worldObjectClass>ColonyArchivalOutpost.Outpost_Sampled</worldObjectClass>
    <texture>World/WorldObjects/Sites/GenericSite</texture>
    <expandingIcon>true</expandingIconTexture>
    <canHaveFaction>true</canHaveFaction>
    <selectable>true</selectable>
    <neverMultipleOnSameTile>true</neverMultipleOnSameTile>
    <modExtensions>
      <li Class="Outposts.OutpostExtension">
        <TicksPerProduction>900000</TicksPerProduction>
        <MinPawns>0</MinPawns>
        <ResultOptions />
        <!-- 投遞用 VOE 預設(送主基地，同普通 VOE 哨站)，不需特設欄位。
             封存帶來的物資只當負成長消耗的緩衝，不是產出去向(spec §8)。 -->
      </li>
    </modExtensions>
  </WorldObjectDef>
</Defs>
```

> ⚠️ 待 Task 9 前以 dnSpy/反編譯核對 `OutpostExtension` 確切欄位名（`TicksPerProduction`/`MinPawns`/`ResultOptions` 已見於反編譯 :2014-2041，但 `texture`/`expandingIcon` 等 WorldObjectDef 欄位以原版 `WorldObjectDef` 為準）。若 `expandingIcon` 欄位名有出入，改用原版某 outpost WorldObjectDef 的欄位集。

- [ ] **Step 3：build**

Run: `dotnet build Source/ColonyArchivalOutpost.csproj -c Release`
Expected: 0/0。

- [ ] **Step 4：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/Source/Outpost_Sampled.cs derived/rimworld_mods/colony-archival-outpost/Defs derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalOutpost.csproj
git commit -m "feat(cao): Outpost_Sampled subclass + WorldObjectDef"
```

---

## Task 3：ColonyArchivalTracker（採樣狀態 MapComponent）

**Files:** Create: `Source/ColonyArchivalTracker.cs`

> `ResourceCounter.AllCountedAmounts`→`Dictionary<ThingDef,int>`(ResourceCounter.cs:17)。`map.resourceCounter` 為 Map 既有欄位。

- [ ] **Step 1：寫 `Source/ColonyArchivalTracker.cs`**

```csharp
using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    public class ColonyArchivalTracker : MapComponent
    {
        public bool isSampling;
        public int startTick = -1;
        public Dictionary<ThingDef, int> startCounts = new Dictionary<ThingDef, int>();

        public ColonyArchivalTracker(Map map) : base(map) { }

        public void BeginSampling()
        {
            isSampling = true;
            startTick = Find.TickManager.TicksGame;
            startCounts = new Dictionary<ThingDef, int>(map.resourceCounter.AllCountedAmounts);
        }

        public void Reset()
        {
            isSampling = false;
            startTick = -1;
            startCounts = new Dictionary<ThingDef, int>();
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref isSampling, "isSampling", false);
            Scribe_Values.Look(ref startTick, "startTick", -1);
            Scribe_Collections.Look(ref startCounts, "startCounts", LookMode.Def, LookMode.Value);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && startCounts == null)
                startCounts = new Dictionary<ThingDef, int>();
        }
    }
}
```

- [ ] **Step 2：build；commit**

```bash
dotnet build Source/ColonyArchivalOutpost.csproj -c Release
git add derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalTracker.cs derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalOutpost.csproj
git commit -m "feat(cao): ColonyArchivalTracker sampling MapComponent"
```

---

## Task 4：ArchivalService（封存核心轉換）

**Files:** Create: `Source/ArchivalService.cs`

> 這是**最高風險任務**（spec §13.1-3）。`AddPawn`(:1022) 的 `CanAddPawn`(:1033) 會擋囚犯/動物/非商隊 pawn → 自寫 occupants 加入；`occupants` 為 private(:743) → 用反射或（若 VOE 有 public API）改走之。

- [ ] **Step 1：寫 `Source/ArchivalService.cs`**

```csharp
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Outposts;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    public static class ArchivalService
    {
        // occupants 是 Outpost 的 private List<Pawn>(:743)；用反射取得以繞過 CanAddPawn。
        private static readonly FieldInfo OccupantsField =
            AccessTools.Field(typeof(Outpost), "occupants");

        public static bool CanArchive(Map map, out string reason)
        {
            reason = null;
            if (map == null || !map.IsPlayerHome) { reason = "CAO.NotPlayerHome".Translate(); return false; }
            // 唯一基地防呆：若這是最後一張玩家家園地圖且無其他投遞目標
            int homeCount = Find.Maps.Count(m => m.IsPlayerHome);
            if (homeCount <= 1) { reason = "CAO.LastBase".Translate(); return false; }
            return true;
        }

        public static ProductivitySnapshot ComputeSnapshot(Map map, ColonyArchivalTracker tracker)
        {
            var end = map.resourceCounter.AllCountedAmounts;
            int elapsedTicks = Find.TickManager.TicksGame - tracker.startTick;
            // 數學防呆下限 = 1 遊戲天(60000 tick)，避免除以趨近 0（spec §6.4）
            float elapsedDays = Mathf.Max(elapsedTicks, 60000) / 60000f;
            // 取所有出現過的 def(期初或期末)，算有號淨流(正=產出、負=消耗)
            var allDefs = new HashSet<ThingDef>(end.Keys);
            allDefs.UnionWith(tracker.startCounts.Keys);
            var rates = new Dictionary<ThingDef, float>();
            foreach (var def in allDefs)
            {
                end.TryGetValue(def, out int e1);
                tracker.startCounts.TryGetValue(def, out int s0);
                int delta = e1 - s0; // 有號淨庫存變化
                if (delta == 0) continue;
                rates[def] = delta / elapsedDays; // 正負都保留
            }
            return new ProductivitySnapshot(rates);
        }

        public static void Archive(Map map)
        {
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null || !tracker.isSampling) return;
            if (!CanArchive(map, out string reason))
            {
                Messages.Message(reason, MessageTypeDefOf.RejectInput, false);
                return;
            }

            var settlement = map.Parent as Settlement;
            int tile = map.Tile;
            var snapshot = ComputeSnapshot(map, tracker);

            // 1) 建 outpost
            var outpost = (Outpost_Sampled)WorldObjectMaker.MakeWorldObject(
                DefDatabase<WorldObjectDef>.GetNamed("pas_archival_Outpost"));
            outpost.Tile = tile;
            outpost.SetFaction(Faction.OfPlayer);
            outpost.SetSnapshot(snapshot);
            Find.WorldObjects.Add(outpost);

            // 2) 搬玩家 pawn（殖民者+玩家動物+殖民地囚犯），繞過 CanAddPawn 直接加 occupants。
            //    囚犯不清 guest 狀態 → 保留囚犯身分(spec §7.4)。敵襲者/中立不納入。
            var occupants = (List<Pawn>)OccupantsField.GetValue(outpost);
            var toMove = map.mapPawns.AllPawnsSpawned
                .Where(p => p.Faction == Faction.OfPlayer || p.IsPrisonerOfColony)
                .ToList();
            foreach (var pawn in toMove)
            {
                pawn.DeSpawn();
                if (!Find.WorldPawns.Contains(pawn))
                    Find.WorldPawns.PassToWorld(pawn, PawnDiscardDecideMode.KeepForever);
                occupants.Add(pawn);
                // 待驗：囚犯/動物進 occupants 後 VOE SatisfyNeeds/CapablePawns 的處理(spec §7.4)
            }

            // 3) 搬儲存物資 → containedItems，留在哨站當庫存緩衝（枚舉實際 Thing，非 counter 數字）
            var carried = map.listerThings.AllThings
                .Where(t => t.def.CountAsResource && t.IsInAnyStorage() && !t.Destroyed)
                .ToList();
            foreach (var t in carried)
            {
                t.DeSpawn();
                outpost.containedItems.TryAdd(t, false);
            }

            // 4) 銷毀地圖
            //   先把舊 Settlement 世界物件移除，再銷毀地圖
            Current.Game.DeinitAndRemoveMap(map, true);
            if (settlement != null && !settlement.Destroyed)
                settlement.Destroy();

            Messages.Message("CAO.Archived".Translate(), outpost, MessageTypeDefOf.PositiveEvent, false);
        }
    }
}
```

> **實作期必驗（spec §13）**：
> - `outpost.containedItems` 的型別與 `TryAdd` 簽名（反編譯 :743 附近找 `containedItems` 定義）；若非 `ThingOwner`，改對應 API。
> - `DeinitAndRemoveMap` 與 `settlement.Destroy()` 先後順序——可能要先 `Destroy` settlement（它會觸發 `MapParent.Abandon`→`DeinitAndRemoveMap`），則 step 4 改成單呼叫 `settlement.Destroy()`。先用最小破壞試，看 Player.log。
> - `PassToWorld`/`DeSpawn` 對動物與囚犯是否需額外處理（囚犯 `guest` 狀態、動物 `mindState`）。

- [ ] **Step 2：build**

Run: `dotnet build Source/ColonyArchivalOutpost.csproj -c Release`
Expected: 0/0。若 `containedItems`/`TryAdd` 簽名不符→依反編譯修正後再 build。

- [ ] **Step 3：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/Source/ArchivalService.cs derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalOutpost.csproj
git commit -m "feat(cao): ArchivalService archive conversion"
```

---

## Task 5：Gizmo 注入（Harmony postfix Settlement.GetGizmos）

**Files:** Create: `Source/Settlement_GetGizmos_Patch.cs`

- [ ] **Step 1：寫 `Source/Settlement_GetGizmos_Patch.cs`**

```csharp
using System.Collections.Generic;
using HarmonyLib;
using RimWorld;
using RimWorld.Planet;
using Verse;

namespace ColonyArchivalOutpost
{
    [HarmonyPatch(typeof(Settlement), nameof(Settlement.GetGizmos))]
    public static class Settlement_GetGizmos_Patch
    {
        public static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> gizmos, Settlement __instance)
        {
            foreach (var g in gizmos) yield return g;

            // 只在玩家家園 Settlement 且有對應 live 地圖時加按鈕
            if (__instance.Faction != Faction.OfPlayer) yield break;
            Map map = __instance.Map;
            if (map == null || !map.IsPlayerHome) yield break;
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null) yield break;

            if (!tracker.isSampling)
            {
                yield return new Command_Action
                {
                    defaultLabel = "CAO.BeginSampling".Translate(),
                    defaultDesc = "CAO.BeginSampling.Desc".Translate(),
                    icon = TexCommand.ForbidOff,
                    action = () => tracker.BeginSampling()
                };
            }
            else
            {
                var cmd = new Command_Action
                {
                    defaultLabel = "CAO.Archive".Translate(),
                    defaultDesc = "CAO.Archive.Desc".Translate(),
                    icon = TexCommand.ClearPrioritizedWork,
                    action = () => ArchivalService.Archive(map)
                };
                if (!ArchivalService.CanArchive(map, out string reason))
                    cmd.Disable(reason);
                yield return cmd;
            }
        }
    }
}
```

> 待驗：`TexCommand.ForbidOff`/`ClearPrioritizedWork` 圖示存在（原版 `TexCommand`）；不存在則換 `BaseContent.BadTex` 或任一現成圖示。

- [ ] **Step 2：build；commit**

```bash
dotnet build Source/ColonyArchivalOutpost.csproj -c Release
git add derived/rimworld_mods/colony-archival-outpost/Source/Settlement_GetGizmos_Patch.cs derived/rimworld_mods/colony-archival-outpost/Source/ColonyArchivalOutpost.csproj
git commit -m "feat(cao): inject sampling/archive gizmos via Harmony"
```

---

## Task 6：Keyed 語言檔

**Files:** Create: `Languages/English/Keyed/CAO.xml`, `Languages/ChineseTraditional/Keyed/CAO.xml`

- [ ] **Step 1：寫 `Languages/English/Keyed/CAO.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <CAO.BeginSampling>Begin productivity sampling</CAO.BeginSampling>
  <CAO.BeginSampling.Desc>Snapshot current stored resources. Net stockpile growth from now until archival sets the outpost's output rate.</CAO.BeginSampling.Desc>
  <CAO.Archive>Archive into outpost</CAO.Archive>
  <CAO.Archive.Desc>Destroy this colony's map. All colony pawns and stored goods move into an abstract outpost that ships the sampled surplus home.</CAO.Archive.Desc>
  <CAO.Archived>Colony archived into an outpost.</CAO.Archived>
  <CAO.NotPlayerHome>Not a player home map.</CAO.NotPlayerHome>
  <CAO.LastBase>Cannot archive your last home base — there would be nowhere to deliver resources.</CAO.LastBase>
</LanguageData>
```

- [ ] **Step 2：寫 `Languages/ChineseTraditional/Keyed/CAO.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <CAO.BeginSampling>開始產能採樣</CAO.BeginSampling>
  <CAO.BeginSampling.Desc>快照目前儲存資源。從現在到封存的儲存區淨增長，將決定哨站的產出率。</CAO.BeginSampling.Desc>
  <CAO.Archive>封存成哨站</CAO.Archive>
  <CAO.Archive.Desc>銷毀這座殖民地的地圖。所有殖民地 pawn 與儲存物資轉入抽象哨站，按採樣到的結餘持續送回主基地。</CAO.Archive.Desc>
  <CAO.Archived>殖民地已封存成哨站。</CAO.Archived>
  <CAO.NotPlayerHome>非玩家家園地圖。</CAO.NotPlayerHome>
  <CAO.LastBase>不能封存最後一座家園——資源將無處投遞。</CAO.LastBase>
</LanguageData>
```

- [ ] **Step 3：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/Languages
git commit -m "feat(cao): en + zh-Hant keyed strings"
```

---

## Task 7：靜態健檢腳本

**Files:** Create: `tests/healthcheck.py`

- [ ] **Step 1：寫 `tests/healthcheck.py`**（仿 cqf-caravan-redemption；XML well-formed + Def/Keyed 一致）

```python
#!/usr/bin/env python3
"""靜態健檢：XML well-formed、WorldObjectDef defName、Keyed 鍵齊全、csproj Compile 與檔案對齊。"""
import sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = True
def fail(m): 
    global ok; ok = False; print("FAIL:", m)

# 1) 所有 XML well-formed
for p in ROOT.rglob("*.xml"):
    if "/1.6/Assemblies/" in str(p): continue
    try: ET.parse(p)
    except Exception as e: fail(f"XML 壞: {p}: {e}")

# 2) WorldObjectDef defName 存在且＝程式碼引用名
wod = ROOT / "Defs/WorldObjectDefs/Outpost_Sampled.xml"
if wod.exists():
    t = ET.parse(wod).getroot()
    names = [d.findtext("defName") for d in t.findall("WorldObjectDef")]
    if "pas_archival_Outpost" not in names:
        fail("WorldObjectDef defName 應含 pas_archival_Outpost")
    cls = t.find(".//worldObjectClass")
    if cls is None or cls.text != "ColonyArchivalOutpost.Outpost_Sampled":
        fail("worldObjectClass 應為 ColonyArchivalOutpost.Outpost_Sampled")
else:
    fail("缺 Defs/WorldObjectDefs/Outpost_Sampled.xml")

# 3) 兩語言 Keyed 鍵集合一致
def keys(p): return {c.tag for c in ET.parse(p).getroot()} if p.exists() else set()
en = keys(ROOT / "Languages/English/Keyed/CAO.xml")
zh = keys(ROOT / "Languages/ChineseTraditional/Keyed/CAO.xml")
if not en: fail("缺英文 Keyed")
if en != zh: fail(f"Keyed 鍵不一致: 只在EN={en-zh} 只在ZH={zh-en}")

# 4) 程式碼引用的 Translate 鍵都在 Keyed 內
src_keys = set()
for cs in (ROOT / "Source").rglob("*.cs"):
    for line in cs.read_text(encoding="utf-8").splitlines():
        import re
        for m in re.finditer(r'"(CAO\.[\w.]+)"\s*\.Translate', line):
            src_keys.add(m.group(1))
missing = src_keys - en
if missing: fail(f"程式碼用到但 Keyed 缺: {missing}")

print("OK" if ok else "HEALTHCHECK FAILED")
sys.exit(0 if ok else 1)
```

- [ ] **Step 2：執行**

Run: `python3 tests/healthcheck.py`
Expected: `OK`，exit 0。

- [ ] **Step 3：commit**

```bash
git add derived/rimworld_mods/colony-archival-outpost/tests/healthcheck.py
git commit -m "test(cao): static healthcheck"
```

---

## Task 8：部署到遊戲 Mods 並載入

**Files:** 無（部署步驟）

- [ ] **Step 1：實體複製到 `~/rimworld_mods`（使用者要求：實體檔，非 symlink）**

```bash
rsync -a --exclude 'Source/obj/' --exclude 'Source/bin/' \
  derived/rimworld_mods/colony-archival-outpost/ \
  "$HOME/rimworld_mods/colony-archival-outpost/"
```
> 註：權威源在 `pas/derived/...`，`~/rimworld_mods` 是部署副本 → **每次 rebuild/改檔後要重新複製**。`~/rimworld_mods` 需是 RimWorld 實際掃描的來源（RimSort/RimPy 自訂來源，或接進 `<install>/Mods`）。見記憶 feedback_rimworld_mod_deploy_target。

- [ ] **Step 2：在遊戲 Mod 列表啟用順序**：Harmony → VEF → VOE → Colony Archival Outpost。確認載入無紅字（Player.log 找 `[ColonyArchivalOutpost] Harmony patches applied`）。

---

## Task 9：實機端到端驗證（行為驗證集中於此）

**Files:** 無（手動 + Player.log 觀察）。失敗則回對應 Task 修。

- [ ] **Step 1：採樣**：dev mode 開一個有儲存區的殖民地→點 Settlement「開始產能採樣」→確認 gizmo 切成「封存成哨站」。
- [ ] **Step 2：囤貨**：dev spawn 或等數日，讓儲存區某些資源淨增長。
- [ ] **Step 3：封存**：點「封存成哨站」→確認：① 世界出現 outpost 圖標 ② 殖民者/囚犯(仍標囚犯)/動物都在 outpost（點開看 occupants） ③ 封存當下儲存區物資進哨站 `containedItems` 緩衝 ④ 舊基地地圖消失 ⑤ Player.log 零紅字。
- [ ] **Step 4：產出/消耗**：dev 快轉一個 `TicksPerProduction` 週期→確認①正成長資源**投遞回主基地**（收到 VOE 投遞信件，同普通 VOE 哨站）、②負成長資源從哨站 `containedItems` 緩衝扣減、③負成長緩衝見底停在 0 不變負。
- [ ] **Step 4b：食物雙重消耗檢查**：採樣含食物負成長時，快轉觀察食物緩衝只被扣一次（VOE `SatisfyNeeds` 與本 mod 負成長扣減不雙算）；若雙算→回 Task 2 在 `Produce()` 排除需求類資源。
- [ ] **Step 5：存讀檔**：採樣中存讀檔一次、封存後存讀檔一次→確認 snapshot(有號率)/occupants(囚犯身分)/containedItems/tracker 都還在、產出消耗續行。
- [ ] **Step 6：唯一基地**：只剩一張家園時確認「封存」鈕 disabled 且 tooltip 正確。
- [ ] **Step 7：更新 session_log + PROJECT.md 完成定義打勾**。

```bash
git add derived/rimworld_mods/colony-archival-outpost/session_log.md derived/rimworld_mods/colony-archival-outpost/PROJECT.md
git commit -m "docs(cao): in-game verification passed"
```

---

## 自我複查結果（spec coverage）

| spec 需求 | 對應 Task |
|---|---|
| §4 元件（snapshot/outpost/tracker/service/patch/def/keyed） | Task 1/2/3/4/5/2/6 |
| §5 資料流三段 | Task 3(採樣)/4(封存)/2(產出) |
| §6 淨結餘語意＋數學防呆下限 | Task 4 `ComputeSnapshot`（`max(elapsedTicks,2500)`、`delta<=0 continue`） |
| §7 封存轉換（建 outpost/搬 pawn/搬物資/銷毀/唯一基地） | Task 4 |
| §7.4 CanAddPawn 繞過 | Task 4（反射取 occupants 直接 Add） |
| §8 動態 ResultOptions | Task 2 |
| §9 邊界 | Task 4 `CanArchive` + Task 5 gizmo Disable |
| §10 存讀檔 | Task 1/2/3 各 ExposeData + Task 9 Step5 |
| §11 VOE/Harmony 共存 | Task 8/9 觀察 |
| §12 測試 | Task 7(靜態) + Task 9(實機) |
| §13 風險 | Task 4 註記 + Task 9 對應 step |

**待實作期以反編譯坐實的點**（已在任務內標）：`OutpostExtension` XML 欄位名、`containedItems`/`TryAdd` 簽名、`TexCommand` 圖示名、`DeinitAndRemoveMap` vs `settlement.Destroy()` 先後、囚犯/動物 `PassToWorld` 副作用。這些是「analysis 非權威、實作以 projects/ 源碼為準」的具體落點，不是 placeholder。
