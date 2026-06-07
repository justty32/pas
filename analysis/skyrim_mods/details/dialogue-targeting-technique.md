# 大規模對話如何精準投放：RDO 的 condition 投放技術

> 素材：`Relationship Dialogue Overhaul.esp` 完整 dump，`/tmp/mfdump/rdo.txt`（59418 行，9765 record）。
> 本文聚焦單一技術細節——**condition 串如何把一句台詞投到正確的 NPC 嘴裡**——比 architecture/ 的 RDO 總論更技術。

## 0. 核心矛盾

Skyrim 全境有上萬個 NPC，而 RDO 只有**一份 ESP**。它沒有、也不可能為每個 NPC 各寫一份台詞。它要解決三件事：

1. **精準**：一句台詞只出現在「該說它的 NPC」嘴裡。
2. **不重複**：同一個 NPC 不會每次都講同一句。
3. **動態**：台詞語氣隨「NPC 與玩家的關係」變化。

答案全在每一筆 `DialogResponses`（INFO record）後面掛的那一串 **condition function**。condition 是一組布林判斷，**全部為真**這句台詞才有資格被選中。本質上 RDO 不是「指定 NPC」，而是**描述一組篩選條件**，讓引擎在執行期把符合的 NPC 撈出來。

dump 中 RDO 自製的 `DialogResponses` 有 **6650 筆**（`grep -c 'Relationship Dialogue Overhaul.esp] DialogResponses'`），覆寫 vanilla 的另有 1268 筆——靠的全是這套 condition 篩選機制，而非逐一指名。

## 1. condition 頻率全景

`grep -oE 'condition: [A-Za-z]+' /tmp/mfdump/rdo.txt | sort | uniq -c | sort -rn | head -25`：

| 次數 | condition function | 投放維度 |
|------|--------------------|----------|
| 9245 | GetIsVoiceType | 身份（嗓音類別）|
| 7224 | GetInFaction | 身份（陣營）|
| 3112 | GetRandomPercent | 隨機不重複 |
| 2142 | GetPlayerTeammate | 關係（是否現役隨從）|
| 1811 | GetActorValue | 關係 / 屬性（disposition、技能等）|
| 1683 | GetRelationshipRank | 關係（關係等級）|
| 1476 | GetVMQuestVariable | 狀態機（quest 變數輪替）|
| 1396 | GetIsID | 身份（指名單一 NPC）|
| 1384 | LocationHasKeyword | 情境（地點分類）|
| 936 | IsInList | 身份（FormList 成員）|
| 923 | ConditionGlobal | 開關（全域變數旗標）|
| 817 | GetSleeping | 情境（NPC 是否在睡）|
| 815 | IsSneaking | 情境（玩家潛行）|
| 748 | GetInCurrentLoc | 情境（當前 location）|
| 605 | GetInWorldspace | 情境（worldspace）|
| 446 | GetIsRace | 身份（種族）|
| 389 | GetInCell | 情境（cell）|
| 377 | IsInCombat | 情境（戰鬥中）|
| 369 | IsInDialogueWithPlayer | 情境（正在與玩家對話）|
| 363 | GetStageDone | 狀態機（quest 階段）|
| 342 | GetIsPlayableRace | 身份（可玩種族）|
| 298 | HasKeyword | 身份（關鍵字）|
| 291 | GetGlobalValue | 開關 |
| 283 | GetActorValuePercent | 關係 / 屬性（百分比，如血量）|
| 253 | GetStage | 狀態機 |

> 一個值得注意的限制：本 dump 只對 `GetIsID` / `GetInFaction` 等「指向某 record」的 condition 印出 `-> FormID`（例：`condition: GetIsIDConditionData -> 000007:Skyrim.esm` 指 PlayerRef）。`GetRelationshipRank`、`GetRandomPercent` 等的**比較運算子與數值**未在此 dump 格式中列出，本文對其閾值的描述為依據 CK 慣例與台詞語意的合理推斷，並已標明。

最關鍵的一個對比：**GetIsVoiceType（9245）vs GetIsID（1396）**。RDO 壓倒性地偏好「按嗓音類別投放」，指名單一 NPC 只佔約六分之一——這就是「一份 ESP 覆蓋上萬 NPC」的根本手法。

## 2. 四大投放維度

### 2.1 誰能說（身份過濾）

身份過濾決定「**這句話有資格從誰嘴裡發出**」。RDO 的規模化核心是 `GetIsVoiceType`：Skyrim 的每個 NPC 都被指派一個 VoiceType（如 `FemaleNord`、`MaleBrute`），數以萬計的 NPC 共用區區數十個 VoiceType。對 VoiceType 投放，等於一次命中所有共用該嗓音的 NPC——而且**已配好同一套語音檔**，不需額外配音。

證據——RDO 的 quest 命名直接揭露此架構。`grep -oE 'quest=aa_RDO[A-Za-z]+'` 得到的 44 個 quest 幾乎全是「`<性別><嗓音>NonHate`」一一對應一個 VoiceType：

```
quest=aa_RDOFemaleNordNonHate
quest=aa_RDOMaleBruteNonHate
quest=aa_RDOFemaleSultryNonHate
quest=aa_RDOMaleCommonerAccentedNonHate
... （共 800 筆 INFO 掛在 *NonHate quest 下；後綴統計：NonHate 800、其餘僅 ThievesGuildUniqueVoices）
```

也就是說，RDO 把台詞庫**先按 VoiceType 切成數十桶**，每桶是一個 quest；桶內每筆 INFO 再用 `GetIsVoiceType` 條件鎖死該嗓音。topic 名同樣編碼了嗓音，例如 `521050` 所屬 topic 為 `MYoungEagerNonHateGoodbye`（`[07A3C1] DialogTopic MYoungEagerNonHateGoodbye`，行 48970）。

其他身份維度由細到粗：

- **GetInFaction（7224）**：投給某陣營全員。常與 VoiceType 疊用做交集（嗓音 ∩ 陣營）。
- **GetIsRace（446）/ GetPCIsRace（玩家種族）**：種族判定。vanilla 的種族自報 INFO `[043AD9] DialogResponses`（行 911，response "Khajiit."）就疊了 `GetPCIsRace ×2 + GetIsSex + GetIsRace ×2 + GetIsVoiceType ×3` 來精確鎖定。
- **IsInList（936）**：以 FormList 列舉一組 record（NPC 群、地點群），是「半指名」。
- **GetIsID（1396）**：指名到底，鎖死單一 actor。例：`condition: GetIsIDConditionData -> 000007:Skyrim.esm`（PlayerRef，出現 271 次，多用來判斷對話另一方是玩家）、`-> 002B6C:Dawnguard.esm`（Serana，127 次，見 §3）。RDO 只在「這句話確實只屬於某個唯一 NPC」時才用它。

### 2.2 關係狀態（動態化）—— mod 名的由來

這是 RDO 區別於普通對話 mod 的招牌。同一個 NPC，隨著與玩家的關係改變，會講出語氣不同的台詞。

- **GetRelationshipRank（1683）**：讀取 NPC 對玩家的關係等級（CK 中 -4 Archnemesis … 0 Acquaintance … +4 Lover）。RDO 用它把同一情境（如 Hello）的台詞分成「敵意 / 中性 / 友好 / 摯愛」幾組，每組掛不同的 rank 閾值。quest 名的 `NonHate` 後綴正是第一層粗篩——「關係沒到 Hate 才進這桶」，桶內再用 GetRelationshipRank 細分。
- **GetPlayerTeammate（2142）**：判斷該 NPC 此刻是否為現役隨從。隨從專屬的旅途閒聊全靠它，例如 §3 的 Serana 台詞。
- **GetActorValue（1811）/ GetActorValuePercent（283）**：讀任意 actor value，可查 disposition（好感度）、技能、或血量百分比（戰鬥中受傷台詞）。

範例——一筆關係化的 Goodbye（`[521050] DialogResponses`，行 49009，topic `MYoungEagerNonHateGoodbye`）：

```
[521050:Relationship Dialogue Overhaul.esp] DialogResponses
    response[1] (Happy): "Oh, goodbye then."
    condition: GetIsVoiceTypeConditionData      ← 嗓音 = MaleYoungEager
    condition: GetRandomPercentConditionData     ← 擲骰（不重複）
    condition: GetRelationshipRankConditionData  ← 關係達到某友好門檻
    condition: GetInFactionConditionData         ← 三個陣營交集進一步收窄
    condition: GetInFactionConditionData
    condition: GetInFactionConditionData
```

emotion 標 `(Happy)` 配上 GetRelationshipRank：友好門檻沒到的玩家，會落到同 topic 下另一組（emotion 與台詞皆不同）的 INFO。

### 2.3 情境（脈絡）

決定「**現在這個當下適不適合講**」。分兩類：

**NPC / 地點脈絡**
- `LocationHasKeyword`（1384）/ `GetInCurrentLoc`（748）/ `GetInWorldspace`（605）/ `GetInCell`（389）：把台詞綁到地點。LocationHasKeyword 最常用，因為它對「一類地點」（城市、酒館、地城）投放而非單一地點，延續了 RDO「按類投放」的一貫思路。
- `GetSleeping`（817）：NPC 在睡覺時通常不該被搭話，或反而有專屬「半夢半醒」台詞。

**玩家當下狀態**
- `IsSneaking`（815）：玩家潛行時 NPC 的反應。
- `IsInCombat`（377）：戰鬥語境的 taunt / hit 台詞。
- `IsInDialogueWithPlayer`（369）：確保是面對面對話而非旁白觸發。

範例——一筆把睡眠 / 潛行 / 地點 / 陣營全疊起來的 Idle 評論（vanilla `HirelingIdles` topic 被 RDO 覆寫並加掛腳本，`[0284F7] DialogResponses`，行 4250；topic `[055DEB] DialogTopic HirelingIdles`，category=Misc subtype=Idle，行 4248）：

```
[0284F7:Skyrim.esm] DialogResponses
    script: RDO_ThisQuestSetStageTIF [2 prop(s)]
    response[1] (Happy): "The College of Winterhold is an amazing sight. I've never set foot on the grounds, but always wanted to."
    condition: ConditionGlobalBinaryOverlay     ← 全域開關（功能是否啟用）
    condition: GetVMQuestVariableConditionData    ← 輪替用 quest 變數
    condition: GetIsIDConditionData -> 02427D:Skyrim.esm  ← 指名某隨從
    condition: GetActorValueConditionData
    condition: GetInFactionConditionData
    condition: GetSleepingConditionData           ← NPC 不在睡
    condition: IsSneakingConditionData            ← 玩家不在潛行
    condition: IsInListConditionData
    condition: GetQuestRunningConditionData (×3)
    condition: GetStageDoneConditionData
    condition: GetInWorldspaceConditionData       ← 限定在某 worldspace
    condition: GetInCurrentLocConditionData       ← 限定在某 location（學院）
```

台詞內容（提到 College of Winterhold）與 `GetInWorldspace + GetInCurrentLoc` 嚴格對應——**這句話只在 NPC 人在學院、清醒、玩家沒潛行時才會冒出來**。

### 2.4 隨機不重複

`GetRandomPercent` 出現 **3112 次**，是排名第三的 condition——幾乎每一句 Hello / Goodbye / Idle 評論都掛它。機制：condition 取一個 0–99 的隨機數，與閾值比較（如 `GetRandomPercent <= 25`），只有擲骰命中才放行。

效果：當一群符合身份 + 情境的 INFO 同時「合格」，引擎不會固定挑第一條，而是讓每條各自擲骰，命中者中再挑——於是同一個 NPC 反覆觸發 Hello 時，會在好幾句之間自然輪替，不會每次都同一句。

它常與兩類同伴搭配：
- **GetVMQuestVariable（1476）/ GetStageDone（363）**：quest 變數做「狀態輪替」——講過 A 句就把變數推進，下次只剩 B、C 句合格，做出「不重複且有序」的對話。
- **`a_RDO_<voicetype>NextComment` 全域 float 冷卻計時器**（dump 開頭即列出 20 個，如 `[047683] GlobalFloat a_RDO_FNORDNextComment`、`[04768A] GlobalFloat a_RDO_MDRNKNextComment`，行 6 起）：每個 VoiceType 一個計時器，配 `ConditionGlobal` 判斷「距上次評論是否已過冷卻」，避免同嗓音 NPC 連珠炮刷屏。

擲骰（每句機率）+ quest 變數（有序輪替）+ 冷卻全域（節流）三者疊加，構成 RDO 的「不重複」層。

## 3. 一個完整 INFO 的解剖

挑 Serana（Dawnguard 唯一隨從）的隨從旅途閒聊。topic `[07F4D6] DialogTopic SeranaNonHateHello`（category=Misc subtype=Hello，quest=`aa_RDODLC1SeranaNonHate`，行 50326）。

```
[20AA1D:Relationship Dialogue Overhaul.esp] DialogResponses
    response[1] (Happy): "So where are we off to, now?"
    condition: GetIsVoiceTypeConditionData          (1)
    condition: IsInDialogueWithPlayerConditionData  (2)
    condition: GetVMQuestVariableConditionData       (3)
    condition: GetPlayerTeammateConditionData        (4)
    condition: GetVMQuestVariableConditionData       (5)
    condition: GetRelationshipRankConditionData      (6)
    condition: GetStageDoneConditionData             (7)
    condition: GetInWorldspaceConditionData          (8)
    condition: GetInWorldspaceConditionData          (9)
    condition: LocationHasKeywordConditionData       (10–16，共 7 個)
```

逐行翻成白話（運算子 / 數值依語意推斷，dump 未印出）：

| # | condition | 白話 |
|---|-----------|------|
| 1 | GetIsVoiceType | 說話者必須是 Serana 的嗓音（FemaleYoungEager 系）|
| 2 | IsInDialogueWithPlayer | 此刻正面對玩家（是搭話而非背景旁白）|
| 3 | GetVMQuestVariable | RDO 對話狀態機變數允許此句（輪替閘）|
| 4 | GetPlayerTeammate | Serana 必須是**現役隨從**——非隨從時整句失格 |
| 5 | GetVMQuestVariable | 第二個狀態變數（多軸輪替）|
| 6 | GetRelationshipRank | 關係達到友好門檻（呼應 emotion `Happy` 與 NonHate）|
| 7 | GetStageDone | 某前置劇情階段已完成 |
| 8–9 | GetInWorldspace ×2 | 限定在某些 worldspace（戶外旅途語境，OR 關係）|
| 10–16 | LocationHasKeyword ×7 | 當前地點需帶某類 keyword（多個做地點分類交集 / 並集）|

**綜合語意**：這句「So where are we off to, now?」只會在——*說話者是 Serana 嗓音、她是我現役隨從、與我關係夠好、相關劇情已推進、我們正在某些戶外地點面對面、且輪替變數與擲骰都放行* ——時才從她嘴裡冒出。把任一條件去掉，這句台詞就會洩漏到不該說它的場合或 NPC。

同 topic 下的 `[20AA19]`（"I'm glad you're here with me."）、`[20AA1A]`（"Just you and me against the world, now."）共用前 7 條身份 / 關係 / 狀態條件，僅在後段地點條件上分流——這正是「同一桶台詞靠 condition 尾段做最後分配」的縮影。

## 4. DialogBranch / DialogTopic 的角色

condition 掛在 **`DialogResponses`（INFO）這一層**——精準投放的全部邏輯都在這裡。上層兩級只是**分類容器**：

- **DialogTopic**：一組 INFO 的歸類。它帶 `category`（Combat / Detection / Misc / Topic）、`subtype`（Hello / Goodbye / Idle / Attack / Hit …）、所屬 `quest`、與可選 `branch`。subtype 決定**引擎在什麼時機輪詢這組 INFO**（玩家靠近 → Hello；離開 → Goodbye；閒置 → Idle）。dump 中 `category / subtype` 分布（`grep -oE 'category=... subtype=...'`）前段為：Topic/Custom 153、Misc/Hello 106、Misc/Idle 76、Misc/Goodbye 71、Detection/NormalToCombat 56、Combat/Taunt 55……
- **DialogBranch**：對 player-initiated 對話樹做更細的分支管理。RDO 的 INFO 絕大多數 `branch=<null>`（1179 筆無 branch），少數劇情對話才用具名 branch（如 `RDOKaieQuestGreet`、`RDOFriendConversationStart`）。

換句話說：**topic/branch 回答「這是什麼類型、何時輪詢」；condition 回答「在合格候選裡，到底投給誰、現在能不能講」。** topic 的 subtype 把搜尋空間先縮到「此刻該類事件的 INFO」，condition 再在其中做最終的 NPC / 情境 / 隨機篩選。

## 5. 可複製的配方（供 ModForge 參考）

把上面歸納成「程式化生成一句規模化台詞」要產出的 condition 範本。要訣是**從寬到窄分層**，每層各管一個投放維度：

**最小規模化配方（一句通用 Hello）**

| 層 | condition | 設定 | 作用 |
|----|-----------|------|------|
| 身份（必填）| `GetIsVoiceType == <某 VoiceType>` | 選一個目標嗓音 | 一次命中所有共用該嗓音、已有配音的 NPC |
| 關係（動態）| `GetRelationshipRank >= <N>` | N=1 友好 / 3 摯友 | 同句的不同關係版本各設不同 N |
| 隨機（防重複）| `GetRandomPercent <= <P>` | P=20~30 | 多句同層時各自擲骰輪替 |

即：`GetIsVoiceType == FemaleNord  AND  GetRelationshipRank >= 1  AND  GetRandomPercent <= 25`。

**收窄到特定族群 / 情境（疊加，AND 交集）**

- 加 `GetInFaction == <faction>`：限該陣營（嗓音 ∩ 陣營）。
- 加 `GetPlayerTeammate == 1`：限現役隨從（旅途閒聊必加）。
- 加 `LocationHasKeyword == <locKeyword>` 或 `GetInCurrentLoc == <loc>`：綁地點類別。
- 加 `IsInCombat == 0` / `GetSleeping == 0` / `IsSneaking == 0`：排除不合時宜的場合。

**指名單一 NPC（放棄規模化時）**

- 用 `GetIsID == <actor FormID>` 取代 `GetIsVoiceType`，其餘層照舊。只在「這句確實獨屬某 NPC」時用。

**節流 / 輪替（進階，可選）**

- 配一個 per-voicetype 全域 float 計時器 + `GetGlobalValue` 比較，做冷卻防刷屏（對應 RDO 的 `a_RDO_*NextComment`）。
- 配 quest 變數 + `GetVMQuestVariable` / `GetStageDone`，把多句做成有序、不回頭的輪替序列。

**鐵律**：condition 是 AND 交集，且必須**全部命中**才放行；漏掉任一個收窄條件，台詞就會洩漏到錯誤的 NPC 或場合（如忘記 `GetPlayerTeammate` 會讓隨從專屬台詞跑到路人嘴裡）。把容器（topic subtype）選對來框定觸發時機，再用 condition 串逐層收窄——這就是「一份 ESP 精準餵養上萬 NPC」的全部祕密。

---

### 取證索引（dump 行號 / FormID）

- condition 頻率：`grep -oE 'condition: [A-Za-z]+' /tmp/mfdump/rdo.txt | sort | uniq -c | sort -rn`
- 解剖 INFO：`[20AA1D:Relationship Dialogue Overhaul.esp] DialogResponses`（行 50523），topic `[07F4D6] DialogTopic SeranaNonHateHello`（行 50326）
- 關係維度：`[521050:Relationship Dialogue Overhaul.esp] DialogResponses`（行 49009），topic `[07A3C1] DialogTopic MYoungEagerNonHateGoodbye`（行 48970）
- 情境維度：`[0284F7:Skyrim.esm] DialogResponses`（行 4250），topic `[055DEB] DialogTopic HirelingIdles`（行 4248）
- 身份 / 種族：`[043AD9:Skyrim.esm] DialogResponses` "Khajiit."（行 911）
- 冷卻全域：`[047683] GlobalFloat a_RDO_FNORDNextComment` 等（dump 行 6 起）
- quest 桶：`grep -oE 'quest=aa_RDO[A-Za-z]+' /tmp/mfdump/rdo.txt | sort -u`（44 個，幾乎全為 `<嗓音>NonHate`）
