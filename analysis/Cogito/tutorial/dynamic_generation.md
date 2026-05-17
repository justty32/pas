# 教學：動態生成場景、物件與 NPC

在沉浸模擬或生存遊戲中，動態生成敵人、隨機掉落物或程序化地圖是常見需求。本教學涵蓋如何使用 COGITO 內建工具與腳本來生成這些元素，並確保它們能被正確存檔。

## 前置知識
- 已閱讀 [Level 4B: 存讀檔完整流程](../architecture/level4_save_load_system.md) (特別是 `Persist` 群組的概念)。
- 瞭解 Godot 的 `preload()` 與 `instantiate()`。

## 實作步驟

### 1. 使用 CogitoSpawnZone 進行區域隨機生成
COGITO 提供了一個非常方便的組件用於生成戰利品或敵人：
1. 在場景中建立一個 `Area3D` 或 `Node3D`，掛載 `addons/cogito/Scripts/cogito_spawnzone.gd`。
2. 添加一個 `BoxShape3D` 節點作為其子節點（定義生成的空間範圍）。
3. 在 Inspector 中設定 `Objects To Spawn` (PackedScene 陣列) 與 `Amount` (數量)。
4. 呼叫 `spawn_objects()` 方法（可透過按鈕、進入房間觸發、或是透過 `_ready()` 自動執行）。

### 2. 透過腳本精確動態生成 (如：掉落物、自訂敵人)
若要在特定位置（例如敵人的手部，或特定座標）動態生成物件：
```gdscript
@export var enemy_prefab : PackedScene

func spawn_boss(spawn_position: Vector3):
    var new_boss = enemy_prefab.instantiate()
    get_tree().get_current_scene().add_child(new_boss)
    new_boss.global_position = spawn_position
    
    # 關鍵：若是透過腳本動態生成的物件且需要被存檔，
    # 必須賦予一個獨一無二的名稱，並加入 Persist 群組！
    new_boss.name = "Boss_" + str(Time.get_ticks_msec())
    new_boss.add_to_group("Persist")
```

### 3. 動態生成的存讀檔相容性
- **Persist 群組**：COGITO 的 `CogitoSceneManager` 在存檔時，會掃描所有 `Persist` 群組內的節點，呼叫其 `save()` 方法。讀檔時，若場景原本沒有該節點，管理器會嘗試透過保存的 `filename` (PackedScene 路徑) 重新 `instantiate()` 它。
- **獨特命名**：如果生成的物件名稱與場景內建的物件重複，讀檔時會產生衝突。務必確保動態生物/物件的 `name` 是全域唯一的。

### 4. 更新 NavigationMesh (針對 NPC)
如果您動態生成了會阻擋路徑的「大型障礙物」，或是拼接了新的房間板塊，NPC 會因為舊的導航網格而撞牆。
1. 確保您的地圖包覆在一個 `NavigationRegion3D` 下。
2. 生成物件後，呼叫烘焙函數：
   ```gdscript
   @onready var nav_region = $NavigationRegion3D
   
   func spawn_wall():
       # ... 生成牆壁的邏輯 ...
       # 重新烘焙導航網格
       nav_region.bake_navigation_mesh(false)
   ```
   *(註：Godot 4 支援非同步烘焙 `bake_navigation_mesh(true)`，可避免遊戲卡頓。)*

## 驗證方式
1. 使用 `CogitoSpawnZone` 在房間內隨機生成三個補血藥。
2. 撿起其中一個。
3. 儲存遊戲，然後重新讀取。
4. 驗證地上的補血藥數量是否仍為兩個，且位置與存檔前完全一致（確認 Persist 群組與序列化運作正常）。
