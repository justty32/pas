# 教學：如何實現進階動作（快跑、蹲下、趴下、翻滾、瞄準）

本教學在理解 `cogito_player.gd` 的 `_physics_process` 流程後，針對各移動機制提供可直接套用的實作方案。

## 前置知識
- 已閱讀 [Level 5E: 玩家完整移動系統](../architecture/level5e_player_movement.md)。

---

## 一、已內建的移動機制（只需調整參數）

以下功能**已完整實作**於 `cogito_player.gd`，只需在 Inspector 調整 @export 值：

| 功能 | 相關 @export | 預設值 | 說明 |
|---|---|---|---|
| 快跑速度 | `SPRINTING_SPEED` | 8.0 | 消耗 `stamina_attribute`（若有設定）|
| 蹲下速度 | `CROUCHING_SPEED` | 3.0 | 蹲下時的移動速度 |
| 蹲下深度 | `CROUCHING_DEPTH` | -0.9 | 頭部相機 Y 軸偏移（負值 = 向下）|
| 滑步初速 | `SLIDING_SPEED` | 5.0 | 快跑蹲下觸發滑行的初始速度 |
| 滑跳加成 | `SLIDE_JUMP_MOD` | 1.5 | 滑行中跳躍的速度倍率 |

耐力消耗由 `stamina_attribute`（`CogitoStaminaAttribute` 節點）管理；若 `player_attributes` 字典中不含 `"stamina"` 則快跑不消耗耐力。

---

## 二、添加「趴下 (Prone)」

趴下是比蹲下更低的狀態，需要額外的碰撞形狀。

### 2.1 節點設定

打開 `cogito_player.tscn`，在根節點下複製 `CrouchingCollisionShape`，命名為 `ProningCollisionShape`：
- 將其 `CapsuleShape3D` 高度縮小（例如 Height = 0.5, Radius = 0.3）
- 設定位置偏移使其貼地（通常 `position.y` 降低）

### 2.2 腳本修改

在 `cogito_player.gd` 加入：
```gdscript
# 在 Movement Properties 區塊加入
@export var PRONING_SPEED : float = 1.5
@export var PRONING_DEPTH : float = -1.2   # 相機最低點

@onready var proning_collision_shape = $ProningCollisionShape

var is_proning : bool = false
```

在 `_physics_process` 的蹲下切換邏輯（約第 857 行，`TOGGLE_CROUCH` 判斷）附近加入趴下狀態機：

```gdscript
# 在現有的 try_crouch 判斷之後加入
if Input.is_action_just_pressed("crouch"):
    if is_proning:
        # 趴下 → 嘗試起身
        _try_leave_prone()
    elif is_crouching:
        # 蹲下 → 趴下（頭頂有空間就繼續往下）
        is_proning = true
        standing_collision_shape.disabled = true
        crouching_collision_shape.disabled = true
        proning_collision_shape.disabled = false
    else:
        # 站立 → 蹲下（使用原有邏輯）
        try_crouch = !try_crouch


func _try_leave_prone() -> void:
    # 使用 ShapeCast3D 測試起身空間（與原有 try_crouch 邏輯相同）
    crouch_raycast.disabled = false
    if !crouch_raycast.is_colliding():  # 頭頂無阻礙
        is_proning = false
        proning_collision_shape.disabled = true
        crouching_collision_shape.disabled = false  # 先回到蹲下
    crouch_raycast.disabled = true
```

在速度計算段加入趴下的 `current_speed` 與相機深度：
```gdscript
# 在蹲下速度計算前加入
if is_proning:
    current_speed = lerp(current_speed, PRONING_SPEED, delta * LERP_SPEED)
    head.position.y = lerp(head.position.y, PRONING_DEPTH, delta * LERP_SPEED)
    # 跳躍在趴下時禁用
```

---

## 三、手動觸發「翻滾 (Dodge Roll)」

`cogito_player.gd` 的 `animationPlayer` 路徑在玩家場景的 `$Body/Neck/Head/Eyes/AnimationPlayer`（`cogito_player.gd:190`）。

### 3.1 確認動畫資源
確認 `AnimationPlayer` 中有名為 `"roll"` 的動畫（若無則需自行建立）。動畫應包含：
- 相機前傾（模擬翻滾視角）
- 時長約 0.4-0.6 秒

### 3.2 腳本實作

```gdscript
# cogito_player.gd 加入
@export var DODGE_DISTANCE : float = 4.0
@export var DODGE_COOLDOWN : float = 1.0

var is_dodging : bool = false
var dodge_cooldown : float = 0.0
var _dodge_direction : Vector3 = Vector3.ZERO


func _physics_process(delta):
    if dodge_cooldown > 0:
        dodge_cooldown -= delta
    # ... 現有邏輯 ...


# 在 _unhandled_input 中加入
func _unhandled_input(event):
    # ... 現有邏輯 ...
    if event.is_action_pressed("dodge") and is_on_floor() and !is_dodging and dodge_cooldown <= 0:
        start_dodge_roll()


func start_dodge_roll() -> void:
    is_dodging = true
    dodge_cooldown = DODGE_COOLDOWN
    
    var input_dir = Input.get_vector("left", "right", "forward", "back")
    if input_dir != Vector2.ZERO:
        _dodge_direction = (body.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
    else:
        _dodge_direction = -head.global_transform.basis.z
    
    animationPlayer.play("roll")
    
    # 翻滾期間短路移動
    var roll_duration = animationPlayer.current_animation_length if animationPlayer.current_animation_length > 0 else 0.5
    await get_tree().create_timer(roll_duration).timeout
    is_dodging = false
```

在 `_physics_process` 的速度計算段插入短路：
```gdscript
if is_dodging:
    main_velocity = _dodge_direction * DODGE_DISTANCE / 0.5  # 速度 = 距離/時間
    velocity = main_velocity + gravity_vec
    move_and_slide()
    return
```

### 3.3 無敵時間 (I-Frames)

`PlayerInteractionComponent` 沒有內建 `is_invulnerable` 屬性，需在 `cogito_player.gd` 自行加入保護邏輯：
```gdscript
var is_rolling : bool = false  # 使用不同名稱與 is_dodging 區分

func start_dodge_roll() -> void:
    is_rolling = true
    is_dodging = true
    # ... 上方邏輯 ...
    await get_tree().create_timer(roll_duration).timeout
    is_dodging = false
    is_rolling = false


# 在 decrease_attribute("health", ...) 的呼叫處加入保護（約第 1003 行落地傷害）
func _on_damage_taken(amount: float) -> void:
    if is_rolling:
        return  # 翻滾中免疫傷害
    decrease_attribute("health", amount)
```
**注意**：COGITO 的傷害多透過 `damage_received` 信號觸發，需在信號回調中加入 `if is_rolling: return` 的判斷。

---

## 四、瞄準 (ADS) 減速

武器的 ADS 邏輯在 `wieldable_toy_pistol.gd` 中實作，需要與 `cogito_player.gd` 溝通。

### 4.1 在武器腳本加入旗標

```gdscript
# wieldable_toy_pistol.gd 加入
var is_aiming : bool = false

func action_secondary(is_released: bool):
    if is_released:
        is_aiming = false
        # ... 原有 FOV 還原邏輯
    else:
        is_aiming = true
        # ... 原有 FOV 縮放邏輯
```

### 4.2 在玩家腳本讀取武器狀態

正確的武器存取方式是 `player_interaction_component.equipped_wieldable_node`（**無** `get_current_wieldable()` 方法）：
```gdscript
# cogito_player.gd 的速度計算段（約第 897 行）
var ads_multiplier : float = 1.0
var wieldable = player_interaction_component.equipped_wieldable_node
if wieldable and wieldable.get("is_aiming"):  # get() 安全存取，武器無此屬性時返回 null
    ads_multiplier = 0.5  # 瞄準時速度減半

# 套用到目標速度
current_speed = target_speed * ads_multiplier
```

---

## 五、滑步閃避（Slide → Dodge 組合技）

在快跑時直接觸發滑行，並給予朝側向的推力：

```gdscript
# 在 _unhandled_input 中加入
if event.is_action_pressed("dodge") and is_sprinting and is_on_floor():
    # 已有 sliding_timer（cogito_player.gd:195）
    sliding_timer.start()
    
    var lateral_dir = Input.get_vector("left", "right", "forward", "back")
    if abs(lateral_dir.x) > 0.3:  # 有橫向輸入才觸發側滾
        var slide_dir = (body.basis * Vector3(lateral_dir.x, 0, 0)).normalized()
        main_velocity += slide_dir * SLIDING_SPEED * 0.8
```

---

## 六、驗證清單

| 測試項目 | 預期結果 |
|---|---|
| 按兩次蹲下鍵 | 第一次蹲下，第二次趴下；能鑽過更窄的縫隙 |
| 趴下後嘗試起身但頭頂有障礙 | 玩家無法起身（頭頂偵測運作） |
| 快跑中按翻滾鍵 | 玩家有明顯位移，動畫播放 `"roll"` |
| 翻滾期間被擊中 | 不受傷（I-Frames 運作，前提是傷害路徑有加入 `is_rolling` 判斷）|
| 持武器時按次要鍵後移動 | 移動速度明顯降低 50% |
| 冷卻期間連按翻滾 | 不觸發（`dodge_cooldown > 0` 阻擋）|
