# DMS 擴充接點：純 XML vs 必須 C# 二分

本檔回答任務核心問題：**想加新機兵/新裝備/新勢力/新物品，純 XML 路徑是什麼？哪些情況才被迫寫 C#？**

## 速查結論

- **DMS 本身是「內容包」，新增內容 99% 是純 XML。** 機兵、武器、裝備、勢力、物品、研究、配方、能力、改裝 — 全部複製既有 Def 改數值即可。
- **行為「積木」住在 Fortified Feature Framework（FFF / `AOBA.Framework`），不在 DMS.dll。** 你想要的行為若 FFF 已有對應 `Fortified.*` 類別 → 純 XML 引用即可；若沒有 → 要寫 C#，且**應寫進 FFF 而非 DMS**。
- **DMS.dll 的 17 個類別都是劇情/任務膠水**（Boss 突襲、文件處理任務、Royalty 授勳/穿梭機），與機兵內容無關，幾乎不需擴充。

## 二分表

| 想做的事 | 純 XML 可做？ | 接點 / 依賴 | 備註 |
|---|---|---|---|
| 新機兵（Automatroid/Drone） | ✅ | 複製 `Things_race/Races_Automatroid_*.xml` 的 ThingDef；`thingClass=Fortified.WeaponUsableMech`；`comps` 用 `Fortified.CompProperties_*` | 行為由 Biotech + FFF 提供 |
| 新人形機（Synthroid） | ✅ | `thingClass=Fortified.HumanlikeMech`（`Races_Synthroid.xml`） | 同上 |
| 機兵可裝哪些武器 | ✅ | `modExtensions` 加 `Fortified.MechWeaponExtension`（`EnableWeaponFilter`） | 純資料過濾器 |
| 新槍械/近戰武器 | ✅ | 複製 `Things_Weapon/*.xml`；`verbClass` 多為原版 `Verb_Shoot`，弧噴用 `Fortified.Verb_ArcSprayProjectile` | 35×Verb_Shoot vs 5×ArcSpray |
| 車載/多管砲塔武器 | ✅ | `Fortified.CompPropertiesMultipleTurretGun` / `Fortified.CompProperties_VehicleWeapon` / `Fortified.TurretMannableExtension` | FFF 提供 |
| 重型可裝備件（背載武器等） | ✅ | `Fortified.HeavyEquippableExtension`（31 處） | FFF 提供 |
| 新裝備/服裝（EVA 服、頭盔） | ✅ | 複製 `Things_Apparel/*.xml`，原版 Apparel | 對應企劃書游騎兵頭盔/EVA 服 |
| 新物品/材料（鉭鎢/石墨稀/組件） | ✅ | 複製 `Things_item/*.xml` + 在生產設施加 `RecipeDef` | 純資料生產鏈 |
| 新生產配方 | ✅ | `RecipeDef`（含 Biotech 母體 `DMS_Recipes_MechGestator_*.xml`） | `<researchPrerequisite>` 控解鎖 |
| 機兵能力（自爆/自修/跳躍/投放） | ✅ | `Abilities/*.xml`，comp 用 `Fortified.CompProperties_Ability*` / `Fortified.ModExtensionJumper` | FFF 提供 |
| 機兵連結 Hediff（死人開關） | ✅ | `Hediffs/Hediffs.xml`，用 `Fortified.Hediff_*` / `Fortified.HediffComp*` | mod 名機制來源 |
| 新研究項目 | ✅ | `Misc/ResearchProject.xml` | 純資料 |
| 新勢力 / 改勢力組成 | ✅ | 複製 `Faction/*.xml`（`DMS_Army` 為範本）；組成靠 `pawnGroupMakers` + PawnKind | 純資料 |
| 新 PawnKind（含 Boss） | ✅ | `Pawnkinds/*.xml`，含 `BossGroupDef`/`PawnKindDef` | 純資料 |
| 空中支援（轟炸/掃射） | ✅ | `AirSupportDef/*.xml` + `Fortified.AirSupportComp_*` / `Fortified.CompProperties_AirSupportSummoner` | FFF 提供 |
| 自然生成地標（機兵墳場/天線） | ✅ | `Prefab/PrefabDef.xml`（`DMS_LightTower`/`DMS_AntennaSegment`）+ Structure | 對應企劃書 |
| 開局劇本（叛逃者） | ✅ | ScenarioDef + `Fortified.Structures.ScenPart_AddStartingStructure` / `ScenPart_ForcedFactionGoodwill` | FFF 提供 ScenPart |
| Ideology 風格/文化 | ✅ | `Ideology/Defs/*`（`MayRequire`） | DLC 條件式 |
| Royalty 頭銜/許可 | ✅（資料）／部分 C# | `Royalty/Defs/Title/*`；獎勵穿梭機 permit 的 worker 是 DMS.dll 的 `RoyalTitlePermitWorker_RewardShuttle` | 既有 worker 可重用 |
| Boss 突襲任務（含 BGM/免馴機師） | ⚠️ 大半 XML，行為靠既有 C# | `Quests/BossGroup.xml` 接 `DMS.QuestNode_Root_BossgroupFactionExposed`；`ModExtension_BossSong`/`NoMechanitorNeed` 是 XML 旗標 | 新增同型 Boss 群＝純 XML；改流程才需碰 C# |
| 文件處理型任務 | ⚠️ 需既有 C# comp | 物品掛 `DMS.CompProperties_QuestWorkable`，任務用 `DMS.QuestNode_TrackDoc` | 重用既有類別＝XML；新邏輯需 C# |
| 全新行為（FFF/原版都沒有的 Comp/Verb/Hediff/Job） | ❌ 必須 C# | 寫新 ThingComp/Verb/HediffComp/JobDriver | **應寫進 FFF（`Fortified.*`）而非 DMS** |

## 必須 C# 的判定法則

只有當「你要的行為，FFF 與原版都沒有對應的 Comp/Verb/HediffComp/ModExtension/Worker 類別」時才需要寫 C#。判定步驟：

1. 先在 FFF（`AOBA.Framework`）反編譯源中搜 `Fortified.*` 有無現成類別。
2. 再看原版（Biotech 機械體、Verb_Shoot、原版 Ability/Hediff comp）能否覆蓋。
3. 都沒有 → 寫 C#。寫的位置應是 **FFF**（讓兄弟內容包 Exosuit/Mobile Dragoon 共用），DMS 只負責用 XML 引用。

## DMS.dll 的 17 個類別（不建議擴充，僅供理解）

| 類別 | 位置 | 用途 |
|---|---|---|
| `CompUseEffect_SummonRaid` / `CompPropertiesUseable_SummonRaid` | `DMS.decompiled.cs:36`/`:75` | 物品召喚 Boss 群 |
| `DMS_DefOf` | `:86` | DefOf 索引 |
| `HarmonyEntry` | `:111` | `Harmony("AOBA.DMS").PatchAll()` |
| `MechanitorPatch` | `:123` | 帶 `NoMechanitorNeed` 的 Boss 群免馴機師 |
| `ModExtension_BossSong` / `NoMechanitorNeed` | `:137`/`:146` | 兩個 DefModExtension（XML 旗標） |
| `QuestNode_Root_BossgroupFactionExposed` | `:149` | 敵對派系發起的 Boss 突襲任務生成 |
| `QuestPart_BossgroupArrivesWithMusic` | `:353` | Boss 到場放 BGM |
| `CompQuestWorkable` / `CompProperties_QuestWorkable` | `:397`/`:577` | 可在研究台「處理」的文件物品 |
| `JobDriver_ProcessQuestWorkable` | `:586` | 搬運+處理文件 Job |
| `WorkGiver_ProcessQuestWorkable` | `:659` | 指派處理文件工作 |
| `QuestNode_TrackDoc` / `QuestPart_TrackDoc` | `:702`/`:731` | 追蹤已處理文件數達標 |
| `RoyalTitlePermitWorker_RewardShuttle` | `:789` | Royalty 呼叫運輸艇 permit |
| `Patch_GenerateBestowingCeremonyQuest` | `:1123` | DMS_Army 授勳改用自製儀式 |
| `QuestNode_Root_PromotionCeremony` | `:1151` | 授勳劇情生成 |

> 全部與「機兵/武器/裝備本體」無關。新增機兵內容**不會**碰到這 17 個類別。
