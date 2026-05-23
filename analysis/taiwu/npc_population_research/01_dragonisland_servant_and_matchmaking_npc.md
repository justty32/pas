# 太吾繪卷 NPC 生成調查：龍島忠僕 / 比武招親 / NPC 生成模板通則

> 版本綁定：實裝版 **0.0.79.60**。
> 反編譯參考源在 `~/dev/taiwu-src/`（較舊、可能漂移）。
> 「對實裝核對過」者已用 `ilspycmd -t <型別>` 反組譯 `Backend/GameData.dll`（路徑 `~/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/Backend/GameData.dll`）逐字確認；其餘僅看舊版反編譯源。
> 原始碼路徑前綴 `backend/` = `~/dev/taiwu-src/backend/`。

---

## 結論速覽（三件事）

| 項目 | 生成方式 | 核心錨點 | 對「造小門派 NPC」可行性 |
|---|---|---|---|
| A 龍島忠僕（伏龍忠僕 FulongServant） | **事件觸發時動態 new**（非世界生成既有） | `EventHelper.CreateFulongServant`（**已對實裝核對**） | **高**：這就是「憑空造一個帶所屬/年齡/性別的 NPC 並掛主僕關係」的完整教科書 |
| B 比武招親（為太吾比武招親 ContestForTaiwuBride） | **篩選既有人口 NPC**（不 new 新人），用月度行動 + 歷練系統 | `CallCharacterPredefinedRules.MatchParticipateCharacter_ContestForTaiwuBride`、`AdventureDomain` 的 `OrgTemplateIdToContestForTaiwuBride` 分支 | **低（作為生成範例）**：它不生成 NPC，只證明「篩人」這條路；對造門派 NPC 幫助有限 |
| C 通則 | 生成統一走 `IntelligentCharacterCreationInfo` → `CharacterDomain.CreateIntelligentCharacter` → `CompleteCreatingCharacter`（**已對實裝核對**） | 同上 + `OrganizationDomain.JoinOrganization` | — |

**最關鍵單一錨點**：`backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/EventHelper.cs:5685` 的 `CreateFulongServant()`。它是憑空造 NPC 的最小完整範本，且已對實裝 DLL 逐字核對。

---

## A. 龍島忠僕（FulongServant）的 NPC 生成

### A-1 何時、由哪段程式碼生成
- **動態生成**，非世界生成既有。由事件呼叫 `EventHelper.CreateFulongServant`。
- 舊版反編譯源簽名（無參）：`backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/EventHelper.cs:5685`
  ```csharp
  public static GameData.Domains.Character.Character CreateFulongServant()
  ```
- **對實裝 DLL 核對（0.0.79.60，有漂移）**：實裝簽名變成帶事件參數
  ```csharp
  public static GameData.Domains.Character.Character CreateFulongServant(string nextEventGuid, EventArgBox argBox)
  ```
  實裝多了從 `argBox` 讀取的覆寫鍵：`FulongServantSetGender`(指定性別)、`FulongServantSetTransgender`、`FulongServantSetBehaviorType`、`FulongServantSetMainAttributeType`，並在指定性別時把魅力設為 `Random.Next(GlobalConfig.Instance.FulongServantBaseAttraction, 900)`。**核心生成流程兩版一致。**

### A-2 生成流程（實裝 DLL 逐字，去掉 argBox 分支後的骨幹）
```csharp
DataContext context = Domain.MainThreadDataContext;
Character taiwu = DomainManager.Taiwu.GetTaiwu();
Location location = taiwu.GetLocation();
OrganizationInfo orgInfo = taiwu.GetOrganizationInfo();   // 直接複製玩家的所屬！
orgInfo.Grade = 0;                                        // 但職位歸 0（最低階）
sbyte gender = Gender.GetRandom(context.Random);
sbyte growingSectId = OrganizationDomain.GetRandomSectOrgTemplateId(context.Random, gender); // 隨機「成長門派」決定資質取向
sbyte growingGrade = (sbyte)context.Random.Next(6);
sbyte stateTemplateId = DomainManager.Map.GetStateTemplateIdByAreaId(location.AreaId);
short charTemplateId = OrganizationDomain.GetCharacterTemplateId(growingSectId, stateTemplateId, gender); // 角色模板 id
short age = (short)context.Random.Next(12, 25);          // 12~24 歲

IntelligentCharacterCreationInfo info = new IntelligentCharacterCreationInfo(location, orgInfo, charTemplateId);
info.Age = age;
info.GrowingSectId = growingSectId;
info.GrowingSectGrade = growingGrade;
info.InitializeSectSkills = false;                       // ★忠僕不自動學門派武學

Character character = DomainManager.Character.CreateIntelligentCharacter(context, ref info); // ★生成
int charId = character.GetId();
DomainManager.Character.CompleteCreatingCharacter(charId);                                   // ★結束「建立中」狀態

character.AddFeature(context, 199);                      // ★掛「忠僕」特性（見 A-4）
character.SetIdealSect(growingSectId, context);
DomainManager.Character.TryCreateGeneralRelation(context, taiwu, character);                  // 建一般關係
DomainManager.Character.ChangeFavorabilityOptional(context, character, taiwu, 10000, 0);     // ★好感拉滿
DomainManager.Taiwu.JoinGroup(context, charId);                                              // ★加入玩家隊伍
ShowGetItemPageForCharacters(new List<int>{ charId }, isVillager:false);
```

### A-3 屬性 / 所屬 / 主僕關係如何建立與儲存
- **性別**：`Gender.GetRandom`（實裝可被 `FulongServantSetGender` 覆寫）。
- **年齡**：`Random.Next(12,25)` → 寫進 `info.Age`。
- **資質/造詣取向**：由 `GrowingSectId`（隨機門派）+ `GrowingSectGrade`（0~5）決定，**不是直接給數值**——數值由 `CreateIntelligentCharacter` 內部依「成長門派 + 階級」算出。要精準指定數值得用 `info.LifeSkillsLowerBound / CombatSkillsLowerBound`（見 IntelligentCharacterCreationInfo 欄位，C-2）。
- **姓名**：`CreateIntelligentCharacter` 內部依 `charTemplateId`（含地域/門派風格）自動隨機生成；亦可用 `info.ReferenceFullName` 指定參考姓名。
- **所屬 `OrganizationInfo`**：直接複製太吾的所屬（`taiwu.GetOrganizationInfo()`）再把 `Grade=0`。型別在 `backend/GameData.Shared/GameData/Domains/Character/OrganizationInfo.cs:8`（**已對實裝核對**），4 欄位：
  ```csharp
  public sbyte OrgTemplateId;   // 門派/勢力模板 id
  public sbyte Grade;           // 職位階級
  public bool  Principal;       // 是否本人入籍（非配偶掛靠）
  public short SettlementId;    // 駐地 id（<0 視為無所屬，不會真的入籍）
  ```
- **「主僕」標記＝三件事疊加，沒有單一「主僕關係表」**：
  1. **特性 199 = `FulongServant`**：`backend/GameData/Config/CharacterFeature.cs:78`
     ```csharp
     public const short FulongServant = 199;
     ```
     這是「這是忠僕」的身份標籤（存在角色的 feature 集合裡）。
  2. **好感拉滿 10000**：`ChangeFavorabilityOptional(...,10000,0)`，簽名 `backend/GameData/GameData/Domains/Character/CharacterDomain.cs:16306`。
  3. **加入玩家隊伍**：`TaiwuDomain.JoinGroup`，`backend/GameData/GameData/Domains/Taiwu/TaiwuDomain.cs:6128`——此處 `character.SetLeaderId(_taiwuCharId, ...)` 把忠僕的 `LeaderId` 設成玩家，並 `_groupCharIds.Add(charId)`。**「跟隨/聽命」的根本就是 `LeaderId == 玩家 charId` 且在玩家 group 集合內。**

### A-4 行為（聽命）走哪套系統
- **隊伍系統 + 隊友月度事件**。`JoinGroup` 後 `LeaderId=玩家`，落點同步到玩家位置（`character.SetLocation(_taiwuChar.GetLocation())`，TaiwuDomain.cs:6128 區段）。
- 隊友的月度行為由事件包 `Taiwu_EventPackage_TeammateMonthAdvanceEvents.dll` 處理（位於 `<遊戲>/Event/EventLib/`）。隊友指令系統相關列舉：`backend/GameData/ETeammateCommandType.cs`、`ETeammateCommandImplement.cs`、`ETeammateCommandOption.cs`。
- **對比範例：強制跟隨者** `EventHelper.CreateForcedToFollowCharacter`（`EventHelper.cs:2345`，**已對實裝核對流程一致**）用 `AddFeature(198)` (= `ForcedToFollow`，CharacterFeature.cs:76) + 好感 **-10000**——同一套生成骨幹，只是 feature 與好感正負相反。可見「跟隨」是 feature + group + 好感的組合，而非獨立子系統。

### A-5 「龍島」名稱對應
- grep `龍島`/`Dragon`/`Servant` 在原始碼字串中**查無「龍島」直譯**；實際對應的是 **伏龍（Fulong）** 系：`FulongServant`(feature 199)、`HelperFulong`(EventActors.cs)、門派武學目錄 `SpecialEffect/CombatSkill/Fulongtan/`（伏龍潭）。中文「龍島」字串應在事件腳本/語言檔（`Event/EventScript/*.twes` 為二進位、`Event/EventLanguages/`），非後端原始碼。**遊戲內所謂龍島忠僕 = 程式碼層的 FulongServant。**

---

## B. 比武招親（ContestForTaiwuBride）的 NPC 生成

### B-1 是事件還是內建系統？觸發點
- **內建「月度行動（MonthlyAction）+ 歷練（Adventure）」系統，外加事件包觸發**，不是單一 `TaiwuEventItem`。
- 觸發 API：`EventHelper.TriggerBrideOpenContest(short settlementId)`，`backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/EventHelper.cs:2400`，內部取 `MonthlyEventActionsManager.PredefinedKeys["BrideOpenContestDefault"]` 並 `CreateWrappedAction(ConfigMonthlyActionDefines.OrgTemplateIdToContestForTaiwuBride[stateTemplateId], -1)`。
- 城市對應的月度行動 id：`backend/GameData/Config/MonthlyActions.cs:56` 起，`BrideOpenContestJingcheng=31`…`BrideOpenContestYangzhou=45`（每座城一個）。
- 對應表：`backend/GameData/GameData/Domains/TaiwuEvent/Enum/ConfigMonthlyActionDefines.cs:7` 的 `OrgTemplateIdToContestForTaiwuBride`（門派模板 id → 月度行動 id 的 Dictionary）。
- 歷練端處理：`backend/GameData/GameData/Domains/Adventure/AdventureDomain.cs:3005` 的 `if (ConfigMonthlyActionDefines.OrgTemplateIdToContestForTaiwuBride.ContainsValue(monthlyActionId))` 分支，選點、設 `AdventureSiteData.TemplateId = adventureId`、跑 `MonthlyHandler()`。
- 婚禮歷練觸發：`EventHelper.TriggerTaiwuWeddingAdventure(int spouseCharId, Location location)`，`EventHelper.cs:2421`，建 `MarriageTriggerAction { SpouseCharId, Location }`。
- 事件包（劇情外殼）：`<遊戲>/Event/EventLib/` 內 `Taiwu_EventPackage_Marry<City>.dll`（各城）、`Taiwu_EventPackage_MarryAdventure.dll`、`FemaleMarry<City>.dll`。

### B-2 候選 NPC 是「篩既有」還是「new 新人」？
- **篩選既有人口 NPC，不 new 新人。** 證據：`backend/GameData/GameData/Domains/TaiwuEvent/MonthlyEventActions/CustomActions/CallCharacterPredefinedRules.cs:11`
  ```csharp
  public static bool MatchParticipateCharacter_ContestForTaiwuBride(Character character)
  {
      if (!CharacterMatchers.MatchNotCalledByAdventure(character)) return false;
      if (!CharacterMatchers.MatchDisplayingAge(character, 16, 50)) return false;   // 年齡 16~50
      if (!CharacterMatchers.MatchMaritalStatus(character, isMarried:false)) return false; // 未婚
      if (!CharacterMatchers.MatchOrganizationType(character, 0, 2)) return false;  // 世俗類所屬 type 0~2
      if (!CharacterMatchers.MatchOrgMemberAllowMarriage(character)) return false;  // 該門派職位允許婚配
      if (CharacterMatchers.MatchIsMonk(character)) return false;                   // 排除僧侶
      sbyte xiangshuLevel = DomainManager.World.GetXiangshuLevel();
      if (!CharacterMatchers.MatchGrade(character, 0, xiangshuLevel)) return false; // 階級 0~相書等級
      return true;
  }
  ```
  全是 `CharacterMatchers.*` 過濾器（namespace `GameData.Domains.Character.Filters`），對既有人口做布林篩選，**完全沒有任何 `Create*`/`new Character`**。新娘與比武參賽者都是地圖上現成的活人 NPC。
- **踩雷／版本警告**：`CallCharacterPredefinedRules` 整個類別與其方法都標了 `[Obsolete]`（CallCharacterPredefinedRules.cs:7,10）。實裝 0.0.79.60 的篩選規則**很可能已改走事件腳本內的 filter-rules 設定**（見 B-4 的 `characterFilterRulesId`）。此檔僅供理解「比武招親是篩既有人口」的事實，**邏輯細節未對實裝核對，勿照抄常數**。

### B-3 婚配成功/失敗後 NPC 去留與所屬
- 候選本就是常駐人口，**失敗不影響其存在**。
- 成功成婚走 `EventHelper.AddHusbandOrWifeRelationsInAdventure(charId, relatedCharId)`，`EventHelper.cs:2289`：
  - `DomainManager.Character.AddHusbandOrWifeRelations(...)` 建夫妻關係。
  - 互加 `AddRelation(..., 16384)`（好感）。
  - 若一方是太吾 → 另一方 `JoinGroup` 入隊。
  - 雙方皆非太吾 → `DomainManager.Organization.UpdateOrganizationAfterMarriage(context, bride, husband)`（`EventHelper.cs:2324`）更新所屬（一般是配偶掛靠 `OrganizationInfo.Principal=false`）。
- 若候選是「臨時智能角色」（temporary，見 C-3），成婚時 `KeepTemporaryCharacterAfterAdventure(...)` 把它轉正、留在常駐人口（`EventHelper.cs:2300` 區段）。

---

## C. 從 A、B 歸納「NPC 生成模板」通則（使用者最終目的）

### C-1 最低限度造一個 NPC：必呼叫的 API 與必填參數
**唯一正規入口**（後端，已對實裝核對）：
```
backend/GameData/GameData/Domains/Character/CharacterDomain.cs:26387
  public Character CreateIntelligentCharacter(DataContext context, ref IntelligentCharacterCreationInfo info)
```
最小步驟（抄 `CreateFulongServant` / `CreateForcedToFollowCharacter` 的骨幹）：
```csharp
DataContext context = Domain.MainThreadDataContext;        // ★主執行緒 context（見 C-4）

// 1) 決定落點、所屬、模板
Location location = /* 落點，多用 taiwu.GetLocation() 或某 settlement 的 location */;
OrganizationInfo orgInfo = new OrganizationInfo(orgTemplateId, grade, principal:true, settlementId); // ★所屬
sbyte stateTemplateId = DomainManager.Map.GetStateTemplateIdByAreaId(location.AreaId);
short charTemplateId = OrganizationDomain.GetCharacterTemplateId(orgTemplateId, stateTemplateId, gender); // ★角色模板

// 2) 填生成資訊
var info = new IntelligentCharacterCreationInfo(location, orgInfo, charTemplateId);
info.Age = age;                 // 不填 = -1 由內部隨機
info.Gender = gender;           // -1 = 隨機
info.GrowingSectId = orgTemplateId;   // 影響資質取向
info.GrowingSectGrade = grade;        // 影響資質強度
info.InitializeSectSkills = true;     // true=自動發該門派武學；忠僕設 false

// 3) 生成 + 收尾（缺 CompleteCreatingCharacter 會卡在「建立中」狀態並在校驗時拋例外）
Character ch = DomainManager.Character.CreateIntelligentCharacter(context, ref info);
DomainManager.Character.CompleteCreatingCharacter(ch.GetId());
```
**三個一定要懂的輔助**：
- `OrganizationDomain.GetCharacterTemplateId(orgTemplateId, stateTemplateId, gender)`：`backend/GameData/GameData/Domains/Organization/OrganizationDomain.cs:3708`，由「門派+地域+性別」決定姓名風格/外觀/初始傾向的模板 id。**必填**。
- `OrganizationDomain.GetRandomSectOrgTemplateId(random, gender)`：`OrganizationDomain.cs:3567`，要隨機門派時用。
- `CompleteCreatingCharacter(int charId)`：`CharacterDomain.cs:27040`，只是把 charId 移出 `_creatingCharIds`；**漏呼叫會在 `CheckCharacterCreationState` 拋 "Some characters are still in creating state"**。

**便捷封裝**（前端事件常用，省去算 templateId）：`EventHelper.CreateIntelligentCharacter(Location, sbyte gender, short age, short baseAttraction, short settlementId, sbyte grade)`，`EventHelper.cs:5735`（**已對實裝核對簽名**）——內部自己組 `OrganizationInfo(settlement.OrgTemplateId, grade, principal:true, settlementId)` 並算 templateId、自動收尾。**做小門派 NPC 最省事的入口，前提是先有 settlement。**

### C-2 「生成參數模板」長相 & 能否注入自訂
- **生成資訊載體 = `IntelligentCharacterCreationInfo`**（struct），`backend/GameData/GameData/Domains/Character/Creation/IntelligentCharacterCreationInfo.cs`（**已對實裝核對**，實裝多一欄 `DisableBeReincarnatedBySavedSoul`）。關鍵可填欄位：
  | 欄位 | 用途 |
  |---|---|
  | `Location`(readonly) / `OrgInfo`(readonly) / `CharTemplateId`(readonly) | 建構子三必填 |
  | `Age` / `BirthMonth` / `Gender` / `Transgender` / `Race` | 基本屬性，-1=隨機 |
  | `GrowingSectId` / `GrowingSectGrade` | 成長門派與階級（決定資質/造詣取向與強度） |
  | `BaseAttraction` | 魅力 |
  | `LifeSkillsLowerBound[]` / `CombatSkillsLowerBound[]` | **指定生活/武學造詣下限**（精準給技能用這個） |
  | `InitializeSectSkills` | 是否自動發成長門派的初始武學 |
  | `ReferenceFullName` | 指定參考姓名 |
  | `Avatar` / `SpecifyGenome`+`Genome` | 指定外觀/基因 |
  | `Mother/Father*`、`PregnantState`、`ReincarnationCharId`、`DestinyType` | 血緣/轉世/天命（造門派 NPC 一般留預設 -1） |
- **「角色模板表」= `Config.Character`**（`backend/GameData/Config/Character.cs`，2萬+ 行常數表，如 `GhostServant=268`）與 `Config.Organization` / `Config.OrganizationMember`。`charTemplateId` 指向 `Config.Character.Instance[id]`。
- **能否用 `AddExtraItem` 注入自訂模板？**——本次未直接核對 `AddExtraItem` 對 `Config.Character` 的擴充行為（屬下一步待查）。但**做小門派 NPC 通常不需要新增角色模板**：直接複用某既有 `charTemplateId`（取自既有門派+地域），再用 `IntelligentCharacterCreationInfo` 的欄位（年齡/性別/造詣下限/所屬）覆寫即可達到「指定屬性」。新增 `Config.Character` 條目才需要 ExtraItem 注入，屬進階需求。

### C-3 三種生成變體（按需求選）
1. **常駐智能 NPC**：`CreateIntelligentCharacter` + `CompleteCreatingCharacter`（A、C-1）。要進門派/人口就用這個。
2. **臨時智能 NPC**：`EventHelper.CreateTemporaryIntelligentCharacter(...)`（`EventHelper.cs:5751`）→ 內部 `DomainManager.Character.CreateTemporaryIntelligentCharacter` + `DomainManager.Adventure.AddTemporaryIntelligentCharacter(charId)`。歷練結束會被清掉，除非 `KeepTemporaryCharacterAfterAdventure` 轉正。實裝另有過載 `CreateTemporaryIntelligentCharacter(DataContext, short characterFilterRulesId, Location)`（**對實裝核對到、舊源沒有**）——用「過濾規則 id」生成，疑似比武招親/歷練臨時對象的新走法。
3. **固定模板 NPC（非智能）**：`EventHelper.CreateNonIntelligentCharacter(short templateId)`（`EventHelper.cs:8327`）、`GetOrCreateFixedCharacterByTemplateId`（`:5028`）——劇情固定角色用，不適合一般門派成員。

### C-4 後端 mod 動態生成的安全時機（踩雷）
- **必須在主執行緒**：用 `Domain.MainThreadDataContext`。所有 `Create*` 範例都取這個 context。
- **過月逐角色方法跑 worker thread**（平行段），在那裡寫全域（如新增角色、改門派成員集合）會偶發崩潰。
- **安全鉤子＝主執行緒事件**：用 `RegisterHandler_AdvanceMonthBegin`（過月開始，主執行緒）等事件鉤生成 NPC，避開平行段。這與既有「太吾現況」筆記一致。
- 生成過程涉及 `AddElement_Objects`、`JoinOrganization`、`Events.RaiseCharacterCreated`（見 `ComplementCreateIntelligentCharacter`，CharacterDomain.cs:26436）等全域寫入，**務必序列化在主執行緒**。

### C-5 與「輕量小門派」的接點：生成後塞進自訂門派
做完 C-1 拿到 `character` 後：
1. **入籍門派**：`OrganizationDomain.JoinOrganization(context, character, destOrgInfo)`，`backend/GameData/GameData/Domains/Organization/OrganizationDomain.cs:692`（**已對實裝核對流程**）。
   - 它讀 `destOrgInfo`（= `character.GetOrganizationInfo()` 或自訂）：
     - `SettlementId < 0` → **直接 return，不入籍**（所以小門派 NPC 的 `OrganizationInfo.SettlementId` 必須 ≥0，且該 SettlementId 要有對應 `Sect`）。
     - `IsSect(OrgTemplateId)` 為真 → 建 `SectCharacter(charId, OrgTemplateId, SettlementId)`，加進 `_sects[SettlementId].GetMembers().Add(charId, Grade)`，跑 `TryAddSectMemberFeature`、`SetRandomSectMentor`。`Grade==8 && Principal` 會加 feature 405（掌門類）。
     - 否則建 `CivilianSettlementCharacter`（世俗駐地）。
   - **小門派必備前置**：先存在一個 id≥42 的自訂門派模板（`Config.Organization`）與一個對應的 `Sect` 物件 + `SettlementId`。`CreateIntelligentCharacter` 收尾時 `ComplementCreateIntelligentCharacter` 已自動呼叫一次 `JoinOrganization(context, character, character.GetOrganizationInfo())`（CharacterDomain.cs:26436 區段）——**所以只要把 NPC 的 `OrgInfo` 設成你的小門派(orgTemplateId≥42, settlementId=你的駐地)，生成當下就自動入籍，不必再手動呼叫。**
2. **給職位 Grade**：即 `OrganizationInfo.Grade`（成員階級索引，對應 `Config.Organization.Instance[orgTemplateId].Members[Grade]` → `OrganizationMember` 條目）。
3. **發武功**：
   - 自動：`info.InitializeSectSkills = true` → 生成時依成長門派發初始武學。
   - 手動指定造詣：`info.CombatSkillsLowerBound[] / LifeSkillsLowerBound[]`。
   - 門派層級的武學掛點（已知）：`OrganizationMemberItem.CombatSkills`（門派成員模板自帶武學）、以及 `info.InitializeSectSkills`。要客製發特定武學，可在生成後另呼叫角色學武 API（本次未細查，沿用既有筆記）。

### C-6 可行性總判

| 目標 | 判定 | 理由 |
|---|---|---|
| 憑空造一個帶指定性別/年齡/所屬的 NPC | **高** | `CreateFulongServant`/`CreateForcedToFollowCharacter` 是現成、已對實裝核對的完整範本；`IntelligentCharacterCreationInfo` 欄位齊全；`CompleteCreatingCharacter` 收尾規則明確 |
| 指定造詣/武學 | **中** | 有 `*SkillsLowerBound` 與 `InitializeSectSkills`，但精準到「某一招」需額外學武 API（未細查） |
| 塞進 id≥42 自訂門派 | **中** | `JoinOrganization` 路徑清楚（須 `SettlementId≥0` + 存在 `Sect`），且生成時自動入籍；門檻在「先把小門派/Sect/Settlement 建出來」這條前置鏈（屬另一條軌） |
| 學比武招親「篩既有人口」 | **低（對生成無用）** | 它根本不生成 NPC；只在「需要從現役人口挑人」時參考 `CharacterMatchers` 過濾器（且舊源 `[Obsolete]`，需重新對實裝核對） |

---

## 待辦 / 未核對清單
- `JoinOrganization` 對「id≥42 自訂門派 + 自建 Sect/Settlement」的實際行為未做端到端驗證（理論路徑通，但 `_sects[SettlementId]` 是否存在需實測）。
- `AddExtraItem` 能否注入 `Config.Character` 角色模板未核對。
- 比武招親實裝的篩選規則（`characterFilterRulesId` 走向）未對實裝細查；舊版 `CallCharacterPredefinedRules` 為 `[Obsolete]`。
- 「精準發某一招武學」的角色學武 API 未細查。

## 已對實裝 DLL（0.0.79.60）逐字核對清單
- `EventHelper.CreateFulongServant`（簽名漂移：實裝帶 `(string, EventArgBox)`，核心流程一致）
- `IntelligentCharacterCreationInfo` 欄位（實裝多 `DisableBeReincarnatedBySavedSoul`）
- `CharacterDomain.CreateIntelligentCharacter` / `CompleteCreatingCharacter` / `CreateCloseFriend` / `CreateTemporaryIntelligentCharacter`(含新過載) / `TryCreateGeneralRelation` / `ChangeFavorabilityOptional` 簽名
- `EventHelper.CreateIntelligentCharacter(Location,...)` / `CreateTemporaryIntelligentCharacter(Location,...)` 便捷版簽名
- `OrganizationInfo`（透過原始碼 + 結構驗證；DLL `-t` 因 ILSpy 版本字串差異未直接吐出，欄位以 GameData.Shared 源核對）

## 僅看舊版反編譯源（未對實裝核對方法體）
- `CreateForcedToFollowCharacter`、`AddHusbandOrWifeRelationsInAdventure`、`TriggerBrideOpenContest`、`TriggerTaiwuWeddingAdventure` 方法體
- `JoinOrganization` / `JoinGroup` 方法體（簽名位置確認，逐字內文僅舊源）
- `CallCharacterPredefinedRules.*`（且標 `[Obsolete]`）
- `ConfigMonthlyActionDefines.OrgTemplateIdToContestForTaiwuBride`、`Config.MonthlyActions`、`Config.CharacterFeature`、`Config.EventActors` 常數
