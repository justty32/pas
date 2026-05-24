# 中小門派 mod｜Experiment #1（收徒與傳授）打底調查：師徒關係 + 收徒

> 建立：2026-05-24。範圍：角色間「關係」資料模型總覽、師徒關係怎麼存、能否建門派外的自由師徒、NPC 收徒、太吾收徒、收徒對關係網的影響。
> **唯一事實來源**：實裝版 **0.0.79.60** 反編譯。權威方法簽名/方法體均以 `ilspycmd -t <型別>` 反組譯 `Backend/GameData.dll` 與 `Backend/GameData.Shared.dll` 逐字確認（下文標 `(實裝核對)`）。舊參考源 `~/dev/taiwu-src/backend/`（約 0.0.76.x）僅供 grep 定位，凡與實裝有出入即標 ⚠️ 漂移。
> 建立在既有調查之上（不重複推導）：
> - `analysis/taiwu/player_faction_research/02_sect_member_npc_setup.md`（OrganizationInfo、JoinOrganization、SettlementId>=0 前提）
> - `analysis/taiwu/npc_population_research/01_dragonisland_servant_and_matchmaking_npc.md`（TryCreateGeneralRelation / ChangeFavorabilityOptional / AddHusbandOrWifeRelations）
> - `analysis/taiwu/player_faction_research/03_npc_directed_action.md`（GetRelatedCharIds(charId, 32768) 仇敵 bitflag、AdvanceMonthBegin 鉤、平行段鐵則）

---

## 0. 一句話結論

**師徒是一條獨立的雙向關係 bitflag（Mentor=2048 / Mentee=4096），完全不綁門派，可在任意兩個角色間用單一 API 建立。**「門派 mentor 機制」只是這條關係的一個自動化來源（入派時挑師父再呼同一個 `AddRelation`），不是師徒關係的儲存處。師徒關係存在關係表（`RelatedCharacters.Mentors` / `.Mentees` 兩個桶），不在 `OrganizationInfo`、也不在 `Character` 的任何欄位上。

- **建自由師徒（最省力）**：`DomainManager.Character.AddRelation(ctx, 弟子charId, 師父charId, 2048)` —— 一次呼叫自動雙向寫入（弟子→師父 = Mentor 2048；師父→弟子 = Mentee 4096）。**不需要門派、不需要先有任何關係、不需要 Harmony。** （`CharacterDomain.AddRelation`，`GameData.dll:18337`，實裝核對）
- **NPC/太吾收徒最省力路徑（含好感/生平/通知）**：`EventHelper.ApplyRelationBecomeMentor(弟子Char, 師父Char)` —— 完整封裝（建關係 + 雙向好感 +3000 + 心情變動 + 生平記錄 + 事件記錄）。`selfChar` 是弟子、`targetChar` 是師父。（`EventHelper.cs:6234`，實裝核對）
- **太吾的弟子怎麼查**：`GetRelatedCharIds(太吾charId, 4096)`（Mentees 桶）。沒有獨立「弟子名冊」結構。
- **NPC 不會自發收徒**：月度自發關係迴圈（`PeriAdvanceMonth_RelationsUpdate`）涵蓋仇敵/愛慕/情侶/夫妻/結拜/朋友/義親，**獨缺 Mentor/Mentee**。NPC 之間的師徒只從三處生：①入派自動挑師父；②事件腳本互動（拜師）；③威逼收徒。

---

## 1. 角色間「關係」資料模型總覽（需求 1）

### 1.1 全套 RelationType bitflag（實裝核對，權威）
位置：`GameData.Domains.Character.Relation.RelationType`（**在 `GameData.Shared.dll`**，純常數 + 位元工具類）。`ilspycmd -t GameData.Domains.Character.Relation.RelationType GameData.Shared.dll`：

| 常數 | 值(十進位) | 值(hex) | 中文 | 反向關係 `GetOppositeRelationType` | 單向? |
|---|---:|---|---|---|---|
| `General` | 0 | 0x0 | 一般相識 | 0 | — |
| `BloodParent` | 1 | 0x1 | 親生父母 | 2 (BloodChild) | 否 |
| `BloodChild` | 2 | 0x2 | 親生子女 | 1 | 否 |
| `BloodBrotherOrSister` | 4 | 0x4 | 親兄弟姊妹 | 4 (對稱) | 否 |
| `StepParent` | 8 | 0x8 | 繼父母 | 16 | 否 |
| `StepChild` | 16 | 0x10 | 繼子女 | 8 | 否 |
| `StepBrotherOrSister` | 32 | 0x20 | 繼兄弟姊妹 | 32 | 否 |
| `AdoptiveParent` | 64 | 0x40 | 義父母 | 128 | 否 |
| `AdoptiveChild` | 128 | 0x80 | 義子女 | 64 | 否 |
| `AdoptiveBrotherOrSister` | 256 | 0x100 | 義兄弟姊妹 | 256 | 否 |
| `SwornBrotherOrSister` | 512 | 0x200 | 結拜兄弟姊妹 | 512 | 否 |
| `HusbandOrWife` | 1024 | 0x400 | 夫妻 | 1024 | 否 |
| **`Mentor`** | **2048** | **0x800** | **師父（我拜對方為師）** | **4096 (Mentee)** | **否** |
| **`Mentee`** | **4096** | **0x1000** | **徒弟（對方拜我為師）** | **2048 (Mentor)** | **否** |
| `Friend` | 8192 | 0x2000 | 朋友 | 8192 (對稱) | 否 |
| `Adored` | 16384 | 0x4000 | 愛慕/好感 | 0 | **是（單向）** |
| `Enemy` | 32768 | 0x8000 | 仇敵 | 0 | **是（單向）** |
| `Invalid` | 65535 | 0xFFFF | 無效 | — | — |
| `Count` | 17 | — | 種類總數 | — | — |

關鍵語義（`RelationType.cs`，實裝核對）：
- **每個關係是 ushort bitflag，一對角色之間可同時持有多個 bit**（OR 疊加）。`HasRelation(currTypes, target)` = `(currTypes & target) != 0`。
- **單向關係只有 Adored(16384)、Enemy(32768)**（`IsOneWayRelation`，`:101`）：其 `GetOppositeRelationType` 回 0，所以只寫單側。其餘全是雙向（建 A→B 時自動建反向 B→A）。
- **師徒是「雙向但不對稱」**：`GetOppositeRelationType(2048)=>4096`、`(4096)=>2048`。建立 A 拜 B 為師 ⇒ A 持 Mentor(2048)指向 B；B 持 Mentee(4096)指向 A。
- 位元群組工具：`IsFamilyRelation`(`0x5FF`)、`IsFriendRelation`(`0x6200`含師徒+朋友)、`ContainBloodExclusionRelations`(`0x7FF`，血親排他)、`ContainNegativeRelations`(`0x8000`仇敵)、`ContainsNonRemovableRelations`(`0x13F`)。
- ⚠️ **drift（與既有筆記/舊源用法的修正）**：`03_npc_directed_action.md` 用 `GetRelatedCharIds(charId, 32768)` 取仇敵，正確無誤。但**舊源把 `AddRelation`/`AllowAdding*Relation` 放在 `RelationType` 類別裡**（`GameData/.../RelationType.cs`），**實裝 0.0.79.60 已把這些方法整批搬到新類別 `RelationTypeHelper`**（見 §1.3）。`RelationType` 在實裝只剩常數 + 位元判斷工具。任何舊筆記寫 `RelationType.AllowAddingMentorRelation` / `RelationType.AddRelation` 都要改成 `RelationTypeHelper.*`。

### 1.2 關係儲存結構：`RelatedCharacters`（17 個桶）
位置：`GameData.Domains.Character.Relation.RelatedCharacters`（**在 `GameData.Shared.dll`**）。每個角色一份，內含 17 個 `CharacterSet` 桶，**每種關係一個桶**（實裝核對 `GetCharacterSet`）：

```
General / BloodParents / BloodChildren / BloodBrothersAndSisters /
StepParents / StepChildren / StepBrothersAndSisters /
AdoptiveParents / AdoptiveChildren / AdoptiveBrothersAndSisters /
SwornBrothersAndSisters / HusbandsAndWives /
Mentors / Mentees / Friends / Adored / Enemies
```
- **`Mentors` 桶 = 我拜為師的人（我的師父們）；`Mentees` 桶 = 拜我為師的人（我的徒弟們）。**
- 後端以 `CharacterDomain._relatedCharIds`(`Dictionary<int, RelatedCharacters>`) 持有「某角色→各關係桶」的索引，另以 `_relations`(`Dictionary<RelationKey, RelatedCharacter>`) 持有「(charId, relatedCharId)→關係細節(RelationType bitflag + Favorability 好感 + 建立日期)」。（見 `CharacterDomain.cs:17747` `GetRelatedCharIds`、`17348` `GetRelation`）

### 1.3 增刪查 API 全盤點（實裝核對，皆 `CharacterDomain` 上的方法，`GameData.dll`）

| API | 行號 | 用途 | 備註 |
|---|---:|---|---|
| `AddRelation(ctx, charId, relatedCharId, addingType, establishmentDate=int.MinValue)` | 18337 | **建任意雙向關係**（自動寫反向 bit） | 內部 `AddRelationInternal` 兩側各一次；**不存在關係時自動 CreateRelation**（見下） |
| `ChangeRelationType(ctx, charId, relatedCharId, removingType, addingType)` | 18348 | 改單側關係 bit（移除某 bit + 加某 bit） | 單側、不自動處理反向 |
| `RemoveRelation(ctx, charId, relatedCharId)` | 18359 | 移除單側整筆關係 | — |
| `TryAddAndApplyOneWayRelation(ctx, charId, relatedCharId, relationType)` | 17973 | 加單向關係（限 16384/32768），含好感/秘聞副作用 | `[DomainMethod]`、非單向會丟例外 |
| `TryRemoveOneWayRelation(...)` | 18034 | 移除單向關係（限 16384/32768） | `[DomainMethod]` |
| `TryCreateGeneralRelation(ctx, selfChar, relatedChar)` | 18088 | 兩人若無任何關係紀錄則建一筆 General(0)（含初始好感計算） | 雙方須都是 intelligent character |
| `TryCreateRelation(ctx, charId, relatedCharId)` | 17948 | 同上的 charId 版 | — |
| `AddHusbandOrWifeRelations(ctx, charId, spouseCharId, ...)` | 18173 | 建夫妻（連帶處理子女繼親等網絡） | 高階封裝，非單純 1024 |
| `AddBloodParentRelations` / `AddStepParentRelations` / `AddAdoptiveParentRelations` | 18104/18127/18150 | 建血/繼/義親（連帶兄弟姊妹網絡） | 高階封裝 |
| `GetRelatedCharIds(charId, relationType)` | 17747 | **取某角色某關係桶的所有對象 id**（`HashSet<int>`） | **權力使喚系統的查詢基石**：傳 4096 取徒弟、2048 取師父、1 取親生父母、32768 取仇敵… |
| `GetRelation(charId, relatedCharId)` / `TryGetRelation(...)` | 17348/17353 | 取一對角色的關係細節（bitflag + 好感） | — |
| `HasRelation(charId, relatedCharId, targetRelationType)` | 17358 | 是否含某關係 | — |
| `GetAliveMentor(charId)` | 17791 | 取第一個活著的師父 id（讀 `Mentors` 桶） | 無對應 `GetAliveMentee`，但徒弟用 `GetRelatedCharIds(id,4096)` 取 |
| `GmCmd_AddRelation(ctx, charId, relatedCharId, addingType)` | 9731 | GM/除錯：加任意關係（血/繼/義/夫妻走高階封裝，其餘走通用 `AddRelation`） | **師徒(2048)走 default 分支 = `AddRelation(...,2048)`** |
| `GmCmd_RemoveRelation(ctx, charId, relatedCharId, removeType)` | 9754 | GM/除錯：移除任意關係（雙側 + 反向 bit） | — |

`RelationTypeHelper`（**實裝新類別，在 `GameData.dll`**，舊源這些在 `RelationType`）—— 驗證「能不能加某關係」：
- `RelationTypeHelper.AllowAddingRelation(charId, relatedCharId, addingType)`（`:29`）：總入口 switch。注意 **`2=>false, 4=>false, 16=>false, ...` 等「反向自動衍生型」直接擋掉**（只能加正向，反向由 `AddRelation` 自動產生）。
- `AllowAddingMentorRelation`(`:162`) / `AllowAddingMenteeRelation`(`:167`) / `AllowAddingFriendRelation`(`:172`) 都只是 `AllowAddingRelation_Direct(charId, relatedCharId, bit)`。
- `AllowAddingRelation_Direct`(`:217`)：**唯一條件 = 該關係 bit 尚未存在**（無關係紀錄→true；有但不含此 bit→true；已含此 bit→false）。**沒有年齡/血緣/距離/門派限制。**

> **對「權力使喚系統」延伸的結論（需求 1 的目的）**：任意關係都可用 `GetRelatedCharIds(發令者charId, 關係bit)` 取得「可被使喚的對象集合」。例如父子下令 = `GetRelatedCharIds(父charId, 2)`（親生子女）；師父使喚徒弟 = `GetRelatedCharIds(師父charId, 4096)`（徒弟）。所有關係共用同一查詢介面，使喚系統可做成「(關係bit, 行動) → 對名單中每人施加行動」的資料驅動原語。下令的「行動」可接 `03_npc_directed_action.md` 的 `StartCharacterPrioritizedAction` / `PersonalNeed` 機制。

---

## 2. 「師徒」關係怎麼存（需求 2）

**結論：師徒 = 獨立的雙向 bitflag（Mentor 2048 / Mentee 4096），存在關係表的 `Mentors`/`Mentees` 桶，與門派完全解耦。** 門派 mentor 機制只是「入派時自動替你挑一位師父並呼叫同一個 `AddRelation`」的自動化來源。

### 2.1 `JoinOrganization` 內「設師父」那段到底寫了什麼（實裝核對）
`OrganizationDomain.JoinOrganization`（`GameData.dll:717`）。SettlementId<0 直接 return（既有筆記已記）。進 Sect 分支後（`:726`），在登記成員、建關係、加特性之後：
```csharp
// OrganizationDomain.cs:741-743 (實裝)
OrganizationMemberItem orgMemberConfig = GetOrgMemberConfig(destOrgInfo);
short mentorSeniorityId = SetRandomSectMentor(context, id, destOrgInfo, members, orgMemberConfig.TeacherGrade);
TryBecomeSectMonk(context, character, sect, orgMemberConfig, mentorSeniorityId);
```
—— 「設師父」= 呼叫 `SetRandomSectMentor`，吃的是 **該職位 config 的 `OrganizationMemberItem.TeacherGrade`**（師父應有的職階）。

### 2.2 `SetRandomSectMentor` 全文（實裝核對，`OrganizationDomain.cs:1863`）
```csharp
private short SetRandomSectMentor(ctx, int charId, OrganizationInfo orgInfo, OrgMemberCollection sectMembers, sbyte mentorGrade)
{
    if (mentorGrade < 0) return -1;                                  // ★TeacherGrade=-1 → 不設師父，直接跳過
    // (1) 已有師父且師父也在本派、職階夠高 → 沿用，不另設
    HashSet<int> existing = DomainManager.Character.GetRelatedCharIds(charId, 2048); // 讀 Mentors 桶
    foreach (int item in existing) { ... if 同派且 Grade>=mentorGrade → return 師父法號SeniorityId; }
    // (2) 否則從 mentorGrade 起、逐階往上找「影響力最高、成年、未被綁架」的成員當師父
    while (mentorGrade < 9) {
        HashSet<int> candidates = sectMembers.GetMembers(mentorGrade);
        if (candidates.Count > 0) {
            // 取 InfluencePower 最高者 num2
            if (num2 >= 0 && RelationTypeHelper.AllowAddingMentorRelation(charId, num2)) {
                DomainManager.Character.AddRelation(context, charId, num2, 2048);   // ★關鍵：就是通用 AddRelation(...,2048)
                return element_Objects2.GetMonasticTitle().SeniorityId;
            }
        }
        mentorGrade++;
    }
    return -1;
}
```
**重點**：
1. 師徒關係最終就是 `AddRelation(ctx, charId, mentorId, 2048)` —— 與自由師徒走同一條路、同一個資料表。沒有「門派專屬師徒表」。
2. `mentorGrade = OrganizationMemberItem.TeacherGrade`，**`< 0` 直接 return -1（不設師父）**。所以小門派只要把職位 config 的 `TeacherGrade` 設成 -1，入派就不會被強制配師父（留給玩家/mod 自行收徒）。
3. 回傳值是「師父的僧侶法號字輩 id」，僅給 `TryBecomeSectMonk` 用（世俗派 `ProbOfBecomingMonk=0` 不受影響）。

### 2.3 全派重整師徒：`UpdateAllMentorsAndMenteesInSect`（實裝核對，`OrganizationDomain.cs:1117`）
遍歷 sect 各職階成員，每人都呼一次 `SetRandomSectMentor(...)`。被 `:1482`（在 sect 流程內）呼叫。對 mod 的意義：**門派每次重整成員時可能重配師父**，若小派不想要這行為，把所有職位 `TeacherGrade=-1` 即可全程關閉。

### 2.4 Character / OrganizationInfo 上有無 mentor 欄位？
**沒有。** `OrganizationInfo` 只有 `{OrgTemplateId, Grade, Principal, SettlementId}`（既有筆記 `02_sect_member_npc_setup.md` §1.1 已記）。`Character` 上沒有 mentor/apprentice 欄位 —— 師徒純粹活在關係表（`Mentors`/`Mentees` 桶）。`Character.GetAliveMentor`（透過 `CharacterDomain`）也是讀關係桶。

---

## 3. 門派外的「自由師徒」能不能建（需求 3）

**能，且最理想 —— 師徒是獨立 bitflag，建立完全不需要門派。**

最小建立（後端，主執行緒）：
```csharp
// 弟子拜師父為師：弟子→師父 Mentor(2048)，自動回寫 師父→弟子 Mentee(4096)
DomainManager.Character.AddRelation(context, 弟子charId, 師父charId, 2048);
```
依據（皆實裝核對）：
- `AddRelation`（`CharacterDomain.cs:18337`）：
  ```csharp
  AddRelationInternal(ctx, charId, relatedCharId, addingType, date);
  ushort opp = RelationType.GetOppositeRelationType(addingType);   // 2048 → 4096
  AddRelationInternal(ctx, relatedCharId, charId, opp, date);      // 自動回寫反向
  ```
- `AddRelationInternal`（`:19014`）：**關係紀錄不存在時走 `CreateRelation` 自動新建**（含初始好感），存在時 OR 進新 bit。⇒ **兩個素不相識的角色也能直接建師徒，不必先 `TryCreateGeneralRelation`。**
- 限制（`RelationTypeHelper.AllowAddingMentorRelation` → `AllowAddingRelation_Direct`，`RelationTypeHelper.cs:162/217`）：**只要尚未是師徒即可**。無年齡、無血緣排他、無門派、無距離限制（這些限制是「門派挑師父」或「事件腳本」自己加的，不在關係層）。

> **對中小門派「小型階段」的結論**：design_vision 設想「小型門派 = 只是師徒關係、可能還沒 sect」—— **這在引擎層完全成立**。創派者收徒 = 對每個徒弟 `AddRelation(徒弟, 創派者, 2048)`，全程不需要 OrganizationInfo / Sect / SettlementId。等升格成「中型門派」再走 `02_sect_member_npc_setup.md` 的佔位 Sect + JoinOrganization 路線把師徒們正式入派（入派時若 `TeacherGrade>=0` 還會自動把同派低階者再配給高階者當師父，可能與既有自由師徒疊加；要乾淨就 `TeacherGrade=-1`）。

---

## 4. NPC 收徒行為（需求 4）

### 4.1 NPC 不會「自發」結成自由師徒
月度自發關係迴圈 `Character.PeriAdvanceMonth_RelationsUpdate`（實裝 `GameData.dll:17807`；舊源 `Character.cs:17889`，邏輯一致）逐一嘗試以下關係（`GetStartOrEndRelationTarget(random, index, 候選桶, ...)`）：

| index | 關係 | bit |
|---:|---|---|
| 0/1 | 結/解仇敵 | 32768 |
| 2 | 結愛慕 | 16384 |
| 3/4 | 結/分手情侶 | (16384) |
| 5/12 | 結/離夫妻 | 1024 |
| 6/7 | 結/絕朋友 | 8192 |
| 8/9 | 結/絕結拜 | 512 |
| 10 | 認義父母 | 64 |
| 11 | 收義子女 | 128 |

**完全沒有 Mentor(2048)/Mentee(4096) 的自發分支**（實裝 `ComplementPeriAdvanceMonth_RelationsUpdate` 的 switch 也只有 64/128/512/1024/8192/16384/32768 案例）。⇒ **NPC 不會在過月時自己拜師/收徒（門派外）。** 這是 mod 必須自己驅動收徒的根因。

### 4.2 NPC 之間師徒的三個既有來源（實裝核對）
1. **入派自動配師父**：§2.2 的 `SetRandomSectMentor`（入派 `JoinOrganization:742` + 全派重整 `UpdateAllMentorsAndMenteesInSect`）。受職位 config `TeacherGrade` 控制。
2. **事件腳本互動（拜師/穿針引線）**：`EventHelper.ApplyStartRelationByThreadNeedle(charIdA, charIdB, 2048, succeed, isBothWayRelation)`（`EventHelper.cs:8455`，實裝核對）。`relationType=2048` 時 `if (succeed) ApplyRelationBecomeMentor(element, element2)`（`:8501-8506`）。`charIdA` 成為 `charIdB` 的徒弟。對應「穿針引線」類角色互動事件。
3. **威逼收徒**：`EventHelper.ApplyAddMentorByThreatening(selfCharId, threatenedCharId, nominatedCharId)`（`EventHelper.cs:8085`，實裝核對）：被威逼者 `threatenedCharId` 被迫拜 `nominatedCharId` 為師 ——
   ```csharp
   if (... && RelationTypeHelper.AllowAddingMentorRelation(threatenedCharId, nominatedCharId)) {
       DomainManager.Character.AddRelation(MainThreadDataContext, threatenedCharId, nominatedCharId, 2048, currDate);
       lifeRecordCollection.AddAddMentorByThreatened(...);  // 生平記錄 451
   }
   ```
   解除版 `ApplySeverMentorByThreatening`（`:8242` 區段，生平 454）。

### 4.3 mod 怎麼觸發/模擬 NPC 收徒（最省力）
- **直接、確定**：在 `RegisterHandler_AdvanceMonthBegin` 主執行緒事件鉤裡，對「創派者→候選徒弟」呼 `EventHelper.ApplyRelationBecomeMentor(徒弟Char, 創派者Char)`（含好感/生平/通知，最自然）；或最精簡呼 `DomainManager.Character.AddRelation(ctx, 徒弟charId, 創派者charId, 2048)`（只建關係，無副作用）。
- **無需 Harmony**：以上全是公開方法。執行緒安全同 `03_npc_directed_action.md` §7：把所有關係寫入放進 `AdvanceMonthBegin`（主執行緒），勿在過月平行段（worker thread）寫關係表。
- ⚠️ 既有「收徒事件 / 月度行為負責收徒」**查無**：`PrioritizedAction` 22 種、`GeneralAction` 各類、月度行動表都沒有「收徒/拜師」專屬 action（`GeneralAction/TeachRandom/` 只是「教武功/教生活技能」TeachCombatSkillAction/TeachLifeSkillAction，是已成師徒後的傳授行為，不是收徒）。⇒ **收徒這個「動作」在遊戲裡不是 NPC AI 自主行為，只透過上述事件/門派/威逼三管道發生。** mod 要 NPC 主動收徒就得自己驅動（如 4.3 第一點）。

---

## 5. 太吾收徒（需求 5）

### 5.1 太吾收徒入口
- **事件互動驅動，非硬編碼系統功能。** 太吾收徒/拜師走的是角色互動事件腳本（`Event/EventLib/Taiwu_EventPackage_CharacterInteraction_Relate.dll` 等「relate/穿針引線」互動），事件腳本透過字串鍵反射呼叫 `EventHelper.ApplyStartRelationByThreadNeedle(..., 2048, ...)` → `ApplyRelationBecomeMentor`。前端 `Assembly-CSharp.dll` 未硬編收徒邏輯（grep 無 BecomeMentor/收徒 符號），確認是資料驅動。⚠️ 事件腳本本身（`.twes` 二進位）未逐一反組譯，但後端落點明確。
- **特例（太吾自動為師）**：`EventHelper.BecomeBuddhistMonk`（`:18460`）—— 角色出家時若 `AllowAddingMentorRelation(角色, 太吾)` 就 `AddRelation(角色, 太吾, 2048)`（角色拜太吾為師）。屬劇情特例，非一般收徒入口。
- ⚠️ **村民差遣**：未找到「差遣村民去收徒」的專屬入口；村民職務系統（`VillagerRoleArrangementAction` 等）與收徒無關。太吾收村民為徒仍走上述關係互動。

### 5.2 太吾的弟子怎麼被記錄
**就是關係表的 Mentee(4096) 桶，沒有獨立弟子名冊。**
- 太吾的徒弟集合 = `DomainManager.Character.GetRelatedCharIds(太吾charId, 4096)`（Mentees 桶）。
- 太吾的師父集合 = `GetRelatedCharIds(太吾charId, 2048)`（Mentors 桶）。
- 拜師當下會寫生平：`LifeRecordCollection.AddGetMentor`（生平 type `GetMentor=467`，`Config/LifeRecord.cs:949`）；解除走 `AddSeverMentor`（471）。

### 5.3 解除全部師徒（mod 收尾可能用到）
`EventHelper.EndAllMentorAndMenteeRelations(charId, orgTemplateId)`（`EventHelper.cs:20931`，實裝核對）：把 charId 的所有 Mentor(2048) 與 Mentee(4096) 關係雙向 `ChangeRelationType(...,0)` 清掉。出師/逐出師門時用。

---

## 6. 收徒對 NPC 關係聯繫的影響（需求 6）

**建立師徒會自動拉好感並登記雙向關係。** 用 `ApplyRelationBecomeMentor`（=事件級收徒）時的完整副作用（`Character.ApplyAddRelation_Mentor`，`GameData.dll:18761`，實裝核對逐字）：
```csharp
public static void ApplyAddRelation_Mentor(ctx, selfChar, targetChar, charBehaviorType, selfIsTaiwuPeople, targetIsTaiwuPeople) {
    if (RelationTypeHelper.AllowAddingMentorRelation(self.id, target.id)) {       // 尚未是師徒
        DomainManager.Character.AddRelation(ctx, self.id, target.id, 2048);       // ★建雙向：self→target Mentor, target→self Mentee
        DomainManager.Character.ChangeFavorabilityOptionalRepeatedEvent(ctx, self, target, 3000);   // ★self 對 target 好感 +3000
        DomainManager.Character.ChangeFavorabilityOptionalRepeatedEvent(ctx, target, self, 3000);   // ★target 對 self 好感 +3000
        self.ChangeHappiness(ctx, BecomeMentorHappinessChange[charBehaviorType]);     // 心情變動（依道德傾向，[0,5,10,-5,0]）
        target.ChangeHappiness(ctx, BecomeMentorHappinessChange[target.behaviorType]);
        lifeRecordCollection.AddGetMentor(self.id, currDate, target.id, location);    // ★生平記錄 467
    }
}
```
要點：
- **雙向關係**：一次建立 `self.Mentors += target`、`target.Mentees += self`（`AddRelation` 自動回寫反向，§3）。`self` = 徒弟、`target` = 師父。
- **雙向好感各 +3000**（`BecomeMentorFavorabilityChange = 3000`，`AiHelper.cs:952`；十進位 3000 約等好感一檔，正向）。
- **心情變動**依師徒雙方道德傾向（`BecomeMentorHappinessChange[5] = {0,5,10,-5,0}`，`AiHelper.cs:934`）。
- **生平記錄**雙方各留痕。
- 解除（`ApplyEndRelation_Mentor`，`:18784`）對稱地各 −3000 好感、−心情、寫 `AddSeverMentor`。

> 注意：若用「最精簡」的 `AddRelation(ctx, 徒弟, 師父, 2048)` 直接建（§3），**只寫關係 bit + 內部初始好感**，不會額外 +3000、不寫生平/通知。要「收徒自動拉好感、像遊戲原生」就用 `ApplyRelationBecomeMentor`（或 `ApplyStartRelationByThreadNeedle`）。要「靜默建關係」就用 `AddRelation`。

---

## 7. 對 Experiment #1（收徒與傳授）的接點彙整

| 需求 | 最省力做法 | 錨點 | Harmony? |
|---|---|---|---|
| 創派者收徒（自由師徒，無門派） | `EventHelper.ApplyRelationBecomeMentor(徒弟Char, 師父Char)`（含好感/生平）或 `AddRelation(ctx, 徒弟, 師父, 2048)`（靜默） | `EventHelper.cs:6234` / `CharacterDomain.cs:18337` | 否 |
| 太吾收徒 | 同上（太吾當 targetChar） | 同上 | 否 |
| 列出某人的徒弟 | `GetRelatedCharIds(charId, 4096)` | `CharacterDomain.cs:17747` | 否 |
| 列出某人的師父 | `GetRelatedCharIds(charId, 2048)` / `GetAliveMentor(charId)` | `:17747` / `:17791` | 否 |
| 出師/逐出師門 | `EventHelper.ApplyRelationSeverMentor(...)` 或 `EndAllMentorAndMenteeRelations(charId, org)` | `EventHelper.cs:6247` / `:20931` | 否 |
| 傳授武功（已成師徒後） | `GeneralAction/TeachRandom/TeachCombatSkillAction`、或直接 `CharacterDomain.LearnCombatSkill`（見 `02_sect_member_npc_setup.md` §2.3） | — | 否 |
| 升格中型門派時正式入派 | `JoinOrganization` + 佔位 Sect（`02_sect_member_npc_setup.md`）；想避免自動配師父就 `OrganizationMemberItem.TeacherGrade=-1` | `OrganizationDomain.cs:717` | 否 |
| 安全注入時機 | 全部放 `RegisterHandler_AdvanceMonthBegin`（主執行緒），勿在過月平行段寫關係 | `03_npc_directed_action.md` §7 | — |

**全部六項皆無需 Harmony patch、無需碰序列化**（師徒是引擎既有的可序列化關係 bit，存檔相容）。這對「做成 JSON 資料驅動框架」極有利：收徒/出師可表達成「(發起者, 對象, 關係=2048, 建/解) + 是否走完整副作用」的純資料原語。

---

## 8. 已對實裝 DLL（0.0.79.60）逐字核對清單
- `RelationType`（常數表 + 位元工具，`GameData.Shared.dll`）—— 全 17 種 bitflag、`GetOppositeRelationType`、`IsOneWayRelation`
- `RelatedCharacters`（17 桶含 `Mentors`/`Mentees`，`GameData.Shared.dll`）—— `GetCharacterSet` switch
- `RelationTypeHelper`（**新類別，`GameData.dll`**）—— `AllowAddingRelation` switch、`AllowAddingMentorRelation`、`AllowAddingRelation_Direct`
- `CharacterDomain.AddRelation`/`AddRelationInternal`/`CreateRelation`/`ChangeRelationType`/`RemoveRelation`/`GetRelatedCharIds`/`GetAliveMentor`/`TryAddAndApplyOneWayRelation`/`TryCreateGeneralRelation`/`GmCmd_AddRelation`/`GmCmd_RemoveRelation`
- `CharacterDomain.PeriAdvanceMonth_RelationsUpdate` + `ComplementPeriAdvanceMonth_RelationsUpdate`（確認無 Mentor 自發分支）
- `OrganizationDomain.JoinOrganization`（設師父段）/ `SetRandomSectMentor` / `UpdateAllMentorsAndMenteesInSect`
- `Character.ApplyAddRelation_Mentor` / `ApplyEndRelation_Mentor`
- `EventHelper.ApplyRelationBecomeMentor` / `ApplyRelationSeverMentor` / `ApplyStartRelationByThreadNeedle`(2048分支) / `ApplyAddMentorByThreatening` / `BecomeBuddhistMonk` / `EndAllMentorAndMenteeRelations`

## 9. 待釐清 / 未核對清單
1. ⚠️ **`AllowAdding*` / `AddRelation` 由 `RelationType` 搬到 `RelationTypeHelper`**（實裝 vs 舊源的明確漂移）已確認；但 `RelationTypeHelper` 是否還有其他舊源沒有的新方法未逐一比對。
2. **事件腳本層（`.twes`）的收徒互動條件**（年齡/好感/門派門檻、太吾收徒的前置）未反組譯確認 —— 後端落點 `ApplyStartRelationByThreadNeedle`/`ApplyRelationBecomeMentor` 確定，但「玩家點哪個選項、需滿足什麼」藏在二進位事件腳本。
3. **村民差遣是否真的無收徒入口** —— 以 grep + 前端符號掃描判定「無」，未窮舉所有月度行動 config，屬負面結論，信心中等。
4. **`ChangeFavorabilityOptionalRepeatedEvent` 與 `ChangeFavorabilityOptional` 差異**（後者見既有龍島筆記）未細查 —— 兩者都用於好感變動，前者疑為「可重複觸發事件」版；對收徒結論無影響。
5. **入派自動配師父與既有自由師徒的疊加行為**：若 mod 先建自由師徒、之後該徒弟入派且職位 `TeacherGrade>=0`，`SetRandomSectMentor` 的 (1) 分支會偵測「已有同派師父」而沿用，但「師父不在本派」時是否仍會「再配一個本派師父」造成一人多師 —— 邏輯上會（Mentors 是集合、可多筆），未實機驗證。建議小派一律 `TeacherGrade=-1` 規避。
6. **`AddRelation` 在過月平行段呼叫的崩潰風險**未實測（理論依 `03_npc_directed_action.md` §7 鐵則，只在主執行緒/事件鉤呼叫即安全）。
