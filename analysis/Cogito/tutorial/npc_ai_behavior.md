# 教學：如何修改與擴充 NPC AI 行為

COGITO 的 NPC 使用基於場景樹的狀態機（`NPC_State_Machine`），狀態之間的切換以 `States.goto("state_name")` 完成。本教學說明如何為 NPC 添加視野感知、聽覺，以及多 NPC 之間的協同警戒。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。
- 已完成 [教學：添加角色動作](adding_character_actions.md) 中 Wander 狀態的實作。

---

## 一、理解現有 Chase 狀態（`npc_state_chase.gd`）

現有的追擊通常由 NPC 場景中的 `Area3D`（偵測範圍）觸發，進入後 `attention_target` 被設定，然後 `npc_state_chase.gd` 每幀更新：
- 導航路徑：`Host.navigation_agent_3d.target_position = chase_target.global_position`
- 移動：`Host.velocity = direction * Host.move_speed`（`npc_state_chase.gd:91,117`）
- 放棄追蹤：超過 `giveup_chase_time` 秒找不到目標，呼叫 `States.load_previous_state("idle")`

```gdscript
# npc_state_chase.gd 核心變數
@export var target_action_distance : float = 1.0    # 到達目標的距離閾值
@export var action_when_caught : String = "attack"  # 到達後切換的狀態
@export var giveup_chase_time : float = 10.0        # 追蹤超時秒數
```

---

## 二、強化感知：加入視覺圓錐 (Vision Cone)

預設觸發方式通常是 `Area3D` 全方位偵測。以下方法讓追擊更符合「只有看到才會追」的潛行邏輯。

### 2.1 節點設定

在 NPC 場景的 `Head` 節點下加入：
```
Head (Node3D)
└── VisionRayCast (RayCast3D)
    ├── enabled = true
    ├── target_position = Vector3(0, 0, -10)   ← 前方 10 單位
    └── collision_mask = Layer 3 (Player)       ← 只掃描玩家所在層
```

**重要**：玩家的 `CollisionShape3D` 應在特定 Layer（預設 `Player` 群組的 tscn 設定中），確認 Layer 號碼與 Mask 一致。

### 2.2 在 npc_state_patrol_on_path.gd 加入視線檢測

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_patrol_on_path.gd 修改
# 在 _physics_process 頂部加入：

@onready var vision_raycast : RayCast3D = Host.find_child("VisionRayCast")

func _physics_process(delta: float) -> void:
    # ── 視線偵測（插入現有邏輯之前）──
    _check_vision()
    # ... 原有巡邏邏輯 ...


func _check_vision() -> void:
    var player = get_tree().get_first_node_in_group("Player")
    if not player or not vision_raycast:
        return
    
    # 距離檢查（先過濾遠距離，減少不必要計算）
    var dist = Host.global_position.distance_to(player.global_position)
    if dist > 15.0:  # 超過 15 單位不偵測
        return
    
    # 視角檢查（前方 120 度視野）
    var dir_to_player = Host.global_position.direction_to(player.global_position)
    var forward = -Host.global_transform.basis.z
    var dot = forward.dot(dir_to_player)
    if dot < 0.5:  # cos(60°) ≈ 0.5，即左右各 60° 共 120°
        return
    
    # 射線阻擋檢查（視線是否被牆壁遮擋）
    vision_raycast.target_position = vision_raycast.to_local(player.global_position)
    vision_raycast.force_raycast_update()
    
    if vision_raycast.is_colliding():
        var collider = vision_raycast.get_collider()
        # 確認打到的是玩家本身（不是玩家後面的牆）
        if collider == player or collider.is_in_group("Player"):
            _trigger_chase(player)


func _trigger_chase(player: Node3D) -> void:
    Host.attention_target = player  # cogito_npc.gd:30
    States.goto("chase")
```

### 2.3 讓 Chase 狀態使用 attention_target

`npc_state_chase.gd` 的 `_state_enter` 預設可能從 `Area3D` 信號獲取目標，確認它讀取 `Host.attention_target`：
```gdscript
# npc_state_chase.gd 修改
func _state_enter() -> void:
    chase_target = Host.attention_target  # 從 NPC 屬性讀取
    if not chase_target:
        States.load_previous_state("idle")
        return
    # ... 其餘邏輯
```

---

## 三、強化感知：聽覺 (Hearing)

聽覺系統需要一個全域信號橋（Signal Bus）。

### 3.1 建立 SignalBus Autoload

建立 `res://scripts/signal_bus.gd`：
```gdscript
# signal_bus.gd (Autoload，命名為 SignalBus)
extends Node

## 發出噪音：position=世界位置，volume=有效半徑（單位：公尺）
signal noise_made(position: Vector3, volume: float)
```

在 **Project Settings → Autoload** 中加入 `signal_bus.gd`，名稱設為 `SignalBus`。

### 3.2 在腳步聲系統中發射信號

`FootstepSurfaceDetector.gd` 的 `_play_interaction()` 播放腳步後加入：
```gdscript
# addons/cogito/DynamicFootstepSystem/Scripts/footstep_surface_detector.gd
# 在播放腳步音效後加入：
func _play_interaction(surface_type: String) -> void:
    # ... 原有邏輯 ...
    audio_stream_player_3d.play()
    
    # 發射全域噪音信號（音量根據是否跑步決定）
    var volume = 6.0 if is_sprinting else 3.0
    SignalBus.noise_made.emit(global_position, volume)
```

也可在**玩家開槍時**發射（在 `wieldable_toy_pistol.action_primary` 中加入 `SignalBus.noise_made.emit(..., 20.0)`）。

### 3.3 在 NPC 的 _ready() 中訂閱信號

在 `cogito_npc.gd` 加入：
```gdscript
# cogito_npc.gd
@export var hearing_range : float = 8.0  # 聽力半徑

func _ready():
    # ... 原有 _ready() 邏輯 ...
    SignalBus.noise_made.connect(_on_noise_made)

func _on_noise_made(noise_pos: Vector3, volume: float) -> void:
    # 只在閒置/巡邏時響應（不干擾已觸發的追擊）
    if npc_state_machine.current in ["chase", "attack"]:
        return
    
    var dist = global_position.distance_to(noise_pos)
    if dist <= min(hearing_range, volume):  # 距離在聽力範圍與音量半徑之內
        attention_target = get_tree().get_first_node_in_group("Player")
        npc_state_machine.goto("chase")
```

---

## 四、群體協同：一隻 NPC 發現玩家通知附近同伴

### 4.1 設定 Enemy 群組

**重要**：COGITO 的 NPC 預設不屬於任何群組。需在 NPC `.tscn` 或 `cogito_npc.gd:_ready()` 中加入：
```gdscript
func _ready():
    # ... 原有邏輯 ...
    add_to_group("Enemy")  # 讓群體協同能查詢到所有 NPC
```

### 4.2 在 Chase 狀態觸發時廣播警報

在 `npc_state_chase.gd` 的 `_state_enter()` 中加入：
```gdscript
func _state_enter() -> void:
    chase_target = Host.attention_target
    if not chase_target:
        States.load_previous_state("idle")
        return
    
    # 廣播警報給 20 單位內的同伴
    _alert_nearby_allies(20.0)
    # ... 其餘追擊邏輯


func _alert_nearby_allies(radius: float) -> void:
    var allies = get_tree().get_nodes_in_group("Enemy")
    for ally in allies:
        if ally == Host:
            continue  # 跳過自己
        if not ally.has_method("receive_alert"):
            continue
        if Host.global_position.distance_to(ally.global_position) <= radius:
            ally.receive_alert(Host.attention_target)
```

在 `cogito_npc.gd` 加入接受警報的方法：
```gdscript
# cogito_npc.gd
func receive_alert(target: Node3D) -> void:
    # 只有閒置/巡邏中的 NPC 才響應警報
    if npc_state_machine.current in ["idle", "patrol_on_path", "wander", "move_to_random_pos"]:
        attention_target = target
        npc_state_machine.goto("chase")
```

---

## 五、整合「警戒 (Alert)」中間狀態（可選）

比直接跳追擊更有層次感的流程：`偵測噪音 → alert（走向聲源調查） → 發現玩家 → chase`。

### 5.1 建立 npc_state_alert.gd

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_alert.gd
extends Node

var Host
var States

@export var investigate_time : float = 5.0  # 停在調查點多久後放棄

var investigate_target : Vector3
var _timer : float = 0.0


func _state_enter() -> void:
    # investigate_target 在切換到此狀態前由外部設定
    Host.navigation_agent_3d.target_position = investigate_target
    _timer = investigate_time
    CogitoGlobals.debug_log(true, "npc_state_alert.gd", "Alert: investigating " + str(investigate_target))


func _state_exit() -> void:
    States.save_state_as_previous(self.name, null)


func _physics_process(delta: float) -> void:
    Host.update_animations(delta)
    
    _timer -= delta
    if _timer <= 0:
        States.goto("idle")  # 調查超時，返回閒置
        return
    
    # 移動到調查點
    if not Host.navigation_agent_3d.is_navigation_finished():
        var next_pos = Host.navigation_agent_3d.get_next_path_position()
        var direction = Host.global_position.direction_to(next_pos)
        if not Host.is_on_floor():
            Host.velocity += Host.get_gravity() * delta
        Host.velocity.x = direction.x * Host.move_speed * 0.7  # 緩慢靠近
        Host.velocity.z = direction.z * Host.move_speed * 0.7
        Host.move_and_slide()
    else:
        # 到達調查點，等待並環視
        Host.velocity = Vector3.ZERO
        _check_vision_at_destination()


func _check_vision_at_destination() -> void:
    var player = get_tree().get_first_node_in_group("Player")
    if not player:
        return
    var dist = Host.global_position.distance_to(player.global_position)
    if dist < 5.0:  # 近距離直接發現
        Host.attention_target = player
        States.goto("chase")
```

### 5.2 觸發切換到 Alert 狀態

修改 `cogito_npc.gd` 的噪音響應：
```gdscript
func _on_noise_made(noise_pos: Vector3, volume: float) -> void:
    if npc_state_machine.current in ["chase", "attack", "alert"]:
        return
    
    var dist = global_position.distance_to(noise_pos)
    if dist <= min(hearing_range, volume):
        if States.has("alert"):  # 確認 alert 狀態存在
            # 需要先設定調查目標
            var alert_state = npc_state_machine.states.get("alert")
            if alert_state:
                alert_state.investigate_target = noise_pos
            npc_state_machine.goto("alert")
        else:
            # 若無 alert 狀態，直接追擊
            attention_target = get_tree().get_first_node_in_group("Player")
            npc_state_machine.goto("chase")
```

---

## 六、驗證清單

| 測試項目 | 預期結果 |
|---|---|
| NPC 在背後移動（慢走） | NPC 無反應（視線偵測：背後不在視角）|
| 在 NPC 正前方 8 單位內移動 | NPC 觸發追擊（Vision Cone 偵測）|
| 在牆後開槍 | NPC 走向開槍位置（聽覺，不是直接追擊）|
| 在一隻 NPC 視野內開槍 | 20 單位內的所有 NPC 也進入追擊（群體協同）|
| NPC 調查完畢但沒看到玩家 | 5 秒後返回 idle |
| 存檔讀檔後 NPC 仍在追擊 | NPC 狀態恢復為 chase（`save()/set_state()` 處理）|
