# 教學 02：前端設計與後端接口規格

> 精神：後端是 MUD 伺服器，只管丟事件；前端是客戶端，負責把事件變成畫面與聲音。
> 後端（GDExtension）只需要知道本文件定義的接口，不需要了解前端內部任何細節。
> 撰寫日期：2026-04-18

---

## 一、整體前端結構

```
Autoloads（全域服務）
  DisplayAPI      ← 後端的唯一入口。GDExtension 只和這裡說話。
  InputHandler    ← 玩家輸入的唯一出口。組裝 PlayerAction 送後端。
  VisualRegistry  ← visual_key → 場景/圖磚的查找表（純前端資料）

主場景 GameWorld
  MapDisplay                 ← 地圖視覺層
    TerrainLayer             ← TileMapLayer，顯示地板/牆/門
    EntityLayer              ← Node2D，容納所有 Gamepiece 節點
    EffectLayer              ← 粒子/Shader 特效
    FogLayer                 ← TileMapLayer，視野霧（FOV）

  HUD（永遠顯示在最上層）
    MessageLog               ← MUD 風格的文字訊息紀錄
    StatusPanel              ← 玩家 HP/MP/狀態列
    HotkeyBar                ← 技能快捷鍵列
    MiniMap                  ← 小地圖（可選）

  UIManager（Modal 層，純前端）
    InventoryDialog          ← 物品欄視窗
    CharacterDialog          ← 角色狀態視窗
    SpellbookDialog          ← 法術書視窗
    ConfirmDialog            ← 確認視窗
```

---

## 二、後端接口規格（GDExtension 必須實作）

### 2.1 `GameEngine`（GDExtension 暴露的 Autoload Node）

這是 **GDExtension 需要暴露的類別**。前端對後端的所有通信都透過這裡。

```gdscript
# GDExtension 需要暴露的 class（以 GDScript 表達接口）

class_name GameEngine extends Node

# ────────────────────────────────────────────
# 前端每幀呼叫（在 DisplayAPI._process 內）
# 推進後端一步邏輯，回傳本幀累積的事件批次
# 無事發生時回傳空陣列
# ────────────────────────────────────────────
func tick(delta: float) -> Array[GameEvent]: ...

# ────────────────────────────────────────────
# 玩家執行動作時，由 InputHandler 呼叫
# ────────────────────────────────────────────
func submit_action(action: PlayerAction) -> void: ...

# ────────────────────────────────────────────
# 純資料查詢（不影響遊戲邏輯、不消耗時間）
# 用於前端需要後端計算結果的場合
# 例如：法術預覽傷害、NPC 名稱、物品描述
# ────────────────────────────────────────────
func query(request: QueryRequest) -> QueryResult: ...
```

> **重點**：GDExtension 只需實作這三個方法。前端其餘的一切，後端不需要知道。

---

## 三、事件系統（GameEvent）

後端透過 `tick()` 的回傳值把事件丟給前端。
事件帶的是「視覺提示」，不是完整遊戲狀態。

### 3.1 `GameEvent` 基底類別

```gdscript
class_name GameEvent extends RefCounted

enum Type {
    # ── 地圖 ──
    TERRAIN_CHANGED,     # 某格地形改變（門開關、牆被炸）
    FOV_UPDATE,          # 可見格子清單更新

    # ── 實體生滅 ──
    ENTITY_SPAWN,        # 新實體出現在地圖上
    ENTITY_REMOVE,       # 實體消失（死亡、離開地圖）

    # ── 實體動作 ──
    ENTITY_MOVE,         # 實體從 A 格移到 B 格
    ENTITY_FACE,         # 實體轉向（不移動）
    ENTITY_ANIMATE,      # 播放指定動畫（攻擊、受擊、施法...）

    # ── 視覺特效（純前端，不影響邏輯）──
    EFFECT_AT,           # 在某格播放特效（爆炸、治療光）
    PROJECTILE_LAUNCH,   # 發射投射物視覺（從 A 飛向 B）

    # ── 文字訊息 ──
    LOG_MESSAGE,         # 丟給訊息日誌的一行文字

    # ── UI 資料更新 ──
    STATS_UPDATE,        # 玩家面板需要更新的數值

    # ── 流程控制 ──
    PLAYER_TURN,         # 現在輪到玩家行動，解鎖輸入
    MAP_ENTER,           # 進入新地圖（前端重新載入場景）
}

var type: Type
```

### 3.2 各事件的欄位定義

後端只需填這些欄位，前端決定怎麼顯示。

---

#### `TERRAIN_CHANGED`
```gdscript
var cell: Vector2i      # 哪一格
var tile_id: StringName # 地形的識別名（前端查 VisualRegistry）
                        # 例：&"wall_stone", &"door_wood_open"
```

---

#### `FOV_UPDATE`
```gdscript
var visible: Array[Vector2i]    # 本幀可見的格子
var remembered: Array[Vector2i] # 已探索但目前不可見的格子
# 前端據此更新 FogLayer
```

---

#### `ENTITY_SPAWN`
```gdscript
var entity_id: int       # 後端分配的唯一 ID（前端用來追蹤這個實體）
var cell: Vector2i       # 出現位置
var visual_key: StringName  # 外觀識別名，前端查 VisualRegistry
                            # 例：&"goblin_warrior", &"player_human"
var direction: int       # 面向（Directions.Points 枚舉值）
var layer: int           # 哪個層：ACTOR=0, ITEM=1（決定渲染優先序）
```

---

#### `ENTITY_REMOVE`
```gdscript
var entity_id: int
# 前端找到對應 Gamepiece，播放消失效果後移除
```

---

#### `ENTITY_MOVE`
```gdscript
var entity_id: int
var from_cell: Vector2i
var to_cell: Vector2i
# 前端：播放移動動畫，更新 EntityRegistry 的位置
```

---

#### `ENTITY_FACE`
```gdscript
var entity_id: int
var direction: int
# 前端：更新 Gamepiece 面向，不移動
```

---

#### `ENTITY_ANIMATE`
```gdscript
var entity_id: int
var animation: StringName  # 例：&"attack", &"hurt", &"cast", &"death"
var wait: bool             # true = 前端等動畫播完再繼續下一個事件
```

---

#### `EFFECT_AT`
```gdscript
var cell: Vector2i
var effect_key: StringName  # 前端查 VisualRegistry 決定播哪個特效
                             # 例：&"explosion_fire", &"heal_green"
var duration: float          # 特效持續時間（秒），-1 = 播完自停
```

---

#### `PROJECTILE_LAUNCH`
```gdscript
var from_cell: Vector2i
var to_cell: Vector2i
var visual_key: StringName   # 投射物外觀，例：&"arrow", &"fireball"
var speed: float             # 格/秒，前端控制動畫速度
```

---

#### `LOG_MESSAGE`
```gdscript
var text: String       # 訊息內文，支援 BBCode（[color=#ff0000]紅字[/color]）
var category: StringName  # 分類，供前端過濾顯示
                          # 例：&"combat", &"system", &"loot"
```

---

#### `STATS_UPDATE`
```gdscript
# 後端只送「有變化的欄位」，前端更新對應 UI 元件
# 使用 Dictionary 讓後端彈性選擇要更新哪些
var data: Dictionary
# 例：{"hp": 45, "hp_max": 100, "mp": 20, "status_effects": ["burn", "slow"]}
```

---

#### `PLAYER_TURN`
```gdscript
# 無額外欄位
# 前端收到後解鎖輸入，等待 InputHandler 送出 PlayerAction
```

---

#### `MAP_ENTER`
```gdscript
var map_id: StringName      # 要進入的地圖識別名
var player_cell: Vector2i   # 玩家在新地圖的起始位置
var map_width: int
var map_height: int
# 前端：重新初始化 MapDisplay，清空所有 Gamepiece
```

---

## 四、前端送給後端的資料（`PlayerAction`）

```gdscript
class_name PlayerAction extends RefCounted

enum Type {
    MOVE,        # 移動一格
    WAIT,        # 等待（跳過，消耗時間）
    ATTACK,      # 近戰攻擊方向
    USE_SKILL,   # 使用技能
    INTERACT,    # 互動（對話、開門、撿物）
    USE_ITEM,    # 使用物品欄中的物品
    PICKUP,      # 撿起腳下物品
    DROP,        # 丟棄物品
    DESCEND,     # 下樓（進入地圖）
    ASCEND,      # 上樓（回上層）
}

var type: Type
var direction: Vector2i    # MOVE / ATTACK / INTERACT 使用
var target_cell: Vector2i  # USE_SKILL 遠程目標
var skill_id: int          # USE_SKILL 使用
var item_index: int        # USE_ITEM / DROP 使用
```

---

## 五、純查詢接口（`QueryRequest` / `QueryResult`）

不影響遊戲邏輯，用於前端顯示資訊。

```gdscript
class_name QueryRequest extends RefCounted

enum Type {
    ENTITY_INFO,     # 取得某實體的資訊（名稱、描述）
    SKILL_PREVIEW,   # 法術傷害/效果預覽
    ITEM_DESC,       # 物品描述文字
    PLAYER_STATS,    # 完整玩家數值（開啟角色面板時）
    INVENTORY,       # 物品欄清單（開啟物品欄時）
    MAP_CELL_INFO,   # 某格的資訊（滑鼠懸停 tooltip）
}

var type: Type
var entity_id: int       # 視查詢類型而定
var cell: Vector2i
var skill_id: int
var item_index: int
```

```gdscript
class_name QueryResult extends RefCounted

var success: bool
var text: String            # 通用文字結果
var data: Dictionary        # 結構化資料，視查詢類型而異
```

---

## 六、`DisplayAPI`（前端核心，Autoload）

這是前端的總調度，負責：
1. 每幀呼叫 `GameEngine.tick()` 取得事件
2. 把事件派發給各個前端元件

```gdscript
# display_api.gd
extends Node

# 各前端子系統在 _ready() 中連結到這些 signal
signal terrain_changed(event: GameEvent)
signal fov_updated(event: GameEvent)
signal entity_spawned(event: GameEvent)
signal entity_removed(event: GameEvent)
signal entity_moved(event: GameEvent)
signal entity_faced(event: GameEvent)
signal entity_animated(event: GameEvent)
signal effect_requested(event: GameEvent)
signal projectile_requested(event: GameEvent)
signal message_logged(event: GameEvent)
signal stats_updated(event: GameEvent)
signal player_turn_started()
signal map_entered(event: GameEvent)


func _process(delta: float) -> void:
    var events: Array[GameEvent] = GameEngine.tick(delta)
    for event in events:
        _dispatch(event)


func _dispatch(event: GameEvent) -> void:
    match event.type:
        GameEvent.Type.TERRAIN_CHANGED:    terrain_changed.emit(event)
        GameEvent.Type.FOV_UPDATE:         fov_updated.emit(event)
        GameEvent.Type.ENTITY_SPAWN:       entity_spawned.emit(event)
        GameEvent.Type.ENTITY_REMOVE:      entity_removed.emit(event)
        GameEvent.Type.ENTITY_MOVE:        entity_moved.emit(event)
        GameEvent.Type.ENTITY_FACE:        entity_faced.emit(event)
        GameEvent.Type.ENTITY_ANIMATE:     entity_animated.emit(event)
        GameEvent.Type.EFFECT_AT:          effect_requested.emit(event)
        GameEvent.Type.PROJECTILE_LAUNCH:  projectile_requested.emit(event)
        GameEvent.Type.LOG_MESSAGE:        message_logged.emit(event)
        GameEvent.Type.STATS_UPDATE:       stats_updated.emit(event)
        GameEvent.Type.PLAYER_TURN:        player_turn_started.emit()
        GameEvent.Type.MAP_ENTER:          map_entered.emit(event)
```

---

## 七、前端各元件的職責與接線

### 7.1 `MapDisplay`

```gdscript
# map_display.gd
extends Node2D

@onready var terrain_layer: TileMapLayer = $TerrainLayer
@onready var entity_layer: Node2D        = $EntityLayer
@onready var effect_layer: Node2D        = $EffectLayer
@onready var fog_layer: TileMapLayer     = $FogLayer

# entity_id → Gamepiece 的本地表
var _entities: Dictionary[int, Gamepiece] = {}


func _ready() -> void:
    DisplayAPI.terrain_changed.connect(_on_terrain_changed)
    DisplayAPI.fov_updated.connect(_on_fov_updated)
    DisplayAPI.entity_spawned.connect(_on_entity_spawned)
    DisplayAPI.entity_removed.connect(_on_entity_removed)
    DisplayAPI.entity_moved.connect(_on_entity_moved)
    DisplayAPI.entity_faced.connect(_on_entity_faced)
    DisplayAPI.entity_animated.connect(_on_entity_animated)
    DisplayAPI.effect_requested.connect(_on_effect_requested)
    DisplayAPI.projectile_requested.connect(_on_projectile_requested)
    DisplayAPI.map_entered.connect(_on_map_entered)


func _on_terrain_changed(event: GameEvent) -> void:
    var tile_coords: = VisualRegistry.get_terrain_tile(event.tile_id)
    terrain_layer.set_cell(event.cell, tile_coords.source_id, tile_coords.atlas_coord)


func _on_entity_spawned(event: GameEvent) -> void:
    var scene: PackedScene = VisualRegistry.get_entity_scene(event.visual_key)
    var gp: Gamepiece = scene.instantiate()
    gp.entity_id = event.entity_id
    gp.position = Gameboard.cell_to_pixel(event.cell)
    gp.direction = event.direction
    entity_layer.add_child(gp)
    _entities[event.entity_id] = gp


func _on_entity_removed(event: GameEvent) -> void:
    var gp: = _entities.get(event.entity_id) as Gamepiece
    if gp:
        await gp.play_animation(&"death")
        gp.queue_free()
        _entities.erase(event.entity_id)


func _on_entity_moved(event: GameEvent) -> void:
    var gp: = _entities.get(event.entity_id) as Gamepiece
    if gp:
        await gp.move_to_cell(event.to_cell)


func _on_entity_animated(event: GameEvent) -> void:
    var gp: = _entities.get(event.entity_id) as Gamepiece
    if gp:
        if event.wait:
            await gp.play_animation(event.animation)
        else:
            gp.play_animation(event.animation)


func _on_effect_requested(event: GameEvent) -> void:
    var effect: = VisualRegistry.create_effect(event.effect_key)
    effect.position = Gameboard.cell_to_pixel(event.cell)
    effect_layer.add_child(effect)


func _on_projectile_requested(event: GameEvent) -> void:
    var proj: = VisualRegistry.create_projectile(event.visual_key)
    proj.launch(event.from_cell, event.to_cell, event.speed)
    effect_layer.add_child(proj)


func _on_map_entered(event: GameEvent) -> void:
    # 清空所有 entity，重設地圖大小
    for gp in _entities.values():
        gp.queue_free()
    _entities.clear()
    terrain_layer.clear()
    fog_layer.clear()
```

---

### 7.2 `MessageLog`（MUD 文字窗口）

```gdscript
# message_log.gd
extends PanelContainer

@onready var _text: RichTextLabel = $RichTextLabel
const MAX_LINES: = 200


func _ready() -> void:
    DisplayAPI.message_logged.connect(_on_message)


func _on_message(event: GameEvent) -> void:
    # 超過行數上限時移除最舊一行
    if _text.get_line_count() >= MAX_LINES:
        var lines: = _text.text.split("\n")
        lines = lines.slice(1)
        _text.text = "\n".join(lines)
    
    _text.append_text(event.text + "\n")
    _text.scroll_to_line(_text.get_line_count())
```

---

### 7.3 `StatusPanel`

```gdscript
# status_panel.gd
extends PanelContainer

@onready var _hp_bar: ProgressBar  = $HPBar
@onready var _mp_bar: ProgressBar  = $MPBar
@onready var _effects_list: HBoxContainer = $EffectsList


func _ready() -> void:
    DisplayAPI.stats_updated.connect(_on_stats_updated)


func _on_stats_updated(event: GameEvent) -> void:
    var d: = event.data
    if d.has("hp"):     _hp_bar.value     = d["hp"]
    if d.has("hp_max"): _hp_bar.max_value = d["hp_max"]
    if d.has("mp"):     _mp_bar.value     = d["mp"]
    if d.has("mp_max"): _mp_bar.max_value = d["mp_max"]
    if d.has("status_effects"):
        _rebuild_effects_icons(d["status_effects"])
```

---

### 7.4 `InputHandler`（Autoload）

輸入鎖只有在收到 `PLAYER_TURN` 後才解開。

```gdscript
# input_handler.gd
extends Node

var _can_act: bool = false


func _ready() -> void:
    DisplayAPI.player_turn_started.connect(func(): _can_act = true)


func _unhandled_input(event: InputEvent) -> void:
    if not _can_act:
        return
    
    var action: = _build_action(event)
    if action:
        _can_act = false          # 鎖定，直到後端再次送 PLAYER_TURN
        GameEngine.submit_action(action)


func _build_action(event: InputEvent) -> PlayerAction:
    if event.is_action_pressed("move_north"): return _move(Vector2i(0,-1))
    if event.is_action_pressed("move_south"): return _move(Vector2i(0, 1))
    if event.is_action_pressed("move_west"):  return _move(Vector2i(-1,0))
    if event.is_action_pressed("move_east"):  return _move(Vector2i(1, 0))
    if event.is_action_pressed("wait"):       return _wait()
    # ... 其他輸入
    return null


func _move(dir: Vector2i) -> PlayerAction:
    var a: = PlayerAction.new()
    a.type = PlayerAction.Type.MOVE
    a.direction = dir
    return a


func _wait() -> PlayerAction:
    var a: = PlayerAction.new()
    a.type = PlayerAction.Type.WAIT
    return a
```

---

### 7.5 `VisualRegistry`（Autoload，純前端資料）

後端只知道 `visual_key`（如 `&"goblin_warrior"`），這裡決定它長什麼樣。

```gdscript
# visual_registry.gd
extends Node

# entity visual_key → 場景路徑
const ENTITY_SCENES: Dictionary[StringName, String] = {
    &"player_human":   "res://scenes/actors/player.tscn",
    &"goblin_warrior": "res://scenes/actors/goblin_warrior.tscn",
    &"orc_brute":      "res://scenes/actors/orc_brute.tscn",
    &"arrow":          "res://scenes/projectiles/arrow.tscn",
    &"fireball":       "res://scenes/projectiles/fireball.tscn",
}

# terrain tile_id → TileMapLayer 的 source + atlas 座標
const TERRAIN_TILES: Dictionary[StringName, Dictionary] = {
    &"floor_stone":    {"source_id": 0, "atlas_coord": Vector2i(0, 0)},
    &"wall_stone":     {"source_id": 0, "atlas_coord": Vector2i(1, 0)},
    &"door_wood":      {"source_id": 0, "atlas_coord": Vector2i(2, 0)},
    &"door_wood_open": {"source_id": 0, "atlas_coord": Vector2i(3, 0)},
}

# effect visual_key → PackedScene
const EFFECT_SCENES: Dictionary[StringName, String] = {
    &"explosion_fire":  "res://scenes/effects/explosion_fire.tscn",
    &"heal_green":      "res://scenes/effects/heal_green.tscn",
    &"hit_slash":       "res://scenes/effects/hit_slash.tscn",
}


func get_entity_scene(key: StringName) -> PackedScene:
    return load(ENTITY_SCENES.get(key, "res://scenes/actors/unknown.tscn"))


func get_terrain_tile(key: StringName) -> Dictionary:
    return TERRAIN_TILES.get(key, {"source_id": 0, "atlas_coord": Vector2i(0, 0)})


func create_effect(key: StringName) -> Node2D:
    var path: = EFFECT_SCENES.get(key, "")
    if path.is_empty():
        return Node2D.new()
    return (load(path) as PackedScene).instantiate()


func create_projectile(key: StringName) -> Node2D:
    return get_entity_scene(key).instantiate()
```

---

## 八、後端接口一覽（實作清單）

這是 GDExtension 需要實作的完整清單，前端不需要其他東西。

### GDExtension 必須暴露的類別與方法

```
class GameEngine extends Node（Autoload）
  ├── tick(delta: float) -> Array[GameEvent]
  ├── submit_action(action: PlayerAction) -> void
  └── query(request: QueryRequest) -> QueryResult

class GameEvent extends RefCounted
  └── type: GameEvent.Type（enum，前端已定義）
  └── [各事件的欄位，見第三節]

class PlayerAction extends RefCounted
  └── type: PlayerAction.Type（enum，前端已定義）
  └── [方向、目標格、技能ID、物品索引]

class QueryRequest extends RefCounted
class QueryResult extends RefCounted
```

### GDExtension 需要使用的 visual_key 與 tile_id 規範

後端送出的所有 `visual_key`、`tile_id`、`effect_key` 必須在 `VisualRegistry` 中有對應項目。
這是前後端之間的**資料契約**，由雙方共同維護一份命名清單即可。

---

## 九、UIManager（純前端，與後端無關）

物品欄、角色面板等 UI 是純前端。只有在需要後端資料時才呼叫 `GameEngine.query()`：

```gdscript
# inventory_dialog.gd

func _on_open_pressed() -> void:
    # 需要後端資料時才查詢
    var req: = QueryRequest.new()
    req.type = QueryRequest.Type.INVENTORY
    var result: = GameEngine.query(req)
    
    _populate_list(result.data)


func _on_use_item(item_index: int) -> void:
    # 使用物品才送 PlayerAction（會影響遊戲邏輯）
    InputHandler.submit(PlayerAction.Type.USE_ITEM, item_index)
```

純瀏覽（翻頁、排序）完全在前端自己做，不通知後端。

---

## 十、前後端契約摘要

```
後端（GDExtension）負責：
  ✔ 決定誰何時行動（包含玩家）
  ✔ 計算所有邏輯結果
  ✔ 產生 GameEvent 清單
  ✔ 回應 PlayerAction
  ✔ 回應 QueryRequest

前端（GDScript）負責：
  ✔ 每幀呼叫 GameEngine.tick()
  ✔ 把 GameEvent 變成動畫、特效、文字
  ✔ 捕捉玩家輸入，在 _can_act=true 時組裝 PlayerAction
  ✔ 決定每個 visual_key 對應哪個場景/特效
  ✔ 管理純 UI 邏輯（不影響遊戲邏輯的 UI 操作）

兩端不需知道對方的內部實作。
唯一的契約是：GameEvent 的欄位定義 + visual_key 的命名清單。
```
