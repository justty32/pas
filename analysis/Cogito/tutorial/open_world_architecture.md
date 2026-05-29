# 系統架構：如何使用 COGITO 製作開放世界遊戲

COGITO 的 `CogitoSceneManager` 設計為「畫面過場載入」模式。本教學說明如何擴充至支援無縫區塊串流的開放世界，並整合 COGITO 原有的存讀檔機制。

## 前置知識
- 已閱讀 [Level 4B: 存讀檔完整流程](../architecture/level4_save_load_system.md)。
- 已完成 [教學：LOD 實作](./lod_implementation.md)。

---

## 一、浮點數精度問題（Double Precision）

開放世界地圖若超過約 5km，距離原點過遠的物件會出現物理抖動（Jitter），因為 32-bit float 在大數值下精度不足。

**解決方案**：使用 Godot 的 double precision 建置版本：
```
Godot 官網下載頁 → 選擇 "double precision" 版本的 editor 和 export templates
```
無需修改程式碼，引擎自動使用 64-bit float 計算物理與位置。

**替代方案（不換建置版本）**：「Origin Rebasing」——當玩家距離原點超過一定距離，將所有物件相對玩家偏移，讓玩家始終接近原點：
```gdscript
# origin_rebasing.gd (Autoload)
extends Node

const REBASING_THRESHOLD := 1000.0

func _process(_delta: float) -> void:
    var player = CogitoSceneManager._current_player_node
    if not player:
        return
    if player.global_position.length() > REBASING_THRESHOLD:
        var offset = player.global_position
        for node in get_tree().get_nodes_in_group("persistent_world"):
            node.global_position -= offset
        player.global_position = Vector3.ZERO
```

---

## 二、區塊管理器（ChunkManager Autoload）

建立 `res://scripts/chunk_manager.gd`，在 **Project Settings → Autoload** 加入（名稱：`ChunkManager`）：

```gdscript
# res://scripts/chunk_manager.gd
extends Node

## 每個 Chunk 的邊長（公尺）
@export var chunk_size : float = 500.0
## 載入半徑（Chunk 數量，建立 2*radius+1 × 2*radius+1 的九宮格）
@export var load_radius : int = 1

## Chunk 場景路徑格式，{x} 和 {z} 會被替換
@export var chunk_path_format : String = "res://Maps/Chunk_{x}_{z}.tscn"
## 目前已載入的 Chunk：Vector2i(chunk_x, chunk_z) → Node
var loaded_chunks : Dictionary = {}
var _loading_queue : Array[Vector2i] = []
var _player : Node3D = null


func _ready() -> void:
    # 延遲取得玩家，等待場景初始化
    call_deferred("_init_player")


func _init_player() -> void:
    _player = CogitoSceneManager._current_player_node


func _process(_delta: float) -> void:
    if not _player:
        _player = CogitoSceneManager._current_player_node
        return

    var player_chunk = _world_to_chunk(_player.global_position)
    _update_chunks(player_chunk)
    _process_loading_queue()


func _world_to_chunk(world_pos: Vector3) -> Vector2i:
    return Vector2i(
        floori(world_pos.x / chunk_size),
        floori(world_pos.z / chunk_size)
    )


func _update_chunks(center: Vector2i) -> void:
    # 計算需要載入的 Chunk 集合
    var needed := {}
    for dx in range(-load_radius, load_radius + 1):
        for dz in range(-load_radius, load_radius + 1):
            var coord := center + Vector2i(dx, dz)
            needed[coord] = true

    # 載入新增的 Chunk
    for coord: Vector2i in needed:
        if not loaded_chunks.has(coord) and coord not in _loading_queue:
            if _chunk_file_exists(coord):
                _loading_queue.append(coord)
                _request_async_load(coord)

    # 卸載離開範圍的 Chunk
    for coord: Vector2i in loaded_chunks.keys():
        if not needed.has(coord):
            _unload_chunk(coord)


func _chunk_file_exists(coord: Vector2i) -> bool:
    var path = chunk_path_format.replace("{x}", str(coord.x)).replace("{z}", str(coord.y))
    return ResourceLoader.exists(path)


func _request_async_load(coord: Vector2i) -> void:
    var path = chunk_path_format.replace("{x}", str(coord.x)).replace("{z}", str(coord.y))
    ResourceLoader.load_threaded_request(path)
    CogitoGlobals.debug_log(true, "ChunkManager", "Requesting load: " + path)


func _process_loading_queue() -> void:
    if _loading_queue.is_empty():
        return

    var coord = _loading_queue[0]
    var path = chunk_path_format.replace("{x}", str(coord.x)).replace("{z}", str(coord.y))
    var progress := []
    var status = ResourceLoader.load_threaded_get_status(path, progress)

    if status == ResourceLoader.THREAD_LOAD_LOADED:
        _loading_queue.pop_front()
        _instantiate_chunk(coord, ResourceLoader.load_threaded_get(path))
    elif status == ResourceLoader.THREAD_LOAD_FAILED:
        _loading_queue.pop_front()
        push_warning("ChunkManager: 載入失敗 " + path)


func _instantiate_chunk(coord: Vector2i, scene: PackedScene) -> void:
    var instance = scene.instantiate()
    instance.name = "Chunk_%d_%d" % [coord.x, coord.y]
    get_tree().current_scene.add_child(instance)
    instance.global_position = Vector3(coord.x * chunk_size, 0, coord.y * chunk_size)
    loaded_chunks[coord] = instance

    # 讀取此 Chunk 的存檔狀態
    _load_chunk_state(coord, instance)
    CogitoGlobals.debug_log(true, "ChunkManager", "Loaded chunk " + str(coord))


func _unload_chunk(coord: Vector2i) -> void:
    var chunk = loaded_chunks.get(coord)
    if not chunk or not is_instance_valid(chunk):
        loaded_chunks.erase(coord)
        return

    # 卸載前儲存此 Chunk 狀態
    _save_chunk_state(coord, chunk)
    chunk.queue_free()
    loaded_chunks.erase(coord)
    CogitoGlobals.debug_log(true, "ChunkManager", "Unloaded chunk " + str(coord))
```

---

## 三、區塊存讀檔整合

COGITO 的 `CogitoSceneManager` 以場景名稱為鍵儲存狀態（`cogito_scene_manager.gd:386`）：
```
user://{slot}/{scene_state_prefix}{scene_name}.res
```

每個 Chunk 可以複用此機制，以 Chunk 名稱為鍵：

```gdscript
## 在 ChunkManager 中加入（接續上方代碼）

func _save_chunk_state(coord: Vector2i, chunk: Node) -> void:
    # 掃描 Chunk 內的 Persist 群組物件
    var chunk_name = "Chunk_%d_%d" % [coord.x, coord.y]
    CogitoSceneManager.save_scene_state(chunk_name, "autosave")
    CogitoGlobals.debug_log(true, "ChunkManager", "Saved state for " + chunk_name)


func _load_chunk_state(coord: Vector2i, _chunk: Node) -> void:
    var chunk_name = "Chunk_%d_%d" % [coord.x, coord.y]
    # 嘗試載入此 Chunk 的歷史狀態
    if CogitoSceneManager._scene_state.state_exists("autosave", chunk_name):
        CogitoSceneManager.load_scene_state(chunk_name, "autosave")
```

**注意**：`CogitoSceneManager.save_scene_state()` 掃描的是全場景的 `Persist` 群組。為了只掃描特定 Chunk，需要在 Chunk 場景中加入標記，或修改 `save_scene_state` 加入 `parent_node` 參數過濾。

---

## 四、地形整合（Terrain3D）

Godot 4 沒有內建地形編輯器。開放世界強烈建議使用 **Terrain3D** 插件（Tokisan Games）：

1. 從 AssetLib 或 GitHub 安裝 Terrain3D。
2. 在場景中添加 `Terrain3D` 節點取代傳統地形 Mesh。
3. **腳步聲整合**（`FootstepSurfaceDetector.gd`）：原本的腳步偵測是掃描 Mesh 的 Surface Material。對 Terrain3D 的混合地形貼圖需要特別處理：

```gdscript
# footstep_surface_detector.gd 的地形擴充
func _get_terrain3d_surface(pos: Vector3) -> String:
    var terrain = get_tree().get_first_node_in_group("Terrain3D")
    if not terrain:
        return "default"
    # Terrain3D 提供 get_texture_id() 方法取得混合權重最高的地表 ID
    var tex_id = terrain.data.get_texture_id(pos)
    match tex_id:
        0: return "grass"
        1: return "dirt"
        2: return "stone"
        _: return "default"
```

---

## 五、Navigation 跨 Chunk 拼接

每個 Chunk 放置獨立的 `NavigationRegion3D`，Godot 4 的 Navigation Server 支援多 Region 自動拼接：

- `Chunk_0_0.tscn`
  - `NavigationRegion3D` ← 烘焙好本 Chunk 範圍的 NavMesh
    - (地形 + 障礙物的碰撞體在此範圍內)

**跨 Chunk 邊緣拼接要求**：相鄰 Chunk 的 NavigationMesh 在邊界處幾何必須重合（通常讓 NavMesh 稍微超出 Chunk 邊界幾公尺）。

Chunk 載入後自動加入 NavigationServer，NPC 的 `NavigationAgent3D` 即可跨 Chunk 尋路。

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 玩家向 +X 移動 500m | Console 顯示 Chunk(1,0) 開始載入 |
| 移入新 Chunk 後 | 舊 Chunk 自動 queue_free，記憶體不累積 |
| 卸載 Chunk 前 | Console 顯示「Saved state for Chunk_X_Z」|
| 重載遊戲後進入同一 Chunk | 掉落物和 NPC 狀態恢復 |
| NPC 追擊玩家跨越 Chunk 邊界 | NPC 不卡住，導航路徑跨越兩個 Region |
