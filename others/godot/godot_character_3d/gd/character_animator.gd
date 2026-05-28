class_name CharacterAnimator extends RefCounted

# 銜接 UnitController 的狀態 signal 與 AnimationTree 的狀態切換。
#
# 支援兩種 AnimationTree 接法：
#   ① 純 AnimationPlayer：直接 play(anim_name)
#   ② AnimationTree + StateMachine：set("parameters/playback", "travel" / state_name)
#
# 用法：
#   var anim := CharacterAnimator.new()
#   anim.bind(animation_tree, unit_controller)         # AnimationTree 路線
#   # 或
#   anim.bind_player(animation_player, unit_controller)  # 純 AnimationPlayer 路線

# 狀態名映射：可在 bind 前覆寫。預設等於 UnitState.DEFAULT_ANIM_MAP。
var anim_map: Dictionary = UnitState.DEFAULT_ANIM_MAP.duplicate()

# 切換動畫時的 crossfade（純 AnimationPlayer 路線才用得到）。
var crossfade_seconds: float = 0.15

# 內部：bound target
var _player: AnimationPlayer
var _tree: AnimationTree
var _playback_path: NodePath = NodePath("parameters/playback")
var _controller_state_signal: Signal


func bind(tree: AnimationTree, controller: Node) -> void:
	_tree = tree
	_tree.active = true
	_subscribe(controller)


func bind_player(player: AnimationPlayer, controller: Node) -> void:
	_player = player
	_subscribe(controller)


# 自訂 AnimationTree 的 playback 路徑（不是預設 parameters/playback 時）。
func set_playback_path(path: NodePath) -> void:
	_playback_path = path


func _subscribe(controller: Node) -> void:
	if not controller.has_signal(&"state_changed"):
		push_warning("CharacterAnimator: controller 沒有 state_changed signal")
		return
	controller.state_changed.connect(_on_state_changed)
	# 立即同步一次當前狀態
	if "state" in controller:
		_apply_state(controller.state)


func _on_state_changed(_prev: int, next: int) -> void:
	_apply_state(next)


func _apply_state(state: int) -> void:
	var anim_name := UnitState.anim_state(state, anim_map)
	if _tree:
		var playback = _tree.get(_playback_path)
		if playback and playback.has_method("travel"):
			playback.travel(anim_name)
		else:
			# fallback：找不到 StateMachinePlayback 就直接 set 參數值
			_tree.set(_playback_path, anim_name)
	elif _player:
		if _player.has_animation(anim_name):
			_player.play(anim_name, crossfade_seconds)
		else:
			push_warning("CharacterAnimator: AnimationPlayer 沒有動畫 '" + anim_name + "'")
