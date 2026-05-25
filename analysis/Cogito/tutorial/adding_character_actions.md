# 教學：如何替玩家與 NPC 添加新動作

本教學以完整可執行的程式碼，說明如何在 COGITO 中為玩家添加「衝刺 (Dash)」機制，以及為 NPC 建立「隨機遊走 (Wander)」狀態。

## 前置知識
- 已閱讀 [Level 5E: 玩家完整移動系統](../architecture/level5e_player_movement.md)。
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。

---

## 一、玩家動作：添加「衝刺 (Dash)」

### 原始碼導航
- `addons/cogito/CogitoObjects/cogito_player.gd`（修改此檔案）

### 玩家移動系統概述
`cogito_player.gd` 的物理流程在 `_physics_process(delta)` 中以線性順序執行，衝刺需要在「速度計算」階段插入，並在衝刺期間短路一般加速邏輯。

### 實作步驟

#### 1. 在 Input Map 加入新動作
Godot 頂部選單 → **Project → Project Settings → Input Map** → 點擊 Add 加入 `dash`，綁定到例如 `Shift + W` 或獨立按鍵 `Q`。

#### 2. 定義衝刺變數
在 `cogito_player.gd` 的 `Movement Properties` 匯出組（約第 75 行之後）加入：
```gdscript
# addons/cogito/CogitoObjects/cogito_player.gd
@export_group("Dash Properties")
@export var DASH_SPEED : float = 20.0
@export var DASH_DURATION : float = 0.2
@export var DASH_COOLDOWN : float = 0.8  # 防止連滾

var is_dashing : bool = false
var dash_cooldown_timer : float = 0.0
var _dash_direction : Vector3 = Vector3.ZERO
```

#### 3. 計時器遞減
在 `_physics_process(delta)` **最頂部**（坐下判斷之前）加入：
```gdscript
# 衝刺冷卻倒數
if dash_cooldown_timer > 0:
    dash_cooldown_timer -= delta
```

#### 4. 輸入偵測
在 `_physics_process` 的輸入處理段（約 `try_crouch` 邏輯附近）加入：
```gdscript
# 衝刺輸入偵測（地面且不在衝刺中且冷卻結束）
if Input.is_action_just_pressed("dash") and is_on_floor() and !is_dashing and dash_cooldown_timer <= 0:
    start_dash()
```

#### 5. 啟動衝刺函數
在腳本末尾加入：
```gdscript
func start_dash() -> void:
    is_dashing = true
    dash_cooldown_timer = DASH_COOLDOWN
    # 使用當前 input_dir 決定衝刺方向，無輸入則向前（相機方向）
    var input_dir = Input.get_vector("left", "right", "forward", "back")
    if input_dir != Vector2.ZERO:
        _dash_direction = (body.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
    else:
        _dash_direction = -head.global_transform.basis.z  # 相機朝向
    
    await get_tree().create_timer(DASH_DURATION).timeout
    is_dashing = false
```

#### 6. 物理整合
在 `_physics_process` 的**速度計算段**（`main_velocity lerp` 的邏輯之前）加入短路：
```gdscript
if is_dashing:
    main_velocity = _dash_direction * DASH_SPEED
    # 跳過下方的 lerp 速度計算，直接到 move_and_slide
    velocity = main_velocity + gravity_vec
    move_and_slide()
    return  # ← 短路：衝刺期間不執行其餘物理
```

### 驗證方式
1. 在 Input Map 確認 `dash` 動作已設定。
2. 運行場景，按衝刺鍵，確認角色有明顯短距離加速。
3. 連續按衝刺鍵，確認冷卻時間有效（不會無限連續衝刺）。
4. 確認衝刺不影響重力（衝刺後會正常落地）。

---

## 二、NPC 動作：添加「隨機遊走 (Wander)」狀態

COGITO 的 NPC 狀態機使用「場景樹掛載式狀態」——每個狀態是 NPC_State_Machine 下的子節點，名稱即是狀態鍵值。新增狀態只需三步：**寫腳本 → 掛節點 → 觸發切換**。

### 原始碼導航
- `addons/cogito/CogitoNPC/npc_states/` — 所有狀態腳本
- `addons/cogito/CogitoNPC/npc_states/npc_state_move_to_random_pos.gd` — 參考實作（隨機位置移動）
- `addons/cogito/CogitoNPC/cogito_npc.gd:69` — `navigation_agent_3d: NavigationAgent3D`

### 狀態機運作原理（快速回顧）
`npc_state_machine.gd` 在 `setup()` 時：
1. 掃描所有子節點，以其 `name` 作為鍵存入 `states` Dictionary。
2. 注入 `Host`（NPC 根節點）與 `States`（狀態機本身）到每個狀態節點。
3. 狀態切換時呼叫 `_state_exit()` → 換節點 → 呼叫 `_state_enter()`。

### 步驟一：建立 npc_state_wander.gd

**完整實作，參照 `npc_state_move_to_random_pos.gd` 的模式：**

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_wander.gd
extends Node

# 由 NPC_State_Machine.setup() 自動注入
var Host  # CogitoNPC 實例
var States  # NPC_State_Machine 實例

@export var max_wander_distance : float = 8.0
@export var idle_after_wander : bool = true

enum WanderStatus { RUNNING, WAITING, SUCCESS, FAILURE }
var current_status : WanderStatus = WanderStatus.RUNNING


func _state_enter() -> void:
    CogitoGlobals.debug_log(true, "npc_state_wander.gd", "Wander state entered")
    var destination = _pick_random_destination()
    Host.navigation_agent_3d.target_position = destination
    current_status = WanderStatus.RUNNING


func _state_exit() -> void:
    # 保存本狀態名稱，讓 load_previous_state() 能返回此狀態
    States.save_state_as_previous(self.name, null)
    CogitoGlobals.debug_log(true, "npc_state_wander.gd", "Wander state exiting")


func _physics_process(delta: float) -> void:
    Host.update_animations(delta)  # 更新動畫混合樹（cogito_npc.gd:117）

    match current_status:
        WanderStatus.RUNNING:
            _handle_running(delta)
        WanderStatus.WAITING:
            # 緩慢停下
            Host.velocity.x = move_toward(Host.velocity.x, 0, delta * Host.move_speed)
            Host.velocity.z = move_toward(Host.velocity.z, 0, delta * Host.move_speed)
            Host.move_and_slide()
            if Host.velocity.length_squared() < 0.01:
                current_status = WanderStatus.SUCCESS
        WanderStatus.SUCCESS:
            if idle_after_wander:
                States.goto("idle")
            else:
                # 直接再找一個新目的地
                var destination = _pick_random_destination()
                Host.navigation_agent_3d.target_position = destination
                current_status = WanderStatus.RUNNING
        WanderStatus.FAILURE:
            # 無法到達目的地，重新選點
            var destination = _pick_random_destination()
            Host.navigation_agent_3d.target_position = destination
            current_status = WanderStatus.RUNNING


func _handle_running(delta: float) -> void:
    if Host.navigation_agent_3d.is_navigation_finished():
        current_status = WanderStatus.WAITING
        return
    if not Host.navigation_agent_3d.is_target_reachable():
        current_status = WanderStatus.FAILURE
        return
    _move_to_next_position(delta)


func _move_to_next_position(delta: float) -> void:
    var next_pos = Host.navigation_agent_3d.get_next_path_position()

    if not Host.is_on_floor():
        Host.velocity += Host.get_gravity() * delta

    var direction = Host.global_position.direction_to(next_pos)
    var look_target = Vector3(
        Host.global_position.x + Host.velocity.x,
        Host.global_position.y,
        Host.global_position.z + Host.velocity.z
    )

    if direction:
        Host.face_direction(look_target)
        Host.velocity.x = direction.x * Host.move_speed  # 使用 walk_speed
        Host.velocity.z = direction.z * Host.move_speed
    else:
        Host.velocity.x = move_toward(Host.velocity.x, 0, Host.move_speed)
        Host.velocity.z = move_toward(Host.velocity.z, 0, Host.move_speed)

    Host.move_and_slide()


func _pick_random_destination() -> Vector3:
    var angle = randf_range(0, TAU)
    var dist = randf_range(2.0, max_wander_distance)
    return Host.global_position + Vector3(cos(angle) * dist, 0, sin(angle) * dist)
```

### 步驟二：在 Godot 編輯器中掛載狀態

1. 開啟 NPC 場景（如 `cogito_npc.tscn`）。
2. 在場景樹中找到 `NPC_State_Machine` 節點。
3. 在 `NPC_State_Machine` 下**新增 Node 子節點**。
4. 在 Inspector 的 Script 欄位附加 `npc_state_wander.gd`。
5. **關鍵**：將該節點重新命名為 `wander`（狀態機以節點名稱為鍵）。
6. 調整 `max_wander_distance` 等 @export 屬性。

### 步驟三：修改 npc_state_idle.gd 觸發切換

原始的 `npc_state_idle.gd:9-14` 在等待 3 秒後固定跳到 `patrol_on_path`，改為根據機率決定：

```gdscript
# addons/cogito/CogitoNPC/npc_states/npc_state_idle.gd（修改）
@export var wander_probability : float = 0.5  # 50% 機率遊走

func _state_enter():
    CogitoGlobals.debug_log(true, "npc_state_idle.gd", "Idle state entered")
    await get_tree().create_timer(randf_range(2.0, 5.0)).timeout  # 隨機閒置時間

    if States.has("wander") and randf() < wander_probability:
        States.goto("wander")
    elif States.has("patrol_on_path"):
        States.goto("patrol_on_path", null)
    # 否則停留在 idle（會再次觸發 _state_enter）
```

**`States.has(state_name)`**（`npc_state_machine.gd:49`）：安全地檢查狀態是否存在，避免 NPC 場景沒有掛載 `wander` 節點時報錯。

### 步驟四：NPC 偵測到玩家後恢復 wander

在 `npc_state_chase.gd` 的失去追蹤邏輯中（若玩家逃離），可讓 NPC 返回遊走：
```gdscript
# npc_state_chase.gd 中，當追蹤失敗時：
if current_chase_status == ChaseStatus.LOST:
    if States.has("wander"):
        States.goto("wander")
    else:
        States.load_previous_state("idle")
```

### 存檔整合

NPC 的 `save()` 儲存 `saved_enemy_state = npc_state_machine.current`（`cogito_npc.gd:191`），讀檔時 `set_state()` 會 `npc_state_machine.goto(saved_enemy_state)`（`cogito_npc.gd:183`）。因此 `wander` 狀態若在存檔時是當前狀態，讀檔後會自動恢復。

### 驗證方式
1. 放置一個帶有 `wander` 狀態的 NPC 到場景。
2. 開啟 `CogitoGlobals` 中的 `is_logging = true`。
3. 運行遊戲，觀察 Console：應看到 `Idle state entered` → 等待幾秒 → `Wander state entered` → NPC 移動 → `Idle state entered`。
4. 確認 NPC 在地板上正確移動，不會穿牆（NavigationMesh 需覆蓋場景）。
5. 存檔後重讀，確認 NPC 狀態正確恢復。
