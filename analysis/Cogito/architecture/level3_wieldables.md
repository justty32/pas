# Cogito — Level 3 Wieldable 具體實作與玩家動作分析

## 一、CogitoWieldable 基類回顧

**位置**：`addons/cogito/Scripts/cogito_wieldable.gd`

所有 Wieldable 繼承此 `Node3D` 基類，實作以下介面：

| 方法 | 呼叫時機 |
|---|---|
| `equip(PIC)` | 玩家裝備時，傳入 PlayerInteractionComponent |
| `unequip()` | 玩家卸下時 |
| `action_primary(item, is_released)` | 主要動作按下/鬆開 |
| `action_secondary(is_released)` | 次要動作按下/鬆開 |
| `reload()` | 換彈時 |

共用 `@onready`：
- `animation_player : AnimationPlayer`
- `audio_stream_player_3d : AudioStreamPlayer3D`
- `wieldable_mesh : MeshInstance3D`
- `player_interaction_component : PlayerInteractionComponent`（equip 時注入）
- `item_reference : WieldableItemPD`（由 PIC 的 equipped_wieldable_item 提供）

---

## 二、wieldable_toy_pistol.gd（投射物手槍）

**位置**：`addons/cogito/Wieldables/wieldable_toy_pistol.gd`

### 彈丸池（Object Pool）
```
POOL_SIZE = 50

_ready():
  for i in 50: projectile_pool.append(projectile_prefab.instantiate())

get_projectile():
  _last_index = wrapi(_last_index + 1, 0, 50)
  return projectile_pool[_last_index]  // 循環重用，避免頻繁 instantiate
```

### 射擊流程（action_primary）
```
1. 若 is_released → return（只在按下時觸發）
2. animation_player.is_playing() → return（利用動畫播放時間控制射速）
3. charge_current <= 0 → send_empty_hint() → return
4. 播放動畫 + 音效
5. item_reference.subtract(1)  // 消耗 1 發彈藥
6. 取得準心射線碰撞點：
   camera_collision = PIC.Get_Camera_Collision()
   Direction = (camera_collision - bullet_point.global_pos).normalized()
7. 從 pool 取彈丸 → 加入 bullet_point → 設定全域位置
8. Projectile.damage_amount = item.wieldable_damage
9. Projectile.set_linear_velocity(Direction * projectile_velocity)
10. Projectile.reparent(current_scene)  // 從 bullet_point 移出，加入場景根節點
```

**準心射線** vs **槍口方向**：方向向量由「相機碰撞點 → 槍口」計算，確保射擊方向與瞄準點一致，而非純槍口朝向（防止近距離偏差）。

### ADS（瞄準鏡模式）
```
action_secondary(is_released):
  if is_released:  // 鬆開 → 縮放還原
    Tween: camera.fov → 75
    Tween: self.position → default_position
    emit update_crosshair(true)   // 顯示準心
  else:            // 按住 → 縮放
    Tween: camera.fov → ads_fov（例如 65）
    Tween: self.position → Vector3(0, y, z)  // 水平置中
    emit update_crosshair(false)  // 隱藏準心
```

---

## 三、wieldable_laser_rifle.gd（連發雷射步槍，Hitscan）

**位置**：`addons/cogito/Wieldables/wieldable_laser_rifle.gd`

### 持續射擊模式（Hold-to-fire）
```
action_primary(_passed_item, is_released):
  if is_released: is_firing = false
  else:           is_firing = true

_physics_process(delta):
  firing_cooldown -= delta
  if is_firing and firing_cooldown <= 0:
    hit_scan_collision(camera_collision)  // 立刻造成傷害（Hitscan）
    播放動畫 + 音效
    item.subtract(1)
    if charge == 0: is_firing = false
    firing_cooldown = firing_delay        // 射速控制
```

### Hitscan 碰撞（hit_scan_collision）
```
bullet_direction = (collision_point - bullet_point.pos).normalized()
ray = PhysicsRayQueryParameters3D.create(bullet_point.pos, collision_point + dir*2)
ray.exclude = [player_rid]              // 排除玩家自身
bullet_collision = world.direct_space_state.intersect_ray(ray)

if collision:
  hit_scan_damage(collider, dir, pos)   // 發送 damage_received 信號
  if collision_scene: hit_scan_scene()  // 生成碰撞特效場景
  if decal_spawn:
    BulletDecalPool.spawn_bullet_decal(pos, normal, collider, basis, texture)
```

**雷射光線視覺**：
```
instantiated_ray = laser_ray_prefab.instantiate()
instantiated_ray.draw_ray(bullet_point.pos, collision_point)  // 繪製從槍口到碰撞點的線段
spawn_node.add_child(instantiated_ray)
```

### 與手槍的差異

| 特性 | 手槍（toy_pistol） | 雷射步槍（laser_rifle） |
|---|---|---|
| 傷害方式 | 投射物（物理彈丸） | Hitscan（即時光線投射） |
| 射擊模式 | 單發（按一次射一發） | 全自動（按住持續射擊） |
| 彈丸管理 | Object Pool（預生成 50 顆） | 無彈丸，光線即時計算 |
| 視覺效果 | 真實彈丸飛行 | 雷射光線場景（laser_ray_prefab） |
| 彈痕 | 無（TODO） | BulletDecalPool 貼花 |

---

## 四、wieldable_pickaxe.gd（近戰鎬，Area3D 傷害）

**位置**：`addons/cogito/Wieldables/wieldable_pickaxe.gd`

### 耐力消耗
```
_ready():
  if uses_stamina:
    player_stamina = CogitoSceneManager._current_player_node.stamina_attribute

action_primary():
  if uses_stamina and player_stamina.value_current < stamina_cost:
    return  // 耐力不足，無法揮擊
  player_stamina.subtract(stamina_cost)
  播放揮擊動畫 + 音效
```

### 雙模式命中偵測

```
damage_area.body_entered → _on_body_entered(collider):
  if collider.has_signal("damage_received"):
    if use_camera_collision:
      // 模式A：Camera-Collider（可靠度高，精度低）
      hit_pos = PIC.Get_Camera_Collision()
      bullet_dir = (hit_pos - player.global_pos).normalized()
    else:
      // 模式B：Hitbox-Collider 射線（精度高，可靠度略低）
      ray_params = PhysicsRayQueryParameters3D（hitbox → collider）
      result = space_state.intersect_ray(ray_params)
      hit_pos = result.position
      bullet_dir = (hit_pos - hitbox_origin).normalized()
    
    collider.damage_received.emit(item_reference.wieldable_damage, bullet_dir, hit_pos)
```

- **模式 A**（Camera）：方向從玩家中心到準心碰撞點，與視覺一致。
- **模式 B**（Hitbox）：從 `damage_area` 原點到目標射線，近戰感較真實，但射線可能穿牆。

---

## 五、wieldable_flashlight.gd（手電筒，電量消耗）

**位置**：`addons/cogito/Wieldables/wieldable_flashlight.gd`

### 電量耗盡機制
```
_process(delta):
  if is_on:
    PIC.equipped_wieldable_item.subtract(delta * drain_rate)  // 每秒扣電量
    if charge == 0: turn_off()
```
消耗量以 `delta * drain_rate` 連續計算，讓 `charge_current` 在 `CogitoAttribute` 的響應式 setter 中到零時自動關燈。

### 防連點機制（Toggle Cooldown）
```
action_primary():
  if not is_action_pressed and can_toggle and not animation_player.is_playing():
    is_action_pressed = true
    can_toggle = false          // 進入冷卻
    animation_player.play()
    toggle_on_off():
      await Timer(button_press_delay)   // 動作確認延遲
      await animation_finished          // 等動畫完成
      if is_on: toggle_flashlight(false)
      elif charge > 0: toggle_flashlight(true)
      else: send_empty_hint()

_process():
  if not can_toggle:
    cooldown_timer += delta
    if cooldown_timer >= toggle_cooldown: can_toggle = true
```

### 卸下時強制關閉
```
unequip():
  animation_player.play(anim_unequip)
  if is_on: turn_off()   // 確保卸下時燈熄滅，不造成「幽靈光源」
```

---

## 六、wieldable_throwable.gd（投擲物）

**位置**：`addons/cogito/Wieldables/wieldable_throwable.gd`

### 特殊設計：投擲物即物品本身
```
instantiate_projectile():
  if projectile_override != null:
    return projectile_override.instantiate()   // 可指定獨立彈丸場景
  return load(item_reference.drop_scene).instantiate()  // 否則使用物品的掉落場景
```
投擲物投出後，即是物品的實體（使用 `drop_scene`），可被撿回（PickupComponent）。

### 投擲後自動管理物品欄
```
equip():
  player_inventory = PIC.parent.inventory_data
  item_slot = get_slot_reference()  // 找到自己在物品欄中的 slot

action_primary():
  unequip()  // 先卸下（播放動畫）
  
  item_slot.quantity -= 1
  if quantity < 1:
    player_inventory.remove_slot_data(item_slot)
    item_reference.put_away()   // 通知 WieldableItemPD 收起
  else:
    equip(PIC)   // 還有剩 → 重新裝備繼續投擲
  
  inventory_updated.emit()   // 通知 HUD 更新數量顯示
  
  // 生成並發射投擲物
  projectile.set_linear_velocity(Direction * projectile_velocity)
  projectile.reparent(current_scene)
```

---

## 七、wieldable_consumable.gd（消耗品）

**位置**：`addons/cogito/Wieldables/wieldable_consumable.gd`

（此 Wieldable 用於「裝備後直接使用消耗品」，如喝藥水的動作。實際效果定義在 `ConsumableItemPD.use()` 中，呼叫後由 PlayerInteractionComponent 刪除物品並換彈。）

---

## 八、玩家動作完整流程

### 主要動作觸發鏈
```
[玩家按下 input_action_primary]
  │
  ▼
PlayerInteractionComponent._unhandled_input()
  └─ if equipped_wieldable_item:
       equipped_wieldable_item.action_primary(equipped_wieldable_item, false)
         └─ 呼叫場景中的 CogitoWieldable 子類（toy_pistol / laser_rifle / ...）
```

### 彈藥補充流程（Reload）
```
[玩家按 reload]
  │
  ▼
PIC.attempt_reload()
  linear scan inventory_slots:
    if slot.inventory_item.name == equipped_item.ammo_item_name:
      move ammo from slot to equipped_item.charge_current
      break

→ CogitoWieldable.reload()  // 播放換彈動畫
```

### 準心碰撞點（Get_Camera_Collision）
```
PIC.Get_Camera_Collision():
  ray = from camera, length = wieldable_range
  exclude player_rid
  if hit: return collision.position
  else:   return camera_pos + forward * wieldable_range
```
所有 Wieldable（Hitscan、投射物方向、近戰方向）都呼叫此方法取得統一的「玩家看向的點」。

---

## 九、Wieldable 設計模式總結

| 實作 | 傷害方式 | 射速控制 | 彈藥消耗 |
|---|---|---|---|
| toy_pistol | 投射物（Object Pool） | animation_player.is_playing() | charge_current - 1 |
| laser_rifle | Hitscan（PhysicsRay） | firing_cooldown timer | charge_current - 1 |
| pickaxe | Area3D body_entered | animation_player.is_playing() | 耐力（CogitoAttribute） |
| flashlight | 無（照明） | toggle_cooldown + anim guard | delta * drain_rate（連續） |
| throwable | 投射物（no pool） | animation_player.is_playing() | quantity（InventorySlot）|

**三種射速控制策略**：
1. **動畫鎖定**：`animation_player.is_playing()` 期間拒絕輸入（手槍、鎬、投擲）。
2. **計時器冷卻**：`firing_cooldown` 倒數（雷射步槍連發），允許每幀檢查。
3. **Toggle 冷卻**：`can_toggle` + 手動計時（手電筒），防止快速連點。
