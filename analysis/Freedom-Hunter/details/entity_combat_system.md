# Entity 與戰鬥系統 深入分析

## 繼承鏈

```
CharacterBody3D
└── Entity (src/entities/entity.gd)
    ├── Player (src/entities/player.gd)
    └── Monster (src/entities/monster.gd)  ← extends "entity.gd"（字串路徑，非 class_name）
```

---

## Entity 基底類別（entity.gd）

### HP 系統

```gdscript
# entity.gd:10-18
var hp: int = 100
var hp_max: int = 100
var hp_regenerable: int = 100   # 可再生上限（受傷後可回復到此值）
var hp_regeneration: int = 1    # 每次回復量
var hp_regeneration_interval: int = 5  # 回復間隔（秒）
signal hp_changed(hp, hp_reg, hp_max)
```

**雙層 HP 設計**：
- `hp`：當前血量
- `hp_regenerable`：可自然回復的上限
- 受傷公式（entity.gd:329）：`hp_regenerable = int(hp + damage_in * regenerable)`
  - `regenerable` 參數（0.0~1.0）決定這次傷害有多少比例「可以再生回來」
  - 例：受 100 傷、regenerable=0.3 → 只有 30 HP 可以慢慢回復

### 耐力系統

```gdscript
# entity.gd:21-32
var stamina: float = 100:
    set(value):
        var previous := stamina
        stamina = clamp(value, 0, stamina_max)
        if previous != stamina:
            stamina_changed.emit(stamina, stamina_max)
```

使用 GDScript setter 自動發射 signal，不需要手動調用。

### AnimationTree 狀態機

```
主狀態機 (state_machine):
    idle-loop  ←→  movement  →  attack  →  rest  →  death

移動子狀態機 (movement_state_machine)，巢狀於 movement 狀態：
    walk-loop  ←→  run-loop  ←→  dodge  ←→  jump  →  falling  →  screaming
```

**狀態驅動移動**（entity.gd:168-193）：
```gdscript
match current_state:
    "rest":     velocity *= Vector3.UP          # 只保留垂直速度（靜止）
    "attack":   velocity *= Vector3(attack_speed, 1, attack_speed)
    "movement":
        match movement_state_machine:
            "walk-loop": velocity *= walk_speed (5.0)
            "run-loop":  velocity *= run_speed  (7.5)，並消耗 stamina
            "dodge":     velocity *= dodge_speed (8.0)
    _:          velocity *= Vector3(0, 1, 0)   # 其他狀態鎖定移動
```

### 傷害計算流程

```
damage(damage_in, regenerable, element=null, weapon=null, entity=null)
    ↓
defense = get_defence()              ← 多型：Entity=0, Player=防具累加
actual_damage = damage_in - defense
    ↓
ailments[element] = timestamp        ← 記錄異常狀態觸發時間
    ↓
hp -= actual_damage
hp_regenerable = hp + damage_in * regenerable
    ↓
if hp <= 0: die()                    ← 觸發死亡
hp_changed.emit(...)
```

### 撞牆傷害

```gdscript
# entity.gd:206-208
var acceleration = (velocity - vi).length()
if acceleration > 10:
    damage(pow(acceleration / 10, 7), 0.5)
```
速度突然驟減超過 10 即觸發墜落/撞牆傷害，指數增長（7次方）使高速衝撞非常致命。

### 多人同步設計

```gdscript
# entity.gd:84-89
func _ready():
    hp_changed.connect(func(hp, hp_reg, hp_max):
        if multiplayer.has_multiplayer_peer() and is_multiplayer_authority():
            rpc("_update_hp", hp, hp_reg, hp_max))
    stamina_changed.connect(func(stam, max):
        if multiplayer.has_multiplayer_peer() and is_multiplayer_authority():
            rpc("_update_stamina", stam, max))
```

**Pattern**：signal + lambda 在 _ready 串接 RPC，只有 authority 端發送。

---

## Player 類別（player.gd）

### 輸入→方向計算（物理引擎每幀）

```gdscript
# player.gd:198-215
var camera := camera_node.get_global_transform()
var input := Vector3()
if Input.is_action_pressed("player_forward"):
    input -= camera.basis.z * strength  # 相機正面方向（-Z）
if Input.is_action_pressed("player_backward"):
    input += camera.basis.z * strength
if Input.is_action_pressed("player_left"):
    input -= camera.basis.x * strength  # 相機右方向（+X）
if Input.is_action_pressed("player_right"):
    input += camera.basis.x * strength
direction = input * Vector3(1, 0, 1)    # 清除 Y 分量
direction = direction.normalized()
```

移動方向相對於相機，而非玩家朝向，符合第三人稱 Action RPG 標準操作。

### 裝備系統

```gdscript
# player.gd:15
var equipment = {
    "weapon": null,
    "armour": {
        "head": null, "torso": null,
        "rightarm": null, "leftarm": null, "leg": null
    }
}
```

**掛載到骨架**（player.gd:31-43）：
```gdscript
func set_equipment(model, bone):
    var skel = $Armature/Skeleton3D
    for node in skel.get_children():
        if node is BoneAttachment3D and node.get_bone_name() == bone:
            node.add_child(model)   # 已有附著點，直接掛入
            return
    # 否則動態建立 BoneAttachment3D
    var ba = BoneAttachment3D.new()
    ba.set_bone_name(bone)
    ba.add_child(model)
    skel.add_child(ba)
```

### 死亡處理（多人情境）

```gdscript
# player.gd:146-153
@rpc("any_peer", "call_local") func died():
    super.died()
    set_process(false)
    set_physics_process(false)
    set_process_input(false)           # 禁用所有輸入
    if not multiplayer.has_multiplayer_peer() or is_multiplayer_authority():
        $/root/hud/respawn.prompt_respawn()  # 只有本地玩家看到復活提示
    $shape.disabled = true             # 禁用碰撞體
```

**非 authority 端**（player.gd:183-189）的死亡動畫：
```gdscript
# _process 中模擬遠端死亡玩家的移動（用於動畫插值）
if state_machine.get_current_node() == "dead" and not is_multiplayer_authority():
    direction = (previous_origin - transform.origin).normalized()
    previous_origin = transform.origin
```

### 互動偵測

```gdscript
# player.gd:77-86
func get_nearest_interact() -> Area3D:
    var areas: Array = $interact.get_overlapping_areas()
    var interacts := []
    for area in areas:
        if area.is_in_group("interact"):
            interacts.append(area)
    if interacts.size() > 0:
        interacts.sort_custom(sort_by_distance)  # 按距離排序
        return interacts[0]
    return null
```

---

## Monster AI 類別（monster.gd）

### AI 狀態流程

```
_physics_process(delta):
    direction = Vector3()              ← 每幀重置方向

    if target_player != null:
        check_target()                 ← 確認目標是否還有效

    if target_player == null:
        find_new_target()              ← 視野內找最近玩家

    if target_player != null:
        hunt_target()                  ← 追蹤模式
    else:
        scout()                        ← 巡邏模式

    nav.get_next_path_position()
    move_entity(delta)
```

### 視野偵測（FOV + Raycast）

```gdscript
# monster.gd:116-123
func line_of_sight(vector: Vector3) -> Dictionary:
    var origin := global_transform.origin
    var eyes: Vector3 = $eyes.global_transform.origin
    var direction := (vector - origin).normalized()
    var angle := global_transform.basis.z.angle_to(direction)
    if angle < field_of_view:          # field_of_view = 120°
        return cast_ray(eyes, vector)  # 視線內才 Raycast
    return {}
```

`find_new_target()`：遍歷視野內所有玩家，對每個玩家做 FOV + Raycast 雙重檢查，取距離最短者。

### 狩獵行為分層

```gdscript
# monster.gd:155-193
func hunt_target():
    var to_target := target_player.global_position - global_position
    var distance := to_target.length()

    if $AnimationTree["parameters/conditions/attacking"]:
        direction = to_target.normalized()
        check_fire_collision()         # 攻擊中持續追蹤 + 火焰傷害判定
    elif distance > 10:
        run(); follow_path()           # 遠距：全速追趕
    elif distance > 5:
        walk(); follow_path()          # 中距：緩步接近
    else:
        attack("attack")               # 近距：發動攻擊
        direction = to_target.normalized()

    # 目標移動超過 1m 才重算路徑（避免每幀重算）
    if old_target_origin.distance_to(target_player.global_position) > 1:
        set_navigation_target(target_player.global_transform.origin)
```

### 火焰攻擊傷害判定

```gdscript
# monster.gd:126-134
func check_fire_collision():
    $fire/RayCast3D.enabled = true
    var to_target := target_player.global_position - global_position
    if $AnimationTree["parameters/conditions/attacking"] and to_target.length() < 5:
        if $fire/RayCast3D.is_colliding() and $fire/RayCast3D.get_collider() == target_player:
            if Time.get_ticks_msec() - last_damage > 1000:  # 1秒冷卻
                target_player.damage(10, 0.3, "fire")
                last_damage = Time.get_ticks_msec()
```

RayCast3D 朝玩家方向射線，確認真的打到（非隔牆）才觸發傷害，同時施加 fire 異常。

### 死亡後腳本替換

```gdscript
# monster.gd:69-76
@rpc("any_peer", "call_local") func died():
    super.died()
    set_physics_process(false)
    $fire.hide()
    $interact.add_to_group("interact")   # 屍體可互動
    $view.disconnect("body_entered", _on_view_body_entered)  # 移除視野偵測
    call_deferred("set_script", preload("res://src/interact/monster drop.gd"))
```

`set_script()` 動態替換腳本，使怪物節點保留在場景樹中但行為完全改變，成為掉落物採集點。

---

## 異常狀態（Ailment）系統

```
ailments: {element_name: timestamp_msec}

Player._on_ailment_added("fire"):
    $Flames.emitting = true
    effect_over_time(
        wait_time=1.0,
        repeat=3,
        effect=damage.bind(10, 0.5),     ← 每秒 10 火焰傷害
        end=func():
            ailments.erase("fire")
            $Flames.emitting = false
    )
```

`effect_over_time`（entity.gd:94-102）使用 `await create_timer()` 異步執行，不阻塞主線程。

Monster 的 `weakness` 字典預定義元素易傷倍率，但目前 damage() 計算中尚未套用（TODO）。

---

## 設計模式總結

| 模式 | 實作位置 | 說明 |
|------|---------|------|
| Template Method | Entity → Player/Monster | `died()`、`respawn()` 由子類 `super()` 後擴展 |
| Observer (Signal) | hp_changed, stamina_changed | 解耦戰鬥數值與 UI/網路層 |
| State Machine | AnimationTree 雙層 | 動畫驅動邏輯，非獨立狀態類別 |
| Authority Pattern | `is_multiplayer_authority()` | 只有 authority 執行物理/AI/發送 RPC |
| Dynamic Script Swap | `set_script()` | Monster 死後變成 Collectible |
