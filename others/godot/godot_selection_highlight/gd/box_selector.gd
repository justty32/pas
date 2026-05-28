class_name BoxSelector extends Control

# 框選 helper（落實 CONCEPT 待決事項「選取框拖曳」）。
# 掛在 CanvasLayer 上覆蓋整個視窗即可。
#
# 用法：
#   var box := BoxSelector.new()
#   box.candidates_provider = func() -> Array: return all_units  # 提供候選清單
#   box.world_pos_extractor = func(unit) -> Vector2:             # 把 unit 投影到螢幕
#       return camera.unproject_position(unit.global_position)
#   box.selection_committed.connect(_on_selection_committed)
#   add_child(box)
#
# 主流程：左鍵按下 → 拖曳出框 → 放開 → 發 signal 回傳框內 unit 清單。

signal selection_committed(units: Array, additive: bool)

@export var box_color: Color = Color(1.0, 0.85, 0.0, 0.15)
@export var border_color: Color = Color(1.0, 0.85, 0.0, 0.9)
@export var border_width: float = 1.5
@export var min_drag_pixels: float = 4.0  # 小於此距離視為點擊不算框選

var candidates_provider: Callable
var world_pos_extractor: Callable

var _dragging: bool = false
var _start: Vector2
var _end: Vector2
var _additive: bool = false


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS  # 不擋下層輸入


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_dragging = true
			_start = event.position
			_end = event.position
			_additive = event.shift_pressed
			queue_redraw()
		else:
			if _dragging:
				_dragging = false
				if _start.distance_to(event.position) >= min_drag_pixels:
					_commit()
				queue_redraw()
	elif event is InputEventMouseMotion and _dragging:
		_end = event.position
		queue_redraw()


func _draw() -> void:
	if not _dragging:
		return
	var rect := _current_rect()
	draw_rect(rect, box_color, true)
	draw_rect(rect, border_color, false, border_width)


func _current_rect() -> Rect2:
	var topleft := Vector2(min(_start.x, _end.x), min(_start.y, _end.y))
	var size := (_end - _start).abs()
	return Rect2(topleft, size)


func _commit() -> void:
	if candidates_provider.is_null() or world_pos_extractor.is_null():
		push_warning("BoxSelector: candidates_provider / world_pos_extractor 未設定")
		return
	var rect := _current_rect()
	var hits: Array = []
	for unit in candidates_provider.call():
		var screen_pos: Vector2 = world_pos_extractor.call(unit)
		if rect.has_point(screen_pos):
			hits.append(unit)
	selection_committed.emit(hits, _additive)
