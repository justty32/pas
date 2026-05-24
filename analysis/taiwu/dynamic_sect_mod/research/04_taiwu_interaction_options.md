# 04 — 太吾與 NPC 互動時注入自訂選項（跨功能入口）

> 建立：2026-05-24。範圍：「中小門派」mod 的**跨功能入口**——太吾與某 NPC 交談/互動時，依條件跳出自訂選項，按下後執行動作（收徒/傳授/委託/創派/據點建設都靠這條）。
>
> **唯一事實來源**：實裝版 **0.0.79.60** 反編譯。下文每條結論標 `【實裝核對】`＝已用 `ilspycmd -t`/`-p` 對實裝 DLL 驗證；未核對者標 `⚠️`。
> - 後端：`…/The Scroll Of Taiwu/Backend/GameData.dll`、`…/Backend/GameData.Shared.dll`
> - 前端：`…/The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`
>
> 先讀過並建立在其上：
> - `details/event_system_modding.md`（事件系統 modding 總覽：`--enable-event-editor` 路線）
> - `details/event_class_anatomy.md`（`TaiwuEventItem`/`TaiwuEventOption` 解剖、`EventTrigger` 表）
> - `player_faction_research/04_player_join_sect_command.md`（`EventHelper.JoinOrganization`、`SetTaiwuAsLeaderOfTaiwuVillage`）
> - `player_faction_research/05_player_town_identity.md`（城鎮身份＝`OrganizationInfo`、`OrganizationInfo.Grade`、`_taiwuBuildingAreas` 建設權）
> - `details/sect_skill_favor_ui.md`（`CommandManager.AddCommandShowUI`）
> - 本目錄 `02_teach_combat_skill.md`（`LearnCombatSkill` 承載動作）
>
> **未動 session_log.md，未 git add/commit，未碰其他檔案。**

---

## 0. 一句話結論

太吾繪卷有一套**官方、config 資料驅動的「角色互動選項」系統**，正是為「點 NPC → 跳一排選項 → 條件式顯示 → 按下執行」而生，而且**條件直接支援「對方在不在門派 / 對方的品階 / 對方是不是城主 / 對方與太吾好感」這些欄位**。

- 兩條路：
  - **(a) 官方事件系統**（`EEventType.NpcInteractEvent` + `TriggerType=CharacterClicked`）：能做「點某 NPC → 條件成立才跳事件 → 事件內含選項 → 選項再帶可見/可選條件 → 選擇後跑後端腳本」。
  - **(b) 前端 Harmony patch**：互動選項實際是後端 `TaiwuEventDomain` 透過 `InteractionEventOption` config + `_characterInteractionEventOptionList` 算出來的（前端只渲染），所以「插一個自訂互動選項」其實**仍要落在後端的 config/事件**上，純前端 patch 只能改外觀、難改「能不能執行」。
- **最省力＝走官方事件編輯器（路線 a），用 `EEventType.NpcInteractEvent`**。它原生支援「點 NPC 觸發」「選項可見/可選條件」「選項腳本呼後端 API」。條件式選項所需的全部判斷（`CharacterInSect`/`CharacterGradeNotSatisfy`/`CharacterIsCastellan`/`FavorAtLeast`）都是**現成的 condition 原語**（`GameData.Domains.TaiwuEvent.EventOption.OptionConditionMatcher`），編輯器拉一拉即可。
- **設計要求的兩個條件式選項都直接可行**：
  - 「對是太吾弟子的 NPC 跳『創派』、但弟子已有門派則不跳」＝ 選項可見條件 `師徒關係`(`CheckHasRelationship`,relation flag) **AND NOT** `CharacterInSect`(ConditionId 21)。
  - 「對城鎮三品以上 NPC 跳『據點建設』」＝ 選項可見條件 `CharacterGradeNotSatisfy`(ConditionId 23) 或更精準的 `OrganizationInfo.Grade` 判斷（含 `CharacterIsCastellan` ConditionId 33）。
- **承載動作全有現成後端 API**（`EventHelper`）：收徒 `ApplyRelationBecomeMentor`、傳授 `LearnCombatSkill`（見 `02_teach_combat_skill.md`）、入派/創派 `JoinOrganization`、建據點 `CreateSectBuildingForce`/`BuildingDomain.AddTaiwuBuildingArea`。前後端傳遞＝前端點擊送 `OnCharacterClicked(charId)` → 後端事件腳本在後端進程執行。
- **風險**：後端事件腳本例外＝後端進程崩（比前端嚴重得多）；版本漂移主要打到「事件包 DLL 須對當前版本重編」。事件系統把多數膠水/條件交給官方框架，跨版風險比手刻 Harmony 低。

---

## 1. 前端「點 NPC」到後端的完整鏈路（事實基礎）

### 1.1 點擊 NPC → 前端橋接 `OnCharacterClicked` 【實裝核對】

前端「交談」按鈕（`UI_CharacterMenuInfo.OnClick`，`btn.name=="TalkBtn"`）呼叫前端 domain 橋：
- `/tmp/fe_decomp/UI_CharacterMenuInfo.cs:177-183`：
  ```csharp
  if ("TalkBtn" == text) {
      TaiwuEventDomainMethod.Call.OnCharacterClicked(base.CharacterMenu.CurCharacterId);
      UIManager.Instance.HideUI(UIElement.CharacterMenu);
  }
  ```
- 另兩個入口同樣呼 `OnCharacterClicked`：`UI_Bottom.cs:960`（地圖角色）、`UI_Bottom.cs:1520`（清單）。
- 橋接：`TaiwuEventDomainMethod.Call.OnCharacterClicked(int charId)`（前端 `GameData.Domains.TaiwuEvent/TaiwuEventDomainMethod.cs`，DomainId=12 的 method call）。

### 1.2 後端依「角色生成型別」分流觸發點 【實裝核對】

`GameData.Domains.TaiwuEvent.TaiwuEventDomain.OnCharacterClicked(DataContext, int)`（`GameData.dll` 反編譯行 3239）：
```csharp
public void OnCharacterClicked(DataContext context, int charId) {
    Character c = DomainManager.Character.GetElement_Objects(charId);
    short templateId = c.GetTemplateId();
    if (!Character.IsXiangshuMinion(templateId)) {
        if (XiangshuAvatarIds.JuniorXiangshuTemplateIds.Contains(templateId))      OnEvent_PurpleBambooAvatarClicked(...);   // 紫竹
        else if (c.GetCreatingType() == 0)                                          OnEvent_FixedCharacterClicked(...);       // 固定/具名劇情角(trigger 67)
        else if (c.GetCreatingType() != 3 || DomainManager.Extra.IsSpecialGroupMember(c)) OnEvent_CharacterClicked(charId);   // ★一般生成 NPC(trigger 2)
        else if (c.GetCreatingType() == 3 && SectMainStoryRelatedConstants.SectMainStoryCharacterTemplateIds.Contains(templateId)) OnEvent_FixedEnemyClicked(...);  // 主線敵
    }
}
```

> **關鍵**：絕大多數一般 NPC（弟子、城鎮居民、普通江湖人）落在 `OnEvent_CharacterClicked` → 觸發點 **`EventTrigger.CharacterClicked = 2`**。固定具名劇情角才走 `FixedCharacterClicked = 67`。中小門派 mod 的對象（自己的弟子、城鎮三品 NPC）屬一般 NPC，**用 `CharacterClicked`（2）這個觸發點**。

### 1.3 後端分發到各 EventManager 【實裝核對】

`TaiwuEventDomain.OnEvent_CharacterClicked(int)`（`GameData.dll` 行 5852）逐個喊每種事件管理器的 `OnEventTrigger_CharacterClicked`：
```csharp
for (int i = 0; i < _managerArray.Length; i++)
    if (CanTriggerEventType((EEventType)i))
        _managerArray[i]?.OnEventTrigger_CharacterClicked(arg0);
```
其中處理 NPC 互動事件的是 **`NpcEventManager`**（`EEventType.NpcInteractEvent`）。

### 1.4 `NpcEventManager` 怎麼決定哪個事件被觸發 【實裝核對】

`GameData.Domains.TaiwuEvent.EventManager.NpcEventManager.OnEventTrigger_CharacterClicked(int arg0)`（`GameData.dll`，方法體行 140-167）：
```csharp
foreach (TaiwuEvent headEvent in _headEventList) {
    if (headEvent.EventConfig.TriggerType == EventTrigger.CharacterClicked) {
        eventArgBox.Set("CharacterId", arg0);          // ★把被點 NPC 的 id 塞進 ArgBox
        headEvent.ArgBox = eventArgBox;
        if (headEvent.EventConfig.CheckCondition()) {  // ★跑事件「進入條件」
            DomainManager.TaiwuEvent.AddTriggeredEvent(headEvent);   // 條件成立才入列觸發
        } else headEvent.ArgBox = null;
    }
}
```
- 只有 `IsHeadEvent==true` 的事件會進 `_headEventList`（`NpcEventManager.HandleEventPackage` 行 44-52）；且有警告：非 head event 設了 TriggerType 不會生效（行 41）。
- `CharacterId` 是事件腳本與選項條件取得「被互動 NPC」的標準鍵（下節條件原語全靠它）。

⇒ **官方路線就是：做一個 `EEventType.NpcInteractEvent` 的 head event，`TriggerType=CharacterClicked`，進入條件決定「對哪種 NPC 才跳」，事件內放選項。**

---

## 2. 選項的條件鏈：支援哪些角色欄位（條件式選項可行性核心）

### 2.1 選項本體 `TaiwuEventOption`：可見/可選各有條件鏈 【實裝核對】

`Config.EventConfig.TaiwuEventOption`（`GameData.dll`）關鍵欄位：
- `OptionKey` / `OptionGuid`：選項識別。
- `VisibleConditions`（`EventConditionList`）＋ `Func<bool> OnOptionVisibleCheck`：**選項是否顯示**。
- `AvailableConditions`（`EventConditionList`）＋ `OnOptionAvailableCheck` ＋ `List<TaiwuEventOptionConditionBase> OptionAvailableConditions`：**選項是否可選（可灰掉）**。
- `Func<string> OnOptionSelect` / `EventScript Script`：**選擇後執行**（回傳要跳的下個事件 GUID 或空）。
- `bool IsVisible`：跑 `OnOptionVisibleCheck()` ＋ `scriptRuntime.CheckConditionList(VisibleConditions, ArgBox)`。
- `bool IsAvailable`：`CheckAvailableConditionsFromCode() && ...FromScript() && ...FromCodeConfig()`，且 `OptionAvailableConditions` 支援 `OrConditionCore`（OR 群組）＋ `OptionConditionModifier`（條件可被修飾）。

> 對應編輯器：`event_class_anatomy.md §3` 的「選項可見條件 / 可選條件 / 選項腳本」就是這幾個欄位。條件鏈吃的 `ArgBox` 在 NPC 互動情境下已被塞 `CharacterId`（§1.4），所以條件可直接讀「被互動 NPC」。

### 2.2 條件原語清單 `ConditionId`（共 60+，挑與門派/互動相關）【實裝核對】

`GameData.Domains.TaiwuEvent.EventOption.ConditionId`（`GameData.dll`，`const short`）。中小門派 mod 直接可用的：

| ConditionId | 值 | 語義（對「被點 NPC」或太吾） |
|---|--:|---|
| `CharacterInSect` | 21 | **NPC 是否已加入任一門派**（見 §2.3 mapper） |
| `CharacterGradeNotSatisfy` | 23 | NPC 的**門派/組織品階**不足（`[Obsolete]` 但仍在；按品階卡選項） |
| `CharacterGradeNotSatisfyByProfession` | 58 | 按職業另算的品階不足 |
| `CharacterIsCastellan` | 33 | **NPC 是不是城主**（grade8+Principal+城鎮 org，見 §2.3） |
| `FavorAtLeast` | 5 | NPC 對太吾**好感類型 ≥ 指定值** |
| `ProfessionFavorAtLeast` | 31 | 依 NPC 行為傾向算的職業好感 ≥ 門檻 |
| `RelationshipNotEnemy` | 24 | 與太吾**非敵對** |
| `CharacterNotTaiwuVillager` | 20 | NPC 非太吾村村民（`OrgTemplateId!=16`） |
| `CharacterNotMonk` | 32 | NPC 非僧 |
| `CharacterBehaviorTypeNeedSatisfy` | 30 | NPC 行為傾向需符合 |
| `CharacterOnOrganizationBlock` | 61 | NPC 正站在自己組織的據點格 |
| `CharacterOnOrganizationRange` | 64 | NPC 在自己組織範圍 |
| `TaiwuAndCharacterNotHusbandOrWife` | 62 | 太吾與 NPC 非夫妻 |
| `TaiwuAndCharacterNotSwornBrotherOrSister` | 63 | 太吾與 NPC 非義兄妹 |
| `CharacterCanBeRecommended` | 55 | NPC 可被舉薦 |
| `TaiwuCanGetTaught` | 54 | 太吾可被該 NPC 傳授 |
| `InteractionOffCooldown` | 52 | 此互動選項對該 NPC 本月未用過（一月一次冷卻） |
| `TaiwuHasItemBySubType` | 27 | 太吾持有某子類道具（消耗品/委託信物） |
| `MoneyMore`/`ResourceMore` | 7/43 | 金錢/資源門檻（建設/委託付費） |

### 2.3 mapper 實作（證明條件確實讀我們要的欄位）【實裝核對】

`GameData.Domains.TaiwuEvent.EventOption.OptionConditionMatcher`（`GameData.dll`，static 方法）：
```csharp
public static bool CharacterInSect(Character arg0)        // ConditionId 21
    => DomainManager.Organization.IsInAnySect(arg0.GetId());

public static bool CharacterIsCastellan(Character arg0) { // ConditionId 33
    OrganizationInfo o = arg0.GetOrganizationInfo();
    return o.Grade == 8 && o.Principal && o.OrgTemplateId >= 21 && o.OrgTemplateId <= 35;  // 城鎮 org 區間
}

public static bool CharacterGradeNotSatisfy(Character arg0)  // ConditionId 23 [Obsolete]
    => EventHelper.CheckSeniorityIsSatisfyByGrade(arg0);     // 依品階查資歷是否滿足

public static bool FavorAtLeast(int arg0, int arg1, sbyte arg2) {  // ConditionId 5
    short fav = DomainManager.Character.GetFavorability(arg0, arg1);
    return FavorabilityType.GetFavorabilityType(fav) >= arg2;
}

public static bool CharacterNotTaiwuVillager(Character arg0)  // ConditionId 20
    => arg0.GetOrganizationInfo().OrgTemplateId != 16;

public static bool InteractionOffCooldown(int arg0, short arg1)  // ConditionId 52
    => DomainManager.TaiwuEvent.IsInteractionEventOptionOffCooldown(arg0, arg1);
```
- `OptionConditionCharacter`（`GameData.dll`）`CheckCondition` 直接 `ConditionChecker(box.GetCharacter("CharacterId"))`——即所有 `Character`→bool 條件吃的就是**被互動 NPC**。
- `OptionConditionFavor`（`GameData.dll`）持 `sbyte FavorType` + `Func<int,int,sbyte,bool>`，把太吾 id、NPC id、門檻丟進 `FavorAtLeast`。

⇒ **條件鏈確實能讀「對方與太吾關係(好感)＋對方是否已有門派(`CharacterInSect`)＋對方品階(`Grade`/`CharacterGradeNotSatisfy`)＋對方城鎮身份(`CharacterIsCastellan`)」。設計要求的條件式選項在原語層完全可行。**

### 2.4 「師徒關係」這個條件怎麼來（設計案例 1 的另一半）

`CharacterInSect` 解決「弟子已有門派則不跳」；「對方是太吾弟子」靠**關係旗標**：
- `EventHelper.CheckHasRelationship(charA, charB, relationFlag)`（`/tmp/be_decomp/.../EventHelper.cs`）被多個 mapper 用（如 `RelationshipNotEnemy` 用 flag 32768、`TaiwuAndCharacterNotHusbandOrWife` 用 1024）。
- 師徒關係 flag：`EventHelper.RelationTypeToNormalInteractionType`（`EventHelper.cs:19109`）顯示 `TeacherSet` 是既有關係型別之一；師徒關係讀寫見本目錄 `02_teach_combat_skill.md` 與 `ApplyRelationBecomeMentor`（§4）。
- ⚠️ **「太吾的弟子」對應的精確 relation flag 數值**未逐位核對（mapper 範例用到的是非敵/配偶/義兄妹等）；做時用編輯器條件 `角色關係` 選「師徒/弟子」即可，不需手填 flag。**標 ⚠️ 待動手時對 `Relation` 列舉核一次。**

---

## 3. 第二層：config 驅動的「角色互動選項」系統（前端互動選單真相）

點 NPC 後彈出的那一排互動選項（交談/贈禮/切磋/學藝…），不是前端硬寫，而是**後端 `TaiwuEventDomain` 依 `InteractionEventOption` config 算出**、前端只負責渲染。這對「路線 b（前端 patch）」的可行性判斷至關重要。

### 3.1 config 型別 `InteractionEventOptionItem` 【實裝核對】

`Config.InteractionEventOptionItem : ConfigItem<…, short>`（`GameData.Shared.dll`）。欄位（節選，全是條件/消耗）：
- 識別/掛接：`short TemplateId`、`string OptionGuid`（**連到某事件包裡某 `TaiwuEventOption` 的 `OptionGuid`**）、`short MutexGroupId`、`EInteractionEventOptionInteractionType InteractionType`、`string Name`。
- **條件欄位（正是我們要的）**：
  - `sbyte[] MinFavorType` / `sbyte[] MaxFavorType`（好感區間）
  - `List<sbyte> BehaviorType` / `List<sbyte> TaiwuBehaviorType`（行為傾向）
  - `List<short> Organization` / `List<short> NonOrganization`（**NPC 屬/不屬哪些門派**）
  - `List<short> OrganizationIdentity`（**組織身份/品階**）
  - `EInteractionEventOptionCompareConsummate CompareConsummate`、`bool AbleJoinSect`、`bool AbleOnOrganizationBlock`
  - `short InteractionFeature`/`InteractionItem`/`TaiwuItem`、`EInteractionEventOptionIdentityAbility IdentityAbility`、`EInteractionEventOptionOrganizationSupport OrganizationSupport`
  - 關係：`ExistentRelation`/`NonexistentRelation`/`TaiwuNonexistentRelation`/`InteractionNonexistentRelation`、`AbleAffectionate`/`AbleNormalMarried`/`AbleMonkMarried`
  - 性別/年齡：`TaiwuGender`/`InteractionGender`/`InteractionMinAge`/`InteractionMaxAge`/`TaiwuMinAge`/`TaiwuMaxAge`
  - 消耗：`ActionPointCost`/`SpiritualDebtCost`/`ExpCost`/`ResourceCost`/`MainAttributeCost`、`bool OncePerMonth`（一月一次冷卻）。

### 3.2 config 與事件選項的綁定 + 顯示判定 【實裝核對】

`GameData.Domains.TaiwuEvent.TaiwuEventDomain`（`GameData.dll`）：
- `_characterInteractionEventOptionList`（行 136）：`List<(TaiwuEventOption, short templateId, TaiwuEventItem)>`。
- `InitCharacterInteractionEventOptionConfigList()`（行 2959）：遍歷所有已載事件包的所有事件選項，**用 `InteractionEventOptionItem.OptionGuid == TaiwuEventOption.OptionGuid` 把 config 條目綁到實際事件選項**。
- `GetVisibleCharacterInteractionEventOptions(int charId)`（行 2998）：對被點 NPC，逐個算該選項的 `IsVisible`/`IsAvailable`（先把 `RoleTaiwu`、`CharacterId` 塞進 ArgBox），回 `Dictionary<short templateId, bool available>`。
- `GetValidInteractionEventOptions(int)`（行 2745）+ `CheckInteractionEventOption(item, targetChar)`（行 2759）：另一層用 config 的消耗/職業技能/資源等粗篩。
- `SetInteractionEventOptionCooldown` / `IsInteractionEventOptionOffCooldown`（行 2800/2805）：`OncePerMonth` 的本月冷卻（`_executedOncePerMonthOptions` 存 `(charId, templateId)`）。

### 3.3 前端只渲染這個結果 【實裝核對】

`/tmp/fe_decomp/MouseTipCharacterOnMapBlock.cs`：
- 行 118-119：`data.VisibleCharacterInteractionEventOptionDict` 有東西才顯示互動區。
- `SetInteractionPanel`（行 516-573）：把 dict 依 `InteractionEventOption.Instance[id].InteractionType` 分組，逐項 `config.Name` 渲染、`available` 決定灰不灰。
- ⇒ **前端互動選單＝後端 `GetVisibleCharacterInteractionEventOptions` 的純展示層**。「能不能出現/能不能執行」全在後端 config + 事件選項條件。

⇒ **結論：要新增一個「互動選單選項」，正規做法＝(1) 在事件包裡定義一個 `TaiwuEventOption`（帶可見/可選條件＋腳本），(2) 在 `InteractionEventOption` config 加一條 `OptionGuid` 指向它。純前端 Harmony 只能改外觀（名字/分組），無法憑空讓一個能執行後端動作的選項出現——因為執行邏輯在後端事件腳本。**

---

## 4. 把選項「插進既有事件/互動」的官方機制：`OptionInjection` / `AddOptionToEvent`

除了「自己做一個 head event」，太吾還有**把自己的選項塞進別人事件**的機制——這對「在原版交談事件上加一條自訂選項」很有用。

### 4.1 事件可借用其他事件的選項：`ExtendEventOptions` 【實裝核對】

`GameData.Domains.TaiwuEvent.TaiwuEvent`（`GameData.dll`）：
- `List<(string srcEventGuid, string optionKey)> ExtendEventOptions`（欄位）。
- `AddOption((string,string) optionInfo)`（行 103）：去重後加入。
- `ToDisplayData()`（行 286-296）：先 `HandleOption` 自己的 `EventOptions`，**再遍歷 `ExtendEventOptions` 把別的事件的選項一起顯示**（`taiwuEvent.ArgBox = ArgBox` 共享上下文）。上限 36 個選項（行 301）。

### 4.2 給事件腳本的注入函數 `OptionInjection`（EventFunction 94）【實裝核對】

`GameData.Domains.TaiwuEvent.FunctionDefinition.BasicFunctions.OptionInjection`（`/tmp/be_decomp/.../BasicFunctions.cs:253-265`，`[EventFunction(94)]`）：
```csharp
int optionIndex = parameters[0].GetIntValue(...);          // 本事件第幾個選項(1-based)
string targetGuid = parameters[1].GetStringValue(...);     // 要注入到哪個事件
DomainManager.TaiwuEvent.GetEvent(targetGuid)
    .AddOption((scriptId.Guid, myEvent.EventConfig.EventOptions[optionIndex-1].OptionKey));
```
⇒ 編輯器裡用「選項注入」函數，把自己的某個選項掛到目標事件（如某個正在進行的互動事件）。

### 4.3 給 mod 程式碼的直呼版 `EventHelper.AddOptionToEvent` 【實裝核對】

`GameData.Domains.TaiwuEvent.EventHelper.EventHelper.AddOptionToEvent(string targetEventGuid, string srcEventGuid, string optionKey)`（`GameData.dll` 行 32177）：
```csharp
if (非空×3) Domain.GetEvent(targetEventGuid)?.AddOption((srcEventGuid, optionKey));
```
- 配套查詢 `EventHelper.GetExtendOptionVisibleCount(string guid, EventArgBox)`（行 32803）。
- ⚠️ **目標事件 GUID**：前端把「標準 NPC 交談事件」的 GUID 寫死為 `567d1caf-8b28-4dbf-8cbe-e746e8ac8cfd`（`EventModel.IsOnNormalInteractEvent`，`/tmp/fe_decomp/EventModel.cs:97`）。這支事件本體在 base game 事件包 DLL（`Event/EventLib`），不在 GameData.dll；**要把選項注入「標準交談」需用此 GUID 當 target，動手前建議反編譯該事件包確認其選項結構與注入時機。標 ⚠️。**

---

## 5. 承載動作：選項腳本 → 後端 API（前後端傳遞）

「聊天選項 → 呼後端 API」這套**完全能承載**收徒/傳授/委託/創派/據點建設。傳遞模型：**前端只送觸發（`OnCharacterClicked` / `EventSelect`），所有動作在後端進程執行**（事件腳本＝C#，跑在後端，可直呼 `EventHelper` 與 `DomainManager.*`）。

### 5.1 選擇選項後回後端：`EventSelect` 【實裝核對】

前端 `TaiwuEventDomainMethod.Call.EventSelect(string eventGuid, string optionKey [, bool isContinue])`（前端 `GameData.Domains.TaiwuEvent/TaiwuEventDomainMethod.cs`）。後端 `TaiwuEventOption.Select(...)` → `OnOptionSelect?.Invoke()` / 跑 `Script` → 執行動作並回傳下個事件 GUID。

### 5.2 各動作的後端入口（均 `EventHelper` static，事件腳本可直呼）【實裝核對 行號】

| 動作 | 後端 API（`EventHelper`，`GameData.dll`） | 備註 |
|---|---|---|
| **收徒（建立師徒）** | `ApplyRelationBecomeMentor(Character self, Character target)`（行 6234） | 反向解除 `ApplyRelationSeverMentor`（6247）；威逼版 `ApplyAddMentorByThreatening`（8085） |
| **傳授武功** | `LearnCombatSkill(int charId, short skillId)`（行 9080） | 細節見 `02_teach_combat_skill.md`（含 `TeachCombatSkill*` 一圈社交副作用版） |
| **委託師傅（鏢局：派人）** | 走「指揮 NPC」軌：太吾村差遣 `TaiwuDomain.SetVillagerWork` 系，或自訂事件寫 NPC 行動目標 | 見 `player_faction_research/04` §3；⚠️ 「請師傅派人去某地」原版無現成自由差遣 API（既有大門派 NPC），需新造 |
| **入派/創派（設身份）** | `JoinOrganization(Character, short settlementId, sbyte grade)`（行 20866）、`ChangeOrganization`、`SetTaiwuAsLeaderOfTaiwuVillage`（30724） | 見 `player_faction_research/04` §1.3 |
| **據點建設** | `CreateSectBuildingForce(sbyte orgTemplateId, short buildingTemplateId)`（行 22025）；建設權 `BuildingDomain.AddTaiwuBuildingArea(ctx, location)` | 見 `player_faction_research/05` §3.2 |

> 條件原語裡 `TaiwuCanGetTaught`(54)、`CharacterCanBeRecommended`(55) 等已是「傳授/舉薦」語境的現成判斷，與這些動作配對天然。

### 5.3 前後端資料怎麼傳

- **觸發**（前端→後端）：`OnCharacterClicked(charId)`（§1.1）、`EventSelect(guid, optionKey)`（§5.1），都是 `GameDataBridge.AddMethodCall`（DomainId=12）。
- **執行**（後端內）：事件腳本拿 `ArgBox.GetInt("CharacterId")` 取 NPC、`DomainManager.Taiwu.GetTaiwuCharId()` 取太吾，呼上表 API；改動經 `DataContext` 寫回存檔。
- **回顯**（後端→前端）：`GetEventDisplayData` / `OnNotifyGameData` 把事件內文＋選項（含 `ExtendEventOptions` 合併後）序列化給前端 `UI_EventWindow` 渲染（最多 28+ 個 `OptionItem` 槽，`/tmp/fe_decomp/UI_EventWindow.cs:41-160`）。

---

## 6. 最省力建議路徑 + 風險

### 6.1 推薦：路線 (a) 官方事件編輯器 + `NpcInteractEvent`

**理由**：條件鏈、選項可見/可選、選項腳本、ArgBox(CharacterId) 全是官方原生；條件式選項要的欄位（門派/品階/城主/好感/師徒）都是現成 condition 原語（§2）；承載動作全是 `EventHelper` 一行式（§5）。膠水碼由編輯器代勞（見 `event_system_modding.md`）。

**最小配方（兩個設計案例直接落地）**：
1. 開 `--enable-event-editor`，建一個事件包，加 head event：`EEventType=NpcInteractEvent`、`TriggerType=CharacterClicked`、`IsHeadEvent=true`。
2. **進入條件**（決定整個事件對哪種 NPC 跳）——可粗篩，細分留給選項可見條件。
3. **創派選項**：可見條件 = `是太吾弟子`(師徒 relation) **AND NOT** `CharacterInSect`(21)；選項腳本呼創派/`JoinOrganization` 流程。
4. **據點建設選項**：可見條件 = `CharacterGradeNotSatisfy`(23)/品階判斷（三品以上）或 `CharacterIsCastellan`(33)；選項腳本呼 `AddTaiwuBuildingArea`/`CreateSectBuildingForce`。
5. 收徒/傳授/委託各做一個選項，配 `InteractionOffCooldown`(52) 之類冷卻。

**若要掛進「標準交談選單」而非獨立彈窗**：再用 `OptionInjection`(EventFunction 94) 或 `EventHelper.AddOptionToEvent` 把選項注入 `567d1caf…`（§4；⚠️ 先驗證該事件包）。或更正規——在 `InteractionEventOption` config 加一條 `OptionGuid` 指向你的選項（§3.2），讓它出現在 hover 互動選單。

### 6.2 路線 (b) 純前端 Harmony patch：不推薦當主力

- 互動選單是後端 config 驅動（§3），純前端 patch 改不了「能執行後端動作的新選項」；只適合微調外觀（改名/分組/灰不灰）。
- 若硬要前端插一個「按鈕→自呼後端 method」，等於繞過官方選項框架，膠水多、跨版脆。

### 6.3 風險分級

| 風險 | 說明 | 等級 |
|---|---|---|
| **後端例外 > 前端例外** | 事件腳本跑在後端進程；未捕捉例外＝後端崩潰、整局凍結/壞檔（比前端 UI 例外只壞一個面板嚴重得多）。`ToDisplayData` 對「無選項」「>36 選項」直接 `throw`（§4.1）。⇒ 條件要保證至少一個選項可見、控制選項數。 | 高 |
| **版本漂移** | 事件包 DLL 由遊戲自帶編譯器對**當前版本**編；換版本可能要重匯出/重編（`event_system_modding.md §7`）。`ConditionId`/`EventTrigger` 常數值跨版可能變動——本檔行號/常數均對 0.0.79.60 核對。 | 中 |
| **`CharacterInSect` 對「克隆世俗派佔位 sect」的語義** | `IsInAnySect` 對 mod 自造的輕量小門派是否回 true，取決於該 org 是否被當 sect（見 `player_faction_research` 命名空間記憶）。⚠️ 需對 mod 自己的 org 型別實測。 | 中 |
| **`CharacterIsCastellan` 的 org 區間寫死 21–35** | `OrgTemplateId >= 21 && <= 35` 才算城主（§2.3）；mod 新 org id 若落在區間外，此條件對 mod 城主回 false。⚠️ 用 mod 自訂城鎮身份時改用 `Grade`/`OrganizationIdentity` 判斷。 | 中 |
| **太吾 `GetInteractionGrade` 回 0** | 既有教訓（`player_faction_research/04` §2.3）：按 grade 開放的判斷對太吾本人可能失效——但本條鏈條件多讀**被互動 NPC** 的 grade（非太吾），影響面較小；仍須留意涉及太吾品階的選項。 | 低-中 |
| **師徒 relation flag 數值** | §2.4 未逐位核對；編輯器用「師徒」條件即可，不必手填。 | 低（待核） |

---

## 7. 關鍵原始碼錨點（速查）

前端（`Assembly-CSharp.dll`，行號為 `/tmp/fe_decomp` 反編譯輸出）：
- 點 NPC 交談 → `UI_CharacterMenuInfo.OnClick`「TalkBtn」：`UI_CharacterMenuInfo.cs:177-183` → `TaiwuEventDomainMethod.Call.OnCharacterClicked`。
- 互動選單渲染：`MouseTipCharacterOnMapBlock.SetInteractionPanel`：`MouseTipCharacterOnMapBlock.cs:516-573`（讀 `VisibleCharacterInteractionEventOptionDict`）。
- 標準交談事件 GUID：`EventModel.cs:97`（`567d1caf-8b28-4dbf-8cbe-e746e8ac8cfd`）。
- 選項槽（≥28）：`UI_EventWindow.cs:41-160`。

後端（`GameData.dll`，行號為 `ilspycmd -t` 輸出）：
- 分流：`TaiwuEventDomain.OnCharacterClicked`（3239）→ `OnEvent_CharacterClicked`（5852）。
- NPC 事件觸發：`NpcEventManager.OnEventTrigger_CharacterClicked`（方法體 140-167，設 `CharacterId` + `CheckCondition`）。
- 條件原語：`EventOption.ConditionId`（常數表）、`EventOption.OptionConditionMatcher`（`CharacterInSect`/`CharacterIsCastellan`/`CharacterGradeNotSatisfy`/`FavorAtLeast` 實作）、`EventOption.OptionConditionCharacter`/`OptionConditionFavor`。
- 選項本體：`Config.EventConfig.TaiwuEventOption`（`IsVisible`/`IsAvailable`/`VisibleConditions`/`OnOptionSelect`）。
- 互動選單 config 系統：`TaiwuEventDomain._characterInteractionEventOptionList`(136)、`InitCharacterInteractionEventOptionConfigList`(2959)、`GetVisibleCharacterInteractionEventOptions`(2998)、`GetValidInteractionEventOptions`(2745)、`CheckInteractionEventOption`(2759)、`Set/IsInteractionEventOptionOffCooldown`(2800/2805)。
- 互動 config 型別：`Config.InteractionEventOptionItem`（`GameData.Shared.dll`）。
- 選項注入：`TaiwuEvent.AddOption`(103)/`ToDisplayData` 合併(286-296)、`BasicFunctions.OptionInjection`(EventFunction 94)、`EventHelper.AddOptionToEvent`(32177)/`GetExtendOptionVisibleCount`(32803)。
- 承載動作：`EventHelper.ApplyRelationBecomeMentor`(6234)、`LearnCombatSkill`(9080)、`JoinOrganization`(20866)、`CreateSectBuildingForce`(22025)。

---

## 8. 待釐清 / 未核對清單

1. ⚠️ **標準交談事件 `567d1caf…` 的選項結構與注入時機**：本體在 `Event/EventLib` 某事件包 DLL，未反編譯。要把自訂選項掛進「標準交談」前，須反編譯該包確認 `OptionInjection`/`AddOptionToEvent` 的目標 optionKey 與觸發點。
2. ⚠️ **師徒 relation flag 精確數值**（§2.4）：編輯器條件夠用，但若要程式判斷需對 `GameData.Domains.Character.Relation` 列舉核一次。
3. ⚠️ **`CharacterInSect`(`IsInAnySect`) 對 mod「克隆世俗派佔位 sect」是否回 true**（§6.3）：決定「創派選項對自家輕量小門派弟子」的可見邏輯，須對 mod org 型別實測。
4. ⚠️ **`CharacterIsCastellan` org 區間 21–35**（§2.3/§6.3）：mod 新城鎮 org id 若超界，城主條件失效；需確認 mod 城鎮 id 落點或改用 `OrganizationIdentity`/`Grade`。
5. ⚠️ **`InteractionEventOption` config 的注入方式**：mod 能否在載入期把新 `InteractionEventOptionItem` 灌進 `InteractionEventOption.Instance`（ConfigData 注入路徑），或須 Harmony？決定「自訂選項出現在 hover 互動選單」是否免 patch。
6. ⚠️ **`OncePerMonth` 冷卻的存檔/重置時機**：`_executedOncePerMonthOptions` 何時清空（過月？），影響委託/收徒類選項的節流設計。
7. ⚠️ **委託「請師傅派人」**：選項可承載，但「既有門派 NPC 自由差遣去某地」原版無入口（`player_faction_research/04` §3.3），需接 NPC 行動目標機制——是承載動作這條最大的新造缺口。
