# 解答：以 GDExtension 作為遊戲邏輯後端的注意事項

> 問題情境：GDScript 只負責渲染 / UI / 輸入接收，所有遊戲邏輯（對話文本、事件結果、物品互動）由 GDExtension 實作。
> 互動模式：玩家操作 → 傳給 GDExtension → 取得結果；`_process()` 每幀向 GDExtension 輪詢需要更新的狀態。
> 分析日期：2026-04-18

---

## 1. API 邊界設計（最重要）

這是整個架構的核心，必須在動筆前設計清楚。

### 1.1 建議的邊界形式

GDExtension 暴露一個（或少數幾個）**單例節點**（autoload compatible），提供：

```
# GDExtension 暴露的 GDScript 可見類別範例（偽碼）

class_name GameEngine extends Node

# --- 玩家操作 API ---
func submit_action(action: PlayerAction) -> ActionResult: ...

# --- 每幀輪詢 ---
func poll_state_updates() -> Array[StateUpdate]: ...

# --- 對話 ---
func get_dialogue(npc_id: StringName) -> DialogueSession: ...
func submit_dialogue_choice(session_id: int, choice_index: int) -> DialogueLine: ...

# --- 查詢（非每幀，按需呼叫）---
func get_entity_snapshot(entity_id: int) -> EntitySnapshot: ...
```

`PlayerAction`, `ActionResult`, `StateUpdate`, `DialogueLine` 等全部定義為 GDExtension 的 `Resource` 或 `RefCounted` 子類。

### 1.2 用 Resource / RefCounted 傳遞資料而非 Dictionary

**不推薦**（GDScript 端每幀分配新的 Dictionary，GC 壓力大）：
```gdscript
# ❌ 避免
func submit_action(action: Dictionary) -> Dictionary:
```

**推薦**（GDExtension 定義強型別物件）：
```gdscript
# ✔ 讓 GDExtension 暴露 class_name PlayerAction extends RefCounted
var action := PlayerAction.new()
action.type = PlayerAction.Type.INTERACT
action.target_id = npc_node.entity_id
var result: ActionResult = GameEngine.submit_action(action)
```

GDExtension 的 `RefCounted` 子類不需手動釋放，且欄位存取比 Dictionary 快一個量級。

---

## 2. 每幀狀態更新（Delta Update 模式）

### 2.1 核心原則：GDExtension 是唯一的「事實來源（Source of Truth）」

- GDScript 的場景節點只是**視圖（View）**，不保存遊戲邏輯狀態。
- GDScript 絕不修改 GDExtension 擁有的狀態，只能透過 `submit_action` 請求修改。

### 2.2 Delta Push vs Polling

有兩種方案：

| 方案 | 做法 | 適合場景 |
| :--- | :--- | :--- |
| **Polling（每幀輪詢）** | GDScript `_process()` 呼叫 `GameEngine.poll_state_updates()` | 邏輯簡單、狀態更新密集 |
| **Signal Push** | GDExtension 在狀態改變時 emit Godot signal | 事件稀疏（對話觸發、寶箱開啟） |

**建議混合使用**：
- 角色位置、動畫狀態 → **Polling**（每幀）
- 事件觸發（戰鬥開始、對話開始、物品取得）→ **Signal**（由 GDExtension emit，GDScript connect）

### 2.3 `StateUpdate` 的設計

```gdscript
# GDExtension 定義
class_name StateUpdate extends RefCounted
enum UpdateType { MOVE, ANIMATION, STATS_CHANGED, ENTITY_DESTROYED, ... }

var entity_id: int
var type: UpdateType
var payload: Variant  # 依 type 不同而異
```

每幀 GDScript 端：
```gdscript
func _process(delta: float) -> void:
    GameEngine.tick(delta)  # 推進 GDExtension 的邏輯時間
    var updates: Array[StateUpdate] = GameEngine.poll_state_updates()
    for update in updates:
        _apply_update(update)
```

**重要**：`poll_state_updates()` 應回傳「自上次 poll 以來變化的內容」，並在 GDExtension 內部清空暫存列表，避免重複處理。

---

## 3. 執行緒（Threading）注意事項

### 3.1 預設：單執行緒，最安全

Godot 的節點 API 只能在主執行緒呼叫。若 GDExtension 邏輯很快（< 1ms），直接在 `_process()` 同步呼叫即可，不需多執行緒。

### 3.2 若邏輯耗時（如 AI 路徑規劃、複雜計算）

把 GDExtension 的 `tick()` 放到 `WorkerThreadPool`：

```gdscript
# GDScript 端
var _logic_done: bool = true

func _process(delta: float) -> void:
    if _logic_done:
        _logic_done = false
        WorkerThreadPool.add_task(func():
            GameEngine.tick(delta)   # GDExtension 邏輯（不觸碰 Godot 節點）
            _logic_done = true
        )
    
    # 主執行緒：只處理已經算好的 StateUpdate
    var updates := GameEngine.poll_state_updates()
    for u in updates:
        _apply_update(u)
```

**鐵則**：GDExtension 在背景執行緒中**絕對不能**呼叫任何 Godot 節點方法（`get_node`、`emit_signal` 等）。只能修改自己的內部狀態，等主執行緒來讀。

---

## 4. 對話系統整合

由於你不打算用 Dialogic，自己設計對話 API：

### 4.1 流程

```
玩家按 interact → submit_action(TALK, npc_id)
  → ActionResult.type == DIALOGUE_STARTED
  → ActionResult.dialogue_session_id: int

GDScript 開啟對話 UI，呼叫 get_next_dialogue_line(session_id)
  → DialogueLine { speaker, text, choices: Array[String] }

玩家選擇 → submit_dialogue_choice(session_id, choice_index)
  → 下一個 DialogueLine（或 type == DIALOGUE_ENDED）
```

### 4.2 GDExtension 建議暴露的對話類型

```cpp
// GDExtension C++ 側（Godot-cpp）
struct DialogueLine : public godot::RefCounted {
    GDCLASS(DialogueLine, RefCounted)
    enum Type { TEXT, CHOICES, END };
    Type type;
    godot::String speaker;
    godot::String text;
    godot::TypedArray<godot::String> choices;
};
```

---

## 5. GDScript 端的「反應式 UI 模式」

參考 godot-open-rpg 的 Signal Bus，但訊號源改為 GDExtension：

```gdscript
# GameEngine（GDExtension autoload）自行暴露 signal
signal combat_started(arena_data: CombatData)
signal dialogue_started(session_id: int)
signal item_acquired(item_data: ItemData)

# GDScript 只 connect，不決定何時 emit
func _ready() -> void:
    GameEngine.combat_started.connect(_on_combat_started)
    GameEngine.dialogue_started.connect(_on_dialogue_started)
```

**好處**：GDScript 完全不知道「什麼條件觸發戰鬥」，這個判斷完全在 GDExtension。

---

## 6. 狀態同步的常見陷阱

| 陷阱 | 說明 | 解法 |
| :--- | :--- | :--- |
| **GDScript 偷偷改狀態** | `player_node.position = ...` 繞過 GDExtension | 所有狀態改變只透過 `submit_action` |
| **每幀 new Dictionary** | GC 頻繁觸發，卡頓 | 用強型別 RefCounted 物件，或預先分配池 |
| **`poll_state_updates` 不清空** | 同一事件被重複套用 | GDExtension 端每次 poll 後清空 pending list |
| **執行緒競爭** | 背景 tick 與主執行緒 poll 同時存取 pending list | 用 mutex 保護，或用 double-buffer 設計 |
| **GDExtension 直接操作節點** | 在非主執行緒呼叫 `Node::add_child` | 嚴禁；只傳資料，節點操作永遠在 GDScript |

---

## 7. 建構管線（Build Pipeline）注意事項

- GDExtension 需為每個目標平台（Windows x64, Linux x64, macOS, Android, iOS）**個別編譯**。
- 使用 `godot-cpp` 的 SCons build system，建議搭配 CI 自動化。
- `.gdextension` 設定檔需列出所有平台的 `.dll` / `.so` / `.dylib` 路徑。
- Debug 版本要開 `debug_symbols=yes`，Release 版本開 `production=yes`。
- **版本鎖定**：GDExtension 二進位與 Godot 版本強綁定；升 Godot 版本需重新編譯 GDExtension。

---

## 8. 除錯建議

- GDExtension 內部實作**詳盡的日誌系統**，因為 GDScript debugger 看不到 C++ 堆疊。
- 在 GDExtension 暴露一個 `debug_dump_state() -> String` 方法，可從 GDScript 呼叫印出完整狀態，方便排查。
- 建議先用純 GDScript 把整個架構 mock 起來（假的 `GameEngine` 單例），確認 GDScript 端設計正確後再接真正的 GDExtension。

---

## 9. 與 godot-open-rpg 的對照

| godot-open-rpg 的做法 | 你的架構調整 |
| :--- | :--- |
| `BattlerStats` 是 GDScript Resource | `BattlerStats` 在 GDExtension，只暴露唯讀 snapshot 給 GDScript |
| `CombatAI.select_action()` 在 GDScript | AI 決策完全在 GDExtension |
| `FieldEvents.combat_triggered` 由 CombatTrigger emit | GDExtension 決定何時 emit `GameEngine.combat_started` |
| `Gameboard.pathfinder` 是 GDScript AStar2D | 路徑計算在 GDExtension，GDScript 只接收 `move_path: Array[Vector2i]` |
| `Cutscene._execute()` 在 GDScript | GDExtension 回傳「事件腳本清單」，GDScript 順序播放 |

---

## 10. 最小可行介面（建議第一版只做這些）

```
GameEngine（GDExtension autoload）
├── tick(delta: float)                    # 每幀推進邏輯
├── poll_state_updates() -> Array         # 取得 delta state
├── submit_action(action: PlayerAction) -> ActionResult  # 玩家操作
├── get_next_dialogue_line(id: int) -> DialogueLine      # 對話推進
└── [signals] combat_started / dialogue_started / scene_changed
```

其餘功能（背包、角色成長、存檔）在第一版用 GDScript stub 實作，確認架構穩定後再遷移到 GDExtension。
