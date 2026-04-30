# 教學：實作 NPC 排程系統 (Radiant AI 基礎)

讓 NPC 擁有自己的「生活作息」是提升開放世界沉浸感的關鍵。本教學說明如何結合全域時間與 COGITO 的 NPC 狀態機。

## 1. 建立全域時間系統 (TimeSystem)

建立一個 Autoload 腳本 `TimeSystem.gd`。

### 實作步驟
```gdscript
extends Node

signal hour_changed(hour)

var current_time : float = 8.0 # 從早上 8 點開始
@export var time_speed : float = 0.01 # 遊戲時間與真實時間比例

func _process(delta):
    var prev_hour = floor(current_time)
    current_time = fmod(current_time + delta * time_speed, 24.0)
    var new_hour = floor(current_time)
    
    if prev_hour != new_hour:
        hour_changed.emit(new_hour)
```

---

## 2. 實作 NPC 排程組件 (ScheduleComponent)

此組件負責監聽時間並切換狀態機。

### 實作步驟
1. 建立 `addons/cogito/CogitoNPC/ScheduleComponent.gd`：
   ```gdscript
   extends Node
   
   @export var npc_state_machine : Node
   
   # 作息表：小時 -> 狀態名
   @export var schedule = {
       8: "work",
       18: "relax",
       22: "sleep"
   }

   func _ready():
       TimeSystem.hour_changed.connect(_on_hour_changed)
       # 初始化當前狀態
       _on_hour_changed(floor(TimeSystem.current_time))

   func _on_hour_changed(hour):
       if schedule.has(hour):
           var target_state = schedule[hour]
           npc_state_machine.goto(target_state)
   ```

---

## 3. 建立對應狀態 (Work, Sleep)

依據 [教學：如何替玩家與 NPC 添加新動作](./adding_character_actions.md)，為 NPC 建立對應節點。

- **`npc_state_sleep.gd`**：
    - `_state_enter()`: 尋找標記為 "Bed" 的 Marker3D，將 NPC 位置設為該處，播放躺下動畫。
    - `_physics_process()`: 什麼都不做（節省效能）。
- **`npc_state_work.gd`**：
    - `_state_enter()`: 導航至工作檯。
    - `_physics_process()`: 循環播放敲打動畫。

---

## 4. 虛擬模擬 (遠距離作息)

當 NPC 因為 Chunk 被卸載而不在場景中時，我們仍需更新他們的邏輯。
1. 在存檔數據中記錄 NPC 最後離開時的時間。
2. 在讀檔時 (`set_state`)，比較當前遊戲時間：
   ```gdscript
   func set_state():
       var current_hour = floor(TimeSystem.current_time)
       # 根據作息表，直接將 NPC 傳送到他現在「應該」在的位置
       var correct_state = get_state_for_hour(current_hour)
       npc_state_machine.goto(correct_state)
       reposition_to_schedule_marker(correct_state)
   ```

---

## 驗證方式
1. 將 `TimeSystem.time_speed` 設快一點。
2. 觀察 NPC 是否在傍晚 6 點自動放下工具，走向酒館或休息區。
3. 觀察 NPC 是否在晚上 10 點走向床鋪並切換至 `sleep` 狀態。
