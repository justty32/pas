# Vanilla Expanded Framework（VEF）— 淺層總覽

> 分析日期 2026-06-12。目的：**坑點導向**，回答「VEF 的全域 Harmony patch 與系統性接管會在哪裡影響我」。非完整架構書。
> 反編譯產物：`pas/projects/rimworld_mods/vanilla-expanded-framework/decompiled/`（VEF.cs 71,881 行）。引用格式 `VEF.cs:行號`。

## 定位

- packageId `OskarPotocki.VanillaFactionsExpanded.Core`，Workshop 2023507013，整個 Vanilla Expanded 系列的共用引擎。
- 本質是「**一大包 DefModExtension / Comp 工具箱 + 讓這些工具箱生效的全域 Harmony patch**」。絕大多數 patch 都是「查 mod extension → 沒有就直接返回」的旁路型；但 patch 本身**無條件掛在原版熱路徑上**（每個 pawn 生成、每張地圖生成、每 tick）。
- 另內建三個歷史上獨立的 mod：FactionDiscovery（存檔中途補派系）、MVCF（多 verb 框架）、PipeSystem（資源管網）。

## DLL 清單與角色（1.6/Assemblies/）

| DLL | 大小 | 角色 | Harmony ID |
|---|---|---|---|
| `VEF.dll` | 1.4 MB | 主體：30+ 子系統（見下） | `OskarPotocki.VEF`（VEF.cs:2131） |
| `KCSG.dll` | 165 KB | 自訂聚落生成引擎。**已另行分析，本輪跳過** → `vanilla-base-generation-expanded/details/kcsg_engine_takeover.md` | KCSG 自有 |
| `MVCF.dll` | 217 KB | 多 verb 框架。**全手動 patch、feature opt-in**（MVCF.cs:1923, :2033） | `legodude17.mvcf` |
| `PipeSystem.dll` | 191 KB | 資源管網（瓦斯/化學燃料等） | `Kikohi.PipeSystem`（PipeSystem.cs:8772） |
| `Outposts.dll` | 98 KB | VOE 哨站引擎。**已另行分析，跳過** → `vanilla-outposts-expanded/` | — |
| `0ModSettingsFramework.dll` | 31 KB | 設定 UI 框架，純加料 | — |
| `0PrepatcherAPI.dll` | 5 KB | **只是 Prepatcher 的屬性 stub**（`[PrepatcherField]` 等），不含注入邏輯 | — |

## Patch 總量統計（VEF.dll）

- `[HarmonyPatch(...)]` 屬性行 **375**（含同一 patch 的多行宣告）；Prefix/Postfix/Transpiler 方法約 **327** 個。
- 手動 `harm.Patch(...)` **32** 處（多在 OptionalFeatures 啟用時才上，VEF.cs:27525-27537）。
- 載入時序（VEF.cs:1030-1062 `VEF_HarmonyCategories.TryPatchAll`）：
  1. Mod ctor 即 `PatchAllUncategorized()` — 絕大多數 patch 啟動就上，**不看有沒有 mod 用到**。
  2. `LongEventHandler.ExecuteWhenFinished` 後上三類分類 patch：`LateHarmonyPatch`（32 個，def 載入後才上，如 BackCompatibility）、`MoveSpeedFactorByTerrainTag`、`UseStoneChunksAsStuffInRecipes`（後兩類掃 DefDatabase 有人用才上）。
  3. `OptionalFeaturesDef` 機制（VEF.cs:4864-4940）：其他 mod 用 XML `ModDef.Activate` 點名 feature → 呼叫 `ApplyFeature(Harmony)` 或上整個 harmonyCategory。`GetOrGenerateMap` 改地圖尺寸即屬此類（TileMutatorMechanics, VEF.cs:27506）。
- MVCF：**0 個屬性 patch**，全部手動、按 feature 分 24 個 PatchSet（Animals/Apparel/Drawing/Reloading/TargetFinder/…），**只有某個 mod 的 ModDef `ActivateFeatures` 點名才上**（MVCF.cs:2020-2040）。沒人點名＝幾乎零 patch。實務上大量 VE 系 mod 會點名。
- PipeSystem：**20** 個屬性 patch。

## 子系統地圖（VEF.cs 命名空間 → 起始行）

| namespace | 行 | 內容 | 對外影響 |
|---|---|---|---|
| `VEF`（root） | 95 | 啟動、IMergeable def 合併、BackCompatibility、UI source 標註 | def 載入期 |
| `VEF.Weathers/Sounds/Plants/Cooking/Memes/Genes/Hediffs/Apparels/Graphics/AnimalBehaviours` | 2305+ | 各式 extension 工具箱 | 純加料為主，可無視 |
| `VEF.Planet` | 4946 | **MovingBase（會移動的 MapParent 世界物件）**、Caravan_PathFollower 三連 patch、FactionGenerator postfix | 世界地圖/商隊 |
| `VEF.Pawns` | 8084 | Pawn.Kill、戰鬥 | |
| `VEF.Weapons` | 10839 | 武器特性（heavy weapon、weapon traits） | |
| `VEF.Things` | 20005 | DoorTeleporter（跨地圖傳送門）→ patch `Settlement.GetFloatMenuOptions`、`MapDeiniter.Deinit` | 聚落 UI |
| `VEF.Storyteller` | 20505 | raid restlessness：patch `SettlementDefeatUtility.IsDefeated`、`Quest.End`、`Pawn.Kill`、`Storyteller.TryFire`、`IncidentWorker_Raid` | 事件 |
| `VEF.Maps` | 24987 | TickManager.DoSingleTick（特殊地形）、TerrainGrid、**MapGenerator.GenerateMap postfix（ObjectSpawnsDef）**、**GetOrGenerateMap 手動 prefix（地圖尺寸）** | 地圖生成/每 tick |
| `VEF.Factions` | 37624 | **GenStep_Settlement transpiler、TileFinder、Faction 初始關係、RaidStrategy、FactionDiscovery（LoadedGame 補派系）、quest 排除** | 派系（使用者核心區） |
| `VEF.Buildings` | 41099 | 建築工具箱 | |
| `VEF.AestheticScaling` | 66174 | 身體縮放渲染快取（Prepatcher 加速點） | 每幀 |
| `VEF.Abilities` | 66780 | 能力框架 → patch `Caravan.GetGizmos`、`Pawn.TryGetAttackVerb` | 商隊 UI |

## 主文

坑點與全域 patch 細節 → `../details/pitfalls_and_global_patches.md`。
