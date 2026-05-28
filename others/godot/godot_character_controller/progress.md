# godot_character_controller — 進度保存

> 最後更新：2026-05-28。新建單元（不在原本 13 個 CONCEPT 內）。

## 一句話：這是什麼

策略單位的**行為層** controller：吃路徑、沿格走、發狀態 signal。
與 `godot_character` / `godot_character_3d`（視覺層，紙娃娃 + 骨骼動畫）互補。

## 為什麼新建

`godot_character{,_3d}` CONCEPT 內容是「視覺呈現」（Skeleton2D + Bone2D / Skeleton3D + 紙娃娃換裝）。
但**讓角色實際在場上移動**是另一個責任：吃命令、沿路徑、抵達 signal、被中斷處理。
這層在 mapcore demo 端寫在 `world_map_3d_interaction.gd` 內，與 UI / 點擊輸入混雜，難以
脫耦複用。本目錄抽出。

## 範圍邊界

**做**：
- 策略單位 controller（接 `move_along_path(path)`）
- 動畫狀態 signal（`state_changed(prev, next)`）給視覺層 hook
- 2D + 3D 平行雙版

**不做**：
- platformer 走跳（CharacterBody3D 重力跳躍）—— 未來需要時新建 `godot_character_platformer/`
- 戰鬥邏輯、AI 決策

## 檔案清單

```
godot_character_controller/
├── CONCEPT.md
├── gd/
│   ├── unit_state.gd            # UnitState：State enum + AnimationTree 狀態名映射
│   ├── unit_controller_3d.gd    # UnitController3D Node3D（含地形高度 follow）
│   └── unit_controller_2d.gd    # UnitController2D Node2D
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| UnitState | State enum 5 種 + name_of + anim_state 映射 | ✅ 完成 |
| UnitController3D | move_along_path / stop / 平滑插值 / 地形高度 follow / 阻擋 signal | ✅ 完成 |
| UnitController2D | 3D 版去掉 Y 軸的對等實作 | ✅ 完成 |
| 視覺層銜接 | 訂閱 state_changed 切 AnimationTree | ❌ 未做（等 godot_character 啟動） |
| 真機驗證 | Godot 4 + mapcore find_path 串接走一單位 | ⏸ **待真機驗證** |

## 設計重點

### 1. State 是 setter 觸發 signal
```gdscript
var state: int = UnitState.State.IDLE:
    set(v):
        if state != v:
            var prev := state
            state = v
            state_changed.emit(prev, v)
```
外部任何地方寫 `unit.state = UnitState.State.ATTACKING` 都會自動發 signal，視覺層只訂閱一條。

### 2. 路徑輸入接受 `Vector2i` 或 `Vector2`/`Vector3`
策略遊戲尋路器（mapcore.find_path）回 `Array[Vector2i]`，但 GDScript 沒辦法直接 type-check
mapcore 的 `TypedArray<Vector2i>`，所以 `move_along_path` 接 `Array` 並在內部自動偵測。
`Vector2`/`Vector3` 也接受，自動依 `tile_size` 反向換成 cell。

### 3. 高度從外部 Callable 注入
`UnitController3D.height_provider` 是 `Callable(cell: Vector2i) -> float`。
典型用法：
```gdscript
controller.height_provider = func(cell: Vector2i) -> float:
    return map_data.get_height_value(cell.x, cell.y) * height_scale
```
這樣 controller 不依賴 mapcore，但能跟著地形起伏走。

### 4. 平滑 vs 瞬移
`smooth_step` 預設 true：用 step_elapsed/step_seconds 線性插值，動畫順滑。
False 時每格瞬移，適合純回合制（每秒走一格的視覺）。

### 5. 中斷策略（CONCEPT 待決事項）
途中收到新 path 時，**當前步走完才切**：呼叫 `move_along_path()` 會把新 path 套上去，
但當前 `_step_from → _step_to` 的插值不打斷。下一格才走新路徑。
若要立刻切，呼叫端先 `stop()` 再 `move_along_path()`。

## 用法範例

### 3D 串接 mapcore_godot
```gdscript
var unit := UnitController3D.new()
unit.tile_size = 1.0
unit.step_seconds = 0.15
unit.height_provider = func(cell: Vector2i) -> float:
    return map_data.get_height_value(cell.x, cell.y) * 3.0
unit.passable_check = func(cell: Vector2i) -> bool:
    return map_data.get_terrain(cell.x, cell.y) != MapCoreMapData.TERRAIN_OCEAN
add_child(unit)
unit.teleport_to_cell(Vector2i(10, 10))

# 玩家點擊目標格 → 規劃路徑 → 命令單位
var path := map_data.find_path(Vector2i(10, 10), Vector2i(20, 30))
unit.move_along_path(path)
unit.arrived.connect(func(_pos: Vector3) -> void: print("到了"))
```

### 動畫銜接（待 godot_character 啟動時對齊）
```gdscript
unit.state_changed.connect(func(_prev: int, next: int) -> void:
    var anim_name := UnitState.anim_state(next)  # e.g. &"walk"
    $AnimationTree.set("parameters/playback", anim_name))
```

### Camera 跟隨
```gdscript
unit.step_completed.connect(func(_cell, world_pos: Vector3) -> void:
    camera_rig.focus(world_pos))
```

## 與其他模組的串接

| 模組 | 互動 |
|------|------|
| `mapcore_godot` | path 來源（`find_path`）、高度（`get_height_value`）、地形可通行性 |
| `godot_camera_rig` | `step_completed` signal → `camera.focus()` 跟隨單位 |
| `godot_selection_highlight` | 上層選取邏輯：選 unit 後 `apply_3d_recursive(unit.get_visual_root())` |
| `godot_character{,_3d}`（視覺層，未做） | 訂閱 `state_changed`、`step_completed` 切動畫；視覺節點作為 controller 的子節點 |
| `godot_world_map_3d` | 提供 map_data，供 height_provider / passable_check 查詢 |

## 待決事項（從 CONCEPT.md 帶過來）

- [x] 移動速度單位 = 每格秒數（`step_seconds`，與 mapcore demo 對齊）
- [x] 中斷策略 = 「當前步走完才切」
- [x] 平滑插值 = 預設開（`smooth_step`）
- [ ] 路徑視覺化（剩餘步數線條）→ 留給上層系統，本檔暴露 `get_remaining_path()` 讓外部自繪

## 下一步（按需）

1. **真機驗證**：Godot 4 + mapcore_godot demo 場景，掛 UnitController3D 與單位 mesh，
   點地圖看走路。
2. **godot_character_3d 視覺層啟動**：把骨骼動畫 + AnimationTree 接上 `state_changed` signal。
3. **Platformer 變體**（未來）：另開 `godot_character_platformer/`，做 CharacterBody3D 走跳。
