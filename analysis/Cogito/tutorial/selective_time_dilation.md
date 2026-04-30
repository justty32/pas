# 教學：如何實現局部時間緩速 (Selective Time Dilation)

本教學將引導您如何在 COGITO 中實現「局部時間緩速」效果。不同於全域的 `Engine.time_scale`，此方法能讓特定物件（如某個敵人或掉落物）變慢，而玩家與其他環境保持正常速度。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。
- 瞭解 Godot 的 `_physics_process(delta)` 運作原理。

---

## 1. 核心概念：局部時間縮放 (Local Time Scale)

要讓物件變慢，我們需要為其定義一個 `local_time_scale` 變數（1.0 為正常，0.1 為 10 倍緩速），並在處理物理移動與動畫時將其納入計算。

---

## 2. 實作：時間緩速組件 (TimeSlowComponent)

建立一個通用的組件，方便掛載到任何物件上。

### 實作步驟
1. 建立 `addons/cogito/Components/TimeSlowComponent.gd`：
   ```gdscript
   extends Node
   class_name TimeSlowComponent

   @export var local_time_scale : float = 1.0 :
       set(value):
           local_time_scale = value
           update_object_speed()

   var parent_node : Node

   func _ready():
       parent_node = get_parent()
       update_object_speed()

   func update_object_speed():
       # 處理動畫
       var anim_tree = parent_node.find_child("AnimationTree")
       if anim_tree:
           anim_tree.anim_player.speed_scale = local_time_scale
       
       var anim_player = parent_node.find_child("AnimationPlayer")
       if anim_player:
           anim_player.speed_scale = local_time_scale
   ```

---

## 3. NPC 的時間緩速整合

NPC 的移動邏輯分散在 `cogito_npc.gd` 與各個狀態腳本中。

### 原始碼導航
- `addons/cogito/CogitoNPC/cogito_npc.gd`
- `addons/cogito/CogitoNPC/npc_states/npc_state_chase.gd` (或其他移動狀態)

### 實作步驟
1. **修改 NPC 基類**：在 `cogito_npc.gd` 增加時間縮放變數。
   ```gdscript
   # cogito_npc.gd
   @export var local_time_scale : float = 1.0
   ```

2. **修正移動邏輯**：在狀態腳本（如 `npc_state_chase.gd`）中，將 `delta` 乘以 `local_time_scale`。
   ```gdscript
   # npc_state_chase.gd 的 _physics_process 中
   var effective_delta = _delta * Host.local_time_scale
   Host.velocity += Host.get_gravity() * effective_delta
   # 移動計算也需縮放
   Host.velocity.x = direction.x * Host.move_speed * Host.local_time_scale
   ```

---

## 4. 物理物件 (RigidBody3D) 的時間緩速

物理物件由引擎驅動，要讓其緩速需手動干預其速度。

### 實作步驟
在掛載到 `RigidBody3D` 的腳本中覆寫 `_integrate_forces`：
```gdscript
func _integrate_forces(state):
    if local_time_scale < 1.0:
        # 每一幀都縮放速度，使其看起來像在濃稠液體中移動
        state.linear_velocity *= local_time_scale
        state.angular_velocity *= local_time_scale
        # 同時需補償重力，否則物體會快速掉落
        state.apply_force(-PhysicsServer3D.area_get_param(get_world_3d().space, PhysicsServer3D.AREA_PARAM_GRAVITY_VECTOR) * mass * (1.0 - local_time_scale))
```

---

## 5. 特效與粒子的時間緩速

對於特效（如火花或煙霧）：
- 修改 `GPUParticles3D` 或 `CPUParticles3D` 的 `speed_scale` 屬性。
- 將其與物件的 `local_time_scale` 連動。

---

## 驗證方式

1. **NPC 測試**：
   - 在場景中放置兩個相同的 NPC，將其中一個的 `local_time_scale` 設為 0.2。
   - 觀察其行走與攻擊動畫是否明顯變慢。
2. **物理物件測試**：
   - 將一個方塊設為 `local_time_scale = 0.1` 並從高處丟下。
   - 確認它是否像「慢動作」一樣緩緩飄落並緩慢彈起。
3. **動態切換測試**：
   - 建立一個觸發區域 (Area3D)，當玩家進入時，透過程式碼將區域內物件的 `local_time_scale` 設為 0.1，離開時恢復 1.0。
