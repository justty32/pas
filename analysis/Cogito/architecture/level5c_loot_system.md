# Cogito — Level 5C Loot 系統分析

## 一、系統架構概覽

```
LootTable（Resource .tres）
  └─ drops : Array[LootDropEntry]（每筆定義一個可能掉落物）

LootDropEntry（Resource .tres）
  ├─ droptype: NONE / GUARANTEED / CHANCE / QUEST
  ├─ weight: float（加權隨機用）
  ├─ inventory_item: InventoryItemPD
  ├─ quantity_min / quantity_max: int
  ├─ quest_id: int（-1 = 非任務物品）
  └─ quest_item_total_count: int

LootGenerator（Node）   ← 暫時性工具節點，用完即刪
  └─ generate(loot_table, amount) → Array[LootDropEntry]

LootComponent（Node3D）  ← 掛在敵人/物件下，連接死亡信號
  ├─ SpawningLogic.SPAWN_ITEM → 直接散射物品到世界
  └─ SpawningLogic.SPAWN_CONTAINER → 生成戰利品袋（可開啟物品欄）
```

---

## 二、LootDropEntry（掉落定義）

**位置**：`Components/LootTables/LootDropEntry.gd`，繼承 `Resource`

```
class_name LootDropEntry extends Resource

enum DropType { NONE=0, GUARANTEED=1, CHANCE=2, QUEST=4 }

@export var name : String              // 人類可讀標籤
@export var droptype : DropType = 2   // 預設 CHANCE
@export var weight : float = 100.0   // CHANCE 的權重（GUARANTEED 忽略此值）
@export var inventory_item : InventoryItemPD
@export var quantity_min : int = 1
@export var quantity_max : int = 15   // 實際數量在 [min, max] 間隨機
@export var quest_id : int = -1      // -1 = 非任務物品
@export var quest_item_total_count : int = 1  // 任務物品最多允許幾個存在
```

**DropType 說明**：
- `GUARANTEED`：每次必定掉落，不佔 `amount_of_items_to_drop` 配額
- `CHANCE`：加權隨機抽取，佔配額
- `QUEST`：僅在對應任務進行中才有機會掉落，佔配額
- `NONE`：不掉落（警告用，設計者可能忘記設定）

---

## 三、LootTable（掉落表）

**位置**：`Components/LootTables/BaseLootTable.gd`

```
class_name LootTable extends Resource

enum DropType { NONE=0, GUARANTEED=1, CHANCE=2, QUEST=4 }

@export var drops: Array[LootDropEntry] = []
```

LootTable 本身只是一個 `drops` 陣列的容器，以 `.tres` 形式存在 FileSystem 中，可在多個 LootComponent 間共享（多個敵人使用同一張掉落表）。

---

## 四、LootGenerator（掉落邏輯）

**位置**：`InventoryPD/cogito_loot_generator.gd`，繼承 `Node`

### 分組與加權隨機

```
generate(loot_table, amount) → Array[LootDropEntry]:
  _sort_loot_table(loot_table):
    match droptype:
      0 → none[]         // 警告並跳過
      1 → guaranteed[]   // 必定掉落
      2 → chance[]       // 加權抽
      4 → quest[]        // 任務物品
  
  input_array = chance[] + quest[]   // 合併兩組進行抽籤
  output_array = _roll_for_randomized_items(input_array, amount)
  output_array.append_array(guaranteed[])  // 必定掉落附加於後
  
  return output_array
```

### 加權隨機抽取（_roll_for_randomized_items）

```
_roll_for_randomized_items(items, amount):
  var rng = RandomNumberGenerator.new()
  var result = []
  var weights = items.map(func(k): return k.weight)
  var failsafe = 0
  
  while result.size() < amount:
    var winner = items[rng.rand_weighted(weights)]  // Godot 4.3+ 原生加權
    
    // Unique 物品判斷
    if winner.inventory_item.is_unique:
      if not _is_unique_found(winner.inventory_item):
        if not result.has(winner): result.append(winner)
    
    // Quest 物品判斷
    elif winner.quest_id > -1 and winner.droptype == 4:
      if _count_quest_items(winner.inventory_item) < winner.quest_item_total_count:
        if CogitoQuestManager.active.get_ids_from_quests().has(winner.quest_id):
          result.append(winner)
    
    // 普通物品
    else:
      result.append(winner)
    
    failsafe += 1
    if failsafe > 32: break   // 防無限迴圈（如所有物品都是 unique 且已存在）
  
  return result
```

**failsafe 限制**：最多嘗試 32 次，可能導致掉落數量不足。在全部是 unique 且已全部存在的情境下，結果陣列可能為空。

### Unique 物品跨容器掃描（_is_unique_found）

```
_is_unique_found(item):
  掃描「loot_bag」群組 + 「lootable_containers」群組 + 「spawned_loot_items」群組
  + 玩家物品欄
  
  合併所有 InventoryItemPD → 檢查 is_unique 旗標 → 若找到相同 unique 物品 return true
```

跨越玩家背包、所有已生成的戰利品袋、場景中散落的物品，確保真正唯一。

### Quest 物品計數（_count_quest_items）

```
_count_quest_items(item):
  同樣掃描 loot_bag + lootable_containers + spawned_loot_items + 玩家物品欄
  計算 item 在所有位置的累計數量
  
  if 總數 >= quest_item_total_count: 不再掉落
```

---

## 五、LootComponent（觸發橋接）

**位置**：`Components/LootComponent.gd`，繼承 `Node3D`

### 初始化

```
_ready():
  call_deferred("_set_up_references")  // 延後初始化避免場景樹未就緒

_set_up_references():
  _player = get_tree().get_first_node_in_group("Player")
  _player_hud = player.find_child("Player_HUD")
  _player_inventory = player.inventory_data
  
  match spawning_logic:
    SPAWN_ITEM      → health_component.death.connect(_spawn_loot)
    SPAWN_CONTAINER → health_component.death.connect(_spawn_loot_container)
    NONE            → 不連接，組件無效
```

### 模式 A：SPAWN_ITEM（物品散射）

```
_spawn_loot():
  lootgen = LootGenerator.new()
  scene_tree.current_scene.add_child(lootgen)
  items = lootgen.generate(loot_table, amount_of_items_to_drop)
  lootgen.queue_free()  // 用完立刻釋放
  
  for item in items:
    spawned = load(item.inventory_item.drop_scene).instantiate()
    spawned.position = parent_position
    scene_tree.current_scene.add_child(spawned)
    
    // 設定 PickupComponent 數量
    for child in spawned.get_children():
      if child is PickupComponent:
        child.slot_data.quantity = randi_range(item.quantity_min, item.quantity_max)
    
    var impulse = Vector3(randf_range(0,3), 5, randf_range(0,3))
    spawned.apply_central_impulse(impulse)   // 隨機方向炸散
    spawned.add_to_group("spawned_loot_items")
  
  // 更新顯示名稱（附加 "x數量"）
  for item in spawned_items:
    if quantity > 1: item.display_name = "物品名 x" + str(quantity)
```

物品直接散落在場景中，可被玩家撿起，且 `spawned_loot_items` 群組讓 `_is_unique_found()` 能掃描到。

### 模式 B：SPAWN_CONTAINER（戰利品袋）

```
_spawn_loot_container():
  spawned_loot_bag = loot_bag_scene.instantiate()
  spawned_loot_bag.position = parent_position
  scene_tree.current_scene.call_deferred("add_child", spawned_loot_bag)
  
  spawned_loot_bag.toggle_inventory.connect(player_hud.toggle_inventory_interface)
  
  spawned_loot_bag.add_to_group("loot_bag")
  spawned_loot_bag.add_to_group("Persist")   // 確保換場景後重新實例化存檔
  
  inventory_to_populate = spawned_loot_bag.inventory_data
  inventory_to_populate.resource_local_to_scene = true  // 獨立資源，不共享
  
  lootgen.generate(loot_table, amount)
  _populate_the_container(inventory_to_populate, items)
```

戰利品袋以 `CogitolootableContainer` 或 `cogito_container.gd` 實作，加入 `"Persist"` 群組確保存讀檔時重新生成。

### 容器填充（_populate_the_container）

```
_populate_the_container(inventory, items):
  slots.resize(items.size())
  inventory.inventory_size.x = 8
  inventory.inventory_size.y = items.size() / 8 + 1
  
  for i in items.size():
    slots[i] = InventorySlotPD.new()
    slots[i].inventory_item = items[i].inventory_item
    slots[i].quantity = randi_range(items[i].quantity_min, items[i].quantity_max)
    slots[i].origin_index = i
    slots[i].resource_local_to_scene = true
    slots[i].inventory_item.resource_local_to_scene = true
```

`resource_local_to_scene = true` 確保每個戰利品袋的物品資源是獨立的，修改數量不會影響原始 `.tres` 定義。

---

## 六、完整掉落流程

```
【設計階段】
  建立 InventoryItemPD .tres（物品定義）
  建立 LootDropEntry .tres（掉落條目）
  建立 LootTable .tres（掉落表，聚合多條目）
  
  NPC/物件場景中：
    加入 LootComponent 子節點
    設定 loot_table, spawning_logic, amount_of_items_to_drop
    設定 health_component_to_monitor（連接死亡信號）

【遊戲中死亡觸發】
  health_attribute.death.emit()
    → LootComponent._spawn_loot() / _spawn_loot_container()
    → LootGenerator.generate()
      → _sort_loot_table（分三組）
      → _roll_for_randomized_items（加權抽 N 個）
        → unique/quest 物品的跨容器掃描
      → append guaranteed（必定掉落）
    → lootgen.queue_free()
    → SPAWN_ITEM: 實例化 drop_scene，套用隨機數量，炸散
    → SPAWN_CONTAINER: 實例化 loot_bag，填充 inventory slots

【玩家互動（SPAWN_CONTAINER）】
  玩家互動 loot_bag → toggle_inventory 信號
    → toggle_inventory_interface(bag.inventory_data)
    → inventory_interface.set_external_inventory(bag)
    → ExternalInventoryUI.show()
    → 玩家拖拉物品 or 「Take All」
```

---

## 七、設計亮點與問題

### 設計亮點

1. **加權隨機 API**：使用 Godot 4.3+ 原生 `rand_weighted()` 直接接受 `PackedFloat32Array`，不需手寫輪盤演算法
2. **跨容器 unique 掃描**：掃描所有 loot_bag 群組、spawned_loot_items、玩家背包，確保全域唯一性
3. **任務物品感知**：查詢 `CogitoQuestManager.active`，只在任務進行中且未達上限時掉落
4. **resource_local_to_scene**：防止多個容器共享同一 Resource 實例，避免數量修改互相干擾

### 已知問題

| 問題 | 位置 | 影響 |
|---|---|---|
| failsafe 32 次上限 | `cogito_loot_generator.gd:205` | 若所有 unique/quest 物品都已達上限，掉落陣列可能為空（amount 不足） |
| `_count_quest_items` 的相等比較 | line 146 | `_slot == item` 比較的是 Resource 參照，而非 name，可能誤判 |
| 戰利品袋不存讀物品狀態 | LootComponent | 玩家僅取走部分後離場，下次回來物品可能重置（取決於 cogito_scene_state 的實作） |
