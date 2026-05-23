# 04 — 太吾加入門派、取得權利、指揮門派 NPC（玩家側）

> 調查領域：使用者 mod 構想第 6 點。聚焦「玩家（太吾）這一側」——玩家所屬門派的資料模型、門派身份→權利、以及「指揮門派 NPC」的入口。
> NPC 所屬/武功的資料模型見 `02_sect_member_npc_setup.md`；NPC 受命行動的底層機制見 `03_npc_directed_action.md`，本文引用、不重複細節。
>
> 版本：實裝 0.0.79.60。所有寫進結論的方法簽名/欄位均已對實裝 DLL 反編譯驗證（見文末「實裝驗證紀錄」）。grep 用舊源 `~/dev/taiwu-src/backend/`，定稿用 `Backend/*.dll`。

---

## 0. 一句話結論

太吾與 NPC 共用同一套「所屬組織」資料模型（`Character._organizationInfo`，型別 `OrganizationInfo`）；加入門派/升職位/退派全走 `OrganizationDomain` 的同一組方法，**對玩家同樣有效**，且 `EventHelper` 已暴露對應的 static mod 入口。**「玩家加入門派 + 取得最高職位」原版就有現成樣板：`EventHelper.SetTaiwuAsLeaderOfTaiwuVillage()`。** 但「指揮門派 NPC」原版唯一成熟的現成系統是**太吾村村民差遣（villager work）**，綁定在特殊組織 `OrgTemplateId==16`（太吾村），**不適用於既有大門派的 NPC**——指揮既有門派 NPC 必須由 mod 新造（接 `03` 的 NPC 行動目標機制）。

---

## 1. 玩家加入門派的既有機制

### 1.1 所屬門派的資料模型（玩家與 NPC 同一套）

- 型別 `OrganizationInfo`（struct，8 bytes 定長序列化）
  位置：實裝 `Backend/GameData.Shared.dll`，`GameData.Domains.Character.OrganizationInfo`；舊源 `backend/GameData.Shared/GameData/Domains/Character/OrganizationInfo.cs:7-17`。
  四個欄位：
  - `sbyte OrgTemplateId`：門派/組織模板 id（`Config.Organization` 索引）。`0` = 無門派/散人；`16` = 太吾村（玩家專屬勢力，見 §3.1）。
  - `sbyte Grade`：在該組織內的**品階/職位等級**（0–8，8 為掌門）。即「身份」的核心欄位。
  - `bool Principal`：是否為該 grade 的「正職」（區別於配偶附屬身份等）。
  - `short SettlementId`：該組織的具體據點 id（`-1` 表無）。
  - `static readonly OrganizationInfo None = (0,0,true,-1)`：散人值。

- 玩家 `Character` 與 NPC 用**完全相同**的單一欄位儲存：
  `Character._organizationInfo`（舊源 `backend/GameData/GameData/Domains/Character/Character.cs:394`）。
  存取器：
  - `Character.GetOrganizationInfo()`（實裝 `Character` 行 18884；舊源 `Character.cs:18970`）
  - `Character.SetOrganizationInfo(OrganizationInfo, DataContext)`（實裝行 18889；舊源 `Character.cs:18975`）—— **所屬門派唯一寫入點**，玩家/NPC 共用。
  - `Character.GetInteractionGrade()` 回傳 `_organizationInfo.Grade`（舊源 `Character.cs:4227-4233`，太吾本人特例回 0，見 §2.3）。

  ⇒ **玩家的所屬 `Organization` 與 NPC 是同一套，沒有玩家專屬的平行欄位。**

### 1.2 加入/退出/換派/升職的底層方法（玩家適用）

全在 `OrganizationDomain`（實裝 `Backend/GameData.dll`，`GameData.Domains.Organization.OrganizationDomain`；舊源 `backend/GameData/GameData/Domains/Organization/OrganizationDomain.cs`）。簽名均對實裝驗證一致：

- `JoinOrganization(context, Character, OrganizationInfo destOrgInfo)`（實裝行 717；舊源 692）
  把角色加進據點成員集合：門派走 `SectCharacter` + `Sect.GetMembers().Add(charId, grade)`，平民據點走 `CivilianSettlementCharacter`。會建立與全據點成員的關係、隨機指派師父（`SetRandomSectMentor`）、若 `grade==8 && Principal` 加掌門特徵 `405`。**注意：此方法只改成員集合，不改 `Character._organizationInfo` 本身。**
- `LeaveOrganization(context, Character, bool charIsDead)`（實裝行 777；舊源 757）：自成員集合移除、處理世襲核心職位空缺、退出 faction、解除藏寶閣守衛等。
- `ChangeOrganization(context, Character, OrganizationInfo destOrgInfo)`（實裝行 861；舊源 829-836）：**換派的標準封裝** = `LeaveOrganization` → `JoinOrganization` → `Character.SetOrganizationInfo(destOrgInfo)` → 觸發 `Events.RaiseCharacterOrganizationChanged`。NPC 入門也走它（`Sect.RecruitOrCreateLackingMembers` → `ChangeOrganization`，舊源 `Sect.cs:288`）。
- `ChangeGrade(context, Character, sbyte destGrade, bool destPrincipal)`（實裝行 889；舊源 838-926）：**升/降職位的核心**。改 `_organizationInfo`、更新成員集合 grade、`grade==8 && Principal` 加掌門特徵 `405`、處理藏寶閣守衛特徵、生命紀錄 `AddChangeGrade`，並對「貴族」職業給聲望。

  ⇒ 這幾個方法吃的就是 `Character`，**玩家也是 `Character`，所以對玩家完全有效**。沒有「僅 NPC 可入門」的限制。

### 1.3 暴露給 mod 事件腳本的 static 入口（EventHelper）

`GameData.Domains.TaiwuEvent.EventHelper.EventHelper`（實裝 `Backend/GameData.dll`；舊源 `backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/EventHelper.cs`）。mod 的事件 Lua/腳本可呼叫：

- `static void JoinOrganization(Character character, short settlementId, sbyte grade)`（實裝行 20866；舊源 19562）：
  同派只改 grade（呼叫 `ChangeGrade(...,destPrincipal:true)`），異派則構造 `targetOrgInfo` 後 `ChangeOrganization`。**這就是 mod「讓某角色（含太吾）入某據點門派並給定職位」的一行式入口。**
- `static void ChangeOrganization(Character character, OrganizationInfo destOrgInfo)`（實裝行 20888；舊源 19584）：直通 `OrganizationDomain.ChangeOrganization`。
- `static void ChangeOrganizationGrade(int charId, int changeValue)`（實裝行 20907；舊源 19603）：相對升降職位（`Clamp(grade+changeValue,0,8)`），含配偶連動 `UpdateGradeAccordingToSpouse`。
- `static void PunishSectMember(...)`、`static void JoinSpouseOrganization(...)` 等配套。

  ⇒ **「加入門派」「取得職位」這兩塊，原版已有 mod 可直接呼叫的後端 API，不需逆向私有方法。**

### 1.4 太吾預設是不是門派成員？能否中途加入別派？

- **預設不是任一既有大門派的正式弟子。** 開局太吾的所屬以劇情/出身決定；散人時 `OrgTemplateId==0`。中途透過劇情事件（如拜入某派的主線/支線）才會被 `ChangeOrganization` 設成該派成員。
- **能中途換派**：`ChangeOrganization` 本就是「先退原派再入新派」，對太吾無特殊封鎖。mod 可在任意自訂事件呼叫 `EventHelper.JoinOrganization(taiwuChar, settlementId, grade)` 讓太吾入任意據點。
- 太吾在所在據點的「門派模板」可由 `OrganizationDomain.GetOrganizationTemplateIdOfTaiwuLocation()`（舊源 `OrganizationDomain.cs:1670`）取得，常用於判斷「太吾現在站在哪個門派地盤」。

---

## 2. 門派身份 → 權利/權限模型

### 2.1 沒有正式的 RBAC「權限」物件——權利由 `Grade` + 特徵(Feature) + 認可率(ApprovingRate) 三者共同決定

舊源全庫 grep `Authority`/`Permission` 在門派語境下**無對應型別**。遊戲實際用三個維度表達「玩家在門派能做什麼」：

1. **`Grade`（職位等級 0–8）**：唯一的「身份」量。每個 grade 對應一個 `OrganizationMemberItem` 設定（`OrganizationDomain.GetOrgMemberConfig(orgInfo)`，舊源 `OrganizationDomain.cs`；由 `Config.Organization.Members[grade]` → `OrganizationMember`）。`OrganizationMemberItem` 含 `GradeName`（職位名）、`TeacherGrade`、`ExtraCombatSkillGrids`、`RestrictPrincipalAmount`、`ChildGrade`、`Clothing` 等——決定該職位的稱謂、可學武功格數、是否限員。職位名取用：`Character.cs:5296-5297`（`Config.Organization.Instance[OrgTemplateId].Name` + `GetOrgMemberConfig(...).GradeName`）。

2. **特徵 Feature（旗標式特權）**：`grade==8 && Principal` ⇒ `AddFeature(405)`（掌門特徵），見 `JoinOrganization`(舊源 712-715)、`ChangeGrade`(舊源 870-877)。藏寶閣守衛 ⇒ `settlement.GetTreasuryGuardFeatureId(grade)` 特徵（`ChangeGrade` 舊源 878-882）。**特定互動/特權靠「有沒有某 feature」開關**，這是最接近「權限」的東西。

3. **門派認可率 ApprovingRate / SectApproval（聲望式權利）**：這是太吾與門派關係最重要的「軟權利」量。
   - `Sect.CalcApprovingRate()`、`Sect.UpdateApprovalOfTaiwu(context)`（舊源 `Sect.cs:220-250`）：門派成員逐個「認可太吾」（`SectCharacter.SetApprovedTaiwu`），累積成認可率。
   - 認可率/認可效果決定太吾在該派的實質特權：
     - `SectApprovingEffectItem`（舊源 `backend/GameData/Config/SectApprovingEffectItem.cs`）：`RequirementSubstitutions`（資質替代——認可後可用其他生活技能資質頂替學功法門檻）、`CombatSkillDirectionBonuses`/`BehaviorTypeBonuses`/`PageBonuses*`（讀書/練功加成）。
     - `TaiwuDomain.GetQualificationWithSectApprovalBonus(orgTemplateId, currQ, requiredQ)`、`GetAttainmentWithSectApprovalBonus(...)`（舊源 `TaiwuDomain.cs:10229+`）：被認可後學該派武功的資質門檻可被替代。
     - `TaiwuDomain.CalcReadingSpeedSectApprovalFactor(...)`（舊源 `TaiwuDomain.cs`）：認可率 ≥400 額外 +25 讀書速度。
   - ⇒ **「玩家能不能順利學該派武功、練功多快」這類權利由認可率決定，而非職位**。
   - `SectFavorability`（舊源 `backend/GameData.Shared/.../Organization/SectFavorability.cs`）：門派間/對太吾的好感，影響敵我與互動。

### 2.2 玩家當上某職位後實際解鎖什麼

- 掌門（grade8）→ feature 405 → 解鎖掌門限定互動（門派事務/收徒/處置弟子等劇情選項以 feature/grade 為條件）。
- 各職位有 `OrganizationMemberItem` 設定的可學武功格數、稱謂、服飾。
- 太吾村（OrgTemplateId16）掌門 → 解鎖**村民差遣全套 UI**（見 §3.1），這是「職位→可指揮 NPC」唯一原版閉環。

### 2.3 重要例外：太吾本人的 `GetInteractionGrade`

`Character.cs:4227-4233`：若 `_id == TaiwuCharId` 則 `GetInteractionGrade` 回傳 **0**（非真實 grade）。意味著很多「互動門檻按 grade」的判斷對太吾本人會用 0。mod 若靠 grade 開特權需注意這一點，較穩的做法是**自掛 feature 旗標**（見 §4）。

---

## 3. 「指揮門派 NPC」的入口（重點）

### 3.1 原版唯一成熟的「玩家差遣 NPC」系統 = 太吾村村民工作（villager work）

綁定特殊組織 `OrgTemplateId==16`（太吾村，玩家自己的勢力）。村民 = 加入太吾村的 NPC，太吾為掌門。整套在 `TaiwuDomain`（實裝 `Backend/GameData.dll`，`GameData.Domains.Taiwu.TaiwuDomain`），均已對實裝驗證存在：

- 把 NPC 變村民：`AddTaiwuVillageResident(context, charId)`（實裝行 14586；舊源 `TaiwuDomain.cs:11113`）。加入太吾村也走 `OrganizationDomain.JoinOrganization`，因 `OrgTemplateId==16` 落入 `JoinOrganization` 的 civilian 分支（舊源 730-747）。
- 指派工作（核心差遣 API，前端 UI 呼叫）：
  - `SetVillagerWork(context, charId, VillagerWorkData, bool allowChild=false)`（實裝行 14080）——通用差遣。
  - `SetVillagerCollectResourceWork`（採集，14080 上方行 13840）、`SetVillagerCollectTributeWork`、`SetVillagerKeepGraveWork`、`SetVillagerIdleWork`、`SetVillagerMigrateWork`、`SetVillagerDevelopWork`（建設，13917）。
  - `SetVillagerRole(context, charId, short roleTemplateId)`（實裝行 16781）——指派村民「職務角色」（VillagerRole），配 `VillagerRoleActionSetting`（`GetVillagerRoleActionSetting`/`SetVillagerRoleActionSetting`，實裝行 3341/3281）做固定行動。
  - `MoveVillagersToWorkLocation(context)`（實裝行 14513）：把村民移到工作地點（**這是「叫 NPC 去某地」的現成位移機制**）。
- 移除/停工：`ExpelVillager(context, charId)`（實裝行 14003）、`StopVillagerWork`/`RemoveVillagerWork`。
- 狀態查詢：`GetAllVillagersStatus`、`GetVillagersAvailableForVillagerRole`、`GetWorkingVillagerCount` 等。

⇒ **這是「玩家加入勢力→當掌門→差遣 NPC 幹活/去某地」的完整原版閉環，但勢力固定是太吾村（OrgTemplateId16），NPC 必須先變成太吾村村民。它不能直接拿來指揮一個既有大門派（如少林）的 NPC。**

### 3.2 第二條現成線：太吾隊伍（Group / Teammate）

把 NPC 收為隨太吾行動的同伴：

- `EventHelper.JoinGroup(int charId, int targetCharId)`（實裝行 5143；舊源 5108）→ `DomainManager.Character.JoinGroup`。
- `EventHelper.JoinGroup(int characterId)`（實裝行 30128，**實裝新增的單參版**）→ `TaiwuDomain.JoinGroup(context, charId, showNotification)`（實裝行 9175）。
- 查詢：`EventHelper.IsInGroup`（實裝 1992 區）、`HasTeammates`、`IsTaiwuGroupFull`、`GetGroupCharIds`（`TaiwuDomain` 行 14830 區）。
- 隊友指揮 UI：`HasTeammateCommandInTaiwuGroup()`（實裝行 30804）、`OpenUpgradeTeammateCommand`（舊源 25376）。

⇒ 隊伍系統讓 NPC 跟著太吾、參與戰鬥、被「隊友指令」操作，但這是**戰術/跟隨層級的指揮**，不是「派 NPC 獨自跑去某地做事」。

### 3.3 「掌門/長老命令門派 NPC 去某地殺某人」——原版無此入口

全庫 grep `Dispatch`/`Assign`/`Order`/`Command`（門派語境）/差遣/指派/調度：**對既有大門派的成員，沒有「玩家對其下達自由行動指令」的 UI 或 API**。NPC 的自主行動由 AI（`PrioritizedActionType` 等）與門派系統驅動，不接受玩家任意指令。
⇒ 要做到「長老命弟子跑去某地殺某人」，**必須由 mod 直接寫該 NPC 的世界行動目標**——這部分的底層機制（行動目標/任務鏈/AI 覆寫）由 `03_npc_directed_action.md` 負責，本文不展開。

---

## 4. 可行性與最小切入

把 mod 構想拆三塊：

| 子目標 | 原版現成支撐 | 需新造 |
|---|---|---|
| **① 太吾加入門派** | **完全現成**：`EventHelper.JoinOrganization(taiwuChar, settlementId, grade)` / `ChangeOrganization`。NPC 與玩家共用 `OrganizationDomain`，對太吾有效。 | 只需 mod 提供「觸發加入」的事件選項 + 條件。 |
| **② 取得權利/職位** | **大部分現成**：`ChangeGrade`/`ChangeOrganizationGrade` 給 grade；`grade8&Principal` 自動掛掌門 feature 405；認可率(`UpdateApprovalOfTaiwu`)決定學功權利。 | 「職位→自訂特權」若超出原版 feature/grade 涵蓋，需 mod 自掛 feature 旗標並自行判斷（注意太吾 `GetInteractionGrade` 回 0 的特例，§2.3）。 |
| **③ 指揮門派 NPC** | **僅太吾村(OrgTemplateId16)有現成差遣系統**（§3.1）；隊伍系統提供跟隨/戰術指揮（§3.2）。 | **對既有大門派 NPC 的自由差遣＝全新造**：自訂事件選項/UI → 寫該 NPC 的行動目標（接 `03`）。 |

### 4.1 推薦最小可行路徑（MVP）

**路線 A（最快、風險最低，借太吾村框架）**——適合「玩家有自己小勢力並指揮其 NPC」：
1. 用自訂事件把太吾設成某勢力掌門：直接套原版樣板 `EventHelper.SetTaiwuAsLeaderOfTaiwuVillage()`（實裝行 30724；舊源 29428-29441 = 設 `OrgTemplateId16, Grade8, Principal` 並 `SetGroupOrganization` 同步隊伍）。
2. 把目標 NPC 變村民：`TaiwuDomain.AddTaiwuVillageResident`（或讓其 `JoinOrganization` 到太吾村據點）。
3. 用 `SetVillagerWork`/`SetVillagerRole`/`MoveVillagersToWorkLocation` 差遣 NPC 採集/建設/移動——**全是原版現成 UI/API**。
   ⇒ 「指揮 NPC」立刻可用，零新造行動系統。代價：勢力被綁成太吾村語義，NPC 要先入村。

**路線 B（貼合「加入既有門派並指揮其弟子」原始需求）**：
1. 自訂事件 → `EventHelper.JoinOrganization(taiwuChar, 目標門派settlementId, grade=8)` 讓太吾入該派並當掌門（或長老）。
2. 取得權利：靠 grade8 的 feature 405 + 拉高認可率（`Sect.UpdateApprovalOfTaiwu` / 直接設認可），或 mod 自掛自訂特權 feature。
3. 指揮該派 NPC：**原版無入口，需新造**——做一個自訂互動/事件「差遣弟子 X 去某地做某事」，在事件後端呼叫 `03` 提供的 NPC 行動目標寫入機制（如設行動目標/任務鏈/AI 覆寫）。
   ⇒ 最貼需求但 ③ 需與 `03` 整合。建議：先用「事件 → 直接搬運該 NPC（`Character` 位移）+ 觸發一個結算事件」做出最小可玩版，再逐步接 `03` 的長期行動目標。

### 4.2 一條落地順序建議
先做 ② 的旗標（用事件給太吾一個「某門派某職位」狀態：`JoinOrganization`+`ChangeGrade`，必要時自掛 feature）→ 再做 ③ 的最小指揮（自訂事件選項「差遣某 NPC 去某地」→ 後端寫該 NPC 行動目標，接 `03`）→ 最後補 ① 的入派觸發條件與 UI 包裝。

---

## 5. 待釐清問題（交棒/後續驗證）

1. **`03` 的 NPC 行動目標 API**：指揮既有門派 NPC「去某地殺某人」具體該呼叫哪個後端方法（行動目標/任務鏈/AI 覆寫）？路線 B 步驟 3 完全依賴此答案。
2. **mod 事件能否直接呼叫 `TaiwuDomain.SetVillagerWork` 系**：這些是前端 UI 用的 domain 方法，`EventHelper` 未轉發（§3 grep 證實 EventHelper 無 villager work 入口）。需確認 mod 事件後端是否能拿到 `DomainManager.Taiwu` 並直接呼叫，或須走別的橋接。
3. **太吾 `GetInteractionGrade` 回 0 的影響面**：哪些「按 grade 開放的門派互動」會因此對太吾失效？決定 ② 要不要全面改用 feature 旗標。
4. **認可率的 mod 寫入點**：是否有 `EventHelper` 級 API 可直接設/加太吾對某派的 ApprovingRate（路線 B 步驟 2 需要），或只能靠 `Sect.UpdateApprovalOfTaiwu` 緩慢累積。
5. **前端互動 UI 掛接**：自訂「差遣」選項要掛在哪個互動點（角色互動選單／門派事務介面），需查前端 `Assembly-CSharp.dll` 的互動事件選項 `InteractionEventOptionItem` 與門派 UI（本文聚焦後端，未深入前端 UI 掛接）。

---

## 實裝驗證紀錄（0.0.79.60）

以下均以 `ilspycmd -t <Type> "<DLL>"` 對實裝 DLL 反編譯，簽名/欄位與舊源一致（行號為實裝反編譯輸出行）：

- `OrganizationInfo` struct（`Backend/GameData.Shared.dll`）：四欄位 `OrgTemplateId/Grade/Principal/SettlementId` + `None` ✅ 與舊源完全一致。
- `OrganizationDomain`（`Backend/GameData.dll`）：`JoinOrganization`(717)、`LeaveOrganization`(777)、`ChangeOrganization`(861)、`ChangeGrade`(889) 簽名一致 ✅。
- `Character`（`Backend/GameData.dll`）：`GetInteractionGrade`(3601)、`GetOrganizationInfo`(18884)、`SetOrganizationInfo`(18889) ✅。
- `EventHelper`（`Backend/GameData.dll`）：`ExpelVillager`(2105)、`JoinGroup(int,int)`(5143)、`JoinOrganization`(20866)、`ChangeOrganization`(20888)、`ChangeOrganizationGrade`(20907)、`JoinGroup(int)`(30128)、`SetTaiwuAsLeaderOfTaiwuVillage`(30724)、`SetGroupOrganization`(30739)、`HasTeammateCommandInTaiwuGroup`(30804) ✅。實裝較舊源**多出單參 `JoinGroup(int characterId)`**。
- `TaiwuDomain`（`Backend/GameData.dll`）：`JoinGroup`(9175)、`IsInGroup`(9443)、`SetVillagerCollectResourceWork`(13840)、`SetVillagerWork`(14080)、`ExpelVillager`(14003)、`MoveVillagersToWorkLocation`(14513)、`AddTaiwuVillageResident`(14586)、`SetVillagerRole`(16781)、`GetVillagerRoleActionSetting`(3341) ✅。
- EventHelper grep 確認**無** `SetVillager*/VillagerWork` mod 入口（村民差遣 API 僅在 TaiwuDomain）。

> 舊源 grep 路徑：`~/dev/taiwu-src/backend/GameData/`（實作主體）；`GameData.Shared/` 多為較大的 stub/序列化骨架，實作以 `GameData/` 為準。
