# NPC 與環境互動 — 系統剖析

> 分析日期：2026-05-23　|　範圍：大世界（非戰鬥）NPC 的自主行為與環境/玩家互動
> 路徑基準：`../SourceCode/Assembly-CSharp/`（以下省略前綴）

## 結論先講

**會，但屬於「資料表 + 場景路徑圖 + 機率」驅動的擬真行為，不是真正的物件親和性 AI（object-affordance / utility AI）。**

NPC 在大世界中**不是靜止的**：會巡邏走動、定時播放休閒動作、發出環境音、彼此交談、甚至主動走向玩家發起切磋/搶劫/委託。但這些都是「演出層」——播動畫＋氣泡＋音效＋沿路徑點移動，並**沒有**對任意場景物件（門、椅子、可拾取物）做語意層級的互動規劃，也**沒有找到以時鐘為核心的作息（日程）系統**。

控制大世界 NPC 的核心類別是 `SweetPotato/NpcController.cs`（2310 行，繼承 `UnitController`），它在 `ConfigComponentFinished()`（`NpcController.cs:652`）依 NPC 原型條件掛載四個行為元件。

---

## 一、NPC 自主行為的四個元件

`NpcController` 內建四個欄位（`NpcController.cs:15-21`），在 `ConfigComponentFinished()` 條件式建立：

| 元件 | 欄位 | 建立條件（`NpcController.cs`） | 作用 |
|---|---|---|---|
| 休閒動作 | `m_NpcXiuXianAnimComponent` | `:660` 預設動畫為 `idle`/空 且 有 `npc_xiuxiananim` 設定 且 有 `bubblegroupid` | 定時播閒置動畫＋氣泡＋音效 |
| 環境音效 | `m_NpcEnvironmentComponent` | `:669` 有 `npc_environmentsound` 設定且 sound 非空 | 玩家靠近時播放環境音 |
| 巡邏 | `m_NpcPatrolComponent` | `:675` `m_NpcEntity.IsPatrolNpc()` 為真 | 沿隨機路徑點走動 |
| 跟隨 | `m_NpcFollowComponent` | （隊友/事件時）| 跟隨目標 |

另外每個 NPC 都會建立三個自動化腳本（`NpcController.cs:679-682`）：`m_AutomatAIScript`、`m_AutomatChatScript`、`m_AutomatPatroScript`（`AutomatScript` 型別），這是 NPC 行為的腳本驅動層。特定 `aiScript`（如 2157、2493，見 `:688`）會載入巡邏腳本。

四個元件的 `ManagedUpdate()` 由 `NpcController.ManagedUpdate()`（`:147`）每幀（依 LOD 計數）呼叫，見 `:208-214`。

### 1.1 休閒動作 `NpcXiuXianAnimComponent.cs`（197 行）

- 資料表 **`npc_xiuxiananim`**（`NpcXiuXianAnim.cs:63`），欄位：`intervalTime`（毫秒）、`animAndPopIds[5]`（`動畫名&氣泡id`，用 `|` 分隔多選）、`conds[5]`（每組動畫的條件）、`sound`。
- 邏輯（`ManagedUpdate` `:43`）：計時到 `intervalTime` → `PlayAnim()`（`:137`）→ 從符合條件 (`AnswerViewNew.IsMatchMultCondition`) 且符合 `bubblegroupid` 的動畫池隨機挑一個 → `m_AnimationComponent.PlayAnim()` ＋ 透過 `NpcBubbleChatRegulator` 加隨機氣泡（`:171`，類型 `RT_XIUXIANANIM`）＋ 距玩家 5.5m 內才放音效（`:172`）。
- **進入劇情時 (`WorldManager.m_IsInJuQing`) 強制中斷**回到 `ACTION_STATE_IDLE`（`:49-61`）。
- 全域開關 `AppGame.Instance.mbPauseXiuXianAndPaoPao` 可一鍵停掉所有休閒動作與氣泡。

### 1.2 環境音效 `NpcEnvironmentComponent.cs`（50 行）

- 資料表 **`npc_environmentsound`**（`NpcEnvironmentSound.cs`，表名 `npc_environmentsound`）。
- 純距離觸發（`ManagedUpdate` `:26`）：玩家距 NPC `< dis` 就 `AudioController.Play(sound)`，離開則 `Stop`。典型用途：鐵匠打鐵聲、攤販吆喝。**只有音效，無動作關聯**。

### 1.3 巡邏 `NpcPatrolComponent.cs`（38 行）

- 建構時 `WayPoint.GetRandomPoint(自身位置, 隨機3~8點, 15f)` 取得巡邏點清單（`:18-19`）。
- `EnterPatrol()` → `npcController.MoveAlongPointPatrol(清單)`；`ExitPatrol()` → `StopMoveAlongWayPoint()`。
- 只有 `IsPatrolNpc()` 的 NPC 才有：判定是 `NpcGender()` 的 **bit 4096** 屬性旗標（`NpcEntity.cs:3072`，`Tools.HasAttribute(NpcGender(), 4096)`）。

---

## 二、核心：WayPoint 路徑點事件系統（場景驅動的湧現互動）

這是「NPC 與環境互動」最關鍵的機制，由兩張表 + 一組執行器組成：

### 2.1 路徑圖 `way_point`（`WayPoint.cs`）

- 場景級導航圖：世界座標 X/Z 從 -256 到 2560，分 64 單位的格（`WayPoint.cs:31-43`）。
- 每個 WayPoint 有 `position`、最多 4 個 `joint`（圖的邊/連接點）、`group`、`eventGroup`。
- `mSingleJointList` = 只有單一連接的「死路點」，用於固定動作（見後）。
- 這是**設計師在地圖上鋪設的路徑網**，巡邏與事件都跑在這張圖上。

### 2.2 事件表 `way_point_event`（`WayPointEvent.cs`）

欄位：`id`、`group`、`type`（對應 `WayPointEventType`）、`chance`（權重）、`condition[]`、`misvalueInt`、`misVauleStr/1/2`。

**16 種事件型別**（`WayPointEventType.cs`）：

| 型別 | 含義 | NPC 做什麼 |
|---|---|---|
| `WPET_RandomAction` | 隨機動作 | 在點上播隨機休閒動畫 |
| `WPET_FixedAction` | 固定動作 | 在點上播固定動畫＋氣泡 |
| `WPET_TalkWithNpc` | 與鄰近 NPC 交談 | **走向 5.5m 內某 NPC，雙方各播動畫對話（NPC↔NPC）** |
| `WPET_AcceptWeiTuo` / `WPET_FaBuWeiTuo` | 接受/發布委託 | 與鄰近持有委託的 NPC 互動 |
| `WPET_PlayerQieCuo` | 切磋 | **主動靠近玩家發起切磋** |
| `WPET_PlayerBiDou` | 比鬥 | 主動找玩家比鬥 |
| `WPET_PlayerQingJiao` | 請教 | 主動找玩家請教 |
| `WPET_PlayerRob` | 搶劫 | 主動找玩家搶劫 |
| `WPET_PlayerYouPian` | 誘騙 | 主動找玩家誘騙 |
| `WPET_FightRedName` | 戰紅名 | 攻擊紅名目標 |
| `WPET_FindShopNpc` | 找商店 NPC | 走向商人 NPC |
| `WPET_VirtualEvent` | 虛擬事件 | 觸發委託傳話類虛擬事件 |
| `WPET_InvitePlayerAcceptWeiTuo` | 邀玩家接委託 | 招呼玩家接委託 |
| `WPET_PlayerHuaYuan` / `WPET_PlayerMusic` | 畫緣/音樂 | **回應玩家使用道具（畫畫/演奏）** |

### 2.3 執行器 `WayPointEventEntity.DoAction()`（`WayPointEventEntity.cs:40`）

流程：
1. 依事件型別決定動畫/目標（`switch` `:55-236`）。挑鄰近 NPC 用 `GetNpcListAround(npc, 5.5f)`（`:404`，含一長串排除條件：非交戰、可互動、是人或動物、非功能 NPC…）。
2. 命中後（`flag=true`）：**停止巡邏 `StopMoveAlongWayPoint()`、退出休閒 `ExitXiuXian()`、關閉 AI 腳本更新**（`:250-255`）。
3. 對目標 NPC 同樣處理（`:258-268`）。
4. 最後 `AutomatScriptManager.ExeScript(200L, ...)`（`:269`）——**腳本 #200 是通用「執行路徑點動作」AI 腳本**，負責播動畫、走位、氣泡。
5. 結束時 `Remove()`（`:272`）還原：回 `ACTION_STATE_IDLE`、重開 AI 腳本、目標 NPC `EnterPatrol()`（`:322-324`），死路點還有 50% 機率連鎖觸發下一個動作（`:330-337`）。

### 2.4 觸發節奏 `WayPointEventManager.cs`（295 行）

- `DoAction(guid, wayPointId)`（`:171`）的前置條件（`:174`）：**必須是 `IsRandomNpc()`（隨機路人 NPC）**、非監獄 NPC、非玩家隊友、`CanContinueWayPointEvent()` 通過。
- 玩家正在用道具且距 ≤15m（`:184`）會優先處理道具互動類事件。
- 死路點（`mSingleJointList`）有 80% 機率走固定動作（`:198`，`Random.Range(0,10000) <= 8000`）。
- 否則依各事件的 `chance` 加權隨機挑一個（`:219-221`，`Tools.RandomOne(權重字典)`）。
- 剛關閉對話 0.5s 內不觸發（`:136`）。
- 全域開關 `AppGame.Instance.mbRandomNpc`（`:78`）與 `mbPause`。

> **重點**：WayPoint 事件主要驅動**隨機 NPC（路人）**，固定劇情 NPC 多靠 `AutomatScript`（自動化腳本）系統控制。

---

## 三、對玩家/環境的「反應式」行為

### 3.1 警戒系統（潛行偵測）`NpcController.cs:2208-2276`

- `UpdateAlertValue(value)`（`:2208`）累加 `AlertValue`（0~1）。
- 玩家處於潛行 `IsQianXing` 且進入 NPC 警戒區（`QianXingManager.IsPlayerInAlertArea`）且**無遮蔽物**（`HasObstacle`，視線判定）時，啟動 `AlertMove()` 協程（`:2230`）——NPC **朝玩家位置 `AutoFindWay` 走過去查看**（`:2251`）。
- `AlertValue` 滿 1 時讓玩家 `ExitQianXingState()`（被發現）。

### 3.2 區域 Collider 觸發 `NpcController.cs:2187-2206`

- `OnFuBenEnterTrigger(Collider)` / `OnFuBenExitTrigger(Collider)`：副本區域觸發回呼。
- 場景另有完整的觸發器體系：`SweetPotato/Areatrigger.cs`、`AreaTriggerEntity.cs`、`AreaTriggerObject.cs`、`ColliderTriggerHook.cs`、`AuraTrigger.cs`（光環範圍）。

### 3.3 復仇追蹤 `NpcController.cs:155`

- NPC `m_Revenge` 時，玩家超出 `m_NpcFight.TrackRange` 才 `LeaveRevenge()`——即被激怒的 NPC 會在追擊範圍內持續追玩家。

---

## 四、玩家 → NPC 的主動互動選單（對照）

這是另一個方向（玩家發起），由 `SweetPotato/NpcInteract.cs`（545 行）+ 資料表 **`npc_interact`** 驅動：

- `INTERACT_TYPE` 列舉約 **110 種**互動（`NpcInteract.cs:24-119`）：交談、商店、PK、拜師(`IT_BAISHI`)、結義(`IT_JIEYI`)、贈禮、煉丹(`IT_ELIXIR`)、鍛造(`IT_SMELT`)、釀酒(`IT_WINE`)、烹飪(`IT_COOK`)、論道(`IT_LUNDAO`)、傳送、門派系列、搶劫、暗殺指派…
- `GetNpcInteractsByNpcID(npcID)`（`:326`）依條件過濾出某 NPC 當下可用的互動清單。
- **此表 mod-aware**：`LoadCSV(int mod, ...)`（`:225`）、`ModId`（`:203`）、`IsModReserve`（`:199`）——可由 mod 擴充。

---

## 五、能力邊界（NPC 做不到什麼）

1. **沒有物件親和性 / 效用 AI**：休閒動畫是「就地播放的動畫片段」，看起來像在用攤位/桌椅/兵器架，但那是**美術把道具與 NPC 擺在一起**，程式碼層面沒有「規劃去使用某個場景物件」的邏輯。
2. **沒有以時鐘為核心的作息（日程）系統**：行為由「玩家距離 + 機率 + 路徑圖 + 條件」驅動，**未發現** time-of-day 的日程狀態機（白天擺攤、晚上回家睡覺這類）。⚠️ 此點為「未找到」，若要做生活模擬 mod 需自行驗證 `AppGame` 的遊戲時間是否有掛 NPC 行為。
3. **移動靠 WayPoint 圖 + NavMesh**：`MoveComponent.AutoFindWay`（`UnitController.cs:2396`）、`MoveAlongWayPoint`（`:2444`），非自由動態避障規劃。

---

## 六、Modding 介入點

### 純資料（已與 Workshop 白名單交叉比對，2026-05-23 確認）

Workshop mod 的可改表 = `SweetPotato/DataMgr.cs:174-194` 的 `RegisterDir`（**正好 21 張**）。
`LoadPlayerMod`（`:373`）讀 `db1_Mod.txt` 時，表名若不在 `RegisterDir` 會**整段靜默丟棄**（`:410-417`，讀掉 N 行後 `continue`）。

| 想做的事 | 表 | 在 21 表白名單？ | 結論 |
|---|---|---|---|
| 改 NPC 可用互動 | `npc_interact` | ✅ 有（`DataMgr.cs:180`）| **可 Workshop 改** |
| 改休閒動作/氣泡 | `npc_xiuxiananim` | ❌ 不在 | **不能 Workshop 改**（本體限定）|
| 改環境音 | `npc_environmentsound` | ❌ 不在 | **不能 Workshop 改** |
| 改路徑圖 | `way_point` | ❌ 不在 | **不能 Workshop 改**（且與場景座標強綁定）|
| 改路徑事件 | `way_point_event` | ❌ 不在 | **不能 Workshop 改** |

> 佐證：這四張表只出現在「本體全量 DB 載入」的 master 表（`DataMgr.cs:957-966`，與 `db1.txt` 對應，~100+ 表），以及 `ModSpace/DataMgr.cs:75-100` 的 mod **編輯器**型別清單裡也**沒有**它們。兩條 mod 路徑都排除這四張。
> 唯一可改的是 `npc_interact`（mod-aware：`LoadCSV(int mod,…)` + `ModId`/`IsModReserve`），但它是「玩家→NPC 選單」，與自主環境行為無關。

### 邏輯改動（BepInEx Harmony）— 自主環境行為唯一可行路徑

- 改休閒/巡邏/環境音/路徑事件的「**內容**」→ 既然不能走 Workshop CSV，只能 BepInEx：
  - **手法 A（直接 patch 行為）**：Harmony patch `NpcXiuXianAnimComponent.PlayAnim`、`WayPointEventEntity.DoAction`、`WayPointEventManager.DoAction`、`NpcPatrolComponent` 等，直接改邏輯/數值。
  - **手法 B（擴白名單，較取巧）**：Harmony postfix `SweetPotato.DataMgr.Init()`，把 `way_point` 等表 `RegisterDir.Add(...)` 進去，就能從自訂 CSV 載入。⚠️ 但 `RegisterType` 要求 `LoadCSV(int mod, string[])` 簽名，而這四個類別只有 `CreateFromCsvRow(string[])`，需自寫 adapter lambda `(mod,row)=>X.CreateFromCsvRow(row)`，且無 mod-ID 命名空間，有 ID 衝突風險。
- 新增事件型別 / 改觸發機率 → patch `WayPointEventEntity.DoAction`、`WayPointEventManager.DoAction`。
- 做真正的作息/物件互動 AI → 在 `NpcController.ManagedUpdate` 注入新狀態，自建場景物件親和性表（本體無此概念）。
- 改警戒/潛行判定 → patch `NpcController.UpdateAlertValue` / `AlertMove`。

---

## 七、關鍵檔案索引

| 檔案 | 行數 | 角色 |
|---|---|---|
| `SweetPotato/NpcController.cs` | 2310 | 大世界 NPC 主控制器 |
| `SweetPotato/NpcXiuXianAnimComponent.cs` | 197 | 休閒動作元件 |
| `SweetPotato/NpcXiuXianAnim.cs` | 65 | `npc_xiuxiananim` 表 |
| `SweetPotato/NpcEnvironmentComponent.cs` | 50 | 環境音效元件 |
| `SweetPotato/NpcPatrolComponent.cs` | 38 | 巡邏元件 |
| `SweetPotato/WayPointEventEntity.cs` | 425 | 路徑點事件執行器（核心）|
| `SweetPotato/WayPointEventType.cs` | 21 | 16 種事件型別列舉 |
| `SweetPotato/WayPointEvent.cs` | — | `way_point_event` 表 |
| `SweetPotato/WayPoint.cs` | — | `way_point` 路徑圖 |
| `WayPointEventManager.cs` | 295 | 事件觸發排程器 |
| `SweetPotato/NpcInteract.cs` | 545 | 玩家→NPC 互動選單 + `npc_interact` 表 |
</content>
</invoke>
