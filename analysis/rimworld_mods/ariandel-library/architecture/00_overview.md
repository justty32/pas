# Ariandel Library — 架構總覽 (Level 1-2)

## 一句話定位

Ariandel Library 是一個 **RimWorld 1.6「特殊角色框架 (Special Character Framework, SCMF)」函式庫**：透過一組自訂 Def 型別、DefModExtension、ThingComp/HediffComp/AbilityComp 與 Harmony patch，讓下游 mod **多半只靠純 XML** 就能做出「具名、唯一、不會真死、有專屬面板、可召回」的特殊 pawn（Boss／劇情角色／神選者），並附帶心靈能力樹、劇情對話、虛境 (Shroud) 儀式、邊緣傳送襲擊等周邊系統。

> 真相來源：作者隨附的 `User_Manual_26May2026.md` 是一份逐模組對照原始碼的完整框架手冊；本分析已逐項抽樣比對反編譯碼確認其準確。

## 它「是什麼」：與 Empire Refactored 的對照

與既分析過的 Empire Refactored 同屬「**核心庫 ＋ 多個 gated 相容外掛**」架構，但定位不同：
- Empire = 派系／領地玩法框架。
- Ariandel Library = **具名角色 (named pawn) 框架**。其本身不直接提供可玩內容，而是作者自己其他 mod（如 Milira Imperium / 萌螈 / Axolotl）的共用底座。

## 相依鏈 ＋ Gated 子模組

```mermaid
graph TD
    Harmony["brrainz.harmony (硬相依)"] --> Core
    Core["AriandelLibrary.dll<br/>命名空間 AriandelLibrary<br/>22751 行・30 個 HarmonyPatch"]

    Core -.IfModActive Royalty.-> Roy["AriandelLibrary.Royalty.dll<br/>補：心靈能力者偽 HasPsylink"]
    Core -.IfModActive Anomaly.-> Ano["AriandelLibrary.Anomaly.dll<br/>補：方尖碑/血肉/心靈宰殺免疫、儀式角色限制"]
    Core -.IfModActive FacialAnimation.-> FA["AriandelLibrary.FA.dll<br/>補：固定臉部特徵"]
    Core -.IfModActive rjw.menstruation.-> RJW["AriandelLibrary.rjw.menstruation.dll<br/>補：懷孕產物替換"]
    Core -.IfModActive Ancot.MiliraRace.-> Mil["AriandelLibrary.Milira.dll<br/>補：米莉拉種族相容"]
    Core -.IfModActive Ideology.-> Ideo["(僅 Def，無 DLL)"]

    Downstream["下游 mod (純 XML)<br/>如 Sample: UserGuideSCMF"] -->|引用全限定類名| Core
```

子模組載入機制：`LoadFolders.xml` 以 `<li IfModActive="...">1.6/Mods/<x></li>` 把對應資料夾（含其 `Assemblies/*.dll`）疊加進載入清單；DLC/前置 mod 不存在時整個資料夾不載入，故 **無硬相依、不會因缺 DLC 報錯**。各子模組 DLL 各自 `PatchAll` 自己組件內的 patch（例：`AriandelLibrary.Royalty` 的 `Ariandel_AriandelLibrary_Royalty_Patch` 靜態建構式，臨時反編譯 `royalty.cs:30`）。

## 核心子系統分類表

| 子系統 | 對下游的接點型別 | 自訂 Def | 純 XML 可做? | 關鍵類別 (反編譯檔行) |
|---|---|---|---|---|
| **特殊角色框架 (SCMF)** | `SpecialPawnExtension` (PawnKindDef) + 一票保護 Extension | `SpecialPawnTabDef` | ✅ 完整 | `SpecialPawnRegistry:17282`、`SpecialPawnExtension:17406`、`...VoidPawnManager:18043`、`AL_SpecialPawnManager:17512` |
| **固定身分生成** | `FixedIdentityExtension` (PawnKindDef) | — | ✅ | `FixedIdentityExtension:16210`（patch `PawnGenerator:15838`） |
| **pawn 保護/限制 Extension 群** | 14+ 個 `AL_*_Extension` (PawnKindDef) | — | ✅ | `AL_AgeFreeze:16338`、`AL_FloatMenuBlocker:16509`、`AL_Kill_Manager:16657`、`AL_TraitLock:16998` 等 |
| **劇情對話系統** | `HediffCompProperties_AriandelDialogue` + `DialogueOptionCompProperty_*` | `DialogueDef` | ✅ | `DialogueDef:5368` |
| **心靈能力/技能樹** | `AL_AbilityDef`/`AL_Ability`、`CompProperties_PsionicManager`、`CompProperties_AbilityRequire*`、costs | `PsionicTabDef` | ✅ (能力效果若要全新則需 C#) | `PsionicTabDef:12283`、`AbilityExtension_BGTex:2281` |
| **虛境儀式 ＋ 結果池** | `ShroudOutcomeDef`、`CompProperties_ShroudRitualSpot`、`RitualBehaviorWorker_ShroudBreakIn` | `ShroudOutcomeDef` | ✅ (資料驅動抽獎) | `ShroudOutcomeDef:12019` |
| **邊緣傳送襲擊** | `PawnsArrivalModeWorker_EdgeWarp` + `AL_Extension_EdgeWarp` | — | ✅ | `AL_Extension_EdgeWarp:10100` |
| **生產建築 / 武器 ThingComp** | `CompProperties_PeriodicGenerator*`、`CompRestrictedWeapon`、`CompRequireStaticID` 等 | — | ✅ | 反編譯檔 Thing 區 |
| **傷害 worker** | `DamageWorker_*_NoDamageFactor/Scaling` + `AL_NoDamageFactor_Extension`/`AL_DamageExtension_Scaling` | — | ✅ | `AL_NoDamageFactor_Extension:14006`、`AL_DamageExtension_Scaling:14591` |
| **特質 Extension** | `AL_LockSkill`/`AL_NoSkillDecay`/`AL_PsychicShockReflect`/`AL_IgnoreGenePenalty` (TraitDef) | — | ✅ | 反編譯檔 `:22220-22336` |
| **皇權 permit** (gated) | `RoyalTitlePermitWorker_*` + `AL_DropResources_Extension`/`AL_CallAid_Group_Extension` | — | ✅ | `:19919`、`:19925` |
| **NPC tag / 全域元件** | `NPCKindTag` (PawnKindDef) | — | ✅ | `NPCKindTag:13990`、DefOf `AriandelLibDefOf:18615` |

## 原始碼／組件分佈

- **單一巨型主 DLL**：所有核心邏輯集中在 `AriandelLibrary.dll`（22751 行反編譯、命名空間 `AriandelLibrary`、30 個 `[HarmonyPatch]`）。主 patch 群鎖定 `PawnGenerator`、`Pawn.Kill`、`Pawn_HealthTracker.AddHediff`、`FloatMenuOptionProvider_*`、`MentalStateHandler`、`PregnancyUtility`、`Building_SubcoreScanner`、`Recipe_Install/RemoveBodyPart`、`SkillRecord.Interval` 等（反編譯檔 `:13971`~`:22296`）。
- **6 個 gated 子模組 DLL**：皆為數 KB 的小組件，職責＝對「該 DLC/mod 才存在的型別」做 Harmony patch 或補 DefModExtension（見相依鏈圖）。
- **無 Patches/ XML patch**：`1.6/Patches/` 為空；相容性全走 C# Harmony + LoadFolders gating。
- **資產**：AssetBundle 著色器 (`miliraimperium_shaders_*`)、`Content/Sounds`、`Content/Textures`。

## 下游使用慣例（手冊 §1 + 範例驗證）

下游 mod 把 Ariandel Library 設為相依，然後在自己的 XML **以全限定類名引用**，三種注入點：
1. `<modExtensions><li Class="AriandelLibrary.XXX_Extension">` — 掛在 PawnKindDef/ThingDef/TraitDef/DamageDef/PawnsArrivalModeDef/MapGeneratorDef。
2. `<comps><li Class="AriandelLibrary.CompProperties_XXX">` — ThingComp/HediffComp/AbilityComp。
3. 直接替換 worker：`<workerClass>`/`<abilityClass>`/`<tabWindowClass>`。

延伸閱讀：`architecture/01_special_character_framework.md`（核心子系統深入）、`details/extension_points.md`（XML/C# 二分）、`tutorial/01_minimal_special_character.md`。
