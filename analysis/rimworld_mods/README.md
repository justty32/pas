# RimWorld Mods 分析群組

對既有 RimWorld 1.6 Workshop mod 做 Analysis，目標導向皆為「在此基礎上 create（擴充/衍生）」。每個 mod 一個子目錄，反編譯/原始碼放在 `projects/rimworld_mods/<mod>/`。

> 共同方法：`ilspycmd <dll> -o <out>` 反編譯（或讀自帶原始碼）→ 追框架相依 DLL → 釐清「純 XML 可做 vs 必須 C#」的二分 → 以 tutorial/extension_points 當核心交付。

## 已分析 mod

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Vanilla Outposts Expanded** | `vanillaexpanded.outposts` / 2688941031 | 世界地圖自治營地：定時產資源/提供服務。引擎在 VEF 的 `Outposts.dll` | **產資源型＝純 XML**（繼承 `OutpostBase`＋`OutpostExtension.ResultOptions`）；互動服務型才需 C# | `vanilla-outposts-expanded/tutorial/01_add_outpost_xml.md` |
| **Custom Quest Framework** | `HaiLuan.CustomQuestFramework` / 2978572782 | 遊戲內視覺化任務/地圖/物件編輯器＋領域腳本（`QuestScriptDef`＋`CQFAction`） | **純 XML 覆蓋 90%+**：`QuestNode_DoCQFActions` 裝既有 100+ 個 `CQFAction`；新副作用才繼承 `CQFAction_Target` 寫 C# | `custom-quest-framework/tutorial/01_add_custom_quest.md` |
| **SpeakUp 畅所欲言** | `cn.speakup.ttyet` / 3445623063（依賴 Interaction Bubbles `Jaxe.Bubbles` / 1516158345） | 純本地 `GrammarResolver` 語法規則驅動的動態對話，**不接 LLM/網路**；與 Bubbles 經原版 `PlayLog` 解耦 | **A 純資料**（`1.6/Patches/` 加 `PatchOperation` 注入對話）／**B 改碼**（`ExtraGrammarUtility.cs::ExtraRules` 加情境變數） | `speakup/details/extension_points.md` |
| **Interaction Bubbles** | `Jaxe.Bubbles` / 1516158345（作者 © Jaxe；SpeakUp 的顯示層依賴） | 把社交互動畫成小人頭上漫畫對話泡泡的**純 UI mod**：零 Def/零 XML 資料層，全機制＝C#＋反射＋4 patch（1116 行單檔）。唯一捕獲點＝`PlayLog.Add` Postfix；文字直接用原版 `Entry.ToGameStringFromPOV` | **沒有資料層可擴充**：純 XML 只能換 9-slice 貼圖＋翻譯；行為全須 fork C#。真正價值＝三可複用範式（`PlayLog.Add` 通用互動捕獲點／小人頭上跟隨浮動 UI／反射零樣板 ModSettings） | `interaction-bubbles/details/extension_points.md` |

### 第二批：載具/傳送門三件套（依賴鏈 Vehicle Framework ← SimplePortal ← RV with PD，皆作者 Furia 除框架本體）

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Vehicle Framework** | `SmashPhil.VehicleFramework` / 3014915404 | 大型底層框架：把「載具」實作成特殊 Pawn（`VehiclePawn : Pawn`），自帶平行尋路/座位/部位健康/砲塔/升級樹。**純 DLL（已反編譯）**，唯一硬相依 Harmony，**與 VEF 無相依**（只有選用相容層）。框架本身不附具體載具，只附 `Base*` 抽象範本 | **新載具＝純 XML**：繼承 `Base*` 範本配 `VehicleDef`/`VehicleBuildDef`＋pattern/graphics＋內建 comp（Fueled/Turrets/Launcher/UpgradeTree）；全新行為（自訂砲塔/comp/尋路）才走 Harmony C# | `vehicle-framework/tutorial/01_add_vehicle_xml.md` |
| **SimplePortal** | `flammpfeil.SimplePortal` / 3325512144 | 繼承原版 `MapPortal`（PitGate 基底），用一對雙向 `linkedPortal` 引用打通**兩張既有真實地圖**的傳送門（pit-gate 風 UI）。**不自建地圖、不主動開 PocketMap**；傳送本體＝`DeSpawn`+`GenSpawn.Spawn` 到對端地圖 | **變體＝純 XML**（`ParentName="SimplePortal_PortalBase"` 調 `CompProperties_SimplePortal` 8 欄）；改傳送行為（目的地/條件/單向）必須 C# | `simple-portal/details/extension_points.md` |
| **RV with built-in PD** | `flammpfeil.rv` / 3342334887（硬相依 VehicleFramework＋SimplePortal） | 一台 VehicleFramework 載具，把**原生 PocketMap 當車內異次元空間**，用 **SimplePortal 傳送門**對接「車輛端↔車內地圖端」。C# 只做三件事：生成掛載車內 PocketMap、互設兩端 `linkedPortal`、寫相容補丁 | **衍生載具＝純 XML**（複製 `VehicleDef`+`VehicleBuildDef`，保留 `CompProperties_RVwitPD` 的 `mapWidth/mapHeight`，SimplePortal comp 自動注入）；改車內生成內容/進出規則才碰碼 | `rv-with-pd/architecture/01_vehicle_pocketmap_glue.md` |

### 第三批：世界地圖大戰略 / 帝國經營 / 基地生成

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Rim War** | `Torann.RimWar` / 2222935097 | 世界地圖派系大戰略模擬層：每派系一份戰力表，AI 派系自主生成可見行軍隊伍、彼此交戰、佔領聚落，接管原版襲擊/商隊/事件。**純 DLL（已反編譯）**；v1.6 已脫離 HugsLib。唯一驅動＝`WorldComponent_PowerTracker.WorldComponentTick` | **純 XML**：改 `Defs/RimWarDefs/RimWarDef.xml`（派系 behavior＋3 係數）＋仿 `Patches/` 用 `PatchOperationAdd` 注入 `WorldObjectCompProperties_RimWarSettlement` 到自訂聚落 | `rim-war/architecture/01_world_simulation.md` |
| **Vanilla Base Generation Expanded** | `VanillaExpanded.BaseGeneration` / 3209927822（硬相依 VFE Core/KCSG） | VFE 系列**純資料 mod（零 .cs/.dll）**：提供 ~317 StructureLayoutDef / 21 SettlementLayoutDef 給 VFE Core 內建 KCSG 引擎，讓派系聚落程序化拼出有規劃感村落。三層＝`SymbolDef`→`StructureLayoutDef`（2D grid）→`SettlementLayoutDef`（tag+count 抽取），靠 **tag 字串**鬆耦合 | **整套派系聚落外觀＝純資料**：畫 StructureLayoutDef＋寫 SettlementLayoutDef＋`PatchOperationAddModExtension` 注入 `KCSG.CustomGenOption` 到 FactionDef；新生成原語才需動 KCSG 引擎（屬 VFE Core） | `vanilla-base-generation-expanded/tutorial/01_add_settlement_layout.md` |
| **Empire Refactored** | `Matathias.Empire` / 3701480464 | 世界地圖帝國經營：單一殖民地擴張成多個自治附庸聚落（每個＝正規 WorldObject `WorldSettlementFC`），自動產資源/繳稅/升級/頒敕令/派軍。**自帶 295 .cs 源碼**。真相＝`FactionFC : WorldComponent`。重構重點＝全面 def 化＋Registry/Interface 接點讓 submod 多免 Harmony | **A 純 XML**（5 種 Def：據點/資源/建築/事件/敕令）→ **B-1 免 Harmony**（DefModExtension＋實作 `FCInterfaces` 介面註冊 Registry）→ **B-2 新 compat DLL**（LoadFolders `IfModActive` 閘門，碰第三方型別才用） | `empire-refactored/details/extension_points.md` |

### 第四批：AOBA 機甲生態系（同作者 AOBA/AobaKuma，共用後端＝Fortified Features Framework）

> 反直覺：表面相依鏈是 MobileDragoon→Exosuit→…，但**真正的共用程式碼後端是 Fortified Features Framework（`Fortified.*` 命名空間）**。Exosuit Framework、DMS Core、MobileDragoon 都引用 `Fortified.*`；它們是平行兄弟，FFF 才是父。家族內有**兩種機甲範式**：FFF 的 `WeaponUsableMech`（持武器機兵，DMS 走這條）vs Exosuit 的可穿戴 Apparel 外骨骼（MobileDragoon 走這條）。

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Fortified Features Framework** | `AOBA.Framework` / 3498575851 | 作者自家機兵/動力甲/工事系列的「雜貨型」共用後端程式庫（38881 行、280+ 型別、74 patch、**去中心化無單一進入點**）：把砲塔/機兵裝備/塗裝迷彩/空中支援/聚落程序生成等十幾個機制封裝成可被 XML 引用的 Comp/DefModExtension/Def/patch。「Fortified（工事）」只是其中一個子系統 | **依子系統而定**（先判斷需求屬哪個子系統）：塗裝/聚落生成/空中支援/彈種/爆炸/可部署砲塔＝純 XML；人型機兵核心/新 Verb/載人砲塔/新潛入任務＝C# | `fortified-features-framework/architecture/00_overview.md` |
| **Exosuit Framework** | `Aoba.Exosuit.Framework` / 3352894993（硬相依 VFE Core；用 FFF 後端） | 把「可駕駛動力外骨骼/小型機甲」實作成**駕駛員穿戴的一整套 Apparel**（核心 `Exosuit_Core : Apparel` 當結構血量/承傷層，各部位模組占 `SlotDef` 格；登機/整備經 `Building_MaintenanceBay`＋隱形 Dummy pawn）。**純框架不含具體機甲** | **新機甲＋常規模組＝純 XML**：金律「一模組＝兩 ThingDef（item⇄apparel 雙生）」，兩邊掛 `CompProperties_ExosuitModule` 互指、`occupiedSlots` 必填、`uiPriority` 不可撞號；只有全新模組「行為」才需 C# | `exosuit-framework/tutorial/01_add_exosuit_xml.md` |
| **Dead Man's Switch (Core)** | `Aoba.DeadManSwitch.Core` / 3121742525（硬相依 Harmony/Biotech/VFE Core；用 FFF 後端） | 「半自動戰爭機兵（Automatroid）軍事勢力」主題的**大型純資料內容包**（357 ThingDef/79 Recipe/68 PawnKind…，對上 DLL 僅 17 類別/1409 行）。機兵行為積木全來自 `Fortified.*`（`WeaponUsableMech`/`HumanlikeMech`），DLL 只做三組原版無 XML 接點的劇情膠水（古機師 Boss 突襲/文件任務鏈/Royalty 授勳） | **新機兵/裝備/武器/勢力/物品/研究＝全純 XML**（複製既有 Def 改數值/Comp）；想要的行為 FFF 與原版都沒有時才寫 C#（且寫進 FFF 非 DMS） | `dead-mans-switch/architecture/00_overview.md` |
| **DMS - MobileDragoon** | `Aoba.DeadManSwitch.MobileDragoon` / 3377130226（硬相依 Exosuit Framework＋DMS Core，**零 DLL**） | 純 XML 內容包：在 Exosuit+DMS 上定義一台「移動龍騎兵」超重型機甲（5 機體框架＋數十換裝模塊＋武器＋研究樹＋三派系兵種）。**證明「在 Exosuit 上做新機甲＝純 XML」** | **複製即新機甲**：照 item⇄apparel 雙生 def＋`ModuleItemBase/ModuleApparelBase/…` ParentName＋`occupiedSlots` 一致；改換裝槽判定/新 UI 才回 C#（且改 framework 非本 mod） | `mobile-dragoon/tutorial/01_clone_a_new_mecha_xml.md` |

### 第五批：世界地圖內容（彼此獨立）

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **RimCities** | `Cabbage.RimCities` / 1775170117 | 世界地圖程序化生成大型可探索/可攻打「城市」聚落（`Cities.City : Settlement`），進入時用自訂 GenStep 管線即時生成街道網/圍牆/建築/居民；附自製舊式任務系統；23 個 Harmony patch 把城市融進原版 Settlement。**資料驅動的程序生成**（演算法寫死 C#、`MapGeneration.xml` 餵參數） | **純 XML（零編譯）**：調生成數量/密度/面積、換傢俱/砲塔/作物清單、用既有裝飾器組新「建築類型」、做同 class 不同風貌的城市殼；**新房間規則/新 GenStep/新任務/讓新城市 defName 自動進世界**（`WorldGenStep_Cities` 城市清單寫死）才需 C# | `rimcities/architecture/01_city_map_generation.md` |
| **Caravan Adventures** | `iforgotmysocks.CaravanAdventures` / 2558957509 | 重 C# 商隊玩法 mod：免 DLC 的商隊 QoL/露營/賞金基底，疊加一條需 Royalty、約 25% 內容的**線性主線劇情**，由單一 `WorldComponent`（`StoryWC`）以「劇情旗標狀態機」推進。**劇情硬編在 C#，刻意繞過原生 QuestScript DSL**（5 個 QuestScriptDef 全是 `QuestNode_Temp` 空殼） | **純 XML 僅限 reskin/數值/翻譯/CE 相容**＋仿 `Expansions/RM` 寫 reskin `ExpansionDef`（作者唯一支援的 XML 擴充點）；**新劇情章節/觸發/順序/對話分支全須 fork DLL** | `caravan-adventures/architecture/00_overview.md` |

### 第六批：Ariandel 特殊角色框架（同作者 Ariandel，框架↔範例配對，同 Exosuit↔MobileDragoon 模式）

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Ariandel Library** | `Ariandel.AriandelLibrary` / 3665997350 | 「特殊角色框架（SCMF）」函式庫：用自訂 Def＋30+ DefModExtension/Comp＋30 patch，把一個 PawnKindDef 升格成「具名、唯一身分、不會真死可召回、有專屬面板、可劇情招募」的 Boss/神選者。**核心庫＋6 個 gated 相容子模組**（Royalty/Anomaly/FA/rjw/Milira 各一 DLL＋Ideology 僅 Def，經 LoadFolders `IfModActive` 疊加，同 Empire Refactored 風格）。隨附 18 章 `User_Manual` | **特殊角色生命週期可 100% 純 XML**（三注入點：`modExtensions` 掛 Extension／`comps` 掛 CompProperties／`workerClass` 替換）；只有全新能力命中效果/全新對話 worker/改框架本身才需 C# | `ariandel-library/tutorial/01_*.md` |
| **SCMF Sample** | `Ariandel.UserGuideSCMF` / 3668177055（硬相依 Ariandel Library，**零 DLL**） | 官方親手寫的**純 XML 教學範例**：把既有種族一隻普通 PawnKind 包裝成被「特殊角色管理器（SCM）」接管的具名/不死/可召回固定角色，全程零 C#，每個 XML 帶逐行雙語教學註解 | **必填三件套**（掛 PawnKindDef.modExtensions）：`FixedIdentityExtension`＋`NPCKindTag`＋`SpecialPawnExtension`（uniqueID 登錄 SCM）；選用行為改寫＝各 `AL_*_Extension`；入手途徑＝`ShroudOutcomeDef`。造新積木（新技能/worker/分頁）才需 C# | `scmf-sample/tutorial/01_make_special_character_xml.md` |

### 第七批：Warband Warfare（使用者特別喜歡，三 DLL 單一 mod，作者 Thumb）

> 「Add player-controlled troops to RimWorld」——世界地圖上玩家**雇用/組建/指揮自己的傭兵團（warband）**。分三 DLL 單向疊加：核心 ← Leadership ← Questline。

| Mod / 子模組 | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Warband Warfare**（核心 `WarfareAndWarbands.dll`） | `Thumb.Warbands` / 3371827271（相依 Harmony；loadAfter CE；incompatible bs.xenotypespawncontrol） | warband＝世界地圖 `Site` 子類 `Warband`，平時只存「兵種 defName→人數」計數表（**不存實體 Pawn、只有領袖一個真 Pawn**），下令攻擊時才 `PawnGenerator` 實體化。**戰鬥進真實地圖實戰、非抽象 points 結算**（攻擊＝實體化成 Caravan 進場玩家操控；反突襲＝排 `IncidentDefOf.RaidEnemy`，points 只定敵方規模不判勝負）。MainButton 開管理 UI | **純 XML**：`FactionDef`/`SitePartDef`/`FactionTraitDef`/`PolicyCategoryDef`、`PolicyDef` 數值欄位、兵種池（任何 mod 的 `isFighter` 人形兵種**自動**進編組清單免改本 mod）；**C#**：Warband 全行為、5 種升級（`PlayerWarbandUpgrade` 硬編子類無 Def）、PolicyDef 特殊效果 workerClass、JobDriver、所有 patch | `warband-warfare/architecture/00_overview.md` |
| ＋ **WAWLeadership**（領導力擴充 DLL） | 同 mod 內 | 給傭兵團的**指揮官 RPG**：`CompLeadership` 掛 pawn，戰鬥累積經驗升級，六屬性（Commanding/Medic/Recruiting/Engineering/Economy/Diplomacy）轉成 warband 技能加成/戰利品倍率/招募折扣/世界地圖主動技能。**純 C# 硬編、零 Def** | 全擴充須改 C#（無可擴充 Def） | `warband-warfare/architecture/02_questline_and_leadership.md` |
| ＋ **WarbandWarfareQuestline**（任務線擴充 DLL） | 同 mod 內 | 「諸侯聯盟（League）4X 元層」：救援村莊任務招小派系加入聯盟，再經政策樹/稅收/道路/軍演/國會投票經營。**任務硬編 C#**（唯一 QuestScriptDef `WAW_SaveVillage` 是空殼、`new Quest`+`AddPart` 手組），但**政策樹 PolicyDef、派系特質 FactionTraitDef 是真資料驅動** | **純 XML**：加數值型 PolicyDef（taxBonus/cost/equipmentBudgetLimitOffset 無 workerClass）／FactionTraitDef；**C#**：政策副作用 PolicyWorker 子類、新任務 | 同上 |

### 第八批：世界/地圖玩法（彼此獨立；Map Mode Framework 為 territory 依賴項，未特別分析）

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Faction Territories and Vassalage** | `jaeger972.factionterritories` / 3626725895（硬相依 Map Mode Framework） | 世界地圖畫確定性派系領土（移動難度加權成長，非固定半徑）＋整套附庸/藩屬外交（附庸化/割讓/藩屬前哨/入侵/建城建路）。繪圖外包 Map Mode Framework。**重 C#** 單 DLL 16317 行 | **純 XML 僅 `CaravanIncidentEntryDef`**（把任一 IncidentDef 對應關係/科技旗標＋權重，做領土感知商隊事件）＋ Map Mode Framework 的 `MapModeDef`；領土演算法/附庸/入侵全 C# | `faction-territories/details/extension_points.md` |
| **MultiFloors** | `telardo.MultiFloors` / 3384660931（依賴 **Prepatcher**） | 為地圖加垂直樓層（Z-level）：每層＝PocketMap，樓梯/電梯＝`Stair : MapPortal`/`Elevator` 上下移動，跨層傳輸物品/電力/配方。核心 22880 行＋9 個 gated ModCompat DLL | **純 XML**：`UpperLevelSettingsDef`（PlanetLayerDef→地形+MapGenerator，MayRequire gate 新星球層 mod）、新外觀樓梯電梯（沿用 thingClass+`StairsModExtension`）；跨第三方 mod 相容＝照抄 ModCompat gated DLL 模式；樓層生成/傳輸/新通行機制 C# | `multifloors/architecture/00_overview.md` |
| **World Tech Level** | `m00nl1ght.WorldTechLevel` / 3414187030（透過 **LunarFramework**） | 開局選科技等級上限→過濾所有超標內容＋低科技替代。本質是「為被資料擴充而生」的過濾框架，~40 patch 攔各生成環節 | **純 XML 擴充性最高**：對外介面就是 `TechLevelConfigDef`（defType+entries[defName/techLevel/priority/ifModPresent…]+alternatives 替代物+storyFilters 關鍵字）。給任意內容 mod 補科技等級＝零 C# 相容補丁；改過濾演算法才需 C#（且須懂 LunarFramework） | `world-tech-level/details/extension_points.md` |
| **Walk the World** | `addvans.WalkTheWorld` / 3546716725 | 把徵召殖民者走到地圖邊緣即徒步進相鄰世界格地圖（無商隊），離開後地圖重置。純 C# 機制 mod，1731 行 | **無資料層、對外無純 XML 擴充面**；行為靠 ModSettings 三 enum 調；衍生須改 C#。注意 `ExitMapGrid` 相關 patch 與其他跨地圖 mod 的衝突 | `walk-the-world/architecture/00_overview.md` |
| **Deep And Deeper** | `Shashlichnik.DeepAndDeeper` / 3509420021 | DRG 風地下採礦遠征：洞窟入口 Site→逐層下探洞窟口袋地圖（CaveMapGenerator Lvl1-4）挖寶應付危險。PocketMap/MapPortal 家族（`CaveEntrance : MapPortal`/`CaveExit : PocketMapExit`） | **純 XML**：新增/重排/調校洞窟層（`MapGeneratorDef` 串 `GenStepDef`，餵 `GenStep_CaveInterest_*` 參數 mineableModifier/reward/countChances/mutant，MayRequire gate DLC）、Site/PawnKind/Items/Buildings/`CaveStabilizer` ext；新興趣點類型/進出崩塌挖掘機制 C# | `deep-and-deeper/details/extension_points.md` |
| **Ancient Urban Ruins** | `XMB.AncientUrbanrUins.MO` / 3316062206 | 都市探索內容＋工具：預製都市廢墟地圖＋大量美術＋「平面圖匯入→生成任務地圖」系統。6 DLL。**核心庫建在 CQF 資料模型上**（含 `CustomMapDataDef`/`DialogTreeDef`/`QuestNode_GenerateCustomSite`，12 處引用 CustomQuestFramework） | **純 XML**：`QuestScriptDef` 用 `QuestNode_GenerateCustomSite` 召喚既有預製地圖＋`DialogTreeDef` 對話＋隱藏派系/商人/研究；新預製地圖＝`CustomMapDataDef`（Def 但靠遊戲內平面圖工具產生）；生成引擎/AI/渲染 C# | `ancient-urban-ruins/details/extension_points.md` |

### 第十一批：經營模擬框架

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **RimSim Management Framework**（边缘模拟经营框架） | `chezhou.Framework.RimSimManagementFramework` / 3736621496（追踪虫 + Migua） | 商店/經營模擬框架：蓋店（收銀台/貨架/販賣機/招牌/廁所/收藏櫃），中立派系顧客自動上門逛街→挑貨→結帳→用服務→堂食，殖民者當店員補貨/顧收銀/備單。單 DLL 64541 行。**Defs 明確分 `Required/`（骨架勿動）與 `Reusable/`（資料驅動擴充，作者註解「複製改 defName」）** | **純 XML（作者明示）**：`GoodsDef`(商品=ThingDef 清單)、`ShopServiceDef`(付費服務，沿用預設 worker 即純 XML)、`CustomerKindDef`、`CollectibleExchangeListDef`、`PurchaseOutcomeDef`、`ShopTuningDef`、新設施(掛既有 ThingComp)；新顧客行為(CustomerActionDef+JobDriver)/服務效果(workerClass)/設施機制需 C# | `rimsim-management/details/extension_points.md` |

### 第十批：世界互動玩法

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Simple Warrants** | `pb3n.SimpleWarrants` / 2676828755（pb3n + Taranchuk，**自帶完整源碼＋.sln**） | 懸賞/通緝佈告欄：派系與玩家張貼懸賞（通緝 pawn 生擒/擊殺、獵殺/馴服動物、取回神器），接單賺賞金。核心＝`abstract Warrant : IExposable`（非 Def）＋三封閉子類，靠 `TargetType` enum；`WarrantsManager : GameComponent` 管理 | **純 XML**：通緝理由（`RulePackDef WantedReasons`）、接單後任務/地點（QuestScriptDef 走 vanilla DSL＋`SW_Camp` tag 抓 SitePartDef）、佈告欄 MainButtonDef、平衡（設定 UI）；**加全新懸賞「目標種類」＝必須 C#**（新 Warrant 子類＋TargetType＋Manager＋UI 接線） | `simple-warrants/details/extension_points.md` |

### 第九批：工具 / UX

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Loading Progress** | `ilyvion.LoadingProgress` / 3535481557（MIT/Apache 開源，GitHub `ilyvion/loading-progress`） | 開發者體驗工具：Harmony 鉤住 RimWorld 啟動載入管線（XML 合併/繼承/交叉引用解析/語言/LongEventHandler），即時顯示載入進度視窗＋逐 mod 載入耗時量測（StartupImpact）。**無 Def、單 DLL** | **無純 XML 擴充面**（純 C# 工具 mod）；create 價值＝技術參考範例（如何 instrument 啟動管線、在 LongEventHandler 畫面畫自訂 UI、量測逐 mod 耗時），衍生只能 fork C# | `loading-progress/architecture/00_overview.md` |

### 第十二批：基礎函式庫（坑點導向淺析，2026-06-12）

> 目的不是擴充而是**避雷**：盤點「裝在清單裡就有全域影響」的框架，標出會坑到自家 mod 的 patch 面。

| Mod | packageId / workshop | 本質 | 主要坑點 | 入口文件 |
|---|---|---|---|---|
| **Vanilla Expanded Framework** | `OskarPotocki.VanillaFactionsExpanded.Core` / 2023507013 | VE 系共用引擎集（VEF.dll 主體 375 個 HarmonyPatch＋KCSG/MVCF/PipeSystem/Outposts 衛星 DLL）。四種 patch 上線時序：啟動即上／def 載入後／掃 DefDatabase 按需／OptionalFeaturesDef 點名 | ①FactionDiscovery 讀檔掃派系彈補生對話框（動態生滅派系的 mod 注意）；②PawnGenerator 三 postfix 無條件跑（NRE 前科區）；③`GetOrGenerateMap` prefix 可改地圖尺寸＋`GenerateMap` postfix 灑 ObjectSpawnsDef 雜物。CaravanArrivalAction 體系未被碰 | `vanilla-expanded-framework/details/pitfalls_and_global_patches.md` |
| **HugsLib** | `UnlimitedHugs.HugsLib` / 818773962 | 老牌 mod 函式庫：ModBase 生命週期/設定框架/更新新聞/log 上傳。17 個全域 patch 常駐（不論有無 mod 依賴），但僅 3 個真改寫原版行為；不碰 Scribe/MapComponent/規則數值 | ①dev 模式改 modlist/語言會**跳過對話框直接重啟**（誤判閃退）；②UtilityWorldObject 存檔黏性（拔 HugsLib 紅字）；③更新新聞掃**所有** mod 的 `News/` 資料夾＋Ctrl+F12 全域按鍵。自家 mod 零依賴 ⇒ 幾乎無事 | `hugslib/details/pitfalls_and_global_patches.md` |

> Rim War 同日加深：`rim-war/details/target_selection_and_arrival.md`（目標選擇＝`NearbyHostileSettlements` 隨機抽樣非窮舉、抵達行為鏈、`IsValidSettlement` 4 個呼叫點影響評估、NpcOutpost 接入推薦＝XML 注入 `RimWarSettlementComp` 零 C#、Empire 附庸會被選為目標但 Vassal 永不被佔領（:11151）、戰績訊號匯流排＝`RW_LetterMaker.Archive_RWLetter`）。

## 重要備註
- **CQF 自帶權威 schema**：mod 目錄內 `<MOD>/.QuestEditor_Library/` 有作者原始碼樹＋4 份 `Skill/*/SKILL.md`（`cqf-overview`/`cqf-def-catalog`/`cqf-action-condition-dev`/`cqf-map-dev`），做 create 時優先參考。
- **SpeakUp 不是 AI 對話**：目前完全是模板規則；若想「接 LLM 讓對話更聰明」是全新對話來源接點（B 類改碼），非改 XML 模板。
- **Interaction Bubbles 是顯示層、`PlayLog.Add` 是通用互動捕獲點**：Bubbles 零 Def/零 XML，無資料層可擴充（純 XML 只能換貼圖+翻譯）。但它示範的 `PlayLog.Add` Postfix 是「小人社交互動發生」最全面的鉤子——自動吃到 SpeakUp 等他 mod 寫進 PlayLog 的文字，配 `Entry.ToGameStringFromPOV(pawn)` 取在地化字串。想做「浮動文字/LLM 對話泡泡/互動觸發事件」的衍生都應接這裡＋自訂文字來源，**不要改 Bubbles 本身**。SpeakUp↔Bubbles 經原版 PlayLog/LogEntry 解耦＝「內容生成」與「顯示」分離的範本。
- **VOE outpost 現行不會被襲擊**：`raidPoints`/`raidFaction` 是死欄位，About 描述過時；唯一的「襲擊設計」是反向（`Outpost_Defensive` 削減打主基地的 raid）。詳見 `vanilla-outposts-expanded/details/raid_and_attack_design.md`。
- **Vehicle Framework 不附具體載具**：框架只給 `Base*` 抽象 Def，卡車/船/直升機由內容 mod（如 Vanilla Vehicles Expanded）提供；那些抽象 Def 即「如何定義載具」的權威範本。
- **RV 的 SimplePortal comp 是被注入的**：`CompSimplePortal` 由 SimplePortal 自己 patch 進 `BaseVehiclePawn`（`Patch_Vehicles.xml`），不是 RV 加的——做衍生載具不必手動加。RV 的 `VehicleFrameworkFix.dll` 修的是 `Map.Index` 複用導致 `VehiclePathingSystem` 快取錯亂。
- **Empire compat 兩風格**：① Harmony patch（VF/RW）；② 核心定義 bridge 介面、gated DLL 提供強型別實作（CE 的 `ICombatExtendedBridge`、HAR 的 `IHARBridge`）。RW 還示範直接走核心 `IBattleModifier` registry 免 patch。
- **VBGE / VOE 同屬 VFE 生態**：引擎都在 VFE Core 及其週邊 DLL；VBGE 是純資料層。**KCSG 引擎已於 2026-06-12 反編譯坐實**（接管＝Harmony Postfix 偷換 `MapGeneratorDef` getter；自訂 WorldObjectDef 掛 `CustomGenOption` 即可吃 KCSG、不必繼承 Settlement）：見 `vanilla-base-generation-expanded/details/kcsg_engine_takeover.md`。
- **Empire 與 Rim War / Vehicle Framework 有 compat 子模組**：本批三者剛好互有接點（Empire 的 `Patch-RW`/`Patch-VF`），跨 mod create 時可交叉參照。
- **AOBA 家族真正的後端是 FFF 不是 Exosuit**：表面相依鏈會誤導；判定「機甲行為從哪來」要看 XML 裡的 `Class="Fortified.*"`（FFF）與 `Exosuit.*`（外骨骼框架）。兩種機甲範式：FFF `WeaponUsableMech`（DMS 持武器機兵）vs Exosuit 可穿戴 Apparel（MobileDragoon）。FFF **去中心化、無單一主 Def 型別**，擴充前要先判斷需求屬哪個子系統。
- **「框架↔零 DLL 範例」配對是本群組最佳純 XML 教材**：MobileDragoon（站 Exosuit 上）與 SCMF Sample（站 Ariandel Library 上）都是作者親手寫、零 .dll 的純 XML 內容/教學，逆推「在框架上做新內容要填哪些欄位」最快。
- **gated 相容子模組是常見大型 mod 模式**：Empire Refactored、Ariandel Library 都用 `LoadFolders.xml` 的 `IfModActive` 把 `Mods/<dlc-or-mod>/`（含其專屬 DLL）條件式疊加，DLC/前置不存在則整夾不載入、無硬相依不報錯；做相容子模組可照抄。
- **「劇情硬編 vs 資料驅動」兩極**：CQF＝純資料任務 DSL（QuestScriptDef＋CQFAction，純 XML 90%+）；Caravan Adventures＝完全相反，劇情寫死在 `StoryWC` 旗標狀態機、5 個 QuestScriptDef 全是空殼 `QuestNode_Temp`，新章節必須 fork DLL。想做資料驅動劇情優先選 CQF 路線。
- **RimCities 城市清單寫死**：`WorldGenStep_Cities.GenerateFresh` 的城市 defName 是四個字串常量，純 XML 可改城市內部生成風貌、但「讓全新城市類型自動出現在世界」需 C#；世界城市數量/尺寸是 mod 設定（`Config_Cities`）非 def。
- **PocketMap/MapPortal 是反覆出現的「第二地圖空間」機制**：RV-with-PD（車內空間）、SimplePortal（打通兩圖）、MultiFloors（樓層）、Deep And Deeper（洞窟層）都用原版 PocketMap＋MapPortal 做另一個地圖。做這類衍生或跨 mod 相容時，進出地圖的 patch 慣例可互相參照。
- **Ancient Urban Ruins 與 CQF 同源**：其核心庫 `AncientMarket_Libraray` 引用 CustomQuestFramework、共用 `CustomMapDataDef`/`DialogTreeDef`/`QuestNode_GenerateCustomSite`。做都市場景任務的衍生時，它是 CQF 之外最佳的 CustomMapDataDef 實戰範例庫；與衍生專案 `cqf-caravan-redemption` 四章故事（Ch1 CustomMapDataDef→Ch2 DialogTreeDef）直接相關。
- **World Tech Level 是純資料相容補丁的範本**：唯一對外介面 `TechLevelConfigDef` 讓「給任意內容 mod 標科技等級＋替代物」零 C#；想給自己的內容 mod 加 WTL 支援照抄即可。
- **「封閉核心型別＋資料化任務外圍」是常見模式**：Simple Warrants（懸賞型別封閉 C#、但接單後任務走純 XML QuestScriptDef＋tag 抓 SitePart）與 Warband Warfare（warband 行為封閉、政策/特質資料驅動）同型——核心物件加新種類要 C#，但風味/任務/地點層用 vanilla QuestScript DSL 開放。`Source/SimpleSettings.cs` 是 Taranchuk 系 mod 通用的反射式設定框架，可單獨參考。
- **Map Mode Framework 未特別分析**：`NozoMe.MapModeFramework`（3296654393）是 Faction Territories 的繪圖依賴，使用者指示只列出備用、不單獨分析；其角色是世界地圖模式繪製引擎（本 mod 繼承 `MapMode_Region`＋用 `MapModeDef` 接入）。

## 衍生（create）產物
> **已遷移至獨立 repo [`~/repo/my_rimworld_mods`](https://github.com/justty32/my_rimworld_mods)**（2026-06 遷移；本 repo 的 `derived/rimworld_mods/` 已清除）。每個 mod 自帶 `PROJECT.md`／`session_log.md`／`docs/`，完整逐 mod 表與狀態見該 repo `README.md`。部署：`~/rimworld_mods/` staging → symlink 進遊戲 `Mods/`。

| 衍生項目 | 基於（本群組分析） | 狀態（2026-06-12） |
|---|---|---|
| `cqf-caravan-redemption` | CQF | ✅ 端到端驗證通過（debug generate→接受→獎勵投放，log 零紅字） |
| `speakup-context-expansion` | SpeakUp（＋Bubbles 顯示層） | ✅ 端到端完成（pain `>`＋food `<` 數值門檻台詞實機驗證） |
| `sims-mode-community` | RimCities LordJob 範式（idea 10） | ✅ 多輪 E2E：影子 MapParent 反攻陷架構＋重組 gizmo 轉發驗證通過 |
| `npc-outposts` | VOE／world_map_grand_strategy idea 4/5 | ✅ E2E 驗證；存檔字典/執行緒問題治本 |
| `faction-politics` | Rim War bridge／idea 7/8 | ✅ Task 10 E2E 全清單通過（分裂/倒戈/上限/存讀檔/Rim War 雙向/Empire 排除） |
| `colony-archival-outpost` | VOE（idea 6 殖民地封存） | v1＋N1/N2/N3/N6/N7 已實作；後續見其 `docs/TODO.md`／`IDEAS.md` |
| `voe-outpost-enhancement` | VOE | v1 完成（哨站升級系統），實機修復 NullRef |
| `body-fortification-hediff`／`body-hp-x10` | —（實驗/工具 hediff） | 修復裝箱失效後重編；body-hp-x10 為 debug 工具 |

### 流民商隊四章故事（CQF 未來擴充設計，已定）
一條主線 QuestScriptDef 串 4 自足章節，章節間僅靠信號鏈＋共享 DB key 耦合：Ch1 探索被洗劫商隊營地（CustomMapDataDef）→ Ch2 生還商人對話委託護送（DialogTreeDef）→ Ch3 途中匪幫來襲防守（GroupDataDef，須保護商人存活）→ Ch4 送達結算聲望/白銀。待最小切片實測過再以「我建骨架＋多 agent 各做一章」並行實作。
