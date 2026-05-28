class_name UnitController2D extends Node2D

# 策略單位 2D controller：吃 cell 路徑沿格走。
# 介面與 UnitController3D 對等，2D 不用考慮高度。

signal state_changed(prev: int, next: int)
signal arrived(at: Vector2)
signal step_completed(cell: Vector2i, world_pos: Vector2)
signal path_blocked()

@export var tile_size: float = 64.0
@export var step_seconds: float = 0.12
@export var smooth_step: bool = true

var state: int = UnitState.State.IDLE:
	set(v):
		if state != v:
			var prev := state
			state = v
			state_changed.emit(prev, v)

var passable_check: Callable  # Callable(cell: Vector2i) -> bool

var _path_cells: Array[Vector2i] = []
var _step_index: int = 0
var _step_elapsed: float = 0.0
var _step_from: Vector2
var _step_to: Vector2


func move_along_path(path: Array) -> void:
	if path.is_empty():
		return
	_path_cells.clear()
	for p in path:
		if p is Vector2i:
			_path_cells.append(p)
		elif p is Vector2:
			_path_cells.append(Vector2i(int(p.x / tile_size), int(p.y / tile_size)))
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


func _prepare_next_step() -> void:
	if _step_index + 1 >= _path_cells.size():
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


func _cell_to_world(cell: Vector2i) -> Vector2:
	return Vector2((cell.x + 0.5) * tile_size, (cell.y + 0.5) * tile_size)


func _is_passable(cell: Vector2i) -> bool:
	if passable_check.is_null():
		return true
	return passable_check.call(cell)
