# Cogito — Level 3 NPC 狀態機詳細行為分析

## 一、CogitoNPC 主體（`cogito_npc.gd`）

**位置**：`addons/cogito/CogitoNPC/cogito_npc.gd`，繼承 `CharacterBody3D`。

### 節點結構
```
CogitoNPC (CharacterBody3D)
├── NavigationAgent3D        ← 路徑規劃
├── AnimationTree            ← 動畫混合樹（Movement blend + UpperBodyState）
├── LookAtArea (Area3D)      ← 定期偵測玩家是否在視野範圍內
├── Rig/Skeleton3D/LookAtModifier3D  ← 頭部朝向玩家
├── VelocityDebugShape       ← 除錯用速度視覺化
├── FootstepPlayer           ← 動態腳步音效
└── NPC_State_Machine        ← 狀態機節點（含各狀態子節點）
```

### 關鍵共用方法

**`face_direction(target_pos)`**：
```
face_at_target = global_pos.direction_to(target_pos)
face_at_target_xz = 去除 Y 分量
target_basis = Basis.looking_at(face_at_target_xz)
basis = basis.slerp(target_basis, rotation_speed)  // 平滑轉向
```

**`update_animations(delta)`**：
```
relative_velocity = global_basis.inverse() * (velocity_xz / sprint_speed)  // 轉換為本地座標
rel_velocity_xz = Vector2(x, -z)
animation_tree.set("parameters/Movement/blend_position", rel_velocity_xz)  // 八方向混合
```

**擊退系統（Knockback）**：
```
apply_knockback(direction):
  knockback_force = direction.normalized() * knockback_strength
  knockback_timer = knockback_duration

_physics_process():
  if knockback_timer > 0:
    velocity = knockback_force
    knockback_force = lerp(knockback_force, ZERO, delta*5)  // 衰減
    move_and_slide(); return   // 擊退期間跳過狀態邏輯
```

**腳步音效（`npc_footsteps`）**：同玩家，使用 `sin(wiggle_index)` 峰值觸發，根據速度切換 walk/sprint 音量。

### 存讀檔
```
save():
  saved_enemy_state = npc_state_machine.current  // 儲存當前狀態名稱
  儲存: pos, rot, patrol_path_nodepath, saved_enemy_state

set_state():
  load_patrol_points()       // 從 nodepath 重建 patrol_path 參照
  npc_state_machine.goto(saved_enemy_state)  // 恢復到儲存時的狀態
```

---

## 二、NPC_State_Machine（`npc_state_machine.gd`）

**位置**：`addons/cogito/CogitoNPC/npc_states/npc_state_machine.gd`

### 設計原理

狀態機將所有狀態節點存入 `states: Dictionary`，但**同一時刻場景樹中只掛載一個當前狀態**。非當前狀態從場景樹移除（但不 free），因此不參與 `_physics_process`，達到隔離效果。

```
setup():
  for child in get_children():
    states[child.name] = child
    child.States = self      // 注入 States 參照
    child.Host = get_host()  // 注入 Host（NPC）參照
    if child.name != current: remove_child(child)  // 非起始狀態移出樹
  restart()
  if start_state: goto.call_deferred(start_state)
```

### goto() 流程
```
goto(state, args):
  await caller("_state_exit")      // 等待舊狀態退出（支援 async）
  remove_child(states[current])    // 舊狀態退出樹
  current = state
  emit state_changed(state)
  add_child(states[state])         // 新狀態進入樹（開始接受 _physics_process）
  await caller("_state_enter", args)
```

### Previous State 機制
```
save_state_as_previous(state, args):
  previous_state = state

load_previous_state():
  goto(previous_state ?? "idle")
```
各狀態在 `_state_exit()` 中呼叫 `States.save_state_as_previous(self.name)` 保存自身，讓後來的狀態（如 attack、switch_stance）能夠回退。

---

## 三、各狀態詳細行為

### 3.1 idle 狀態

**位置**：`npc_states/npc_state_idle.gd`

```
_state_enter():
  await Timer(3 秒)
  States.goto("patrol_on_path")
```
完全被動等待 3 秒後自動跳到 patrol。無移動邏輯。

---

### 3.2 patrol_on_path 狀態（沿路徑巡邏）

**位置**：`npc_states/npc_state_patrol_on_path.gd`

#### TravelStatus 狀態機（內嵌）
```
RUNNING  → 移動中
WAITING  → 抵達路點，等待 patrol_point_wait_time 秒
SUCCESS  → 全路徑完成（目前不處理）
FAILURE  → 路點不可達，跳下一個
```

#### 路徑索引循環
```
iterate_patrol_point_index():
  if index == path.size()-1: index = 0  // 循環
  else: index += 1
```

#### 移動邏輯（`move_host_to_next_position`）
```
next_pos = nav_agent.get_next_path_position()  // NavigationAgent3D 規劃路徑
if not on_floor: velocity += gravity * delta   // 重力
direction = global_pos.direction_to(next_pos)
face_direction(velocity_lookahead)
velocity.xz = direction.xz * move_speed
move_and_slide()
```

#### 路點等待
```
wait_at_patrol_point():
  patrol_wait_timer.start()           // one_shot timer
  current_travel_status = WAITING
  timeout → resume_patrolling():
    iterate_index → 更新目標 → RUNNING
```

#### 錯誤處理
若路點不可達（`!is_target_reachable()`），直接跳下一個路點。

---

### 3.3 move_to_random_pos 狀態（隨機漫遊）

**位置**：`npc_states/npc_state_move_to_random_pos.gd`

```
_state_enter():
  target = pick_destination():
    dir = Vector3(rand(-1,1), 0, rand(-1,1)).normalized()
    distance = randi_range(1, max_distance_from_host)
    return dir * distance   // 相對座標，非絕對！（TODO：此處可能有 bug）
  nav_agent.target_position = target
  status = RUNNING

SUCCESS → goto("idle")   // 抵達後回到 idle
FAILURE → pick_destination() 重試
```

---

### 3.4 chase 狀態（追擊）

**位置**：`npc_states/npc_state_chase.gd`

#### ChaseStatus 內嵌狀態機
```
CHASING → 追擊中（持續更新 nav_agent.target = chase_target.global_pos）
WAITING → 目標暫時不可達（啟動 giveup_chase_time 倒數計時）
CAUGHT  → 進入距離 → goto(action_when_caught)  // 預設 "attack"
LOST    → 超時或手動呼叫 stop_chasing() → load_previous_state()
```

#### 速度切換
```
_state_enter():
  Host.move_speed = Host.sprint_speed  // 追擊時切換為衝刺速度
stop_chasing():
  Host.move_speed = Host.walk_speed    // 放棄追擊時恢復步行速度
```

#### 目標不可達處理
```
_running():
  if !nav_agent.is_target_reachable():
    start_waiting():
      chase_wait_timer.start()   // giveup_chase_time 倒數
      status = WAITING
  
WAITING 中：
  持續更新 target_position
  if is_target_reachable():
    chase_wait_timer.stop()
    status = CHASING  // 目標重新可達 → 恢復追擊
  (若計時器到期) → stop_chasing() → status = LOST
```

#### 等待時朝向目標
```
WAITING:
  if face_target_while_waiting:
    Host.face_direction(chase_target.global_position)
```

---

### 3.5 attack 狀態（攻擊）

**位置**：`npc_states/npc_state_attack.gd`

#### 流程
```
_state_enter():
  target = Host.attention_target
  count_down = attack_duration
  attempt_attack()  // 立即執行第一次攻擊

_physics_process():
  if count_down <= 0:
    attempt_attack()
    goto(state_after_attack)  // Inspector 設定後續狀態（通常是 "chase"）
  else:
    count_down -= delta
  同時停止 NPC 移動（velocity lerp to zero）
```

#### attempt_attack()
```
觸發動畫（AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE）
if distance_to(target) <= 1.5:
  attack(target)   // 僅在近距離實際造成傷害，但動畫始終播放
```

#### attack() 傷害邏輯
```
await Timer(0.15)  // 等待動畫對齊（硬編碼延遲）

if target is CogitoPlayer:
  target.apply_external_force(dir * attack_stagger)  // 擊飛玩家
  target.decrease_attribute("health", attack_damage) // 直接減血

if target.has_signal("damage_received"):
  target.damage_received.emit(attack_damage, damage_direction)
```

---

### 3.6 switch_stance 狀態（切換姿態）

**位置**：`npc_states/npc_state_switch_stance.gd`

```
_state_enter():
  upper_body_sm = animation_tree.get("parameters/UpperBodyState/playback")
  if !stance_active:
    upper_body_sm.travel("RaisedFists")  // 進入戰鬥姿態
    stance_active = true
  else:
    upper_body_sm.travel("Neutral")      // 回到中立姿態
    stance_active = false
  
  States.load_previous_state()  // 立即回到前一個狀態（瞬時狀態）
```

`switch_stance` 是「一次性瞬時狀態」，進入後執行動畫切換，立刻退回前一狀態，類似「中間件」。

---

## 四、NPC 狀態轉換圖

```
         ┌─────────────────────────────────────┐
         ▼                                     │
      [idle]                            [load_previous_state]
    等待 3 秒後                                 ▲
         │                                     │
         ▼                              [switch_stance]
  [patrol_on_path]                    （瞬時，立即返回）
  沿路點循環移動
         │                                     
  （attention_target 設置時，外部呼叫 goto("chase")）
         │
         ▼
      [chase]
   CHASING → 追擊
   WAITING → 目標不可達
   CAUGHT  ──────────────────────────────────►[attack]
   LOST    ── load_previous_state() ──────►[patrol/idle]   攻擊完成
                                                      │  goto(state_after_attack)
                                                      ▼
                                                   [chase]
```

---

## 五、動畫系統整合

AnimationTree 採用雙軌道結構：

| 軌道 | 參數路徑 | 控制內容 |
|---|---|---|
| Movement | `parameters/Movement/blend_position` | 八方向移動混合（Vector2） |
| UpperBodyState | `parameters/UpperBodyState/playback` | StateMachine：Neutral / RaisedFists / hit |
| 攻擊 OneShot | `parameters/UpperBodyState/RaisedFists/attack/request` | 觸發攻擊動畫（ONE_SHOT_REQUEST_FIRE） |

**頭部追蹤**：`LookAtModifier3D.target_node` 設為玩家 Head 的路徑（`_on_check_player_timer_timeout` 定期更新），Area3D 離開時清空。

---

## 六、與玩家的感知連接

CogitoNPC 本身沒有內建視野感應邏輯；`attention_target` 需由外部設置：

```gd
// cogito_npc.gd
func _on_security_camera_object_detected(object: Node3D) -> void:
    attention_target = object
```

`CogitoSecurityCamera` 偵測到玩家時，透過信號將玩家設為 `attention_target`，再由場景設計者在 Inspector 或腳本中呼叫 `States.goto("chase")` 觸發追擊。感知邏輯完全外掛式，不耦合在 NPC 主體內。
