class_name UnitController3D extends Node3D

# 策略單位 3D controller：吃 path（Array[Vector2i] 或 Array[Vector3]），沿格走。
# 不耦合 mapcore；path 由外部給。
#
# 與 mapcore demo 端的單位移動差異：
#   - demo 的單位移動寫在 world_map_3d_interaction.gd 裏，與 UI/輸入混在一起
#   - 本檔抽出純 controller 行為，狀態 signal 與視覺/UI 解耦
#   - 支援 cell 路徑（Vector2i）與世界路徑（Vector3）兩種輸入

signal state_changed(prev: int, next: int)
signal arrived(at: Vector3)
signal step_completed(cell: Vector2i, world_pos: Vector3)
signal path_blocked()

@export var tile_size: float = 1.0
## 走一格秒數。0.12 = mapcore demo 預設。
@export var step_seconds: float = 0.12
## 走格之間是否平滑插值（false = 一格瞬移到下一格）
@export var smooth_step: bool = true
## 走到地形 Y 高度。外部可 set_height_provider 注入；若 null 永遠走 Y=0。
@export var follow_terrain_height: bool = true

var state: int = UnitState.State.IDLE:
	set(v):
		if state != v:
			var prev := state
			state = v
			state_changed.emit(prev, v)

# 外部注入：給定 cell (x, z) → 該格的 Y 高度（搭配 mapcore.get_height_value 或自製）。
# 簽名：Callable(cell: Vector2i) -> float
var height_provider: Callable

# 外部注入（選用）：判斷下一格能否通行。回傳 true 表示可走。
# 簽名：Callable(cell: Vector2i) -> bool
var passable_check: Callable

# ── 內部 ──────────────────────────────────────────────────────────────────
var _path_cells: Array[Vector2i] = []
var _step_index: int = 0
var _step_elapsed: float = 0.0
var _step_from: Vector3
var _step_to: Vector3


# ── 公開 API ──────────────────────────────────────────────────────────────

## 沿 cell 路徑移動。path 通常是 mapcore.find_path 的回傳。
## path 第一個 cell 應該是當前位置（會跳過不重複走）。
func move_along_path(path: Array) -> void:
	if path.is_empty():
		return
	_path_cells.clear()
	for p in path:
		if p is Vector2i:
			_path_cells.append(p)
		elif p is Vector3:
			_path_cells.append(Vector2i(int(p.x / tile_size), int(p.z / tile_size)))
	_step_index = 0
	_prepare_next_step()
	state = UnitState.State.MOVING


func stop() -> void:
	_path_cells.clear()
	_step_index = 0
	if state == UnitState.State.MOVING:
		state = UnitState.State.IDLE


func get_remaining_path() -> Array[Vector2i]:
	if _step_index >= _path_cells.size():
		return []
	return _path_cells.slice(_step_index)


func teleport_to_cell(cell: Vector2i) -> void:
	stop()
	position = _cell_to_world(cell)


# ── 每幀 ──────────────────────────────────────────────────────────────────

func _process(delta: float) -> void:
	if state != UnitState.State.MOVING:
		return
	if _step_index >= _path_cells.size():
		_finish_path()
		return

	if smooth_step:
		_step_elapsed += delta
		var t := clamp(_step_elapsed / step_seconds, 0.0, 1.0)
		position = _step_from.lerp(_step_to, t)
		if t >= 1.0:
			_advance_step()
	else:
		_step_elapsed += delta
		if _step_elapsed >= step_seconds:
			position = _step_to
			_advance_step()


# ── 內部步驟 ──────────────────────────────────────────────────────────────

func _prepare_next_step() -> void:
	if _step_index + 1 >= _path_cells.size():
		# 已在最後一格
		_finish_path()
		return
	var next_cell := _path_cells[_step_index + 1]
	if not _is_passable(next_cell):
		path_blocked.emit()
		stop()
		return
	_step_from = position
	_step_to = _cell_to_world(next_cell)
	_step_elapsed = 0.0


func _advance_step() -> void:
	_step_index += 1
	step_completed.emit(_path_cells[_step_index], _step_to)
	if _step_index + 1 >= _path_cells.size():
		_finish_path()
	else:
		_prepare_next_step()


func _finish_path() -> void:
	if _path_cells.is_empty():
		state = UnitState.State.IDLE
		return
	state = UnitState.State.IDLE
	arrived.emit(position)
	_path_cells.clear()
	_step_index = 0


func _cell_to_world(cell: Vector2i) -> Vector3:
	var y := 0.0
	if follow_terrain_height and not height_provider.is_null():
		y = height_provider.call(cell)
	return Vector3((cell.x + 0.5) * tile_size, y, (cell.y + 0.5) * tile_size)


func _is_passable(cell: Vector2i) -> bool:
	if passable_check.is_null():
		return true
	return passable_check.call(cell)
