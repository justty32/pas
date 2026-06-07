# RDO 的 FormList 投放機制

> 素材：`Relationship Dialogue Overhaul.esp`。
> ESP 文字 dump 在 `/tmp/mfdump/rdo.txt`（59418 行）；但 ModForge 的 `dump` 指令對 FormList **只印出 EditorID 一行、不展開成員**（FLST 走的是 catch-all 渲染，見 dump 第 58953–58970 行），所以 FormList 成員型別、IsInList condition 的參數（指向哪個 FormList、比較值 0 還是 1）都是用一支臨時 Mutagen 程式（載入 `Skyrim.esm`/`Update.esm`/`Dawnguard.esm`/`HearthFires.esm`/`Dragonborn.esm` 五個 master 解析 master 端 FormKey）離線解碼取得，本文所列數字與成員名皆來自該解碼結果。
> 本文聚焦 **FormList 這個子機制**；對話投放的總論（condition 串如何把台詞投到正確 NPC）見 `dialogue-targeting-technique.md`，兩篇互補、可互相引用。

---

## 0. 一句話結論

RDO 的「FormList」與大家直覺想的不一樣：**18 個 FormList 裡，真正主導對話投放的不是 `aaa_RDOVoices*`（目標名單），而是一個排除名單 `aaa_RDOPreventedActorsList`**。936 次 `IsInList` 條件**全部**指向這一個 list，且 923 次是 `==0`（守門：不在黑名單才放行）。目標投放（「這句話該給誰」）幾乎全交給 `GetIsVoiceType`（9245 次）逐句直接鎖嗓音；Voices FormList 只在少數需要「一條 condition 涵蓋整組嗓音」時當捷徑用（210 次）。

---

## 1. FormList 全表（18 個，分群）

dump 第 58953–58970 行列出全部 18 個 FormList 的 `[FormID] EditorID`。下表的「成員型別 / 數量」來自離線解碼（dump 不展開成員）：

### A. 排除名單（PreventedActors，3 個）——投放的真正主力

| FormID | EditorID | 成員 | 說明 |
|--------|----------|------|------|
| `[01EE3A]` | `aaa_RDOPreventedActorsList` | **0 項（空）** | 全 936 次 `IsInList` 唯一指向的 list；ESP 出貨時是空的 |
| `[02E153]` | `aaa_RDOPreventedActorsHatePL` | **0 項（空）** | 在 dialogue/quest condition 中**零引用** |
| `[02E154]` | `aaa_RDOPreventedActorsFriend` | **0 項（空）** | 同上，零引用 |

三個排除名單**出貨時全為空**。`aaa_RDOPreventedActorsList` 被 condition 引用 936 次卻沒有靜態成員——這是刻意的「**空容器 + 執行期/補丁填充**」設計（見 §4）。

### B. 目標名單（Voices，10 個）——成員清一色 VoiceType

| FormID | EditorID | 成員型別×數量 |
|--------|----------|----------------|
| `[056995]` | `aaa_RDOVoicesFemaleList` | VoiceType × 18 |
| `[056996]` | `aaa_RDOVoicesMaleList` | VoiceType × 27 |
| `[11767B]` | `aaa_RDOVoicesMarriageAll` | VoiceType × 26 |
| `[11767C]` | `aaa_RDOVoicesFollowerAll` | VoiceType × 43 |
| `[223F67]` | `aaa_RDOVoicesAll` | VoiceType × 54 |
| `[35E1E6]` | `a_RDO_USKPVendorMiscVoices` | VoiceType × 15 |
| `[400398]` | `aaa_RDOVoicesUnique` | VoiceType × 9（具名 NPC 專屬嗓音）|
| `[A1D4C4]` | `a_RDOVoicesFollowerGenericResponses` | VoiceType × 14 |
| `[B8EEBF]` | `_RDO_OriginalVoicesFollowerAll` | VoiceType × 17 |
| `[CD811F]` | `_RDOVoicesFollowerAllPlusUniques` | VoiceType × 52 |

成員證據（`aaa_RDOVoicesFemaleList` 解碼，節選）：

```
-> VoiceType:FemaleCommoner (013ADE:Skyrim.esm)
-> VoiceType:FemaleEvenToned (013ADD:Skyrim.esm)
-> VoiceType:FemaleNord (013AE7:Skyrim.esm)
-> VoiceType:FemaleOrc (013AEB:Skyrim.esm)
-> VoiceType:FemaleSultry (013AE0:Skyrim.esm)
-> VoiceType:DLC2FemaleDarkElfCommoner (0247E5:Dragonborn.esm)   ← 含 DLC 嗓音
```

`aaa_RDOVoicesUnique` 全部是「具名主角」的專屬 VoiceType（不是泛用嗓音）：

```
-> VoiceType:FemaleUniqueKarliah (01B080:Skyrim.esm)
-> VoiceType:MaleUniqueBrynjolf  (01B07E:Skyrim.esm)
-> VoiceType:DLC1SeranaVoice      (002B6F:Dawnguard.esm)
-> VoiceType:DLC2FemaleUniqueFrea (017F80:Dragonborn.esm)
```

**重點：這 10 個全是 VoiceType 的集合，沒有一個裝 Actor / Faction / Race。** 「目標名單」鎖的維度是「嗓音類別」，不是「特定 NPC」。

### C. 其他用途（5 個）——與對話投放無關

| FormID | EditorID | 成員 | 用途 |
|--------|----------|------|------|
| `[A03FB0]` | `a_CustomSpellList` | Spell × 57 | 法術清單（如 `Flames 012FCD`、`Frostbite 02B96B`），供「NPC 是否會某類法術」等判斷 |
| `[03EF8C]` | `_RDOEncOrcHuntersFemale` | Npc × 5（RDO 自製 `_RDOEncOrcHunter0xF`）| 自製遭遇 NPC 群組 |
| `[DC60C0]` | `_RDOLeveledActorsWEAdventurerSS` | Npc × 2（`_WEAdventurerSpellsword*F`）| 自製冒險者 actor |
| `[F14397]` | `_RDOICAOWERoad02Noble` | **Package × 1** | AI Package 容器（非 actor/voice）|
| `[FB12EA]` | `_RDOEncHunters` | Npc × 1（`_RDOEncHunterNordM`）| 自製遭遇 NPC |

C 群是 RDO 自帶的小型遭遇/演出資源，與「大規模對話投放」這個主題無關，列出只為完整。

---

## 2. FormList 怎麼被 condition 引用

`IsInList` condition 在 dialogue 中出現 **936 次**（dump `grep -c 'IsInList' = 936`）。離線解碼每一筆 `IsInList` 指向的 FormList 與比較值，結果單一得驚人：

```
-- IsInList referenced FormLists (count) --
   936  aaa_RDOPreventedActorsList     ← 936 次全指這一個

-- IsInList list==value breakdown --
   923  aaa_RDOPreventedActorsList ==0  ← 守門：NOT in list
    13  aaa_RDOPreventedActorsList ==1  ← 邊緣用途（見下）
```

**沒有任何一筆 `IsInList` 指向 Voices 名單。** Voices FormList 從不透過 `IsInList` 投放；它們只透過 `GetIsVoiceType`（把 VoiceType-or-List 槽指向整個 FormList）使用，見 §3。

### 2.1 真實 INFO：IsInList 當排除守門（==0）

解碼一筆典型的 RDO 自製 follower 台詞（`[BF944D]`，完整 condition 串）：

```
[BF944D] DialogResponses
    GetIsVoiceType EqualTo 1 v=FemaleCommoner  (013ADE:Skyrim.esm) [OR]
    GetIsVoiceType EqualTo 1 v=FemaleEvenToned (013ADD:Skyrim.esm) [OR]
    GetIsVoiceType EqualTo 1 v=FemaleYoungEager(013ADC:Skyrim.esm)
    GetRandomPercent LessThanOrEqualTo 97
    IsInList        EqualTo 0 list=aaa_RDOPreventedActorsList   ← 守門
    GetRelationshipRank EqualTo 4
    GetInFaction    EqualTo 0 faction=PlayerMarriedFaction
    GetInFaction    EqualTo 0 faction=CurrentFollowerFaction
```

讀法：嗓音是三種女性泛用嗓音之一（OR 群）**且** 隨機 97% 過關 **且** `IsInList(aaa_RDOPreventedActorsList) == 0`（**這個 NPC 不在排除名單**）**且** 關係等級=4 **且** 不在婚姻/隨從陣營 → 才講這句。

`IsInList==0` 在此是**否決閘**：把這句話投給「符合嗓音/關係條件、但又不在黑名單上的所有 NPC」。

另一筆（`[F37AA5]`，給「會跑腿的小孩」的台詞）同樣模式：

```
[F37AA5] DialogResponses
    GetIsID EqualTo 1 id=Player
    GetRelationshipRank GreaterThanOrEqualTo 1
    GetInFaction EqualTo 0 faction=CurrentFollowerFaction
    GetIsVoiceType EqualTo 1 v=FemaleChild
    GetAllowWorldInteractions EqualTo 1
    IsInList EqualTo 0 list=aaa_RDOPreventedActorsList   ← 守門
    GetInFaction EqualTo 0 faction=BYOHRelationshipAdoptionFaction
```

「目標是 `FemaleChild` 嗓音、關係≥1、不在排除名單」——投放靠 `GetIsVoiceType` 鎖嗓音，`IsInList==0` 只負責剔除被列入黑名單的個別 NPC。

### 2.2 邊緣的 ==1 用途（13 筆）

13 筆 `IsInList==1` 不是「白名單投放」，而是 RDO 覆寫 vanilla follower INFO 時保留的 vanilla OR 群的一部分。例如 `[0D8E14]`：

```
[0D8E14] "All right."
    GetIsVoiceType    EqualTo 0 v=FemaleSultry          [OR]
    GetVMQuestVariable EqualTo 0                        [OR]
    IsInList          EqualTo 1 list=aaa_RDOPreventedActorsList
    GetIsVoiceType    EqualTo 1 v=VoicesFollowerNeutral
    GetInFaction      EqualTo 1 faction=CurrentFollowerFaction
```

`==1` 在這裡是「**如果**這個 NPC 在排除名單上，就走 vanilla 的這條 follower 回應」——即被排除者退回原版台詞的回退分支，屬於相容性收尾，不是主力投放手段（僅 13/936 ≈ 1.4%）。

### 2.3 PreventedActorsList 被掛在哪

離線統計「哪些 record 持有指向各 FormList 的 FormLink」：

```
aaa_RDOPreventedActorsList  被引用：DialogResponses 936、Quest 76
aaa_RDOVoicesFemaleList     被引用：DialogResponses 58、Quest 2
aaa_RDOVoicesMaleList       被引用：DialogResponses 60、Quest 2
aaa_RDOVoicesAll            被引用：DialogResponses 20、Quest 1
aaa_RDOPreventedActorsHatePL 被引用：（無）
aaa_RDOPreventedActorsFriend 被引用：（無）
```

排除名單橫跨 936 句台詞 + 76 個 quest 的 condition——是整個 mod 共用的單一守門 list。`HatePL` / `Friend` 兩個排除名單在 ESP 內**完全沒被引用**，是為未來/補丁預留的空殼。

---

## 3. Voices FormList 與 GetIsVoiceType 的分工

這是本主題最容易誤判的一點。數字（離線統計 dialogue condition）：

```
Total GetIsVoiceType in dialogue conditions: 9245
   - 指向「單一 VoiceType」 : 9035  (97.7%)
   - 指向「Voices FormList」 :  210  (2.3%)
Total IsInList               :  936  （全部指 PreventedActorsList，與 Voices 無關）
```

**結論：RDO 以「`GetIsVoiceType` 逐句直接鎖單一嗓音」為絕對主力**（9035 次）。`GetIsVoiceType` 的參數槽（VoiceType-or-List）原生就能塞「一個 VoiceType」或「一個裝 VoiceType 的 FormList」；RDO 絕大多數選擇逐句指名單一嗓音，常以 `[OR]` 串接幾個嗓音（如 §2.1 的三條 Female OR 群）。

Voices FormList 只在 **210 次**「想用一條 condition 涵蓋一整組嗓音」時當捷徑（解碼前幾名）：

```
   60  GetIsVoiceType -> aaa_RDOVoicesMaleList
   58  GetIsVoiceType -> aaa_RDOVoicesFemaleList
   20  GetIsVoiceType -> aaa_RDOVoicesAll
   12  GetIsVoiceType -> _RDO_OriginalVoicesFollowerAll
    4  GetIsVoiceType -> aaa_RDOVoicesUnique
    3  GetIsVoiceType -> a_RDO_USKPVendorMiscVoices
   ...（其餘為 vanilla 既有的 VoicesFollowerNeutral 等清單）
```

也就是說，Voices FormList 的角色是「**把 N 個 OR 的 `GetIsVoiceType` 壓成一條**」——當某句話要投給「全部男性嗓音」時，用 `GetIsVoiceType==1 voice/list=aaa_RDOVoicesMaleList` 一條，省掉 27 條 OR。但 RDO 大部分台詞要鎖的是 1～3 種特定嗓音（語氣要對），所以逐句指名才是常態。

**分工總結：**
- `GetIsVoiceType(單一 VoiceType)` = 主力，精準到「語氣對的那幾種嗓音」。
- `GetIsVoiceType(Voices FormList)` = 捷徑，用在「要涵蓋一大組嗓音」的少數場合（集中管理 + 一條搞定）。
- `IsInList(PreventedActorsList==0)` = 與嗓音正交的**全域排除閘**，每句台詞都加一條，剔除不該講話的個別 NPC。

三者**並用、各司其職**，不是「擇一」。

---

## 4. PreventedActors 排除機制

### 運作方式
- ESP 出貨時 `aaa_RDOPreventedActorsList` **是空的**（0 成員），但被 936 句台詞 + 76 quest 引用為 `IsInList(...)==0`。
- 空 list + `==0` 的初始效果 = 「永遠通過」（沒人在名單裡 → 條件恆真 → 不擋任何人）。
- 一旦有 NPC 被加入這個 list（執行期由 RDO 自身腳本/MCM，或由第三方相容補丁靜態追加成員），**所有掛了 `IsInList(PreventedActorsList)==0` 的台詞會立刻對該 NPC 全部失效**——即「一鍵把某 NPC 從 RDO 的泛用對話池裡摘掉」。

### 為什麼要這樣設計
RDO 用嗓音/陣營/關係**按類**投放（§3），無可避免會掃到一些「不該講泛用台詞」的對象：重要劇情 NPC、有自己整套對話的獨特角色、其他 mod 的自訂隨從等。逐句去加排除條件成本太高，於是 RDO 把「排除」收斂成**單一共用黑名單 + 每句一條守門**：要豁免一個 NPC，只需把它丟進 `aaa_RDOPreventedActorsList`，不必動 936 句台詞。

### 證據要點
- 936 句台詞中 923 句（98.6%）用 `IsInList(PreventedActorsList)==0` 當守門（§2 統計）。
- 該 list 在 ESP 內無靜態成員、且 RDO quest 的 VMAD script property 中**找不到名稱含 "Prevent" 的屬性**（離線掃描 `mod.Quests[].VirtualMachineAdapter.Scripts[].Properties` 無命中）——印證成員是「執行期/外部填充」而非 ESP 內寫死。
- 兩個未使用的排除名單 `HatePL` / `Friend`（§1.A）是為「依關係動態切換排除集合」預留的擴充點，目前空置。

---

## 5. 可複製配方：用 FormList 做規模化投放

把 RDO 的做法抽成可重用範本。一個「規模化投放」的台詞 condition 串長這樣：

```
GetIsVoiceType == 1  voice/list = <白名單：單一 VoiceType 或 aaa_VoicesXXX FormList>   [可 OR 多條]
IsInList       == 0  list       = <黑名單：aaa_PreventedActorsList>                      ← 全域守門
<其他維度>           例如 GetRelationshipRank / GetInFaction / GetRandomPercent
```

對應到 FormList 的兩種角色：

1. **白名單（目標集合）**：建一個裝 VoiceType 的 FormList（如 `aaa_VoicesFemaleList`），用 `GetIsVoiceType==1` 引用 → 一條 condition 涵蓋整組嗓音。**用在「這組台詞要投給一大類 NPC」**。
2. **黑名單（排除集合）**：建一個**空** FormList（如 `aaa_PreventedActorsList`），用 `IsInList==0` 引用，掛在每一句台詞上 → 之後只要往這個 list 加 actor，就能把它一次從整個對話池摘除。**用在「集中管理豁免名單」**。

### 與「逐句寫 GetIsVoiceType」的差異

| 面向 | FormList 集中管理 | 逐句寫 GetIsVoiceType |
|------|------------------|----------------------|
| condition 條數 | 一條涵蓋整組（白名單 list）| 每個嗓音一條，常 OR 串接 |
| 改動成本 | 改 list 成員 → 全部引用同步生效 | 要逐句改 condition |
| 可被別的 mod 注入 | **可**（補丁往 FormList 追加成員即可，不必碰台詞）| 不可（condition 寫死在 INFO 裡）|
| 精準度 | 較粗（整組）| 較細（可只鎖「語氣對」的 1～3 種）|

RDO 的實際取捨：**目標投放用逐句 `GetIsVoiceType`**（要語氣精準，9035 次），只在「要涵蓋一大組」時退用白名單 FormList（210 次）；**排除則一律用黑名單 FormList**（集中管理 + 可被補丁注入，923 次）。白名單追求精準故少用 FormList，黑名單追求「集中 + 可注入」故全用 FormList——這是兩種需求各取所長的結果。

---

## 6. 對 ModForge 的意義

ModForge 目前**無法生成 FormList record**，condition 也**不支援 IsInList / GetIsVoiceType**。對照 `others/modforge-relevance.md`「可短期補」第 2 點，要支援 RDO 式投放，缺三塊：

### (a) FormList record builder（FLST）
- 現況：`Generator.Build.Conditions.cs` / `Generator.Build.Vendor.cs` 只能**引用**既有（vanilla）FormList——`NpcSpec.SellBuyList` 是「ref → 一個 vanilla FormList」（`Spec.Actors.cs:82`），全 Core 內**沒有任何 `AddNew*FormList` 之類的建立路徑**。
- 要補：一個 `FormListSpec`（EditorID + `items[]` 的 ref 清單），build 時建 FLST record、把成員 FormLink 填進去。成員型別不限（VoiceType / Actor / Spell / Package 都可，如 §1 所示），builder 不需限制型別。
- **特例要支援「空 FormList」**：排除名單範式（§4）的核心就是「出貨時空、執行期/補丁填充」，所以 `items[]` 允許為空。

### (b) condition 支援 IsInList（引用該 FormList）+ GetIsVoiceType
- 現況：`Generator.Build.Conditions.cs` 的 dispatch 已有 `getinfaction` / `getisid` / `haskeyword` 等 case（行 56–65），但**沒有 `isinlist`、也沒有 `getisvoicetype`**（grep 兩者皆 0 命中）。
- 要補：
  - `case "isinlist": { var d = new IsInListConditionData(); if (hasParam) d.FormList.Link.SetTo(paramFk); ... }`——paramFk 解析到 (a) 建的 FLST。
  - `case "getisvoicetype": { var d = new GetIsVoiceTypeConditionData(); if (hasParam) d.VoiceTypeOrList.Link.SetTo(paramFk); ... }`——paramFk 可指向單一 VoiceType **或** Voices FormList（同一個槽，RDO 兩種都用）。
- dispatch 結構已可擴充，這是低成本高 ROI（解鎖「按類投放」的第一步，見 `dialogue-targeting-technique.md`）。

### (c) spec 層「名單 + 一組 condition 套 N 句」的批次模板
- 現況：ModForge condition 逐句手寫，沒有「一組 condition 重用到多句台詞」的批次入口。
- 要補：一個批次 dialogue 模板，讓使用者寫一次「白名單 list ref + 排除 list ref + 一組維度 condition」，套用到一張台詞表的 N 句上，build 時對每句 INFO 複製這組 condition。對應 RDO「6650 句自製台詞共用同一套 condition 骨架」的規模化做法。
- 與 (a)(b) 合起來才完整：(a) 給 list，(b) 給能引用 list 的 condition，(c) 給「一套 condition × N 句」的批次展開。三者缺一，RDO 式投放就只能逐句手刻。

### 落地優先序（務實）
1. **(b) condition 兩個 case** —— 改一個檔、十幾行，立刻能在台詞裡引用 vanilla VoiceType / 既有 FormList 做排除與按嗓音投放。
2. **(a) FormList builder** —— 讓使用者能自建白/黑名單（尤其空黑名單）。
3. **(c) 批次模板** —— 工程較大，是把前兩者規模化的入口，最後做。
