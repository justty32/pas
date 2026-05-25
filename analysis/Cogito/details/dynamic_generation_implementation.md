# 深入剖析：動態生成與持久化 (Persistence) 實作細節

本文件詳細紀錄 COGITO 如何處理動態生成的物件以及其存讀檔的底層機制，這對於實作隨機地圖或動態敵人系統至關重要。所有代碼均對應實際原始碼行號。

---

## 1. 兩個持久化群組：`Persist` vs `save_object_state`

COGITO 的場景狀態保存使用**兩套不同的機制**，初學者常誤以為只有一個：

| 群組 | 用途 | 存檔行為 | 讀檔行為 |
|---|---|---|---|
| `Persist` | 動態實例化的物件（如撿起前的道具、動態生成的敵人） | 呼叫 `node.save()` 取得字典 | **先刪除**場景中所有 Persist 節點，再從字典中的 `filename` 重新 `instantiate()` |
| `save_object_state` | 場景中靜態存在的物件（如門、拉桿），只需保存其狀態變化 | 呼叫 `node.save()` 取得字典 | **不刪除節點**，直接用 `get_node(path)` 找到現有節點後套用狀態 |

`CogitoObject._ready()` 在 `cogito_object.gd:51` 會自動將所有繼承自它的物件加入 `Persist` 群組：
```gdscript
# cogito_object.gd:49-52
func _ready():
    self.add_to_group("interactable")
    self.add_to_group("Persist")  # 所有 CogitoObject 都自動加入
    find_interaction_nodes()
```

---

## 2. `save_scene_state` 原始碼逐行解析

`cogito_scene_manager.gd:386-434` 的完整存檔邏輯：

```gdscript
func save_scene_state(_scene_name_to_save, slot: String) -> void:
    # --- 處理 Persist 群組 ---
    var save_nodes = get_tree().get_nodes_in_group("Persist")
    
    _scene_state.clear_saved_nodes()  # 清除上次存檔資料
    
    for node in save_nodes:
        # 驗證 1：必須是從 .tscn 實例化的節點（有 scene_file_path）
        # 若是純程式碼建立的節點，讀檔時無法 load(path) 重建，直接跳過
        if node.scene_file_path.is_empty():
            continue

        # 驗證 2：必須實作 save() 函數
        if !node.has_method("save"):
            continue
            
        # 特殊處理：RigidBody3D 額外保存物理速度
        if node is RigidBody3D:
            var node_data = node.save()
            node_data["linear_velocity_x"] = node.linear_velocity.x
            node_data["linear_velocity_y"] = node.linear_velocity.y
            node_data["linear_velocity_z"] = node.linear_velocity.z
            node_data["angular_velocity_x"] = node.angular_velocity.x
            node_data["angular_velocity_y"] = node.angular_velocity.y
            node_data["angular_velocity_z"] = node.angular_velocity.z
            _scene_state.add_node_data_to_array(node_data)
        else:
            _scene_state.add_node_data_to_array(node.save())
    
    # --- 處理 save_object_state 群組 ---
    var state_nodes = get_tree().get_nodes_in_group("save_object_state")
    _scene_state.clear_saved_states()
    for node in state_nodes:
        if !node.has_method("save"):
            continue
        _scene_state.add_state_data_to_array(node.save())  # 存入不同的陣列
        
    _scene_state.write_state(slot, _scene_name_to_save)
    # 注意：寫入的是 "temp" slot，之後再 copy_temp_saves_to_slot()
```

---

## 3. `load_scene_state` 原始碼逐行解析

`cogito_scene_manager.gd:322-383` 的完整讀檔邏輯：

```gdscript
func load_scene_state(_scene_name_to_load: String, slot: String) -> void:
    if _scene_state and _scene_state.state_exists(slot, _scene_name_to_load):
        _scene_state = _scene_state.load_state(slot, _scene_name_to_load)
        
        # === 第一步：清除現有 Persist 節點（避免重複）===
        var save_nodes = get_tree().get_nodes_in_group("Persist")
        for i in save_nodes:
            i.queue_free()  # 全部刪除，包含初始場景放置的道具
            
        # === 第二步：從存檔資料重新實例化 ===
        var array_of_node_data = _scene_state.saved_nodes
        for node_data in array_of_node_data:
            var new_object = load(node_data["filename"]).instantiate()
            
            # 掛回原本的父節點（用路徑字串）
            if get_node(node_data["parent"]):
                get_node(node_data["parent"]).add_child(new_object)
                
            new_object.position = Vector3(node_data["pos_x"], node_data["pos_y"], node_data["pos_z"])
            new_object.rotation = Vector3(node_data["rot_x"], node_data["rot_y"], node_data["rot_z"])
            
            # RigidBody3D 恢復物理速度
            if new_object is RigidBody3D:
                new_object.linear_velocity = Vector3(
                    node_data["linear_velocity_x"],
                    node_data["linear_velocity_y"],
                    node_data["linear_velocity_z"]
                )
                
            # 套用所有其他自訂屬性（除了已處理的固定鍵）
            for data in node_data.keys():
                if data in ["filename", "parent", "pos_x", "pos_y", "pos_z",
                            "rot_x", "rot_y", "rot_z", "item_charge"]:
                    continue
                new_object.set(data, node_data[data])  # 用反射設定屬性
                
            # 若有 set_state()，延遲呼叫（等場景樹初始化完成）
            if new_object.has_method("set_state"):
                new_object.set_state.call_deferred()
        
        # === 第三步：恢復 save_object_state 群組節點狀態 ===
        var array_of_state_data = _scene_state.saved_states
        for state_data in array_of_state_data:
            # 不重新實例化，直接找到現有節點
            var node_to_set = get_node(state_data["node_path"])
            node_to_set.position = Vector3(state_data["pos_x"], state_data["pos_y"], state_data["pos_z"])
            node_to_set.rotation = Vector3(state_data["rot_x"], state_data["rot_y"], state_data["rot_z"])
            for data in state_data.keys():
                if data in ["filename", "parent", "pos_x", "pos_y", "pos_z", "rot_x", "rot_y", "rot_z"]:
                    continue
                node_to_set.set(data, state_data[data])
            if node_to_set.has_method("set_state"):
                node_to_set.set_state()  # 注意：此處不使用 call_deferred
```

**關鍵差異**：`Persist` 節點讀檔用 `set_state.call_deferred()`（等待 `add_child` 完成），`save_object_state` 節點用 `set_state()`（節點已在場景樹中，立即呼叫安全）。

---

## 4. `CogitoObject.save()` 完整字典格式

`cogito_object.gd:91-119` 的實際回傳字典：

```gdscript
func save():
    if self.is_in_group("spawned_loot_items"):
        spawned_loot_item = true
        
    var node_data = {
        "filename": get_scene_file_path(),          # res://path/to/scene.tscn
        "parent": get_parent().get_path(),           # /root/Scene/SpawnContainer
        "interaction_nodes": interaction_nodes,      # 互動組件陣列（序列化用）
        "pos_x": position.x,
        "pos_y": position.y,
        "pos_z": position.z,
        "rot_x": rotation.x,
        "rot_y": rotation.y,
        "rot_z": rotation.z,
        "spawned_loot_item": spawned_loot_item,      # 是否來自戰利品生成
    }
    
    # 若父節點是 RigidBody3D，額外加入速度（注意：CSM 也會補上，這裡是 fallback）
    var rigid_body = find_rigid_body()
    if rigid_body:
        node_data["linear_velocity_x"] = rigid_body.linear_velocity.x
        # ... 其餘速度分量
    
    return node_data
```

**自訂擴充方式**：繼承 `CogitoObject` 後 override `save()`，先呼叫 `super.save()` 再加入自訂鍵值：

```gdscript
# my_enemy.gd extends CogitoObject
func save() -> Dictionary:
    var data = super.save()
    data["current_hp"] = health_attribute.value_current
    data["alert_level"] = _alert_level
    data["patrol_index"] = _patrol_index
    return data
```

讀檔時 `set()` 反射會自動恢復 `current_hp`、`alert_level`、`patrol_index`，前提是腳本中有這些變數。

---

## 5. `CogitoObject.set_state()` 的作用

`cogito_object.gd:70-77`：

```gdscript
func set_state():
    find_cogito_properties()     # 重新掃描 CogitoProperties 子節點
    
    if spawned_loot_item:
        add_to_group("spawned_loot_items")  # 恢復「戰利品」群組標記
```

預設的 `set_state()` 很精簡——主要目的是讓 `CogitoProperties`（物理反應、燃燒等特殊屬性）重新連接。若繼承後有更複雜的初始化需求（例如 NPC 恢復巡邏路線），在子類 override：

```gdscript
func set_state():
    super.set_state()
    # 恢復 NPC 特有狀態（patrol_index 已透過 set() 反射恢復）
    _move_to_patrol_point(patrol_index)
    if alert_level > 2:
        npc_state_machine.goto("alert")
```

---

## 6. 存檔的暫存機制（temp → slot）

`cogito_scene_manager.gd:573-582` 顯示自動存檔流程：

```gdscript
func _save_autosave_state() -> void:
    _current_scene_name = get_tree().get_current_scene().get_name()
    _current_scene_path = get_tree().current_scene.scene_file_path
    
    save_player_state(_current_player_node, CogitoGlobals.cogito_settings.auto_save_name)
    save_scene_state(_current_scene_name, CogitoGlobals.cogito_settings.auto_save_name)
    
    # copy_temp_saves_to_slot 將「其他場景的舊存檔」一起合併進 slot
    copy_temp_saves_to_slot(CogitoGlobals.cogito_settings.auto_save_name)
```

存檔流程：`save_player_state()` 和 `save_scene_state()` 都先寫到 `user://temp/` 目錄，再由 `copy_temp_saves_to_slot()` 複製到正式 slot 目錄。這保證了「跨場景存檔」的完整性：即使玩家在 B 場景存檔，A 場景的存檔資料不會遺失（先複製 A 到 temp，再把 B 寫入 temp，最後整個 temp 複製到 slot）。

**實際檔案路徑格式**：
```
user://A/cogito_scene_state_MainScene.res   ← 場景存檔（slot A）
user://A/cogito_player_state.res            ← 玩家存檔（slot A）
user://temp/cogito_scene_state_MainScene.res ← 過渡暫存
```

---

## 7. 動態生成完整實作範例

以「隨機刷怪點」為例，讓生成的敵人能被存讀檔：

```gdscript
# EnemySpawner.gd - 掛在場景中的靜態節點
extends Node3D

@export var enemy_scene: PackedScene
@export var max_enemies: int = 3
@export var spawn_container_path: NodePath  # 指向場景中靜態存在的容器節點

var _spawn_container: Node3D


func _ready() -> void:
    # 取得靜態父容器（讀檔後此節點保證存在）
    _spawn_container = get_node(spawn_container_path)


func spawn_enemy(at_position: Vector3) -> Node:
    var enemy = enemy_scene.instantiate()
    
    # 1. 掛到靜態容器下（保證讀檔時 parent path 有效）
    _spawn_container.add_child(enemy)
    
    # 2. 賦予唯一名稱（讀檔時 node_path 用得到）
    enemy.name = "Enemy_%d" % [enemy.get_instance_id()]
    
    # 3. 設定位置
    enemy.global_position = at_position
    
    # CogitoObject._ready() 已自動加入 Persist 群組
    # 確認 enemy_scene 的根節點是 CogitoObject 的子類即可
    
    return enemy
```

**不需要手動呼叫 `add_to_group("Persist")`**，因為 `CogitoObject._ready()` 會自動完成。

---

## 8. `CogitoSpawnZone` 深度解析

`cogito_spawnzone.gd` 完整原始碼：

```gdscript
extends Area3D

@export var spawn_area: CollisionShape3D  # 必須是 BoxShape3D
@export_range(1, 100) var spawn_amount: int = 1
@export var object_to_spawn: PackedScene


func _ready() -> void:
    if !spawn_area.shape.is_class("BoxShape3D"):
        print("spawn area is not a BoxShape3D!")


func spawn_objects():
    var left_to_spawn = spawn_amount
    var spawn_point: Vector3 = Vector3.ZERO
    while left_to_spawn > 0:
        # 在 BoxShape3D 範圍內隨機選點
        spawn_point.x = randf_range(
            spawn_area.global_position.x - spawn_area.shape.size.x,
            spawn_area.global_position.x + spawn_area.shape.size.x
        )
        spawn_point.y = randf_range(
            spawn_area.global_position.y - spawn_area.shape.size.y,
            spawn_area.global_position.y + spawn_area.shape.size.y
        )
        spawn_point.z = randf_range(
            spawn_area.global_position.z - spawn_area.shape.size.z,
            spawn_area.global_position.z + spawn_area.shape.size.z
        )
        
        var spawned_object = object_to_spawn.instantiate()
        spawned_object.position = spawn_point
        get_tree().current_scene.add_child(spawned_object)  # 直接掛在場景根節點下
        
        left_to_spawn -= 1


func _on_generic_button_pressed() -> void:
    spawn_objects()  # 由 GenericButton 的信號觸發
```

**設計限制**：

1. **只接受 BoxShape3D**：`_ready()` 有檢查，若不是 BoxShape3D 只是 print 警告，不會 crash，但 `spawn_area.shape.size` 對非 Box 形狀無效。
2. **父節點固定為場景根節點**：`get_tree().current_scene.add_child(spawned_object)` — 若需要掛到特定容器，須繼承後 override `spawn_objects()`。
3. **Persist 群組由物件自身決定**：`CogitoSpawnZone` 不處理持久化。若 `object_to_spawn` 是 `CogitoObject`，它的 `_ready()` 會自動加入 `Persist`；若是純 Node3D，不會被存檔。
4. **觸發機制**：只有 `_on_generic_button_pressed()` 連接；若要在 `_ready()` 或 Timer 觸發，需自行連接信號或呼叫 `spawn_objects()`。

---

## 9. 常見陷阱與解決方案

### 陷阱 A：父節點遺失（讀檔時 get_node 失敗）

**症狀**：Console 顯示 `get_node(parent_path)` 回傳 null，物件消失。

**根因**：`save()` 存的 `parent` 是 `get_parent().get_path()`，若父節點是另一個動態生成的物件，讀檔時父節點尚未建立。

**解決方案**：所有持久化物件的父節點必須是場景中**靜態存在**的節點（在 `.tscn` 中就存在，不是動態建立的）：
```gdscript
# 建立專用的靜態容器
# 在場景中手動新增：Node3D → 命名 "SpawnContainer"
# 存檔時的 parent 路徑固定為 /root/MyScene/SpawnContainer
```

### 陷阱 B：重複物件（讀檔後場景中有兩份）

**根因**：初始場景（`.tscn`）已放置物件，讀檔時 `load_scene_state` 先 `queue_free()` 所有 Persist 節點，再重新 instantiate。若時序問題（`queue_free` 尚未完成），可能短暫出現重複。

**解決方案**：通常 `queue_free()` 在下一幀才生效，而讀檔的 `for` 迴圈在同一幀執行——此問題較罕見，但若出現，可在 instantiate 前加 `await get_tree().process_frame`。

### 陷阱 C：`set()` 反射失敗（屬性不存在或型別不符）

**根因**：`load_scene_state` 用 `new_object.set(data, node_data[data])` 反射設定屬性，若屬性名稱打錯或型別不符（如存了 `float` 但屬性是 `int`），GDScript 會靜默失敗。

**解決方案**：
```gdscript
# 在 set_state() 中做型別驗證
func set_state():
    super.set_state()
    # 確保型別正確
    _alert_level = int(_alert_level)   # 防止 float→int 問題
```

### 陷阱 D：NavMesh 不更新（動態生成的障礙物）

**根因**：Godot 4 的 Navigation Server 在執行時期不會自動更新已烘焙的 NavMesh。

**解決方案**：若動態生成的物件含有 `NavigationObstacle3D`，或需要重新烘焙：
```gdscript
# 生成障礙物後，強制重新烘焙（只在場景有 NavigationRegion3D 時有效）
func spawn_and_rebake(scene: PackedScene, pos: Vector3) -> void:
    var obj = scene.instantiate()
    obj.global_position = pos
    get_tree().current_scene.add_child(obj)
    
    # 找到場景中的 NavigationRegion3D 並重新烘焙
    var nav_region = get_tree().get_first_node_in_group("nav_region")
    if nav_region:
        nav_region.bake_navigation_mesh()  # 非同步，不阻塞主執行緒
```
