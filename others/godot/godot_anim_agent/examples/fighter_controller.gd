extends Node2D

@onready var anim_player: AnimationPlayer = $AnimationPlayer
@onready var anim_tree: AnimationTree    = $AnimationTree

var _tree_active := true

func _ready() -> void:
	anim_tree.active = true
	print("=== Fighter 動畫預覽 ===")
	print("Space（按住）→ do_punch（state machine idle→punch→idle）")
	print("1/2/3/4    → AnimationPlayer 直播 idle/punch/guard/step_in")
	print("T          → 關 AnimationTree，切到 AnimationPlayer 模式")

func _process(_delta: float) -> void:
	if not _tree_active:
		return
	var punch := Input.is_action_pressed("ui_accept")  # Space
	anim_tree["parameters/conditions/do_punch"] = punch

func _input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	match event.keycode:
		KEY_1: _play_direct("idle")
		KEY_2: _play_direct("punch")
		KEY_3: _play_direct("guard")
		KEY_4: _play_direct("step_in")
		KEY_T:
			_tree_active = false
			anim_tree.active = false
			print("AnimationTree 已關，切到 AnimationPlayer 模式")

func spawn_hit_spark() -> void:
	print("💥 hit spark")

func _play_direct(anim: String) -> void:
	_tree_active = false
	anim_tree.active = false
	anim_player.play(anim)
	print("▶ AnimationPlayer: ", anim)
