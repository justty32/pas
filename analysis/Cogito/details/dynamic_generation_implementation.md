# 深入剖析：動態生成與持久化 (Persistence) 實作細節

本文件詳細紀錄 COGITO 如何處理動態生成的物件以及其存讀檔的底層機制，這對於實作隨機地圖或動態敵人系統至關重要。

## 1. 持久化核心邏輯：`Persist` 群組

在 COGITO 中，動態生成的物件是否能被存檔，完全取決於它是否屬於 `Persist` 群組。

### 存檔流程 (`save_scene_state`)
當 `CogitoSceneManager` 執行存檔時：
1. **掃描群組**：呼叫 `get_tree().get_nodes_in_group("Persist")` 取得所有持久化節點。
2. **驗證資格**：
    - 檢查 `scene_file_path`：只有從 `.tscn` 實例化出來的節點才能被存檔（否則讀檔時無法 `load()`）。
    - 檢查 `save()` 方法：節點腳本必須實作 `save()` 函數並回傳一個包含位置、旋轉等資訊的字典。
3. **物理保存**：若為 `RigidBody3D`，管理器會自動額外記錄其 `linear_velocity` 與 `angular_velocity`。
4. **寫入磁碟**：將所有節點數據序列化為 JSON。

### 讀檔流程 (`load_scene_state`)
1. **清理舊物**：首先**刪除**當前場景中所有屬於 `Persist` 群組的節點（避免重複）。
2. **實例化新物**：
    - 從 JSON 讀取 `filename` (即路徑)。
    - 使用 `load(path).instantiate()` 重新建立物件。
    - 根據記錄的 `parent` 路徑，將物件重新 `add_child()` 回場景樹。
3. **還原狀態**：
    - 還原 Transform (Pos/Rot)。
    - 若有實作 `set_state()` 方法，則呼叫它以執行自訂的初始化。

---

## 2. 動態生成實作範例

若要實作一個「動態刷怪點」，您的腳本應如下：

```gdscript
# EnemySpawner.gd
extends Node3D

@export var enemy_scene : PackedScene

func spawn_enemy():
    var enemy = enemy_scene.instantiate()
    # 1. 決定父節點：若要存檔，必須確保父節點在讀檔時已存在
    get_tree().current_scene.add_child(enemy)
    
    # 2. 設定位置
    enemy.global_position = self.global_position
    
    # 3. 賦予唯一名稱：讀檔時管理路徑的關鍵
    enemy.name = "DynamicEnemy_" + str(enemy.get_instance_id())
    
    # 4. 加入持久化群組
    enemy.add_to_group("Persist")
```

---

## 3. 避免常見陷阱

### 陷阱 A：父節點遺失
如果動態生成的物件被掛載到另一個也是動態生成的物件下，且後者沒有被正確存檔，則子物件在讀檔時會因為找不到 `parent` 路徑而載入失敗。
- **解決方案**：始終將持久化物件掛載到場景中的靜態節點（如 `NavigationRegion3D` 或一個專門的 `SpawnContainer`）之下。

### 陷阱 B：缺乏 `save()` 函數
如果您的物件加入了 `Persist` 群組但腳本沒寫 `save()`，管理器會直接跳過它。
- **解決方案**：確保繼承自 `CogitoObject` 或手動實作：
```gdscript
func save():
    return {
        "filename" : get_scene_file_path(),
        "parent" : get_parent().get_path(),
        "pos_x" : position.x,
        "pos_y" : position.y,
        # ... 其他自訂屬性 ...
    }
```

### 陷阱 C：NavMesh 不更新
NPC 在動態生成的場景中會「撞牆」。
- **解決方案**：生成物件後呼叫 `NavigationServer3D.map_get_iteration_id(get_world_3d().get_navigation_map())` 觸發地圖更新，或對 `NavigationRegion3D` 呼叫 `bake_navigation_mesh()`。

---

## 4. 進階：`CogitoSpawnZone` 深度解析

`CogitoSpawnZone` (位於 `addons/cogito/Scripts/cogito_spawnzone.gd`) 是一個封裝好的工具：
- **隨機化**：利用 `randf_range` 在 `BoxShape3D` 範圍內隨機生成。
- **效能優化**：它在 `_ready` 或信號觸發時執行，避免在物理幀進行重度計算。
- **限制**：預設的 `CogitoSpawnZone` 生成的物件**不一定**會自動加入 `Persist` 群組，除非預製件 (Prefab) 本身在腳本中就寫了 `add_to_group("Persist")`。
