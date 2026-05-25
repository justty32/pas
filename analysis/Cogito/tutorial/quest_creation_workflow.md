# 教學：任務系統完整工作流程（Quest Creation Workflow）

本教學說明從建立 `CogitoQuest` 資源到在遊戲中接受、推進、完成任務的完整流程，涵蓋 `CogitoQuestUpdater`、`ui_quest_hud.gd`，以及與 Dialogic 的整合。

## 前置知識
- 已閱讀 [Level 5F: 對話整合](../architecture/level5f_dialogue.md)。
- 已取消注解 `DialogicInteraction.gd`（見 [教學：對話介面調整](./ui_modification_dialogue.md)）。

---

## 一、建立 CogitoQuest 資源

`CogitoQuest` 是一個 Godot `Resource`（`cogito_quest.gd`），在 Editor 中建立：

1. `FileSystem → 右鍵 → New Resource → CogitoQuest`
2. 命名：`quest_kill_bandits.tres`

**Inspector 欄位說明**（對應 `cogito_quest.gd`）：

```
quest_name:               "kill_bandits"      ← 程式邏輯用（全小寫、無空格）
quest_title:              "清除盜賊"          ← 顯示在 QuestHUD 的標題
quest_description_active: "前往東邊廢墟，消滅 3 名盜賊。"
quest_description_completed: "感謝你清除了盜賊！"
quest_description_failed:    "你讓盜賊逃走了。"

quest_counter_goal: 3    ← 計數型任務：需要 3 次進度
                         ← 非計數型任務設為 0（直接呼叫 complete_quest）
```

**兩種任務類型**：
- **計數型**：`quest_counter_goal > 0`，呼叫 `change_quest_counter(quest, 1)` 累加，達到目標自動完成。
- **直接完成型**：`quest_counter_goal = 0`，手動呼叫 `CogitoQuestManager.complete_quest(quest)`。

---

## 二、場景中的 CogitoQuestUpdater

`CogitoQuestUpdater`（`cogito_quest_updater.gd`）是掛在場景物件上的觸發器，支援四種操作：`Start`、`Complete`、`Fail`、`ChangeCounter`。

### 用法一：玩家進入區域觸發（Area3D）

```
Area3D
├── CollisionShape3D
└── CogitoQuestUpdater
    ├── quest_to_update: [拖入 quest_kill_bandits.tres]
    ├── update_type: ChangeCounter
    └── counter_change: 1
```

連接信號：`Area3D.body_entered → CogitoQuestUpdater._on_body_entered`（已在腳本中定義）。

**防重複觸發**：`CogitoQuestUpdater` 內建 `has_been_triggered: bool` 旗標，`ChangeCounter` 類型只觸發一次。

### 用法二：NPC 死亡觸發

在 `CogitoNPC` 的死亡處理中呼叫（以 `npc_state_dead.gd` 為例）：

```gdscript
# npc_state_dead.gd 的 enter() 函數中
func enter() -> void:
    Host.animation_tree.set("parameters/Transition/transition_request", "dead")
    
    # 找到場景中對應的 QuestUpdater
    var updater = Host.find_child("BanditQuestUpdater", true, false)
    if updater:
        updater.update_quest()
    
    # 或直接呼叫（需要持有 Quest 資源引用）
    # CogitoQuestManager.change_quest_counter(kill_bandits_quest, 1)
```

更好的做法：在 NPC 上建立一個持有 Quest 資源的組件，NPC 死亡時自動通知：

```gdscript
# bandit_npc.gd extends CogitoNPC（或附加在 NPC 的腳本）
@export var quest_on_death: CogitoQuest
@export var quest_counter_change: int = 1

# 在 HitboxComponent 的 got_hit 信號或死亡信號觸發
func _on_npc_died() -> void:
    if quest_on_death and CogitoQuestManager.is_quest_active(quest_on_death):
        CogitoQuestManager.change_quest_counter(quest_on_death, quest_counter_change)
```

---

## 三、CogitoQuestManager API 速查

`cogito_quest_manager.gd` 所有公開方法：

```gdscript
# 開始任務（接受 CogitoQuest 資源，不是字串！）
CogitoQuestManager.start_quest(quest: CogitoQuest)

# 完成任務（必須先在 active 群組中）
CogitoQuestManager.complete_quest(quest: CogitoQuest)

# 失敗任務
CogitoQuestManager.fail_quest(quest: CogitoQuest)

# 計數型進度（達到 quest_counter_goal 自動呼叫 complete_quest）
CogitoQuestManager.change_quest_counter(quest: CogitoQuest, value_change: int)

# 用 quest_id（int）操作（適合 Dialogic 呼叫）
CogitoQuestManager.call_quest_method(quest_id: int, method: String, args: Array)
CogitoQuestManager.set_quest_property(quest_id: int, property: String, value: Variant)

# 查詢
CogitoQuestManager.is_quest_active(quest)    # → bool
CogitoQuestManager.is_quest_completed(quest) # → bool
CogitoQuestManager.get_active_quests()       # → Array[CogitoQuest]

# 信號（在 Autoload 上）
CogitoQuestManager.quest_activated  # 任務開始
CogitoQuestManager.quest_completed  # 任務完成
CogitoQuestManager.quest_updated    # 計數更新
CogitoQuestManager.quest_failed     # 任務失敗
```

---

## 四、Dialogic 整合：NPC 對話接任務

### 前置條件

1. 已取消注解 `DialogicInteraction.gd`。
2. 建立一個 `QuestBridge` Autoload，持有所有 Quest 資源的引用：

```gdscript
# res://scripts/quest_bridge.gd (Autoload: QuestBridge)
extends Node

## 在 Inspector 中拖入所有 Quest 資源
@export var kill_bandits: CogitoQuest
@export var find_herb: CogitoQuest
# ... 其他任務

func start_quest(quest_name: String) -> void:
    var quest = get(quest_name)
    if quest:
        CogitoQuestManager.start_quest(quest)

func get_quest_status(quest_name: String) -> String:
    var quest = get(quest_name)
    if not quest:
        return "unknown"
    if CogitoQuestManager.is_quest_completed(quest):
        return "completed"
    if CogitoQuestManager.is_quest_active(quest):
        return "active"
    return "available"
```

### Dialogic Timeline 範例（`guard_quest.dtl`）

```
Guard: 冒險者！我們村子附近有盜賊作亂。
Guard: 你願意幫忙清除他們嗎？

[choice]
  + [我願意] → accept
  + [抱歉，我很忙] → refuse
[/choice]

[label accept]
Guard: 太好了！前往東邊廢墟，消滅 3 名盜賊。
[call node="QuestBridge" method="start_quest" args=["kill_bandits"]]
[end_branch]

[label refuse]
Guard: ...好吧。
[end_branch]
```

### 回報任務的 Timeline（`guard_report.dtl`）

```
[if {QuestBridge.get_quest_status("kill_bandits")} == "completed"]
Guard: 你真的做到了！感謝你保護村子。
[call node="CogitoSceneManager._current_player_node" method="increase_currency" args=["gold", 100]]
[else]
Guard: 盜賊還沒清乾淨，繼續加油！
[/if]
```

---

## 五、ui_quest_hud 的顯示機制

`ui_quest_hud.gd` 會自動連接 `CogitoQuestManager` 的所有信號（`_ready()` 中）。任務狀態改變時，UI 自動更新。**不需要手動呼叫 update 函數**。

### 任務日誌顯示位置

`ui_quest_hud.gd:8-13` 顯示節點結構：
```
QuestDisplay (PanelContainer)
└── VBoxContainer
    └── TabContainer
        ├── QUESTS_active     ← 進行中
        ├── QUESTS_completed  ← 已完成
        └── QUESTS_failed     ← 已失敗
```

任務日誌在玩家開啟物品欄時同步顯示（`player_hud.show_inventory` 信號觸發 `_show_quest_display()`）。

### 自訂任務條目外觀

`ui_quest_hud.gd:6` 的 `quest_entry: PackedScene` 是每一條任務的顯示模板。`set_quest_info(title, description, counter_text)` 由 `quest_entry.gd`（`Components/quest_entry.gd`）實作。修改此場景即可自訂任務條目的字體、背景、進度條外觀。

---

## 六、任務存讀檔

COGITO 的任務狀態由 `CogitoSceneManager.save_player_state()` 自動處理（`cogito_scene_manager.gd:225-241`）：
- 存檔：active / completed / failed 三個群組分別存入 `_player_state`
- 讀檔：`quest.start(true)`（mute=true，不播音效）重新初始化

**注意**：`CogitoQuest` 資源必須是**存檔到磁碟的 .tres 檔案**（有 `resource_path`），純程式碼建立的 `CogitoQuest.new()` 無法被正確序列化。

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 與 NPC 對話選擇接任務 | Console：`Quest kill_bandits has been started`；任務日誌出現 |
| 殺死 1 名盜賊 | 任務計數器：`1/3`；Hint 提示更新 |
| 殺死第 3 名盜賊 | 任務自動完成，移至「已完成」分頁 |
| 回報任務後獲得金幣 | `player.player_currencies["gold"].value_current` 增加 |
| 存檔讀檔後 | 任務狀態保持（active/completed）；計數器恢復 |
