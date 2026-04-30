# Cogito — Level 4C 任務系統分析

## 一、系統架構概覽

```
CogitoQuestManager（Autoload Node）
  ├─ available : AvailableQuestsGroup   ← 可接但尚未接受的任務
  ├─ active    : ActiveQuestsGroup      ← 進行中任務
  ├─ completed : CompletedQuestsGroup   ← 已完成任務
  └─ failed    : FailedQuestsGroup      ← 失敗任務

CogitoQuest（Resource .tres）           ← 任務資料定義
CogitoQuestUpdater（Node3D）            ← 場景中的觸發橋接組件
ui_quest_hud.gd（Node）                 ← 任務列表 UI
QuestEntry（Control）                   ← 單筆任務顯示組件
```

---

## 二、CogitoQuest（任務資料）

**位置**：`QuestSystem/CustomResources/cogito_quest.gd`，繼承 `Resource`

### 欄位定義

| 欄位 | 類型 | 用途 |
|---|---|---|
| `quest_name` | String | 程式邏輯識別名稱（內部使用） |
| `quest_title` | String | 顯示於 UI 的標題 |
| `quest_description_active/completed/failed` | String | 三個狀態的描述文字 |
| `quest_description` | String | 當前動態描述（由狀態切換時更新） |
| `quest_counter_current` | int | 當前進度計數 |
| `quest_counter_goal` | int | 完成門檻 |
| `quest_completed` | bool | 完成旗標 |
| `quest_failed` | bool | 失敗旗標 |
| `audio_on_start/complete/fail` | AudioStream | 各狀態的音效 |

### quest_counter 響應式屬性

```
var quest_counter: int:
  get: return quest_counter_current
  set(value):
    quest_counter_current = value
    if quest_counter_current >= quest_counter_goal and !quest_completed:
      complete()   // 自動完成任務
```

`quest_counter` 是計算屬性（getter/setter），賦值時自動檢查是否達成目標。直接操作 `quest_counter_current` 則**不會**觸發自動完成。

### 狀態方法

```
start(_mute = false):
  play audio_on_start
  quest_description = quest_description_active
  quest_completed = false; quest_failed = false

complete(_mute = false):
  play audio_on_complete
  quest_description = quest_description_completed
  quest_counter_current = quest_counter_goal  // 強制設為目標值
  quest_completed = true; quest_failed = false

failed(_mute = false):
  play audio_on_fail
  quest_description = quest_description_failed
  quest_failed = true; quest_completed = false

update():
  quest_completed = true  // ⚠ 僅設旗標，無其他邏輯（TODO: 未實作）
```

---

## 三、CogitoQuestGroup（任務群組）

**位置**：`QuestSystem/CustomResources/cogito_quest_group.gd`，繼承 `Node`

```
CogitoQuestGroup
  └─ quests : Array[CogitoQuest]

add_quest(quest)       → quests.append(quest)
remove_quest(quest)    → quests.erase(quest)
is_quest_inside(quest) → quest in quests
clear_group()          → quests.clear()
get_quest_from_id(id)  → 線性掃描 quest.id（⚠ 見下方 Bug）
```

四個子類（`AvailableQuestsGroup` / `ActiveQuestsGroup` / `CompletedQuestsGroup` / `FailedQuestsGroup`）除 `ActiveQuestsGroup` 有一個 `update_quest(id)` 方法外，其他僅繼承基類，無額外邏輯。

---

## 四、CogitoQuestManager（任務管理器 Autoload）

**位置**：`QuestSystem/cogito_quest_manager.gd`

### 訊號

| 訊號 | 觸發時機 |
|---|---|
| `quest_activated(quest)` | 任務進入 active 群組 |
| `quest_updated(quest)` | 計數器變更 |
| `quest_completed(quest)` | 任務進入 completed 群組 |
| `quest_failed(quest)` | 任務進入 failed 群組 |

### 核心流程方法

**start_quest(quest)**：
```
防衛檢查：若已在 active/completed/failed 中 → 直接 return
available.remove_quest(quest)
active.add_quest(quest)
quest_activated.emit(quest)
quest.start()
Audio.play_sound(COGITO_QUEST_START)
```

**complete_quest(quest)**：
```
if !active.is_quest_inside(quest): return   // 必須在進行中
if quest.quest_completed == false: return   // 必須已標記完成

quest.complete()
active.remove_quest(quest)
completed.add_quest(quest)
quest_completed.emit(quest)
```

注意：`complete_quest()` 需要 `quest.quest_completed == true` 才執行。此旗標由 `quest.complete()` 或 `quest_counter` setter 自動設置，因此通常流程是先透過 counter 達到目標自動設旗標，再由 `complete_quest()` 移動群組。

**fail_quest(quest)**：
```
if !active.is_quest_inside(quest): return
quest.failed()
active.remove_quest(quest)
failed.add_quest(quest)
quest_failed.emit(quest)
```

**change_quest_counter(quest, value_change)**：
```
if !active.is_quest_inside(quest): return
quest.quest_counter_current += value_change   // 直接改 _current（非 setter）
quest_updated.emit(quest)

if quest.quest_counter_current == quest.quest_counter_goal:   // 精確相等判斷
  quest.update()
  complete_quest(quest)
```

⚠ **設計不一致**：
- `quest_counter` setter 用 `>=`（超過也觸發）
- `change_quest_counter` 用 `==`（精確相等才觸發）

若 `value_change` 超過剩餘需求（如目標=5，當前=3，增加+3），counter 跳至 6，`==5` 不成立，任務不會完成。

### 反射方法

```
call_quest_method(quest_id, method, args):
  掃描所有群組 → 找到指定 id 的 quest → quest.callv(method, args)

set_quest_property(quest_id, property, value):
  掃描所有群組 → 找到 quest → 驗證 property 存在 → quest.set(property, value)
```

這兩個方法允許在不知道具體任務類別的情況下動態操作任務屬性，但目前 `CogitoQuest.id` 已被注解（`#@export var id: int`），導致 `get_quest_from_id()` 無法正確運作。

---

## 五、CogitoQuestUpdater（場景觸發橋接組件）

**位置**：`QuestSystem/Components/cogito_quest_updater.gd`，繼承 `Node3D`

### Inspector 欄位

```
quest_to_update : CogitoQuest   ← 拖入目標 .tres 資源
update_type : UpdateType        ← Start / Complete / Fail / ChangeCounter
counter_change : int = 0        ← ChangeCounter 時的增量（可為負）
```

### 觸發邏輯

```
update_quest():
  match update_type:
    Start:
      CogitoQuestManager.start_quest(quest_to_update)
    Complete:
      quest_to_update.update()            // 先設 quest_completed = true
      CogitoQuestManager.complete_quest(quest_to_update)
    Fail:
      CogitoQuestManager.fail_quest(quest_to_update)
    ChangeCounter:
      if has_been_triggered: return       // 防止重複觸發
      if !is_quest_active:
        CogitoQuestManager.start_quest(quest_to_update)  // 自動啟動
      CogitoQuestManager.change_quest_counter(quest_to_update, counter_change)
      has_been_triggered = true
```

**ChangeCounter 的自動啟動**：若任務尚未開始，進入觸發區域時會先自動 `start_quest()`，再 `change_quest_counter()`，讓設計者不需要另外放置 Start 觸發器。

### 內建事件連接

```
_on_body_entered(body):
  if body.is_in_group("Player"):
    update_quest()      // 區域觸發（Area3D 子節點）

_on_pickup_component_was_interacted_with(...):
  update_quest()        // 撿起物品時觸發（連接 PickupComponent 信號）
```

設計者只需在 Inspector 拖入任務資源並選擇操作類型，無需撰寫任何腳本。

### 持久化支援

```
save():
  return {
    "node_path": get_path(),
    "has_been_triggered": has_been_triggered,
    "pos_x/y/z": ..., "rot_x/y/z": ...
  }

set_state():
  pass  // 空實作（反射式屬性賦值已由 load_scene_state 處理）
```

`CogitoQuestUpdater` 加入 `"save_object_state"` 群組後，`has_been_triggered` 會隨場景狀態存讀，確保玩家離開場景再回來後不會重複觸發已完成的計數。

---

## 六、UI 系統

### ui_quest_hud.gd

**位置**：`QuestSystem/Components/ui_quest_hud.gd`

```
_ready():
  CogitoQuestManager 四個訊號 → 對應 _on_quest_* 方法（發通知）
  player_hud.show_inventory → _show_quest_display()
  player_hud.hide_inventory → _hide_quest_display()
  quest_display.hide()  // 預設隱藏

_show_quest_display():
  update_active_quests()
  update_completed_quests()
  update_failed_quests()
  quest_display.show()
```

**全量重建模式**：每次開啟物品欄時，清除所有已顯示的 `QuestEntry` 節點，再從 QuestManager 讀取當前清單重建。無增量更新。

```
update_active_quests():
  清除 active_group 所有子節點
  for quest in CogitoQuestManager.get_active_quests():
    instanced_entry = quest_entry.instantiate()
    active_group.add_child(instanced_entry)
    instanced_entry.set_quest_info(
      quest.quest_title,
      quest.quest_description,
      str(quest_counter_current) + "/" + str(quest_counter_goal)
    )
```

### QuestEntry

**位置**：`QuestSystem/Components/quest_entry.gd`，繼承 `Control`

```
set_quest_info(name, description, counter):
  quest_name_label.text = name
  quest_description_label.text = description
  if counter == "0/0":
    quest_counter_label.text = ""   // 無計數器任務隱藏此欄
  else:
    quest_counter_label.text = counter
```

### 通知系統（Quest Notification）

```
_on_quest_activated/completed/failed/updated(quest):
  if send_quest_notifications:
    player_hud._on_set_hint_prompt(null,
      tr("QUEST_start") + ": " + tr(quest.quest_title)  // 本地化鍵值
    )
```

任務狀態變更時以 Hint Prompt（與互動提示共用組件）顯示通知字串，支援 `tr()` 本地化。

---

## 七、完整任務生命週期

```
【設計階段】
  在 FileSystem 建立 .tres（CogitoQuest Resource），填寫名稱、描述、計數目標

【遊戲中接取任務】
  玩家接觸 CogitoQuestUpdater（Start 類型）或 NPC 對話
    → CogitoQuestManager.start_quest(quest)
    → quest 移入 active 群組
    → quest_activated.emit → HUD 通知

【進度更新】
  玩家完成子目標（觸碰觸發區 / 撿起物品）
    → CogitoQuestUpdater.update_quest()（ChangeCounter）
    → CogitoQuestManager.change_quest_counter(quest, +1)
    → quest_counter_current += 1
    → quest_updated.emit → HUD 通知
    → 若 counter == goal → quest.update() → complete_quest()

【完成任務】
  CogitoQuestManager.complete_quest(quest)
    → quest 從 active 移入 completed
    → quest_completed.emit → HUD 通知

【失敗任務】
  CogitoQuestManager.fail_quest(quest)
    → quest 從 active 移入 failed
    → quest_failed.emit → HUD 通知

【存讀檔】
  save: _player_state.player_active/completed/failed_quests = [...CogitoQuest Resources]
        _player_state.player_active_quest_progression = {quest_name: counter}
  load: for quest in active_quests: quest.start(true); active.add_quest(quest)
        for entry in progression: quest.quest_counter = entry_value
```

---

## 八、任務群組狀態轉移圖

```
           ┌──────────────────────────────────────┐
           │                                      │
        [available]                               │
    (CogitoQuest .tres 預設狀態)                   │
           │                                      │
    start_quest()                                 │
           │                                      │
           ▼                                      │
        [active]                                  │
    進行中，計數器運作                             │
           │                                      │
     ┌─────┴──────┐                               │
     │            │                               │
complete_quest() fail_quest()                     │
     │            │                               │
     ▼            ▼                               │
 [completed]  [failed]                            │
     │            │                               │
     └────────────┴──── move_quest_to_group() ───►┘
                        （可強制移動，繞過正常流程）
```

---

## 九、設計模式與問題分析

### 設計亮點

1. **Resource-as-Quest-Definition**：任務定義為 `.tres` 檔案，在 Godot Editor 的 FileSystem 中可視化管理，支援版本控制，無需資料庫

2. **群組狀態機**：用四個陣列（available/active/completed/failed）取代任務內部狀態字段，群組成員資格即是狀態，邏輯清晰

3. **CogitoQuestUpdater 無代碼橋接**：設計者不寫腳本，透過 Inspector 拖入任務資源並選擇操作類型，物理觸碰或撿取即觸發——降低設計門檻

4. **訊號解耦**：QuestManager 發訊號，HUD 訂閱，任務邏輯與顯示完全分離

5. **本地化整合**：所有 UI 通知文字使用 `tr()` 鍵值，與 Cogito 本地化系統統一

### 已知問題

| 問題 | 位置 | 影響 |
|---|---|---|
| `quest.update()` 未實作 | `cogito_quest.gd:81` | 呼叫 `Complete` 類型時只設旗標，無法正確完成進度型任務 |
| `quest.id` 已被注解 | `cogito_quest.gd:7` | `get_quest_from_id()` / `call_quest_method()` / `set_quest_property()` 無法運作 |
| `==` vs `>=` 不一致 | `cogito_quest_manager.gd:101` | `change_quest_counter` 用精確相等，超過目標不觸發完成 |
| `has_been_triggered` 不支援重置 | `cogito_quest_updater.gd:10` | 若任務需重複計數（如多個撿取點），後續觸發器無法觸發 |
