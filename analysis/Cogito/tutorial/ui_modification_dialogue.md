# 教學：如何調整對話（Dialogue）介面

COGITO 提供兩個對話插件的橋接組件：**Dialogic v2** 與 **Dialogue Nodes**。兩者的腳本**全部預設以注解方式存在**，使用前必須手動啟用。本教學說明完整啟用流程與 UI 外觀修改方式。

## 前置知識
- 已閱讀 [Level 5F: 對話整合](../architecture/level5f_dialogue.md)。
- 已從 Godot AssetLib 安裝對應的對話插件。

---

## 一、重要：橋接腳本全部被注解

`DialogicInteraction.gd` 和 `DialogueNodesInteraction.gd` 的**所有功能代碼都被注解掉了**（`DialogicInteraction.gd:1-41`）。安裝插件後必須手動取消注解才能使用。

**激活步驟**：

### Dialogic 插件（推薦）
1. 在 Godot AssetLib 搜尋並安裝 **Dialogic**（Emilio Coppola 的版本，支援 Godot 4）。
2. 打開 `addons/cogito/Components/Interactions/DialogicInteraction.gd`。
3. 選取所有被注解的代碼（第 9 行到最後）→ `Ctrl+K` 取消注解。
4. 完整的 Dialogic 橋接腳本如下（確認取消注解後的狀態）：

```gdscript
# addons/cogito/Components/Interactions/DialogicInteraction.gd（取消注解後）
extends InteractionComponent

@export var dialogic_timeline : DialogicTimeline

var player_interaction_component : PlayerInteractionComponent


func _ready() -> void:
    pass


func interact(_player_interaction_component: PlayerInteractionComponent):
    player_interaction_component = _player_interaction_component
    start_dialogue()


func start_dialogue():
    # 暫停玩家互動（鎖定移動、隱藏 HUD 提示）
    player_interaction_component.get_parent().toggled_interface.emit(true)
    # 連接 menu 鍵到中斷對話
    if !player_interaction_component.get_parent().menu_pressed.is_connected(abort_dialogue):
        player_interaction_component.get_parent().menu_pressed.connect(abort_dialogue)
    # 連接對話結束信號
    if !Dialogic.timeline_ended.is_connected(stop_dialogue):
        Dialogic.timeline_ended.connect(stop_dialogue)
    Dialogic.start(dialogic_timeline)


func stop_dialogue():
    player_interaction_component.get_parent().toggled_interface.emit(false)


func abort_dialogue():
    Dialogic.end_timeline()
    stop_dialogue()
```

### Dialogue Nodes 插件
1. 安裝 **Dialogue Nodes**（Nagi 的版本）。
2. 取消注解 `DialogueNodesInteraction.gd` 的所有代碼。
3. 在 NPC 場景中添加 `$DialogueBubble` 子節點（需要 `DialogueBubble.tscn`，由插件提供）。

---

## 二、`toggled_interface` 的作用

兩個插件的橋接都使用 `toggled_interface.emit(true/false)` 來暫停/恢復玩家狀態：
- `emit(true)` → 玩家進入「介面模式」：移動暫停、HUD 隱藏、滑鼠游標顯示。
- `emit(false)` → 恢復正常遊戲狀態。

這個信號連接到 `player_hud_manager.gd:116`：
```gdscript
player.toggled_interface.connect(_on_external_ui_toggle)
```

**若對話開啟後玩家仍可移動**，確認 `toggled_interface.emit(true)` 是否有被呼叫（確認取消注解正確）。

---

## 三、修改 Dialogic UI 外觀

Dialogic v2 的對話介面**完全由插件的 Style 系統控制**，COGITO 本身只負責呼叫 `Dialogic.start(timeline)`。

**修改對話方塊樣式**：
1. 點擊 Godot 頂部選單的 **Dialogic** 標籤。
2. 前往 **Settings → Layouts**（或 **Styles**）。
3. 建立或修改一個 Layout：
   - **Dialog Box**：對話方塊的背景 Panel 樣式。
   - **Character Name**：說話者名稱的字體與位置。
   - **Portrait**：角色頭像的位置（左/右/中）。
   - **Choices**：選項按鈕的樣式。

**對話中隱藏遊戲 HUD**：
1. 對話介面預設會覆蓋在遊戲視圖上層。
2. `toggled_interface.emit(true)` 已暫停玩家互動並隱藏大部分 HUD 元素。
3. 若需要完全隱藏底部屬性條，在 `player_hud_manager.gd` 的 `_on_external_ui_toggle` 函數中加入：
   ```gdscript
   func _on_external_ui_toggle(is_open: bool) -> void:
       ui_attribute_area.visible = !is_open  # 對話時隱藏屬性條
       wieldable_hud.visible = !is_open
   ```

---

## 四、修改 Dialogue Nodes UI 外觀

Dialogue Nodes 的 `DialogueBubble` 是一個標準 Control 場景：
1. 在插件的 `addons/dialogue_nodes/objects/` 目錄下找到 `DialogueBubble.tscn`。
2. 直接修改其 Panel 背景、Label 字體、選項按鈕樣式。
3. 修改後的場景在所有使用 `DialogueNodesInteraction` 的 NPC 上生效（因為是同一個場景實例）。

---

## 五、在 NPC 上掛載對話組件

### 節點結構（以 Dialogic 為例）：
```
CogitoNPC
├── NPC_State_Machine
├── HitboxComponent
├── DialogicInteraction (Node + dialogic_interaction.gd)  ← 掛在此處
│   └── Inspector: dialogic_timeline = [選擇 .dtl 時間軸資源]
└── BasicInteraction  ← 可選：保留其他互動選項
```

### 建立 Dialogic Timeline：
1. Dialogic 面板 → 新建 Timeline → 命名（如 `npc_shopkeeper.dtl`）。
2. 添加對話節點、角色節點、選項分支。
3. 存檔 → `DialogicInteraction` Inspector 的 `dialogic_timeline` 欄位指向該 .dtl 檔案。

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 取消注解前嘗試互動 | 報錯或無反應（腳本為空）|
| 正確取消注解後與 NPC 互動 | 對話視窗開啟，玩家無法移動 |
| 對話結束或按 Menu 鍵 | 對話關閉，玩家恢復正常控制 |
| 在 Dialogic Styles 修改字體 | 對話文字樣式更新 |
| `toggled_interface` emit 確認 | `_on_external_ui_toggle` 執行，HUD 元素隱藏 |
