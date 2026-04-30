# Cogito — Level 2 核心模組職責深度分析

---

## 1. 玩家系統（`CogitoPlayer`）

### 節點層級結構
```
CogitoPlayer (CharacterBody3D)
└── Body (Node3D)
    └── Neck (Node3D)
        └── Head (Node3D)
            └── Eyes (Node3D)
                ├── Camera (Camera3D)
                └── AnimationPlayer
└── PlayerInteractionComponent
└── FootstepPlayer (FootstepSurfaceDetector)
└── StandingCollisionShape / CrouchingCollisionShape
└── CrouchRayCast
└── SlidingTimer / JumpCooldownTimer
└── NavigationAgent3D       ← 用於起身後尋找安全落點
└── Wieldables (%節點)
```

### `_physics_process(delta)` 主迴圈流程

```
_physics_process(delta)
│
├─ [is_sitting] → _process_on_sittable(delta)  ← 坐下時短路
│
├─ [on_ladder]  → _process_on_ladder(delta)     ← 爬梯時短路
│
├─ 取得 input_dir（is_movement_paused → Vector2.ZERO）
│
├─ ── 蹲下/起身 ──
│   ├─ TOGGLE_CROUCH 模式：just_pressed 切換 try_crouch
│   └─ HOLD 模式：pressed = try_crouch
│
├─ ── 速度狀態機 ──
│   ├─ 蹲下中：
│   │   ├─ 若 sprinting+輸入中 → 啟動 sliding_timer，記錄 slide_vector
│   │   └─ current_speed lerp → CROUCHING_SPEED（滑行中不修改）
│   └─ 站立中：
│       ├─ sprint + stamina > 0 → lerp → SPRINTING_SPEED（支援 bunnyhop）
│       └─ 普通 → lerp → WALKING_SPEED
│
├─ 自由視角（free_look 鍵 / 滑行中）：neck 左右偏轉，eyes.z 傾斜
│  否則：neck.rotation.y 累加回 body.rotation.y
│
├─ ── 重力與跳躍 ──
│   ├─ is_on_floor：gravity_vec = 0
│   └─ 在空中：gravity_vec += gravity_vector * gravity * delta
│
├─ ── 方向計算 ──
│   direction = (body.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
│
├─ ── 速度合成 ──
│   ├─ 地面：main_velocity lerp 至 direction * current_speed
│   └─ 空中：main_velocity lerp 至 direction * current_speed（AIR_LERP_SPEED）
│
├─ ── 跳躍 ──
│   └─ is_on_floor + jump pressed：main_velocity.y = JUMP_VELOCITY
│       ├─ 蹲跳：CROUCH_JUMP_VELOCITY
│       └─ 滑跳：main_velocity.x/z * SLIDE_JUMP_MOD
│
├─ ── 樓梯處理（Stair Stepping）──
│   └─ test_motion() 前方碰撞 → 再 test_motion() 向上偏移 STEP_HEIGHT
│       若可通行 → 瞬移高度差（smoothed by step_height_camera_lerp）
│
├─ velocity = main_velocity + gravity_vec
│
├─ move_and_slide()
│
├─ ── 推動 RigidBody3D ──
│   └─ get_slide_collision() → 對 RigidBody3D 施加 PLAYER_PUSH_FORCE
│
├─ ── 頭部晃動（Headbob）──
│   └─ 依 wiggle_index 計算 sin/cos 偏移 → eyes.position
│
├─ ── 腳步音效 ──
│   └─ 依速度 velocity_sqr 決定間隔（walk/sprint），呼叫 footstep_surface_detector
│
└─ ── 落地判斷 ──
    └─ was_in_air && velocity.y < landing_threshold → 播放落地音效
```

### 屬性系統初始化（`_ready`）
- 以 `find_children("","CogitoAttribute",false)` 自動掃描所有子屬性節點，放入 `player_attributes: Dictionary`（key = `attribute_name`）。
- `health.death` signal → `_on_death()`（設 `is_dead = true`，通知 PIC）。
- `visibility.attribute_changed` signal → `sanity_attribute.on_visibility_changed()`（若兩者皆存在）。
- 貨幣同理掃描 `CogitoCurrency` 子節點。

---

## 2. PlayerInteractionComponent（PIC）

### 職責
作為玩家所有主動行為的「中樞調度器」：互動、搬運、投擲、持用武器。

### 關鍵資料結構
| 變數 | 型別 | 說明 |
|---|---|---|
| `interactable` | 物件（setter） | 當前視線內的互動物件；setter 自動 emit `interactive_object_detected` |
| `carried_object` | 物件（setter） | 當前搬運的物件；setter 自動 emit `started_carrying` |
| `equipped_wieldable_item` | `WieldableItemPD` | 當前裝備的物品 Resource |
| `equipped_wieldable_node` | `CogitoWieldable` | 當前裝備的 3D 場景節點 |
| `is_changing_wieldables` | bool | 換武器動畫播放中，鎖定輸入 |

### 互動分派流程（`_handle_interaction(action)`）
```
_handle_interaction(action)
│
├─ [is_carrying]
│   ├─ carried_object.input_map_action == action → _drop_carried_object()
│   └─ 否則掃 carry_parent.interaction_nodes
│       └─ 找到 PickupComponent / BackpackComponent / ExtendedPickupInteraction → node.interact(self)
│           └─ DualInteraction → await interaction_complete → _rebuild_interaction_prompts()
│
└─ [interactable != null && !is_carrying]
    └─ 掃 interactable.interaction_nodes
        └─ node.input_map_action == action && !is_disabled → node.interact(self)
            └─ DualInteraction → await interaction_complete → _rebuild_interaction_prompts()
```

### Wieldable 換裝流程（`change_wieldable_to`）
```
change_wieldable_to(next_wieldable)
  1. is_changing_wieldables = true
  2. 若已持物：舊物 is_being_wielded = false → equipped_wieldable_node.unequip() → await unequip 動畫
  3. queue_free 舊 node
  4. equip_wieldable(next_wieldable)
     ├─ wieldable_item.build_wieldable_scene() → add_child 到 wieldable_container
     ├─ node.equip(self)
     └─ await equip 動畫結束 → is_changing_wieldables = false
```

### 重裝（`attempt_reload`）
- 從 `inventory_data.inventory_slots` 線性搜尋匹配 `ammo_item_name` 的格子。
- 按 `reload_amount` 批次充能 `charge_current`，消耗對應格子的 `quantity`。
- 最後 emit `inventory_updated` 與 `update_wieldable_data`。

### 投擲公式
```
throw_force = mass * throw_power_mass_multiplier
throw_force = clamp(throw_force, 0, max_throw_power)
若 throw_force >= throw_stamina_threshold 且耐力不足 → 改為 drop
```

---

## 3. InteractionComponent（互動組件基類）

**腳本位置**：`Components/Interactions/InteractionComponent.gd`

### 核心 @export 屬性
| 屬性 | 功能 |
|---|---|
| `input_map_action` | 觸發此互動的輸入動作名稱 |
| `interaction_text` | HUD 互動提示文字 |
| `is_disabled` | 可被其他組件（如 DualInteraction）動態關閉 |
| `ignore_open_gui` | false = GUI 開啟時不處理此互動 |
| `attribute_check` | `NONE / FAIL_MESSAGE / HIDE_INTERACTION` |
| `attribute_to_check` | 要檢查的屬性名稱（對應 `player_attributes` key）|
| `min_value_to_pass` | 通過門檻 |

### 屬性檢查流程（`check_attribute`）
1. 從 `player_interaction_component.player.player_attributes` 取得對應屬性。
2. 若 `value_current >= min_value_to_pass`：套用 `attribute_effects`（ConsumableEffect 陣列），回傳 `true`。
3. 否則依模式顯示 fail hint 或隱藏互動。

### 已知子類
| 子類 | 功能 |
|---|---|
| `BasicInteraction` | 觸發 signal，無附加邏輯 |
| `PickupComponent` | 將物件加入 inventory |
| `CarryableComponent` | 搬運物理物件 |
| `LockInteraction` | 需要 KeyItem |
| `HoldInteraction` | 長按才觸發 |
| `DualInteraction` | 需兩個互動，emit `interaction_complete` 同步 |
| `ReadableComponent` | 顯示筆記/文字 UI |
| `DialogicInteraction` | 觸發 Dialogic 對話 |
| `BackpackComponent` | 觸發容器物品欄 |
| `ExtendedPickupInteraction` | 支援多選項拾取 |

---

## 4. 物品欄系統（`CogitoInventory`）

**腳本位置**：`InventoryPD/cogito_inventory.gd`（extends Resource）

### 資料結構
```
CogitoInventory (Resource)
├── inventory_slots : Array[InventorySlotPD]   ← 大小 = size.x * size.y
├── inventory_size  : Vector2i                  ← (寬, 高)
├── grid            : bool                      ← 是否啟用網格模式
└── starter_inventory : Array[InventorySlotPD]  ← 初始物品清單
```

### Grid 模式下的空間管理
- 物品有 `item_size: Vector2`（e.g., 手槍 = (1,2)）。
- `inventory_slots` 是一維陣列，同一物件佔多格時全部指向同一個 `InventorySlotPD`（`add_adjacent_slots` 處理）。
- `origin_index` 記錄物品左上角格子位置，`null_out_slots` 依 `item_size` 清空所有佔用格。
- `is_enough_space`：先檢查邊界，再確認佔用格只有一個不同 origin 物件（swap 邏輯）。

### 關鍵操作
| 函數 | 行為 |
|---|---|
| `pick_up_slot_data(slot)` | 先找可 merge 的格子，再找空格，失敗 → send_hint "Unable to pick up" |
| `grab_slot_data(index)` | 取走整疊（null_out_slots），emit inventory_updated |
| `grab_single_slot_data(index)` | 取一個，quantity -= 1，歸零則清格 |
| `use_slot_data(index)` | 呼叫 `item.use(owner)`，成功且是 consumable → quantity -= 1 |
| `remove_slot_data(slot)` | 直接清除特定 slot（用於 key 消耗等） |
| `drop_single_slot_data(grabbed, index)` | 支援 merge、ammo 充能（拖拽彈藥到武器格）、combinable 合成 |
| `take_all_items(target)` | 批次轉移所有物品到另一個 inventory |

### Combine 合成流程（在 `drop_single_slot_data`）
```
grabbed 是 CombinableItemPD && slot.item.name == grabbed.target_item_combine
  → remove_slot_data(slot)          # 消耗目標物
  → grabbed.quantity -= 1           # 消耗材料
  → pick_up_slot_data(resulting_item)  # 加入合成結果
```

---

## 5. 物品 Resource 繼承鏈

```
Resource
└── InventoryItemPD          (基類：名稱、圖示、堆疊設定、掉落場景、音效)
    ├── ConsumableItemPD     (use() → 對玩家屬性 add/subtract)
    ├── WieldableItemPD      (use() → take_out/put_away；charge 系統)
    │   └── [WieldableItemPD 引用 wieldable_scene: PackedScene]
    ├── KeyItemPD            (use() → 配合 LockInteraction，用後自動消耗)
    ├── AmmoItemPD           (reload_amount；is_ammo_item() 標記)
    ├── CombinableItemPD     (target_item_combine, resulting_item)
    └── CurrencyItemPD       (轉交 CogitoCurrency 節點)
```

### `WieldableItemPD.use(target)` 雙態邏輯
```
is_being_wielded == false → take_out()
  └─ is_being_wielded = true
     update_wieldable_data(PIC)  # emit updated_wieldable_data signal → HUD 更新
     PIC.change_wieldable_to(self)

is_being_wielded == true → put_away()
  └─ is_being_wielded = false
     PIC.change_wieldable_to(null)
```

---

## 6. 屬性系統（`CogitoAttribute`）

**腳本位置**：`Components/Attributes/cogito_attribute.gd`（extends Node）

### 設計核心：setter 驅動的響應式數值
```gdscript
var value_current : float:
    set(value):
        var prev = value_current
        value_current = clamp(value, 0, value_max)
        attribute_changed.emit(attribute_name, value_current, value_max, prev < value_current)
        if value_current <= 0:
            attribute_reached_zero.emit(...)
```
- `add(amount)` / `subtract(amount)` → 修改 `value_current` 觸發 setter。
- `is_locked` 時跳過實際修改，但仍 emit signal（確保 UI 正確顯示）。
- `dont_save_current_value` 旗標：存檔時跳過此屬性的當前值。

### 內建屬性子類
| 子類 | 額外行為 |
|---|---|
| `cogito_health_attribute` | `attribute_reached_zero` emit `death` signal |
| `cogito_stamina_attribute` | 自動恢復邏輯（`_process`）|
| `cogito_visibility_attribute` | 整合環境 LightZone，計算可見度 |
| `cogito_sanity_attribute` | 監聽 visibility signal 變化 |
| `cogito_light_meter_attribute` | 量測環境光強度 |

---

## 7. 場景管理與存檔（`CogitoSceneManager`）

**腳本位置**：`SceneManagement/cogito_scene_manager.gd`（Autoload Node）

### 存檔槽架構
```
user://
└── {slot}/                  ← 存檔槽 A / B / C（_active_slot）
    ├── {player_state_prefix}.res    ← CogitoPlayerState
    └── {scene_state_prefix}{scene_name}.res  ← CogitoSceneState（每場景一個）
```

### 讀檔流程（`loading_saved_game`）
```
loading_saved_game(slot)
  1. 讀取 CogitoPlayerState.res
  2. 若當前場景 == 存檔場景 → load_scene_state + load_player_state（原地套用）
  3. 否則 → load_next_scene(stored_scene_path, mode=LOAD_SAVE)
             → 場景載入完成後再執行 2
```

### 持久化涵蓋範圍
- **PlayerState**：位置、旋轉、inventory、屬性值、當前武器、貨幣。
- **SceneState**：場景內所有 `CogitoObject`（門開關、箱子狀態、物品是否已被拾取…）。
- 每個 `CogitoObject` 的 `cogito_name`（@export）作為場景狀態 Dictionary 的 key。

### 場景切換模式（`CogitoSceneLoadMode`）
| 模式 | 說明 |
|---|---|
| `TEMP` | 臨時切換，不觸發存/讀檔 |
| `LOAD_SAVE` | 切換後自動載入對應場景狀態 |
| `RESET` | 切換後清空場景狀態（回到初始） |

---

## 模組互動關係圖

```
CogitoPlayer
  │  player_attributes{} ← CogitoAttribute nodes（子節點掃描）
  │  inventory_data ← CogitoInventory Resource
  └─ PlayerInteractionComponent (PIC)
       │  interaction_raycast → InteractionRayCast
       │  interactable ← 射線偵測到的物件
       │  carried_object
       │  equipped_wieldable_item ← WieldableItemPD
       └─ equipped_wieldable_node ← CogitoWieldable (場景實例)

互動觸發鏈：
  玩家按 F/E
  → PIC._unhandled_input → _handle_interaction(action)
  → target.interaction_nodes[i].interact(PIC)
  → [PickupComponent] → inventory.pick_up_slot_data()
  → [CarryableComponent] → PIC.start_carrying(node)
  → [WieldableItem via QuickSlot] → WieldableItemPD.use(player) → PIC.change_wieldable_to()

存檔觸發鏈：
  暫停選單 Save 按下
  → CogitoSceneManager.save_player_state(player)
  → CogitoSceneManager.save_scene_state(scene)
  → ResourceSaver.save(state, "user://slot/...")
```
