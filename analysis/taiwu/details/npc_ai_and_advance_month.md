# NPC AI 與過月行為（Advance Month）剖析

> 日期：2026-05-23
> 範圍：定位《太吾繪卷》NPC 的「世界行為 AI」「戰鬥 AI」與「過月模擬管線」三套系統的實際程式碼，並標出做 mod 的精準切入點。
> 來源：反編譯後端 `~/dev/taiwu-src/backend/`（GameData.dll，獨立 .NET 6 進程）。**所有 NPC 模擬都在後端**，故相關 mod 必須是 Backend plugin（net6.0，引用 `<遊戲>/Backend/` 的 GameData.* dll）。

---

## 0. 三層結構（先分清「哪個 AI」）

「NPC 的 AI」在太吾裡其實是**三套互不相干的系統**，動手前要先確認你要改的是哪一層：

| 層 | 管什麼 | 程式位置 | 觸發時機 |
|---|---|---|---|
| **A. 世界行為 AI** | 過月時 NPC「去做什麼」（復仇、入門派、探索、偷搶、教學、求醫…） | `GameData/Domains/Character/Ai/` | 每次過月（`PeriAdvanceMonth`） |
| **B. 戰鬥 AI** | 戰鬥中「怎麼出招、換兵器、改招式」 | `GameData/Domains/Combat/Ai/`（行為樹）+ 遊戲內 `AiEditor` | 進戰鬥時 |
| **C. 過月模擬管線** | 整個世界每月推進的編排（誰先誰後、世界級事件） | `GameData/Domains/World/WorldDomain.cs` | `WorldDomain.AdvanceMonth` |

A 與 C 緊密耦合（A 是 C 的其中幾個階段），B 獨立。

---

## 1. 過月主管線（C 層）

**總入口**：`World/WorldDomain.cs:7067` `public void AdvanceMonth(DataContext context)`

```
AdvanceMonth(context)                                  // WorldDomain.cs:7067
├─ 清理上月暫存（商隊、情報、綁架…）
├─ DomainManager.Character.ResetAllAdvanceMonthStatus()
├─ Events.RaiseAdvanceMonthBegin(context)              // ★ 事件鉤 1
├─ 主線進度 >= 3 ？
│   ├─ PreAdvanceMonth(context, monitor)               // WorldDomain.cs:8427
│   ├─ PeriAdvanceMonth(context, monitor)              // WorldDomain.cs:7214 ← NPC 決策都在這
│   └─ PostAdvanceMonth(context, monitor)              // WorldDomain.cs:8203
│   （早期則走 *_BornArea 變體）
├─ CheckMonthlyEvents(context)                         // 世界級月度事件結算
└─ SetAdvancingMonthState(20, ...)                     // 等玩家看完通知
```

過月結束（玩家關掉月度通知）後：`AdvanceMonth_DisplayedMonthlyNotifications`（WorldDomain.cs:7122）→ `Events.RaiseAdvanceMonthFinish(context)` ★ 事件鉤 3 → 存檔。

### 1.1 PeriAdvanceMonth 的階段（WorldDomain.cs:7214）

逐角色決策用 `WorkerThreadManager.Run(階段方法, ...)` **依地區平行**跑。`SetAndNotifyAdvancingMonthState(context, N, ...)` 的 N 是進度碼，順序如下：

| 狀態碼 | 階段（worker 方法） | 對應 ParallelModification | 內容 |
|---:|---|---|---|
| 2 | `_UpdateCharacterStatus` / `_CharacterMixedPoisonEffect` | `PeriAdvanceMonthUpdateStatusModification` | 更新狀態、中毒結算 |
| 4 | `_CharacterSelfImprovement(+PracticeAndBreakout / LearnNewSkills)` | `PeriAdvanceMonthSelfImprovementModification` + `PracticeAndBreakoutModification` | NPC 練功、突破、學新技能 |
| 5 | `_CharacterActivePreparation(+GetSupply)` | `PeriAdvanceMonthActivePreparationModification` + `...GetSupplyModification` | 主動補給、備裝 |
| 6 | `_CharacterPassivePreparation` | `PeriAdvanceMonthPassivePreparationModification` | 被動準備 |
| 7 | `_CharacterRelationsUpdate` | `PeriAdvanceMonthRelationsUpdateModification` | 關係/好感更新 |
| 8 | `_CharacterPersonalNeedsProcessing` | — | 處理個人需求（PersonalNeed） |
| 9 | `_CharacterPrioritizedAction` | `PrioritizedActionModification` | **★ 優先級行動（A 層上半）** |
| 10 | `_CharacterGeneralAction` | `PeriAdvanceMonthGeneralActionModification` | **★ 一般行動（A 層下半）** |
| 11 | `_CharacterFixedAction` | `PeriAdvanceMonthFixedActionModification` | 固定行動（村民工作、逃犯團…） |

> 第 9/10/11 三步被 `disableAiActions` 旗標整段跳過（主線「神遊」橋段用），可見這三步＝NPC「自主決策」核心；前面 2~8 是狀態結算與準備。

### 1.2 平行執行的鐵則（改 A 層必懂）

每個 `PeriAdvanceMonth_Execute*` 方法跑在 **worker thread**，因此遊戲用「**先算、後套用**」兩段式避免資料競爭：

1. **平行階段**（worker thread）：`Character.PeriAdvanceMonth_Execute*(context)` 只**計算決策**，把結果塞進一個 `*Modification` 物件，再 `context.ParallelModificationsRecorder.RecordParameterClass(mod)` 排隊。**不可在此直接改全域狀態。**
2. **串行套用階段**（主執行緒）：`Character.ComplementPeriAdvanceMonth_Execute*(context, mod)` 把排隊的決策真正套用（扣資源、移動、加 buff…）。

> 每個行動方法都成對出現 `PeriAdvanceMonth_ExecuteXxx`（算）+ `ComplementPeriAdvanceMonth_ExecuteXxx`（套用）。Harmony patch A 層時務必認清你 patch 的是哪一段——在平行段做寫入＝偶發崩潰/存檔損毀。

---

## 2. 世界行為 AI：優先級行動（A 層上半）

NPC 每月先選一個「優先級行動」（劇情/強制性的高優先行為），選不到才退回「一般行動」。

### 2.1 決策迴圈

`Character/Character.cs:16577` `PeriAdvanceMonth_ExecutePrioritizedAction(DataContext)`：

```csharp
// 取現有行動的優先級
int prevPriority = config[prevAction].BasePriority + config[prevAction].MoralityPriority[behaviorType];
// 遍歷整張優先級行動表，擇優
for (short i = 0; i < PrioritizedActions.Instance.Count; i++) {
    var config = PrioritizedActions.Instance[i];
    int priority = config.BasePriority + config.MoralityPriority[behaviorType]; // ← 道德傾向決定偏好
    if (priority > prevPriority && (!hasPrev || config.IsPrevActionInterrupted)
        && !DomainManager.Extra.IsPrioritizedActionInCooldown(_id, i)) {
        var action = PrioritizedActionType.TryCreatePrioritizedAction(context, this, i, ref conditions); // ← 各行動自己的成立條件
        if (action != null) { mod.Action = action; prevPriority = priority; }
    }
}
```

兩個關鍵旋鈕：
- **資料層**：`PrioritizedActions` 設定表（ConfigCell，欄位見 `Config/PrioritizedActionsItem.cs`）：`BasePriority`、`MoralityPriority[behaviorType]`（5 種道德型各一個權重）、`ActionCoolDown`、`Duration`、`IsAdultOnly` / `IsNonLeader` / `IsNonMonk` / `OrgTemplateId` / `OrgGrade` 等門檻。
- **程式層**：`Character/Ai/PrioritizedActionType.cs` 的 `TryCreateAction_<名稱>` 各方法（每個行動「能不能成立、目標選誰、走多久」的硬編碼邏輯）。

### 2.2 行動型別表（`PrioritizedActionType.CreatePrioritizedAction` switch，templateId → 類別）

| Id | 行動 | 類別檔（`Character/Ai/PrioritizedAction/`） |
|---:|---|---|
| 0 | 入門派 | JoinSectAction |
| 1 | 赴約（太吾召喚） | AppointmentAction |
| 2/3 | 保護/營救親友 | Protect/RescueFriendOrFamilyAction |
| 4 | 弔唁 | MournAction |
| 5 | 探訪親友 | VisitFriendOrFamilyAction |
| 6/7 | 尋寶/找特殊材料 | FindTreasure/FindSpecialMaterialAction |
| 8 | 復仇 | TakeRevengeAction |
| 9 | 爭奪傳承之書 | ContestForLegendaryBookAction |
| 10 | 收養嬰兒 | AdoptInfantAction |
| 11~16 | 各門派劇情行為（遠山殺魔、峨眉同門相殘、百花治狂…） | SectStory*Action |
| 17~20 | 追緝逃犯、越獄、尋求庇護、押送囚犯 | HuntFugitive/EscapeFromPrison/SeekAsylum/EscortPrisonerAction |
| 21 | 村民職務安排 | VillagerRoleArrangementAction |
| 22 | 截命門追殺太吾 | HuntTaiwuAction |
| — | （基類抽象）可擴充行動 | `BasePrioritizedAction` / `ExtensiblePrioritizedAction` |

每個行動類繼承 `BasePrioritizedAction`（`Character/Ai/PrioritizedAction/BasePrioritizedAction.cs`），可覆寫：`CheckValid` / `OnStart` / `OnInterrupt` / `OnArrival` / `Execute` / `OnCharacterDead`，外加自訂序列化（`ExtensiblePrioritizedAction` 是給變長欄位用的基類）。

---

## 3. 世界行為 AI：一般行動（A 層下半）

選不到優先級行動時，跑「一般行動」——按**需求類別**分組的日常行為。介面 `Character/Ai/GeneralAction/IGeneralAction.cs`：

```csharp
public interface IGeneralAction {
    sbyte ActionEnergyType { get; }
    bool CheckValid(Character self, Character target);
    void ApplyInitialChangesForTaiwu(DataContext, Character self, Character target);
    void ApplyChanges(DataContext, Character self, Character target);  // ← 套用效果
}
```

需求分組（`Character/Ai/GeneralAction/` 子資料夾）：
- **HealthDemand**：求醫、解毒、療傷、補內力、恢復精氣神…
- **WealthDemand**：索要/購買/偷/搶/騙 物資與物品、盜墓、取門派庫房…
- **StudyDemand**：求學功法/技藝、偷學、騙學、突破需求…
- **LifeSkillRandom**：打造、占卜、鬥蟲、品茶酒、娛樂、覺醒…
- **SocialStatusRandom**：行乞、修養、施恩、療傷助人、商譽…
- **TeachRandom**：教功法/技藝
- **BehaviorAction**：贈與、販賣、入庫、賺經驗（戰鬥/讀書/閒逛/鬥蟲）…

驅動：`Character.cs:11367 PeriAdvanceMonth_ExecuteGeneralAction(...)`（算）/ `ComplementPeriAdvanceMonth_ExecuteGeneralActions`（套用）。各行動的機率/權重常數集中在 `Character/Ai/AiHelper.cs`（`GeneralActionConstants`、`DemandActionType`、`HarmActionType` 等），是調平衡的好地方。

---

## 4. 戰鬥 AI（B 層，行為樹）

獨立系統，與過月無關。

- **Runtime**：`Combat/Ai/`。節點分 `Action/`（出招、換兵器、改招式、設記憶值…數十種 `AiActionXxx`）、`Node/`（`AiNodeBranch` 分支、`AiNodeLinear` 線性、`AiNodeAction` 葉）、`Condition/`。
- **工廠/註冊**：`Combat/Ai/AiNodeFactory.cs` 的 `Register(Assembly)` 會掃描組件中所有實作 `IAiNode` 且帶 `[AiNodeAttribute]` 的型別，依 `EAiNodeType` 註冊到 `Mapping`。→ 理論上 mod 可註冊自訂節點，但 `EAiNodeType` 是固定 enum，新增**節點種類**受限；改既有節點行為較實際。
- **藍圖資料**：行為樹本身是資料（`Config/AiNode.cs`、`AiNodeItem.cs`、`PrioritizedActions.cs`…的 ConfigCell），由前端 `Assembly-CSharp/AiEditor/`（`UI_AiEditor`、`AiBlueprintSnapshot`、`AiNodeTemplate`…）這個**遊戲內視覺化編輯器**產生與升級（含 V100→V106 的藍圖版本遷移器）。
- **相關 enum**（前端 root）：`EAiNodeType` / `EAiActionType` / `EAiConditionType` / `EAiParamType`。

> 改戰鬥 AI 最省事的路線是改藍圖資料（ConfigCell），其次才是 Harmony patch 個別 `AiActionXxx.Execute`。

---

## 5. 世界級月度事件（C 層的可擴充點）

非「逐角色」而是「整個世界每月觸發一次」的事件，在 `TaiwuEvent/MonthlyEventActions/`：

- 基類 `MonthlyActionBase.cs`，可覆寫：`IsMonthMatch` / `TriggerAction` / `MonthlyHandler` / `Activate` / `Deactivate` / `FillEventArgBox` / `CollectCalledCharacters` / `CreateCopy`…
- 內建範例：`EnemyNestMonthlyAction`（妖魔巢穴）、`MartialArtTournamentMonthlyAction`（比武大會）、`SeasonalMonthlyAction`（節氣）、`CustomActions/`（百花/伏龍/十方劇情觸發、婚姻觸發、傳承之書…）。
- 管理器：`MonthlyEventActionsManager.cs`；介面 `IMonthlyActionGroup` / `IDynamicAction`。
- 由 `WorldDomain.CheckMonthlyEvents`（過月尾段）結算。

---

## 6. Mod 切入點總表（依你想做什麼挑路線）

| 我想… | 路線 | 精準靶點 |
|---|---|---|
| 調某行為**多/少發生**（如讓 NPC 更愛復仇） | **純資料** | 改 `PrioritizedActions` ConfigCell：`BasePriority` / `MoralityPriority` / `ActionCoolDown`（用 `ConfigDataModificationUtils`，無需 patch） |
| 改某行為的**成立條件/選目標** | Harmony | patch `PrioritizedActionType.TryCreateAction_<名稱>`（後端） |
| 改 NPC 日常**需求行為機率/效果** | Harmony / 資料 | patch 對應 `GeneralAction/*Action` 的 `CheckValid`/`ApplyChanges`，或改 `AiHelper` 常數 |
| **整段重寫**優先級選擇邏輯 | Harmony | patch `Character.PeriAdvanceMonth_ExecutePrioritizedAction`（注意平行執行緒鐵則，§1.2） |
| 在**每月開始/結束**跑自己的程式 | **事件**（最乾淨） | `Events.RegisterHandler_AdvanceMonthBegin / _PostAdvanceMonthBegin / _AdvanceMonthFinish`（後端，於 `OnEnterNewWorld` 註冊；武學 mod 即用 `_AdvanceMonthFinish` 送功法） |
| 加一個**全新優先級行為** | Harmony + 資料 + 程式 | ①寫 `BasePrioritizedAction`/`ExtensiblePrioritizedAction` 子類；②在 `PrioritizedActions` 表加一列；③patch `PrioritizedActionType.CreatePrioritizedAction` 與 `TryCreatePrioritizedAction` 的 switch 接上新 id。難點＝序列化與存檔相容 |
| 加一個**全新世界級月度事件** | 程式 + 註冊 | 寫 `MonthlyActionBase` 子類，經 `MonthlyEventActionsManager` 註冊 |
| 改**戰鬥**出招邏輯 | 資料 / Harmony | 改 AI 藍圖（ConfigCell，或遊戲內 AiEditor），或 patch `Combat/Ai/Action/AiActionXxx` |

### 三個過月事件 API（`GameData/DomainEvents/Events.cs`）
- `RegisterHandler_AdvanceMonthBegin(OnAdvanceMonthBegin)` — Events.cs:2656，過月一開始
- `RegisterHandler_PostAdvanceMonthBegin(OnPostAdvanceMonthBegin)` — Events.cs:2671
- `RegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish)` — Events.cs:2686，玩家看完通知、存檔前
（皆 `void Handler(DataContext context)`；對應 `UnRegisterHandler_*` 於 `Dispose` 解除）

---

## 7. 重要約束

1. **必須是 Backend plugin**：以上邏輯全在 `GameData.dll`（後端 .NET 6 進程）。沿用 `MySwordArt.Backend` 的建置設定（net6.0、引用 `<遊戲>/Backend/` 的 GameData.* dll）。
2. **平行執行緒安全**（§1.2）：A 層的逐角色方法跑在 worker thread，遵守「Execute 算 / Complement 套用」兩段式。
3. **存檔相容**：凡新增會被序列化的狀態（如新 `BasePrioritizedAction` 子類），都牽涉 `ISerializableGameData` 的 `Serialize/Deserialize`，存檔升級風險高，建議優先走「資料表 + 既有行動」而非新增型別。
4. **事件路線最穩**：只要在月界做事（送東西、改數值、觸發判定），優先用 `RegisterHandler_AdvanceMonth*`，避開 patch 與執行緒問題。

---

## 8. 參考檔案

- `~/dev/taiwu-src/backend/GameData/GameData/Domains/World/WorldDomain.cs:7067`（`AdvanceMonth`）、`:7214`（`PeriAdvanceMonth`）
- `…/Domains/Character/Character.cs:16577`（`PeriAdvanceMonth_ExecutePrioritizedAction`）、`:11367`（`…ExecuteGeneralAction`）、`:10715`（`…ExecuteFixedActions`）
- `…/Domains/Character/Ai/PrioritizedActionType.cs`、`AiHelper.cs`、`PrioritizedAction/BasePrioritizedAction.cs`、`GeneralAction/IGeneralAction.cs`
- `…/Domains/Character/ParallelModifications/PrioritizedActionModification.cs` 等 `PeriAdvanceMonth*Modification.cs`
- `…/Domains/Combat/Ai/AiNodeFactory.cs`、`Combat/Ai/Action/`、`Node/`
- `…/Domains/TaiwuEvent/MonthlyEventActions/MonthlyActionBase.cs`、`MonthlyEventActionsManager.cs`
- `…/Config/PrioritizedActionsItem.cs`、`PrioritizedActions.cs`、`MonthlyActions.cs`、`AiNode.cs`
- `~/dev/taiwu-src/backend/GameData/GameData/DomainEvents/Events.cs:2656-2696`（過月事件）
- 前端：`~/dev/taiwu-src/Assembly-CSharp/AiEditor/`、`EAiNodeType/EAiActionType/EAiConditionType/EAiParamType.cs`
- 交叉參考：`details/backend_combat_events.md`（戰鬥事件、DomainManager 動詞 API）、`details/martial_arts_mod_anatomy.md`（`OnEnterNewWorld`→`RegisterHandler_AdvanceMonthFinish` 過月送功法範例）
