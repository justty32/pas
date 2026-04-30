# Cogito — Level 5D CarryableComponent 物理搬運機制分析

## 一、概覽

**位置**：`Components/Interactions/CarryableComponent.gd`，繼承 `InteractionComponent`

CarryableComponent 讓 RigidBody3D 物件可被玩家「抓取」並在空中浮動攜帶，支援手動旋轉與丟擲。它整合於 Cogito 的互動組件體系，附加到任何 RigidBody3D 即可使用。

---

## 二、Inspector 欄位

| 欄位 | 預設 | 說明 |
|---|---|---|
| `is_carryable_while_wielding` | false | 是否可在持武器時搬運 |
| `carry_distance_offset` | 0 | 搬運距離相對 interaction_raycast 末端的偏移量 |
| `lock_rotation_when_carried` | true | 搬運時鎖定物件旋轉（防翻滾） |
| `carrying_velocity_multiplier` | 10 | 物件趨近速度（越高越硬，越低越飄） |
| `drop_distance` | 1.5 | 超過此距離自動丟下（防穿牆） |
| `enable_manual_rotating` | true | 允許按住次要動作手動旋轉 |
| `rotation_speed` | 2.0 | 手動旋轉速度（deg/frame） |

---

## 三、核心機制

### 抓取（hold）

```
hold():
  if parent_object is RigidBody3D:
    if lock_rotation_when_carried:
      parent_object.set_lock_rotation_enabled(true)  // 防旋轉
    parent_object.freeze = false   // 確保物理啟用
  
  player_interaction_component.start_carrying(self)
  interaction_raycast.add_exception(parent_object)   // 射線不再碰到自己
  
  is_being_carried = true
  carry_state_changed.emit(true)
  Audio.play(pick_up_sound)
```

**`interaction_raycast.add_exception`**：讓玩家抓著物件時不會偵測到自己，防止互動系統在「自己」上觸發。

### 放下（leave）

```
leave():
  if is_being_rotated:
    player.is_movement_paused = false   // 恢復移動
  
  if lock_rotation_when_carried:
    parent_object.set_lock_rotation_enabled(false)  // 解鎖旋轉
  
  player_interaction_component.stop_carrying()
  interaction_raycast.remove_exception(parent_object)
  
  is_being_carried = false
  carry_state_changed.emit(false)
```

### 丟擲（throw）

```
throw(power):
  leave()  // 先放下（解除所有抓取狀態）
  Audio.play(drop_sound)
  
  var impulse = player_interaction_component.Get_Look_Direction() * power
  parent_object.apply_central_impulse(impulse)  // 沿玩家視線方向推力
  thrown.emit(impulse)
```

---

## 四、_physics_process 浮動搬運

```
_physics_process(_delta):
  if !is_being_carried: return
  
  carry_position = PIC.get_carryable_destination_point(carry_distance_offset)
  
  // 浮動物理：每幀設定速度趨近目標點
  parent_object.set_linear_velocity(
    (carry_position - parent_object.global_position) * carrying_velocity_multiplier
  )
  
  // 手動旋轉（按住次要動作）
  if enable_manual_rotating and Input.is_action_pressed("action_secondary"):
    player.is_movement_paused = true   // 暫停玩家移動
    is_being_rotated = true
    rotate_object(_delta)
  
  // 鬆開次要動作，恢復移動
  if is_being_rotated and Input.is_action_just_released("action_secondary"):
    player.is_movement_paused = false
  
  // 超距自動丟下
  if (carry_position - parent_object.global_position).length() >= drop_distance:
    leave()
```

**浮動物理原理**：不是直接設置位置，而是設置線速度（`v = delta_pos * multiplier`），物件通過物理引擎移動，保留與場景其他物件的碰撞互動。`carrying_velocity_multiplier` 越高越「硬」，越低越「飄」。

### 手動旋轉（rotate_object）

```
rotate_object(_delta):
  input_dir = Input.get_vector("left", "right", "forward", "back")
  
  if input_dir.length() > 0:
    // 以相機為基準計算旋轉軸（去除垂直分量）
    rotation_basis = camera.global_basis.rotated(camera.global_basis.x, -camera.global_rotation.x)
    rotation_vector = rotation_basis * Vector3(input_dir.y, input_dir.x, 0).normalized()
    
    parent_object.global_rotate(rotation_vector, deg_to_rad(rotation_speed))
```

旋轉軸以相機水平基底計算，讓 WASD 旋轉方向與玩家視角一致。按住次要動作期間 `is_movement_paused = true`，玩家無法移動。

---

## 五、自動丟下的觸發條件

| 條件 | 實作位置 | 說明 |
|---|---|---|
| 超過 `drop_distance` | `_physics_process:82` | 物件漂移太遠（如穿牆後） |
| 玩家碰到物件 | `_on_body_entered(body)` | body 在 Player 群組即丟下 |
| 物件離開場景樹 | `_exit_tree()` | 避免殭屍攜帶狀態 |

```
_on_body_entered(body):
  if body.is_in_group("Player") and is_being_carried:
    leave()   // 防止玩家被物件頂飛

_exit_tree():
  if is_being_carried: leave()   // 清理狀態
```

---

## 六、與 PlayerInteractionComponent 的整合

CarryableComponent 呼叫 PIC 的以下方法：

```
PIC.start_carrying(carryable_component):
  is_carrying = true
  equipped_carryable = carryable_component

PIC.stop_carrying():
  is_carrying = false
  equipped_carryable = null

PIC.get_carryable_destination_point(offset):
  // 回傳 interaction_raycast 末端 + offset 的世界座標
  // 即玩家「面前」固定距離的位置

PIC.Get_Look_Direction():
  // 玩家相機的正前方向量（用於丟擲方向）
```

**`is_carrying` 旗標的影響**：
- `CogitoQuickslots._cycle_through_quickslotted_wieldables()` 會檢查 `is_carrying`，搬運中不允許切換武器
- 其他 interaction 邏輯可查詢此旗標防止衝突操作

---

## 七、信號清單

| 信號 | 觸發時機 | 用途 |
|---|---|---|
| `carry_state_changed(is_being_carried)` | 抓起/放下 | 外部系統監聽搬運狀態變化 |
| `thrown(impulse)` | 丟擲時 | 記錄或觸發特效 |
| `was_interacted_with` | 繼承自 InteractionComponent | 觸發互動提示消失 |

---

## 八、架構定位

```
CarryableComponent 繼承鏈：
  InteractionComponent
    └─ CarryableComponent

// interact() 入口（玩家按下互動鍵）
interact(PIC):
  if is_disabled: return
  check_attribute(PIC)  // 力量等屬性檢查（繼承自 InteractionComponent）
  carry(PIC)
    → toggle hold/leave
```

CarryableComponent 是標準互動組件，可與 AttributeCheck（力量需求搬運重物）結合，且尊重 `is_disabled` 旗標（可在劇情中鎖定某些物件）。

---

## 九、設計要點

- **純物理驅動**：靠設定 `linear_velocity` 而非直接 `global_position = target`，保留物理碰撞
- **`lock_rotation`**：搬運時鎖定旋轉防止物件翻滾，放下後恢復
- **`add_exception` / `remove_exception`**：管理 raycast 例外清單，防止物件遮擋互動
- **移動暫停設計**：旋轉模式下凍結玩家位移（但不凍結視角），讓旋轉操作更精確
