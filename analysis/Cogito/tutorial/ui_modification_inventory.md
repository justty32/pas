# 教學：如何修改物品欄 (Inventory) UI

本教學將引導您如何修改 COGITO 的物品欄介面，包括格子外觀、佈局以及拖放行為。

## 前置知識
- 已閱讀 [Level 5A: 物品欄 UI 系統](../architecture/level5a_inventory_ui.md)，瞭解 `inventory_interface` 與 `InventoryUI` 的職責。
- 具備 Godot 4 控制節點 (Control Nodes) 的基本使用經驗。

## 原始碼導航

主要相關檔案位於：
- `addons/cogito/InventoryPD/UiScenes/inventory_interface.tscn` (大圖視窗)
- `addons/cogito/InventoryPD/UiScenes/inventory_interface.gd` (邏輯協調)
- `addons/cogito/InventoryPD/UiScenes/InventoryUI.tscn` (物品格子容器)
- `addons/cogito/InventoryPD/UiScenes/Slot.tscn` (單個格子外觀)
- `addons/cogito/InventoryPD/UiScenes/Slot.gd` (格子互動邏輯)

## 實實步驟

### 1. 修改物品欄背景與佈局
若要更換物品欄的底圖或調整整體大小：
1. 打開 `inventory_interface.tscn`。
2. 找到 `PlayerInventory` 節點。它通常是一個 `PanelContainer`。
3. 您可以修改其 `Theme Overrides` 中的 `Styles/Panel`，或是更換整個節點類型（例如改為 `NinePatchRect`）。

### 2. 自訂格子 (Slot) 外觀
COGITO 的物品欄是動態生成的，每個格子的外觀由 `Slot.tscn` 決定：
1. 打開 `addons/cogito/InventoryPD/UiScenes/Slot.tscn`。
2. 修改 `Background` (TextureRect) 以更換格子底圖。
3. 修改 `Highlight` (ColorRect) 以自訂滑鼠懸停或選取時的顏色。
4. **注意**：`ItemIcon` (TextureRect) 的 `Expand Mode` 建議保持為 `Ignore Size` 並配合 `Stretch Mode` 為 `Keep Centered`，因為物品圖示可能是跨格子的（見 `InventoryItemPD.item_size`）。

### 3. 修改物品名稱與描述顯示
當玩家點擊物品時，資訊顯示在 `inventory_interface`：
- 在 `inventory_interface.tscn` 中尋找 `InfoPanel` 容器。
- 這裡包含了 `ItemName` (Label) 與 `ItemDescription` (RichTextLabel)。
- 您可以調整這些節點的字體、大小或佈局位置。

### 4. 調整拖放 (Drag and Drop) 提示
當物品被拖起時，會有一個「跟隨滑鼠」的預覽：
- 邏輯位於 `inventory_interface.gd` 的 `_process` 函數中。
- `grabbed_slot_data` 變數儲存了當前被抓取的物品資訊。
- 您可以修改 `GrabbedSlot` 節點的渲染方式。

## 驗證方式
1. 進入 `addons/cogito/DemoScenes/COGITO_1_TutorialScene.tscn`。
2. 按下 `Tab` 或 `I` 打開物品欄。
3. 檢查格子顏色、字體風格是否符合您的修改。
4. 嘗試拖動一個物品（如手電筒），確認跟隨滑鼠的預覽 UI 是否正確顯示。
