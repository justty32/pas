# Sofia Follower —— Papyrus 腳本架構

## 定位

`architecture/sofia-follower.md` 已從 ESP record 層解剖了 Sofia 這個成熟語音隨從（30 quest / 28 scene / 54 package / 57 GLOB），但當時註明「2 個 BSA 無工具解包，本分析聚焦 ESP record 層」。本篇補上缺的那一層：把 `SofiaFollower.bsa` 裡的 `scripts/` 解出來，分析其 Papyrus 腳本架構，印證 record 層觀察的「純引擎機制、零 SKSE 資料結構依賴」是否在程式碼層也成立，並整理出「一個真實隨從到底需要哪些常駐邏輯 script」——這正是 ModForge 若要生成完整隨從必須補的 script 模板清單。

BSA 內 `scripts/` 共 **323 個 `.pex`（編譯後 bytecode，無 `.psc` 原始碼）**，無任何 mesh/texture/voice 被本分析抽出。還原程度與解包方法見文末「解包方法與還原程度」。

## 腳本清單（323 個，分四群）

來源：`SofiaFollower.bsa` → `scripts/`（解出於 `_sofia_extract/scripts/`）。檔名前綴即 CK 自動生成的 fragment 類別：

| 群 | 數量 | 命名 | 性質 |
|---|---|---|---|
| TIF（TopicInfo fragment） | 259 | `tif__<formid>.pex`，內部 `SRC: TIF__<FORMID>.psc` | 對白行的「結束/開始 fragment」，CK 編輯對話時掛的小片段 |
| 具名邏輯 script | 31 | `sofia*.pex` / `jjsofia*.pex` / `ski_*.pex` | 隨從的真正「大腦」與各子系統 |
| PF（Package fragment） | 11 | `pf_<pkgname>_<formid>.pex` | package 的 OnBegin/OnEnd/OnChange fragment |
| 每-NPC comment | 9 | `nazeem_comment1..3` / `carlotta_comment1..4` / `braith_comment1..2` | 對特定 vanilla NPC 吐槽的對白 fragment（手刻、非模板展開） |
| SF（Scene fragment） | 8 | `sf_<scenename>_<formid>.pex` | scene phase 的 fragment（醉酒/婚禮/idle/主線/comment scene） |
| QF（Quest fragment） | 5 | `qf_<questname>_<formid>.pex` | quest stage 的 fragment（quest/drunk/wedding/trackingmarker/Jarvis 彩蛋） |

數量驗證：259 + 31 + 11 + 9 + 8 + 5 = 323。

### TIF / SF / QF / PF —— fragment 群（283/323，佔 88%）

這四群佔了腳本總數近九成，但**單個都極小**。典型 TIF（`TIF__00020948.psc`）只有一個 `Fragment_0` 函式 + 二三個 property（指向某個 quest/scene）。它們不是「邏輯」，而是 CK 把對白選項 / scene phase / quest stage / package 事件上掛的「按一下執行這幾行」的接著劑——`Fragment_N` 函式體內通常就是 `SetStage()`、`Start()` 某個 scene、設一個 GLOB。

這正是 **ModForge 目前已能生成的那一類**（CLAUDE.md「已落地功能」：quest fragment / TIF fragment Papyrus、scene fragment）。Sofia 有 259 個 TIF——印證一個對白量大的隨從，光對白 fragment 就會是腳本檔數的主體，但這些是機械化、模板化的，自動生成正是它們該被生成的方式。

具名的 fragment 例外值得記一筆：
- `QF_JJSofiaWeddingCeremony`（`Fragment_4/6/8/10`，11 prop）—— 婚禮 quest 各 stage 的演出觸發，property 全是 `Alias_*`（PriestRef / SofiaRef / PlayerRef / 各 marker）+ `SofiaWeddingScene` + `TimeScale`，fragment 在對應 stage 啟動婚禮 scene 並調時間流速。對照 record 層的 wedding stage 0→200。
- `SF_JJSofiaDrunkScene` / `SF_JJSofiaMainQuestDialogueScene`（後者 record 層即那段 17-phase 線性獨白）—— scene 各 phase 的 fragment。
- `pf__02065568.pex` / `pf__0206602f.pex` 等無名 PF —— package fragment，多半空殼或一兩行 EvaluatePackage。

## 核心邏輯 script —— Sofia 的「大腦」分工

31 個具名 script 才是真正的隨從邏輯。沒有單一巨無霸狀態機；Sofia 把「大腦」**按子系統拆成數個常駐 quest-script**，呼應 record 層觀察到的「微服務式 quest 拆分」。按職責與規模分群（規模見文末，依 `.pex` byte 數）：

### A. 跟隨與在場核心

- **`SofiaFollowerScript.psc`**（掛 `JJSofiaFollowerMain`，12 prop）—— 隨從**狀態機本體**。函式 `SetFollower / FollowerWait / FollowerFollow / DismissFollower`，property 含 `pFollowerAlias`（ReferenceAlias）、`pCurrentHireling`（faction）、各式 `FollowerDismissMessage*`（Companions / Wedding / Wait 的解散訊息，男女分版）、`FollowerHuntingBow`+`FollowerIronArrow`（解散時發還的預設武器）。它走的是 **vanilla 隨從框架的 SetPlayerTeammate / AddToFaction(CurrentHirelingFaction) / RemoveFromFaction** 那套，加上 `SetObjectiveDisplayed`、`StartTimer`、`RegisterForUpdateGameTime`。這就是 record 層 objective[10]「is waiting for you」背後的程式碼。

- **`SofiaCatchUpNewScript.psc`**（掛 `JJSofiaScripts`，16 prop）—— **catch-up 跟隨**（隨從脫隊時瞬移趕上）。核心函式 `OnUpdate` + `SofiaCatchUp`：用 `GetDistance` 量 Sofia 對玩家距離，超過 `SofiaCatchUpDistance`（GLOB，MCM 可調）且 `SofiaCatchUpEnabled` 開、`HasLOS` 判定後 `MoveTo` 把 Sofia 拉到玩家身邊再 `EvaluatePackage`。節拍用 `RegisterForSingleUpdate`（poll 迴圈）。同檔還管馬（`SofiaRideHorse`：`SofiaHorseEnabled` 時夾帶 `JJSofiaMountHorseScene` / `JJSofiaDismountHorseScene`、`SofiaHorseSummoned`、`COCMarker`），並用 `SetAlpha`（隱形瞬移避免玩家看到 pop-in）。這是「真隨從必備、但 ModForge 完全沒有」的典型常駐邏輯。

- **`SofiaLeadTheWayScript.psc`**（7 函式：`OnPackageStart/End/Change` + `OnUpdate`）—— 帶路到目的地，靠監聽 package 生命週期事件推進。對應 record 層 `JJSofiaLeadTheWay` quest。

### B. comment 排程器（Sofia 之所以「會吐槽」的引擎）

- **`SofiaCommentScript.psc`**（掛 `JJSofiaDialogue`，15 prop）—— **comment frequency 排程器**，Sofia「個性」的核心。函式 `OnUpdate / SofiaMakeComment / GetPlayerDialogueTarget / SetCommentFrequency / ReloadScript`。運作：用 `RegisterForSingleUpdate` 週期醒來，依 `SofiaCommentFrequency`（GLOB，MCM 可調 0=關）決定間隔，`SofiaDisableComments` 為總開關；觸發時呼叫 `GetPlayerDialogueTarget`（透過 `JJSofiaGetTargetSpell` 取玩家瞄準對象，見下）→ 啟動 `JJSofiaIdleDialogueScene` 或 `JJSofiaMainQuestDialogueScene` 念一句。同檔還掛 `JJSofiaSetHorseSpell`、`SummonSofiaSpell`、左手法術（`FireboltLeftHand/LightningBoltLeftHand/IceSpikeLeftHand`），並用 `IsInDialogueWithPlayer` 避免插嘴。**這支 + 259 個 TIF 對白池，就是「語音隨從會自言自語」的全部機制——純 timer-poll + scene.Start()，零 SKSE。**

- **`JJSofiaQuestUpdateScript.psc`**（掛 `JJSofiaMainQuestDialogue`，7 函式）—— 另一個 comment 觸發器，專管「劇情情境評論」：`SofiaWitnessDragon`（目睹龍時吐槽）、`SofiaMakeComment`、`GetPlayerDialogueTarget`。對應 record 層 `JJSofiaWitnessDragon` GLOB。

- **`JJSofiaGetTargetScript.psc`**（小，掛 `JJSofiaCastSpell`）+ **`jjsofiagettarget` 機制** —— 透過一個施在玩家身上的 spell 取得「玩家正看著誰/什麼」，供 comment 系統決定要評論誰。這是 Skyrim 沒有原生「取玩家準心目標」API 時的標準 workaround（cast 一個 script effect 法術讀 target）。

- **`JJSofiaQuestLineManager.psc`**（**161 個 property，零自訂函式**）—— 不是邏輯，是個**巨型 property 索引表**：`MQLine1..45`、`CollegeQuestLine1..28`、`CompanionsQuestLine1..20`、`ANightToRememberQuestLine1..8`、各 Daedric quest（BoethiahsCalling / TheBlackStar / TheCursedTribe / IllMetByMoonlight / TheHouseOfHorrors / DiscerningTheTransmundane / TheOnlyCure / ADaedrasBestFriend / TheBreakOfDawn / TheWhisperingDoor / WakingNightmare / TheMindOfMadness / PiecesOfThePast）的逐 stage 引用。它讓 Sofia 的對白條件能用「玩家在 X 主線/支線進行到第 N 步」當觸發——把幾十條 vanilla quest 的 stage 全綁進 property，對白才能「應景」。對照 `JJSofiaVariablesScript` 裡那批 `Accompanied*`（見下）。

### C. 狀態中樞與關係/婚姻/醉酒

- **`JJSofiaVariablesScript.psc`**（掛 `JJSofiaVariables`，**33 個 conditional property，僅 GetState/GotoState 無自訂函式**）—— record 層提到的「變數中樞」。全是布林/數值 property 當持久化旗標：`RelationshipLevel`、`SofiaIsDating`、`SofiaIsMarried`、`IsDrunk`、`IsTalking`、`KillsWitnessed`、`DungeonsWitnessed`、`TimeAccompanied`、`DaysAccompanied`、`NudeBombReady`、`SandboxingEnabled`、`InitiateRomanceDialogue`、`InitiateMarriagePrompt`，以及一整排 `Accompanied<VanillaQuest>`（AccompaniedMainQuest / AccompaniedCompanionsQuest / AccompaniedTheBlackStar / …）。**conditional property 會被對白 condition 直接讀**——這是 Sofia 把「狀態」攤在 Papyrus property 上、讓對白系統零成本查詢的手法，等價於別的 mod 用 StorageUtil 存的東西，但這裡純靠 quest script property 落存檔。

- **`JJSofiaRelationshipScript.psc`**（掛 `JJSofiaRelationship`，3 prop + `UpdateSofiaStats`）—— 好感度/統計累加。`OnUpdateGameTime` 週期跑 `UpdateSofiaStats`，把「Dungeons Cleared / People Killed / Animals Killed / Creatures Killed / Undead Killed / Daedra Killed / Automatons Killed」這些見證統計寫進 quest（字串字面值直接出現在 string table）。配 record 層 `SofiaPlayerLike` GLOB。

- **`SofiaMarriageScript.psc`**（掛 `JJSofiaRelationship`，`UpdateGold/SofiaInvestGold/CancelInvestGold` + `OnLocationChange`）—— 婚後經濟系統。`OnUpdateGameTime` 定期讓已婚 Sofia「找到 gold 分給你」或「花你的 Septims」（字面值「Sofia has found … gold which she shares with you.」/「Sofia has spent … Septims of your gold.」），`OnLocationChange` 配 `LocTypeTown`/`LocTypeCity` keyword 判斷在城鎮才結算。`SofiaInvestGold` 是 vanilla 配偶店鋪投資的仿作。

- **`SofiaDrunkScript.psc`**（掛 `JJSofiaDrunk`，9 prop）—— 醉酒狀態機。`OnInit/OnUpdateGameTime` 排程，property 串起 `SofiaDrinkPackage`/`SofiaDrunkPackage`/`SofiaDrunkStopPackage` 三個走路搖晃 package + `JJSofiaDrunkScene`/`JJSofiaDrunkSceneEnd`/`JJSofiaDrunkGiveDrinkDialogue` 三個 scene/對白。對照 record 層 drunk stage 0–50 與 `JJSofiaDrunkScene`（RepeatConditionsWhileTrue 循環）。

### D. 外觀 / 物品 / 換裝

- **`SofiaOutfitManagement.psc`**（`OnItemAdded/OnItemRemoved/SortOutfitStore`）+ **`SofiaSortOutfit.psc`** + **`SofiaWardrobeScript.psc`**（`OnItemAdded/RedressSofia/OnCombatStateChanged`）—— 換裝/衣櫥系統，監聽 container 物品進出自動分類、戰鬥結束後 `RedressSofia` 補穿。對應 record 層 `SofiaStorage`/`SofiaClothes` container 與 `JJSofiaWardrobe` quest。
- **`SofiaClothingFix.psc`** —— record 層提到的「脫衣 glitch」矯正。
- **`SofiaPlayerGive.psc`** / **`JJSofiaRecieveGold.psc`**（sic）—— 送禮收禮、收金幣（提升好感度），對應 `JJSofiaGiveGift` quest。
- **`SofiaNudeBombScript.psc`**（`OnEffectStart` → 是個 ActiveMagicEffect 腳本）—— record 層 `SofiaNudeBombSpell` 的效果腳本。

### E. 系統 / 基礎建設

- **`SofiaMCMscript.psc`**（掛 `JJSofiaMCM`，**最大的 script，21.7 KB、19 函式、24 prop**）—— SkyUI MCM 設定選單。函式全是 SkyUI 框架回呼：`OnConfigInit/OnConfigOpen/OnConfigClose/OnPageReset/OnOptionSelect/OnOptionSliderAccept/OnOptionMenuAccept/…`，外加 `ResetSofia`（重置隨從）、`RemoveAllSpells`、`UpdateStats`、`IntToHex`。它 `extends SKI_ConfigBase`（SkyUI 提供的基底；同 BSA 內無此基底 `.pex`，靠玩家裝 SkyUI 提供），把 record 層那批 MCM-寫入 GLOB（`SofiaCatchUpEnabled/Distance`、`SofiaCommentFrequency`、`SofiaDisableComments`、`SofiaHorseEnabled`、戰鬥風格 index…）暴露成可調選項。**這是 Sofia 唯一真正吃 SKSE/SkyUI 的地方，且為選配。**
- **`SofiaHasSKSEscript.psc`**（`CheckSKSE`）+ **`SofiaCheckOnLoadSKSE.psc`** —— **SKSE 探測降級**。`CheckSKSE` 呼叫 `SKSE.GetVersion()`（string table 裡的 `skse` / `GetVersion`）判斷有無 SKSE，設 `SofiaHasSKSE` GLOB；沒 SKSE 就跳過 MCM、用預設值跑。這就是 readme「Do I need SKSE? No」的程式碼證據。
- **`SofiaNewVersionScript.psc`** / **`SofiaUpdateScript.psc`** / **`SofiaReloadScripts.psc`** / **`JJSofiaScriptsStartup.psc`** —— 版本升級/腳本熱重載骨架（舊存檔升新版時重設 property、重註冊 update）。對應 record 層 `SofiaIsUpdated`/`SofiaModVersion` GLOB。
- **`SofiaAliasScript.psc`**（`OnDeath/OnPackageChange`，`extends ReferenceAlias`）—— 掛在 Sofia 的 alias 上，處理她死亡（essential 復活流程）與 package 切換。
- **`SKI_PlayerLoadGameAlias.psc`**（`OnPlayerLoadGame`）—— SkyUI 提供的標準「玩家讀檔時觸發」alias 基底（隨 SkyUI 一起編進來，用於 MCM 重註冊）。
- **`JJSofiaSummon.psc`** / **`JJSofiaSetHorseEffect.psc`** —— 召喚找人 spell（`SummonSofiaSpell`）與召喚馬的 magic effect。
- **`SofiaKeyDebugScript.psc`**（`OnKeyDown` + `RegisterForKey`）—— **熱鍵 debug**（需 SKSE 的 `RegisterForKey`），開發者用，玩家版多半不綁鍵。

### F. 每-NPC comment（手刻 9 支，非模板展開）

`nazeem_comment1..3`、`carlotta_comment1..4`、`braith_comment1..2` —— 對應 record 層那套「8 組 `*Comment` quest + `*SayComment` scene」。**注意：這些是手刻命名的獨立 fragment，不是程式化批次展開**——印證 record 層的判斷「同一份模板複製 N 份、手動換目標 actor 與台詞」。Guard/Taarie 的 comment 則走 SF（`sf_jjsofiaguardsaycomment` / `sf_jjsofiataariesaycomment`），混用兩種掛法。

## 狀態管理手法 —— 印證「零 SKSE 資料結構依賴」

對全部 323 個 `.pex` 的 string table 做精確 token 掃描（`StorageUtil` / `JContainers64` / `JValue` / `JFormDB` / `JIntMap` / `JFormMap` / `PapyrusUtil`）：**零命中**。唯一含 `skse` 子字串的是檔名（`SofiaHasSKSEscript` 等），其引用的也只是 `SKSE.GetVersion()` 做版本探測，與 `RegisterForKey`（debug 熱鍵，選配）。

因此 record 層的結論在程式碼層完全成立——Sofia 的狀態三條腿：

1. **GlobalVariable（57 個）**：跨子系統共享的旗標與設定（catch-up/comment 開關與數值、好感度 `SofiaPlayerLike`、`SofiaHasSKSE`、技能鏡像、暫存 `JJTemp*`）。多支 script 共讀同一批 GLOB（如 `SofiaCommentFrequency` 被 CommentScript 與 MCMScript 共用）——GLOB 當「跨 script 全域變數」用。
2. **Quest script property**：`JJSofiaVariablesScript` 的 33 個 conditional property、`SofiaMCMscript` 24 prop、`SofiaFollowerScript` 12 prop、`JJSofiaQuestLineManager` 161 prop——Papyrus property 隨 quest 進存檔，承載「複雜/結構化但無需 per-actor 表」的狀態。conditional property 還能被對白 condition 直接讀，省去 getter。
3. **Quest stage**：線性進度（wedding 0→200、drunk 0→50），由 QF fragment 推進。

**為何夠用、不需 JContainers**：Sofia 是唯一隨從，好感度只要一個 GLOB，從不需要「每個 NPC 各自一張狀態表」那種會逼出 JFormDB 的場景（對照 `architecture/jcontainers.md` 對 per-actor KV 的分析）。`JJSofiaQuestLineManager` 那 161 個 property 看似龐大，但它是**靜態的 Form 引用表**（編譯期固定），不是 runtime 動態增長的容器——用 property bag 就能裝，正是「不掛 native 資料結構」的關鍵。

## 對 ModForge 的意義

ModForge 已能生成 fragment 那一層（quest fragment / TIF fragment / scene fragment Papyrus，見 ModForge CLAUDE.md「已落地功能」）。Sofia 的 283 個 fragment（TIF/SF/QF/PF）正落在 ModForge 的能力範圍內、且本就該被自動生成。**真正的缺口是那 31 個具名常駐邏輯 script**——一個能動的隨從靠它們活著，而 ModForge 目前一個都不生成。把它們整理成「ModForge 若要做隨從品類，需補的 script 模板」優先序：

1. **跟隨距離維持 / catch-up（`SofiaCatchUpNewScript` 模式）** —— 最不可省。`OnUpdate` poll + `GetDistance` 比 `SofiaCatchUpDistance` GLOB + `HasLOS` + `MoveTo`(+`SetAlpha` 隱形瞬移) + `EvaluatePackage`。這是「隨從不會永遠卡在門後」的引擎。ModForge 有 follow PACK template，但沒有這支補丁式 catch-up script——應做成一個參數化模板（距離 GLOB + 目標 alias）。
2. **comment 排程器（`SofiaCommentScript` 模式）** —— 「會講話的隨從」核心。timer-poll（`RegisterForSingleUpdate`）+ frequency GLOB + 總開關 GLOB + `scene.Start()` 念一句 + `IsInDialogueWithPlayer` 防插嘴。ModForge 有 AutoStart 在場偵測 scene controller（`MFSceneBanterController`），形狀已很接近——把它擴成「依 frequency 週期觸發 idle banter scene」就補上了，這是 ModForge 既有資產最容易延伸出的一支。
3. **取玩家準心目標（`JJSofiaGetTargetScript` 模式）** —— Skyrim 無原生 API，靠 cast 一個 script-effect spell 讀 target。任何「對你正看的東西做反應」的隨從都要這支。小而通用，值得做成模板。
4. **狀態中樞 quest script（`JJSofiaVariablesScript` 模式）** —— 一個 quest 掛滿 conditional property 當持久化狀態表，被對白 condition 直接讀。ModForge 已會生 GlobalSpec（GLOB），但 conditional-property-on-quest 這種「能被對白 condition 讀的 per-quest 狀態」目前沒有抽象——對隨從對白分支很有用。
5. **MCM 設定選單（`SofiaMCMscript` + `SofiaHasSKSEscript` 降級）** —— `extends SKI_ConfigBase` + 一套 OnConfig* 回呼把 GLOB 暴露成選項，配 `SKSE.GetVersion()` 探測降級。隨從類 mod 幾乎都有 MCM，這是 ModForge 最大的「使用者可調設定」缺口（與 `architecture/sofia-follower.md` 的結論一致）。需要生成 SkyUI 基底依賴 + config schema → OnConfig* 模板。
6. **版本升級/腳本重載骨架（`Sofia*Update/NewVersion/ReloadScripts`）** —— 任何要「更新後不破壞舊存檔」的 mod 都需要。ModForge 生成物若要可長期維護，這是務實的一塊。

務實結論：Sofia 在程式碼層也證明了「純 GLOB + quest property + quest stage，零 SKSE 資料結構」足以撐起成熟單體隨從。ModForge 預設不需要 native 依賴。但「隨從會跟上、會應景吐槽」這兩件最定義「活隨從」的事，分別靠 catch-up script 與 comment 排程器——這兩支（加上取準心目標的小工具）是 ModForge 把「能生隨從骨架」變成「能生有靈魂的隨從」最值得先補的 script 模板，且都與 ModForge 既有的 PACK / AutoStart-scene 資產同源、延伸成本低。

## 解包方法與還原程度

**BSA 解包（自寫 extractor，完整還原檔案）。** 目標 `SofiaFollower.bsa`（78 MB），header magic `BSA\0`、version `0x69`(105) = Skyrim SE 格式。先解 36-byte header：`archive_flags = 0x3`（bit0 dir-names + bit1 file-names 存在，**bit2 compressed 未設**），故檔案**未壓縮**、無需 zlib（每檔資料即原始 bytes）。folder_count=13、file_count=1824。用 Python 按 v105 佈局自寫 extractor：13 個 24-byte folder record（uint64 hash / uint32 count / uint32 pad / uint64 offset，offset 需減 total_file_name_length 才是真實位置）→ 每 folder block 前置 1-byte 命名長度 + folder 名 + N 個 16-byte file record（uint64 hash / uint32 size / uint32 offset；size bit30 = 與 archive 預設相反的壓縮 toggle，本檔皆未壓）→ 末端 file-name block（null 分隔，與 record 同序）。只抽 `folder.startswith('scripts')` 的條目，得 **323 個 `.pex`，零遺漏、零損毀**（mesh/texture/voice 未抽）。BSA 內**無 `scripts/source/*.psc`**，只有編譯後 bytecode。pip 上的 `bsa` 套件無內容、`bethesda-structs` 未安裝，故未用第三方庫。

**`.pex` 反組（自寫 PEX header/string-table/debug 解析器，函式簽名級還原）。** Champollion（完整反編譯器）未 build（vcpkg 條目存在但 build 過重，放棄）。改用 Python 自寫 PEX 解析器：PEX 為 big-endian、magic `0xFA57C0DE`，依序讀 header → **string table（u16 count + 每筆 u16-len 字串）** → **debug info（每函式：object/state/name 字串索引 + type + 指令數）** → user-flags/objects。本解析器**完整還原了 string table 與 debug 函式表**（object::state::function 三元組）——這已足以取得：每個 script 的真實 `.psc` 名、所有自訂函式名、所有 property/變數名（`::Xxx_var` 樣式）、所引用的引擎 API 與型別名、以及所有字串字面值（含對白訊息如「Sofia has spent … Septims」）。**未還原的是函式體 bytecode（opcode 指令流）**——故「邏輯做什麼」是由「函式名 + property 名 + 被呼叫的引擎函式名 + 字串字面值 + 對照 record 層」推斷，而非逐行反編譯。對本分析（架構、子系統分工、狀態管理手法、ModForge 模板缺口）這個還原層級完全足夠且結論可靠；若需逐行演算法細節（如 catch-up 的確切距離判斷分支），才需要 Champollion 級反編譯。
