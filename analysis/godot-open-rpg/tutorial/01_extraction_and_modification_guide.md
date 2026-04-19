# 教學 01：從 godot-open-rpg 提取素材，改造為 GDExtension 後端的回合制 RPG

> 目標：建立一個「GDScript 純前端 + GDExtension 純後端」的 Roguelike 風格 RPG。
> 地圖分兩層（世界地圖 / 局部地圖），世界以 `next_turn()` 驅動，玩家行動以 `player_act()` 觸發。
> 本教學假設你已讀過 `answers/gdextension_backend_architecture.md`。
> 撰寫日期：2026-04-18

---

## 全文導覽

```
第 1 章  架構全貌與設計決策
第 2 章  從 godot-open-rpg 提取什麼 / 丟棄什麼
第 3 章  核心迴圈設計：next_turn() 與 player_act()
第 4 章  兩層地圖系統（WorldMap / LocalMap）
第 5 章  逐步改造：TurnManager、PlayerInput、Gamepiece
第 6 章  GDExtension 的最小 API 規格
第 7 章  實作順序建議（Milestone 清單）
```

---

## 第 1 章：架構全貌與設計決策

### 1.1 整體架構圖

```
┌─────────────────────────────────────────────────────┐
│                   Godot 前端（GDScript）              │
│                                                     │
│  InputHandler ──→ player_act(action) ──→ TurnManager│
│                                          │          │
│  MapDisplay ←── StateUpdate 列表 ←── next_turn()    │
│  (Gamepiece 動畫 / TileMap 渲染 / UI)                │
│                                                     │
│  [Autoloads]  GameEvents / MapManager / Player      │
└──────────────────────┬──────────────────────────────┘
                       │  GDExtension API
┌──────────────────────▼──────────────────────────────┐
│                 GDExtension（C++）                   │
│                                                     │
│  submit_action() / advance_time() / poll_updates()  │
│  WorldState / EntityManager / PathPlanner           │
│  DialogueEngine / InventorySystem / CombatCalc      │
└─────────────────────────────────────────────────────┘
```

### 1.2 三大設計決策

| 決策 | 理由 |
| :--- | :--- |
| **沒有獨立戰鬥場景** | 所有行動（含戰鬥）都在 Tilemap 上發生；GDExtension 決定攻擊傷害，GDScript 只播 hit 動畫 |
| **`next_turn()` 是世界推進的唯一入口** | 避免散落各處的「AI 更新」；每次呼叫後統一更新 Gamepiece 視覺 |
| **`player_act()` 回傳時間消耗** | 支援「時間票券（Time Cost）」系統：行走消耗 100 tick，施法消耗 150 tick，這決定敵人行動幾次 |

---

## 第 2 章：從 godot-open-rpg 提取什麼 / 丟棄什麼

### 2.1 直接保留（幾乎不改動）

| 檔案 | 來源路徑 | 保留理由 |
| :--- | :--- | :--- |
| `gameboard.gd` | `src/field/gameboard/gameboard.gd` | 格子座標系統完整，直接可用 |
| `gameboard_properties.gd` | `src/field/gameboard/gameboard_properties.gd` | 格子尺寸 / 邊界定義 |
| `gameboard_layer.gd` | `src/field/gameboard/gameboard_layer.gd` | TileMapLayer 阻擋格判斷邏輯 |
| `pathfinder.gd` | `src/field/gameboard/pathfinder.gd` | AStar2D 包裝，初期在 GDScript 用，之後可移入 GDExtension |
| `gamepiece_registry.gd` | `src/field/gamepieces/gamepiece_registry.gd` | 格子 ↔ Gamepiece 映射，完全可用 |
| `gamepiece_animation.gd` | `src/field/gamepieces/animation/gamepiece_animation.gd` | 動畫播放邏輯不需要改 |
| `directions.gd` | `src/common/directions.gd` | 四向枚舉與向量映射 |
| `field_events.gd` 的 Signal Bus 模式 | `src/field/field_events.gd` | 模式保留，但內容擴充 |
| `screen_transition.gd` | `src/common/screen_transitions/` | 地圖切換轉場直接可用 |
| `music_player.gd` | `src/common/music/` | 直接可用 |
| `debug/` 工具 | `src/field/gameboard/debug/` | 除錯用，照搬 |

### 2.2 大幅修改後保留

#### `gamepiece.gd` → 改為「即時跳格 + 動畫」

**原本**：`Gamepiece extends Path2D`，用 `PathFollow2D` 達到連續平滑移動（適合即時遊戲）。

**新版**：改為 `Node2D`，移動是一格一格的：
1. 接到 `StateUpdate.MOVE` → 直接設定 `position = Gameboard.cell_to_pixel(new_cell)` 
2. 同時播放 walk 動畫（duration ≒ 0.1s），動畫結束後 idle
3. 不再需要 `_process()` 的連續推進

**保留的邏輯**：`animation_scene: PackedScene`（動態附加動畫子場景）、`direction`、`rest_position`、`arrived` signal。

**丟棄的邏輯**：`Path2D` curve 管理、`PathFollow2D`、`follower`、`move_to(target_point)`、`stop()`、`_process(delta)` 裡的連續移動邏輯。

#### `player_controller.gd` → 改為「輸入收集器（InputHandler）」

**原本**：`PlayerController` 監聽 `FieldEvents.cell_selected`、WASD 鍵，在 GDScript 端算路徑並連續移動。

**新版**：`InputHandler` 只做「把輸入封裝成 `PlayerAction` 並呼叫 `player_act()`」，路徑計算交給 GDExtension。

**保留的邏輯**：`_unhandled_input()` 捕捉 WASD / 滑鼠點擊的框架、`Interaction` 判斷。

**丟棄的邏輯**：`move_along_path()` 的自己算路徑、`Trigger` 的腳本式觸發（改由 GDExtension 的 StateUpdate 通知）。

#### `field.gd` → 改為 `TurnManager`

**原本**：`Field extends Node2D`，管理場景顯示 / 隱藏（配合戰鬥場景切換）。

**新版**：`TurnManager extends Node`（或直接成為 autoload），核心職責：
- `player_act(action)` → 傳給 GDExtension → 取回 `ActionResult.time_cost` → 呼叫 `next_turn(time_cost)`
- `next_turn(time_cost)` → `GameEngine.advance_time(time_cost)` → `poll_state_updates()` → 派發給各 Gamepiece / UI

### 2.3 完全丟棄

| 丟棄的模組 | 替代方案 |
| :--- | :--- |
| `combat.gd`, `combat_arena.gd` | 戰鬥計算移入 GDExtension，戰鬥視覺在 Tilemap 上（Gamepiece 的 hit / death 動畫） |
| `combat_events.gd` | 不再有獨立戰鬥狀態；`GameEvents` 統一處理 |
| `battler.gd`, `battler_stats.gd`, `battler_action*.gd`, `battler_roster.gd` | 全部移入 GDExtension |
| `combat_ai_random.gd` | 移入 GDExtension |
| `path_loop_ai_controller.gd` | NPC 移動路徑由 GDExtension 決定，GDScript 只接收 `StateUpdate.MOVE` |
| `cutscene.gd`, `trigger.gd`, `interaction.gd`, `templates/` | 大幅簡化；「腳本式事件」改為 GDExtension 回傳 `EventSequence` 清單，GDScript 逐一播放 |
| Dialogic addon | 自製對話 UI，文本來自 GDExtension 的 `DialogueLine` |
| `inventory.gd` | 移入 GDExtension |

---

## 第 3 章：核心迴圈設計

### 3.1 `player_act()` — 玩家行動入口

```gdscript
# TurnManager.gd（autoload）

func player_act(action: PlayerAction) -> void:
    # 在輸入到下一幀之間，鎖定輸入避免連按
    _input_locked = true
    
    # 把行動交給 GDExtension 處理
    var result: ActionResult = GameEngine.submit_action(action)
    
    if result.is_valid:
        # 用行動消耗的時間推進世界
        await next_turn(result.time_cost)
    
    _input_locked = false
```

### 3.2 `next_turn()` — 世界推進

```gdscript
# TurnManager.gd

func next_turn(elapsed_time: float) -> void:
    # 1. 推進 GDExtension 的邏輯時鐘
    GameEngine.advance_time(elapsed_time)
    
    # 2. 取得本次推進後所有變化的物件狀態
    var updates: Array[StateUpdate] = GameEngine.poll_state_updates()
    
    # 3. 依序套用（等待動畫播完後才算「一回合結束」）
    for update in updates:
        await _apply_update(update)
    
    # 4. 通知 UI 等其他系統「本回合結束」
    GameEvents.turn_ended.emit(elapsed_time)


func _apply_update(update: StateUpdate) -> void:
    var gp: Gamepiece = GamepieceRegistry.get_gamepiece(update.source_cell)
    
    match update.type:
        StateUpdate.Type.MOVE:
            if gp:
                await gp.move_to_cell(update.target_cell)  # 播動畫後 resolve
        
        StateUpdate.Type.ANIMATION:
            if gp:
                gp.animation.play(update.animation_name)
                await gp.animation.animation_finished
        
        StateUpdate.Type.ENTITY_SPAWNED:
            _spawn_gamepiece(update)
        
        StateUpdate.Type.ENTITY_DESTROYED:
            if gp:
                await gp.animation.play("death")
                gp.queue_free()
        
        StateUpdate.Type.DIALOGUE_STARTED:
            GameEvents.dialogue_started.emit(update.dialogue_session_id)
        
        StateUpdate.Type.MAP_CHANGE:
            await MapManager.switch_to(update.target_map_id)
```

### 3.3 `PlayerAction` 的種類

```gdscript
# GDExtension 暴露的 Resource（偽碼）
class_name PlayerAction extends RefCounted

enum Type {
    MOVE,       # 移動到相鄰格
    WAIT,       # 等待（跳過一回合）
    ATTACK,     # 近戰攻擊鄰格敵人
    CAST,       # 施放技能（帶目標格）
    TALK,       # 與鄰格 NPC 對話
    PICK_UP,    # 撿起腳下物品
    USE_ITEM,   # 使用物品（帶物品 id）
    ENTER,      # 進入鄰格建築 / 下一層
    EXIT,       # 離開當前地圖（回世界地圖）
}

var type: Type
var direction: Vector2i    # 對 MOVE / ATTACK / TALK 使用
var target_cell: Vector2i  # 對 CAST 使用
var item_id: int           # 對 USE_ITEM 使用
var skill_id: int          # 對 CAST 使用
```

### 3.4 `ActionResult.time_cost` 與時間系統

GDExtension 內部維護一個全域「時鐘（tick）」。不同行動消耗不同時間，敵人也有各自的行動速度閾值：

```
行走一格      = 100 tick
施法（中速）  = 150 tick
施法（慢速）  = 250 tick
等待          = 100 tick
```

GDExtension 在 `advance_time(elapsed_time)` 時，讓所有速度 ≥ elapsed_time 的實體行動，並把它們的 `StateUpdate` 加入 pending 列表。這樣玩家每次行動後，敵人可能行動零次、一次或多次，自然實現「速度差」機制。

---

## 第 4 章：兩層地圖系統

### 4.1 概念

```
WorldMap（大地圖）                 LocalMap（小地圖）
每格 = 一個「地區」                每格 = 一步實際位置
玩家移動到「城鎮格」               玩家在城鎮內部行走
→ 觸發 ENTER 行動                  NPC、物品、dungeon floor 在這裡
→ MapManager 切換到 LocalMap
→ LocalMap 載入對應地區的 tscn
```

### 4.2 `MapManager`（autoload）

```gdscript
# map_manager.gd (autoload)
extends Node

signal map_changed(new_map_id: StringName)

var current_map: BaseMap = null  # WorldMap 或 LocalMap 的基底類別
var _world_map: WorldMap
var _local_map: LocalMap

func _ready() -> void:
    _world_map = $WorldMap
    _local_map = $LocalMap
    _local_map.hide()
    current_map = _world_map


func switch_to(map_id: StringName) -> void:
    # 由 TurnManager._apply_update(StateUpdate.MAP_CHANGE) 呼叫
    await Transition.cover(0.2)
    
    if map_id == &"world":
        _local_map.hide()
        _world_map.show()
        current_map = _world_map
        Gameboard.properties = _world_map.gameboard_properties
    else:
        # 讓 GDExtension 決定應該載入哪個地圖場景
        var map_scene: PackedScene = _load_local_map(map_id)
        _local_map.load_map(map_scene)
        _world_map.hide()
        _local_map.show()
        current_map = _local_map
        Gameboard.properties = _local_map.gameboard_properties
    
    map_changed.emit(map_id)
    Transition.clear.call_deferred(0.2)


func _load_local_map(map_id: StringName) -> PackedScene:
    # 路徑規則：res://maps/local/<map_id>.tscn
    return load("res://maps/local/%s.tscn" % map_id)
```

### 4.3 `WorldMap` 與 `LocalMap` 的共同基底

```gdscript
# base_map.gd
class_name BaseMap extends Node2D

@export var gameboard_properties: GameboardProperties
@export var initial_music: AudioStream

# 地圖載入完成後，向 Gameboard autoload 登記自己的 properties
func _ready() -> void:
    Gameboard.properties = gameboard_properties
    if initial_music:
        Music.play(initial_music)
```

```gdscript
# world_map.gd
class_name WorldMap extends BaseMap

# WorldMap 的每個格子存放 POI（Point of Interest）資訊
# 由 GDExtension 以 StateUpdate.ENTITY_SPAWNED 方式初始化地標 Gamepiece
```

```gdscript
# local_map.gd
class_name LocalMap extends BaseMap

# 動態換載地圖 tscn（包含 TileMapLayers 和預設 Gamepiece）
func load_map(scene: PackedScene) -> void:
    # 清空舊地圖
    for child in get_children():
        child.queue_free()
    await get_tree().process_frame
    
    var new_map: = scene.instantiate()
    add_child(new_map)
```

### 4.4 兩層地圖的 Gameboard 切換問題

godot-open-rpg 的 `Gameboard` 是單一 autoload，預設綁定一個 `GameboardProperties`。兩層地圖需要切換 properties：

**解法**：`MapManager.switch_to()` 裡直接設定 `Gameboard.properties = new_map.gameboard_properties`（見 4.2）。`Gameboard.properties` 的 setter 會 emit `properties_set` signal，讓已存在的 Gamepiece 重新對齊新格子尺寸。

> **注意**：WorldMap 與 LocalMap 的格子尺寸可以不同（例如 WorldMap 每格 64px，LocalMap 每格 16px），只要 `GameboardProperties.cell_size` 設定正確即可。

---

## 第 5 章：逐步改造

### 5.1 新版 `Gamepiece`（移除 Path2D）

```gdscript
# gamepiece.gd（改造後）
@tool
class_name Gamepiece extends Node2D

signal arrived  # 保留，供 TurnManager 的 await 使用

@export var animation_scene: PackedScene:
    set(value):
        # 邏輯與原本相同，動態替換動畫子場景
        ...

@export var move_speed: float = 4.0  # 格/秒（純動畫用，不影響遊戲邏輯）

var animation: GamepieceAnimation = null
var direction: = Directions.Points.SOUTH:
    set(value):
        if value != direction:
            direction = value
            animation.direction = direction

var entity_id: int = -1  # GDExtension 端的實體 ID，用於對應 StateUpdate


# 由 TurnManager._apply_update() 呼叫
# 立即更新邏輯位置 + 播放移動動畫
func move_to_cell(target_cell: Vector2i) -> void:
    var target_pos: = Gameboard.cell_to_pixel(target_cell)
    
    # 計算面向方向
    var delta: = target_pos - position
    direction = Directions.vector_to_direction(delta)
    
    animation.play("run")
    
    # Tween 動畫（純視覺，不影響邏輯格位）
    var tween: = create_tween()
    tween.tween_property(self, "position", target_pos, 1.0 / move_speed)
    await tween.finished
    
    animation.play("idle")
    arrived.emit()


func _ready() -> void:
    if not Engine.is_editor_hint() and is_inside_tree():
        if Gameboard.properties == null:
            await Gameboard.properties_set
        
        var cell: = Gameboard.get_cell_under_node(self)
        position = Gameboard.cell_to_pixel(cell)
        
        if GamepieceRegistry.register(self, cell) == false:
            queue_free()
```

> **與原版的最大差異**：不再繼承 `Path2D`，不再有 `_process()` 裡的連續移動。移動由 `move_to_cell()` 的 Tween 完成，`await` 確保動畫播完才繼續 `next_turn()`。

### 5.2 新版 `InputHandler`（取代 `PlayerController`）

```gdscript
# input_handler.gd
class_name InputHandler extends Node

# 是否鎖定輸入（TurnManager 在處理回合期間設為 true）
var is_locked: bool = false


func _unhandled_input(event: InputEvent) -> void:
    if is_locked:
        return
    
    # WASD / 方向鍵 → 移動行動
    var dir: = Vector2i.ZERO
    if event.is_action_pressed("ui_up"):    dir = Vector2i(0, -1)
    elif event.is_action_pressed("ui_down"): dir = Vector2i(0, 1)
    elif event.is_action_pressed("ui_left"): dir = Vector2i(-1, 0)
    elif event.is_action_pressed("ui_right"):dir = Vector2i(1, 0)
    
    if dir != Vector2i.ZERO:
        var action: = PlayerAction.new()
        action.type = PlayerAction.Type.MOVE
        action.direction = dir
        TurnManager.player_act(action)
        return
    
    # Space / Enter → 等待
    if event.is_action_pressed("interact"):
        var action: = PlayerAction.new()
        action.type = PlayerAction.Type.WAIT
        TurnManager.player_act(action)
        return
    
    # 滑鼠點擊 → 移動到目標格（由 GDExtension 算路徑）
    if event is InputEventMouseButton and event.pressed:
        var clicked_cell: = Gameboard.pixel_to_cell(
            get_viewport().get_camera_2d().get_global_mouse_position()
        )
        if clicked_cell != Gameboard.INVALID_CELL:
            GameEvents.cell_selected.emit(clicked_cell)
```

```gdscript
# 接收「點擊格子」事件，組裝移動請求（路徑由 GDExtension 計算）
# 可放在 InputHandler 或 TurnManager 內

func _on_cell_selected(cell: Vector2i) -> void:
    var player_cell: = GamepieceRegistry.get_cell(Player.gamepiece)
    if cell == player_cell:
        return
    
    var action: = PlayerAction.new()
    action.type = PlayerAction.Type.MOVE_TO  # 長途移動，讓 GDExtension 算路徑
    action.target_cell = cell
    TurnManager.player_act(action)
```

### 5.3 新版 `TurnManager`（autoload）

```gdscript
# turn_manager.gd
extends Node

var _input_locked: bool = false


func player_act(action: PlayerAction) -> void:
    if _input_locked:
        return
    _input_locked = true
    
    GameEvents.input_paused.emit(true)
    
    var result: ActionResult = GameEngine.submit_action(action)
    
    if result.is_valid:
        await next_turn(result.time_cost)
    
    GameEvents.input_paused.emit(false)
    _input_locked = false


func next_turn(elapsed_time: float) -> void:
    GameEngine.advance_time(elapsed_time)
    
    var updates: Array[StateUpdate] = GameEngine.poll_state_updates()
    
    # 可以把更新分批：先處理移動、再處理戰鬥效果、再處理 UI
    var move_updates: = updates.filter(func(u): return u.type == StateUpdate.Type.MOVE)
    var other_updates: = updates.filter(func(u): return u.type != StateUpdate.Type.MOVE)
    
    # 同步播放所有移動動畫（敵我同時動）
    var move_promises: Array = []
    for u in move_updates:
        var gp: = _get_or_spawn_gamepiece(u)
        if gp:
            move_promises.append(gp.move_to_cell(u.target_cell))
    
    for promise in move_promises:
        await promise
    
    # 逐一處理其他更新
    for u in other_updates:
        await _apply_update(u)
    
    GameEvents.turn_ended.emit(elapsed_time)


func _get_or_spawn_gamepiece(update: StateUpdate) -> Gamepiece:
    var gp: = GamepieceRegistry.get_gamepiece(update.source_cell)
    if gp == null and update.type == StateUpdate.Type.MOVE:
        # 若找不到（可能是首次出現），改用 entity_id 找
        gp = GamepieceRegistry.get_gamepiece_by_entity_id(update.entity_id)
    return gp


func _apply_update(update: StateUpdate) -> void:
    var gp: = GamepieceRegistry.get_gamepiece(update.source_cell) \
           if update.source_cell != Gameboard.INVALID_CELL \
           else null
    
    match update.type:
        StateUpdate.Type.ANIMATION:
            if gp:
                gp.animation.play(update.animation_name)
                if update.wait_for_finish:
                    await gp.animation.animation_finished
        
        StateUpdate.Type.ENTITY_SPAWNED:
            var new_gp_scene: PackedScene = load(update.scene_path)
            var new_gp: Gamepiece = new_gp_scene.instantiate()
            new_gp.entity_id = update.entity_id
            MapManager.current_map.add_child(new_gp)
            new_gp.position = Gameboard.cell_to_pixel(update.target_cell)
        
        StateUpdate.Type.ENTITY_DESTROYED:
            if gp:
                gp.animation.play("death")
                await gp.animation.animation_finished
                gp.queue_free()
        
        StateUpdate.Type.DIALOGUE_STARTED:
            GameEvents.dialogue_started.emit(update.dialogue_session_id)
            await GameEvents.dialogue_ended  # 等玩家看完對話
        
        StateUpdate.Type.MAP_CHANGE:
            await MapManager.switch_to(update.target_map_id)
        
        StateUpdate.Type.STATS_CHANGED:
            GameEvents.entity_stats_changed.emit(update.entity_id, update.stats_snapshot)
```

### 5.4 新版 `GameEvents`（取代 `FieldEvents` + `CombatEvents`）

```gdscript
# game_events.gd (autoload，取代 field_events.gd 與 combat_events.gd)
extends Node

## 輸入相關
signal input_paused(is_paused: bool)
signal cell_selected(cell: Vector2i)
signal interaction_selected(entity_id: int)

## 回合相關
signal turn_ended(elapsed_time: float)

## 地圖相關
signal map_changed(map_id: StringName)

## 對話相關
signal dialogue_started(session_id: int)
signal dialogue_ended

## 實體相關
signal entity_stats_changed(entity_id: int, stats: EntityStatsSnapshot)
signal player_died
```

---

## 第 6 章：GDExtension 最小 API 規格

本章整合前述設計，給出第一版 GDExtension 必須實作的完整介面。

```cpp
// game_engine.h（GDExtension C++ 對外介面）
class GameEngine : public godot::Node {
    GDCLASS(GameEngine, Node)

public:
    // ─── 核心迴圈 ───
    godot::Ref<ActionResult> submit_action(godot::Ref<PlayerAction> action);
    void advance_time(float elapsed_time);
    godot::TypedArray<StateUpdate> poll_state_updates();

    // ─── 對話 ───
    godot::Ref<DialogueLine> get_next_dialogue_line(int session_id);
    godot::Ref<DialogueLine> submit_dialogue_choice(int session_id, int choice_index);

    // ─── 地圖 ───
    godot::String get_local_map_scene_path(godot::StringName map_id);

    // ─── 查詢（UI 用，非每幀）───
    godot::Ref<EntityStatsSnapshot> get_entity_stats(int entity_id);
    godot::TypedArray<godot::String> get_player_inventory();

    // ─── Debug ───
    godot::String debug_dump_state();
};
```

對應 GDScript 側可見的暴露型別：

```
PlayerAction (RefCounted)    - type, direction, target_cell, item_id, skill_id
ActionResult (RefCounted)    - is_valid: bool, time_cost: float, message: String
StateUpdate (RefCounted)     - type: Type, entity_id: int, source_cell, target_cell,
                               animation_name, dialogue_session_id, target_map_id,
                               scene_path, stats_snapshot, wait_for_finish: bool
DialogueLine (RefCounted)    - type: Type(TEXT/CHOICES/END), speaker, text, choices
EntityStatsSnapshot(RefCounted) - hp, max_hp, mp, max_mp, ... (唯讀)
```

---

## 第 7 章：實作順序（Milestone 清單）

### Milestone 1：靜態單地圖可移動（不含 GDExtension）

- [ ] 從 godot-open-rpg 複製 `gameboard/`、`gamepiece_registry.gd`、`directions.gd`
- [ ] 改造 `gamepiece.gd`（移除 Path2D，改用 Tween）
- [ ] 建立 `GameEvents` autoload（Signal Bus）
- [ ] 建立 `TurnManager` autoload（先用 GDScript mock 版 `GameEngine`）
- [ ] 建立 `InputHandler`，WASD 觸發 `player_act(MOVE)`
- [ ] mock `GameEngine.submit_action(MOVE)` 直接回傳 `{is_valid: true, time_cost: 100}`
- [ ] mock `poll_state_updates()` 回傳玩家移動一格的 `StateUpdate`
- [ ] **驗收**：玩家可以用 WASD 在 Tilemap 上一格一格移動，每次按鍵 = 一回合

### Milestone 2：雙地圖切換

- [ ] 建立 `MapManager` autoload
- [ ] 建立 `WorldMap` 與 `LocalMap` 場景
- [ ] mock `GameEngine` 在玩家踩到特定格時回傳 `StateUpdate.MAP_CHANGE`
- [ ] `TurnManager._apply_update()` 中呼叫 `MapManager.switch_to()`
- [ ] **驗收**：玩家在世界地圖上走到城鎮格，畫面切換到城鎮地圖；按 EXIT 返回

### Milestone 3：NPC 移動（GDExtension AI）

- [ ] GDExtension 實作 `submit_action` 與 `advance_time`
- [ ] GDExtension 在 `advance_time` 後計算 NPC 移動，push `StateUpdate.MOVE` 到 pending 列表
- [ ] `poll_state_updates()` 回傳玩家 + NPC 的移動
- [ ] GDScript `next_turn()` 同步播放所有移動動畫
- [ ] **驗收**：每次玩家移動，NPC 也移動一步（全部同時播動畫）

### Milestone 4：對話系統

- [ ] GDExtension 在玩家 `submit_action(TALK)` 時回傳 `ActionResult`，並在 `poll_state_updates()` 加入 `StateUpdate.DIALOGUE_STARTED`
- [ ] 建立對話 UI 節點，監聽 `GameEvents.dialogue_started`
- [ ] 對話 UI 呼叫 `GameEngine.get_next_dialogue_line(session_id)` 取得文本
- [ ] 選擇後呼叫 `GameEngine.submit_dialogue_choice(session_id, idx)` 取得下一行
- [ ] **驗收**：走到 NPC 旁邊按 Space，出現對話框，文本來自 GDExtension

### Milestone 5：戰鬥視覺（在地圖上打架）

- [ ] GDExtension 在玩家 `submit_action(ATTACK)` 後 push `StateUpdate.ANIMATION("attack")`（玩家）、`StateUpdate.ANIMATION("hit")`（敵人）、可能有 `StateUpdate.STATS_CHANGED`
- [ ] 建立 HP bar UI，監聽 `GameEvents.entity_stats_changed`
- [ ] 若敵人死亡，GDExtension push `StateUpdate.ENTITY_DESTROYED`
- [ ] **驗收**：玩家攻擊旁邊的敵人，播放攻擊動畫，敵人 HP 條更新，死亡後消失

---

## 附錄：新版 Autoload 清單

| Autoload 名稱 | 取代原本 | 職責 |
| :--- | :--- | :--- |
| `GameEngine` | —（新增） | GDExtension 後端單例 |
| `TurnManager` | `Field` | 核心迴圈（player_act / next_turn） |
| `MapManager` | —（新增） | 雙地圖切換 |
| `GameEvents` | `FieldEvents` + `CombatEvents` | 統一事件匯流排 |
| `Gameboard` | `Gameboard`（保留） | 格子座標系統 |
| `GamepieceRegistry` | `GamepieceRegistry`（保留） | 格子 ↔ Gamepiece 映射 |
| `Player` | `Player`（保留，簡化） | 玩家當前 Gamepiece 持有者 |
| `Camera` | `Camera`（保留） | 相機跟隨 |
| `Transition` | `Transition`（保留） | 畫面轉場 |
| `Music` | `Music`（保留） | 背景音樂 |
