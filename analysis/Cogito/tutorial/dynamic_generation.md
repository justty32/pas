# 教學：動態生成場景、物件與 NPC

本教學說明如何在 COGITO 中動態生成物件並確保它們能被存讀檔，涵蓋 `CogitoSpawnZone`、腳本手動生成，以及 NavigationMesh 的動態更新。

## 前置知識
- 已閱讀 [Level 4B: 存讀檔完整流程](../architecture/level4_save_load_system.md)（特別是 `Persist` 群組的概念）。

---

## 一、CogitoSpawnZone 的正確使用

`cogito_spawnzone.gd` **繼承自 `Area3D`**（`cogito_spawnzone.gd:1: extends Area3D`），因此應作為 Area3D 節點使用，而非掛載在其他節點上。

### 1.1 節點設定

```
CogitoSpawnZone (Area3D + cogito_spawnzone.gd)
└── CollisionShape3D
    └── BoxShape3D  ← 生成範圍
```

在 Inspector 設定（`cogito_spawnzone.gd:3-7`）：

| 欄位 | 類型 | 說明 |
|---|---|---|
| `spawn_area` | CollisionShape3D | 指向子節點的 CollisionShape3D |
| `spawn_amount` | int (1-100) | 一次生成幾個 |
| `object_to_spawn` | PackedScene | **單一**場景（非陣列，每次生成同一種物件）|

### 1.2 生成邏輯（`cogito_spawnzone.gd:16-28`）

```gdscript
func spawn_objects():
    var left_to_spawn = spawn_amount
    while left_to_spawn > 0:
        # 在 BoxShape3D 範圍內隨機選點
        spawn_point.x = randf_range(spawn_area.global_position.x - spawn_area.shape.size.x,
                                     spawn_area.global_position.x + spawn_area.shape.size.x)
        # y, z 同理...
        
        var spawned_object = object_to_spawn.instantiate()
        spawned_object.position = spawn_point
        get_tree().current_scene.add_child(spawned_object)
        left_to_spawn -= 1
```

**注意**：生成點是相對於 `spawn_area.global_position` 計算，但 `BoxShape3D.size` 是**半徑**（即 size = (2,2,2) 代表 4x4x4 的範圍）。

### 1.3 觸發方式

```gdscript
# 方式一：場景 _ready() 時自動生成
# 在另一個腳本或在 CogitoSpawnZone 子腳本中：
func _ready():
    spawn_zone.spawn_objects()

# 方式二：玩家進入觸發區
func _on_trigger_area_body_entered(body):
    if body.is_in_group("Player"):
        spawn_zone.spawn_objects()

# 方式三：連接到 CogitoButton（見 cogito_button.gd）
# 在 CogitoButton 的 was_interacted_with 信號 → spawn_zone.spawn_objects()
```

### 1.4 限制與注意事項

- 每次呼叫 `spawn_objects()` 都會生成新物件，沒有去重機制——需自行控制呼叫時機（避免重複生成）。
- 生成的物件不帶 `Persist` 群組（除非物件場景的腳本自行加入），無法被自動存檔。見下方「存讀檔整合」。

---

## 二、腳本手動精確生成

需要在特定位置（如敵人手部、事件觸發點）生成物件時：

```gdscript
# 建議封裝為工具函數
func spawn_at(scene: PackedScene, world_pos: Vector3, world_rot: Vector3 = Vector3.ZERO) -> Node:
    var instance = scene.instantiate()
    get_tree().current_scene.add_child(instance)
    instance.global_position = world_pos
    instance.global_rotation = world_rot
    return instance


# 生成 NPC 的完整範例
@export var enemy_prefab : PackedScene

func spawn_enemy_at(pos: Vector3) -> void:
    var enemy = spawn_at(enemy_prefab, pos)
    
    # 讓生成的 NPC 能被存檔（關鍵步驟）
    # 方法：確保 enemy_prefab 已是 Persist 群組成員（在 cogito_npc.gd:_ready() 中 add_to_group("Persist")）
    # 並給予唯一名稱避免讀檔時衝突
    enemy.name = "DynamicEnemy_" + str(Time.get_ticks_msec())
```

---

## 三、存讀檔整合（Persist 群組）

動態生成的物件能被存檔的**三個必要條件**（`cogito_scene_manager.gd` 讀取邏輯）：

| 條件 | 說明 |
|---|---|
| 1. 加入 `"Persist"` 群組 | `CogitoObject` 和 `CogitoNPC` 的 `_ready()` 已自動完成 |
| 2. `get_scene_file_path()` 非空 | 物件**必須是從 .tscn 實例化**的（非直接放入場景的孤立節點）|
| 3. 實作 `save()` 方法 | `CogitoObject.save()` 和 `CogitoNPC.save()` 已實作 |

**讀檔重建流程**：
```
存檔時：scan "Persist" group → 每個節點呼叫 save() → 儲存 {filename, parent, pos, rot, ...}

讀檔時：
  對所有 Persist 群組節點 → queue_free()（清除舊實例）
  對存檔資料中每個 entry：
    load(filename).instantiate() → 加入 parent → 設定 pos/rot → 呼叫 set_state()
```

**重要**：若動態生成的物件名稱與場景內建的固定節點名稱重複，讀檔時 `add_child()` 會因節點名稱衝突而改變名稱，導致 `parent` 路徑失效。**務必使用 `Time.get_ticks_msec()` 或 UUID 確保唯一名稱**。

```gdscript
# 動態生成 + 確保可存檔的標準寫法
func spawn_persistent_object(scene: PackedScene, pos: Vector3) -> Node:
    var obj = scene.instantiate()
    obj.name = scene.resource_path.get_basename().get_file() + "_" + str(Time.get_ticks_msec())
    get_tree().current_scene.add_child(obj)
    obj.global_position = pos
    # obj 的腳本（CogitoObject 或 CogitoNPC）會在 _ready() 中自動加入 Persist 群組
    return obj
```

---

## 四、動態更新 NavigationMesh

動態生成的大型障礙物或新房間板塊會讓現有的 NavigationMesh 過期，導致 NPC 卡牆。

### 4.1 場景設定

確保場景根節點下有 `NavigationRegion3D`，且 `NavigationMesh` 資源已烘焙好基礎地圖。

```gdscript
@onready var nav_region : NavigationRegion3D = $NavigationRegion3D

func spawn_wall_and_update_nav(pos: Vector3) -> void:
    # 先生成障礙物
    var wall = wall_prefab.instantiate()
    add_child(wall)
    wall.global_position = pos
    
    # 等待一幀讓物件完成添加後再重新烘焙
    await get_tree().process_frame
    
    # 非同步烘焙（Godot 4 支援，不阻塞主線程）
    nav_region.bake_navigation_mesh(true)  # true = 非同步
    # 連接完成信號若需要後處理
    if not nav_region.bake_finished.is_connected(_on_nav_bake_finished):
        nav_region.bake_finished.connect(_on_nav_bake_finished)


func _on_nav_bake_finished() -> void:
    print("NavigationMesh 重新烘焙完成")
    # NPC 的 NavigationAgent3D 會自動使用新的地圖
```

**效能注意**：重新烘焙費時且 CPU 密集，避免每幀呼叫。建議在生成大量物件後統一烘焙一次，而不是每個物件生成後各自觸發。

---

## 五、程序化生成波次敵人

結合定時器與上述方法，實現波次生成系統：

```gdscript
# wave_spawner.gd
extends Node

@export var enemy_scenes : Array[PackedScene] = []  # 多種敵人
@export var spawn_points : Array[Marker3D] = []     # 出現點
@export var waves : Array[int] = [3, 5, 8]          # 每波敵人數量

var current_wave : int = 0
var active_enemies : Array[Node] = []


func start_next_wave() -> void:
    if current_wave >= waves.size():
        print("所有波次結束！")
        return
    
    var count = waves[current_wave]
    current_wave += 1
    
    for i in count:
        var scene = enemy_scenes[randi() % enemy_scenes.size()]
        var point = spawn_points[randi() % spawn_points.size()]
        var enemy = spawn_persistent_object(scene, point.global_position)
        active_enemies.append(enemy)
        
        # 監聽死亡信號
        var health = enemy.find_child("CogitoHealthAttribute")
        if health:
            health.death.connect(_on_enemy_died.bind(enemy))
    
    print("波次 %d 開始，%d 個敵人" % [current_wave, count])


func _on_enemy_died(enemy: Node) -> void:
    active_enemies.erase(enemy)
    if active_enemies.is_empty():
        print("本波清空！準備下一波...")
        await get_tree().create_timer(5.0).timeout
        start_next_wave()
```

---

## 六、驗證清單

| 測試項目 | 預期結果 |
|---|---|
| 呼叫 `spawn_objects()`，物件出現在 BoxShape 範圍內 | 物件位置均在設定的空間內 |
| 動態生成物件後存檔再讀檔 | 物件仍在（前提：物件是從 .tscn 實例化且加入了 Persist 群組）|
| 生成兩個同名動態物件後存讀檔 | 注意衝突警告；使用時間戳命名可避免 |
| 生成牆壁後 NPC 卡在牆邊 | 呼叫 `bake_navigation_mesh(true)` 後 NPC 能繞行 |
| 波次敵人全部死亡 | 5 秒後自動觸發下一波 |
