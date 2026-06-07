# Sofia Follower v2.51

## 定位

完整的**語音隨從（voiced follower）mod**，作者 John Jarvis（配音 Christine Slagman）。和 JContainers 那種「純 library、零內容」相反——Sofia 是**滿載內容**的單一 ESP：1741 個 record，其中超過 1100 條對白回應、近 30 個 quest、28 個 scene、54 個 AI package。它幾乎只用**原版引擎機制**（quest / scene / dialogue / package / GlobalVariable）堆出一個有個性、會吐槽、能結婚、能喝醉的隨從，**不掛任何 SKSE 資料結構依賴**（dump 中 `jcontainer/jvalue/jformdb` 出現次數為 0；readme 也明說「Do I need SKSE? No」，SKSE 只用於選配的 MCM 選單）。

對 ModForge 而言，Sofia 是「一個成熟隨從 mod 在 record 層長什麼樣」的黃金樣本，特別適合對照 ModForge 既有的 QuestSpec / SceneSpec / NpcSpec / GlobalSpec / PACK templates。

## 檔案結構

來源：`~/skyrim_mods/Sofia Follower v.2/`

- `Data/SofiaFollower.esp` —— 主檔，master(s) = `[Skyrim.esm, Update.esm]`（`/tmp/mfdump/sofia.txt:1`），localized=False（字串內嵌、非 .strings 外置）。
- 2 個 BSA（script `.pex`、voice `.fuz`、mesh/texture `.nif/.dds`）——**無工具解包**，本分析聚焦 ESP record 層。
- `Sofia Follower Readme V.2.51.txt` —— 起始流程、summon spell、drunk/relationship 系統線索。

起始劇情（readme）：玩家到 Whiterun 馬廄（horses 那塊，不是建築）→ 喚醒躺在乾草堆的 Sofia → 對話邀請入隊。找不到她可用 summon spell 或 quest journal 的 tracking marker。

record 類型分佈（前段）：DialogResponses 1135 / DialogTopic 239 / DialogBranch 63 / Package 54 / GlobalShort+Float 57 / Quest 30 / Scene 28 / PlacedObject 26 / FormList 15 / Spell 9 / Npc 9 / DialogView 9 / Class 6 / ArmorAddon 6 / CombatStyle 5 / VoiceType 4 / Cell 4 / Worldspace 3 / Relationship 3 / Faction 3 / Container 3 / StoryManagerQuestNode 1 / NavigationMesh 1。

> 命名慣例：作者前綴混用 `JJ`（John Jarvis）與 `Sofia`，readme 也說「Most things related to Sofia will either start with the prefix JJ or have Sofia in the name」。

## record 解剖

### 1. Quest 全表（30 個）—— 「一個隨從用幾十個 quest 各司其職」

來源：`/tmp/mfdump/sofia.txt:7267`–`7386`。把 30 個 quest 按職責分群：

#### A. 主控 / 狀態核心
| Quest | FormID | 掛載 script（屬性數） | 角色 |
|---|---|---|---|
| `JJSofiaFollowerMain` | `[01010A]` | SofiaFollowerScript (12) | 隨從主狀態機，objective[10]「is waiting for you」 |
| `JJSofiaScripts` | `[00AA58]` | SofiaNewVersionScript(16)+SofiaUpdateScript(18)+SofiaCatchUpNewScript(16) | 版本升級 / catch-up 跟隨邏輯總成 |
| `JJSofiaVariables` | `[0557B1]` | JJSofiaVariablesScript (19) | 變數中樞，flags=273（StartGameEnabled），quest script property 存狀態 |
| `JJSofiaRelationship` | `[05373C]` | JJSofiaRelationshipScript(3)+SofiaMarriageScript(5) | 好感度 + 婚姻條件追蹤 |

#### B. 對話容器（每個 quest = 一批 dialogue / scene 的掛載點）
- `JJSofiaDialogue` `[001D8B]`（SofiaCommentScript 14 prop）—— 核心隨從互動分支（trade / part ways / follow / can I talk / storage…，見 DialogBranch 群 `:7548`+）。
- `JJSofiaIdleDialogue` `[007F02]` —— 閒聊；單一 scene topic 掛 **149 個 INFO group**（`:1420`），是全 mod 最大的對白池。
- `JJSofiaMainQuestDialogue` `[020467]`（JJSofiaQuestUpdateScript 7 + JJSofiaQuestLineManager 0）—— Sofia 個人主線劇情。
- `JJSofiaSidequestDialogue` `[034EBF]` —— bounty / 支線。
- `JJSofiaBardSongs` `[02F2D1]` —— 唱歌（多首歌各一個 scene，見下）。

#### C. 互動 comment（對特定 vanilla NPC 吐槽，高度模板化）
8 組，每組「`*Comment` quest（priority=60）+ `*SayComment` scene（flags=BeginOnQuestStart, StopQuestOnEnd）」成對出現：
`JJSofiaNazeemComment` `[03088D]` / `JJSofiaCarlottaComment` `[03BB10]` / `JJSofiaBraithComment` `[03CB44]` / `JJSofiaLarsComment` `[06FCCB]` / `JJSofiaNelkirComment` `[070239]` / `JJSofiaTaarieComment` `[070244]` / `JJSofiaEndarieComment` `[070251]` / `JJSofiaGuardComment` `[070D22]`。

這些 comment quest 用 `alias[2]` 直接 `uniqueActor` 指向 vanilla NPC，例如 `LarsRef -> 013BAF:Skyrim.esm`、`NelkirRef -> 01434D:Skyrim.esm`、`TaarieRef -> 0132AB:Skyrim.esm`、`EndarieRef -> 01326F:Skyrim.esm`（`:7371`–`7380`）。**這是「批次生成的 per-NPC 吐槽」設計模式**——同一結構複製 8 份，只換目標 actor 與對白。

#### D. 系統 / 工具
| Quest | FormID | 用途 |
|---|---|---|
| `JJSofiaMCM` | `[00C55D]` | SofiaMCMscript (26 prop)，SkyUI MCM 設定選單 |
| `JJSofiaGetHasSKSE` | `[00E5FE]` | SofiaHasSKSEscript，偵測有無 SKSE → 設 `SofiaHasSKSE` GLOB |
| `JJSofiaTrackingMarker` | `[043CED]` | flags=281，objective「Sofia Tracking Marker」（可在 journal 切換的找人 marker） |
| `JJSofiaClothingFix` | `[04BAE3]` | 修「脫衣 glitch」的外觀矯正 |
| `JJSofiaWardrobe` | `[061F70]` | 衣櫥/換裝 |
| `JJSofiaBattleCommands` | `[030DF3]` | priority=90，戰鬥指令 |
| `JJSofiaCastSpell` | `[03749E]` | 觸發 Sofia 施法（nude bomb 等） |
| `JJSofiaGiveGift` | `[040C27]` | 送禮（提升好感度） |
| `JJSofiaLeadTheWay` | `[017D1E]` | 帶路到目的地 |

#### E. 劇情 / 演出
- `JJSofiaWeddingCeremony` `[05167F]`（QF script 11 prop，flags=**RunOnce**，priority=100）—— 完整婚禮，stage 0→5→10→20→150(FailQuest「You stood Sofia up」)→200(CompleteQuest「You married Sofia」)，objective「Go To Wedding」（`:7343`–`7358`）。
- `JJSofiaDrunk` `[01A866]`（priority=100）—— 醉酒系統，stage 0–50。readme 提供 console 救援 `stopquest jjsofiadrunk`。
- `JJSofiaQuest` `[0285BD]` —— 起始 meeting quest，stage[0]=**StartUpStage**（馬廄醒來/邀請）。
- `JJJarvisDialogue` `[0343F0]` —— 作者彩蛋角色 Jarvis。

**設計模式歸納**：Sofia 把一個隨從拆成「**一個職責一個 quest**」的微服務式架構——狀態核心、跟隨邏輯、每種互動、每首歌、每個被吐槽的 NPC、每個系統功能各自一個 quest。好處是各功能可獨立 start/stop（readme 的救援指令正是靠這個粒度），壞處是 record 數爆炸（光 comment 就 8×2 個 record）。

### 2. Scene 解剖

Skyrim 的 scene = **phase 序列**，每個 phase 綁一個 action（Dialog / Package / Timer），actor 透過 alias 索引引用，並帶 behavior flags 控制中斷行為。

#### 範例（主貼）：`JJSofiaMainQuestDialogueScene` `[020468]`

來源：`/tmp/mfdump/sofia.txt:7702`–`7722`。**1 actor / 17 phase / 17 action**，是「一句台詞一個 phase」的線性獨白：

```
Scene JJSofiaMainQuestDialogueScene
  script: SF_JJSofiaMainQuestDialogueS_02020468 [1 prop(s)]
  scene: quest=JJSofiaMainQuestDialogue  flags=Interruptable  1 actor(s), 17 phase(s), 17 action(s)
    actor alias #0  behavior=DeathEnd, CombatEnd, DialoguePause
    action: Dialog alias #0 phase 0  -> topic 020469:SofiaFollower.esp (Neutral)
    action: Dialog alias #0 phase 1  -> topic 047839:SofiaFollower.esp (Neutral)
    action: Dialog alias #0 phase 2  -> topic 0500E1:SofiaFollower.esp (Neutral)
    ...（phase 3–15，每行 Dialog alias #0 -> 一個 topic）...
    action: Dialog alias #0 phase 16 -> topic 06B15B:SofiaFollower.esp (Neutral)
```

要點：
- **actor alias #0 的 behavior flags**：`DeathEnd`（actor 死則 scene 結束）、`CombatEnd`（進戰鬥則結束）、`DialoguePause`（玩家發起對話時暫停）——這是「演出中可被打斷、不卡死」的標準三旗標，全 mod 幾乎每個 scene 都用。
- 17 個 phase 都是同一個 actor（alias #0 = Sofia）對著玩家連說 17 句；scene 本身只負責**排序與節拍**，台詞內容在各 topic 的 INFO 裡。
- scene-level `flags=Interruptable`：整段可被中斷。

#### 範例（對比）：`SofiaWeddingScene` `[051BF6]` —— 多 actor 編排

來源：`:7805`–`7827`。**3 actor / 20 phase / 17 action**，flags=StopQuestOnEnd：

- actor alias #0（Sofia）、#2（Crooked Priest）、#1 交錯念誓詞（phase 1 Sofia → phase 4 Priest → phase 5 Sofia …），中間穿插 `Package alias #2 phase 2`、`Package alias #2 phase 17`（NPC 走位）。
- 證明 scene 能做**多角色對拍 + 走位**的完整演出，且 phase 數（20）> action 數（17）——有些 phase 是純等待節拍、不掛 action。

#### scene 的三種 action 類型（與 ModForge 對齊）
全 28 個 scene 只用到三種 action：
1. **Dialog**（最多）—— 綁一個 dialog topic 念一句。
2. **Package**—— NPC 做動作，如 `JJSofiaCastNudeBomb`（`:7750`，1 phase 1 action = Package alias #0）、`JJSofiaMountHorseScene`/`DismountHorseScene`（`:7797`/`7801`）。
3. **Timer**—— 停頓。見 `JJSofiaDrunkScene` `[07387F]`（`:7875`）：3 phase / 4 action，混用 `Package alias #0 phase 0` + `Timer alias #0 phase 0` + `Dialog phase 1` + `Timer phase 1`，flags=**RepeatConditionsWhileTrue**（醉態循環）。

comment scene 的共同模板（`JJSofia*SayComment`）：2 actor（Sofia + 目標 NPC）/ 2 phase，phase 0 Sofia 開口（情緒常為 Disgust/Anger）→ phase 1 目標 NPC 回嘴，flags=`BeginOnQuestStart, StopQuestOnEnd`（quest 一啟動就演、演完關 quest）。例 `JJSofiaNazeemSayComment`（`:7744`）。

### 3. Package（54 個）—— 隨從行為骨架

來源：`:7387`–`7499`+。所有 package 都 `template=` 引用 vanilla package 當骨架，再覆寫資料。按用途分群：

- **跟隨變體**：`SofiaFollowerPackage` `[013192]`、`JJSofiaFollowPackage` `[049FF0]`、`SofiaFollowBeside` `[065568]`、`SofiaFollowSneaking` `[06602E]`、`SofiaFollowIdleWait` `[06602F]`、`SofiaFollowWeaponDrawn` `[066AF5]`、`SofiaFollowerStealthKillPackage` `[030DF4]`（AlwaysSneak+WeaponDrawn）。
- **戰鬥風格覆寫**（一大群 `SofiaCombatOverride*`，各引用不同 CombatStyle，內外景成對）：MagicOnly / MeleeOnly / RangedOnly / DualWeildOnly / 各 Default + Exterior 版，外加 Brawl / CoveringFire / IgnoreCombat。對應 MCM 的戰鬥風格切換（見 `SofiaCombatStyles` FormList `[014C9D]`）。
- **解散 / 待命**：`SofiaDismissedSandbox` `[01169B]`、`SofiaFollowerSandbox` `[04AAB5]`、`SofiaStayAtCurrentLocation` `[038F9C]`、`JJSofiaNPCStandStill` `[03646E]`。
- **坐騎**：`SofiaHorseFollowerPackage` `[010BD0]`、`SofiaHorseSummoned` `[01318E]`、`JJSofiaMountHorse` `[0447B2]`、`JJSofiaDismountHorse` `[044D1B]`、`SofiaHorseFleeCombat` `[043CE9]`。
- **劇情 / force-greet**：`SofiaMeetingSleep` `[0285BC]`（馬廄睡覺）、`SofiaIntroForceGreet` `[02B20C]`（MustComplete，強制搭話）、婚禮系列（`SofiaGoToWeddingPackage`、`CrookedPriestGoToWedding`、`PlayerSofiaWeddingTakePosition`、`SofiaWeddingPriestFG01/02`…）、醉酒（`SofiaDrinkPackage`/`SofiaDrunkPackage`/`SofiaDrunkStop`）、`SofiaCastNudeBombPackage`。

要點：所有 package 都掛在某個 quest（`quest=` 欄）或由 alias 動態套用；戰鬥覆寫透過 FormList + GLOB index 在 runtime 切換，不重建 record。

### 4. GlobalShort/Float（57 個）—— 隨從的 runtime 設定與狀態旗標

來源：`:24`–`80`。GLOB 同時扮演「使用者設定」與「狀態旗標」兩種角色：

- **使用者設定（MCM 寫入）**：`SofiaCatchUpEnabled` / `SofiaCatchUpDistance`(Float) / `SofiaDisableComments` / `SofiaCommentFrequency`(Float) / `SofiaNudeBombEnabled` / `SofiaHorseEnabled` / `SofiaFollowBesideVar` / `SofiaCombatStyleNum` / `SofiaCombatClassIndex` / `SofiaCombatStyleIndex`。
- **狀態旗標**：`SofiaShouldTalk` / `SoifaIsTalking`(sic) / `SofiaIsGivingItem` / `SofiaHorseIsSummoned` / `SofiaIgnoreCombat` / `JJSofiaHasMetPlayer` / `JJSofiaMainQuestStage` / `JJSofiaWitnessDragon` / `SofiaWeddingStoodUp` / `SofiaPlayerLike`（好感度數值）/ `SofiaNPCresponse` / `SofiaIsUpdated`。
- **環境偵測**：`SofiaHasSKSE`、`SofiaModVersion`(Float，版本號)。
- **整排技能鏡像**：`SkillOneHanded` … `SkillSpeech` 共 18 個——把玩家全技能複製進 GLOB（推測供對白/戰鬥風格條件判斷用）。
- **玩家裝備分類**：`JJPlayerOutfitType` / `JJIsCriminalOutfit` / `JJIsHeavyArmour` / `JJIsRevealing` / `JJIsMageOutfit` / `JJIsBadOutfit` / `JJIsGoodOutfit`（配合 `JJPlayerCriminalOutfits` 等 FormList，讓 Sofia 評論玩家穿著）。
- **通用 scratch**：`JJTempBool` / `JJTempInt` / `JJTempFloat` / `JJTempIndex`（Papyrus 沒有好的暫存機制時，用 GLOB 當共享暫存變數）。

### 5. 狀態存儲觀察

**Sofia 幾乎完全靠 GLOB + quest stage + quest script property 存狀態，沒掛 JContainers**：

- 57 個 GLOB 承載所有跨存檔的旗標與設定。
- quest stage 承載線性進度（wedding 0→200、drunk 0→50、main quest stage 透過 `JJSofiaMainQuestStage` GLOB 鏡像）。
- 複雜狀態塞進 quest 上的 script property（`JJSofiaVariablesScript` 19 prop、`SofiaMCMscript` 26 prop、`SofiaFollowerScript` 12 prop）——Papyrus property 本身會進存檔。
- **沒有 per-actor 動態狀態表的需求**：Sofia 是唯一隨從，好感度只需一個 `SofiaPlayerLike` GLOB，不像「每個 NPC 各自好感度」那種會逼出 JFormDB 的場景。這正解釋了她為何不需要 JContainers。

其餘支援 record（簡述）：
- **NPC（9）**：`JJSofiaFollower` `[0012C4]`（race 013746=Nord female、class=SofiaCombatSpellsword、voice=JJSofiaVoiceType、aiData Aggressive/Foolhardy、3 perk）；配角 Voldar / Jarvis / OldMage / MasterThief / CrookedPriest（婚禮主持）/ JJSofQuestGuard / GiftStorage / JJSofiaHorse。
- **Relationship（3）**：`NataliePCRelationship` `[001828]`（parent=JJSofiaFollower child=Player rank=**Ally**，"Natalie" 疑為 Sofia 內部代號）；`SofiaHorseRelationship`、`HorsePlayerRelationShip`（馬↔Sofia/玩家 Ally）。用 RELA record 直接固定隨從對玩家友好。
- **Faction（3）**：`SofiaFollowerFaction` / `SofiaDismissedFaction` / `SofiaBrawlFaction`——隨從狀態用 faction membership 表示。
- **Spell（9）**：`SummonSofiaSpell` `[043CEB]`（玩家用的召喚找人）、`SofiaSummonHorseSpell`、`SofiaNudeBombSpell`、`JJSofiaGetTargetSpell`（取玩家目標）、`SofiaFirebolt/LightningBolt/IceSpikeLeftHand`（左手法術，供戰鬥風格用）。
- **VoiceType（4）**：`JJSofiaVoiceType` `[0022EE]` + Jarvis/CrookedPriest/Colin 配角音。
- **CombatStyle（5）**：`SofiaMeleeOnly/RangedOnly/MagicOnly/DualWeildOnly` + `csVoldar`，配 6 個 Class，組成 MCM 可切換的戰鬥矩陣。
- **Container（3）+ Cell（1）**：`SofiaStorage`/`SofiaClothes`/`SofiaTempStore` 放在自訂內景 cell `JJSofiaStore` `[00E600]`（readme 的 `coc jjsofiastore`），含 1 個自訂 NavigationMesh。
- **StoryManagerQuestNode（1）**：`JJSofiaGuardTrigger` `[07182A]`——唯一一個 SM 觸發（衛兵互動），其餘對話皆靠 force-greet package / scene，非 SM。
- **DialogView（9）**：CK 用的對話視圖容器（QuestMeeting / IntroForceGreet / BardSongs / GiveGift / Wedding / Relationship / Questions / GenericFollower / LeadTheWay），把分散在多 quest 的 branch 聚到一個 CK 編輯視圖。

## 關鍵設計

- **微服務式 quest 拆分**：一個職責一個 quest（30 個），換取獨立 start/stop 的可控性與救援能力（readme 全靠 `stopquest`/`startquest` 粒度排錯）。
- **批次模板化 comment**：8 組 `*Comment`+`*SayComment` 結構同構、只換目標 actor 與台詞——典型「同一份模板複製 N 份」需求。
- **scene = phase 序列 + 三種 action**：Dialog（念台詞）/ Package（走位、施法）/ Timer（停頓），actor 用 alias 索引、帶 DeathEnd/CombatEnd/DialoguePause 三旗標確保可中斷不卡死；單 actor 線性獨白與多 actor 對拍（婚禮）共用同一機制。
- **GLOB 萬用化**：設定、狀態、技能鏡像、裝備分類、甚至暫存變數全用 GLOB——因為只有一個隨從，不需要 per-actor 狀態表，這是「不掛 JContainers 也夠用」的根因。
- **vanilla template 覆寫**：54 個 package 全 `template=Skyrim.esm:...`，戰鬥風格用 FormList+GLOB index 在 runtime 切換而非重建 record。
- **SKSE 為選配**：核心功能零 SKSE 依賴，MCM 才需要；`JJSofiaGetHasSKSE` 在 runtime 探測並降級。

## 對 ModForge 的意義

ModForge（`~/repo/ModForge`）已有 QuestSpec / SceneSpec / ScenePhaseSpec（Dialog/Package/Timer action）/ NpcSpec / GlobalSpec / RelationshipSpec / PACK templates / AutoStart 在場偵測。對照 Sofia 的真實做法：

### ModForge 已對齊的
- **Scene 結構**：Sofia 的 scene 正是 ModForge SceneSpec/ScenePhaseSpec 的形狀——phase 序列、每 phase 一個 Dialog/Package/Timer action（ModForge `SceneAction.TypeEnum` 恰好就這三種，見 ModForge CLAUDE.md 鐵律），actor alias + DeathEnd/CombatEnd/DialoguePause behavior flags。Sofia 的 `JJSofiaMainQuestDialogueScene`（17 phase 線性獨白）幾乎可一對一用 ModForge ScenePhaseSpec 重建。
- **comment scene 的 BeginOnQuestStart/StopQuestOnEnd**：對應 ModForge scene `Conditions.beginOnQuestStart`。
- **Package 走位 action**：對應 ModForge scene 的 Package action 引用 `packages[]` 的 PACK。
- **GlobalSpec**：Sofia 的 57 個 GLOB 正是 ModForge GlobalSpec（short/long/float）的目標用例。
- **NpcSpec**：race/class/voice/combatStyle/aiData/perk/essential-protected 都已涵蓋。
- **RelationshipSpec**：ModForge 已有 Parent/Child/Rank（`Spec.Actors.cs`），對應 Sofia 的 3 個 RELA（隨從對玩家固定 Ally）。
- **uniqueActor alias fill**：Sofia 的 comment quest 用 `uniqueActor -> Skyrim.esm:NPC` 指向 vanilla NPC，對應 ModForge 的 `uniqueActor:<ref>` alias fill。

### Sofia 用了、ModForge 目前沒有的
1. **MCM 設定選單（SkyUI）**：`JJSofiaMCM`（SofiaMCMscript 26 prop）+ `JJSofiaGetHasSKSE` 降級偵測。ModForge 無 MCM 生成；隨從類 mod 的「使用者可調設定」幾乎都靠 MCM，這是最大缺口。要做需生成 MCM Papyrus + config schema + SKSE 探測降級。
2. **DialogView record**：CK 編輯用的對話視圖聚合（9 個）。ModForge 直接生 quest/branch/topic，不產 DLVW；對 in-game 無影響，但若要讓產物在 CK 裡可維護，缺這層。
3. **多 actor 對拍 scene**：婚禮 scene（3 actor / 20 phase，Dialog+Package 交錯）。ModForge SceneSpec 目前以單/少 actor 為主，需確認多 alias actor + phase>action（純等待 phase）的支援程度。
4. **批次 per-NPC comment 生成**：Sofia 手刻 8 組同構 comment（quest+scene+alias+對白）。ModForge 缺「給一份模板 + 一張目標 NPC 清單 → 批次展開 N 組 quest/scene」的生成器。這是把 Sofia 模式自動化的明確機會。
5. **戰鬥風格 runtime 切換矩陣**：FormList（CombatStyle 集合）+ GLOB index + 一大群成對 CombatOverride package。ModForge 有 PACK templates 但無「FormList + 切換 index」這種 runtime 多態 package 的高階抽象。
6. **VoiceType 自訂 + voice asset 管線**：Sofia 自訂 4 個 VoiceType 並在 BSA 帶 .fuz。ModForge 的 voice-gen interface 仍是 deferred plan（見 MEMORY voice-gen-interface-future）。
7. **救援用的 quest 粒度約定**：Sofia 刻意把功能拆成可單獨 stopquest 的 quest。ModForge QuestSpec 可生多 quest，但沒有「為 runtime 排錯而拆分」這個設計指引。

### 務實結論
Sofia 證明「不掛 JContainers，純用 GLOB + quest stage + script property」足以撐起一個成熟單體隨從——這對 ModForge 是好消息：**預設不需要 native 依賴**就能生成像樣的隨從。JContainers 的 per-actor 狀態表只在「多隨從 / 每 NPC 各自狀態」時才必要（見 `jcontainers.md` 與 `others/modforge-relevance.md`）。ModForge 若要瞄準隨從這個品類，**優先補的是 MCM 生成與批次 per-NPC comment 展開**，而非資料結構持久化。
