# Cogito — Level 3 互動物件系統深度剖析

## 概述

Cogito 的互動物件系統由兩個層次構成：

1. **CogitoObject 基類**（`CogitoObjects/cogito_object.gd`）— 提供共用的持久化介面、AABB 查詢、InteractionComponent 自動掃描。
2. **具體物件類別**（Door、Switch、Container 等）— 各自實作 `interact()` / `save()` / `set_state()` 三件套，加入對應的遊戲群組（`"interactable"`、`"save_object_state"`）。

---

## 一、CogitoObject（基類）

**位置**：`addons/cogito/CogitoObjects/cogito_object.gd`

### 職責
- 繼承 `Node3D`，標記 `@tool`（支援 Editor 預覽）。
- `_ready()` 時：
  1. 加入 `"interactable"` 與 `"Persist"` 群組（場景管理器掃描這些群組儲存物件）。
  2. `find_interaction_nodes()`：掃描所有 `InteractionComponent` 子節點存入 `interaction_nodes`。
  3. `find_cogito_properties()`：掃描第一個 `CogitoProperties` 存入 `cogito_properties`（物質屬性系統）。

### AABB 計算
```
get_aabb():
  若 custom_aabb 非空 → 直接回傳自訂 AABB
  否則 → 遍歷所有可見 MeshInstance3D，merge 各自的 AABB
```
用途：計算物件空間大小，輔助投擲落點、互動提示 Marker 位置。

### 存檔介面
```
save() → {
  filename, parent, pos, rot,
  spawned_loot_item,
  (若為 RigidBody3D) linear_velocity, angular_velocity
}
```
注意：`save()` 額外偵測 RigidBody3D（向上爬父節點），儲存物理速度，確保讀檔後物件維持靜止姿態。

### CogitoProperties 整合
`_on_body_entered/exited` 呼叫 `cogito_properties.start_reaction_threshold_timer(body)`，驅動物質反應（如燃燒傳播、溫度擴散）。

---

## 二、CogitoDoor（門）

**位置**：`addons/cogito/CogitoObjects/cogito_door.gd`

### 三種門型態（DoorType）

| 型態 | 移動方式 | 關鍵參數 |
|---|---|---|
| `ROTATING` | `_physics_process` 中 `rotation.move_toward(target, delta*speed)` | `open_rotation`、`closed_rotation`、`angle_tolerance` |
| `SLIDING` | `Tween.tween_property(self,"position", ...)` | `open_position`、`closed_position`、`door_speed` |
| `ANIMATED` | `AnimationPlayer.play(opening_animation)` | `animation_player`、`opening_animation`、`reverse_opening_anim_for_close` |

`_validate_property()` 根據 `door_type` 動態隱藏 Inspector 中不相關的參數欄位（GDScript `PROPERTY_USAGE_NO_EDITOR`）。

### 互動流程

```
interact(interactor):
  若 is_locked → door_rattle()（播音 + send_hint）
  若 !is_open  → open_door(interactor)  + sync doors_to_sync_with
  否則         → close_door(interactor) + sync doors_to_sync_with
```

### 雙向旋轉（bidirectional_swing）
```
open_door():
  offset = interactor.global_pos - door.global_pos
  dot = offset.dot(door.basis.x)
  swing_direction = -1 if dot < 0 else 1
  target_rotation = open_rotation * swing_direction
```
門根據玩家站在哪一側決定往哪個方向開。

### 鎖定系統
- `key : KeyItemPD`：鑰匙物品資源（Resource 型別）。
- `lockpick : InventoryItemPD`：撬鎖道具（更通用型別）。
- `unlock_door()` 中若 `key.discard_after_use == true`，會線性掃描玩家 `inventory_slots` 找到對應物品並呼叫 `remove_item_from_stack()`。
- `interact2(interactor)`：次要互動 — 只要門未開就可以鎖/解鎖（`lock_unlock_switch()`），並同步 `doors_to_sync_with`。

### 雙門同步
```gd
doors_to_sync_with : Array[NodePath]
// open_door() / close_door() / lock_unlock_switch() 均遍歷並轉發同名方法
```

### 自動關門
```
open_door():
  if auto_close_time > 0:
    close_timer = Timer.new(); add_child; start()
    close_timer.timeout → on_auto_close_time() → close_door()
close_door():
  if close_timer: close_timer.queue_free()
```

### 存檔
```
save() → { node_path, is_locked, is_open, pos, rot }
set_state():
  若 is_open 且無 auto_close → set_to_open_position()
  否則 → set_to_closed_position()
  emit object_state_updated, lock_state_updated
```

---

## 三、CogitoSwitch（開關）

**位置**：`addons/cogito/CogitoObjects/cogito_switch.gd`

### 觸發鏈設計
```
objects_call_interact : Array[NodePath]
objects_call_delay    : float

call_interact_on_objects():
  for nodepath in objects_call_interact:
    await Timer(objects_call_delay)
    get_node(nodepath).interact(player_interaction_component)
```
**任何實作 `interact()` 的物件都可以被 Switch 串聯觸發**，形成觸發鏈（如開關 → 開門 → 播動畫）。

### 物品需求機制
```
needs_item_to_operate = true:
  第一次觸發 → check_for_item() → 消耗物品 → 切換開關 → is_holding_item=true
  第二次觸發 → 將物品加回玩家 inventory → 切換回去
```
開關可以「取走」玩家的物品作為條件，再次互動時歸還，類似 Immersive Sim 中的「插入零件啟動機器」機制。

### 節點顯隱控制
```
switch_on():
  nodes_to_show_when_on → .show()
  nodes_to_hide_when_on → .hide()
switch_off(): 反轉
```
純靠 Inspector 拖拽即可控制哪些燈光/裝飾開關時顯示或隱藏。

### 子彈觸發
```
_on_damage_received():
  interact(CogitoSceneManager._current_player_node.player_interaction_component)
```
Switch 可以被子彈射擊觸發（`damage_received` 信號連接到 `_on_damage_received`）。

---

## 四、CogitoContainer（容器）

**位置**：`addons/cogito/CogitoObjects/cogito_container.gd`

### 設計重點
- 擁有自己的 `inventory_data : CogitoInventory` Resource（.tres 資產），可在 Inspector 預先配置容器內物品。
- `_ready()` 呼叫 `inventory_data.apply_initial_inventory()`，初始化容器的初始物品陣列。
- 加入 `"external_inventory"` 群組，讓 UI 系統能辨識此物件為外部物品欄。

### 互動流程
```
interact(_player_interaction_component):
  toggle_inventory.emit(self)  // 信號發送給 HUD / InventoryUI
```
Container 本身不直接操作 UI；它只發出信號，HUD 接收後開啟一個「外部物品欄」視窗，讓玩家在自己物品欄與容器物品欄間拖拽轉移。

### 容器開關動畫
```
open() / close():
  uses_animation → animation_player.play(open_animation) 或 play_backwards
  更新 interaction_text → emit object_state_updated
```

---

## 五、CogitoKeypad（密碼鍵盤）

**位置**：`addons/cogito/CogitoObjects/cogito_keypad.gd`

### 輸入處理
```
_on_button_received(str):
  "C" → clear_entered_code()
  "E" → check_entered_code()
  _  → append_to_entered_code(str)
    若長度達到 passcode.length() → 自動 check_entered_code()
```

### 解鎖流程
```
check_entered_code():
  若相符 → unlock_keypad():
    播音 → 綠燈 → emit correct_code_entered
    await Timer(unlock_wait_time)
    for door in doors_to_unlock:
      door.unlock_door()
      if open_when_unlocked: door.open_door()
    close()
  若不符 → 紅燈 → await timer → clear
```

### UI 聚焦管理
```
open():  emit toggled_interface(true)  // 停止玩家移動/視角
         grab_focus_button.grab_focus()
close(): emit toggled_interface(false)
         disconnect menu_pressed
```
`_on_focus_changed()` 監聽 `viewport.gui_focus_changed`，防止鍵盤事件穿透到玩家控制器。
```
_unhandled_input():
  if in_focus: get_viewport().set_input_as_handled()
```

### 直接引用型態
```gd
doors_to_unlock : Array[CogitoDoor]  // 強型別陣列，不是 NodePath
```
與 Switch 的 `Array[NodePath]` 相比，Keypad 直接持有 `CogitoDoor` 參照，省去 `get_node()` 步驟，但喪失泛用性。

---

## 六、CogitoVendor（販賣機）

**位置**：`addons/cogito/CogitoObjects/cogito_vendor.gd`

### 架構
- 依賴子節點 `GenericButton`（CogitoSwitch 或 CogitoButton）與 `CurrencyCheck` 組件。
- `CurrencyCheck.transaction_success` 信號 → `_on_transaction_success()`。
- `_ready()` 中從玩家 `find_children("","CogitoCurrency")` 取得貨幣屬性節點。

### 販賣流程
```
_on_transaction_success():
  send_hint(icon, purchased_hint_text)
  amount_remaining -= 1
  _update_vendor_state()
  _delayed_object_spawn()

_delayed_object_spawn():
  await Timer(spawn_delay)
  spawned_object = object_to_spawn.instantiate()
  spawned_object.position = spawn_point.global_position
  get_tree().current_scene.add_child(spawned_object)  // 動態生成物品到場景
```

### 庫存限制
```
_update_vendor_state():
  if amount_remaining == 0:
    cogito_button.allows_repeated_interaction = false
    stock_label.text = stock_empty_text
```
`spawn_delay` 不可超過按鈕 `press_cooldown_time`，防止連點產生超出庫存的物品。

---

## 七、CogitoPressurePlate（壓力板）

**位置**：`addons/cogito/CogitoObjects/cogito_pressure_plate.gd`

### 物理偵測機制

壓力板使用**雙重偵測策略**：

1. **`_on_plate_body_entered`**（Area3D 信號）：
   - 若偵測到 Player → `plate_node.add_constant_central_force(Vector3(0,-3,0))`（施加向下持續力，使板子真的被壓下）。
   - 偵測到 CogitoObject → 記錄（重物壓板）。

2. **`_physics_process` 位置偵測**：
   ```
   if !is_activated and 板子與加壓位置距離 <= 0.03 → weigh_down()
   if  is_activated and 板子與加壓位置距離 > 0.03  → weight_lifted()
   ```
   透過物理位移（而非碰撞事件）判斷板子是否真的被壓到底，避免碰撞事件漏報。

3. **`_on_plate_body_exited`**：
   - Player 離開 → 移除持續力。
   - CogitoObject 離開 → `weight_lifted()`。

### 觸發串聯
與 CogitoSwitch 相同，持有 `objects_call_interact : Array[NodePath]`，在 `weigh_down()` 中呼叫。

---

## 八、CogitoSnapSlot（卡扣插槽）

**位置**：`addons/cogito/CogitoObjects/cogito_snap_slot.gd`

### 用途
類似 Immersive Sim 的「放置謎題」：玩家拖著特定物件靠近時自動吸附鎖定，可作為謎題觸發條件。

### 物件識別
```
instanced_expected_object = expected_object.instantiate()  // 僅取名稱，不加入場景

_on_body_entered_snap_area(body):
  if body is CogitoObject and
     instanced_expected_object.cogito_name == body.cogito_name:
    place_carryable(body)
```
用 `cogito_name` 字串比對而非類型比對，允許同場景多個同名物件互換。

### 放置與凍結
```
place_carryable(carryable):
  carryable.set_freeze_mode(0)  // FreezeMode.STATIC
  carryable.freeze = true        // 停止物理模擬
  carryable.global_transform = snap_position.global_transform
```

### 動態信號切換（is_holding_object setter）
```
is_holding_object = true:
  snap_shape.visible = false
  await Timer(setter_delay)
  disconnect body_entered
  connect    body_exited    // 開始偵測物件移出
is_holding_object = false:
  snap_shape.visible = true
  await Timer(setter_delay)
  disconnect body_exited
  connect    body_entered   // 重新偵測物件移入
```
`setter_delay` 防止放下瞬間觸發移除信號。

---

## 九、CogitoProjectile（彈丸）

**位置**：`addons/cogito/CogitoObjects/cogito_projectile.gd`

繼承 `CogitoObject`，由 Wieldable 實作類（如 `wieldable_toy_pistol.gd`）在射擊時動態實例化並設定 `damage_amount`。

### 碰撞處理（4 種情境）
```
_on_body_entered(collider):
  (1) 彈丸無屬性、目標無屬性 → deal_damage()
  (2) 目標有屬性、彈丸無屬性 → deal_damage()（忽略目標屬性，TODO）
  (3) 彈丸有屬性、目標無屬性 → 若彈丸是 SOFT 材質 → 不傷害
  (4) 雙方皆有屬性 → 若雙方皆 SOFT → deal_damage()
                     → 呼叫 cogito_properties.check_for_systemic_reactions()（觸發物質連鎖）
```

### 黏附機制
```
stick_on_impact = true:
  linear_velocity = angular_velocity = Vector3.ZERO
  stick_to_object(collider):
    PinJoint3D.node_a = self.path
    PinJoint3D.node_b = collider.path
    get_tree().root.add_child(joint)
```
用 `PinJoint3D` 關節把彈丸釘在目標上（如弓箭插入牆壁）。

### 生命週期
```
Lifespan Timer → timeout → on_timeout() → die()
die():
  play sound_on_death
  spawn_on_death 場景列表依序實例化（如爆炸特效）
  queue_free()
```
`pick_up_delay` 防止玩家射出後立刻撿回彈丸。

---

## 十、互動物件系統架構圖

```
┌─────────────────────────────────────────────────────────┐
│                互動物件（各自繼承 Node3D）                 │
│  CogitoObject        CogitoDoor   CogitoSwitch           │
│  CogitoContainer     CogitoKeypad CogitoPressurePlate    │
│  CogitoSnapSlot      CogitoVendor CogitoProjectile       │
└───────┬─────────────────────┬───────────────────────────┘
        │ 全部實作             │
   save() / set_state()    interact(PIC)
        │                     │
        ▼                     ▼
 CogitoSceneManager    PlayerInteractionComponent
 (存檔/讀檔掃描              (玩家視角互動分派)
  "save_object_state")
```

### 觸發鏈模式（Trigger Chain）

```
[玩家互動]
    │
    ▼
CogitoSwitch.interact()
  └─ call_interact_on_objects()
       ├─► CogitoDoor.interact()   (開門)
       ├─► CogitoSwitch.interact() (連鎖觸發另一開關)
       └─► CogitoVendor 子節點.interact()
```

所有具體物件只要實作 `interact(PIC)` 即可加入觸發鏈，**無需繼承共同基類或實作特定介面**（Duck Typing）。

---

## 十一、持久化模式總覽

所有互動物件均實作相同的持久化三件套：

| 方法 | 時機 | 職責 |
|---|---|---|
| `save()` | 存檔時，場景管理器掃描 `"save_object_state"` 群組 | 回傳 Dictionary，序列化狀態（`is_open`、`is_locked`、位置等） |
| `set_state()` | 讀檔後，場景管理器呼叫 | 從已反序列化的欄位（如 `is_open`）還原物件視覺/物理狀態，不產生音效/動畫 |
| `_ready()` | 場景初始化 | 加入 group、初始化互動文字，有時與 `set_state()` 邏輯重疊 |

**`set_state()` 與 `_ready()` 的差異**：
- `_ready()` 的開門動畫會播放 Tween；`set_state()` 直接設定 `position`/`rotation_degrees`，靜默還原狀態，不觸發聲音或動畫。

---

## 十二、LockInteraction 組件橋接

**位置**：`addons/cogito/Components/Interactions/LockInteraction.gd`

繼承 `InteractionComponent`，作為「鎖定邏輯」與「互動組件系統」之間的橋接器：

```
interact(PIC):
  if check_for_item(PIC, parent.key) → parent.interact2(PIC)
  elif check_for_item(PIC, parent.lockpick) → parent.interact2(PIC)
  else:
    if parent.is_locked → send_hint(key_hint)

check_for_item(interactor, item):
  遍歷 inventory_slots，比對 inventory_item == item
  若 discard_after_use → remove_item_from_stack(slot)
  return true/false
```

`lock_state_updated` 信號連接到 `_lock_state_updated(text)`，讓互動提示文字與門的鎖定狀態保持同步。
