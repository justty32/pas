# VEF 坑點與全域 Harmony Patch（坑點導向）

> 視角：自家 mod 集中在 WorldObject/Settlement 子類、聚落地圖生成（GenStep/MapParent）、商隊 arrival action、VOE 哨站衍生、派系生成/敵對/倒戈。
> 引用 `VEF.cs:行號` = `pas/projects/rimworld_mods/vanilla-expanded-framework/decompiled/VEF.cs`。KCSG、Outposts 已另行分析，此處不重複。

## 0. 先記住的整體性質

- VEF patch 九成是「**postfix 查 DefModExtension，沒有就 return**」的旁路型：你的 def 不掛 VEF extension 就不改你的*數值*，但 **patch 程式碼本身照跑**，會在你的呼叫路徑上多一層（NRE 前科即出在這種「照跑」的 postfix）。
- 危險的不是單一 patch，而是它掛的位置：`PawnGenerator`、`MapGenerator.GenerateMap`、`FactionGenerator.NewGeneratedFaction`、`GameComponentUtility.LoadedGame` 這些**你的 mod 一定會路過的咽喉**。

## 1. 世界地圖 / 聚落 / 地圖生成（你的核心區）

### 1.1 `GetOrGenerateMapUtility.GetOrGenerateMap` — 有 prefix，會改地圖尺寸
- 手動 patch（VEF.cs:27530-27537），prefix `TweakMapSizes`（VEF.cs:27008-27033）：依 tile 上的 `TileMutatorDef` + `TileMutatorExtension` 以 `ref IntVec3 size` **改寫即將生成的地圖尺寸**（倍率或直接 override X/Z）。
- **條件式**：屬 OptionalFeature「TileMutatorMechanics」（VEF.cs:27506 `ApplyFeature`），要有 mod 用 `ModDef.Activate` 點名才上；同包還 patch `Game.InitNewGame`（transpiler）、`WorldPathGrid.CalculatedMovementDifficultyAt`、`TileMutatorWorker_River` 等。
- 對你：拜訪/哨站 mod 經 `GetOrGenerateMap` 生地圖時，**地圖尺寸可能不是你要求的值**——任何掛了 TileMutatorExtension 的 tile mutator 都會乘上去。若你的 GenStep 對地圖尺寸有假設（固定佈局、邊距），這裡會踩。
- 除生命週期以外：VEF **沒有** patch `MapParent.MapGeneratorDef`/`GetOrGenerateMap` 的「換生成器」邏輯——那是 KCSG.dll 幹的（已分析）。`MapParent` 生命週期（PostRemove/ShouldRemoveMapNow/CheckRemoveMapNow）原版方法 VEF 主體只動了 `Site.ShouldRemoveMapNow`（見 1.4）。

### 1.2 `MapGenerator.GenerateMap` — postfix 對每張地圖加掛生成
- VEF.cs:28084-28100：postfix 在 `LongEventHandler.ExecuteWhenFinished` 裡跑 `DoMapSpawns(__result)`，依 `ObjectSpawnsDef`（biome/地形/離殖民地距離過濾）在**任何剛生成的地圖**上灑東西（含 pawn：VEF.cs:28221 走 `PawnGenerator.GeneratePawn`）。
- 對你：你的聚落地圖、哨站地圖**也是地圖**，會吃到別的 VE mod 定義的 ObjectSpawnsDef（多半是動物/雜物）。佈局精確的 KCSG 聚落上多出雜物即源於此類。錯誤被 try/catch 包住只 log（VEF.cs:28090-28097），不會炸生成。

### 1.3 `GenStep_Settlement.ScatterAt` — transpiler 換掉 BaseGen 符號
- VEF.cs:38534-38558：transpiler 找到 `ldstr "settlement"`，插入呼叫 `SettlementGenerationSymbol(original, faction)`——若派系 `FactionDefExtension.settlementGenerationSymbol` 非空，**整個聚落生成的根符號被換掉**。
- 對你：若你的 GenStep 繼承/重用原版 `GenStep_Settlement`，而目標派系被任何 mod 掛了這個 extension（或 KCSG 的 CustomGenOption），版面整個不是原版。自寫 GenStep 不經 `GenStep_Settlement.ScatterAt` 則不受影響。

### 1.4 `Site.ShouldRemoveMapNow` — postfix 攔截世界物件移除
- VEF.cs:20517-20543：postfix 若任何進行中 quest 有 `QuestPart_KeepSite` 指向該 Site，把 `alsoRemoveWorldObject` 改回 false。只影響 `Site` 子類；你的 Settlement/MapParent 子類不在此列，但若你**繼承 Site** 做據點就要知道移除可能被否決。

### 1.5 `Settlement.GetFloatMenuOptions` / `MapDeiniter.Deinit` — DoorTeleporter 掛件
- VEF.cs:46342-46368：`Settlement.GetFloatMenuOptions` postfix——聚落**有地圖且圖上有 DoorTeleporter** 時，往商隊右鍵選單 concat 傳送選項。你的 Settlement 子類若覆寫 `GetFloatMenuOptions`，postfix 仍會包在你的結果外面（`HasMap` 才動作，平時 no-op）。
- VEF.cs:46371-46376：`MapDeiniter.Deinit` prefix 清掉該地圖的 DoorTeleporter 註冊。地圖卸載路徑多一步，但只動它自家集合。

### 1.6 `SettlementDefeatUtility.IsDefeated` — postfix（storyteller 加料）
- VEF.cs:20938-20957：postfix 只在「已判定打下據點」後記時間戳（raid restlessness 機制），**不改判定結果**。你的聚落攻陷邏輯安全；但注意它假設 `Current.Game.GetComponent<StorytellerWatcher>()` 存在。

### 1.7 地圖每 tick 面
- `TickManager.DoSingleTick` prefix+postfix（VEF.cs:26088-26119）：**每個 game tick** 開一支 Stopwatch、對每張地圖取 `SpecialTerrainList` 更新特殊地形。對你無行為影響，但這是「VEF 常駐在 tick 路徑」的代表——profiling 時會看到它。
- `Storyteller.TryFire` prefix（VEF.cs:21248-21257）：`fi?.def == null` 時**靜默吞掉 incident**。若你手排 FiringIncident 而 def 沒填好，它不噴錯直接消失——除錯時的隱形坑。

## 2. 派系（生成 / 敵對 / 倒戈）

### 2.1 `FactionGenerator.NewGeneratedFaction` — 兩個 postfix
- VEF.cs:5124-5158（VEF.Planet）：新派系生成後，掃 `MovingBaseDef.baseFaction == 該派系 def` → **自動在世界地圖灑 MovingBase（會動的 MapParent 世界物件）**。只對 Surface layer。你 runtime `NewGeneratedFaction` 生派系也會觸發；除非有 VE mod 為你的派系定義 MovingBaseDef，否則迴圈空跑。
- VEF.cs:31652-31659：postfix 跑 `TaggedDefProperties.GenerateTags(__result)`。注意**沒有 null 防護**：`__result.def` 直接解參照——若其他 mod 的 prefix 讓 `__result` 為 null 會 NRE（與前科同型）。
- 你動態生派系＝必經這兩個 postfix。世界生成期間炸掉的 NRE 前科（VEF/VPE PawnGenerator postfix 鏈）同屬這種「無條件 postfix 假設結果完好」的模式。

### 2.2 `Faction.TryMakeInitialRelationsWith` — postfix 改初始好感
- VEF.cs:38759-38791（`[HarmonyAfter(alien_race)]`）：依**雙方** `FactionDefExtension.startingGoodwillByFactionDefs` 覆寫 baseGoodwill/kind。對你：你生成派系時的初始敵對狀態可能被**別的 mod 對你的 factionDef 的設定**改掉；之後 runtime 的 `SetRelation`/倒戈不受影響（只掛初始關係建立點）。

### 2.3 FactionDiscovery — `GameComponentUtility.LoadedGame` postfix（中途補派系）
- VEF.cs:39524-39596：**每次讀檔**掃全 `FactionDef`：
  - `ForcedFactionData.forceAddFactionIfMissing` → **不問玩家直接補生派系＋聚落**（`NewFactionSpawningUtility.SpawnFactions`，VEF.cs:39829）。
  - 其餘「存檔裡數量為 0 且未被忽略」的 def → 彈 `Dialog_NewFactionSpawning` 問玩家要不要補。
  - 跳過條件：`isPlayer`、`hidden && requiredCountAtGameStart<=0`、硬編 defName `PColony`（VEF.cs:39814-39821）。
  - `StartedNewGame` postfix（VEF.cs:39599-39613）把開局當下所有 def 加入忽略清單，所以對話框只針對「中途加 mod 的派系」。
- 對你（最直接的派系坑）：
  - 你 mod 若有「**不該被自動補生**的 FactionDef」（模板派系、動態生成專用、劇情派系），玩家中途裝 mod 讀檔會被提示生成它，或被 ForcedFactionData 邏輯誤掃 → 設 `hidden=true`（且 `requiredCountAtGameStart<=0`）才能躲掉。
  - 你動態移除派系（倒戈吞併、滅國）後，**下次讀檔 VEF 會發現數量 0 又跳對話框**——除非 hidden 或玩家按過 ignore。
- 同檔還 patch `WorldFactionsUIUtility.DoRow/DoWindowContents`（VEF.cs:38814/:38833）：世界生成 UI 阻止移除 forced 派系、插警告字串。

### 2.4 襲擊與 quest 的派系過濾
- `IncidentWorker_RaidEnemy.ResolveRaidStrategy` postfix（VEF.cs:38731-38756）：派系有 `FactionDefExtension.allowedStrategies` → **重抽並覆寫 `parms.raidStrategy`**；抽不到就 log error + 強制 ImmediateAttack。你手排對玩家的襲擊若走這個 worker，策略可能被換。
- `SiteMakerHelper.FactionCanOwn`（VEF.cs:38560-38576）、`QuestNode_GetFaction.IsGoodFaction`（VEF.cs:38578）、`QuestNode_GetPawn.IsGoodPawn`（VEF.cs:38598）、`QuestNode_Root_DistressCall.FactionUsable`（VEF.cs:38625）：`excludeFromQuests` 一刀切把派系從 quest/site 池剔除。你選派系若重用這些原版 helper，池子可能比你想的小。
- `TileFinder.RandomSettlementTileFor`（VEF.cs:38629-38700）：prefix 把 faction 存進 **static 欄位** `factionToCheck`，再 postfix 原版內部的 tile 評分 lambda，依 `FactionDefExtension.disallowedBiomes` 等把分數歸零。對你：(a) 你呼叫 `RandomSettlementTileFor` 為自家派系/哨站找 tile 時，落點規則被 extension 左右；(b) static 狀態非執行緒安全——別在 worker thread 呼叫它。

## 3. PawnGenerator / 前科區

VEF 對 PawnGenerator 掛了三個 patch，**每個 pawn 生成都跑**（含你的聚落駐軍、商隊成員、哨站人員）：

| patch | 位置 | 行為 |
|---|---|---|
| `GenerateNewPawnInternal` postfix | VEF.cs:71295-71372 | 依 `PawnKindAbilityExtension` 給 pawn 加 implant hediff＋能力。有 `__result == null` 防護；之後鏈式解參照 `kindDef`→extension→`health` 多層 |
| `GenerateGenes` postfix | VEF.cs:37133-37150 | 對每個 active gene 跑 `GeneUtils.ApplyGeneEffects` |
| `GeneratePawnRelations` prefix | VEF.cs:34635-34648 | 性轉基因 pawn 直接跳過原版關係生成（return false） |

- 前科：使用者排查過「VEF/VanillaPsycastsExpanded 的 PawnGenerator postfix NRE 炸世界生成」（cqf-caravan-redemption session）。模式一致——**postfix 鏈上任何一環對半成品 pawn 解參照失敗，整個世界生成/地圖生成跟著炸**，而且 stack trace 指向 PawnGenerator 而非肇事 mod。
- 對你的防守：自家批量生 pawn 的地方（聚落生成、warband 式實體化）包 try/catch 並在 bug report 模板要求玩家提供完整 modlist；測試矩陣固定加 VEF＋VPE。

## 4. 商隊（Caravan / arrival action）

- VEF **不 patch** `CaravanArrivalAction` 體系本身；自家 arrival action 子類（`CaravanArrivalAction_MovingBase`、`CaravanArrivalAction_UseDoorTeleporter`）純加料。你的 arrival action 安全。
- `Caravan_PathFollower` 三連 patch（VEF.Planet，服務 MovingBase 追蹤）：
  - `ExposeData` postfix（VEF.cs:5069-5082）：用 **static dict** 對每個 path follower 多存一個 `caravanToFollow` 節點——別人的存檔裡會出現 VEF 的字段，你解析 caravan 存檔 XML 時別假設欄位集合。
  - `PatherTickInterval` prefix（VEF.cs:5084-5109）：每次商隊 path tick 查 dict；**只對曾被指向 MovingBase 的商隊**改道（目的地 tile 跟著移動目標重設 `StartPath`）。一般商隊每 tick 多一次 dict 查找而已。
  - `StartPath` postfix（VEF.cs:5111-5122）：每次 StartPath 檢查 dict，目的地變了就解除追蹤。你的 mod 對商隊下 `StartPath` 指令完全相容——頂多把 VEF 的 MovingBase 追蹤踢掉（這是它預期行為）。
- `Caravan.GetGizmos` postfix（VEF.cs:69387-69412）：為商隊成員的 VEF 能力加 gizmo，迭代所有 pawn 的 comp，純加料。

## 5. 載入期 def mutation（PatchOperation 之外）

- `Def/ThingDef/HediffDef/StorytellerDef/WorldObjectDef.ResolveReferences` prefix（VEF.cs:765-890）：對 `modExtensions`/`comps` 清單做 **IMergeable 合併**（同型別 extension 多份合一）。只動實作 IMergeable 的型別，一般 mod 無感；但要知道**你的 WorldObjectDef.comps 清單在 ResolveReferences 前會被掃一遍**。
- `BackCompatibility.BackCompatibleDefName/GetBackCompatibleType` postfix（VEF.cs:542/:580，LateHarmonyPatch）：提供 XML 驅動的 def 改名/型別轉向（存檔相容工具）。讀檔時 def 名解析多一層查表。
- 啟動 static ctor（VEF.cs:2110-2122）：`PawnShieldGenerator.Reset`、`ScenPartUtility.SetCache`、`ResearchProjectUtility.AutoAssignRules`——研究自動分 tab 等 def 級調整。

## 6. Prepatcher / 0PrepatcherAPI

- `0PrepatcherAPI.dll` 只是屬性定義（`[PrepatcherField]`/`[ValueInitializer]`），**自身不做任何注入**。
- 唯一用點：`VEF.AestheticScaling` 的 `CachedPawnDataExtensions.GetCachePrePatched`（VEF.cs:66210-66216）——裝了 Zetrith 的 Prepatcher（`zetrith.prepatcher`，啟動時偵測，VEF.cs:2116）時，這個 extension method 會被改寫成 **Pawn 上真正注入的欄位**，pawn 渲染縮放快取變 O(1) 欄位讀取。
- **退化行為**：沒裝 Prepatcher 時走 `PawnDataCache` 的字典快取＋ThreadStatic 迷你快取（VEF.cs:66218-66250）。**行為等價、純效能差異**，不影響相容性。對你：零風險，可無視。
- AestheticScaling 本身倒是掛在每幀路徑：`PawnRenderer.ParallelGetPreRenderResults`、`BaseHeadOffsetAt`（VEF.cs:34676）、`PawnUIOverlay`、`SelectionDrawer`（VEF.cs:35950-66174 區段）——渲染數值被 body size 快取乘算，與世界/派系邏輯無關。

## 7. MVCF（一段話）

MVCF 的 patch 面全在**武器/verb/戰鬥 AI**：`Verb`、`VerbTracker`、`Pawn_MeleeVerbs`、`Pawn.TryGetAttackVerb`、`AttackTargetFinder`/`TargetFinder`、`JobGiver_AIFightEnemy`、`Pawn_DraftController` gizmo、彈藥 reload。關鍵是它**完全 opt-in**：0 個屬性 patch，24 個 PatchSet 按 feature 手動上（MVCF.cs:2033-2040），只有某個 mod 的 `ModDef.ActivateFeatures` 點名（或用了 deprecated reload comp，MVCF.cs:173/:280）才生效——但實務上 VE 系 mod 幾乎一定會點亮幾個 feature。對你的世界/派系/商隊領域**無交集**；唯一沾邊的是 VEF 自己以 `[HarmonyBefore("legodude17.mvcf")]` patch `Pawn.TryGetAttackVerb`（VEF.cs:71374-71395），autocast 能力可能替換 pawn 攻擊 verb——只影響戰鬥行為。

## 8. PipeSystem（一段話）

20 個屬性 patch，面向**建築/資源網**：`Thing.SpawnSetup`（transpiler，改全體 Thing 生成時的堆疊合併分支，PipeSystem.cs:5724）、`Thing.PostMapInit`（prefix，超堆疊截斷）、`CompGlower` ×2（管網供能發光）、`Designator_Build/Install`、`DesignationCategoryDef`、`Game`、`CompAffectedByFacilities`、`Widgets.DefIcon`。對你的領域基本無交集；唯一要記的是 **`Thing.SpawnSetup` 的 transpiler 掛在超熱路徑**，若你也 transpile 同方法要測共存（transpiler 疊 transpiler 是經典炸點）。

## 9. 可無視的子系統（純加料、不碰你的路徑）

`VEF.Sounds`、`VEF.Weathers`（除非做天氣）、`VEF.Plants`、`VEF.Cooking`、`VEF.Memes`、`VEF.Genes`/`Hediffs`/`Apparels`（pawn 屬性工具箱）、`VEF.AnimalBehaviours`、`VEF.Graphics`（材質/shader 工具）、`VEF.Research`（UI 標註）、`VEF.Buildings`、`VEF.Abilities`（除非用它的能力框架）、`0ModSettingsFramework`、`0PrepatcherAPI`、武器特性、`VEF.AestheticScaling`（渲染）。這些對 WorldObject/聚落/商隊/派系**零交集**。

## 10. 坑點風險表（高 → 低）

| # | VEF 子系統 | 被 patch 的原版面 | 影響你的哪個 mod | 建議 |
|---|---|---|---|---|
| 1 | FactionDiscovery | `GameComponentUtility.LoadedGame` postfix（VEF.cs:39524）每次讀檔掃 FactionDef、彈補生對話框／強制補生 | 派系生成/倒戈：動態生滅派系、模板 FactionDef 會被誤掃 | 不該補生的 def 設 `hidden=true` 且 `requiredCountAtGameStart<=0`；測試「讀檔→是否跳對話框」 |
| 2 | PawnGenerator 三 patch（＋VPE 等疊加） | `GenerateNewPawnInternal`/`GenerateGenes` postfix、`GeneratePawnRelations` prefix（VEF.cs:71295/:37133/:34635） | 所有批量生 pawn 的點（聚落駐軍、哨站、商隊）；前科 NRE 炸世界生成 | 自家生成包 try/catch；測試矩陣固定加 VEF+VPE；bug 模板要 modlist |
| 3 | TileMutator OptionalFeature | `GetOrGenerateMap` prefix 改 `ref size`（VEF.cs:27530/:27008） | 拜訪/哨站 mod：地圖尺寸假設失效 | GenStep 不要假設固定尺寸；用實際 `map.Size`；和 VE 生態 mod 同開測一次 |
| 4 | ObjectSpawns | `MapGenerator.GenerateMap` postfix DoMapSpawns（VEF.cs:28084） | 聚落地圖生成：圖上多出非你規劃的物件/動物 | 視覺驗收時帶 VE 動物 mod 測；不要假設地圖只有你生成的東西 |
| 5 | Factions 聚落生成 | `GenStep_Settlement.ScatterAt` transpiler 換根符號（VEF.cs:38534）；＋KCSG（另文） | 聚落地圖生成：重用原版 GenStep 時版面被換 | 自家版面用自寫 GenStep，不重用 `GenStep_Settlement`；或檢查目標派系有無 extension |
| 6 | Factions 落點/關係 | `TileFinder.RandomSettlementTileFor`（static 狀態，VEF.cs:38629）、`Faction.TryMakeInitialRelationsWith` postfix（VEF.cs:38759） | 派系生成：落點被 disallowedBiomes 過濾；初始好感被覆寫 | 落點要求嚴格就自寫 tile 選擇；初始關係在生成後自己 `SetRelation` 蓋一次；勿在 thread 呼叫 RandomSettlementTileFor |
| 7 | Storyteller/Raid | `IncidentWorker_RaidEnemy.ResolveRaidStrategy` postfix 覆寫策略（VEF.cs:38731）；`Storyteller.TryFire` prefix 吞 null-def incident（VEF.cs:21248） | 派系敵對：手排襲擊策略被換；手排 incident 靜默消失 | 手排襲擊直接填好 `parms.raidStrategy` 不依賴 resolve；FiringIncident 的 def 必填 |
| 8 | MovingBase（VEF.Planet） | `FactionGenerator.NewGeneratedFaction` postfix ×2（VEF.cs:5124/:31652，後者無 null 防護）、`Caravan_PathFollower` 三連（VEF.cs:5069-5122，存檔多欄位＋每 tick dict 查找） | 派系生成必經；商隊存檔格式 | 動態生派系時注意 postfix 鏈；解析 caravan 存檔別假設欄位集 |
| 9 | Quest 派系過濾 | `SiteMakerHelper.FactionCanOwn` 等四個 postfix（VEF.cs:38560-38625） | 派系：用原版 helper 選派系時池子被 `excludeFromQuests` 縮小 | 選派系 fallback 要處理「池子為空」 |
| 10 | Site/Settlement 掛件 | `Site.ShouldRemoveMapNow`（VEF.cs:20517）、`Settlement.GetFloatMenuOptions`（VEF.cs:46342）、`MapDeiniter.Deinit`（VEF.cs:46371）、`SettlementDefeatUtility.IsDefeated`（VEF.cs:20938） | WorldObject 生命週期：繼承 Site 時移除可被否決；其餘 no-op 加料 | 繼承 Site 做據點時測 quest 共存；其他可無視 |
| 11 | 載入期合併 | `*.ResolveReferences` prefix IMergeable（VEF.cs:765）、BackCompatibility（VEF.cs:542） | def 載入：基本無感 | 無 |
| 12 | MVCF / PipeSystem | verb 戰鬥面（opt-in）／建築管網＋`Thing.SpawnSetup` transpiler | 與你領域無交集 | 只在你也 transpile `Thing.SpawnSetup` 時測共存 |
