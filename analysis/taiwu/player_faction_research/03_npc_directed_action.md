# NPC 受命行動：「指派一個 NPC 去某地殺某人」可行性與實作路徑

> 日期：2026-05-23
> 目標：使用者想做「小門派長老 NPC 對弟子 NPC 下命令 → 弟子跑去某地殺指定的人」。本文釐清遊戲如何驅動 NPC 世界行為，並評估「強制指派某 NPC 去特定地點殺特定角色」的所有可行路徑。
> **版本核對**：所有方法簽名/方法體/行號均已對實裝版 **0.0.79.60** 反編譯驗證（`Backend/GameData.dll`、`GameData.Shared.dll`）。舊源 `~/dev/taiwu-src/`（約 0.0.76.x）只用作 grep 索引與交叉比對，文中標出兩者差異。
> 索引文件交叉參考：`analysis/taiwu/details/npc_ai_and_advance_month.md`（過月管線總覽）、`dual_assembly_type_conflict.md`（型別歸屬/編譯）。

---

## 0. 一句話結論

**完全可行，而且有現成範例。** 遊戲的「復仇（TakeRevenge，行動 id=8）」就是一個現成的「NPC 跑去殺指定角色」的完整管線：用 `NpcTravelTarget` 鎖定目標角色 → 過月時自動移動過去 → 到達後在世界層模擬戰鬥/下毒/暗算把人弄死。Mod 只要把這個既有行動「強加」到弟子身上即可，**不需要新寫任何行動型別，也不需要碰序列化**。

最省力的兩條路（細節見 §5、§6）：
- **路 A（最穩）**：事件鉤 `RegisterHandler_AdvanceMonthBegin` 裡呼叫 `DomainManager.Character.StartCharacterPrioritizedAction(context, 弟子, new TakeRevengeAction { Target = new NpcTravelTarget(被害者charId, 月數) })` ── 直接、確定性地強制指派。
- **路 B（更「自然」）**：給弟子塞一個「復仇需求」`PersonalNeed`（TemplateId=21，指向被害者 charId），讓 NPC 在下次過月**自己**選中 TakeRevenge。較柔性但受權重/機率/冷卻影響，不保證立刻觸發。

---

## 1. 世界行為 AI 決策骨架（已對實裝 DLL 核對）

### 1.1 過月管線中的位置
過月總入口 `WorldDomain.AdvanceMonth`（舊源 `World/WorldDomain.cs:7067`，實裝 raise 點在 `:7093`）依序：
```
Events.RaiseAdvanceMonthBegin(context)        // WorldDomain.cs:7093 ★主執行緒、在 NPC 決策之前 → mod 注入的最佳時機
PreAdvanceMonth(context, monitor)             // :7097
PeriAdvanceMonth(context, monitor)            // :7098  ← NPC「決定做什麼」在這
PostAdvanceMonth(context, monitor)            // :7099  ← NPC「實際移動」在這
...
Events.RaiseAdvanceMonthFinish(context)       // :7130  玩家看完通知、存檔前
```

`PeriAdvanceMonth`（舊源 `WorldDomain.cs:7214`）以 `WorkerThreadManager.Run(階段方法, …)` **依地區平行**跑，狀態碼 9/10/11 是 NPC 自主決策核心：
| 狀態碼 | worker 方法（WorldDomain.cs 行號，舊源） | 內容 |
|---:|---|---|
| 9 | `PeriAdvanceMonth_CharacterPrioritizedAction`（:7298） | **★優先級行動**（劇情/強制性高優先行為） |
| 10 | `PeriAdvanceMonth_CharacterGeneralAction`（:7306） | 一般日常行動 |
| 11 | `PeriAdvanceMonth_CharacterFixedAction`（:7314） | 固定行動（村民工作、逃犯團） |

第 9/10/11 整段被 `disableAiActions` 旗標跳過（主線「神遊」橋段，`WorldDomain.cs:7218` 由全域事件參數 `MainStoryLine_SpiritualWanderPlace_TaiwuVillagersCenter` 決定）。

### 1.2 「決定做什麼」的決策迴圈（已核對）
**實裝**：`Character.PeriAdvanceMonth_ExecutePrioritizedAction(DataContext)` ── 反編譯 `GameData.dll` 行號 **16526**（舊源同名方法在 `Character.cs:16577`，邏輯一致）。

要點（實裝 16532-16583）：
```csharp
sbyte behaviorType = GetBehaviorType();                       // 道德傾向（5 型）
// 取現有行動的優先級當門檻
int num = hasPrev ? cfg.BasePriority + cfg.MoralityPriority[behaviorType] : -1;
for (short i = 0; i < PrioritizedActions.Instance.Count; i++) {   // 遍歷整張優先級行動表
    var c = PrioritizedActions.Instance[i];
    int prio = c.BasePriority + c.MoralityPriority[behaviorType];  // ← 道德傾向決定偏好
    if (prio > num && (!hasPrev || c.IsPrevActionInterrupted)
        && !DomainManager.Extra.IsPrioritizedActionInCooldown(_id, i)) {
        var action = PrioritizedActionTypeHelper.TryCreatePrioritizedAction(context, this, i, ref conditions);
        if (action != null) { mod.Action = action; num = prio; }   // 擇優
    }
}
```
注意這裡只「**算**」，把選定的行動塞進 `PrioritizedActionModification` 排隊（`context.ParallelModificationsRecorder.RecordParameterClass(mod)`，實裝 16591-16593），**不直接寫全域狀態**（平行段鐵則，§7）。

兩個關鍵旋鈕：
- **資料層**：`PrioritizedActions` 設定表（ConfigCell，欄位 `Config/PrioritizedActionsItem.cs`）：`BasePriority`、`MoralityPriority[behaviorType]`（5 種道德型各一權重）、`ActionCoolDown`、`FailToCreateActionCoolDown`、`Duration`、門檻 `IsAdultOnly`/`IsNonLeader`/`IsNonTaiwuTeammate`/`IsNonMonk`/`LoafChance`/`OrgTemplateId`/`OrgGrade`/`IsPrevActionInterrupted`。
- **程式層**：`PrioritizedActionTypeHelper.TryCreateAction_<名稱>` 各方法（每個行動「能不能成立、選誰當目標、走多久」的硬編碼邏輯）。
  - ⚠️ **版本漂移**：實裝把舊源的 `PrioritizedActionType`（同時含常數＋ switch 工廠）拆成兩個型別：常數仍叫 `PrioritizedActionType`（在 `GameData.Shared.dll`，只有 `JoinSect=0…TakeRevenge=8, Count=9`），而 switch 工廠/`TryCreate*` 全搬到 **`PrioritizedActionTypeHelper`**（在 `GameData.dll`）。要 patch `TryCreateAction_*` 必須對 `GameData.Domains.Character.Ai.PrioritizedActionTypeHelper` 下手，不是 `PrioritizedActionType`。

### 1.3 「實際移動」與「執行行動」分兩段、跨多個月
這是理解「跑去某地殺人」如何運作的關鍵：

- **套用決策（主執行緒）**：`Character.ComplementPeriAdvanceMonth_ExecutePrioritizedAction(context, mod)` ── 實裝 `GameData.dll:16597`（舊源 `Character.cs:16647`）。它：
  1. 新行動 → 中斷舊行動、`AddCharacterPrioritizedAction`、`action.OnStart()`；舊行動 → `Target.RemainingMonth--`。
  2. **只有當角色已在目標地點才執行**：實裝 16644
     ```csharp
     if (mod.IsNewAction || !character._location.IsValid() || !action.Target.IsTargetInteractable()
         || !character._location.Equals(action.Target.GetRealTargetLocation())) {
         DomainManager.Character.SetCharacterPrioritizedAction(...); return;  // 還沒到，這個月不執行
     }
     if (!action.HasArrived) action.OnArrival(context, character);  // 16649
     if (action.Execute(context, character)) { /* 行動完成→移除 */ }   // 16657 ← 真正「殺人」在這
     ```
- **移動（主執行緒，PostAdvanceMonth 階段）**：`CharacterDomain.UpdateIntelligentCharacterMovements`（實裝 `GameData.dll:15973`，舊源 `:15040`）→ 對每個 NPC 呼叫 `Character.UpdateIntelligentCharacterMovement`（實裝 `:16022`，舊源 `:16069`）→ 內部優先嘗試 `TravelToPrioritizedActionTargetLocation`（實裝 `:16256`，舊源 `:16311`）：把 NPC 朝 `action.Target.RealLocation` 移動一步（同區 `GroupMove`，跨區 `NpcCrossAreaTravel`）。
  - 在 `PostAdvanceMonth` 內呼叫點：`WorldDomain.cs:8251`（`if (!disableAiActions) UpdateIntelligentCharacterMovements`）。

> **時間模型**：指派行動後，NPC **每月走一段路**靠近目標，到達當月才 `Execute`（動手）。距離遠（跨地區）會花數個月。`NpcTravelTarget.RemainingMonth`（=行動 Duration）耗盡前沒到/沒殺成就放棄。所以「指派 → 殺成」通常橫跨數個過月，不是即時。

---

## 2. 行動型別清單（實裝 0.0.79.60，已核對 `PrioritizedActionTypeHelper` 雙 switch）

`PrioritizedActionTypeHelper.CreatePrioritizedAction(templateId)` 與 `TryCreatePrioritizedAction(...)` 的 switch 範圍 **id 0~22**（實裝反編譯，與舊源完全一致）。標★者帶「移動到目標」並可能「對人動手」：

| Id | 行動類別（`Character/Ai/PrioritizedAction/`） | 目標如何帶入 | 是否「移動＋對人」 |
|---:|---|---|---|
| 0 | JoinSectAction | `NpcTravelTarget(門派駐地Location, …)` | 移動，不殺 |
| 1 | AppointmentAction（太吾召喚赴約） | `NpcTravelTarget(駐地Location)` + `TargetCharId=太吾` | 移動 |
| 2 | ProtectFriendOrFamilyAction | `NpcTravelTarget(targetCharId, …)` | ★移動到人（保護） |
| 3 | RescueFriendOrFamilyAction | `NpcTravelTarget(targetCharId, …)` | ★移動到人（營救被綁者） |
| 4 | MournAction（弔唁） | `NpcTravelTarget(targetCharId→墓Location)` | 移動到墓 |
| 5 | VisitFriendOrFamilyAction | `NpcTravelTarget(targetCharId, …)` | ★移動到人 |
| 6 | FindTreasureAction | `NpcTravelTarget(Location, …)` | 移動到地點 |
| 7 | FindSpecialMaterialAction | `NpcTravelTarget(Location, …)` | 移動到地點 |
| **8** | **TakeRevengeAction（復仇）** | **`NpcTravelTarget(targetCharId, …)`** | **★★移動到人並「殺」── 本需求的現成範本** |
| 9 | ContestForLegendaryBookAction（爭奪傳承之書） | `NpcTravelTarget(書主charId, …)` | ★移動到人（搶書，可能動手） |
| 10 | AdoptInfantAction | `NpcTravelTarget(嬰charId, …)` | 移動到人 |
| 11 | SectStoryYuanshanToFightDemonAction（遠山殺魔） | `NpcTravelTarget(妖魔Location)` | ★移動＋戰鬥 |
| 12 | SectStoryShixiangToFightEnemyAction（十方殺敵） | `NpcTravelTarget(敵Location)` | ★移動＋戰鬥 |
| 13 | SectStoryEmeiToFightComradeAction（峨眉同門相殘） | `NpcTravelTarget(同門charId)` | ★移動＋戰鬥（殺人） |
| 14 | DejaVuAction（似曾相識） | `NpcTravelTarget(太吾charId)` | 移動到太吾 |
| 15 | GuardTreasuryAction（守庫房） | `NpcTravelTarget(駐地Location)` | 移動到地點 |
| 16 | SectStoryBaihuaToCureManic（百花治狂） | `NpcTravelTarget(狂者charId)` | ★移動到人 |
| 17 | HuntFugitiveAction（追緝逃犯） | `NpcTravelTarget(逃犯charId, …)` | ★★移動到人並擒/殺 |
| 18 | EscapeFromPrisonAction（越獄） | `NpcTravelTarget(逃亡Location)` | 移動 |
| 19 | SeekAsylumAction（尋求庇護） | `NpcTravelTarget(敵對門派Location)` | 移動 |
| 20 | EscortPrisonerAction（押送囚犯） | `NpcTravelTarget(門派Location)` + `TargetCharId=囚犯` | 移動 |
| 21 | VillagerRoleArrangementAction（村民職務） | `NpcTravelTarget(工作Location)` | 移動 |
| 22 | HuntTaiwuAction（截命門追殺太吾） | `NpcTravelTarget(太吾charId, …)` | ★★移動到人並殺（追殺，但目標寫死＝太吾） |

**「移動到某座標/地格」與「移動到某角色」由同一結構承載** ── `NpcTravelTarget` 兩種建構子（見 §4）。**「攻擊/殺指定角色」現成項＝id 8（復仇）、17（追緝逃犯）、22（追殺太吾）、13（同門相殘）**，其中 8/13/17 的目標 charId 可由 mod 任意指定（22 寫死太吾）。

---

## 3. 既有「追殺/仇殺」機制 ── TakeRevenge 是最佳借力點（已逐行核對）

### 3.1 它怎麼選目標、怎麼移動、怎麼殺
`PrioritizedActionTypeHelper.TryCreateAction_TakeRevenge`（實裝 `GameData.dll` 反編譯 `:468`；舊源 `PrioritizedActionType.cs:488`）的選目標邏輯：
1. 機率閘：`AiHelper.PrioritizedActionConstants.TakeRevengeChance[behaviorType]`，非自由行動者(`!CanStroll`)減半，再經特效 318 修正。
2. **優先讀「復仇需求」**：遍歷 `selfChar.GetPersonalNeeds()`，若有 `need.TemplateId == 21` → `targetCharId = need.CharId`（**直接鎖定 mod 想要的目標，繞過下面的仇敵掃描**）。
3. 否則掃 `DomainManager.Character.GetRelatedCharIds(selfCharId, 32768)`（32768=仇敵 RelationType 旗標）裡好感夠低、距離 ≤90 時間成本的仇敵。
4. 建 `NpcTravelTarget travelTarget = new NpcTravelTarget(targetCharId, maxDuration)` → `return new TakeRevengeAction { Target = travelTarget }`。

`TakeRevengeAction`（`Character/Ai/PrioritizedAction/TakeRevengeAction.cs`，實裝核對一致）：
- `ActionType => 8`。
- `OnStart`（被指派當下，主執行緒）：記生命記錄 `AddDecideToRevenge`，若涉及太吾人發月度通知 `AddGoToRevenge`，並 `DomainManager.Character.AddOngoingVengeance(context, selfCharId, Target.TargetCharId)`（登記「正在被復仇」）。
- `Execute`（**到達目標當月才跑**，主執行緒，舊源 `TakeRevengeAction.cs:57`／實裝核對一致）：依道德傾向 `TakeRevengeActionPriorities[behaviorType]` 選加害方式，呼叫其一：
  ```csharp
  case 0: DomainManager.Character.HandleAttackAction(context, selfChar, targetChar);      // 動武
  case 1: DomainManager.Character.HandlePoisonAction(context, selfChar, targetChar, ItemKey.Invalid, -1);  // 下毒
  case 2: DomainManager.Character.HandlePlotHarmAction(context, selfChar, targetChar, ItemKey.Invalid, -1); // 暗算
  ```
  回傳 `!IsCharacterAlive(Target.TargetCharId) || ...`（目標死了＝行動完成）。
- `OnInterrupt`/`OnCharacterDead`：`FinishOngoingVengeance`（清掉復仇登記）。

### 3.2 「殺」其實是世界層模擬戰鬥，不是進戰鬥場景
`HandleAttackAction`（`CharacterDomain.cs` 實裝 `:1983`，舊源 `:1798`）內部走 `SimulateCharacterCombat(...)`（依雙方屬性/戰力擲骰），不開即時戰鬥畫面。`HandlePoisonAction`（實裝 `:2255`）、`HandlePlotHarmAction`（實裝 `:2117`）同理。所以 NPC 對 NPC 的「殺」是後端純模擬結算 ── mod 不需要處理戰鬥場景。

**結論**：TakeRevenge 把「鎖定某角色→自動移動過去→世界層動手殺」整條鏈都做好了，是 mod 最省力的借力點。

---

## 4. 命令承載結構：`NpcTravelTarget`＋`PersonalNeed`（已核對）

### 4.1 `NpcTravelTarget`（行動的「去哪/找誰」載體）
`GameData.Domains.Character.Ai.NpcTravelTarget`（struct，`ISerializableGameData`，實裝核對與舊源一致）：
```csharp
public NpcTravelTarget(Location targetLocation, int maxDuration);  // 模式①：固定地點
public NpcTravelTarget(int targetCharId, int maxDuration);          // 模式②：跟著某角色跑
public int TargetCharId;     // 目標角色（模式②）
public int RemainingMonth;   // 剩餘可執行月數（=行動 Duration），每月遞減，歸零放棄
public Location RealLocation => GetRealTargetLocation();  // 模式②時即時解析目標當前所在地，會跟著目標移動
```
`GetRealTargetLocation()`（模式②）會解析目標角色「現在在哪」（含跨區移動中的去向、若死了取墓地）── 所以追殺會**跟著目標跑**，不是釘死在指派當下的座標。`EscortPrisonerAction` 還示範了「主目標是 Location、但額外帶 `Target.TargetCharId=囚犯」的複合用法。

### 4.2 既有「命令/委託/師命」結構盤點（point 5）
查遍 `Organization/`、`Character/`、`Taiwu/`，**遊戲沒有泛用的「角色對角色下令」資料結構**（沒有 Commission/Mission/Mandate/Decree 之類）。最接近的兩個既有承載點：
- **太吾召喚（Appointments）**：`TaiwuDomain._appointments`（`Dictionary<int charId, short settlementId>`，`TaiwuDomain.cs:207`），由 `AddAppointment(context, charId, settlementId)`（`:4457`）寫入；對應行動 id=1 `AppointmentAction`。但這是**太吾專屬**（玩家召喚 NPC 到某駐地），不是 NPC 對 NPC、也不含「殺」。
- **PersonalNeed（個人需求）**：最通用的「給某 NPC 一個動機」的資料結構（見下）。`TemplateId==21`＝復仇需求、`==26`＝想入某門派、`==22`＝想弔唁、`==24`＝想尋寶…。`TryCreateAction_*` 多會優先讀對應 PersonalNeed 來定目標。

→ 「長老下令弟子」這層**語義在遊戲裡不存在**，需 mod 自行表達。最自然的承載＝直接用 `PersonalNeed`(21) 或直接 `StartCharacterPrioritizedAction` 灌一個 `TakeRevengeAction`（見 §5/§6）。若要做得像「門派任務系統」，得自己存一張「指派表」（mod 私有狀態）並在每月事件鉤裡重放，遊戲沒有現成表可掛。

### 4.3 `PersonalNeed`（給 NPC 植入動機的通用結構）
`GameData.Domains.Character.Ai.PersonalNeed`（實裝核對一致）：
```csharp
// 工廠（PersonalNeed.cs:337，(sbyte, int) 重載 → 寫入 CharId）
public static PersonalNeed CreatePersonalNeed(sbyte templateId, int charIdOrAmount);
// 植入（Character.cs:7838，實例方法，主執行緒）
public void AddPersonalNeed(DataContext context, PersonalNeed personalNeed);
public bool OfflineAddPersonalNeed(PersonalNeed personalNeed);  // 不發 modification（離線/批次用）
```
**復仇需求**＝`PersonalNeed.CreatePersonalNeed(21, 被害者charId)`，其 `RemainingMonths` 自動取 `Config.PersonalNeed.Instance[21].Duration`。植入後，弟子下次過月 `TryCreateAction_TakeRevenge` 會優先讀它鎖定目標。

---

## 5. 強制指派一個 NPC 的行動：三條路評估（point 4）

### 路 (a)：改 `PrioritizedActions` 資料調權重 ── 不適用本需求
改 ConfigCell（`BasePriority`/`MoralityPriority`/`ActionCoolDown`）只能讓「某類行為整體更/少發生」，**無法指定「哪個 NPC、針對哪個目標」**。對「長老指名某弟子殺某人」這種精確指派沒用。可作輔助（例如全域提高復仇傾向），但非主路。

### 路 (b)：直接呼叫公開 API 強制指派 ── ★最推薦
**不需要 Harmony patch**。`CharacterDomain` 有現成公開方法（實裝核對）：
```csharp
// CharacterDomain.cs:4529（實裝）
public void StartCharacterPrioritizedAction(DataContext context, Character character, BasePrioritizedAction action)
//  → 若有舊行動先 OnInterrupt+移除，再 AddCharacterPrioritizedAction + action.OnStart
```
用法（在事件鉤的主執行緒裡）：
```csharp
var disciple = DomainManager.Character.GetElement_Objects(discipleId);
var action = new TakeRevengeAction {
    Target = new NpcTravelTarget(victimCharId, /*月數，夠長*/ 36)
};
DomainManager.Character.StartCharacterPrioritizedAction(context, disciple, action);
```
之後遊戲自有管線會：每月 `UpdateIntelligentCharacterMovement` 把弟子朝 victim 移動 → 到達當月 `ComplementPeriAdvanceMonth_ExecutePrioritizedAction` 觸發 `TakeRevengeAction.Execute` 動手殺。**完全複用既有移動＋殺人鏈，零序列化負擔**（`TakeRevengeAction` 是遊戲既有的可序列化型別，存檔相容）。

注意：`StartCharacterPrioritizedAction` 會被「下個月的決策迴圈」覆寫 ── 若某月決策迴圈算出一個 `priority` 更高的行動（且 `IsPrevActionInterrupted`），會中斷我們指派的復仇。`TakeRevenge` 的 BasePriority 在表中偏高，但若要「死命令、不可被打斷」，可：①把指派包進 mod 私有「指派表」，在每次 `AdvanceMonthBegin` 重新 `StartCharacterPrioritizedAction`（重放）直到目標死亡；或 ②patch 決策迴圈讓被指派者跳過重選（見路 c）。

### 路 (c)：Harmony patch ── 需要更強控制時
- **patch `PrioritizedActionTypeHelper.TryCreateAction_TakeRevenge`**（注意是 Helper 不是 Type，§1.2）：postfix 裡，若 `selfChar` 在 mod 的指派表中，無條件回傳一個鎖定指定 victim 的 `TakeRevengeAction`（覆蓋遊戲自選的目標/機率閘）。
- **patch 決策迴圈 `Character.PeriAdvanceMonth_ExecutePrioritizedAction`**（實裝 16526）：prefix 偵測被指派者，直接塞 `mod.Action` 並 return，讓它不參與一般擇優。⚠️ 此方法跑在 **worker thread**（§7），prefix 只能讀 + 寫進 `PrioritizedActionModification`/排隊，**不可在此直接改全域**。
- 兩者都比路 (b) 複雜，僅在「需要壓過遊戲自身決策、保證持續追殺」時才值得。

### 路選擇建議
- **預設用路 (b)**：`AdvanceMonthBegin` 事件鉤 + `StartCharacterPrioritizedAction(TakeRevengeAction)`，配 mod 私有指派表每月重放確保不被打斷。最穩、最少踩雷。
- 想要「更像遊戲原生（NPC 自己起意）」用 **路 B（§6）植 PersonalNeed(21)**。
- 需要絕對壓制 NPC 自選邏輯時才加 **路 (c) 的 Helper postfix**。

---

## 6. 兩條最省力實作配方（彙整）

**配方 A（確定性，推薦）**
1. 後端 plugin 在 `OnEnterNewWorld` 註冊 `Events.RegisterHandler_AdvanceMonthBegin(OnBegin)`（`Events.cs` 實裝 `:2821`）。
2. mod 維護私有指派表 `{discipleId → (victimId, 剩餘月數)}`（mod 自己序列化或每場重建）。
3. `OnBegin(context)`（主執行緒、在 NPC 決策之前）：對表中每筆，若 victim 仍活，
   `DomainManager.Character.StartCharacterPrioritizedAction(context, 弟子, new TakeRevengeAction { Target = new NpcTravelTarget(victimId, n) })`；victim 死了或月數歸零就移除。

**配方 B（柔性，較自然）**
1. 同樣在 `AdvanceMonthBegin` 主執行緒。
2. 對弟子 `disciple.AddPersonalNeed(context, PersonalNeed.CreatePersonalNeed(21, victimId))`（`Character.cs:7838`）。
3. 弟子下次過月 `TryCreateAction_TakeRevenge` 自選 TakeRevenge 鎖定 victim。
   - 缺點：受 `TakeRevengeChance[behaviorType]`、`CanStroll`、冷卻、與其他高優先行動競爭影響，**不保證立刻或一定觸發**；好處是表現得像 NPC 自發復仇、且天然走完整生命記錄/通知流程。

兩配方都複用既有移動＋戰鬥模擬，**不新增行動型別、不碰序列化格式**，存檔相容風險最低。

> 「殺成」需要弟子戰力足以在 `SimulateCharacterCombat` 中擊殺 victim；若弟子太弱可能反被殺或殺不死（`Execute` 回傳 false → 留著行動下月再試直到 RemainingMonth 歸零）。若要「保證秒殺」得另外 patch `HandleAttackAction`/戰鬥模擬，超出本需求範圍。

---

## 7. 執行緒風險與避法（point 6，務必遵守）

過月逐角色方法跑在 **worker thread**（`WorkerThreadManager.Run(...)`，依地區平行），採「**先算、後套用**」兩段式：
- **平行段（worker thread）**：`Character.PeriAdvanceMonth_Execute*`（如決策迴圈 16526）只**計算**並把結果塞 `*Modification` 物件、`context.ParallelModificationsRecorder.RecordParameterClass(mod)` 排隊。**絕不可在此直接寫全域狀態**（改別的角色、改門派、改地圖…），否則偶發崩潰/存檔損毀。
- **串行段（主執行緒）**：`Character.ComplementPeriAdvanceMonth_Execute*`（如套用相 16597）才真正套用（移動、扣資源、`AddOngoingVengeance`…）。

本 mod 的雷與避法：
| 動作 | 安全嗎 | 說明 |
|---|---|---|
| 在 `RegisterHandler_AdvanceMonthBegin/Finish` 事件鉤裡呼叫 `StartCharacterPrioritizedAction`/`AddPersonalNeed` | ✅ 安全 | 事件 raise 在 `WorldDomain.cs:7093`/`:7130`，**主執行緒、且在/外於平行段之外**。這是首選注入點。 |
| 在 `AdvanceMonthBegin` 鉤裡讀寫 mod 私有指派表 | ✅ 安全 | 主執行緒。 |
| postfix `TryCreateAction_TakeRevenge`（路 c） | ⚠️ 有限度 | 它在決策**平行段**被呼叫。postfix 只能回傳/組裝行動物件（局部），**不可在 postfix 內改其他角色或全域容器**。 |
| prefix/patch 決策迴圈 `PeriAdvanceMonth_ExecutePrioritizedAction` | ⚠️ 平行段 | 同上，只能寫進 `PrioritizedActionModification` 並排隊，禁止直接寫全域。 |
| 直接呼叫 `HandleAttackAction` 等想「立刻殺」 | ⚠️ | 這些是串行段 API（`Complement*`/事件鉤裡安全）；別在 worker thread 呼叫。 |

**一句話**：把所有「指派/植入需求」的寫入動作放進 **`AdvanceMonthBegin` 事件鉤（主執行緒）**，就完全避開平行段執行緒雷；能不 patch 決策/Helper 就不 patch。

---

## 8. 待釐清問題（需進一步驗證）

1. **`Config.PersonalNeed.Instance[21].Duration` 實際月數**：決定配方 B 的復仇需求能撐幾個月才過期；未讀 ConfigCell 數值（需 dump config 或實機觀察）。
2. **`PrioritizedActions[8]`（TakeRevenge）的 BasePriority/MoralityPriority 實際值**：決定路 (b) 指派後「下月被更高優先行動打斷」的機率；未讀數值。
3. **`StartCharacterPrioritizedAction` 從事件鉤呼叫時，當月是否立即被 PeriAdvanceMonth 決策迴圈覆寫**：理論上 `AdvanceMonthBegin`(7093) 在 `PeriAdvanceMonth`(7098) 之前，當月決策迴圈仍會跑、可能覆寫我們的指派 ── 需確認 `IsPrevActionInterrupted` 與優先級比較後是否保留。建議實機驗證或改用「每月重放」確保穩定。
4. **弟子戰力不足時的回退行為**：`Execute` 回傳 false 後是否會無限重試到 RemainingMonth 歸零、期間是否反被 victim 反殺 ── 需實機觀察。
5. **跨地區移動的 90 時間成本上限**：`TryCreateAction_*` 多處有「目標 AreaId 不同且 `GetTotalTimeCost > 90` 就放棄」的閘（如復仇選敵掃描 §3.1 step3）。但**路 (b) 直接 new `TakeRevengeAction` 繞過了選目標階段的這個閘**，需確認 `TravelToPrioritizedActionTargetLocation` 在跨遠距時是否仍會放棄（`AllowCrossAreaTravel` 判定）。
6. **mod 私有指派表的存檔**：若要跨存檔保留「長老的命令」，得自己處理序列化（遊戲無現成委託表）。

---

## 9. 關鍵原始碼位置索引（實裝 0.0.79.60 已核對；行號來自反編譯 `GameData.dll`）

- 決策迴圈（算）：`GameData.Domains.Character.Character.PeriAdvanceMonth_ExecutePrioritizedAction` — `GameData.dll:16526`
- 套用（含到達後 Execute）：`Character.ComplementPeriAdvanceMonth_ExecutePrioritizedAction` — `GameData.dll:16597`
- 移動驅動：`Character.UpdateIntelligentCharacterMovement` — `:16022`；`Character.TravelToPrioritizedActionTargetLocation` — `:16256`；`CharacterDomain.UpdateIntelligentCharacterMovements` — `:15973`（過月呼叫點 `WorldDomain.cs:8251`）
- 行動工廠（switch + TryCreate*）：`GameData.Domains.Character.Ai.PrioritizedActionTypeHelper`（**實裝改名**，舊源叫 `PrioritizedActionType`）；`TryCreateAction_TakeRevenge` — 反編譯 `:468`
- 行動常數：`GameData.Domains.Character.Ai.PrioritizedActionType`（**僅常數**，在 `GameData.Shared.dll`，`JoinSect=0…TakeRevenge=8, Count=9`）
- 復仇行動：`GameData.Domains.Character.Ai.PrioritizedAction.TakeRevengeAction`（`ActionType=>8`、`OnStart`/`Execute`）
- 行動基類：`...PrioritizedAction.BasePrioritizedAction`（`Target`/`HasArrived`/`OnStart`/`OnArrival`/`Execute`/`OnInterrupt`/`OnCharacterDead`）
- 目標載體：`GameData.Domains.Character.Ai.NpcTravelTarget`（雙建構子、`RealLocation`/`GetRealTargetLocation`/`IsTargetInteractable`）
- 強制指派 API：`CharacterDomain.StartCharacterPrioritizedAction` — `:4529`；`AddCharacterPrioritizedAction` — `:4518`；`RemoveCharacterPrioritizedAction` — `:4542`；`TryGetCharacterPrioritizedAction` — `:4504`
- 仇殺登記：`CharacterDomain.AddOngoingVengeance` — `:4547`；`IsTargetForVengeance` — `:4562`；`FinishOngoingVengeance`
- 加害結算：`CharacterDomain.HandleAttackAction` — `:1983`；`HandlePlotHarmAction` — `:2117`；`HandlePoisonAction` — `:2255`（內部 `SimulateCharacterCombat`）
- 需求植入：`Character.AddPersonalNeed` — `:7838`；`PersonalNeed.CreatePersonalNeed(sbyte,int)` — `PersonalNeed.cs:337`
- 過月事件 API：`GameData.DomainEvents.Events.RegisterHandler_AdvanceMonthBegin` — `:2821`；`...PostAdvanceMonthBegin` — `:2836`；`...AdvanceMonthFinish` — `:2851`（raise 點 `WorldDomain.cs:7093`/`PostAdvanceMonth:8208`/`:7130`）
- 過月管線：`WorldDomain.AdvanceMonth`（raise begin `:7093`）、`PeriAdvanceMonth`（`:7214`，狀態 9 prioritized 在 `:7298`）、`PostAdvanceMonth`（`:8203`，移動 `:8251`）

> 編譯本 mod 須是 **Backend plugin**（net6.0，引用 `Backend/` 的 `GameData.dll`/`GameData.Shared.dll`/`GameData.Utilities.dll`），沿用 `MySwordArt.Backend` 設定；型別歸屬細節見 `details/dual_assembly_type_conflict.md`。
