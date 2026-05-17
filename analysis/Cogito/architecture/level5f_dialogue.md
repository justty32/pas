# Cogito — Level 5F 對話整合分析

## 一、概覽

Cogito 提供兩個對話整合組件，均以**全注解（commented-out）**的形式存在，為安裝對應 addon 後提供啟用範本：

| 組件 | 目標 Addon | 對話形式 |
|---|---|---|
| `DialogicInteraction.gd` | Dialogic（官方知名對話插件） | 時間軸式對話（TimeLine） |
| `DialogueNodesInteraction.gd` | Dialogue Nodes（AssetLib） | 節點式對話泡泡（DialogueBubble） |

兩者均繼承 `InteractionComponent`，可掛在任何場景物件或 NPC 下。

---

## 二、DialogicInteraction.gd

**位置**：`Components/Interactions/DialogicInteraction.gd`

### 安裝步驟

```
1. 在 Godot AssetLib 或 GitHub 安裝 Dialogic addon
2. 取消此檔案全部注解（Ctrl + K）
3. 加入 DialogicInteraction.tscn 至物件/NPC 場景
4. 在 Inspector 指定 dialogic_timeline（.dtl 時間軸資源）
```

### 核心邏輯（取消注解後）

```
@export var dialogic_timeline : DialogicTimeline

func interact(_player_interaction_component: PlayerInteractionComponent):
  player_interaction_component = _player_interaction_component
  start_dialogue()

func start_dialogue():
  // 開啟 UI 覆蓋（隱藏準心等）
  player_interaction_component.get_parent().toggled_interface.emit(true)
  
  // 連接 ESC 鍵中斷
  if !player_interaction_component.get_parent().menu_pressed.is_connected(abort_dialogue):
    player_interaction_component.get_parent().menu_pressed.connect(abort_dialogue)
  
  // 連接對話結束
  if !Dialogic.timeline_ended.is_connected(stop_dialogue):
    Dialogic.timeline_ended.connect(stop_dialogue)
  
  Dialogic.start(dialogic_timeline)   // 啟動 Dialogic 時間軸

func stop_dialogue():
  player_interaction_component.get_parent().toggled_interface.emit(false)  // 恢復 UI

func abort_dialogue():
  Dialogic.end_timeline()  // 強制結束
  stop_dialogue()
```

### 整合點

| 機制 | 說明 |
|---|---|
| `toggled_interface.emit(true)` | 觸發玩家 HUD 切換（隱藏準心、屏蔽武器輸入等） |
| `menu_pressed.connect(abort_dialogue)` | 玩家按 ESC 中斷對話 |
| `Dialogic.timeline_ended` | 對話自然結束時恢復 UI |

---

## 三、DialogueNodesInteraction.gd

**位置**：`Components/Interactions/DialogueNodesInteraction.gd`

### 安裝步驟

```
1. 在 Godot AssetLib 搜尋「Dialogue Nodes」並安裝
2. 取消此檔案全部注解（Ctrl + K）
3. 在 DialogueNodesInteraction.tscn 中加入 $DialogueBubble 節點
4. 在 Inspector 設定 dialogue_data（.tres 對話資源）
```

### 核心邏輯（取消注解後）

```
@export var dialogue_data : DialogueData
@onready var dialogue_bubble: DialogueBubble = $DialogueBubble

func _ready() -> void:
  dialogue_bubble.data = dialogue_data  // 綁定對話資源

func interact(_player_interaction_component: PlayerInteractionComponent):
  player_interaction_component = _player_interaction_component
  start_dialogue()

func start_dialogue():
  player_interaction_component.get_parent().toggled_interface.emit(true)
  
  // 連接 ESC 中斷
  if !player_interaction_component.get_parent().menu_pressed.is_connected(abort_dialogue):
    player_interaction_component.get_parent().menu_pressed.connect(abort_dialogue)
  
  // 連接對話結束
  if !dialogue_bubble.dialogue_ended.is_connected(stop_dialogue):
    dialogue_bubble.dialogue_ended.connect(stop_dialogue)
  
  dialogue_bubble.start("START")  // 從 START 節點開始播放

func stop_dialogue():
  player_interaction_component.get_parent().toggled_interface.emit(false)

func abort_dialogue():
  dialogue_bubble.stop()
  stop_dialogue()
```

### 差異與 Dialogic 的比較

| 特性 | Dialogic | Dialogue Nodes |
|---|---|---|
| 對話形式 | 全螢幕時間軸（Timeline） | 場景內氣泡（DialogueBubble） |
| 啟動方式 | `Dialogic.start(timeline)` | `dialogue_bubble.start("START")` |
| 結束信號 | `Dialogic.timeline_ended` | `dialogue_bubble.dialogue_ended` |
| 中斷方式 | `Dialogic.end_timeline()` | `dialogue_bubble.stop()` |
| 對話泡泡 | 無（自行管理） | 內建 DialogueBubble 節點 |

---

## 四、共同設計模式

兩個組件共享相同的整合契約：

### 1. UI 暫停協議

```
player_interaction_component.get_parent().toggled_interface.emit(true/false)
```

`CogitoPlayer.toggled_interface` 信號觸發 `is_showing_ui = true/false`，讓玩家 HUD 知道外部 UI 已開啟，進而：
- 屏蔽武器輸入（PlayerInteractionComponent）
- 顯示/隱藏準心
- 防止意外觸發其他互動

### 2. ESC 中斷機制

```
menu_pressed.connect(abort_dialogue)
```

玩家按下 `menu`（ESC）時，CogitoPlayer 發射 `menu_pressed` 信號。對話組件監聽此信號，強制中斷對話並恢復 UI。

### 3. 連線保護（is_connected 檢查）

兩個組件在連接信號前均檢查 `is_connected(...)`，防止多次互動時重複連接信號（Godot 中重複連接同一 callable 會警告）。

---

## 五、使用架構圖

```
場景中的 NPC 或物件
  └─ DialogicInteraction（InteractionComponent 子類）
        @export dialogic_timeline : DialogicTimeline

玩家按下互動鍵
  → PlayerInteractionComponent.interact(target)
  → target 掃描所有 InteractionComponent
  → DialogicInteraction.interact(PIC)
  → start_dialogue()
    → toggled_interface.emit(true)   ← 暫停 HUD
    → Dialogic.start(timeline)       ← 啟動對話
    → 等待 timeline_ended 或 menu_pressed

對話結束
  → stop_dialogue()
    → toggled_interface.emit(false)  ← 恢復 HUD
```

---

## 六、注意事項

1. **所有程式碼均為注解狀態**：兩個組件在未安裝對應 addon 之前完全無效（繼承 InteractionComponent 但不覆寫任何有效方法），不需擔心副作用
2. **Dialogic 版本差異**：Dialogic v2（Godot 4 版）的 API 與 v1 不同，注解中的 `Dialogic.start()`、`Dialogic.timeline_ended` 對應 v2 的 API
3. **對話期間的 PIC 狀態**：`toggled_interface` 不會完全鎖死輸入，玩家仍可移動（只影響 `is_showing_ui` 旗標），若需鎖定移動需額外調用 `_on_pause_movement()`
4. **NPC 整合**：可同時在 NPC 上配置 `cogito_npc.gd`（NPC 行為狀態機）和 `DialogicInteraction`，互動時可暫停 NPC AI（需自行連接信號）
