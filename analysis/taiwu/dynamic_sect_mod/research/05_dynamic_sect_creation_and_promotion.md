# 中小門派 mod — 動態誕生與升格機制調查（05）

> 建立：2026-05-24。調查領域：中小門派在**遊戲途中**「動態誕生」與「升格中型」的最核心機制。
> **唯一事實來源**：實裝版 0.0.79.60 後端 DLL（`Backend/GameData.dll`、`Backend/GameData.Shared.dll`），全部方法/型別已用 `ilspycmd -t` 反編譯逐字核對（下文 path:line 皆指向**反編譯出的實裝原始碼行號**，非舊參考源）。凡未核對者明確標 ⚠️。
> 接續並建立於：`player_faction_research/02`（佔位 sect、`JoinOrganization` 的 `SettlementId>=0` 前提）、`npc_population_research/01`（`CreateIntelligentCharacter` 收尾自動入籍）、`player_faction_research/01`（`_taiwuBuildingAreas` 建設權軌）、`new_sect_mod/phase2_map_findings.md`（陳家堡上地圖踩雷，反證「不上地圖更輕」）、`dynamic_sect_mod/design_vision.md`（設計願景，§六接點表）。
> **本次同時釘死了 `02 §6 待釐清 #1`（佔位 vs 上地圖雙登記）這個長期懸案——見下方 §1.4。**

---

## 0. 一句話結論（先給答案）

- **動態誕生最省力且最穩的方案＝「預生池＋認領」（方案 2）**，**不要**在 runtime 新建 settlement（方案 1）。
- 做法：開新世界前注入 **N 個空門派 config（id≥42、克隆世俗派、各職位 `Amount=0`、`RestrictPrincipalAmount=false`）** → 開局 `CreateEmptySects` 自動各生一個 `AreaId=-1` 的佔位 `Sect` 進池（這條已是遊戲每局必跑的既有機制，零自建）→「門派誕生」時用 `JoinSect`／`ChangeOrganization` 把師徒們塞進池中一個尚未認領的佔位 sect 的 `SettlementId`。**完全避開 runtime `CreateSettlement`、避開地圖、避開「count>1 → GetSettlementByOrgTemplateId 回 null」陷阱。**
- **升格判定（過月主執行緒鉤）**：
  - **人數**＝`DomainManager.Organization.GetSettlementByOrgTemplateId(myOrgId).GetMembers().GetCount()`（`OrgMemberCollection.GetCount()` 把 9 階位 HashSet 加總，`GameData.Shared` 的 `OrgMemberCollection.cs:108`）。
  - **據點**＝這條跟「身份」是兩條獨立軌；最乾淨的「有無據點」表徵＝**該門派是否在某地格的產業網格佔了一格**（mod 自己記哪格屬於它，或查 `BuildingDomain.GetBuildingBlockList(location)` 看那格 templateId 是不是 mod 放的據點建築）。**不要**借 `_taiwuBuildingAreas`（那是太吾玩家專屬的家園/建設軌）。
- **runtime 新建（方案 1）技術上能跑但不穩**：`CreateSettlement` 會連帶 `SetLargeSectFavorabilities` + `CreateSettlementMembers`（要真實 `Location`、會生一批成員），且新 sect 進每月所有 `_sects` 迴圈；對「途中誕生一個空殼小派」是殺雞用牛刀且副作用面大。

---

## 1. 範圍 1：runtime 動態新建一個 Sect + 合法 SettlementId — 可行但不建議

### 1.1 `CreateSettlement`（runtime 新建的唯一正規入口）— 實裝逐字
`OrganizationDomain.CreateSettlement(DataContext, Location, sbyte orgTemplateId)`（`OrganizationDomain.cs:2102`）：
```csharp
public short CreateSettlement(DataContext context, Location location, sbyte orgTemplateId)
{
    short num = GenerateNextSettlementId(context);
    if (IsSect(orgTemplateId))
    {
        Sect sect = new Sect(num, location, orgTemplateId, context.Random);
        AddElement_Sects(num, sect);
        SetLargeSectFavorabilities(_largeSectFavorabilities, context);   // ★大派好感網重算
        AddSettlementCache(sect);
        CreateSettlementMembers(context, sect);                          // ★立刻生成一批成員
    }
    else { /* CivilianSettlement 分支，同樣 CreateSettlementMembers */ }
    return num;
}
```
- `GenerateNextSettlementId`（`:2215`）：回傳 `_nextSettlementId` 並自增、用 `SetNextSettlementId` 寫回（走 op-log）。**runtime 呼叫安全、id 不會撞**（全局單調遞增）。
- `AddElement_Sects`（`:4607`）：`_sects.Add` ＋ `OperationAdder.DynamicObjectCollection_Add(3, 0, objectId, ...)` ＋ `Serialize`。**這一步把新 Sect 正式註冊進序列化/操作日誌系統**——所以 runtime 新建的 sect **會進存檔、會被前端認得**（前端透過同一份序列化資料讀）。
- `AddSettlementCache`（`:1800`）：寫三張快取 `_locationSettlements[Location]`、`_settlements[id]`、`_orgTemplateId2Settlements[orgTemplateId]`。
  - ⚠️ **`_locationSettlements.Add(settlement.GetLocation(), ...)` 用 Location 當 Dictionary key**——若新建時給的 `Location` 與既有任何 settlement 撞（含佔位 sect 的 `Location(-1, n)`），會丟 `ArgumentException`（重複鍵）。runtime 新建必須給一個**未被佔用的合法 Location**。

### 1.2 副作用評估（為何「不穩」）
1. **`CreateSettlementMembers`（`:2227`）會立刻生人**：依 `OrganizationItem.Population>0` 與各職位 `Members[grade]→OrganizationMemberItem.Amount>0` 大批 `CreateCoreCharacter`/`CreateBrothersAndSisters`/`CreateSpouseAndChildren`（`:2269-2294`）。若我們想要的是「空殼小派、人由師徒認領」，這完全是反效果——除非把 config 的 `Population<=0`（`:2253` 直接 return，不生人）。但若 `Population<=0`，那跟「預生池佔位」就沒差了，反而多繞 runtime。
2. **要真實 `Location`**：`Sect` ctor 與 `CreateSettlementMembers` 都會讀 `location.AreaId`（`:2257` `GetStateTemplateIdByAreaId`、`GetSettlementBlocks`）。給 `AreaId=-1` 時 `GetStateTemplateIdByAreaId(-1)` 會走 `b<=0 → 取太吾村 state`（`:2258-2261`）——能不崩但語意混亂；給真實 `AreaId` 則需先確認那格沒被佔（撞 `_locationSettlements` 鍵）。
3. **`SetLargeSectFavorabilities` 每次新建都重算**（`:2109`）：對 id≥42 非大派無實質影響（`GetLargeSectIndex(42)=-1`，`:1385`），但是無謂開銷。
4. **進每月所有 `_sects` 迴圈**：新 sect 一旦進 `_sects`，`UpdateApprovingRateEffectOnAdvanceMonth`(`:570`)、`UpdateSectPrisonersOnAdvanceMonth`(`:1395`)、`UpdateFugitiveGroupsOnAdvanceMonth`(`:1403`)、`UpdateSettlementCacheInfo`(`:1524`，含 `SortMembersByCombatPower`/`ForceUpdateInfluencePowers`)、`RecordSettlementStandardPopulations`(`:3176`) 等全月度流程都會掃到它。**這些對「空成員 sect」都是空迴圈（安全）**，但這正是「預生池」方案早已驗證過的同一條路（佔位 sect 本來就在這些迴圈裡跑了好幾年——15 大派的佔位也在，見 §1.4），所以 runtime 新建並不會比預生池更安全，只是多了個生成時機風險。

### 1.3 安全時機
若真要 runtime 新建，**必須在主執行緒**（`Domain.MainThreadDataContext`），用過月主執行緒鉤 `Events.RegisterHandler_AdvanceMonthBegin`／`RegisterHandler_AdvanceMonthFinish`（宣告於 `GameData.DomainEvents.Events`，`RegisterHandler_AdvanceMonthBegin`＝full decompile `GameData.decompiled.cs:631427`、`RegisterHandler_AdvanceMonthFinish`＝`:631457`）。`AddElement_*`/`JoinOrganization` 都是全域寫入，**過月平行段（worker thread）內絕對不可呼**（與既有 MEMORY「過月平行段勿寫全域」一致）。

### 1.4 ⚠️→✅ 釘死長期懸案：佔位 sect 與上地圖 sect 的「雙登記」
> 推翻/補完 `player_faction_research/02 §6 待釐清 #1`。

開新世界順序（`MapDomain.CreateAllAreas`，full decompile `GameData.decompiled.cs:588313` 起）：
1. `DomainManager.Organization.CreateEmptySects(context)`（`:588313`）→ `OrganizationDomain.CreateEmptySects`（`OrganizationDomain.cs:2086`）：**對每個 `IsSect=true` config（含 15 大派 id 1-15）各生一個佔位 `Sect`，`Location = new Location(-1, num)`**（num 是 sect 計數器，故各佔位 Location 互不撞）。
2. 之後 `CreateNormalArea` 的聚落迴圈（`:588850` 區段）對 area 的 `config.OrganizationId[i]` 呼 `CreateSettlement(context, location, orgId)`——**對 area 16 的 `OrganizationId={1,37,38}`（實裝核對：`MapArea` 的 `organizationId17 = new sbyte[3]{1,37,38}`、`settlementBlockCore17 = new short[3]{19,35,36}`，`GameData.Shared` `MapArea.cs:2584` 區段）會再 `new Sect` 一個少林(id 1) 的真實 settlement。**

**結論（鐵證）**：`RemoveSettlementCache`（`OrganizationDomain.cs:1814`）與 `RemoveElement_Sects`（`:4616`）在**整個 GameData.dll 反編譯中從未被任何地方呼叫**（`grep` 全 decompile 僅命中宣告本身）。⇒ **佔位 sect 永不被移除、永不被搬移**（無 `Settlement.SetLocation`，`Settlement` 類無此方法）。⇒ **大派（id 1-15）在 `_orgTemplateId2Settlements[id]` 必有 2 筆（佔位 1 + 上地圖 1）。**

而 `GetSettlementByOrgTemplateId`（`:637`）在 `count>1 || count==0` 時**回 null**（`:644-651`）。⇒ **`GetSettlementByOrgTemplateId(大派id)` 在 runtime 實際回 null**；`GetSettlementIdByOrgTemplateId(大派id)` 回 -1（`:679` 的 `?? -1`）。
- 多處對大派直接 `(Sect)GetSettlementByOrgTemplateId(orgTemplateId)`（如 `:1199`、`:3149`、`:3171`）**若真被以大派 id 呼叫會 NPE**——但它們是冷門/防禦路徑（如 `FixAbnormalCharacterOrganization`，`CharacterDomain.cs:1470`，只在 `SettlementId<0` 的異常修復時跑、`:1491` 的 `IsLargeSect` 分支才碰），正常流程大派 settlement 是用 `GetSettlementByLocation` / 透過 area 的 `SettlementInfo` 拿到、不靠這個 by-orgTemplateId 查表。

> **對本 mod 的決定性意義**：`GetSettlementByOrgTemplateId(id)` 要「恰回 1 個」**只有在該 id 名下恰好 1 個 settlement 時成立**。
> - **小派 id≥42 若「只佔位、永不上地圖」→ count==1 → `GetSettlementByOrgTemplateId(42)` 穩定回那個佔位 sect。✅ 這正是我們要的。**
> - **反過來：千萬不要讓小派 id 又上地圖（被任何 area `OrganizationId[]` 引用）**，否則 count 變 2、`GetSettlementByOrgTemplateId(42)` 回 null，所有靠這條查表的程式（含我們自己升格時數人）全壞。**這也再次佐證「不上地圖更輕、更穩」。**

---

## 2. 範圍 2：方案 2「預生池＋認領」— 重點推薦，逐項對比

### 2.1 機制
- **前置（plugin Initialize，世界生成前）**：用 `Config.Organization.AddExtraItem` 注入 **N 個** 空門派 config（id 42, 43, …, 42+N-1）。每個：`IsSect=true`、克隆某**世俗派**（避開僧侶法號字庫，`SeniorityGroupId=-1` 安全，依 `02 §3.3` + `Sect.cs:156` 的 `SeniorityGroupId>=0` 守衛）、`Population<=0`（佔位不生人）、所有職位 `OrganizationMemberItem.Amount=0`、`RestrictPrincipalAmount=false`（見 §2.3 第 1 點防 throw）。
  - **時機已釘死**：`MapArea.Init()`/`Organization.Init()`（`ReloadAllConfigData`，並行 join）嚴格早於 plugin `Initialize()`，而 `InitializeSectOrgTemplateIds()`（`OrganizationDomain.cs:3890`，建可加入門派池 `_allSectOrgTemplateIds`）在 `OnInitializeGameDataModule` 跑、**晚於** plugin Initialize——所以注入的 id≥42 **會被收進可加入門派池**（`:3895` 對每個 `IsSect` config 收）。與陳家堡 `phase2 §4` 同一條時序鏈。
- **開局自動佔位**：`CreateEmptySects`（`:2086`）對每個 `IsSect` config 各生 1 個佔位 sect。⇒ **N 個小派各得一個 `AreaId=-1`、count==1、`GetSettlementByOrgTemplateId(42+k)` 穩回的合法 `SettlementId`，零自建 settlement。**
- **誕生＝認領**：「某 NPC 創派」時，從池中挑一個**尚未被認領**的佔位 sect（mod 自記哪些已用），把創派者 + 弟子用 `JoinSect`/`ChangeOrganization`（帶 `OrganizationInfo(42+k, grade, true, 該佔位 SettlementId)`）塞進去。**SettlementId 來自 `GetSettlementIdByOrgTemplateId(42+k)`，必 ≥0，滿足 `JoinOrganization` 硬前提。**

### 2.2 方案 1 vs 方案 2 對比

| 維度 | 方案 1：runtime `CreateSettlement` | 方案 2：預生池＋認領（**建議**） |
|---|---|---|
| 是否自建 settlement | 是（runtime new Sect + 進 op-log） | 否（用每局必生的佔位 sect） |
| 需要合法 Location | **要**（給 AreaId/BlockId，且不可撞 `_locationSettlements` 鍵，`:1802`） | 不要（佔位是 `Location(-1, n)`，引擎自帶且不撞） |
| 會否意外生成員 | `Population>0` 時會（`CreateSettlementMembers`, `:2111`）；要刻意設 `Population<=0` 才不生 | 永不（佔位 sect 天生空成員，成員只在 `CreateSettlement` 時生） |
| 池容量 | 無上限（隨時 new） | **有上限 = 注入的 N 個 config**（用完要再開新世界才會多）⚠️ |
| 前端認得 | 認得（進序列化） | 認得（佔位也進序列化、`AddSettlementCache`） |
| 過月/AI 異常路徑 | 與方案 2 相同（都進 `_sects` 月度迴圈，空成員＝空迴圈安全） | 同左（且 15 大派佔位已驗證跑多年無事） |
| `GetSettlementByOrgTemplateId` 可用 | 視 count（若該 id 也有佔位則 count==2→null，要小心） | **穩定回 1 個**（只要該 id 不上地圖，count 恆 1） |
| 工程量／風險 | 高（時機、Location、成員、count 全要顧） | 低（只做 config 注入 + JoinSect） |

**結論**：方案 2 全面勝出，唯一代價是「同一局可誕生的小派數量上限＝注入的 N」。建議 N 取一個慷慨值（如 20~50），單局夠用；若要無上限再退而求其次評估方案 1（並務必 `Population<=0` + 妥善 Location）。

### 2.3 認領時的兩個必查陷阱
1. **`CheckPrincipalMembersAmount` 會 throw（`:1840-1860`）**：`JoinOrganization` 收尾在 `destOrgInfo.Principal==true` 時呼它（`:770-772`）；若該職位 config `RestrictPrincipalAmount=true` 且該階 principal 人數 > `Amount`，**丟 `Exception`**（`:1860`，後端未捕捉＝整個 GameData 進程崩）。⇒ **注入 config 時，師徒會用到的職位務必 `RestrictPrincipalAmount=false`（或 `Amount` 設足夠大）。**
2. **`SetRandomSectMentor`（`:1863`）對空 sect 安全**：找不到符合 `mentorGrade` 的成員就回 -1（迴圈空集合、`:1881` `while mentorGrade<9` 找不到自然結束），不崩。掌門（`Grade==8 && Principal`）會自動加 feature 405（`:737-740`）。

---

## 3. 範圍 3：小門派狀態存哪（建議方案）

設計願景拍板「升格判定＝過月查人數＋據點；狀態存哪再說」。給出建議：

### 3.1 「身份」本身不必另存 — 已落在 `OrganizationInfo`
- 每個小派成員（含創派者）的「我屬於 42+k 號小派、在那個 SettlementId、職階 grade」**已存在 `Character` 內嵌的 `OrganizationInfo`（8 bytes，`OrgTemplateId/Grade/Principal/SettlementId`）**——這是引擎原生序列化的，免 mod 自存（見 `02 §1.1`）。
- 「這個小派目前有哪些人」**已由佔位 `Sect.Members`（`OrgMemberCollection`）持有**，`JoinOrganization` 會 `members.Add(charId, grade)` + `sect.SetMembers(...)`（`:734-735`，走 op-log 入存檔）。⇒ **成員名冊不必 mod 自存。**

### 3.2 需要 mod 私有表的，只有「引擎沒有的概念」
小型 vs 中型、是否已認領哪個池子 id、據點在哪格、外交關係（願景 §七#3 拍板「自建關係表」）等，引擎無對應欄位 ⇒ **mod 自序列化一張私有表**。建議：

| 要存的 | 建議存法 |
|---|---|
| 哪些池中 id 已被認領、認領給誰（創派者 charId） | **mod 私有表**（key=orgTemplateId 42+k，value=創派者 charId + 誕生日期 + 階段 enum） |
| 小型／中型階段旗標 | mod 私有表（一個 enum；升格＝過月時重算後寫這裡） |
| 據點 Location（哪格產業屬於它） | mod 私有表（小派沒上地圖、沒有 `Settlement.Location` 真實值，據點是「借用某城鎮產業網格的一格」，引擎不會幫記歸屬，見 §4.2） |
| 外交/地區影響 | mod 私有表（願景已拍板自建） |

- **不建議**借 `OrganizationInfo` 塞自訂位（它 4 欄位語意固定、序列化長度寫死 8 bytes）；也不建議借某 feature 表達「中型」（feature 是角色級、不是門派級）。
- **mod 私有表的序列化**：後端 mod 自己用檔案/存檔附帶資料持久化（太吾 mod 慣例：跟著存檔 slot 存自己的 json/二進位）。⚠️ 此持久化機制本調查未深入（屬框架層，design_vision §三 JSON 框架的一部分），列待釐清。

---

## 4. 範圍 4：升格判定（過月主執行緒鉤）

掛 `Events.RegisterHandler_AdvanceMonthBegin`（或 Finish，`GameData.DomainEvents.Events`）。對 mod 私有表裡每個「已認領、仍小型」的小派，重算兩條件：

### 4.1 數「目前人數」— 最直接、已核對
```csharp
short orgId = 42 + k;
Settlement s = DomainManager.Organization.GetSettlementByOrgTemplateId(orgId); // count==1 → 穩回佔位 sect
if (s == null) { /* 防呆：理論上不該 null，除非該 id 不慎上了地圖 */ }
int memberCount = s.GetMembers().GetCount();   // ★人數
```
- `Settlement.GetMembers()`（public，`Settlement.cs:1799`）回 `OrgMemberCollection`。
- `OrgMemberCollection.GetCount()`（`GameData.Shared` `OrgMemberCollection.cs:108-111`）＝`_grade0.Count + … + _grade8.Count`，把 9 階位 HashSet 加總。**這就是「某小門派目前人數」的權威讀法。**
- 若要排除嬰幼（願景未要求，但很多既有程式這樣做）：`DomainManager.Character.ExcludeInfant(members.GetMembers(b))`（`OrganizationDomain.cs:1611` 等多處用法可參考）。
- ⚠️ **不要遍歷全人口查關係網數人**——那是 O(人口) 且語意不準；`Sect.Members` 就是門派成員集合，直接 `GetCount()` 最省。

### 4.2 判「有沒有據點（產業視圖佔一格）」
願景定義據點＝「在某地點的產業視圖中擁有一格屬於它的地盤」，且要「複用既有產業建築」。底層事實（建立於 `player_faction_research/01 §6` + 本次核對）：

- **建築運行時資料 `BuildingBlockData` 不存 `OrganizationId`**（`01 §6.1`）；「某格屬於某組織」是**間接**的（靠該格所在 settlement 的 `Location` + 該組織把建築 `PlaceBuildingAtBlock` 放上去）。
- **小派沒上地圖、沒有真實 `Location`**（佔位是 `AreaId=-1`）⇒ **它沒有「自己的產業網格」**。所以「小派的據點」只能是**借用某個既有城鎮聚落的產業網格裡的一格**——而引擎**不會自動記住「這一格歸 42 號小派」**。
- `PlaceBuildingAtBlock`（`BuildingDomain.cs:678`）的前提：`_buildingAreas[new Location(areaId, blockId)]` **必須已存在**（`:683` 直接索引，不存在會 `KeyNotFoundException`）⇒ 只能放在「已有 `BuildingAreaData` 的城鎮地格」（城鎮在世界生成時 `CreateBuildingArea`，見 full decompile `:588892`）。
- **`_taiwuBuildingAreas`／`AddTaiwuBuildingArea`／`GetTaiwuBuildingAreas`（`BuildingDomain.cs:6303/14260`、`_taiwuBuildingAreas` 欄位 `:103`）是太吾玩家專屬的家園/建設區清單**——世界生成只對太吾村那格 `AddTaiwuBuildingArea`（full decompile `:588895` 的 `if (b9==16)`，與 `CreateEmptyStateAreas` 的 `:588402`）。⚠️ **不要拿這條軌當「小派據點」的判定或登記**，否則會跟太吾家園機制混淆（陳家堡產業 crash 的教訓正是家園身分被誤用，`phase2 §10`）。

**所以「有無據點」的建議判法（mod 自記為主，引擎查為輔）**：
1. **mod 自記**：玩家/NPC「砸錢建據點」時，mod 在私有表記下 `(orgId 42+k → 據點 Location(areaId, blockId) + 該格的 blockIndex/templateId)`。升格判定直接讀這張表「該小派是否有登記據點」即可，**最簡單、最可靠**。
2. **引擎查為輔（驗證據點建築還在）**：`DomainManager.Building.GetBuildingBlockList(new Location(areaId, blockId))`（`BuildingDomain.cs:334`）回該地格產業網格全部 `BuildingBlockData`，檢查 mod 記的那個 blockIndex 的 `TemplateId` 是否仍是 mod 的據點建築（防被拆/被覆蓋）。

⇒ **升格條件成立 = `memberCount >= 10`（願景§一）AND mod 私有表記錄該小派有有效據點。** 兩者都在過月主執行緒鉤裡算，純讀取、不寫全域（寫只寫 mod 私有表的階段旗標），安全。

---

## 5. 範圍 5：「創派宣告」登記流程

把創派者 + 一兩個弟子，從「散人/各自門派」登記成「同屬新小派」。

### 5.1 用 `JoinSect`（最貼「加入門派」語意，會寫生平）
`OrganizationDomain.JoinSect(DataContext, Character, OrganizationInfo destOrgInfo)`（`OrganizationDomain.cs:702`）：
```csharp
LeaveOrganization(context, character, charIsDead: false);   // 先脫離原門派（散人/原派）
JoinOrganization(context, character, destOrgInfo);          // 登記進新 sect 成員集合
character.SetOrganizationInfo(destOrgInfo, context);        // 寫角色身份欄位
... AddJoinSectSucceed(...)                                 // 寫「加入門派成功」生平
Events.RaiseCharacterOrganizationChanged(...)               // 廣播身份變更事件
```
- 通用版 `ChangeOrganization`（`:861`）做同樣三步但生平記錄不同（`AddJoinOrganization`/`AddChangeOrganization`/`AddBreakAwayOrganization`，且 `OrgTemplateId==20`＝丐幫 特例跳過）。**「創派」用 `JoinSect` 最對味（弟子們「加入了新門派」）。**

### 5.2 `destOrgInfo` 怎麼填（關鍵）
```csharp
short sid = DomainManager.Organization.GetSettlementIdByOrgTemplateId(orgId42k); // ★必 ≥0（佔位 count==1）
// 創派者：掌門 grade 8
var founderOrg = new OrganizationInfo(orgId42k, grade: 8, principal: true, settlementId: sid);
// 弟子：低階 grade（例如 0），principal: true
var discipleOrg = new OrganizationInfo(orgId42k, grade: 0, principal: true, settlementId: sid);
DomainManager.Organization.JoinSect(ctx, founder,   founderOrg);
DomainManager.Organization.JoinSect(ctx, disciple,  discipleOrg);
```

### 5.3 `JoinOrganization` 的 `SettlementId>=0` 硬前提 — 實裝再核對
`OrganizationDomain.JoinOrganization`（`:717`）開頭：
```csharp
if (destOrgInfo.SettlementId < 0) return;   // :719 — SettlementId 無效直接 return，不登記任何集合
```
- `SettlementId>=0` 才走 sect 分支（`IsSect`→`_sects[SettlementId]`，`:726-743`）：建 `SectCharacter`、`members.Add(id, grade)`、與全聚落成員建關係、`TryAddSectMemberFeature`、`SetRandomSectMentor`、`TryBecomeSectMonk`、grade8+principal 加 feature 405。
- ⇒ **`sid` 必須來自 `GetSettlementIdByOrgTemplateId(orgId42k)` 且該 id count==1**（佔位 sect，§1.4）。**這是整條誕生流程的命脈**——若小派不慎上了地圖（count==2），`GetSettlementIdByOrgTemplateId` 回 -1，`JoinOrganization` 直接 return，師徒登記不進去，門派形同沒誕生。

### 5.4 太吾（玩家）對等
太吾自己創派同理：對 `DomainManager.Taiwu.GetTaiwu()` 呼 `JoinSect`（帶上面的 `founderOrg`）。願景§一強調玩家對等——機制上 `JoinSect`/`OrganizationInfo` 對玩家與 NPC 一視同仁（龍島忠僕範本 `CreateFulongServant` 也是直接複製太吾的 `OrganizationInfo` 再改 grade，見 `npc_population_research/01 A-2`）。⚠️ 太吾改 `OrganizationInfo` 是否觸發前端門派 UI/主線判定的額外副作用，未端到端實測，列待釐清。

### 5.5 收徒/師徒關係 vs 門派身份是兩件事
- 願景的「小型門派＝師徒關係」：師徒關係（relation 2048，`SetRandomSectMentor` 在 `:1869` 用 `GetRelatedCharIds(charId, 2048)` 找師父）與「同屬一個門派 `OrgTemplateId`」**是兩條獨立資料**。
- **建議**：小型階段可先只建師徒關係（不認領 sect、`OrganizationInfo` 不變）；到「創派宣告」才認領佔位 sect 並 `JoinSect`，把師徒們的 `OrgTemplateId` 統一成 42+k。這樣「小型＝純師徒、還沒佔池子」與「中型＝已認領 sect」對應得很乾淨，也省池子（沒宣告就不吃池容量）。

---

## 6. 關鍵原始碼錨點（全部實裝 0.0.79.60 核對）

| 機制 | 方法/型別 | 位置（反編譯行號） |
|---|---|---|
| 開局佔位 sect（每局必跑，N 個小派各 1 個） | `OrganizationDomain.CreateEmptySects` | `OrganizationDomain.cs:2086` |
| runtime 新建 settlement（方案 1，不建議） | `OrganizationDomain.CreateSettlement` | `OrganizationDomain.cs:2102` |
| 新 settlement id 產生 | `GenerateNextSettlementId` | `OrganizationDomain.cs:2215` |
| 註冊 sect 進序列化/op-log | `AddElement_Sects` | `OrganizationDomain.cs:4607` |
| 三快取登記（含 Location 鍵） | `AddSettlementCache` | `OrganizationDomain.cs:1800` |
| **佔位移除（從未被呼叫）** | `RemoveSettlementCache`/`RemoveElement_Sects` | `:1814`/`:4616`（全 decompile 零呼叫點） |
| by-orgTemplateId 查 settlement（count!=1 回 null） | `GetSettlementByOrgTemplateId` | `OrganizationDomain.cs:637` |
| 取 SettlementId（null→-1） | `GetSettlementIdByOrgTemplateId` | `OrganizationDomain.cs:677` |
| 加入門派（**SettlementId>=0 前提**） | `JoinOrganization` | `OrganizationDomain.cs:717`（守衛 `:719`） |
| 創派宣告/換派（寫生平） | `JoinSect` / `ChangeOrganization` | `OrganizationDomain.cs:702` / `:861` |
| 改職階 | `ChangeGrade` | `OrganizationDomain.cs:889` |
| principal 超額會 throw | `CheckPrincipalMembersAmount` | `OrganizationDomain.cs:1840`（throw `:1860`） |
| 師父指派（空 sect 安全） | `SetRandomSectMentor` | `OrganizationDomain.cs:1863` |
| 可加入門派池（含 id≥42） | `InitializeSectOrgTemplateIds` | `OrganizationDomain.cs:3890` |
| 大派索引（id≥42 回 -1） | `GetLargeSectIndex` | `OrganizationDomain.cs:1385` |
| **數人數** | `Settlement.GetMembers().GetCount()` | `Settlement.cs:1799` + `OrgMemberCollection.cs:108`（Shared） |
| Sect ctor（SeniorityGroupId>=0 守衛） | `Sect(short,Location,sbyte,IRandomSource)` | `Sect.cs:152`（守衛 `:156`） |
| 過月鉤註冊 | `Events.RegisterHandler_AdvanceMonthBegin/Finish` | `GameData.DomainEvents.Events`（full decompile `:631427`/`:631457`） |
| 據點：放建築（前提 BuildingArea 已存在） | `BuildingDomain.PlaceBuildingAtBlock` | `BuildingDomain.cs:678`（索引 `:683`） |
| 據點：查某地格產業網格 | `BuildingDomain.GetBuildingBlockList` | `BuildingDomain.cs:334` |
| 太吾家園/建設軌（**勿用於小派據點**） | `_taiwuBuildingAreas`/`AddTaiwuBuildingArea`/`GetTaiwuBuildingAreas` | `BuildingDomain.cs:103`/`:6303`/`:14260` |
| 世界生成聚落迴圈（CreateSettlement 上地圖） | `MapDomain.CreateNormalArea`（settlement loop） | full decompile `GameData.decompiled.cs:588850` 區段 |
| area16 org/block 值（核對「上地圖＝雙登記」） | `MapArea`（`organizationId17={1,37,38}`、`settlementBlockCore17={19,35,36}`） | `GameData.Shared` `MapArea.cs:2584` 區段 |
| NPC 生成自動入籍 | `CharacterDomain.CreateIntelligentCharacter`→收尾 `JoinOrganization` | `CharacterDomain.cs:27821`；`FixAbnormalCharacterOrganization` `:1470` |

---

## 7. 對既有調查的勘誤/漂移

1. **`player_faction_research/02 §6 待釐清 #1`（佔位 vs 上地圖雙登記、有無清理）→ 本次釘死**：**無清理**（`RemoveSettlementCache`/`RemoveElement_Sects` 全 decompile 零呼叫）。大派確實 count==2，`GetSettlementByOrgTemplateId(大派id)` 在 runtime 回 null。小派只要不上地圖即 count==1、查表穩。`02 §4.3` 末「`GetSettlementByOrgTemplateId(42)` 可正常回傳」**對小派成立、對大派不成立**——`02` 當時用大派比喻時略過了這層，本檔補正。
2. **`design_vision §六` 接點表「據點在產業視圖（複用建築）」列了 `_taiwuBuildingAreas + AddTaiwuBuildingArea`**——本次釐清這條是**太吾玩家專屬軌**，**不適合**當小派據點的歸屬登記/判定。小派據點建議「mod 私有表記歸屬 + `GetBuildingBlockList` 驗建築還在」。接點表該欄宜註明「身份與建設兩條獨立軌；小派據點走 mod 私有表，非 `_taiwuBuildingAreas`」。
3. 其餘既有調查（`OrganizationInfo` 結構、`JoinOrganization` 守衛、`CreateEmptySects` 佔位、`Sect` ctor SeniorityGroupId 守衛、`CreateIntelligentCharacter` 自動入籍）本次逐字核對**全部一致、無漂移**。

---

## 8. 待釐清 / 未對實裝核對清單

- ⚠️ **mod 私有表的持久化機制**（隨存檔 slot 存自訂資料的太吾 mod 慣例）未在本次深入；屬框架層（design_vision §三 JSON 框架），影響「升格階段/據點歸屬/外交表」怎麼跨存檔保存。
- ⚠️ **空成員佔位 sect 跑 N 個月的實機行為**：理論上所有 `_sects` 月度迴圈對空成員＝空迴圈（且 15 大派佔位已驗多年），但「N 個額外空小派佔位」未實機跑多月驗證有無冷門路徑 NPE（如某處假設「sect 必有掌門」）。本調查只讀資料模型/方法體，未跑遊戲。
- ⚠️ **太吾自己 `JoinSect` 改 `OrganizationInfo` 的前端/主線副作用**（門派列表、主線判定、UI）未端到端實測。
- ⚠️ **`PlaceBuildingAtBlock` 在「非太吾村城鎮地格」放 mod 據點建築**是否被產業視圖正常顯示/可互動，未實測（`player_faction_research/01 §7.2` 已指出非家園地格建造綁 `_isTaiwuVillage`，可能需 Harmony patch；屬建設軌、本檔只判「有無據點」不涉建造流程）。
- ⚠️ **方案 2 池子用罄後的行為**（同一局誕生數超過注入的 N）：本檔建議慷慨取 N；若需 runtime 擴池只能退方案 1，其 Location/成員/count 風險見 §1.2/§1.4。
- ⚠️ `CreateSettlementMembers` 對 `Population<=0` 直接 return（`:2253`）已核對；但方案 1 若給真實 `Location` 又 `Population>0`，生成的成員 grade 分布/數量公式（`:2269-2294`，含 `worldPopulationFactor`）未逐一驗證對小派的合理性（因不建議走方案 1，未深究）。
