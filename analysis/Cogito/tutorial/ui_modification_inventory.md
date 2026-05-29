# 教學：如何修改物品欄（Inventory）UI

本教學說明如何修改物品欄格子外觀、佈局、拖放行為，以及如何擴充物品資訊面板。

## 前置知識
- 已閱讀 [Level 5A: 物品欄 UI 系統](../architecture/level5a_inventory_ui.md)。
- 具備 Godot 4 Control 節點基礎。

---

## 一、主要檔案導覽

| 檔案 | 類型 | 職責 |
|---|---|---|
| `InventoryPD/UiScenes/inventory_interface.gd` | `.gd` 腳本（**無同名 .tscn**）| 邏輯協調；實際場景在 `Player_HUD.tscn` 中的 `$InventoryInterface` |
| `InventoryPD/UiScenes/InventoryUI.tscn + .gd` | 完整場景 | 格子容器（GridContainer 或 VBoxContainer）|
| `InventoryPD/UiScenes/Slot.tscn + Slot.gd` | 完整場景 | 單個格子的外觀與信號 |

**重要**：`inventory_interface.gd` 中的 @onready 路徑揭示了完整結構（`inventory_interface.gd:7-17`）：
```gdscript
@onready var grabbed_slot_node = $GrabbedSlot         # 拖曳中的跟隨格子
@onready var external_inventory_ui = $ExternalInventoryUI
@onready var hot_bar_inventory = $HotBarInventory
@onready var info_panel = $InfoPanel
@onready var item_name = $InfoPanel/MarginContainer/VBoxContainer/ItemName
@onready var item_description = $InfoPanel/MarginContainer/VBoxContainer/ItemDescription
@onready var drop_prompt = $InfoPanel/MarginContainer/VBoxContainer/HBoxDrop
@onready var assign_prompt = $InfoPanel/MarginContainer/VBoxContainer/HBoxAssign
@onready var use_prompt = $InfoPanel/MarginContainer/VBoxContainer/HBoxUse
```

---

## 二、格子外觀修改（Slot.tscn）

`SlotPanel`（`Slot.gd:1`）節點結構：
- SlotPanel (PanelContainer + Slot.gd)
  - MarginContainer
    - TextureRect — 物品圖示（@onready texture_rect）
  - QuantityLabel (Label) — 數量（右下角，@onready quantity_label）
  - ChargeLabel (Label) — 耐久/彈藥數（@onready charge_label）
  - Selected (Panel) — 選取高亮框（@onready selection_panel）
  - Panel — 滑鼠 hover 高亮（在 _on_focus_entered 中 show）

**格子尺寸**：固定為 **64×64 px**，多格物品為 `64 * item_size.x × 64 * item_size.y`（`Slot.gd:109`）。修改格子大小需同時調整：
1. `SlotPanel` 的 `custom_minimum_size`
2. `InventoryUI.gd` 中 GridContainer 的 `columns` 欄位（影響格子排列）

**修改步驟**：
1. 打開 `addons/cogito/InventoryPD/UiScenes/Slot.tscn`。
2. 修改 `SlotPanel`（PanelContainer）的 `Theme Override → Styles → panel` 更換背景框。
3. 修改 `Selected`（Panel）的 `StyleBoxFlat` 顏色 → 更換選取高亮色。
4. `@export var highlight_color` 在 Inspector 直接設定 hover 顏色，由 `_on_focus_entered` 使用（`Slot.gd:128-130`）。

---

## 三、物品欄背景與佈局

物品欄介面整體容器在 `Player_HUD.tscn` 的 `$InventoryInterface` 節點下：
1. 打開 `Player_HUD.tscn`。
2. 找到 `InventoryInterface` 節點。
3. 展開找到 `InventoryUI`（物品格子容器）→ 修改其 `PanelContainer` 的 Theme 換底圖。

**調整欄數**（物品欄寬度）：
1. 打開 `InventoryUI.tscn`。
2. 找到 GridContainer 節點 → 修改 `columns` 屬性（預設通常為 8）。
3. **注意**：欄數需與 `InventoryPD` 資源中的 `inventory_width` 一致，否則格子會排列混亂。

---

## 四、物品資訊面板（InfoPanel）

玩家點擊物品時，`inventory_interface.gd` 會顯示 `info_panel` 並填入資料。節點路徑：
- $InfoPanel/MarginContainer/VBoxContainer/
  - ItemName (Label) ← item_name.text = "劍"
  - ItemDescription (Control) ← item_description
  - HBoxDrop ← 丟棄提示（鍵盤隱藏）
  - HBoxAssign ← 快捷鍵提示（鍵盤隱藏）
  - HBoxUse ← 使用提示

鍵盤/手把自動切換（`inventory_interface.gd:53-59`）：
```gdscript
func _on_input_device_change(_device, _device_index):
    if _device == "keyboard":
        drop_prompt.hide()   # 鍵盤不顯示手把按鍵提示
        assign_prompt.hide()
    else:
        drop_prompt.show()
        assign_prompt.show()
```

**修改物品描述顯示**：
1. 打開 `InventoryInterface`（在 Player_HUD.tscn 中）找到 `InfoPanel`。
2. 修改 `ItemName` Label 的字體、大小。
3. `ItemDescription` 通常是 `RichTextLabel` 或自訂 `Control`，可修改其 `bbcode_enabled` 支援 BBCode 格式。

---

## 五、自訂拖放預覽（GrabbedSlot）

拖動物品時，`GrabbedSlot` 節點跟隨滑鼠移動（`inventory_interface.gd:50`）：
```gdscript
grabbed_slot_node.visibility_changed.connect(update_grabbed_slot_position)
```

**修改拖放預覽外觀**：
1. 在 `Player_HUD.tscn` 找到 `InventoryInterface/GrabbedSlot`。
2. 它是一個與 `Slot.tscn` 相同類型的節點，但設定了 `mouse_filter = MOUSE_FILTER_IGNORE`（`inventory_interface.gd:48`）。
3. 可修改其 `modulate` 透明度（如設為 `Color(1,1,1,0.6)` 讓拖曳時半透明）。

---

## 六、快捷欄（HotBar）修改

快捷欄由 `hot_bar_inventory`（`$HotBarInventory`）管理，對應 `hot_bar_inventory.gd`。
- 快捷欄格子數量在 `cogito_player.tscn` 的玩家 `inventory_data`（`InventoryPD` 資源）設定：`hotbar_slots` 欄位。
- 外觀修改與一般格子相同（修改 `Slot.tscn`，因為快捷欄也使用相同格子場景）。

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 開啟 COGITO_3_Lobby.tscn，按 Tab/I | 物品欄開啟 |
| hover 格子 | 高亮顏色符合修改後的 `highlight_color` |
| 點擊有數量的物品 | 右下角顯示 `x2` 等數量標籤 |
| 點擊武器物品 | 顯示耐久/彈藥數（ChargeLabel）|
| 拖曳物品 | 跟隨滑鼠的預覽格子樣式符合修改 |
| 使用手把 | drop_prompt 和 assign_prompt 顯示（鍵盤時隱藏）|
