# 擴充接點：純 XML vs 必須 C# 二分

> 行號指 `projects/rimworld_mods/caravan-adventures/decompiled/CaravanAdventures.decompiled.cs`；資料路徑指 mod 安裝目錄 `.../2558957509/1.6/`。

## 結論先講
Caravan Adventures 是一個**重 C# 的玩法 mod**。它的 `Story/` 與 `Expansions/` 目錄**不是**「劇情用 DSL、引擎用 C#」那種乾淨分層——`Story/` 只是劇情的**素材庫 (asset/stat library)**，而**劇情的流程、轉移、編排 100% 寫死在 DLL 的 `StoryWC` 狀態機**。`Expansions/` 是一個 C# 外掛框架的薄資料宣告，真正 reskin 邏輯也在 C#。

因此「做衍生劇情純 XML 能到哪」的答案是：**幾乎到不了任何地方**。純 XML 只能調素材數值，無法新增或改寫劇情章節。

## 純 XML vs 必須 C# 二分表

| 想做的事 | 純 XML 可行? | 接點 / 理由 |
|---|---|---|
| 改 Boss 數值/外觀/掉落 | 是 | `Story/Defs/BossBodyAndRaceDefs/`、`PawnKindDefs/`、`BossAbilityDefs/`，標準 Def 覆蓋 |
| 改神殿地圖外觀/散佈物 | 部分 | `Story/Defs/MapGeneration/`、`ThingDefs/ShrineThingDefs.xml` 可改素材，但 GenStep 行為（`GenStep_ScatterMasterShrines :9166`）在 C# |
| 改自訂異能數值 | 是 | `Story/Defs/AbilityDefs/Abilities.xml`；但異能效果 `CompAbilityEffect_*`（`:22026+`）在 C# |
| 改派系關係/陣營 | 是 | `Story/Defs/FactionDefs/FactionDefs.xml` |
| 改露營帳篷的素材成本/外觀 | 是 | `Defs/ThingDefs/CampThingDefs.xml` |
| **新增一個劇情章節** | **否** | 章節定義是 `flagsToAdd` 硬編清單（`:9475`）+ `CheckCanStart*` guard + `QuestCont_*` 控制器，全在 C# |
| **改劇情觸發條件/順序** | **否** | 轉移條件寫死在 `WorldComponentTick`（`:9602`）的 if 鏈 |
| 改某事件的觸發機率 | 否（baseChance=0） | `Story/Defs/IncidentDefs/StoryIncidents.xml` 把 baseChance 設 0，**完全由 C# 狀態機手動觸發**，不走原生 IncidentMaker |
| **改對話內容/分支** | **否** | `TalkSet` 用 `className`/`methodName`（`:8903`）反射呼叫 C# 方法；對話文本走 Languages，但分支邏輯在 C# |
| 替換機械族成蟲族（reskin 全 mod） | 半 | 見下「Expansions」 |
| 翻譯／改文案 | 是 | `Languages/`（標準 RimWorld i18n） |
| CombatExtended 武器相容 | 是 | `CEPatches/Patches/*.xml`，標準 PatchOperation |

## QuestScript / Incident 為何不可純 XML 擴充

1. **QuestScriptDef 是空殼**：`Story/Defs/QuestScriptDefs/QuestScriptDefs.xml` 5 個 def 全指向 `QuestNode_Temp`，其 `RunInt` 直接 `return true`（`:11611`）。RimWorld 原生的 QuestNode/QuestPart 樹（資料驅動 DSL）在此被架空，新增 QuestScriptDef 不會接到任何邏輯。
2. **Incident baseChance=0**：`StoryIncidents.xml` 三個 incident（`CAFriendlyCaravan`/`CAMechRaidMixed`/`CAUnusualInfestation`）都 `baseChance=0`，由 `StoryWC` 在對的劇情階段用 C# 主動 `FireIncident`。它們的 `workerClass` 也都指向自訂 `IncidentWorker_*`（`:5447`、`:5574`、`:5536`）——換成純 XML 的原生 worker 會少掉劇情鉤子。

## Story/ 目錄的真正角色：素材庫，非劇情 DSL
`Story/Defs/` 18 個子目錄的內容是「劇情**用到**的東西長什麼樣」：Boss 的 race/body/ability/projectile/sound、神殿與 shrine thing、psycast hediff、faction、pawnkind、mapgen 配置、game condition。這些是標準 Def，可被 `PatchOperation` 覆蓋或新增**素材**——但它們是被 `StoryWC` 透過 `StoryDefOf`（`:6064`）/`StoryQuestDefOf`（`:11866`）/`CaravanStorySiteDefOf`（`:8868`）等 DefOf 以**寫死的 defName 引用**消費的。也就是說：你能改一座神殿的外觀，但不能用 XML 多塞一座有新流程的神殿（流程不存在於 XML）。

## Expansions/ 目錄的真正角色：C# 外掛框架的資料宣告
- `Expansions/RM/Defs/Defs/Expansion.xml` 宣告一個自訂 `ExpansionDef`（class `CaravanAdventures.Expansions.ExpansionDef`，`:4006`）：
  ```xml
  <CaravanAdventures.Expansions.ExpansionDef>
    <defName>ExpRimedieval</defName>
    <assemblyName>Rimedieval</assemblyName>   <!-- 用「目標 mod 的組件名」做偵測 -->
    <replacesContent>true</replacesContent>
    <expSettingsDef>ExpRimedievalSettings</expSettingsDef>
  </CaravanAdventures.Expansions.ExpansionDef>
  ```
- `ExpansionManager.ActiveExpansion`（`:4024`）：偵測 Rimedieval 安裝（`CompatibilityPatches.RMInst`）→ 回傳對應 ExpansionDef。
- `ExpSettingsDef`（`:4041`）只暴露**極少數可換的引用**：`ancientMechSignalPawnKind`、`primaryEnemyFactionDef`、`bossDefPrefix`、`endBossPawnKindDef`——即「把劇情中的敵人從機械換成蟲族」。實際替換邏輯讀這些欄位，仍在 C#。
- 配套一個 `PatchOperationFindMod` 補丁（`Expansions/RM/Patches/Patches/RMChangeBossesToInsects.xml`）把基底機械 `fleshType` 改 Insectoid。

**判讀**：Expansions 是「為已知第三方 mod 量身做的相容／reskin 槽位」，不是開放給玩家自製劇情的擴充點。要新增一個 Expansion，必須 (a) 寫一個 `ExpansionDef` XML + ExpSettingsDef，且 (b) 該 reskin 只能在 C# 已預留的少數欄位範圍內生效；超出範圍（新章節、新流程）仍需改 DLL。

## 給 Create 模式的建議（衍生方向）
1. **純 XML 衍生**：合理目標僅限「reskin / 數值平衡 / 翻譯 / 新 Boss 外觀 / CE 相容補丁」。可仿 `Expansions/RM` 寫一個自己的 ExpansionDef（例如把機械換成別的種族），這是門檻最低、作者明確支援的擴充點。
2. **要新劇情章節**：必須 fork DLL，在 `flagsToAdd`（`:9475`）加旗標、在 `WorldComponentTick`（`:9602`）加 guard、新增一個 `QuestCont_*` 控制器並掛進 `QuestCont`（`:10982`）。屬於 C# 開發，非 XML。
3. **對話衍生**：新增可對話 NPC 需掛 `CompTalk` + 配 `TalkSet`（指定 className/methodName），分支邏輯必寫 C#；只有文本可走 `Languages/`。
