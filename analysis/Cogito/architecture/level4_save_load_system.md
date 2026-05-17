# Cogito — Level 4B 存讀檔完整流程分析

## 一、系統架構概覽

存讀檔系統由四個核心類別協作：

```
CogitoSceneManager（Autoload）
  ├─ CogitoPlayerState（Resource）← 玩家一切狀態
  ├─ CogitoSceneState（Resource）  ← 場景物件狀態
  ├─ LoadingScreen（CanvasLayer）  ← 非同步場景切換
  └─ CogitoScene（Node）           ← 場景根節點，含 Connector 傳送點

CogitoWorldPropertySetter（Node）  ← 跨場景全域旗標寫入
```

---

## 二、存檔槽與目錄結構

**根目錄**：`user://`（由 `CogitoSceneManager.cogito_state_dir` 定義）

```
user://
├── A/
│   ├── COGITO_player_state_.res         ← 玩家狀態（唯一一個）
│   ├── COGITO_scene_state_Level1.res    ← Level1 場景狀態
│   ├── COGITO_scene_state_Level2.res    ← Level2 場景狀態（多場景各有一份）
│   └── A.png                            ← 存檔截圖
├── B/
│   └── ...
├── autosave/
│   └── ...
└── temp/                                ← 臨時緩衝區（場景切換中使用）
```

**前綴常數**（定義於 `cogito_settings.gd`）：
```
scene_state_prefix = "COGITO_scene_state_"
player_state_prefix = "COGITO_player_state_"  （注意：無後綴，每個 slot 只有一個）
auto_save_name = "autosave"
```

---

## 三、兩種持久化群組

場景中所有需要持久化的節點必須加入對應 Group：

| Group 名稱 | 對應類別 | 讀檔行為 |
|---|---|---|
| `"Persist"` | 可移動/可生成物件（RigidBody、投射物、撿拾品） | **重新實例化**（先 queue_free 再 `load(filename).instantiate()`） |
| `"save_object_state"` | 固定場景物件（Door、Switch、Container） | **只更新屬性**（節點仍在場景中，直接 `set()` 屬性值） |

兩者均需實作 `save()` 方法（回傳 Dictionary）。`"Persist"` 群組額外需要 `scene_file_path` 非空（必須是已實例化的場景）。

---

## 四、儲存流程

### 4.1 儲存場景狀態（save_scene_state）

**位置**：`cogito_scene_manager.gd:386`

```
save_scene_state(_scene_name, slot):

  ## Persist 群組 → saved_nodes
  for node in get_nodes_in_group("Persist"):
    if scene_file_path.is_empty(): continue  // 非實例化場景跳過
    if !has_method("save"): continue
    node_data = node.save()
    if node is RigidBody3D:
      附加 linear_velocity + angular_velocity
    _scene_state.add_node_data_to_array(node_data)

  ## save_object_state 群組 → saved_states
  for node in get_nodes_in_group("save_object_state"):
    if !has_method("save"): continue
    _scene_state.add_state_data_to_array(node.save())

  _scene_state.write_state(slot, _scene_name)
```

### 4.2 儲存玩家狀態（save_player_state）

**位置**：`cogito_scene_manager.gd:215`

寫入 `_player_state`（CogitoPlayerState Resource）的內容：

| 資料類別 | 欄位 | 格式 |
|---|---|---|
| 物品欄 | `player_inventory`, `player_quickslots` | Resource 直接儲存 |
| 可揮舞物電量 | `saved_wieldable_charges` | `Array[{resource, charge_current}]` |
| 任務 | `player_active/completed/failed_quests`, `player_active_quest_progression` | `Array[CogitoQuest]` + Dictionary |
| 屬性 | `player_attributes` | `Dictionary<String, Vector2(current, max)>` |
| 貨幣 | `player_currencies` | `Dictionary<String, Vector2(current, max)>` |
| 全域旗標 | `world_dictionary` | Dictionary（跨場景持久） |
| 位置/旋轉 | `player_position`, `player_rotation` | Vector3 |
| 姿態 | `player_try_crouch`, `is_sitting`, ... | bool + Vector3 等 |
| 碰撞體形狀 | `standing/crouching_collision_shape_enabled` | bool |
| 節點 Transform | `body/neck/head/eyes/camera_transform` | Transform3D |
| 互動組件 | `interaction_component_state` | `Array[{equipped_wieldable_item, is_wielding, wieldable_was_on}]` |
| 截圖 | `player_state_screenshot_file` | PNG 路徑 |
| 元資料 | `player_state_savetime`, `player_state_slot_name` | int, String |

**最後一步**：
```
_player_state.write_state("temp")  // 先寫入臨時槽
```

### 4.3 臨時緩衝區（Temp Slot）機制

```
自動存檔流程（_save_autosave_state）：
  1. save_player_state(player, "autosave") → 寫入 temp/
  2. save_scene_state(scene_name, "autosave") → 寫入 temp/
  3. copy_temp_saves_to_slot("autosave") → 複製 temp/ → autosave/

場景切換時（CogitoScene._enter_tree, save_temp_on_enter=true）：
  → save_scene_state(scene_name, "temp")
  → save_player_state(player, "temp")
```

**設計意圖**：`temp` 槽作為「交易緩衝區」，避免存檔過程中途崩潰而留下不完整的存檔槽。程式退出時（`_exit_tree()`）自動清除 `temp/` 目錄。

---

## 五、讀取流程

### 5.1 讀取場景狀態（load_scene_state）

**位置**：`cogito_scene_manager.gd:322`

```
load_scene_state(_scene_name, slot):
  if !state_exists(slot, _scene_name): return

  // 先清除所有現有 Persist 節點（避免重複）
  for node in get_nodes_in_group("Persist"):
    node.queue_free()

  // 重建 Persist 節點
  for node_data in _scene_state.saved_nodes:
    new_object = load(node_data["filename"]).instantiate()
    get_node(node_data["parent"]).add_child(new_object)
    new_object.position = Vector3(x, y, z)
    new_object.rotation = Vector3(x, y, z)
    if RigidBody3D: 恢復 linear/angular_velocity
    for data in node_data.keys():
      new_object.set(data, node_data[data])  // 反射式屬性賦值
    if has_method("set_state"): set_state.call_deferred()

  // 更新 save_object_state 節點
  for state_data in _scene_state.saved_states:
    node = get_node(state_data["node_path"])
    node.position = ...; node.rotation = ...
    for data in state_data.keys():
      node.set(data, state_data[data])  // 反射式屬性賦值
    if has_method("set_state"): node.set_state()
```

**關鍵設計**：`set()` 反射機制讓 `node_data` 字典中任何匹配的屬性名都能直接賦值，無需為每個物件寫客製化讀取邏輯。`set_state.call_deferred()` 確保屬性賦值完成後才執行初始化。

### 5.2 讀取玩家狀態（load_player_state）

**位置**：`cogito_scene_manager.gd:116`

```
load_player_state(player, slot):
  _player_state = _player_state.load_state(slot)  // 從磁碟載入

  // 物品欄
  player.inventory_data = _player_state.player_inventory
  player.inventory_data.assigned_quickslots = _player_state.player_quickslots

  // 任務
  CogitoQuestManager.active.clear_group()
  for quest in player_active_quests:
    quest.start(true)  // mute audio
    CogitoQuestManager.active.add_quest(quest)
  ... (completed/failed 同理)
  // 恢復任務計數器
  for entry in player_active_quest_progression:
    for quest in active.quests:
      if quest.quest_name == entry:
        quest.quest_counter = value

  // 可揮舞物電量（依 Resource 指標比對）
  for data in saved_wieldable_charges:
    for slot in inventory_slots:
      if slot.inventory_item == data["resource"]:
        slot.inventory_item.charge_current = data["charge_current"]

  // 屬性（Vector2）
  for attribute in player_attributes:
    Vector2 data = player_attributes[attribute]
    player.player_attributes[attribute].set_attribute(data.x, data.y)

  // 位置 / 旋轉 / 姿態
  player.global_position = player_position
  player.body.global_rotation = player_rotation
  player.is_crouching = player.try_crouch = player_try_crouch

  // 特殊狀態（坐姿、碰撞體、節點 Transform）
  load_sitting_state(player)
  load_collision_shapes(player)
  load_node_transforms(player)

  // 互動組件（deferred）
  for state_data in interaction_component_state:
    player.player_interaction_component.set(data, value)
  player.player_interaction_component.set_state.call_deferred()

  player.player_state_loaded.emit()
  fade_in()  // 讀取完成後淡入
```

### 5.3 PlayerInteractionComponent 的 set_state()

**位置**：`PlayerInteractionComponent.gd:372`

```
set_state():
  updated_wieldable_data.emit(null, 0, null)  // 清除 HUD 顯示

  // 清除所有已實例化的 Wieldable 節點
  for leftover in wieldable_container.get_children():
    leftover.queue_free()
  equipped_wieldable_node = null

  // 從 WieldableItemPD 重建 Wieldable 場景
  if is_wielding and equipped_wieldable_item:
    temp_wieldable.is_being_wielded = false
    temp_wieldable.use(get_parent())  // 重新走一遍「裝備」流程

    // 如果手電筒讀取時是開著的，重新打開
    if equipped_wieldable_node.has_method("toggle_on_off") and wieldable_was_on:
      equipped_wieldable_node.toggle_flashlight(wieldable_was_on)
```

---

## 六、場景切換流程（load_next_scene / LoadingScreen）

**位置**：`cogito_scene_manager.gd:438`，`loading_screen.gd`

```
load_next_scene(target, connector_name, passed_slot, load_mode):
  loading_screen = LoadingScene.tscn.instantiate()
  loading_screen.next_scene_path = target
  loading_screen.connector_name = connector_name
  loading_screen.passed_slot = passed_slot
  loading_screen.load_mode = load_mode
  get_tree().root.add_child(loading_screen)
```

### CogitoSceneLoadMode 枚舉

| 值 | 名稱 | 行為 |
|---|---|---|
| 0 | TEMP | 正常場景切換，載入 temp 槽的場景/玩家狀態 |
| 1 | LOAD_SAVE | 讀取存檔，切換後呼叫 `loading_saved_game(passed_slot)` |
| 2 | RESET | 重置場景，忽略所有存讀檔 |

### LoadingScreen 非同步載入流程

```
_ready():
  ResourceLoader.load_threaded_request(next_scene_path)  // 開始背景載入

_process():
  status = ResourceLoader.load_threaded_get_status(next_scene_path)
  if status == THREAD_LOAD_LOADED:
    set_process(false)
    await Timer(forced_delay = 0.5s)  // 防止快速場景閃爍

    current_scene.free()
    new_scene = ResourceLoader.load_threaded_get(path).instantiate()
    root.add_child(new_scene)

    match load_mode:
      LOAD_SAVE (1): CogitoSceneManager.loading_saved_game(passed_slot)
      TEMP (0):      load_scene_state("temp"); load_player_state("temp")
      RESET (2):     (不做任何存讀操作)

    get_tree().current_scene = new_scene
    if connector_name != "":
      new_scene.move_player_to_connector(connector_name)  // 傳送至出口位置
    queue_free()
  else:
    // 更新進度條顯示（remap 到 0~99%）
```

---

## 七、CogitoScene：場景根節點

**位置**：`cogito_scene.gd`

```
CogitoScene (extends Node)
├── connectors : Array[Node3D]   ← 傳送點陣列（依名稱比對）
└── save_temp_on_enter : bool    ← 進入場景時是否自動存 temp
```

**`move_player_to_connector(name)`**：線性掃描 `connectors` 陣列，找到名稱匹配的 Node3D 後直接設定玩家全域位置與旋轉。

**`_enter_tree()`**：
```
CogitoSceneManager._current_scene_root_node = self
if save_temp_on_enter:
  save_scene_state(scene_name, "temp")
  save_player_state(player, "temp")
```
場景進入時自動設定 CSM 的根節點參照，並可選地存 temp 存檔（用於「離開場景時能讀回」）。

---

## 八、CogitoWorldPropertySetter：跨場景全域旗標

**位置**：`world_property_setter.gd`

```
CogitoWorldPropertySetter
├── properties_to_set_ON : Dictionary  ← 收到 true/void 信號時寫入
└── properties_to_set_OFF : Dictionary ← 收到 false 信號時寫入

set_properties(dict):
  for property in dict:
    CogitoSceneManager._current_world_dict[property] = dict[property]
```

全域旗標存於 `CogitoSceneManager._current_world_dict`，隨 `save_player_state` 序列化至 `world_dictionary`，讀取時復原。設計者連接場景事件信號至此組件的 `on_bool_signal` / `on_void_signal`，即可輕易持久化「門被永久開啟」、「NPC 已死亡」等跨場景旗標。

---

## 九、同場景 vs 跨場景讀取

**位置**：`cogito_scene_manager.gd:90`

```
loading_saved_game(passed_slot):
  _player_state = load_state(passed_slot)

  if _current_scene_name == _player_state.player_current_scene:
    // 同一場景：直接讀取
    load_scene_state(player_current_scene, slot)
    load_player_state(player, slot)
  else:
    // 不同場景：先切換再讀取
    load_next_scene(player_current_scene_path, "", slot, CogitoSceneLoadMode.LOAD_SAVE)
    // LoadingScreen 切換後呼叫 loading_saved_game(passed_slot) 再次執行此邏輯
```

---

## 十、完整流程圖

```
【手動存檔】
玩家按 Save
  │
  ├─ save_player_state(player, slot) → _player_state.write_state("temp")
  ├─ save_scene_state(name, slot) → _scene_state.write_state("temp", name)
  └─ copy_temp_saves_to_slot(slot) → temp/ → slot/

【場景切換（含自動儲存）】
玩家走過傳送門
  │
  ├─ (CogitoScene.save_temp_on_enter) 保存當前場景至 temp/
  └─ load_next_scene(target, connector, "temp", TEMP)
       └─ LoadingScreen:
            ├─ 非同步載入新場景 (load_threaded_request)
            ├─ 釋放舊場景 (current_scene.free())
            ├─ 載入 temp 場景狀態 (load_scene_state)
            ├─ 載入 temp 玩家狀態 (load_player_state)
            └─ move_player_to_connector(connector_name)

【讀取存檔】
玩家選 Slot 讀取
  │
  ├─ loading_saved_game(slot)
  │    ├─ [同場景] load_scene_state + load_player_state → fade_in()
  │    └─ [跨場景] load_next_scene(load_mode=LOAD_SAVE)
  │         └─ LoadingScreen → loading_saved_game(slot) 再次執行
  └─ player.player_state_loaded.emit()

【程式退出】
_exit_tree() → delete_temp_saves()
```

---

## 十一、架構設計要點

1. **Resource 直接序列化**：`CogitoPlayerState` 和 `CogitoSceneState` 繼承 `Resource`，利用 Godot 的 `ResourceSaver.save()` / `ResourceLoader.load()` 直接序列化物件圖，無需手寫 JSON 格式

2. **反射式屬性賦值**：`node.set(key, value)` 讓儲存字典直接驅動屬性還原，避免為每種物件撰寫客製化讀取邏輯

3. **Temp 槽緩衝**：寫入總是先進 temp，確認後才複製至最終槽（類似資料庫 commit 機制）

4. **雙層持久化分工**：`"Persist"` 群組的節點可被銷毀並重建（位置可能改變），`"save_object_state"` 群組的節點始終在場景中只需更新狀態——二者分工清晰

5. **Vector2 壓縮屬性**：屬性以 `Vector2(current, max)` 儲存，節省欄位數，且保留最大值讓難度調整後不丟失設定

6. **set_state.call_deferred()**：場景狀態恢復邏輯必須在同一幀完成所有節點實例化後才執行，`call_deferred` 確保執行順序正確
