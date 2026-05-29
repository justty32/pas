# 教學：實作 NPC 排程系統（Radiant AI 基礎）

讓 NPC 擁有「生活作息」是沉浸式開放世界的關鍵。本教學使用 Autoload 全域時間、`ScheduleComponent` 組件，以及兩個完整的自訂 NPC 狀態：`sleep` 和 `work`。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。
- 已完成 [教學：如何替玩家與 NPC 添加新動作](./adding_character_actions.md)（知道如何建立自訂 NPC 狀態）。

---

## 一、建立全域時間系統（TimeSystem Autoload）

建立 `res://scripts/time_system.gd`，在 **Project Settings → Autoload** 加入（名稱：`TimeSystem`）：

```gdscript
# res://scripts/time_system.gd
extends Node

## 遊戲時間整點切換時發射（hour = 0~23）
signal hour_changed(hour: int)

## 目前遊戲時間（0.0 ~ 24.0）
var current_time : float = 8.0

## 時間流速：1.0 = 真實秒數，60.0 = 1 分鐘對應 1 遊戲小時
@export var time_speed : float = 60.0


func _process(delta: float) -> void:
    var prev_hour := floori(current_time)
    current_time = fmod(current_time + delta * time_speed / 3600.0, 24.0)
    var new_hour := floori(current_time)

    if prev_hour != new_hour:
        hour_changed.emit(new_hour)


func get_hour() -> int:
    return floori(current_time)


func get_state_for_hour(hour: int, schedule: Dictionary) -> String:
    # 倒序找最近的時間點
    var best_hour := -1
    for h: int in schedule.keys():
        if h <= hour and h > best_hour:
            best_hour = h
    # 若沒有找到（例如 hour=2，作息從 8 點開始），取前一天最後一個
    if best_hour == -1:
        for h: int in schedule.keys():
            if h > best_hour:
                best_hour = h
    return schedule.get(best_hour, "idle")
```

**`time_speed` 換算**：`time_speed = 60` 時，60 秒真實時間 = 1 遊戲小時（即一個遊戲日為 24 分鐘）。

---

## 二、建立 ScheduleComponent

建立 `addons/cogito/Components/ScheduleComponent.gd`，掛載到 NPC 根節點下：

```gdscript
# addons/cogito/Components/ScheduleComponent.gd
extends Node
class_name ScheduleComponent

## 作息表：整點小時 → 狀態名稱（必須是 NPC 狀態機中存在的狀態）
## 範例：{8: "work", 18: "relax", 22: "sleep"}
## 注意：GDScript @export 對 Dictionary 只支援 String 鍵；整點轉換在 _on_hour_changed 中處理
@export var schedule_string : Dictionary = {
    "8":  "work",
    "12": "relax",
    "18": "relax",
    "22": "sleep"
}

## 指向 NPC 的 NPC_State_Machine 節點
@export var npc_state_machine : Node

var _schedule : Dictionary = {}


func _ready() -> void:
    # 將字串鍵轉為整數鍵
    for key in schedule_string:
        _schedule[int(key)] = schedule_string[key]

    TimeSystem.hour_changed.connect(_on_hour_changed)
    # 初始化：根據當前時間立即切換到正確狀態
    _on_hour_changed(TimeSystem.get_hour())


func _on_hour_changed(hour: int) -> void:
    var target_state = TimeSystem.get_state_for_hour(hour, _schedule)
    if npc_state_machine and npc_state_machine.current != target_state:
        # 只有當前不在目標狀態時才切換，避免打斷攻擊等高優先級狀態
        var current = npc_state_machine.current
        if current not in ["chase", "attack"]:
            CogitoGlobals.debug_log(true, "ScheduleComponent", "Hour %d: switching %s → %s" % [hour, current, target_state])
            npc_state_machine.goto(target_state)


## 取得當前「應在」的狀態（供虛擬模擬使用）
func get_current_scheduled_state() -> String:
    return TimeSystem.get_state_for_hour(TimeSystem.get_hour(), _schedule)
```

### 掛載到 NPC 場景

- **CogitoNPC** (CharacterBody3D + cogito_npc.gd)
  - **NPC_State_Machine**
    - idle
    - chase
    - attack
    - work（新增）
    - sleep（新增）
  - **ScheduleComponent** (+ schedule_component.gd)
    - Inspector: npc_state_machine = ../NPC_State_Machine

---

## 三、建立 npc_state_sleep.gd

睡眠狀態：NPC 移動至最近的 "Bed" Marker3D 並停止所有 AI。

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_sleep.gd
extends Node

var Host   # 由 NPC_State_Machine 自動填入
var States

## 搜尋範圍內的 Bed Marker3D（放在床頭）
@export var bed_search_group : String = "Bed"
@export var arrival_threshold : float = 0.5

var _bed_position : Vector3 = Vector3.ZERO
var _arrived : bool = false


func _state_enter() -> void:
    _arrived = false
    _find_nearest_bed()

    if _bed_position != Vector3.ZERO:
        Host.navigation_agent_3d.target_position = _bed_position
    else:
        # 找不到床：原地停止
        _arrived = true

    CogitoGlobals.debug_log(true, "npc_state_sleep", "Sleep: heading to bed at " + str(_bed_position))


func _state_exit() -> void:
    States.save_state_as_previous(self.name, null)


func _physics_process(delta: float) -> void:
    if _arrived:
        # 躺下：速度歸零，停止 AI
        Host.velocity = Vector3.ZERO
        Host.move_and_slide()
        return

    # 導航至床位
    if Host.navigation_agent_3d.is_navigation_finished():
        _arrived = true
        _play_sleep_animation()
        return

    var next_pos = Host.navigation_agent_3d.get_next_path_position()
    var direction = Host.global_position.direction_to(next_pos)

    if not Host.is_on_floor():
        Host.velocity += Host.get_gravity() * delta

    Host.velocity.x = direction.x * Host.move_speed * 0.7
    Host.velocity.z = direction.z * Host.move_speed * 0.7
    Host.face_direction(next_pos)
    Host.move_and_slide()
    Host.update_animations(delta)


func _find_nearest_bed() -> void:
    var beds = Host.get_tree().get_nodes_in_group(bed_search_group)
    var best_dist := INF
    for bed in beds:
        var dist = Host.global_position.distance_to(bed.global_position)
        if dist < best_dist:
            best_dist = dist
            _bed_position = bed.global_position


func _play_sleep_animation() -> void:
    # 嘗試播放 sleep 動畫；若無則維持 idle
    if Host.animation_tree:
        # 切換到睡眠 upper body 狀態（需在 AnimationTree 中建立 "sleep" 狀態）
        Host.set_upper_body_state("sleep")
```

---

## 四、建立 npc_state_work.gd

工作狀態：NPC 移動至 "WorkStation" Marker3D 並循環播放工作動畫。

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_work.gd
extends Node

var Host
var States

@export var workstation_group : String = "WorkStation"
@export var work_anim_interval : float = 3.0  # 每次工作動畫的間隔

var _work_position : Vector3 = Vector3.ZERO
var _arrived : bool = false
var _work_timer : float = 0.0


func _state_enter() -> void:
    _arrived = false
    _work_timer = 0.0
    _find_nearest_workstation()

    if _work_position != Vector3.ZERO:
        Host.navigation_agent_3d.target_position = _work_position


func _state_exit() -> void:
    States.save_state_as_previous(self.name, null)


func _physics_process(delta: float) -> void:
    if _arrived:
        # 到達後：朝工作台方向，循環工作動畫
        Host.velocity = Vector3.ZERO
        Host.face_direction(_work_position)
        Host.move_and_slide()

        _work_timer -= delta
        if _work_timer <= 0:
            _work_timer = work_anim_interval
            _play_work_animation()
        return

    # 導航至工作台
    if Host.navigation_agent_3d.is_navigation_finished():
        _arrived = true
        _work_timer = work_anim_interval
        return

    var next_pos = Host.navigation_agent_3d.get_next_path_position()
    var direction = Host.global_position.direction_to(next_pos)

    if not Host.is_on_floor():
        Host.velocity += Host.get_gravity() * delta

    Host.velocity.x = direction.x * Host.move_speed
    Host.velocity.z = direction.z * Host.move_speed
    Host.face_direction(next_pos)
    Host.move_and_slide()
    Host.update_animations(delta)


func _find_nearest_workstation() -> void:
    var stations = Host.get_tree().get_nodes_in_group(workstation_group)
    var best_dist := INF
    for station in stations:
        var dist = Host.global_position.distance_to(station.global_position)
        if dist < best_dist:
            best_dist = dist
            _work_position = station.global_position


func _play_work_animation() -> void:
    # 觸發敲擊動畫（使用 NPC 攻擊動畫的 OneShot 節點）
    if Host.animation_tree:
        Host.animation_tree.set(
            "parameters/UpperBodyState/RaisedFists/attack/request",
            AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE
        )
```

---

## 五、場景標記設定

在場景中放置導航標記，並加入對應群組：

- **Scene**
  - **CogitoNPC**
    - ScheduleComponent
  - **BedMarker** (Marker3D)（加入群組 "Bed"）
    - 位於床頭，Y 偏移與 NPC 腳底對齊
  - **WorkstationMarker** (Marker3D)（加入群組 "WorkStation"）
    - 位於鐵砧或工作台前

**群組加入方式**：選取 Marker3D → Node 面板 → Groups → 輸入群組名稱。

---

## 六、虛擬模擬（跨場景作息延續）

COGITO 讀檔時會呼叫 `cogito_npc.gd:set_state()`。在此加入即時作息同步：

```gdscript
# cogito_npc.gd 的 set_state() 擴充
func set_state():
    find_cogito_properties()
    load_patrol_points()

    # 恢復戰鬥狀態
    npc_state_machine.goto(saved_enemy_state)

    # 虛擬模擬：若有 ScheduleComponent，強制同步到當前應在的作息狀態
    var schedule_comp = find_child("ScheduleComponent", true, false)
    if schedule_comp and saved_enemy_state not in ["chase", "attack"]:
        var correct_state = schedule_comp.get_current_scheduled_state()
        npc_state_machine.goto(correct_state)
        _reposition_to_schedule_marker(correct_state, schedule_comp)


func _reposition_to_schedule_marker(state_name: String, schedule_comp: Node) -> void:
    # 依狀態名稱找對應 Marker 並傳送 NPC
    var group_map := {"sleep": "Bed", "work": "WorkStation"}
    var group = group_map.get(state_name, "")
    if group.is_empty():
        return
    var markers = get_tree().get_nodes_in_group(group)
    if markers.is_empty():
        return
    var nearest = markers[0]
    var best_dist := INF
    for m in markers:
        var d = global_position.distance_to(m.global_position)
        if d < best_dist:
            best_dist = d
            nearest = m
    global_position = nearest.global_position
```

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 將 `time_speed` 設為 3600（1 秒 = 1 小時）| 時間快速流逝 |
| 時鐘到達作息表中的 "22"（睡覺）| NPC 走向最近的 Bed 標記並停止 |
| 時鐘到達 "8"（工作）| NPC 走向最近的 WorkStation 並循環敲擊動畫 |
| NPC 正在追擊玩家時時間到達 "22" | NPC 繼續追擊（不因作息中斷）|
| 存檔後讀檔（時間為 "3" 凌晨）| NPC 傳送到床邊，切換至 sleep 狀態 |
