# Cogito — Level 5E 玩家完整移動系統分析

## 一、節點層級結構

```
CogitoPlayer (CharacterBody3D)
  ├─ Body (Node3D)                    ← 水平旋轉（Y 軸，滑鼠左右）
  │   └─ Neck (Node3D)               ← 自由視角旋轉（Y 軸）
  │       └─ Head (Node3D)           ← 蹲伏/頭部偏移
  │           └─ Eyes (Node3D)       ← 頭部晃動 + 視角傾斜
  │               ├─ Camera (Camera3D)
  │               └─ AnimationPlayer ← jump/landing/roll 動畫
  ├─ StandingCollisionShape
  ├─ CrouchingCollisionShape
  ├─ CrouchRayCast                   ← 偵測頭頂是否有障礙（不可站起）
  ├─ SlidingTimer
  ├─ JumpCooldownTimer               ← 防連跳
  ├─ FootstepPlayer (FootstepSurfaceDetector)
  └─ NavigationAgent3D               ← 離座位後尋找安全落點用
```

---

## 二、移動狀態變數

| 變數 | 說明 |
|---|---|
| `is_walking` / `is_sprinting` / `is_crouching` | 當前移動狀態（互斥） |
| `is_free_looking` | 按住 free_look 時 neck 旋轉不帶動 body |
| `is_movement_paused` | 凍結輸入（旋轉物件、UI 開啟、坐下等） |
| `is_jumping` / `is_in_air` | 起跳旗標 / 空中狀態 |
| `on_ladder` | 梯子模式 |
| `is_sitting` | 坐下狀態，走獨立的 `_process_on_sittable()` |
| `current_speed` | 實際速度（lerp 到目標速度） |
| `main_velocity` | 主要速度向量（XZ 移動 + Y 重力分量） |
| `gravity_vec` | 當前重力向量（落地即清零） |
| `bunny_hop_speed` | Bunny hop 累積速度 |

---

## 三、_physics_process 主流程

```
_physics_process(delta):
  1. if is_sitting → _process_on_sittable(delta); return
  2. if on_ladder  → _process_on_ladder(delta); return
  
  3. input_dir = Input.get_vector("left","right","forward","back")
     if is_movement_paused: input_dir = Vector2.ZERO
  
  4. 手把類比搖桿鏡頭（joystick_h/v_event）
  
  5. CROUCH 處理
  6. SLIDING 判斷
  7. 速度 lerp（walk/sprint/crouch）
  8. 自由視角（free_look）
  9. 重力處理
  10. 頭部晃動（wiggle）
  11. 跳躍
  12. 方向 lerp
  13. 樓梯偵測（step_check）
  14. velocity = main_velocity; move_and_slide()
  15. RigidBody3D 推力
  16. 腳步聲
```

---

## 四、蹲伏與滑行

### 蹲伏（Crouch）

```
// Toggle 模式或持續按住模式
if TOGGLE_CROUCH and is_action_just_pressed("crouch"):
  try_crouch = !try_crouch
elif !TOGGLE_CROUCH:
  try_crouch = is_action_pressed("crouch")

// 蹲伏條件：try_crouch 或頭頂有碰撞（CrouchRayCast.is_colliding）
if try_crouch or crouch_raycast.is_colliding():
  head.position.y = lerp(head.position.y, CROUCHING_DEPTH, delta * LERP_SPEED)
  current_speed = lerp(current_speed, CROUCHING_SPEED, delta * LERP_SPEED)
  standing_collision_shape.disabled = true
  crouching_collision_shape.disabled = false
  is_crouching = true
else:
  // 站起時：頭頂無障礙才切換碰撞體
  if head.position.y < CROUCHING_DEPTH/4:  // 仍在過渡中
    crouching_collision_shape.disabled = false
    standing_collision_shape.disabled = true
  else:
    standing_collision_shape.disabled = false
    crouching_collision_shape.disabled = true
```

### 滑行（Slide）

```
if is_sprinting and input_dir != Vector2.ZERO and is_on_floor() and try_crouch:
  sliding_timer.start()
  slide_vector = input_dir   // 滑行方向固定在起始輸入

// 滑行中方向鎖定，速度隨計時器剩餘時間衰減
if !sliding_timer.is_stopped():
  direction = body.basis * Vector3(slide_vector.x, 0, slide_vector.y)
  current_speed = (sliding_timer.time_left / wait_time + 0.5) * SLIDING_SPEED

// 滑行結束，停止按 sprint，速度正常恢復
```

**滑行跳躍（slide jump）**：
```
if is_jumping and !sliding_timer.is_stopped():
  main_velocity.y = JUMP_VELOCITY * SLIDE_JUMP_MOD   // 乘以 1.5 的跳躍修正
  jumped_from_slide = true
  sliding_timer.stop()
```

---

## 五、跳躍系統

```
if is_action_pressed("jump") and !is_movement_paused and is_on_floor() and jump_timer.is_stopped():
  jump_timer.start()   // 防連跳（JumpCooldownTimer）
  is_jumping = true
  
  var jump_vel = is_crouching ? CROUCH_JUMP_VELOCITY : JUMP_VELOCITY
  
  // 耐力需求（若有 stamina_attribute）
  var doesnt_need_stamina = not stamina_attribute or stamina_attribute.value_current >= jump_exhaustion
  var crouch_jump = not is_crouching or CAN_CROUCH_JUMP
  
  if doesnt_need_stamina and crouch_jump:
    if stamina_attribute: decrease_attribute("stamina", jump_exhaustion)
    animationPlayer.play("jump")
    Audio.play_sound(jump_sound)
    main_velocity.y = jump_vel
    
    // 平台速度繼承（可選）
    if platform_on_leave != PLATFORM_ON_LEAVE_DO_NOTHING:
      main_velocity += get_platform_velocity()
    
    // Bunny hop 加速
    if is_sprinting and CAN_BUNNYHOP:
      bunny_hop_speed += BUNNY_HOP_ACCELERATION
```

**Bunny hop**：每次在奔跑中跳躍，`bunny_hop_speed` 累積增加（`+= BUNNY_HOP_ACCELERATION`），落地後重置（見 `is_on_floor()` 分支）。

---

## 六、空中控制

```
if is_on_floor():
  direction = lerp(direction, body.basis * input_direction, delta * LERP_SPEED)
elif input_dir != Vector2.ZERO:
  direction = lerp(direction, body.basis * input_direction, delta * AIR_LERP_SPEED)
  // AIR_LERP_SPEED 通常低於 LERP_SPEED，空中轉向較慢
```

空中不完全失去控制，但 `AIR_LERP_SPEED`（預設 6）低於地面 `LERP_SPEED`（預設 10），轉向反應較遲鈍。

---

## 七、樓梯爬升（step_check）

**位置**：`cogito_player.gd:1148`，使用 `PhysicsServer3D.body_test_motion()` 三段測試

```
step_check(delta, is_jumping_, step_result):
  for i in STEP_CHECK_COUNT:  // 預設 2 次，分割步高
    step_height = STEP_HEIGHT_DEFAULT - i * (STEP_HEIGHT_DEFAULT / COUNT)
    
    // 測試 1：向上（step_height）—— 空間夠嗎？
    is_collided = body_test_motion(transform, step_height)
    if collided and collision_normal.y < 0: continue   // 頭頂有東西，跳過這個高度
    
    transform.origin += step_height   // 假設已在高一步的位置
    
    // 測試 2：向前（main_velocity * delta）—— 前方通暢嗎？
    is_collided = body_test_motion(transform, main_velocity * delta)
    if not is_collided:
      transform.origin += main_velocity * delta
      
      // 測試 3：向下（-step_height）—— 確認有地可站？
      is_collided = body_test_motion(transform, -step_height)
      if is_collided and collision_normal.angle_to(UP) <= STEP_MAX_SLOPE_DEGREE:
        is_step = true
        step_result.diff_position.y = -remainder.y  // 需要移動的高度差
        break
    else:
      // 牆壁情況：側滑後再測試
      wall_normal = test_result.collision_normal
      transform.origin += wall_normal * WALL_MARGIN  // 微小偏移防卡住
      motion = main_velocity.slide(wall_normal)
      // 再次測試前進 + 下落
```

結果：`step_result.diff_position.y` 是本幀需要向上偏移的高度，直接修改 `global_transform.origin`，並用負值修正 `head.position` 讓鏡頭平滑。

---

## 八、自由視角（Free Look）

```
if is_action_pressed("free_look") or !sliding_timer.is_stopped():
  is_free_looking = true
  
  if sliding_timer.is_stopped():   // 純自由視角
    eyes.rotation.z = -deg_to_rad(neck.rotation.y * FREE_LOOK_TILT_AMOUNT)  // 頭部傾斜
  else:   // 滑行中的自動傾斜
    eyes.rotation.z = lerp(eyes.rotation.z, deg_to_rad(4.0), delta * LERP_SPEED)
else:
  is_free_looking = false
  body.rotation.y += neck.rotation.y  // neck 的旋轉「歸還」給 body
  neck.rotation.y = 0
  eyes.rotation.z = lerp(eyes.rotation.z, 0.0, delta * LERP_SPEED)
```

自由視角期間：neck 旋轉，body 不動（玩家可扭頭不轉身）。放開後：neck 角度加入 body，neck 歸零。

---

## 九、梯子移動（_process_on_ladder）

```
_process_on_ladder(delta):
  input_dir = Input.get_vector("left","right","forward","back")
  ladder_speed = LADDER_SPEED
  
  if CAN_SPRINT_ON_LADDER and is_action_pressed("sprint"):
    ladder_speed = LADDER_SPRINT_SPEED   // 快速爬梯
  
  look_vector = camera.get_camera_transform().basis
  looking_down = look_vector.z.dot(Vector3.UP) > 0.5
  
  y_dir = 1 if looking_down else -1   // 看下方時前進 = 下降
  direction = (body.basis * Vector3(input_dir.x, input_dir.y * y_dir, 0)).normalized()
  main_velocity = direction * ladder_speed
  
  if is_action_pressed("jump"):
    main_velocity += look_vector * JUMP_VELOCITY * LADDER_JUMP_SCALE  // 跳離梯子
  
  velocity = main_velocity
  move_and_slide()
  
  if is_on_floor() and not ladder_on_cooldown:
    on_ladder = false   // 落地自動退出
```

**enter_ladder 偵測**（由 `ladder_area.gd` 呼叫）：
```
enter_ladder(ladder, ladderDir):
  looking_away = camera.basis.z.dot(ladderDir) < 0.33
  looking_down = camera.basis.z.dot(Vector3.UP) > 0.5
  if looking_down or not looking_away: return   // 朝梯子看才能抓住
  on_ladder = true
  ladder_on_cooldown = true  // 防止落地後立即再抓
```

---

## 十、坐下/起立系統

### 坐下（_sit_down）

```
_sit_down():
  standing/crouching_collision_shape.disabled = true
  set_physics_process(false)   // 暫停物理（靜態坐下）
  
  // Tween 移動到 sit_position_node.global_transform
  if sittable.physics_sittable:
    set_physics_process(true)  // 物理坐下（如移動的載具）
    Tween: global_transform → sit_position.global_transform
  else:
    Tween: global_transform → sit_position.global_transform
  
  _sit_down_finished():
    // Tween neck 朝向 look_marker
```

### 起立（_stand_up）

四種離開行為（`PlacementOnLeave`）：
- `ORIGINAL`：Tween 回到坐下前的位置
- `AUTO`：NavigationAgent3D 搜尋最近空位（隨機方向 + 遞增距離，最多 10 次）
- `TRANSFORM`：Tween 到指定的 leave_node
- `DISPLACEMENT`：以坐位與原始位置的偏移量計算新位置（跟隨移動座椅）

```
_move_to_nearby_location(sittable):
  while attempts < 10:
    candidate = seat_pos + random_direction * exit_distance
    navigation_agent.target_position = candidate
    if navigation_agent.is_navigation_finished():
      Tween: position → nav_target; break
    exit_distance += 0.5
    attempts += 1
  if failed: _move_to_leave_node(sittable)  // fallback
```

### 坐下期間的更新（_process_on_sittable）

```
_process_on_sittable(delta):
  if !currently_tweening:
    self.global_transform = sittable.sit_position_node.global_transform  // 持續跟隨（載具）
  
  if sittable.eject_on_fall:
    angle_to_up = chair_up.angle_to(global_up_vector)
    if angle_to_up > sittable.eject_angle:   // 椅子翻倒
      sittable.interact(PIC)   // 強制彈出
```

---

## 十一、落地特效與墜落傷害

```
// 落地時（was_in_air → is_on_floor）
if last_velocity.y < landing_threshold:
  velocity_ratio = clamp((last_velocity.y - min_vel) / (max_vel - min_vel), 0, 1)
  LandingVolume = lerp(min_volume, max_volume, velocity_ratio)
  LandingPitch = lerp(max_pitch, min_pitch, velocity_ratio)
  footstep_player._play_interaction("landing")

// 高速墜落動畫
if last_velocity.y <= -7.5:
  animationPlayer.play("roll")    // 翻滾動畫（可關閉 disable_roll_anim）
elif last_velocity.y <= -5.0:
  animationPlayer.play("landing")

// 墜落傷害
if fall_damage > 0 and last_velocity.y <= fall_damage_threshold:
  decrease_attribute("health", fall_damage)
```

---

## 十二、外力施加（apply_external_force）

**位置**：`cogito_player.gd:1280`

```
apply_external_force(force_vector: Vector3):
  if force_vector.length() > 0:
    velocity += force_vector
    move_and_slide()
```

**使用場景**：
- `explosion.gd`：爆炸衝擊波
- 彈射器/風扇等自定義物件
- NPC 擊退

直接修改 `velocity` 後立刻 `move_and_slide()`，效果即幀生效，不需等下一幀的 `_physics_process`。

---

## 十三、重力覆蓋（override_gravity）

```
override_gravity(external_gravity_force, external_gravity_vector):
  gravity = external_gravity_force
  gravity_vector = external_gravity_vector
  gravity_vec = gravity_vector * gravity
  velocity += gravity_vec
  move_and_slide()
```

用於反重力區域、零重力場景或特殊物理事件，直接覆蓋 ProjectSettings 的重力設定。

---

## 十四、RigidBody3D 推力

```
for col_idx in get_slide_collision_count():
  var col = get_slide_collision(col_idx)
  if col.get_collider() is RigidBody3D:
    col.get_collider().apply_central_impulse(-col.get_normal() * PLAYER_PUSH_FORCE)
```

玩家走入 RigidBody3D 時，以 `PLAYER_PUSH_FORCE`（預設 1.3）向外施力，讓小物件可被推動。

---

## 十五、移動系統整體流程圖

```
_physics_process(delta)
  │
  ├─ is_sitting → _process_on_sittable() [return]
  ├─ on_ladder  → _process_on_ladder()   [return]
  │
  ├─ input_dir（WASD）
  ├─ Crouch（toggle/hold + raycast 防站起）
  │    └─ Slide（sprint + crouch + moving → sliding_timer）
  │
  ├─ Speed lerp：CROUCH → WALK → SPRINT（bunny_hop 累積）
  ├─ Headbob wiggle（wiggle_index 三角函數）
  ├─ Free Look（neck vs body 旋轉分離）
  │
  ├─ 重力（落地清零，空中累積）
  ├─ 跳躍（jump_timer 防連跳 + stamina 消耗 + slide_jump_mod）
  ├─ 方向 lerp（地面 LERP_SPEED，空中 AIR_LERP_SPEED）
  │
  ├─ step_check（三次 body_test_motion：上→前→下）
  │    └─ 成功 → 偏移 origin + 平滑 head offset
  │
  ├─ velocity = main_velocity; move_and_slide()
  ├─ RigidBody 推力
  └─ 腳步聲（wiggle_vector.y 觸發節奏）
```
