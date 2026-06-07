# 擴充接點：純 XML vs 必須 C# 二分

本檔回答下游 mod 的核心問題：**用 Ariandel Library 做東西，純 XML 能到哪？何時必須寫 C#？** 並列出可引用的接點清單。

## 一、總結論

> Ariandel Library 是一個**極度偏向「純 XML 可組裝」**的框架。它的設計哲學就是把行為邏輯封進 C#（庫自己提供），下游只用 XML 引用全限定類名來「組裝」。
>
> **整個「特殊角色」生命週期（宣告 → 固定身分 → 保護開關 → 死亡召回 → 面板 → 劇情招募）可 100% 純 XML 完成**——`Ariandel.UserGuideSCMF` 範例 mod 就是無任何 C# 的活證明（其 About.xml 明言「By using only these XML files—without any C#」）。

## 二、純 XML 可做（庫已提供現成類別，下游只引用）

| 需求 | 純 XML 接點 | 掛在 |
|---|---|---|
| 宣告特殊角色 | `AriandelLibrary.SpecialPawnExtension` | PawnKindDef.modExtensions |
| 角色分頁 | 自訂 `<AriandelLibrary.SpecialPawnTabDef>` Def | (新 Def) |
| 固定姓名/年齡/背景/特質/hediff | `AriandelLibrary.FixedIdentityExtension` | PawnKindDef.modExtensions |
| 不會真死/死後召回 | `AriandelLibrary.AL_Kill_Manager_Extension` | PawnKindDef.modExtensions |
| 全套保護開關 | `AL_AgeFreeze`/`AL_RefuseMentalBreak`/`AL_FloatMenuBlocker`/`AL_HediffImmunity`/`AL_SubcoreScannerBlocker`/`AL_SurgeryBlocker`/`AL_LockConsciousness`/`AL_TraitLock`/`AL_StatLock`/`AL_AzzyPregnancy`/`AL_WarpRetreat`/`AL_LockSkill`-`AL_NoSkillDecay`(後二者掛 TraitDef) | PawnKindDef / TraitDef .modExtensions |
| 劇情對話 | 自訂 `<AriandelLibrary.DialogueDef>` + `HediffCompProperties_AriandelDialogue` + `DialogueOptionCompProperty_*`/`DialogueLineCompProperty_*` | (新 Def) + HediffDef.comps |
| 劇情招募並註冊 | `DialogueOptionCompProperty_RecruitDialogPawn` + `_RegisterDialogPawn` | DialogueDef option |
| 多重消耗/動態冷卻能力 | `abilityClass=AriandelLibrary.AL_Ability` + `CostPsychic`/`CostThingComp` | AbilityDef |
| 能力使用條件 | `CompProperties_AbilityRequireSkill`/`_RequireHediff`/`_OnlyPawnKind`/`_StatRequirement` | AbilityDef.comps |
| 心靈能力樹面板 | 自訂 `<AriandelLibrary.PsionicTabDef>` + `CompProperties_PsionicManager` | (新 Def) + AbilityDef.comps |
| 虛境儀式結果池 | 自訂 `<AriandelLibrary.ShroudOutcomeDef>`（+內建 `ShroudOutcome_Generator` worker）、`CompProperties_ShroudRitualSpot` | (新 Def) + ThingDef.comps |
| 口袋地圖結果 | `ShroudOutcomeCompProperties_PocketMap` | ShroudOutcomeDef.comps |
| 邊緣傳送襲擊 | `workerClass=PawnsArrivalModeWorker_EdgeWarp` + `AL_Extension_EdgeWarp` | PawnsArrivalModeDef |
| 自動生產建築 | `CompProperties_PeriodicGenerator`/`_WithResources`/`_Selectable` | ThingDef.comps |
| 武器限制/能量消耗 | `CompRestrictedWeapon`/`CompUserRestriction`/`CompRequireStaticID`/`CompTimeSkillGain` | ThingDef.comps |
| 自訂傷害 | `DamageWorker_*_NoDamageFactor`/`_Scaling` + `AL_NoDamageFactor_Extension`/`AL_DamageExtension_Scaling` | DamageDef |
| NPC tag 查詢 | `AriandelLibrary.NPCKindTag` | PawnKindDef.modExtensions |
| 地圖音樂 | `AL_ModExtension_MapCompPlayMusic` | MapGeneratorDef |
| 皇權 permit (gated) | `RoyalTitlePermitWorker_*` + `AL_DropResources_Extension`/`AL_CallAid_Group_Extension` | RoyalTitlePermitDef |

DLC/前置 mod 專屬接點用 XML 的 `MayRequire="..."` 屬性 gate（範例已示範，見 `tutorial`）：
- `AriandelLibrary.Anomaly.AL_RitualRoleRestriction_Extension` / `_ObeliskDuplicationBlocker_Extension` / `_FleshbeastReflect_Extension` / `_PsychicSlaughterReflect_Extension`（`MayRequire="Ludeon.RimWorld.Anomaly"`）
- `AriandelLibrary.rjw.menstruation.AL_RJW_Menstruation_Pregnancy_Extension`（`MayRequire="rjw.menstruation"`）

## 三、必須 C#（庫無對應現成類別時）

| 情境 | 為何需 C# |
|---|---|
| **全新能力效果** | 庫只提供「消耗/冷卻/條件」骨架 (`AL_Ability`)；若要全新的命中效果，仍需自寫 `CompProperties_AbilityEffect_*`（或用原版/其他 mod 的）。 |
| **全新對話選項行為** | `DialogueOptionComp` 體系可繼承擴充；庫內建的招募/跳轉/播音等以外的副作用需自寫 comp 子類。 |
| **全新虛境結果類型** | `ShroudOutcomeDef.workerClass` 預設 `ShroudOutcome_Generator` 已涵蓋能力/事件/hediff/物品/pawn 抽獎；非此模式的結果需自寫 worker 或 `ShroudOutcomeComp`。 |
| **武器自訂能量欄位** | `CostThingComp`/`CompRestrictedWeapon` 可讀「既有 ThingComp 的欄位」，但那個能量 ThingComp 本身需由你或他 mod 用 C# 提供。 |
| **把真身綁進管理器的非對話途徑** | 若不走「對話招募」也不走 hediff 自動驗證，要在自訂事件/quest 裡呼叫 `VoidPawnManager.CheckAndRegisterPawn(pawn)` 需 C#。 |
| **改框架本身行為** | 任何超出既有欄位的邏輯（如自訂面板版面、改召回冷卻演算法）。 |

## 四、可繼承/可實作的接點（C# 進階）

> 多為 `internal`/`public` 反編譯所得；實際可見性需以官方公開 API 為準，下游通常 **以全限定類名在 XML 引用即可，不需引組件**。

| 基類/介面 | 用途 | 反編譯檔行 |
|---|---|---|
| `DialogueDef : Def` | 對話 Def | `:5368` |
| `ShroudOutcomeDef : Def` | 虛境結果 Def | `:12019` |
| `PsionicTabDef : Def` / `SpecialPawnTabDef : Def` | 分頁 Def | `:12283` / `:17277` |
| `SpecialPawnExtension : DefModExtension` 等 30+ Extension | 各掛點 | 見 `00_overview` |
| `AL_Ability`（擴 vanilla Ability）+ `IAbilityCost`(`CostPsychic`/`CostThingComp`) | 自訂能力消耗 | — |
| `ShroudOutcome_Generator`（預設 outcome worker） | 虛境結果產生 | — |
| `AriandelLibrary_GameComponent_VoidPawnManager : GameComponent, IThingHolder` | 真身註冊 API (`CheckAndRegisterPawn`/`SendPawnToVoid`/`SendToShroud`) | `:18043` |
| `SpecialPawnRegistry`（靜態，`GetStaticID(PawnKindDef)`） | kind→staticID 查詢 | `:17282` |
| `AriandelLibDefOf`（DefOf 入口） | 內建 Def 引用 | `:18615` |

## 五、要點與陷阱（手冊 §18 + 源碼）

- 多數快取類在 `StaticConstructorOnStartup` 掃全 Def；改 XML 後須**重啟遊戲**才生效。
- `uniqueID`/`staticID` 是唯一身分，**勿重複、勿亂改**；重複會被當複製人清除（`VoidPawnManager` 真身判定，`:18043`）。
- 紋理路徑**不含 `.png`**。
- 生產建築需有 `CompThingContainer`、有電、容器未滿才生產（`WithResources` 版另需足夠資源且玩家未關填充）。
- 子模組 patch 不存在缺 DLC 風險：`LoadFolders.xml` 的 `IfModActive` + XML 的 `MayRequire` 雙重 gate。
