# 教學：動態生成場景、物件與 NPC

本教學說明如何在 COGITO 中動態生成物件並確保它們能被存讀檔，涵蓋 `CogitoSpawnZone`、腳本手動生成，以及 NavigationMesh 的動態更新。

本文聚焦「**如何使用與擴充**」。持久化系統的**逐行底層剖析**（`save_scene_state` / `load_scene_state` 的反射還原、temp→slot 暫存機制、字典完整格式）請見 [details/dynamic_generation_implementation.md](../details/dynamic_generation_implementation.md)，本教學僅引用其結論，不重複展開。

> 本專案目標引擎為 **Godot 4.6**（`project.godot:19: config/features=PackedStringArray("4.6", ...)`）。下文涉及 Godot 4 與 Godot 3 行為差異處（如 `BoxShape3D.size`）皆以 4.x 為準。

## 前置知識
- 已閱讀 [Level 4B: 存讀檔完整流程](../architecture/level4_save_load_system.md)（特別是 `Persist` 群組的概念）。
- 動態物件持久化的內部機制：見上述 details 文件。

---

## 一、CogitoSpawnZone 的正確使用

`cogito_spawnzone.gd` **本身就繼承 `Area3D`**（`cogito_spawnzone.gd:1: extends Area3D`），它**就是**生成區節點，不是掛在別的節點上的元件。此腳本**沒有 `class_name`**，且在整個 addon／DemoScenes 中**沒有任何現成場景引用它**——它是一個獨立的工具腳本，要用就自己把它掛到一個 Area3D 上。

### 1.1 節點設定

- `CogitoSpawnZone`（Area3D，掛 `cogito_spawnzone.gd`）
  - `CollisionShape3D`
    - `BoxShape3D` ← 生成範圍（必須是 BoxShape3D，見下方檢查）

在 Inspector 設定（`cogito_spawnzone.gd:3-7`）：

| 欄位 | 類型 | 原始碼 | 說明 |
|---|---|---|---|
| `spawn_area` | `CollisionShape3D` | `:3` | 指向子節點的 CollisionShape3D（其 shape 須為 BoxShape3D）|
| `spawn_amount` | `int`（範圍 1–100）| `:5` | 一次呼叫生成幾個（`@export_range(1,100)`，預設 1）|
| `object_to_spawn` | `PackedScene` | `:7` | **單一**場景（非陣列，每次生成同一種物件）|

`_ready()` 只做一件事——檢查 shape 是否為 BoxShape3D，不是的話僅 `print` 警告、**不會 crash**（`cogito_spawnzone.gd:10-13`）：

```gdscript
func _ready() -> void:
    if !spawn_area.shape.is_class("BoxShape3D"):
        print("spawn area is not a BoxShape3D!")
```

### 1.2 生成邏輯（`cogito_spawnzone.gd:16-28`）

```gdscript
func spawn_objects():
    var left_to_spawn = spawn_amount
    var spawn_point : Vector3 = Vector3.ZERO
    while left_to_spawn > 0:
        spawn_point.x = randf_range(spawn_area.global_position.x - spawn_area.shape.size.x,
                                     spawn_area.global_position.x + spawn_area.shape.size.x)
        # y (:21)、z (:22) 同理
        var spawned_object = object_to_spawn.instantiate()
        spawned_object.position = spawn_point          # 注意：用的是 position（區域本地座標）
        get_tree().current_scene.add_child(spawned_object)  # 直接掛到目前場景根節點下
        left_to_spawn -= 1
```

**重要校正（與 Godot 3 不同）**：在 Godot 4，`BoxShape3D.size` 是盒子的**完整尺寸**（full extents），不是半徑。生成程式用的範圍是 `global_position ± size`，等於 `global_position ± 全尺寸`，所以**實際撒點範圍是盒子可見大小的 2 倍**，物件會散到 BoxShape3D 視覺邊界之外。若想讓生成點落在盒子內，應自行改成 `± size * 0.5`（需繼承後 override `spawn_objects()`，見 1.4）。

另一個細節：`spawned_object.position = spawn_point`（`:25`）設的是**本地座標**，但 `spawn_point` 是用 `spawn_area.global_position`（全域座標）算出來的——只有當生成物的父節點（場景根）位於原點時兩者才一致。若場景根有位移，撒點位置會偏移。

### 1.3 觸發方式

腳本內**已內建一個觸發入口**（`cogito_spawnzone.gd:31-32`）：

```gdscript
func _on_generic_button_pressed() -> void:
    spawn_objects()
```

依此命名慣例，最直接的用法是把 COGITO 的 `GenericButton`（或任何按鈕／拉桿）的「按下」信號連到這個 `_on_generic_button_pressed()`。其他常見觸發法：

```gdscript
# 方式一：場景啟動就生成（在外部腳本或子類）
func _ready():
    $CogitoSpawnZone.spawn_objects()

# 方式二：玩家進入某觸發區
func _on_trigger_area_body_entered(body):
    if body.is_in_group("Player"):
        $CogitoSpawnZone.spawn_objects()

# 方式三：直接連 CogitoSpawnZone 自身的 Area3D 信號（它本身就是 Area3D）
#   在 Inspector 把 body_entered 連到一個自訂處理函數，內部呼叫 spawn_objects()
```

### 1.4 限制與擴充點

| 限制（原始碼依據） | 影響 | 擴充方式 |
|---|---|---|
| 無去重機制：每次呼叫都生成 `spawn_amount` 個（`:17-28`）| 重複觸發會無限堆疊 | 自行用旗標／計數控制呼叫時機 |
| 撒點範圍是盒子 2 倍（`:20-22`，Godot4 `size`=全尺寸）| 物件散出可見盒外 | override `spawn_objects()`，改用 `size * 0.5` |
| 父節點固定為 `get_tree().current_scene`（`:26`）| 無法指定容器 | override `spawn_objects()`，改 `add_child` 目標 |
| 不處理 Persist（腳本完全不碰群組）| 生成物能否存檔取決於物件自身 | 生成物根節點是 `CogitoObject`/`CogitoNPC` 即自動 Persist（見三）|

---

## 二、腳本手動精確生成

需要在特定位置（敵人手部、事件觸發點）生成物件時，封裝一個工具函數即可：

```gdscript
func spawn_at(scene: PackedScene, world_pos: Vector3, world_rot: Vector3 = Vector3.ZERO) -> Node:
    var instance = scene.instantiate()
    get_tree().current_scene.add_child(instance)   # 必須先 add_child 再設 global_*
    instance.global_position = world_pos
    instance.global_rotation = world_rot
    return instance
```

> 順序重點：`global_position` / `global_rotation` 必須在 `add_child()` **之後**設定，否則節點尚未進入場景樹、全域變換無意義。

---

## 三、存讀檔整合（Persist 群組）

> 以下是「使用層」結論。存檔／讀檔的逐行實作（反射還原、`set_state.call_deferred()` 時序、temp→slot）見 [details/dynamic_generation_implementation.md](../details/dynamic_generation_implementation.md) §2–§6。

動態生成的物件要能被存檔，需同時滿足**三個條件**，對應 `save_scene_state()` 的過濾邏輯（`cogito_scene_manager.gd:391-417`）：

| 條件 | 原始碼依據 | 是否需手動處理 |
|---|---|---|
| 1. 在 `"Persist"` 群組中 | 存檔掃描 `get_nodes_in_group("Persist")`（`cogito_scene_manager.gd:391`）| **否**——`CogitoObject._ready()`（`cogito_object.gd:51`）與 `CogitoNPC._ready()`（`cogito_npc.gd:82`）皆自動 `add_to_group("Persist")` |
| 2. `scene_file_path` 非空（必須是從 .tscn 實例化）| `if node.scene_file_path.is_empty(): continue`（`cogito_scene_manager.gd:398-400`）| **是**——務必用 `PackedScene.instantiate()` 生成，純程式碼建立的 `Node3D.new()` 會被**靜默跳過** |
| 3. 實作 `save()` 方法 | `if !node.has_method("save"): continue`（`cogito_scene_manager.gd:402-404`）| **否**——`CogitoObject.save()`（`cogito_object.gd:91`）、`CogitoNPC.save()`（`cogito_npc.gd:187`）已實作 |

### 3.1 讀檔重建流程（重點結論）

讀檔時 `load_scene_state()`（`cogito_scene_manager.gd:322-383`）對 `Persist` 群組做的是「**全清除後重建**」：

1. `get_nodes_in_group("Persist")` 全部 `queue_free()`（`:331-334`）——連 .tscn 裡原本擺好的道具一起刪。
2. 對存檔每筆 `node_data`：`load(node_data["filename"]).instantiate()`（`:338`），再 `get_node(node_data["parent"]).add_child(...)`（`:339-340`）。
3. 套用 `position` / `rotation`（`:343-344`），其餘鍵用 `new_object.set(data, ...)` 反射還原（`:352-355`）。
4. 若有 `set_state()` 方法 → `set_state.call_deferred()`（`:362-363`，延後到場景樹就緒）。

關鍵後果：**`parent` 路徑（`get_parent().get_path()`，見 `cogito_object.gd:97` / `cogito_npc.gd:195`）在讀檔時必須仍然有效**。所以生成物的父節點要是「**場景裡靜態存在的節點**」，不能是另一個也會被 `queue_free()` 的動態物件。

### 3.2 `save()` 不存節點名稱——命名衝突風險

`CogitoObject.save()`（`cogito_object.gd:91-119`）與 `CogitoNPC.save()`（`cogito_npc.gd:187-206`）的字典**只存 `filename`、`parent`、`pos_*`、`rot_*` 等**，**不存節點 `name`**。讀檔時 `add_child(new_object)` 用的是 .tscn 的預設根名稱。當同一父節點下要掛多個同名實例時，Godot 會自動把名稱改成 `Name`, `@Name@2`…——這通常無害（因為不靠 name 索引），但若你**自訂的 `set_state()` 或外部腳本是用固定 name 去 `get_node` 找這個物件，就會找不到**。建議生成時就給唯一名稱：

```gdscript
# 動態生成 + 確保可存檔的標準寫法
func spawn_persistent_object(scene: PackedScene, parent: Node, pos: Vector3) -> Node:
    var obj = scene.instantiate()                      # 條件2：從 .tscn 實例化
    parent.add_child(obj)                              # 父節點須為「靜態存在」節點
    obj.name = scene.resource_path.get_file().get_basename() + "_" + str(obj.get_instance_id())
    obj.global_position = pos
    # 條件1、3 由 CogitoObject/CogitoNPC 的 _ready()/save() 自動滿足
    return obj
```

### 3.3 自訂要存的欄位

要存額外狀態（血量、警戒等級）時，繼承 `CogitoObject`／`CogitoNPC` 後 override `save()`，先呼叫 `super.save()` 再塞自訂鍵；對應欄位在腳本中必須是**真實存在的變數**，讀檔時 `set()` 反射才還原得回去（`cogito_scene_manager.gd:352-355`）：

```gdscript
# my_enemy.gd  extends CogitoObject
func save() -> Dictionary:
    var data = super.save()
    data["current_hp"] = $CogitoHealthAttribute.value_current
    data["alert_level"] = alert_level   # alert_level 必須是本腳本的成員變數
    return data
```

複雜重建邏輯（重連巡邏路徑等）放進 override 的 `set_state()`。可參考 `CogitoNPC.set_state()`（`cogito_npc.gd:179-183`）的範例：它在還原後 `load_patrol_points()` 並 `npc_state_machine.goto(saved_enemy_state)`。

---

## 四、生成 + 持久化資料流（Mermaid）

```mermaid
flowchart TD
    subgraph 生成階段
        A[呼叫 spawn_objects() / spawn_persistent_object]
        A --> B[PackedScene.instantiate()]
        B --> C[加到「靜態」父節點 add_child]
        C --> D[CogitoObject/NPC._ready()<br/>add_to_group Persist]
    end

    subgraph 存檔階段 save_scene_state
        E[get_nodes_in_group Persist]
        E --> F{scene_file_path<br/>非空?}
        F -- 否 --> X[跳過: 純程式碼節點]
        F -- 是 --> G{有 save()?}
        G -- 否 --> X
        G -- 是 --> H[node.save() 取得字典<br/>filename/parent/pos/rot/...]
        H --> I[寫入 _scene_state.saved_nodes]
    end

    subgraph 讀檔階段 load_scene_state
        J[queue_free 所有 Persist 節點]
        J --> K[load filename .instantiate]
        K --> L[get_node parent .add_child]
        L --> M[還原 pos/rot + set 反射還原其餘鍵]
        M --> N[set_state.call_deferred]
    end

    D -.下次存檔.-> E
    I -.寫檔/讀檔.-> J
```

對應原始碼：生成 `cogito_spawnzone.gd:16-28`；Persist 註冊 `cogito_object.gd:51` / `cogito_npc.gd:82`；存檔過濾 `cogito_scene_manager.gd:391-417`；讀檔重建 `cogito_scene_manager.gd:322-363`。

---

## 五、端到端步驟：做一個「可存讀檔的生成區」

目標：玩家按下按鈕生成幾個可被撿起的道具，存檔離開再讀檔，道具仍在原位。

1. **建立靜態容器**：在主場景根下新增一個 `Node3D`，命名為 `SpawnContainer`。它在 .tscn 中就存在 → 讀檔時 `get_node("…/SpawnContainer")` 必定有效（解決 §3.1 的 parent 路徑問題）。
2. **準備生成物**：用一個根節點是 `CogitoObject`（或其子類）的 `.tscn`（例如 demo 中的可撿道具）。確認它是 `PackedScene`，這樣才有 `scene_file_path`（滿足條件 2）。
3. **建立生成區**：新增 `Area3D`，掛上 `cogito_spawnzone.gd`；其下放 `CollisionShape3D` + `BoxShape3D`。在 Inspector 把 `spawn_area` 指到該 CollisionShape3D、`object_to_spawn` 指到步驟 2 的 .tscn、`spawn_amount` 設為 3。
4. **改掛到容器（建議）**：因為內建 `spawn_objects()` 固定 `add_child` 到場景根（`cogito_spawnzone.gd:26`），若要掛到 `SpawnContainer`，寫個子類 override，或在外部生成腳本改用 §3.2 的 `spawn_persistent_object(scene, $SpawnContainer, pos)`。
5. **接觸發**：把 `GenericButton` 的按下信號連到生成區的 `_on_generic_button_pressed()`（`cogito_spawnzone.gd:31`）。
6. **驗證**：進遊戲 → 按按鈕生成 → 存檔 → 退出 → 讀檔。道具應在原位（因滿足三條件且父節點靜態）。

---

## 六、動態更新 NavigationMesh

動態生成的大型障礙物會讓既有 NavigationMesh 過期，導致 NPC 卡牆。Godot 4 執行期**不會自動**重烘焙。

> 下列 `NavigationRegion3D.bake_navigation_mesh()`、`bake_finished` 信號為 **Godot 4 引擎 API**（非 COGITO 自有），未在本 addon 內封裝；請以 Godot 官方文件為準。

```gdscript
@onready var nav_region : NavigationRegion3D = $NavigationRegion3D

func spawn_wall_and_update_nav(wall_prefab: PackedScene, pos: Vector3) -> void:
    var wall = wall_prefab.instantiate()
    add_child(wall)
    wall.global_position = pos

    await get_tree().process_frame          # 等一幀讓節點完成進樹
    nav_region.bake_navigation_mesh()       # 重新烘焙（CPU 密集，勿每幀呼叫）
```

**效能**：生成大量障礙後**統一烘焙一次**，不要每個物件各觸發一次。

---

## 七、程序化生成波次敵人

結合定時器與上述方法的波次系統。死亡偵測用 `CogitoHealthAttribute` 的 `death` 信號（`cogito_health_attribute.gd:7: signal death()`）：

```gdscript
# wave_spawner.gd
extends Node

@export var enemy_scenes : Array[PackedScene] = []   # 多種敵人 .tscn
@export var spawn_points : Array[Marker3D] = []
@export var waves : Array[int] = [3, 5, 8]
@export var spawn_container_path : NodePath          # 指向場景靜態容器

var current_wave : int = 0
var active_enemies : Array[Node] = []

func start_next_wave() -> void:
    if current_wave >= waves.size():
        return
    var count = waves[current_wave]
    current_wave += 1
    var container = get_node(spawn_container_path)
    for i in count:
        var scene = enemy_scenes[randi() % enemy_scenes.size()]
        var point = spawn_points[randi() % spawn_points.size()]
        var enemy = spawn_persistent_object(scene, container, point.global_position)  # §3.2
        active_enemies.append(enemy)

        # 用「型別」過濾找 CogitoHealthAttribute（find_children 第二參數=class，第三=遞迴）
        var health_nodes = enemy.find_children("", "CogitoHealthAttribute", true, false)
        if health_nodes.size() > 0:
            health_nodes[0].death.connect(_on_enemy_died.bind(enemy))

func _on_enemy_died(enemy: Node) -> void:
    active_enemies.erase(enemy)
    if active_enemies.is_empty():
        await get_tree().create_timer(5.0).timeout
        start_next_wave()
```

> **校正**：用 `find_children("", "CogitoHealthAttribute", true, false)`（**型別**過濾），而非 `find_child("CogitoHealthAttribute")`——後者比對的是**節點名稱**，除非剛好有節點叫這名字才會命中。`CogitoNPC` 本身並未持有 health 的 `@onready` 參照（`cogito_npc.gd:47-75` 無此欄位），故須以型別搜尋。

---

## 八、常見陷阱表

| # | 陷阱 | 症狀 | 根因（原始碼） | 解法 |
|---|---|---|---|---|
| 1 | 純程式碼節點不被存檔 | 存讀檔後動態物件消失 | `scene_file_path.is_empty()` 直接跳過（`cogito_scene_manager.gd:398-400`）| 一律用 `PackedScene.instantiate()`，勿用 `Node3D.new()` |
| 2 | 父節點遺失 | 讀檔時 `get_node(parent)` 為 null，物件不掛回 | parent 存的是 `get_parent().get_path()`（`cogito_object.gd:97`），若父也是動態物件，讀檔時已被 `queue_free()`（`:331-334`）| 父節點用 .tscn 中靜態存在的容器 |
| 3 | 撒點散出盒外 | 生成物超出 BoxShape3D 可見範圍 | Godot4 `size`=全尺寸，程式用 `±size`＝2 倍範圍（`cogito_spawnzone.gd:20-22`）| override 改 `± size*0.5` |
| 4 | 重複觸發堆疊 | 物件越生越多 | `spawn_objects()` 無去重（`:16-28`）| 自行控制呼叫次數／旗標 |
| 5 | 自訂欄位讀檔沒還原 | 血量等回到預設 | `set()` 反射靜默失敗：欄位不存在或型別不符（`cogito_scene_manager.gd:352-355`）| 確認是真實成員變數；在 `set_state()` 做型別轉換 |
| 6 | 靠 name 找不到動態物件 | 自訂腳本 `get_node("X")` 失敗 | `save()` 不存 `name`，多實例被自動改名 | 生成時設唯一 name（§3.2）|
| 7 | NPC 生成後卡牆 | 繞不過動態障礙 | Godot 4 不自動重烘焙 NavMesh | 生成後 `nav_region.bake_navigation_mesh()`（§六）|
| 8 | 把 SpawnZone 當元件掛 | 行為異常 | 它本身就是 `Area3D`（`cogito_spawnzone.gd:1`）| 直接當生成區節點用，別掛在別的節點上 |

---

## 九、驗證清單

| 測試項目 | 預期結果 |
|---|---|
| 設好 `spawn_area`/`object_to_spawn`，呼叫 `spawn_objects()` | 生成 `spawn_amount` 個物件，位置在 `global_position ± size` 範圍（注意是 2 倍盒） |
| 生成物根節點是 CogitoObject → 存檔再讀檔 | 物件仍在（滿足 Persist + scene_file_path + save() 三條件） |
| 用 `Node3D.new()` 動態建立節點 → 存讀檔 | 物件消失（被 `scene_file_path.is_empty()` 跳過，符合預期） |
| 生成物父節點設為動態物件 → 存讀檔 | 物件不掛回（parent 路徑失效）；改靜態容器後正常 |
| 生成牆壁後 NPC 卡牆 → 呼叫 `bake_navigation_mesh()` | NPC 能繞行 |
| 波次敵人全部 `death` 觸發 | 5 秒後自動下一波 |
