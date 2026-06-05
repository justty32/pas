# Session Log — rimworld-mod-guide

- 2026-06-05 建立 derived/rimworld-mod-guide，定位：給資深 C# 工程師的 RimWorld mod HTML 入門指南。
- 2026-06-05 手寫 `_shared.css`（暗色主題）與 `index.html`（總覽頁）。
- 2026-06-05 並行 subagent 產出 01~07 七個內容頁（環境/XMLDef/Harmony/模式/除錯/UI/進階）。
- 2026-06-05 統一 index、01、02、03 的 nav 為全站 8 連結。
- 2026-06-05 補上 PROJECT.md。全 8 頁 + CSS 完成，可直接開 html/index.html 瀏覽。
- 2026-06-05 新增 09-sound-audio.html（音效系統）；採用 12 連結 nav（含 08/09/10/11）。
- 2026-06-05 新增 08-graphics-textures.html（貼圖圖形系統，9 大節 + 完整 C#/XML 範例）；12 連結 nav，active=08。
- 2026-06-05 依規格重寫 07-advanced.html（Transpiler/性能/Scribe/引用陷阱/多版本/跨Mod/資料速查 7 節 + 延伸資源），8 連結 nav，active=07。
- 2026-06-05 新增 11-pawn-generation.html（Pawn 生成與屬性，10 大節：PawnKindDef/Request/Pawn 結構/RaceProperties/完整生成範例/Backstory/Trait+Skill/Hediff/ThingSetMaker/常見坑），12 連結 nav，active=11。
- 2026-06-05 新增 13-world-map.html（世界地圖與派系，10 大節：World/WorldGrid/Tile、WorldObject(Def)、繼承自訂、FactionDef、派系關係、C#建faction+goodwill、Caravan/WorldPath、BiomeDef、SettlementDef/SitePartDef、常見坑），17 連結 nav，active=13。
- 2026-06-05 新增 17-apparel-equipment.html（服裝與裝備，§0~§10：概念地圖/Apparel ThingDef/ApparelLayerDef圖層衝突/穿著圖形+PawnRenderer/StatBases防護/Equipment武器/C#穿戴/ApparelProperties/自訂Comp/常見坑/最小清單）；暫用簡易 2 連結 nav（待全站統一覆蓋）。

- 2026-06-05 新增 14-research-production.html（研究與生產鏈，§1~§10：ResearchProjectDef、ResearchTabDef佈局、C#查詢解鎖(FinishProject/IsFinished)、RecipeDef、IngredientCount+ThingFilter、工作台ThingDef(WorkGiver_DoBill/billGiver)、Bill系統(BillStack/RecipeWorkerCounter)、自訂RecipeWorker(Notify_IterationCompleted)、StatDef+StatPart效率、常見坑），17 連結 nav，active=14。

## 進度快照（接上用）
- 當前理解：8 頁 HTML 指南已全部完成且 nav 一致，內容齊全。
- 剩餘待辦：(選用) 統一 02 頁 logo 文字；(選用) 校對各頁程式碼範例正確性；(選用) 加 Preview/截圖。
- 2026-06-05 新增 12-incidents-storyteller.html（事件與敘事者，§0~§10：資料流/IncidentDef/IncidentWorker(CanFireNowSub+TryExecuteWorker)/IncidentParms/三型別完整範例(襲擊+訪客+天氣)/Storyteller架構/三大Comp(OnOffCycle+RandomMain+FactionInteraction)/威脅點數/LetterDef/GameCondition/除錯坑），17 連結 nav，active=12。
- 2026-06-05 新增 20-needs-mood-thoughts.html（需求心情想法，總覽資料流+10 大節：NeedDef/自訂Need(NeedInterval+CurLevel)、啟用need(ShouldHaveNeed)、ThoughtDef(stages/durationDays/stackLimit)、Memory vs Situational、TryGainMemory、MoodOffset+崩潰閾值、MentalStateDef/MentalBreakDef、ThoughtWorker、trait的nullify/thoughtOffset、常見坑），暫用簡易 2 連結 nav（待全站統一覆蓋）。
- 2026-06-05 新增 15-combat-damage.html（戰鬥與傷害系統，§1~§10：DamageDef(workerClass/armorCategory/harmAllLayersUntilOutside/deathMessage)、DamageWorker階層+DamageInfo struct、C#主動造傷(TakeDamage/DamageResult)、Verb系統(VerbProperties/Verb_Shoot/MeleeAttack/LaunchProjectile)、自訂Verb覆寫TryCastShot、ProjectileDef+Projectile.Impact、護甲三檔機率模型+ArmorUtility.GetPostArmorDamage(穿透=扣評分,Sharp降級Blunt)、BodyPartDef/BodyDef coverage命中部位、Tool+ToolCapacityDef近戰、常見坑)，17 連結 nav，active=15。
- 2026-06-05 新增 26-storage-filters.html（儲存、分類與篩選，§1~§11：心智模型(分類樹→ThingFilter→StorageSettings)、ThingCategoryDef階層(parent/childThingDefs回填)、ThingDef.thingCategories歸類、ThingFilter維度+API+XML(categories/disallowed/special/parentFilter)、StorageSettings+IStoreSettingsParent+SlotGroup+StoragePriority、繼承Building_Storage(fixedStorageSettings上界/defaultStorageSettings/Accepts override/Notify_ReceivedThing)、堆疊stackLimit+TryAbsorbStack/SplitOff/CanStackWith(澄清CompStackable非原版)、ThingRequest+ListerThings查詢(ForDef/ForGroup/勿cache活清單)、ThingDefCountClass成本產出、SpecialThingFilterDef+Worker(Matches vs CanEverMatch)、常見坑)，暫用簡易 2 連結 nav（待全站統一覆蓋）。
- 2026-06-05 新增 25-map-generation.html（地圖生成，§1~§10：MapGeneratorDef/GenStepDef/GenStep流水線+GenerateMap骨架、內建GenStep(ElevationFertility/Terrain/Caves/RockChunks/ScatterThings)、自訂GenStep(覆寫Generate+SeedPart+floodFiller礦脈範例+GenStepDef XML+PatchOperationAdd注入)、TerrainDef(fertility/pathCost/affordances/SetTerrain)、放置(GenSpawn/CellFinder/繼承GenStep_Scatterer+ScatterThingsUtility)、噪聲原理(Elevation/Fertility/Caves三grid+礦脈lump)、ModuleBase/Perlin(Verse.Noise+ScaleBias+MapGenFloatGrid+NoiseDebugUI)、order全域排序鍵+插隊決策、結構生成(BaseGen/SymbolResolver+KCSG StructureLayoutDef)、常見坑(order錯置/未覆蓋全圖/效能/WipeMode/SeedPart重複/public欄位))，暫用簡易 2 連結 nav（待全站統一覆蓋）。
