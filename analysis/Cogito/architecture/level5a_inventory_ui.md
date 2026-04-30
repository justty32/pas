# Cogito — Level 5A 物品欄 UI 系統分析

## 一、系統架構概覽

```
InventoryItemPD（Resource .tres）    ← 物品定義
InventorySlotPD（Resource）          ← 插槽封裝（物品 + 數量 + 位置）
CogitoInventory（Resource）          ← 物品欄資料（槽位陣列 + 快捷槽）
    │
    ├─ inventory_interface.gd（Control）    ← 頂層協調器
    │     ├─ InventoryUI.gd（格子 UI）
    │     │     └─ Slot.gd（SlotPanel，單格）
    │     ├─ hot_bar_inventory.gd（Hotbar）
    │     │     └─ Slot.gd（復用）
    │     └─ CogitoQuickslots（Node）
    │           └─ CogitoQuickslotContainer.gd（單快捷槽）
    │
    └─ ExternalInventoryUI（同 InventoryUI）  ← 外部容器（箱子等）
```

---

## 二、資料模型

### InventoryItemPD（物品定義）

**位置**：`InventoryPD/CustomResources/InventoryItemPD.gd`，繼承 `Resource`

| 欄位 | 類型 | 用途 |
|---|---|---|
| `name` / `description` | String | UI 顯示文字 |
| `icon` | Texture2D | 全尺寸圖示（格子模式會裁切） |
| `item_size` | Vector2 | 格子佔位（如 2×1 = 橫跨兩格） |
| `is_stackable` / `stack_size` | bool/int | 堆疊限制 |
| `is_droppable` / `is_unique` | bool | 丟棄限制 / 唯一物品（Loot 用） |
| `drop_scene` | 路徑 | 丟棄到世界的 Scene |
| `can_auto_slot` / `slot_number` | bool/int | 自動快捷槽設定 |

**格子圖示裁切**（`get_region(x, y)`）：
```
icon 圖片依 item_size 等分，每格取對應區塊
x_chunk = icon.width / item_size.x
region = Rect2i(x * x_chunk, y * y_chunk, x_chunk, y_chunk)
→ 每個 SlotPanel 只顯示自己格位的圖示片段
```

### InventorySlotPD（插槽）

**位置**：`InventoryPD/CustomResources/InventorySlotPD.gd`

```
inventory_item : InventoryItemPD   ← 物品參照
quantity : int                     ← 數量（setter 發射 stack_has_changed）
origin_index : int = -1            ← 格子佔位的「原點格」索引（左上角）
```

**格子物品佔多格的編碼**：一個 2×1 物品放在 index 3，則：
- index 3: `origin_index = 3`
- index 4: `origin_index = 3`（共享）

所有 slot 透過 `origin_index` 識別同一個物品。

**合併判斷**：
```
can_merge_with(other):
  same_item and is_stackable and quantity < stack_size

can_fully_merge_with(other):
  same_item and is_stackable and (quantity + other.quantity) <= stack_size
```

---

## 三、InventoryUI.gd — 格子渲染

**位置**：`InventoryPD/UiScenes/InventoryUI.gd`，繼承 `PanelContainer`

### 全量重建模式（populate_item_grid）

```
set_inventory_data(inventory_data):
  inventory_data.inventory_updated.connect(populate_item_grid)

populate_item_grid(inventory_data):
  for child in grid_container: child.queue_free()   // 清除舊節點
  slot_array.clear()
  grid_container.columns = inventory_data.inventory_size.x
  
  for slot_data in inventory_data.inventory_slots:
    var slot = Slot.instantiate()
    slot.set_slot_data(slot_data, index, false, columns)
    slot.set_hotbar_icon()
  
  override_slot_focus_neighbors()   // 設定上下左右焦點鄰居
  if grid: apply_slot_icon_regions()  // 格子模式：裁切圖示
```

每次 `inventory_updated` 信號觸發時，完整重建所有 SlotPanel 節點。

### 格子模式圖示分割（apply_slot_icon_regions）

```
apply_item_icons(item_data, origin_index):
  for x in item_size.x:
    for y in item_size.y:
      slot_array[origin_index + x + y*columns].set_icon_region(x, y)
```

### 拖放高亮（highlight_slots / count_intersecting_items）

```
highlight_slots(index, highlight):
  highlight_size = grabbed_slot.item_data.item_size
  for all slots in highlight area:
    show/hide selection_panel
  change_slot_colours(count_intersecting_items(index, size))

count_intersecting_items → int:
  -1 = 越界（紅色）
   0 = 空格（綠色）
   1 = 有物品可交換（黃色）
  >1 = 多物品不可放（紅色）
```

### 游標越界偵測（out_of_bounds）

```
out_of_bounds(index, x, y):
  // 超出格子總數
  if index + x + y*columns >= slot_array.size(): return true
  // 行偏移（格子換行問題）
  if int(index/columns) != int((index+x)/columns): return true
```

---

## 四、Slot.gd（SlotPanel）— 單格邏輯

**位置**：`InventoryPD/UiScenes/Slot.gd`，繼承 `PanelContainer`

### 顯示邏輯

```
set_slot_data(slot_data, index, moving, x_size):
  item_data = slot_data.inventory_item
  origin_index = slot_data.origin_index
  
  check_if_top_right_slot → quantity_slot = true  // 數量顯示在右上格
  check_if_bottom_right_slot → ammo_slot = true    // 彈藥顯示在右下格
  
  if quantity > 1 and quantity_slot:
    quantity_label.show()  // 顯示 "x3"
  
  if has charge_changed signal and not no_reload and ammo_slot:
    charge_label.text = str(charge_current)  // 顯示彈藥數
    item_data.charge_changed.connect(_on_charge_changed)  // 響應式更新
```

**數量/彈藥只在「右下角格」顯示**，多格物品不在每格都重複。

### 輸入處理（游標 + 手把）

```
_on_gui_input(event):
  inventory_move_item  → slot_pressed.emit(index, "inventory_move_item")
  inventory_use_item   → slot_pressed.emit(index, "inventory_use_item")
  inventory_drop_item  → slot_pressed.emit(index, "inventory_drop_item")
  inventory_assign_item → slot_pressed.emit(index, "inventory_assign_item")

_on_focus_entered → highlight_slot.emit(index, true) + 音效
_on_mouse_entered → grab_focus()   // 滑鼠移入即自動聚焦（兼容手把導覽）
```

---

## 五、inventory_interface.gd — 頂層協調器

**位置**：`InventoryPD/UiScenes/inventory_interface.gd`

### 開關物品欄

```
open_inventory():
  is_inventory_open = true  // setter 自動 emit inventory_open(true)
  for node in nodes_to_show: node.show()
  hot_bar_inventory.hide()   // 開啟物品欄時隱藏 hotbar
  if gamepad: inventory_ui.slot_array[0].grab_focus.call_deferred()

close_inventory():
  if grabbed_slot_data:  // 若正在拖動，歸還物品
    player.inventory_data.pick_up_slot_data(grabbed_slot_data)
  hot_bar_inventory.show()
```

### 拖放流程（grabbed_slot_data）

`grabbed_slot_data: InventorySlotPD` 是全域拖動狀態：

```
// 拿起物品
grabbed_slot_data = inventory_data.grab_slot_data(index)
grabbed_slot_node.show()  // 跟隨滑鼠的浮動圖示

// 放下物品
grabbed_slot_data = inventory_data.drop_slot_data(grabbed_slot_data, target_index)

// 單個拿起（右鍵）
grabbed_slot_data = inventory_data.grab_single_slot_data(index)
```

### 物品丟棄到世界（_drop_item）

```
_drop_item(slot_data):
  scene_to_drop = load(slot_data.inventory_item.drop_scene).instantiate()
  if scene_to_drop is not CogitoObject: return false
  
  // ShapeCast3D 碰撞測試：找最近安全距離
  shape_cast.shape.size = item.get_aabb().size
  var safe_distance = drop_distance * shape_cast.closest_collision_safe_fraction()
  
  if 太近: return false
  
  CogitoSceneManager._current_scene_root_node.add_child(dropped_item)
  dropped_item.position = 計算結果的安全位置
  dropped_item.find_interaction_nodes() // 恢復互動節點
  → 讓撿起組件持有 slot_data（避免物品定義遺失）
```

丟棄時使用 ShapeCast3D 掃描，確保不會丟進牆壁裡。

### 手把操作（on_inventory_button_press）

match `[grabbed_slot_data, action]` 的二維狀態機：

```
[null, "move_item"] → 拿起
[_, "move_item"]    → 放下
[null, "use_item"]  → 使用
[_, "use_item"]     → 放下單個
[null, "drop_item"] → 丟棄
[null, "assign"]    → 開始指定快捷槽（焦點轉移到 quick_slots）
[_, "assign"]       → 取消指定，歸還物品
```

---

## 六、Hot Bar（hot_bar_inventory.gd）

**位置**：`InventoryPD/UiScenes/hot_bar_inventory.gd`

```
set_inventory_data(inventory_data):
  inventory_data.inventory_updated.connect(populate_hotbar)
  hot_bar_use.connect(inventory_data.use_slot_data)   // 按鍵 → 使用

populate_hotbar(inventory_data):
  if grid: populate_grid()  // 每個 origin_index 只顯示一個 slot
  else:    populate_non_grid()  // 直接取前 N 個 slot
```

Hotbar 最多顯示 `hotbar_slot_amount`（預設 4）個格，按鍵 `quickslot_1~4` 發射 `hot_bar_use.emit(index)` 直接呼叫 `use_slot_data()`。

**與 QuickSlots 的差異**：
- Hotbar = 固定顯示前 N 格物品（簡單模式）
- QuickSlots = 玩家自定義指定任意物品到槽（完整模式）
- `is_using_hotbar: bool` 決定用哪個系統

---

## 七、快捷槽系統（CogitoQuickslots + CogitoQuickslotContainer）

### CogitoQuickslots（Node）

**位置**：`InventoryPD/CogitoQuickSlots.gd`

```
quickslot_containers : Array[CogitoQuickslotContainer]  // 最多 N 個快捷槽
inventory_reference : CogitoInventory:
  set: 
    inventory_reference.unbind_quickslot_by_index.connect(on_unbind_quickslot_by_index)
    inventory_reference.picked_up_new_inventory_item.connect(on_auto_quickslot_new_item)
    set_inventory_quickslots(inventory_reference)  // 載入或初始化
```

**_unhandled_input**：監聽 `quickslot_1~4` → `inventory_data.use_slot_data(assigned_quickslots[i].origin_index)`

**自動快捷槽（on_auto_quickslot_new_item）**：
```
if !item.can_auto_slot: return
if 已在某快捷槽: return   // 避免重複
for quickslot in containers:
  if 空位 and (slot_number == -1 or slot_number == i+1):
    bind_to_quickslot(slot_data, quickslot)
    return
```

### 武器循環（_cycle_through_quickslotted_wieldables）

```
// 找出所有快捷槽中的 WieldableItemPD
quickslotted_wieldable_indexes = []
for container: if is WieldableItemPD → append

// 循環邏輯
if cycle_up:
  // 找到當前裝備的快捷槽位置，移至下一個
  // 若已是最後一個且 allow_unequip: put_away()
  // 否則跳回第一個
```

### CogitoQuickslotContainer（Control）

**位置**：`InventoryPD/UiScenes/CogitoQuickslotContainer.gd`

```
update_quickslot_data(slot_data):
  inventory_slot_reference = slot_data
  item_texture.show(); item_texture.texture = item_reference.icon
  inventory_slot_reference.stack_has_changed.connect(update_quickslot_stack)

clear_this_quickslot():
  inventory_slot_reference = null
  item_reference = null
  item_texture.hide()
  quickslot_cleared.emit(self)
```

---

## 八、格子物品欄完整資料流

```
【物品撿起】
  PickupComponent.interact()
    → inventory_data.pick_up_slot_data(slot_data)
    → inventory_updated.emit()
    → populate_item_grid() / populate_hotbar()（重建 UI）
    → picked_up_new_inventory_item.emit() → auto-quickslot 檢查

【物品欄開啟】
  player.toggle_inventory_interface.emit()
    → inventory_interface.open_inventory()
    → nodes_to_show 顯示，hot_bar_inventory 隱藏
    → quick_slots 進入焦點模式（手把）

【拖放移動】
  Slot 點擊 → on_inventory_button_press() / _on_gui_input()
    → grab_slot_data() → grabbed_slot_data 設值 → grabbed_slot_node 顯示
    → 移到目標格 → drop_slot_data() → inventory_updated.emit()

【快捷槽使用（遊戲中）】
  quickslot_1 輸入 → use_slot_data(origin_index)
    → inventory_data.use_slot_data(index)
    → InventoryItemPD.use(player_interaction_component)

【物品欄關閉】
  close_inventory()
    → 若有 grabbed_slot_data → 歸還至物品欄
    → 清除焦點，hot_bar_inventory 恢復顯示
```

---

## 九、架構設計模式總結

| 模式 | 實作 | 說明 |
|---|---|---|
| 全量重建 UI | `populate_item_grid()` 清除再重建 | 避免增量更新的複雜性 |
| origin_index 格子編碼 | 多格 slot 共享 origin_index | 一個物品 = 多個 SlotPanel 節點 |
| 響應式 charge_label | 連接 `charge_changed` 信號 | 彈藥即時更新不需重建 UI |
| ShapeCast3D 安全丟棄 | `closest_collision_safe_fraction()` | 防止物品丟進牆壁 |
| 雙系統並存 | is_using_hotbar 切換 | Hotbar 簡單 / QuickSlots 進階 |
| 手把二維狀態機 | match [grabbed_slot_data, action] | 清楚處理拿起/放下/使用各情境 |
