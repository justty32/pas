# Relationship Dialogue Overhaul (RDO Final, v1187)

## 定位

對話 overhaul，不是「新增劇情」mod。它的核心命題是：**接管 vanilla 既有的對話框架（quest / topic / scene / Story Manager 節點），把海量新台詞用「條件」投放進去**，讓全 Skyrim 的隨從、配偶、市民、商人在既有情境下講出更豐富、隨關係/隨從狀態變化的話。

判別依據（用 ESP dump 統計）：插件共 **9765 records**，其中 **8153 是 RDO 新增、1612 是 vanilla override**。但「新增」的 8153 records 絕大多數是 `DialogResponses`（INFO，6650 條）與 `DialogTopic`（1151 條）——也就是台詞與話題容器本身；真正改變遊戲對話「流向」的，是那 51 個被整個覆寫的 vanilla `Quest`、31 個覆寫的 `Scene` 與 4 個覆寫的 Story Manager 節點。RDO 把新台詞掛到既有 quest 底下，再靠每句台詞上的 condition 決定誰、何時、以多大機率聽到。

對照本目錄既有的 JContainers（純 library、零遊戲內容），RDO 是另一個極端：幾乎沒有「機制」，全是「內容 + 投放規則」。它示範的不是程式技巧，而是**規模化對話的資料工程**。

來源：
- mod 目錄 `~/skyrim_mods/Relationship Dialogue Overhaul - RDO Final-1187-Final/`（ESP 3 MB + BSA 116 MB）。
- BSA 116 MB 幾乎全是語音 `.fuz`（無工具解包，本檔不分析語音）。
- ESP 完整 dump：`/tmp/mfdump/rdo.txt`（59418 行，9765 records）。
- masters = `[Skyrim.esm, Update.esm, Dawnguard.esm, HearthFires.esm, Dragonborn.esm]`（dump 第 1 行）。

## 檔案結構

| 部分 | 內容 | 大小 |
|---|---|---|
| `Relationship Dialogue Overhaul.esp` | 全部邏輯：9765 records | 3 MB |
| BSA（語音 archive） | 對應台詞的 `.fuz`（語音 + lip sync）；無 loose 工具解包 | 116 MB |

ESP 即全部可分析素材。每一句 RDO 新台詞理論上對應 BSA 裡一個 `.fuz`——這也是為什麼台詞量（6650 新 INFO）撐起 116 MB 語音。

## record 解剖

### 全體 record 分佈（按來源 plugin 切）

判別法：dump 中每個 record header 形如 `[FormID:plugin名] Type EditorID`。**FormID 高位（plugin index）決定該 record 的「歸屬」**——`:Relationship Dialogue Overhaul.esp]` 是 RDO 自己新增的 record；`:Skyrim.esm]`（或 `:Dragonborn.esm` 等）是 RDO **override 既有 vanilla record**（同一 FormID、被 RDO 的版本覆蓋）。

| Type | vanilla override | RDO 新增 | 小計 |
|---|---:|---:|---:|
| DialogResponses (INFO) | 1304 | 6650 | 7954 |
| DialogTopic | 181 | 1151 | 1332 |
| Quest | 51 | 101 | 152 |
| Package | 20 | 54 | 74 |
| DialogBranch | 2 | 42 | 44 |
| Scene | 31 | 3 | 34 |
| GlobalFloat | 0 | 21 | 21 |
| PlacedNpc | 10 | 8 | 18 |
| FormList | 0 | 18 | 18 |
| Npc | 0 | 17 | 17 |
| Spell | 0 | 15 | 15 |
| MagicEffect | 1 | 13 | 14 |
| PlacedObject | 0 | 12 | 12 |
| Book | 0 | 10 | 10 |
| Cell | 7 | 1 | 8 |
| StoryManagerQuestNode | 4 | 3 | 7 |
| Relationship | 0 | 6 | 6 |
| Class | 0 | 5 | 5 |
| StoryManagerBranchNode | 0 | 3 | 3 |
| CombatStyle | 0 | 3 | 3 |
| GlobalShort | 1 | 2 | 3 |
| Weapon | 0 | 2 | 2 |
| Outfit | 0 | 2 | 2 |
| Faction | 0 | 2 | 2 |
| Armor / Perk / ObjectEffect / MiscItem / Message / LeveledNpc / Container | 0 | 各 1~3 | — |
| **總計** | **1612** | **8153** | **9765** |

來源命令：`grep -E '^  \[[0-9A-F]{6}:[^]]+\] ' /tmp/mfdump/rdo.txt`（2 空格縮排 = 頂層 record header，恰好 9765 行），再按 plugin 與 Type 拆。

### override vs 新增：FormID 判別法（具體例證）

**override 既有 vanilla record**（FormID 屬 Skyrim.esm，被 RDO 整個覆寫，把新 INFO 塞進去）：

- `[04C49D:Skyrim.esm] Quest FollowerCommentary01 "Entrances to Dungeons"`
- `[04C6EB:Skyrim.esm] Quest FollowerCommentary02 "Follower sees an impressive view"`
- `[0367DD:Skyrim.esm] Quest DialogueSolitudeErikurScene1 "Erikur House Scene 1"`
- `[016FA6:Skyrim.esm] Quest DialogueGenericSceneSpecial01`
- `[096500:Skyrim.esm] DialogResponses`（戰鬥嘲諷 INFO，RDO 加入新 response「It's... nothing...」+ 三條 condition）

**RDO 新增 record**（FormID 屬 RDO 自己的 plugin index，EditorID 多帶 `RDO`/`a_RDO`/`_…RDO` 前綴）：

- `[FCF905:Relationship Dialogue Overhaul.esp] StoryManagerBranchNode RDOHaafingarHoldScenes`
- `[CE2329:Relationship Dialogue Overhaul.esp] Npc _KaieRDO "Kaie"`
- `[04767F:Relationship Dialogue Overhaul.esp] GlobalFloat a_RDO_FCMDNextComment`

一句話：**看 `:` 後面的 plugin 名**。屬 `Skyrim.esm`/DLC = override vanilla；屬 `Relationship Dialogue Overhaul.esp` = RDO 原創。

### 一個 vanilla DialogResponses override 的解剖

`/tmp/mfdump/rdo.txt` 的戰鬥嘲諷話題 `[013EE3:Skyrim.esm] DialogTopic`（category=Combat / subtype=Attack）底下，RDO 覆寫的 INFO：

```
[04949B:Skyrim.esm] DialogResponses
    response[1] (Anger): "For Skyrim!"
    condition: GetRandomPercentConditionData
    condition: GetIsIDConditionData -> 000007:Skyrim.esm
    condition: GetIsVoiceTypeConditionData
    condition: HasKeywordConditionData
    condition: GetInFactionConditionData
    condition: GetInCurrentLocConditionData
    condition: GetIsEditorLocationConditionData
```

讀法：這是 vanilla 戰鬥喊話 INFO（FormID 屬 Skyrim.esm），RDO 把新 response 與一整串 condition 灌進去。`GetIsID -> 000007:Skyrim.esm` 是玩家（vanilla Player FormID 0x7）。`GetIsVoiceType` + `GetInFaction` 把這句限定到某一「類」NPC，`GetRandomPercent` 讓它只在一定機率下觸發。**這正是 RDO 的縮影：覆寫 vanilla 容器，內容靠條件投放。**

## override 策略

### 1. 海量 condition 投放（mod 的靈魂）

對 dump 全體 condition 跑頻率（`grep -oE 'condition: [A-Za-z]+' … | sort | uniq -c | sort -rn`）：

| 次數 | condition function | 投放用途 |
|---:|---|---|
| 9245 | GetIsVoiceType | **把台詞限定到一個語音類型**（= 一整類 NPC，如 MaleNord、FemaleEvenToned），不逐一指名 |
| 7224 | GetInFaction | **把台詞限定到一個陣營**（如隨從陣營、城衛兵、商人）——「一類人」的另一把刷子 |
| 3112 | GetRandomPercent | 隨機門檻，避免同一句反覆觸發、製造變化 |
| 2142 | GetPlayerTeammate | 是否為玩家隨從——隨「隨從狀態」切換台詞 |
| 1811 | GetActorValue | AV 門檻（信心、戰鬥狀態等） |
| 1683 | GetRelationshipRank | **隨與玩家的關係等級變化**——mod 名所指的核心軸 |
| 1476 | GetVMQuestVariable | 讀 quest 腳本變數（追蹤對話冷卻、進度） |
| 1396 | GetIsID | 指名特定 actor（如玩家 0x7、或 RDO 自家 NPC） |
| 1384 | LocationHasKeyword | 地點類型（城市/旅店/地城）門檻 |
| 936 | IsInList | **目標在某 FormList 內**——配合 RDO 的 `aaa_RDOVoices*` 名單批次投放 |
| 923 | ConditionGlobal（GlobalVariable 開關） | 全域旗標（功能模組開/關） |
| 817 | GetSleeping / 815 IsSneaking / 748 GetInCurrentLoc / 605 GetInWorldspace … | 情境細分 |

**分佈的解讀**：前兩名 `GetIsVoiceType`(9245) + `GetInFaction`(7224) 壓倒性領先，直接證明 RDO 的投放單位是**「類」而非「個」**——一句通用台詞用「語音類型 + 陣營」就能覆蓋成百上千個 NPC，無需逐一掛到每個 actor。再疊上 `GetRelationshipRank`(1683) + `GetPlayerTeammate`(2142)，讓同一情境下台詞隨「玩家與你的關係 / 你是不是隨從」分流。最後 `GetRandomPercent`(3112) 在每一束候選台詞上做隨機抽選，避免重複。三層疊起來就是：**用條件把有限的台詞素材，組合投放成「看起來無限」的對話覆蓋面**。

（投放手法的逐句細節版另見 `details/dialogue-targeting-technique.md`，本檔只點到原則。）

### 2. FormList 作為投放名單

RDO 新增 18 個 FormList，命名即用途，是 `IsInList`(936) 的彈藥：

- `aaa_RDOVoicesAll` / `aaa_RDOVoicesMaleList` / `aaa_RDOVoicesFemaleList`——全部 / 男 / 女語音類型集合
- `aaa_RDOVoicesFollowerAll` / `aaa_RDOVoicesMarriageAll`——隨從 / 配偶語音集合
- `_RDOVoicesFollowerAllPlusUniques`、`a_RDOVoicesFollowerGenericResponses`——隨從專用回應名單
- `aaa_RDOPreventedActorsList` / `…HatePL` / `…Friend`——**排除名單**（不該被投放的 actor，避免覆蓋到劇情關鍵或不合適的 NPC）

把「哪些語音 / 哪些 actor 屬於這一類」抽成 FormList，再以 `IsInList` 一次性套用到大量 INFO——這是 RDO 把投放規則**集中管理**的手段（改一個 list，所有引用它的台詞投放面同步變動）。

### 3. 嫁接進 vanilla Story Manager 樹

Story Manager 是 Skyrim 觸發「環境 scene 對話」的事件樹。RDO 同時 **override vanilla 節點** 與 **新增自己的節點**：

**7 個 StoryManagerQuestNode**（4 override + 3 新）：

| FormID:plugin | EditorID | 性質 |
|---|---|---|
| `016FA1:Skyrim.esm` | GenericScenesSpecial | override vanilla |
| `03524A:Skyrim.esm` | SolitudeWinkingSkeeverScenes | override vanilla |
| `046E1A:Skyrim.esm` | PawnedPrawnConversations | override vanilla |
| `071227:Skyrim.esm` | RiftenBeggarConversations | override vanilla |
| `D0093A:Relationship Dialogue Overhaul.esp` | a_RDOKaieConfrontQuestNode | RDO 新增 |
| `FC05F2:Relationship Dialogue Overhaul.esp` | a_RDOAssaultActorNode | RDO 新增 |
| `FCF908:Relationship Dialogue Overhaul.esp` | RDOSolitudeMarketplaceScenes | RDO 新增 |

**3 個 StoryManagerBranchNode**（全部 RDO 新增）：

- `FCF905:Relationship Dialogue Overhaul.esp` RDOHaafingarHoldScenes
- `FCF906:Relationship Dialogue Overhaul.esp` RDOSolitudeScenes
- `FCF907:Relationship Dialogue Overhaul.esp` RDOSolitudeMarketScenes

手法：override `GenericScenesSpecial` / `SolitudeWinkingSkeeverScenes` 等既有節點，等於把新的環境對話 scene 掛到 vanilla 已在跑的事件流上（沿用引擎已配置好的觸發條件）；同時新增 `RDOHaafingar…` / `RDOSolitudeMarket…` 等自家 branch/quest 節點，承載 RDO 原創的城市 marketplace scene。**override 既有節點 = 蹭 vanilla 的觸發；新增節點 = 擴充新觸發點。**

### 4. Scene / Package / 新 NPC

- **Scene（34）**：31 override + 3 新。override 的多是 `DialogueSolitude…` / `DialogueRiften…` 等 vanilla 城市閒聊 scene（RDO 替換對白內容）；3 個新 scene 服務 RDO 原創角色劇情。
- **Package（74）**：54 新 + 20 override。AI package 支撐新 NPC 的行為（走位、值守），以及讓既有 NPC 配合新 scene 的動作。
- **17 個新 Npc**：兩類。其一是 RDO 原創的具名對話角色（帶完整關係檔）——`_KaieRDO "Kaie"`、`_SarynRDO "Saryn"`、`_RazitaRDO "Razita"`、`_LorionRDO "Lorion"`、`_DunoreRDO "Dunore"`、`_NubareeRDO "Nubaree"`，每個都配一條 `Relationship` record（`_KaiePlayerRelationshipRDO` 等 6 條）定義其與玩家的初始關係。其二是 encounter/leveled 用的泛型角色（`_RDOEncOrcHunter0xF`、`_RDOEncHunterNordM`、`_WEAdventurerSpellSword…`）。
- **6 個 Relationship record**：全部是上述 6 名 RDO 原創 NPC 對「玩家」的關係定義——這是 mod 名「Relationship」的字面落點，但量極小（6 條），相對於 1683 次 `GetRelationshipRank` 條件，可見**關係系統主要靠「讀 vanilla 既有關係」來分流台詞，而非自己定義大量新關係**。
- 另有少量道具支援原創角色：`_RDOKaieSwordAbsorbHealth "Kaie's Sword of Leeching"`、一批 `a_RDO*` Spell（Fireball/IceStorm/ConjureGargoyleSentinel 等，給 NPC 施法用）、若干 Book（吟遊詩人新詩節 `a_RDOBardEddaVerse*`）。

## 對 ModForge 的意義

ModForge 目前的 dialogue/quest builder 是**「新增導向」**：它能做 storyEvent 掛 SM、scene phase → dialog、AI package、以及一組 condition（見 ModForge CLAUDE.md「已落地功能」與 `src/ModForge.Core/Generator.Build.Conditions.cs`）。RDO 揭示了三個 ModForge **尚未涵蓋** 的能力，若要做「對話包」式內容缺一不可。務實列出差距：

### (a) override 既有 vanilla record 的能力 —— 完全沒有

ModForge 的 dialogue 路徑只把 condition 掛到**自己建的** INFO 上：`WireDialogueConditions()` 用 `dialogResponsesByEd.TryGetValue(d.EditorId, …)` 找的是 spec 內自建 record（`src/ModForge.Core/Generator.Build.Conditions.cs:128-159`）。沒有「取出某個 Skyrim.esm 既有 Quest / DialogTopic / INFO，覆寫它、往裡塞 response」的入口。而 RDO 的 1612 個 override（含 51 個 vanilla Quest、1304 個 vanilla INFO）正是靠此。Mutagen 本身支援 `GetOrAddAsOverride`（ModForge 已在 navmesh/exterior-cell 等 world 路徑用到 override），但 **dialogue/quest builder 沒有暴露這條路**。這是最大、也最根本的差距。

### (b) 以 condition 模板批次套用到「一類 NPC」 —— 沒有

ModForge 的 condition 是「逐句手寫」：spec 裡每個 dialogue 條目各自帶一個 `conditions[]` 陣列。RDO 的玩法是**一束台詞共用一組投放條件**（同一 VoiceType + Faction + RandomPercent），靠 FormList 集中管理目標集合。ModForge 沒有：
- FormList builder（RDO 的 18 個 `aaa_RDOVoices*` 名單機制）；
- 「把一組 condition 套用到 N 句台詞」的模板/批次語法。
要做對話包，需要一個「投放模板」抽象，而非逐句複製條件。

### (c) `GetIsVoiceType` / `IsInList` 這類 condition 的 spec 支援 —— 缺

ModForge 的 `SupportedConditionFunctions`（`Generator.Build.Conditions.cs:6-13`）目前涵蓋 `GetInFaction`、`GetRelationshipRank`、`GetRandomPercent`、`GetIsID`、`GetActorValue` 等——與 RDO 高頻條件有交集，但**關鍵的 `GetIsVoiceType`（RDO 第一名，9245 次）與 `IsInList`（936 次）都不在支援清單內**。沒有 `GetIsVoiceType`，就無法做「投到一整類語音的 NPC」這個 RDO 最核心的手法；沒有 `IsInList`，就無法配合 FormList 名單投放。`LocationHasKeyword`、`GetPlayerTeammate`、`GetVMQuestVariable` 也都缺。

### 小結（差距優先序）

| 缺口 | 對「做對話包」的阻塞程度 |
|---|---|
| override 既有 vanilla quest/topic/INFO | 致命——沒有它根本無法「接管 vanilla 對話」 |
| `GetIsVoiceType` + `IsInList` condition | 致命——RDO 規模化投放的兩支主刷子 |
| FormList builder | 高——投放名單的集中管理載體 |
| condition 批次/模板套用 | 高——否則逐句手寫無法規模化 |
| `GetPlayerTeammate` / `LocationHasKeyword` / `GetVMQuestVariable` | 中——投放維度的補強 |

不誇大：ModForge 現有的 condition framework 與 SM 掛載能力，已經是這條路的**地基**（BuildCondition 的 dispatch 架構加幾個 case 即可補上 VoiceType/IsInList）。真正缺的是「override 入口」與「批次投放」這兩個結構性能力——前者是 Mutagen API 已有、ModForge 未暴露；後者是純粹的 spec 設計工作。RDO 證明這條路可行且有明確的工程模式可抄，但它與 ModForge 當前「新增導向」的設計是兩種不同的內容生產範式。

→ 對照建議見 `others/modforge-relevance.md`。
