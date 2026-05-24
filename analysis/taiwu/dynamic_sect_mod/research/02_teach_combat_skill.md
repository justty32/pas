# 傳授武功（收徒 experiment #1 打底）

> 建立：2026-05-24。範圍：「把一個特定武功教給某角色」的後端 API 與機制，NPC 版＋太吾版都涵蓋。為「中小門派」mod 的 experiment #1（收徒與傳授）打底。
>
> **唯一事實來源**：實裝版 **0.0.79.60** 反編譯。下文每條結論標 `【實裝核對】`＝已用 `ilspycmd -t` 對實裝 DLL 驗證；`【舊源】`＝僅看較舊參考源 `~/dev/taiwu-src/`（行為穩定但簽名可能漂移，已盡量交叉比對）。
> - 後端：`…/The Scroll Of Taiwu/Backend/GameData.dll`
> - 前端：`…/The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`
>
> 先讀過並建立在其上：`player_faction_research/02_sect_member_npc_setup.md`（§2 武功指派）、`details/martial_arts_mod_anatomy.md`、`details/sect_skill_favor_ui.md`、`progress.md`。**未動 session_log.md，未 git add/commit。**

---

## 0. 一句話結論

- **「教某角色一個特定武功」最省力的後端 API ＝ `CharacterDomain.LearnCombatSkill(ctx, charId, skillTemplateId, readingState)`**（`GameData.dll` `CharacterDomain.cs:4248`，`[DomainMethod]`）。它對 **任意 charId** 都成立——太吾、NPC 共用同一支；太吾版 `TaiwuDomain.TaiwuLearnCombatSkill` 只是它的薄包裝。**無祕笈前提、無造詣/品階門檻**，唯一硬性檢查是「該角色尚未學過此武功」（學過會丟 Exception）。
- **遊戲裡確實有現成的「傳授」語義**：`Character.GetTeachableCombatSkillBookIds` + `TeachCombatSkillAction`（命名空間 `…Character.Ai.GeneralAction.TeachRandom`）。它是 NPC 過月「主動把自己會、對方不會的武功教給對方」的完整行動物件，`ApplyChanges` 內部最終仍呼 `targetChar.LearnNewCombatSkill(...)`，並附帶生平記錄、好感/心情變化、密報。**「傳授」＝「`LearnCombatSkill` ＋一圈社交副作用」**。
- 因此 mod 有兩個層級可選：
  1. **只要「弟子學會」**：直接 `LearnCombatSkill` 一行解決（最省力、可控）。
  2. **要「像原版那樣有師徒傳授感」（生平、好感、密報、按頁傳授）**：複用 `TeachCombatSkillAction`，`new` 它填四個欄位後呼 `action.ApplyChanges(ctx, 師傅, 弟子)`。

---

## 1. 後端核心 API：`CharacterDomain.LearnCombatSkill`

### 1.1 實裝簽名與方法體 【實裝核對】
`GameData.dll` → `GameData.Domains.Character.CharacterDomain.cs:4247-4257`：

```csharp
[DomainMethod]
public void LearnCombatSkill(DataContext context, int charId, short skillTemplateId, ushort readingState = 0)
{
    Character element_Objects = GetElement_Objects(charId);
    List<short> learnedCombatSkills = element_Objects.GetLearnedCombatSkills();
    if (learnedCombatSkills.Contains(skillTemplateId))
        throw new Exception($"Combat skill already learned. TemplateId:{skillTemplateId}");
    element_Objects.LearnNewCombatSkill(context, skillTemplateId, readingState);
}
```

> **與既有調查的差異訂正**：`player_faction_research/02_sect_member_npc_setup.md` §2.3 記為 `CharacterDomain.cs:3984`，且把 `readingState` 寫成第 4 參。**簽名正確（4 參、`ushort readingState=0`）但行號在實裝版是 4248 而非 3984**（舊源漂移，不影響結論）。

**前提核對**：
- ❌ **不需要先有祕笈**——方法體完全沒碰 Item/SkillBook。
- ❌ **不需要造詣/品階門檻**——沒有任何 attainment/qualification/grade 檢查。
- ✅ **唯一硬性檢查**：`learnedCombatSkills.Contains(skillTemplateId)` ＝已學過就丟 Exception。**mod 呼叫前務必先查 `GetLearnedCombatSkills().Contains(id)` 防重，否則崩。**
- `skillTemplateId` ＝ `Config.CombatSkill` 的武功 template id（**不是** SkillBook 物品 id）。

### 1.2 `readingState` 是什麼 【實裝核對】
`readingState`（`ushort`）＝**該武功「已讀頁面」的 bit mask**，每個 bit 對應一頁（內頁 internal index）。
- 證據：`TeachCombatSkillAction.ApplyChanges` 用 `(ushort)(1 << (int)InternalIndex)` 當 readingState（`TeachCombatSkillAction.cs:54`）＝「只開教的那一頁」。
- 過月自然修煉路徑也用 `1 << pageInternalIndex` 逐頁累加（`Character.cs:9968`）。
- `readingState = 0`（預設）＝**一頁都沒讀的「空殼」**：武功掛上去了、列在已學清單，但沒有任何頁面修煉度（要靠之後讀祕笈/過月才填頁）。
- 底層：`LearnNewCombatSkill`（`Character.cs:3196`）→ `DomainManager.CombatSkill.CreateCombatSkill(_id, skillTemplateId, readingState)`（`CombatSkillDomain.cs:832`）→ `new CombatSkill(charId, skillTemplateId, readingState)`，把 readingState 直接灌進 CombatSkill 實體。

> **傳授起始修煉度怎麼設**：
> - 想「弟子立刻會、但要自己練」→ `readingState = 0`。
> - 想「弟子直接會第 0 頁」→ `readingState = 1`（`1 << 0`）。
> - 想「弟子整本通透」→ 灌滿對應頁數的 bit（可抄師傅的：`師傅CombatSkill.GetReadingState()`，見 §3）。

### 1.3 `LearnNewCombatSkill` 的副作用（太吾特例）【實裝核對】
`Character.cs:3196-3207`：除了建 CombatSkill＋加進 `_learnedCombatSkills`，**若 charId 是太吾**會多做：`DomainManager.Taiwu.RegisterCombatSkill(ctx, skill)` ＋ `AddLegacyPoint(ctx, 20)`（加 20 傳承點）。NPC 則只是單純掛上。

### 1.4 其他學武入口（核對結論：沒有「另一支獨立 API」）【實裝核對】
- `CharacterDomain` 內所有「讓角色擁有武功」的路徑只有兩類：
  1. **`LearnCombatSkill` → `LearnNewCombatSkill`**（單一武功，運行時主動學）；
  2. **`DomainManager.CombatSkill.RegisterCombatSkills(charId, List<CombatSkill>)`**（`CharacterDomain.cs:5219/16655/27676/…` 多處），這是**生成期/離線批次**把一整批 `CombatSkill` 實體掛給角色（如 `OfflineCreateIntelligentCharacter`、輪迴繼承等），**不是運行時的「教一個」API**。
- 所以「運行時教某角色一個特定武功」的唯一入口就是 `LearnCombatSkill`（及其太吾包裝 `TaiwuLearnCombatSkill`）。
- 對照組：`GetCombatSkillToLearn`（`Character.cs:8686`，private）只是「過月自學清單產生器」——依角色當前職位 config 的 `CombatSkills` 算出「下一個該學的武功/該讀的頁」，回給過月供應流程，**它本身不教，只列清單**（與既有調查一致）。

---

## 2. 現成的「傳授」語義：`TeachCombatSkillAction`

**結論：遊戲有現成「A 主動把某武功傳授給 B」的機制**，不必只靠 raw `LearnCombatSkill` 自己拼。grep `Teach*` 命中以下實體（NPC 過月行動體系）：

### 2.1 可傳授清單：`Character.GetTeachableCombatSkillBookIds` 【實裝核對】
`Character.cs:13454-13470`：

```csharp
public void GetTeachableCombatSkillBookIds(Character targetChar, List<(short, short)> weightTable)
{
    var charCombatSkills = DomainManager.CombatSkill.GetCharCombatSkills(_id);
    foreach (short learnedCombatSkill in _learnedCombatSkills) {
        CombatSkillItem cfg = Config.CombatSkill.Instance[learnedCombatSkill];
        if (cfg.BookId >= 0
            && charCombatSkills[learnedCombatSkill].GetReadingState() != 0   // 師傅自己至少讀過一頁
            && !targetChar._learnedCombatSkills.Contains(learnedCombatSkill)) // 弟子還沒學
        {
            int weight = 3 << 8 - cfg.Grade;       // 品階越低權重越高
            if (cfg.IsNonPublic) weight /= 3;       // 不外傳武功權重打 1/3
            weightTable.Add((cfg.BookId, (short)weight));   // 注意：存的是 BookId，非 skill id
        }
    }
}
```
配套布林：`Character.CanTeachCombatSkill(targetChar)`（`Character.cs:13429`）＝上面條件「存在至少一個」。

### 2.2 行動觸發：`OfflineCalcGeneralAction_TeachSkill` 【實裝核對】
`Character.cs:13486-13565`（過月 general action）：選一個對象 → `GetTeachableCombatSkillBookIds` 取加權表 → 隨機抽一本書 → 用 `GetTaughtNewSkillSuccessRate` 算成功率 → 包成 `TeachCombatSkillAction` 丟進 `mod.PerformedActions`。耗 action energy type 4。
- 對象來源：`caringCharIds`（在意的人）優先，否則同格 `currBlockChars`，篩選器 `IsValidTargetForTeachSkill` ＝ `CanTeachCombatSkill || CanTeachLifeSkill`。
- 同類場景另有 `Sect.cs:1015-1057`（峨眉關押教功）也是這套：建 `TeachCombatSkillAction` → `action.ApplyChanges(ctx, character, targetChar)`。**這是「A 教 B 一個特定武功」最完整的範本呼叫法。**【舊源，已交叉比對 `TeachCombatSkillAction` 實裝一致】

### 2.3 結果套用：`TeachCombatSkillAction.ApplyChanges`（最關鍵）【實裝核對】
`GameData.Domains.Character.Ai.GeneralAction.TeachRandom.TeachCombatSkillAction`（`GameData.dll` 與舊源逐行一致核對通過）：

```csharp
public class TeachCombatSkillAction : IGeneralAction
{
    public short SkillTemplateId;      // 要教的武功 template id
    public byte  InternalIndex;        // 教哪一頁（內頁 index）
    public byte  GeneratedPageTypes;   // 該頁正/逆練類型（給太吾領祕笈用）
    public bool  Succeed;              // 是否教成功（外部用成功率擲骰決定）

    public bool CheckValid(Character self, Character target)
        => !target.GetLearnedCombatSkills().Contains(SkillTemplateId);

    public void ApplyChanges(DataContext ctx, Character selfChar, Character targetChar)
    {
        short bookId = Config.CombatSkill.Instance[SkillTemplateId].BookId;   // skill → book
        SkillBookItem bookCfg = Config.SkillBook.Instance[bookId];
        byte pageId = CombatSkillStateHelper.GetPageId(InternalIndex);
        if (Succeed) {
            lifeRecord.AddLearnCombatSkillWithInstructionSucceed(target, ..., bookId, pageId+1);
            if (targetCharId == 太吾) {                                       // 教給太吾→還會塞一本祕笈進背包
                ItemKey k = DomainManager.Item.CreateDemandedSkillBook(ctx, bookId, InternalIndex, GeneratedPageTypes);
                targetChar.AddInventoryItem(ctx, k, 1);
            }
            targetChar.LearnNewCombatSkill(ctx, SkillTemplateId, (ushort)(1 << InternalIndex));  // ★ 真正學會
            targetChar.ChangeHappiness(ctx, bookCfg.BaseHappinessChange);
            DomainManager.Character.ChangeFavorabilityOptionalMonthlyEvolution(ctx, targetChar, selfChar, bookCfg.BaseFavorabilityChange);
        } else {
            lifeRecord.AddLearnCombatSkillWithInstructionFail(...);
        }
        // 不論成敗都加一筆「指點武學」密報
        secretInfo.AddInstructOnCombatSkill(selfCharId, targetCharId, SkillTemplateId);
    }
}
```

> **這證明「傳授」＝薄薄一層社交包裝在 `LearnNewCombatSkill` 之上**：核心一行就是 `targetChar.LearnNewCombatSkill(ctx, SkillTemplateId, 1 << InternalIndex)`。差別只在 `TeachCombatSkillAction` 額外給：生平記錄（succeed/fail）、心情、好感、密報，且**只教一頁**（`1 << InternalIndex`）。

### 2.4 成功率：`Character.GetTaughtNewSkillSuccessRate` 【實裝核對】
`Character.cs:10109-10121`（static）：
```csharp
public static int GetTaughtNewSkillSuccessRate(sbyte grade, short qualification, short attainment, sbyte cleverness)
{
    var gd = SkillGradeData.Instance[grade];
    if (attainment   > gd.ReadingAttainmentRequirement)     return 100;
    if (qualification> gd.PracticeQualificationRequirement) return 100;
    return Math.Max((cleverness + attainment*100/gd.ReadingAttainmentRequirement)/2,
                    (cleverness + qualification*100/gd.PracticeQualificationRequirement)/4);
}
```
> 這是**弟子端**的學成機率：吃弟子的「該類武學造詣 attainment／資質 qualification／悟性 cleverness（personality[1]）」對上「武功品階要求」。**注意這只決定 `Succeed` 旗標**——若 mod 直接呼 `LearnCombatSkill` 則完全繞過此擲骰（必定學會）。

---

## 3. 傳授門檻（彙整）

| 問題 | 用 raw `LearnCombatSkill` | 用 `TeachCombatSkillAction`（原版傳授語義） |
|------|------|------|
| 師傅必須自己會該武功？ | **否**（API 不檢查師傅）。mod 可讓「不會的人」教，甚至無師傅。 | **是**——`GetTeachableCombatSkillBookIds` 只列「師傅 `_learnedCombatSkills` 內、且 `ReadingState != 0`（至少讀過一頁）」的武功。 |
| 武功要有祕笈（BookId）？ | **否** | **是**——`cfg.BookId >= 0` 才可傳授（無書武功不進清單）。 |
| 造詣/品階門檻？ | **無** | 門檻反映在**成功率**（§2.4），不是硬擋；造詣/資質夠高直接 100%。 |
| 弟子起始 readingState？ | mod 自訂（0＝空殼、`1<<n`＝開某頁、抄師傅 = 滿頁） | 固定「教師傅已讀的最低一頁」：`InternalIndex` ＝師傅 `readingState` 第一個已讀 bit，弟子拿 `1 << InternalIndex`（一次一頁）。 |
| 弟子已學過？ | API 丟 Exception，**呼叫前自己防重** | `CheckValid` / 清單篩選都已排除已學者。 |

**收徒 experiment #1 的門檻設計建議**：
- 想要「資料驅動、可組合條件」的傳授原語（design_vision 的方向），門檻不該寫死，建議把「師傅須會此武功」「弟子造詣門檻」「起始頁數」做成 mod 端可選 flag，行為一律落到 `LearnCombatSkill`。
- 若要復刻「會失敗、有師徒感」，照抄 §2.4 算成功率 + §2.3 `TeachCombatSkillAction.ApplyChanges`。

---

## 4. 祕笈路徑（發書讓對方自學）vs 直接 LearnCombatSkill

### 4.1 `CreateSkillBook` 簽名（訂正 progress.md 的提醒）【實裝核對】
`GameData.dll` → `ItemDomain.cs`，有三個 overload：
- `CreateSkillBook(ctx, short templateId, sbyte completePagesCount=-1, sbyte lostPagesCount=-1, sbyte outlinePageType=-1, sbyte normalPagesDirectProb=50, bool outlineAlwaysComplete=true)`（`:2516`）
- `CreateSkillBook(ctx, short templateId, byte pageTypes, sbyte completePagesCount=-1, sbyte lostPagesCount=-1, bool outlineAlwaysComplete=true)`（`:2525`）
- `CreateSkillBook(ctx, short templateId, ushort activationState)`（`:2534`）

**第一參 `templateId` ＝ SkillBook 物品 config id**（`Config.SkillBook.Instance[templateId]`），**不是武功 id**——與 progress.md 一致。
- **武功 id → 祕笈 id 的橋**：`Config.CombatSkill.Instance[skillId].BookId`（在 `TeachCombatSkillAction.cs:43`、`GetTeachableCombatSkillBookIds` 都這樣轉）。`BookId < 0` ＝該武功無對應祕笈（無法走發書路）。
- 另有 `CreateDemandedSkillBook(ctx, short templateId, byte ensuredPageIndex, byte pageTypes=0)`（`:2493`）＝造「保證含某頁」的祕笈，正是傳授給太吾時用的（`TeachCombatSkillAction` succeed 分支）。

### 4.2 兩種傳授實作比較

| | (A) 直接 `LearnCombatSkill` | (B) 發祕笈讓對方自學 |
|--|------|------|
| 弟子是否「立刻會」 | ✅ 當下就掛進已學清單 | ❌ 只是拿到一本書，要對方自己讀（過月/手動）才會 |
| 呼叫成本 | 一行（＋防重） | 造書 `CreateSkillBook(bookId,...)` → `targetChar.AddInventoryItem(ctx, itemKey, 1)`；NPC 是否真的讀還受其過月 AI／造詣影響 |
| 控制弟子修煉度 | 直接用 `readingState` 精準設 | 由祕笈完整度 + 對方讀書成功率決定，**不可控** |
| 適合 | 「收徒即傳功」「保證學會」的 mod 行為 | 「賜書」「給線索讓 NPC 自然成長」的軟性傳授 |
| 對太吾 | `TaiwuLearnCombatSkill` 直接會 | 太吾要自己進讀書 UI 讀 |

> **結論：experiment #1（收徒傳授）主線用 (A) `LearnCombatSkill`**——直接、可控、可設起始頁。(B) 發書當「補充風味」（賜書橋段）即可。原版 `TeachCombatSkillAction` 其實是 **(A) 為主**（直接 `LearnNewCombatSkill`），只在「教給太吾」時 **額外** 塞一本書當紀念（不是靠書才學會）。

---

## 5. 太吾傳授（玩家把自己會的武功傳給弟子）

### 5.1 後端：同一支 API 【實裝核對】
- `TaiwuDomain.TaiwuLearnCombatSkill(ctx, short skillTemplateId, ushort readingState=0)`（`TaiwuDomain.cs:3831`）**只是 `CharacterDomain.LearnCombatSkill(ctx, _taiwuCharId, …)` 的包裝**（外加把暫存的「未學武功讀書進度」轉正）。
- 所以「太吾教弟子」根本不需要 Taiwu 專用 API——直接 `CharacterDomain.LearnCombatSkill(ctx, 弟子charId, skillId, readingState)` 即可（弟子是普通 NPC）。**「太吾 vs NPC」在後端是同一支 `LearnCombatSkill(任意 charId)`。**
- 前端可呼叫的 domain method（mod 從前端觸發時用）：`CharacterDomainMethod.Call.LearnCombatSkill(int charId, short skillTemplateId, ushort readingState)`（`Assembly-CSharp.dll`，內部 `GameDataBridge.AddMethodCall(-1, 4, 91, charId, skillTemplateId, readingState)`，即 **DomainId=4(Character)、MethodId=91**）。
  - ⚠️ **類名/methodId 漂移**：舊源寫 `CharacterDomainHelper.MethodCall.LearnCombatSkill` 且 `const = 92`；實裝版類名已改 `CharacterDomainMethod.Call`、methodId 已變 **91**（92 變成 `LearnLifeSkill`）。與 `sect_skill_favor_ui.md` 記的 `OrganizationDomainHelper→OrganizationDomainMethod` 同類漂移。

### 5.2 前端入口（粗略；細節屬「太吾互動選項」那支）
原版「太吾傳授」是一條**講師/品鑒系 profession ultimate**的複雜流程，不是單純聊天選項：
- 開窗：`DisplayEventHandler.HandleDisplayEvent_OpenMultiSelectSkillBook(bool isCombatSkillBook)`（`Assembly-CSharp.cs`，舊源 `DisplayEventHandler.cs:1824`）→ 開 `UI_MultiSelectSkillBook`（太吾選要傳的祕笈，`level = GlobalConfig.TeachSkillBookSelctMaxCount`）。
- 選完對象/書 → 後端算出 `TasterUltimateResult` → `UI_MultiSelectSkillBook.OpenTeachSkillResultConfirm` → 開 `UI_TeachCombatSkillResultConfirm`（`Assembly-CSharp`，舊源 `UI_TeachCombatSkillResultConfirm.cs:13`）顯示「教成功率 + 好感/關係變化預覽」，確認後套用。
- 即太吾版前端是「**多選祕笈 + 多選弟子 + 結果確認**」的批次傳功 UI（綁 profession skill 觸發），**比 mod 自己接一個聊天選項重很多**。

> **給 mod 的選擇**：experiment #1 不必複刻這套 profession UI。最省力＝在 mod 自訂的「收徒/傳授」互動選項（另一支調查負責 UI 接點）回呼裡直接呼後端 `LearnCombatSkill(弟子charId, skillId, readingState)`，或走 §2.3 `TeachCombatSkillAction.ApplyChanges` 取得原版社交副作用。

---

## 6. 給 experiment #1 的最省力配方

1. **「收徒即傳功」核心一行**（後端，弟子 charId 已知）：
   ```csharp
   var learned = DomainManager.Character.GetElement_Objects(discipleId).GetLearnedCombatSkills();
   if (!learned.Contains(skillId))
       DomainManager.Character.LearnCombatSkill(ctx, discipleId, skillId, readingState);  // readingState=0 空殼，或抄師傅
   ```
2. **要原版師徒傳授感**（生平/好感/心情/密報、按頁）：
   ```csharp
   new TeachCombatSkillAction {
       SkillTemplateId = skillId,
       InternalIndex   = 師傅該武功 readingState 的第一個已讀頁,
       GeneratedPageTypes = CombatSkillStateHelper.GeneratePageTypesFromReadingState(ctx.Random, 師傅readingState),
       Succeed = true   // 或用 GetTaughtNewSkillSuccessRate 擲骰
   }.ApplyChanges(ctx, 師傅Char, 弟子Char);
   ```
3. **太吾教弟子**：同 1./2.，charId 填弟子；太吾自己學則 `TaiwuLearnCombatSkill` 或 `LearnCombatSkill(太吾charId,…)`。
4. **賜書（軟傳授）**：`bookId = Config.CombatSkill.Instance[skillId].BookId`（須 `>=0`）→ `var k = DomainManager.Item.CreateSkillBook(ctx, bookId, …)` → `disciple.AddInventoryItem(ctx, k, 1)`。

---

## 7. 待釐清 / 未核對清單

1. **【未對 DLL 核對】`CombatSkillStateHelper` 的頁面 bit 細節**：`GetPageId`/`IsPageRead`/`GetNextPageToRead`/`GeneratePageTypesFromReadingState` 的精確位元佈局（哪些 bit 是正練/逆練/綱目頁）未逐一展開；目前只確認 readingState 是「每頁一 bit、`1<<index`」。若 mod 要精準構造「某頁開、某頁逆練」需再 dump 此 helper。
2. **【未核對】`SkillGradeDataItem.ReadingAttainmentRequirement / PracticeQualificationRequirement`** 的實際數值（成功率公式吃這兩個 config 欄位）——只看了公式，沒看 config 值；若要調傳授成功率手感需查 `SkillGradeData` config。
3. **【粗略】太吾前端傳授 UI 鏈**：`UI_MultiSelectSkillBook` → `TasterUltimateResult` 後端算法（`ProfessionSkillHandle`/`TasterUltimateResult`）未深入——這是「太吾互動選項」另一支調查的範疇，本支只確認「後端落到同一支 `LearnCombatSkill`」。
4. **【未驗】mod 自呼 `TeachCombatSkillAction.ApplyChanges` 的時機安全性**：它會寫 LifeRecord/SecretInformation/MonthlyEvent collection，在過月平行段外（如事件回呼、AdvanceMonth 鉤）呼叫是否安全，沒實機跑過（記憶提示：過月平行段勿寫全域）。建議在 `AdvanceMonthBegin/Finish` 鉤的單執行緒段呼叫。
5. **行號漂移彙整**（建議綁簽名時點對點再核）：`LearnCombatSkill` 實裝 `:4248`（舊源記 `:3984`）；前端 domain method 類名 `CharacterDomainMethod.Call`（舊 `CharacterDomainHelper.MethodCall`）、methodId **91**（舊 const 92）。

---

## 附：本支實裝核對清單
- 【實裝核對 ✅】`CharacterDomain.LearnCombatSkill`（`:4248`，`[DomainMethod]`，方法體）— `GameData.dll`
- 【實裝核對 ✅】`Character.LearnNewCombatSkill`（`:3196`）、`GetCombatSkillToLearn`（`:8686`）、`GetTeachableCombatSkillBookIds`（`:13454`）、`CanTeachCombatSkill`（`:13429`）、`OfflineCalcGeneralAction_TeachSkill`（`:13486`）、`GetTaughtNewSkillSuccessRate`（`:10109`）— `GameData.dll`
- 【實裝核對 ✅】`TeachCombatSkillAction`（`…Ai.GeneralAction.TeachRandom`，全類逐行與舊源一致）— `GameData.dll`
- 【實裝核對 ✅】`TaiwuDomain.TaiwuLearnCombatSkill`（`:3831`）、`IsTaiwuAbleToGetTaught`（`:5083`）— `GameData.dll`
- 【實裝核對 ✅】`ItemDomain.CreateSkillBook` ×3 overload（`:2516/2525/2534`）、`CreateDemandedSkillBook`（`:2493`）、`CombatSkillDomain.CreateCombatSkill`（`:832`）— `GameData.dll`
- 【實裝核對 ✅】`OrganizationDomain.GetHighestGradeOfTeachableCombatSkill`（approval→可教品階，與「教某特定武功」無關，僅釐清語義）— `GameData.dll`
- 【實裝核對 ✅】前端 `CharacterDomainMethod.Call.LearnCombatSkill(int,short,ushort)` → `AddMethodCall(-1,4,91,…)` — `Assembly-CSharp.dll`
- 【舊源，已交叉比對】`Sect.cs` 教功範本呼叫、`DisplayEventHandler`/`UI_MultiSelectSkillBook`/`UI_TeachCombatSkillResultConfirm` 太吾前端鏈（屬另一支範疇，僅粗查）— `~/dev/taiwu-src/Assembly-CSharp/`
