# 教學：如何實現局部時間緩速 (Selective Time Dilation)

本教學實作「局部時間縮放」——讓特定 NPC、物理物件或特效變慢，而玩家與其他環境保持正常速度。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。

---

## 一、核心概念：為何不用 Engine.time_scale

`Engine.time_scale` 影響所有物件（包括玩家），適合整體暫停或進入子彈時間的「所有東西都慢下來」效果。局部緩速需要不同做法：

- **動畫**：設定 `AnimationPlayer.speed_scale`、`AnimationTree` 的 speed_scale
- **NPC 移動**：將 `delta` 乘以縮放係數
- **RigidBody3D**：在 `_integrate_forces` 中縮放速度
- **粒子**：設定 `GPUParticles3D.speed_scale`

---

## 二、TimeSlowComponent 組件實作

建立一個可掛載到任何物件的通用組件：

```gdscript
# addons/cogito/Components/TimeSlowComponent.gd
extends Node
class_name TimeSlowComponent

## 1.0 = 正常速度，0.1 = 十分之一速度，0.0 = 完全停止
@export var local_time_scale : float = 1.0:
    set(value):
        local_time_scale = clampf(value, 0.0, 10.0)
        _apply_to_animations()

var _parent : Node


func _ready() -> void:
    _parent = get_parent()
    _apply_to_animations()


func _apply_to_animations() -> void:
    if not _parent:
        return
    
    # AnimationPlayer
    var anim_player = _parent.find_child("AnimationPlayer", true, false)
    if anim_player is AnimationPlayer:
        anim_player.speed_scale = local_time_scale
    
    # AnimationTree（NPC 使用）
    var anim_tree = _parent.find_child("AnimationTree", true, false)
    if anim_tree is AnimationTree:
        anim_tree.speed_scale = local_time_scale
    
    # GPUParticles3D
    for particles in _parent.find_children("*", "GPUParticles3D", true, false):
        particles.speed_scale = local_time_scale
    for particles in _parent.find_children("*", "CPUParticles3D", true, false):
        particles.speed_scale = local_time_scale
```

---

## 三、NPC 移動的時間縮放

NPC 的移動邏輯分散在各狀態腳本的 `_physics_process` 中，每個狀態都用 `delta` 計算速度。只需讓 `Host` 提供一個 `effective_delta` 即可。

### 3.1 在 cogito_npc.gd 加入縮放變數

```gdscript
# cogito_npc.gd 加入
@export var local_time_scale : float = 1.0
```

### 3.2 修改狀態腳本使用 effective_delta

以 `npc_state_move_to_random_pos.gd` 的 `_move_host_to_next_position()` 為例（`npc_state_move_to_random_pos.gd:65-83`）：

```gdscript
# 修改前（直接使用 delta）
func move_host_to_next_position(_delta: float) -> void:
    if not Host.is_on_floor():
        Host.velocity += Host.get_gravity() * _delta
    # ...

# 修改後（使用 effective_delta）
func move_host_to_next_position(_delta: float) -> void:
    var effective_delta = _delta * Host.get("local_time_scale", 1.0)
    
    if not Host.is_on_floor():
        Host.velocity += Host.get_gravity() * effective_delta
    
    var direction = Host.global_position.direction_to(next_position)
    if direction:
        Host.face_direction(face_direction)
        # 速度直接乘縮放，不用 delta（速度本身就是每秒值）
        Host.velocity.x = direction.x * Host.move_speed * Host.get("local_time_scale", 1.0)
        Host.velocity.z = direction.z * Host.move_speed * Host.get("local_time_scale", 1.0)
    Host.move_and_slide()
```

**使用 `get("local_time_scale", 1.0)` 的原因**：若某個狀態對應的 NPC 沒有定義 `local_time_scale`，`get()` 返回預設值 1.0，不會報錯。

### 3.3 chase 狀態的縮放

`npc_state_chase.gd` 中的移動邏輯同理，在 `velocity` 計算時乘上縮放：
```gdscript
# npc_state_chase.gd 約第 117 行
var next_position = Host.navigation_agent_3d.get_next_path_position()
var scale = Host.get("local_time_scale", 1.0)
Host.velocity.x = direction.x * Host.move_speed * scale
Host.velocity.z = direction.z * Host.move_speed * scale
```

---

## 四、RigidBody3D 物件的時間縮放

物理物件由 PhysicsServer 驅動，需透過 `_integrate_forces` 手動介入：

```gdscript
# 掛在 RigidBody3D 的腳本中
@export var local_time_scale : float = 1.0

func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
    if is_equal_approx(local_time_scale, 1.0):
        return  # 正常速度，不干預
    
    # 縮放線速度與角速度（每幀壓縮，產生「濃稠液體」感）
    state.linear_velocity *= local_time_scale
    state.angular_velocity *= local_time_scale
    
    # 補償重力：引擎每幀加的重力是 g * delta（未縮放），
    # 我們已縮放 linear_velocity，但引擎會再加一次完整的重力，導致下落過快。
    # 解法：手動抵銷多餘重力
    var gravity_dir = PhysicsServer3D.area_get_param(
        get_world_3d().space,
        PhysicsServer3D.AREA_PARAM_GRAVITY_VECTOR
    ) as Vector3
    var gravity_mag = PhysicsServer3D.area_get_param(
        get_world_3d().space,
        PhysicsServer3D.AREA_PARAM_GRAVITY
    ) as float
    
    # 抵銷 (1 - scale) 比例的重力
    state.apply_force(-gravity_dir * gravity_mag * mass * (1.0 - local_time_scale))
```

---

## 五、觸發緩速的實際場景

### 場景一：「子彈時間」技能（玩家按鍵暫時凍結所有敵人）

```gdscript
# player_skill.gd（附加在 CogitoPlayer 或其子節點）
@export var bullet_time_duration : float = 3.0
@export var bullet_time_scale : float = 0.2
var _slow_targets : Array[Node] = []


func activate_bullet_time() -> void:
    var enemies = get_tree().get_nodes_in_group("Enemy")
    for enemy in enemies:
        if enemy.has_method("set") and "local_time_scale" in enemy:
            enemy.local_time_scale = bullet_time_scale
            _slow_targets.append(enemy)
    
    await get_tree().create_timer(bullet_time_duration).timeout
    deactivate_bullet_time()


func deactivate_bullet_time() -> void:
    for target in _slow_targets:
        if is_instance_valid(target):
            target.local_time_scale = 1.0
    _slow_targets.clear()
```

### 場景二：進入特定區域觸發緩速（Area3D 觸發器）

```gdscript
# slow_zone_trigger.gd（掛在 Area3D）
@export var time_scale_in_zone : float = 0.3
@export var affect_objects_only : bool = false  # false 也影響 NPC

func _on_body_entered(body: Node3D) -> void:
    if body.is_in_group("Enemy") or (not affect_objects_only):
        if "local_time_scale" in body:
            body.local_time_scale = time_scale_in_zone
        var slow_comp = body.find_child("TimeSlowComponent")
        if slow_comp:
            slow_comp.local_time_scale = time_scale_in_zone


func _on_body_exited(body: Node3D) -> void:
    if "local_time_scale" in body:
        body.local_time_scale = 1.0
    var slow_comp = body.find_child("TimeSlowComponent")
    if slow_comp:
        slow_comp.local_time_scale = 1.0
```

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 設定 NPC 的 `local_time_scale = 0.2` | NPC 動畫緩慢，移動速度降為 20% |
| 設定 RigidBody3D 的 `local_time_scale = 0.1` | 物件緩緩飄落，彈起也很慢 |
| 觸發子彈時間技能 | 所有 Enemy 群組成員變慢，3 秒後恢復 |
| 玩家進入 SlowZone | 玩家速度不受影響（只有 Enemy 縮放），NPC 在區域內慢動作 |
| 粒子特效（如火焰）在設定後 | `speed_scale` 降低，粒子動得更緩慢 |
