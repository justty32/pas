# 門派成員與 NPC 屬性設置（②，涵蓋使用者需求 2＋4）

> 建立：2026-05-23。調查領域：小門派的 NPC 該怎麼設——所屬門派、會用武功、職位/資歷、能否掛在特殊建築而非佔地圖聚落槽、輕量化最小切入點。
> **唯一事實來源**：方法簽名/方法體已對實裝版 0.0.79.60 反編譯驗證（`Backend/GameData.dll`、`Backend/GameData.Shared.dll`，`ilspycmd -t`）；型別關係/grep 用較舊參考源 `~/dev/taiwu-src/backend/`。下文凡標 `(實裝核對)` 者即已對實裝 DLL 比對一致。
> 與並行 session 零交集；未動 `session_log.md`、`details/`、`answers/`。`new_sect_mod/`（陳家堡）只當索引引用。

---

## 0. 一句話結論

NPC 的「所屬門派」就是 `Character` 內嵌的一個 **8-byte struct `OrganizationInfo` = {OrgTemplateId, Grade, Principal, SettlementId}**。
- **所屬門派** = `OrgTemplateId`（門派 config id，如 42）；
- **職位/資歷** = `Grade`（sbyte），它索引門派 config 的 `Members[]` 陣列拿到該職位的 `OrganizationMemberItem`（含稱謂、武學、屬性加成）；
- **會用武功** = 由該職位 `OrganizationMemberItem.CombatSkills` 列表決定，每筆解析成「門派+類型」的武學樹，學到 0..MaxGrade；
- **根據地** = `SettlementId`（執行期聚落實體 id，−1＝無）。

關鍵輕量化發現：`IsSect=true` 的門派在開局 **一定** 會由 `CreateEmptySects` 生出一個佔位 `Sect` 實體（`Location.AreaId = -1`，不在地圖上），因此 **不必上地圖聚落槽** 就有合法 `SettlementId` 可供 NPC 掛靠。商會不是獨立組織型別（是平民聚落的某身份），所以「掛在建築上的門派」沒有現成資料模型；輕量小派的正解是「**第 16 個非大派 Sect + 不上地圖（停在 placeholder）**」而非「掛建築」。

---

## 1. NPC 所屬門派／組織

### 1.1 資料模型：`OrganizationInfo`（內嵌於 Character）
位置：`backend/GameData/GameData/Domains/Character/OrganizationInfo.cs`（型別實際在 **GameData.Shared.dll**，非 GameData.dll）。 (實裝核對)

```csharp
public struct OrganizationInfo(sbyte orgTemplateId, sbyte grade, bool principal = true, short settlementId = -1)
{
    public sbyte OrgTemplateId;   // 門派 config id（= OrganizationItem.TemplateId，如 42）
    public sbyte Grade;           // 職位/資歷等級，索引 OrganizationItem.Members[Grade]
    public bool  Principal;       // 是否「正式成員/本人」（false = 配偶之類的附帶身份）
    public short SettlementId;    // 執行期聚落實體 id（-1 = 無根據地，不在任何聚落）
    public static readonly OrganizationInfo None = new OrganizationInfo(0, 0, true, -1);

    // 實裝版多了這個（舊源沒有）：Grade 如何取得職位定義
    public OrganizationMemberItem GetOrgMemberConfig() {
        short index = Config.Organization.Instance[OrgTemplateId].Members[Grade];
        return OrganizationMember.Instance[index];
    }
}
```
- 序列化固定 8 bytes（`OrgTemplateId`,`Grade`,`Principal` 各 1 + `SettlementId` 2 + padding）。
- `Character` 內以 fixed field offset 14 存放（`Character.cs:96 OrganizationInfo_Offset = 14u`、`OrganizationInfo_Size = 8`）。 (實裝核對)

### 1.2 讀寫欄位
- 取得：`Character.GetOrganizationInfo()`（`Character.cs:18970`）。
- 設定：`Character.SetOrganizationInfo(OrganizationInfo, DataContext)`（`Character.cs:18975`）——這只改 Character 上的欄位，**不會** 把人登記進聚落成員集合。 (實裝核對)

### 1.3 兩條設定途徑

**(A) 角色生成時就指定**（最常見、最省事）
- 入口：`CharacterDomain.CreateIntelligentCharacter(ctx, ref IntelligentCharacterCreationInfo info)`（`CharacterDomain.cs:26387`），其 `info.OrgInfo` 帶進門派資訊。
- 實作核心：`Character.OfflineCreateIntelligentCharacter(...)`（`Character.cs:23017`）：
  - `Character.cs:23025` 取 `orgTemplateId = info.OrgInfo.OrgTemplateId`；
  - `Character.cs:23032-23034` 由此推出 `orgMemberConfig = OrganizationMember.Instance[GetMemberId(orgTemplateId, info.OrgInfo.Grade)]`；
  - `Character.cs:23035` `_organizationInfo = info.OrgInfo`（直接寫入欄位）。
- 收尾：`CharacterDomain.ComplementCreateIntelligentCharacter(...)`（`CharacterDomain.cs:26436`）在 `:26458` 呼 `JoinOrganization(ctx, character, character.GetOrganizationInfo())` ——這一步才把人登記進聚落成員集合。

**(B) 運行時加入／轉派**（已存在的 NPC 後天加入門派）
- `OrganizationDomain.JoinSect(ctx, character, destOrgInfo)`（`OrganizationDomain.cs:702`，實裝） = `LeaveOrganization` → `JoinOrganization` → `SetOrganizationInfo` → 寫生平記錄 → `RaiseCharacterOrganizationChanged`。 (實裝核對)
- 通用版：`OrganizationDomain.ChangeOrganization(...)`（`OrganizationDomain.cs:861` 實裝 / 舊源 829）做同樣三步但不寫「加入門派成功」生平。
- 底層：`OrganizationDomain.JoinOrganization(ctx, character, destOrgInfo)`（`OrganizationDomain.cs:717` 實裝 / 舊源 692）。

> 結論：**(A) 用 `IntelligentCharacterCreationInfo.OrgInfo` 在生成時帶；(B) 用 `JoinSect`/`ChangeOrganization` 在運行時切。** 兩者最終都落到 `SetOrganizationInfo`（寫欄位）＋`JoinOrganization`（登記聚落集合）。

### 1.4 ⚠️ `JoinOrganization` 的硬性前提：`SettlementId >= 0`
`OrganizationDomain.JoinOrganization`（`:717`）開頭即： (實裝核對)
```csharp
if (destOrgInfo.SettlementId < 0) return;   // SettlementId 無效就直接 return，不登記任何集合
```
- `SettlementId >= 0` 才會：建 `SectCharacter`、加入 `sect.GetMembers()`（`OrgMemberCollection`）、與全聚落成員建關係、`TryAddSectMemberFeature`、設師父、`TryBecomeSectMonk`。
- 若 `OrgTemplateId` 的 `IsSect=true` 走 sect 分支（`_sects[SettlementId]`）；否則走 `CivilianSettlement` 分支。
- **言外之意**：要讓 NPC「真正屬於某門派並被門派系統認得」，必須給一個合法 `SettlementId`。這正是下面第 4 節「能否不佔聚落」的關鍵約束。

---

## 2. NPC 會用的武功

### 2.1 武功容器
- 角色已學武學列表：`Character._learnedCombatSkills`（`List<short>`，`Character.cs:550`）—— 存的是 skill template id。
- 實際武學狀態（頁數、修煉度等）由 **CombatSkill domain** 持有：生成時 `CharacterDomain.ComplementCreateIntelligentCharacter` 在 `:26450` 呼 `DomainManager.CombatSkill.RegisterCombatSkills(charId, mod.CombatSkills)`，把 `mod.CombatSkills`（一批 `GameData.Domains.CombatSkill.CombatSkill`）登記給角色。

### 2.2 門派 config → 成員武學的指派路徑（生成時）
入口：`Character.OfflineAddPresetOrgMemberCombatSkills(ctx, mod, orgConfig, orgMemberConfig, ageInfluence)`（`Character.cs:24274`），在 `OfflineCreateIntelligentCharacter` 的 `:23150` 被呼（受 `info.InitializeSectSkills` 旗標控制）。
核心迴圈在 `OfflineAddPresetOrgMemberCombatSkillsInternal`（`Character.cs:24301`）：
```csharp
foreach (PresetOrgMemberCombatSkill presetSkill in orgMemberConfig.CombatSkills) {
    CombatSkillItem presetSkillCfg = Config.CombatSkill.Instance[presetSkill.SkillGroupId];
    IReadOnlyList<CombatSkillItem> group =
        CombatSkillDomain.GetLearnableCombatSkills(presetSkillCfg.SectId, presetSkillCfg.Type); // 門派+類型 → 武學樹
    int maxGrade = Clamp(presetSkill.MaxGrade * ageInfluence / 100, 0, group.Count - 1);
    for (int skillGrade = 0; skillGrade <= maxGrade; skillGrade++) {
        CombatSkillItem skillConfig = group[skillGrade];
        charCombatSkills.Add(new CombatSkill(-1, skillConfig.TemplateId, readingState));
        _learnedCombatSkills.Add(skillConfig.TemplateId);
        // 機率附帶秘笈、最配武器
    }
}
```
- `PresetOrgMemberCombatSkill`（`backend/GameData/Config/ConfigCells/Character/PresetOrgMemberCombatSkill.cs:6`）= `{ short SkillGroupId, sbyte MaxGrade }`。
- `GetLearnableCombatSkills(orgTemplateId, combatSkillType)`（`CombatSkillDomain.cs:136`）= 查 `_learnableCombatSkillsCache[orgTemplateId][combatSkillType]` —— 即「某門派某武學類型」的可學武學樹（依品級排序）。 (實裝核對：方法體在實裝 DLL 同為快取查表)

> **武功怎麼依門派配**：門派的「武學樹」其實掛在 **`OrganizationMemberItem.CombatSkills`（每個職位各一份）**，每筆 `PresetOrgMemberCombatSkill` 用 `SkillGroupId` 指向某 `CombatSkillItem`，由其 `SectId`+`Type` 換到該門派該類型的武學樹，成員學到 `0..MaxGrade` 品級。**所以「門派武學」=「各職位 config 列的 CombatSkills 之集合」**，不是門派 config 上的單一欄位。

### 2.3 運行時學武（NPC 過月時自學門派武功）
- `Character.GetCombatSkillToLearn()`（`Character.cs:8732`）：以 `OrganizationDomain.GetOrgMemberConfig(_organizationInfo)`（即「我目前職位」的 config）的 `CombatSkills` 為清單，逐筆找下一個還沒學的 skill / 還沒讀完的頁，回傳給過月供應流程去學。生活技能同理 `GetLifeSkillToLearn()`（`Character.cs:8676`）。
- 主動學單一武學的 API：`CharacterDomain.LearnCombatSkill(ctx, charId, skillTemplateId, readingState)`（`CharacterDomain.cs:3984`）。
- （太吾村村民 id=16 是特例：武功改抄該地州 `MapState.SectID` 的 grade-6 成員 config，見 `Character.cs:8735-8744`。輕量小派不會碰到。）

---

## 3. NPC 身份／職位與資歷

### 3.1 `Grade` = 職位/資歷等級（核心）
- `Grade`（`OrganizationInfo.Grade`，sbyte）就是「在門派裡的職階」。它索引門派 config：
  `OrganizationItem.Members`（`short[]`，`OrganizationItem.cs:71`）—— `Members[Grade]` 給出該職階對應的 `OrganizationMember` 表 id，再 `OrganizationMember.Instance[id]` 取得 `OrganizationMemberItem`。
- 門派最高職階：生成時 `maxGrade = (orgTemplateId != 16) ? 8 : 7`（`OrganizationDomain.cs:2189`）——門派最多 0..8 共 9 階；掌門通常是 Grade 8（`JoinOrganization` 在 `:712` 對 `Grade==8 && Principal` 加 feature 405「掌門」）。

### 3.2 職位定義：`OrganizationMemberItem`
位置：`backend/GameData/Config/OrganizationMemberItem.cs`。每一列定義「某門派某職階」的完整模板，關鍵欄位：
- `GradeName`：職階稱謂（走 `OrganizationMember_language` 語言表）——這就是「掌門/長老/弟子」之類的顯示名。
- `Organization`(sbyte)、`Grade`(sbyte)：這列屬於哪個門派的哪一階（元資料）。
- `Amount / UpAmount / DownAmount / RestrictPrincipalAmount`：該職階生成幾人、人數上限。
- `CombatSkills`(List<PresetOrgMemberCombatSkill>)、`CombatSkillsAdjust[14]`、`ExtraCombatSkillGrids[5]`、`LifeSkillsAdjust[16]`、`MainAttributesAdjust`：該職階的武學/技能/屬性配置。
- `Neili / ConsummateLevel / ExpPerMonth / ContributionPerMonth / Fame`：實力與貢獻。
- `Gender / SurnameId / InitialAges[4]`、`ChildGrade / BrotherGrade / TeacherGrade / RejoinGrade`：性別限制、姓氏、初始年齡、家族與師徒職階關係。
- `IdentityInteractConfig`(List<sbyte>)、`IdentityActiveAge`：身份互動（商人身份就藏在這——見 §4.2）。
- `MonasticTitleSuffixes[gender]`、`ProbOfBecomingMonk`、`MonkType`：僧侶/道士法號相關（見 §3.3）。
- `Equipment[8] / Clothing / Inventory / DropResources / PreferProfessions`：裝備、隨身物、掉落、職業傾向。

`OrganizationInfo.ToString()`（實裝）顯示名 = `門派名 + GradeName`（`Principal=false` 時改用 `SpouseAnonymousTitles`）。 (實裝核對)

### 3.3 `SeniorityGroupId` 與僧侶法號 —— 修正「-1 會崩」的說法
- `OrganizationItem.SeniorityGroupId`（sbyte，`OrganizationItem.cs:31`，預設 −1）= 「資歷字輩組」，**只服務僧侶/道士派的法號生成**。
- 取值僅 0..3 合法（0 少林、1 峨眉、2 武當、3 燃山），其餘值 `GetSeniorityRange` / `GetMonasticTitleSuffixRange` 會 **拋 Exception**（`OrganizationDomain.cs:3651 / 3671`，實裝同此 `_ => throw new Exception(...)`）。 (實裝核對)
- **但 `Sect` 建構子有防護**：`Sect(...)`（`Sect.cs:147`）`if (orgConfig.SeniorityGroupId >= 0) {...} else { _minSeniorityId = -1; _availableMonasticTitleSuffixIds = new List<short>(); }`（`Sect.cs:151/167`）——**SeniorityGroupId = −1 時建構不崩**，只是不初始化字輩。
- 真正會崩的時機是 **生成僧侶成員** 時走到法號生成：
  - `OrganizationDomain.TryBecomeSectMonk`（`:1528`，實裝）：`if (CheckConditionOfBecomingSectMonk(...) && orgMemberCfg.ProbOfBecomingMonk > 0 && Random.CheckPercentProb(orgMemberCfg.ProbOfBecomingMonk))` 才進 `BecomeSectMonkInternal`。 (實裝核對)
  - `BecomeSectMonkInternal`（`:1874`）呼 `CharacterDomain.CreateSectMemberMonasticTitle(ctx, sect, mentor)`（`CharacterDomain.cs:15328`），其中若 suffix 池耗盡會呼 `GetMonasticTitleSuffixRange(SeniorityGroupId)`；`SeniorityGroupId = −1` → 拋例外。
- **修正後結論**：「`SeniorityGroupId` 不可 −1、走 `CreateSectMemberMonasticTitle`、−1 會崩」**只在僧侶派（任一職位 `ProbOfBecomingMonk > 0`）才成立**。**做非僧侶的世俗小派時，把所有職位的 `ProbOfBecomingMonk = 0`、`MonkType = 0`，`SeniorityGroupId` 留 −1 完全安全**，且省掉法號字庫。陳家堡若克隆少林(id 1)就繼承了僧侶屬性，這才是它「不可 −1」的根因——換成克隆世俗派（如華山/武當的世俗職階）即可解套。

### 3.4 怎麼指定某 NPC 擔任某職位
- 生成時：`IntelligentCharacterCreationInfo.OrgInfo = new OrganizationInfo(orgTemplateId, grade, principal:true, settlementId)`，`grade` 即職位（見 `OrganizationDomain.CreateCoreCharacter` `:2273` 就是這樣帶）。
- 運行時改職位：`OrganizationDomain.ChangeGrade(ctx, character, destGrade, destPrincipal)`（`:889` 實裝 / 舊源 838）——它重建 `OrganizationInfo`（保留 OrgTemplateId/SettlementId、換 Grade/Principal）並 `SetOrganizationInfo`，升階時寫生平記錄。
- 直接整個換派+換職：`JoinSect` / `ChangeOrganization`（帶新的完整 `OrganizationInfo`）。

> **這同時回答需求 4「給 NPC 設特別身份」**：身份 = `OrganizationInfo` 的 `OrgTemplateId`+`Grade`；「某小門派的某職位」就是 `new OrganizationInfo(我的門派id, 目標Grade, true, 該門派SettlementId)`，生成時帶或運行時用 `ChangeGrade`/`JoinSect` 設。職位的顯示名與能力來自 `Members[Grade]` 指到的 `OrganizationMemberItem`。

---

## 4. 小門派能否「掛在特殊建築（如商會）」而非佔聚落槽

### 4.1 組織的根據地一律是 `Settlement`，且綁定地圖 Location
- `Settlement`（抽象基類，`Settlement.cs:27`）有 `short Id`、`sbyte OrgTemplateId`、`Location Location`（`:30/33/36`）。子類只有兩種：`Sect`（`SettlementType.Sect = 0`）與 `CivilianSettlement`（`SettlementType.CivilianSettlements = 1`，`SettlementType.cs`）。
- 沒有「掛在 building 上的組織」這種第三型別。組織的「根據地」概念 = 一個 `Settlement` 實體 + 其 `Location(AreaId, BlockId)`。

### 4.2 商會不是獨立組織型別
- `Character.IsMerchant(orgInfo)`（`Character.cs:5519`，實裝）：商人 = 「`OrganizationItem.IsCivilian && Grade == 4 && OrganizationMemberItem.IdentityInteractConfig 含 4`」。**即商人只是某平民聚落（城鎮）的一個職階身份**，靠 `IdentityInteractConfig` 標記，不是門派、不是獨立組織。 (實裝核對)
- 交易資料 `MerchantData`（`Merchant/MerchantData.cs`）是 **per-character** 的買賣庫存；其 `ItemOwnerType` 有 `BuildingMerchant`（`MerchantData.cs:628`）一支，代表「建築自帶商人庫存」是 **物品歸屬層** 的概念，**不是組織層**。
- 沒有「商會」這個 Organization/Settlement 子型。產業視圖建築跳交易視窗的機制屬另一支 agent（`01_building_production_view.md`）的範疇。

### 4.3 但門派 **可以不上地圖** —— `CreateEmptySects` 佔位機制（最關鍵發現）
開新世界時的順序（`MapDomain.CreateAreas/...` 內，`MapDomain.cs:3560`）： (實裝核對 `CreateEmptySects` 方法體一致)
1. `OrganizationDomain.CreateEmptySects(ctx)`（`OrganizationDomain.cs:2007`，實裝 `:2086`）：**對每個 `IsSect=true` 的 org config 都生一個 `Sect`**，`Location = new Location(-1, index)`（`AreaId = -1`，即不在任何地圖 area）：
   ```csharp
   foreach (OrganizationItem orgCfg in Config.Organization.Instance)
       if (orgCfg.IsSect) {
           short settlementId = GenerateNextSettlementId(ctx);
           Sect sect = new Sect(settlementId, new Location(-1, index), orgCfg.TemplateId, ctx.Random);
           AddElement_Sects(settlementId, sect);
           AddSettlementCache(sect);   // 登記進 _orgTemplateId2Settlements[TemplateId]
           index++;
       }
   ```
2. 之後地圖 area 生成時，依該 area 的 `MapAreaItem.OrganizationId[]` 對「要上地圖的門派」呼 `CreateSettlement(ctx, location, orgTemplateId)`（`MapDomain.cs:4101`）——這才給真實 `Location` 並 `CreateSettlementMembers`（生成成員）。
3. `GetSettlementByOrgTemplateId(orgTemplateId)`（`:677` 實裝）= `GetSettlementByOrgTemplateId` 取 `_orgTemplateId2Settlements[id]`，**僅當該 org 名下恰好 1 個 settlement 時回傳，0 或 >1 都回 null**（`:644-651`）。 (實裝核對)

> **可行性結論**：
> - 「掛在商會/特殊建築上」**沒有現成資料模型**——組織根據地一律是 `Settlement`，商會不是組織。所以無法照搬商會。
> - **但「不佔地圖聚落槽」是可行的**：只要自訂門派 `IsSect=true` 且 **不被任何 area 的 `OrganizationId[]` 引用**，它就會 **停在 `CreateEmptySects` 的佔位實體**——名下恰好 1 個 settlement、`AreaId = -1`（不在地圖上）、`GetSettlementByOrgTemplateId(42)` 可正常回傳一個合法 `SettlementId`。
> - 這個佔位 sect **沒有成員**（成員只在 `CreateSettlement → CreateSettlementMembers` 時生），所以小派的 NPC 要 **自己生** 或 **運行時加入**（§1.3 兩途徑），用該 `SettlementId` 滿足 `JoinOrganization` 的 `SettlementId >= 0` 前提即可。
> - 視覺上「根據地像個建築」需前端／產業視圖配合（非本支範疇），但 **組織側完全不需要地圖聚落槽**。這是比陳家堡「上地圖新增槽位」輕得多的路。

---

## 5. 輕量化建議：最小可行小門派

目標：少量 NPC、有所屬、會用武功、有職位。相較陳家堡（克隆少林、上地圖新增聚落槽）可省掉：

| 步驟 | 陳家堡（重） | 輕量小派（最小） | 依據 |
|------|------|------|------|
| 上地圖聚落槽 | 反射加長某 area 的 `OrganizationId[]`+`SettlementBlockCore[]`（phase2 §1，最硬處） | **完全省略**：門派不進任何 `OrganizationId[]`，停在 `CreateEmptySects` 佔位（`AreaId=-1`） | `OrganizationDomain.cs:2007`；`phase2_map_findings.md` §1 |
| 大派陣列防越界 | 確認 `IsLargeSect`(1..15) / `LargeSectFavorabilities[15]` 不越界 | **天然免疫**：自訂 id（如 42）`GetLargeSectIndex` 回 −1，所有大派路徑有 `index>=0` 防護自動略過 | `OrganizationDomain.cs:1380/1385`（實裝）；`phase0_findings.md` §0 |
| 僧侶法號/字輩 | 克隆少林 → 繼承 `SeniorityGroupId=0`、僧侶屬性、需法號字庫 | **改克隆世俗派 + 全職位 `ProbOfBecomingMonk=0`、`MonkType=0`、`SeniorityGroupId=-1`**，免字庫、不會崩 | §3.3；`Sect.cs:147-171`、`OrganizationDomain.cs:1528` |
| 成員生成 | `CreateSettlementMembers` 依 `Members[grade]` 大批生成（含兄弟姐妹/配偶子女） | 自己用 `CreateIntelligentCharacter`（帶 `OrgInfo`）少量生，或運行時 `JoinSect` 把現成 NPC 拉進來 | `OrganizationDomain.cs:2148`；§1.3 |
| 職位表 | 完整 9 階 `Members[0..8]` 各一 `OrganizationMemberItem` | 只填用得到的少數 Grade（其餘指向 `Amount=0` 的空職位即可不生人） | `OrganizationDomain.cs:2190-2194`（`Amount>0` 才生） |
| 武學樹 | 繼承少林全套 | 只在用到的職位 `OrganizationMemberItem.CombatSkills` 掛幾個 `PresetOrgMemberCombatSkill` | §2.2 |

**最小切入點（組織側）**：
1. 反射克隆一個 **世俗** 門派的 `OrganizationItem`（避開僧侶屬性），設新 `TemplateId`（如 42）、`IsSect=true`、`SeniorityGroupId=-1`、小 `Population`、`Members[]` 指向少數低 `Amount` 的世俗職位列；`Organization.Instance.AddExtraItem(...)`（陳家堡 Phase 1 已驗證可行）。
2. **不碰地圖**——不加進任何 `OrganizationId[]`，靠 `CreateEmptySects` 自動佔位拿到合法 `SettlementId`（`GetSettlementByOrgTemplateId(42)`）。
3. NPC 設置：少量 `new OrganizationInfo(42, grade, true, GetSettlementIdByOrgTemplateId(42))`，生成時帶（`CreateIntelligentCharacter`）或運行時 `JoinSect`。職位＝`grade`，武功＝該 grade 的 `OrganizationMemberItem.CombatSkills`。

---

## 6. 待釐清問題

1. **`CreateEmptySects` 佔位 vs 大派被放上地圖的雙重登記**：15 大派（id 1-15）顯然也走 `CreateEmptySects`（`IsSect=true`），又被 area `OrganizationId[]` 引用而 `CreateSettlement` 再生一個——若兩者並存，`_orgTemplateId2Settlements[id]` 會有 2 筆使 `GetSettlementByOrgTemplateId` 回 null。實裝是否有「佔位被移除/重用」的清理（未在 `OrganizationDomain` 找到明顯 `RemoveSettlementCache` 對應呼叫）尚未釘死。**對自訂 id-42 小派無影響**（它只有佔位 1 筆），但若日後想讓小派也上地圖，需先確認此清理機制，否則可能撞「>1 → null」。建議下一步 grep 大派如何避免雙登記（可能 `OrganizationId[]` 引用的是 id 1-15、但這些在 `CreateEmptySects` 後是否被 area 流程「移走 location」而非「新建」）。
2. **佔位 sect（AreaId=-1）的副作用**：許多月度流程／NPC AI 會讀 `sect.GetLocation()`；`AreaId=-1` 對成員的「回據地」「巡邏」「過月供應」等是否有 NPE/異常路徑，需在塞入成員後實機跑幾個月驗證（本支只調查資料模型，未跑遊戲）。
3. **前端顯示**：佔位門派沒有地圖據點，門派列表/NPC 資訊面板（`GetSettlementMembers`、`GetOrganizationCombatSkillsDisplayData` 等前端查詢）對 `AreaId=-1` 的門派是否正常顯示，需前端核對（屬 ① 那支或前端 agent 範疇）。
4. **`InitializeSectSkills` 旗標（已釘死）**：生成時武學/生活技能受 `info.InitializeSectSkills` 控制（`Character.cs:23148/23152`），其 **預設為 `true`**（`Creation/IntelligentCharacterCreationInfo.cs:61`），所以一般生成路徑會自動配門派武功；只有顯式設 false 才不配。自製生成路徑保持預設即可。
