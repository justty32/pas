class_name Character2D extends Node2D

# 2D 角色整合 facade，對等於 Character3D。
# Godot 4 的 AnimationTree 同樣支援 2D，所以可以共用 CharacterAnimator
# （from godot_character_3d 那邊的）。本檔不重複實作 animator，直接引用。
#
# 預期場景結構：
#   Character2D (本腳本)
#   ├── UnitController2D                ← @export controller
#   ├── Skeleton2D                       ← 視覺骨骼樹
#   │   ├── Bone2D [Hip] ...
#   │   ├── Sprite2D [base body parts]
#   │   └── ...
#   ├── AnimationPlayer
#   ├── AnimationTree (選用)
#   └── PaperDoll2D                      ← @export paper_doll

signal equipped(slot_name: String, texture: Texture2D)
signal arrived(at: Vector2)
signal state_changed(prev: int, next: int)

@export var controller: UnitController2D
@export var paper_doll: PaperDoll2D
@export var animation_player: AnimationPlayer
@export var animation_tree: AnimationTree

var _animator: CharacterAnimator  # 跨 2D/3D 通用


func _ready() -> void:
	if controller == null:
		controller = _find_child_of_class(self, "UnitController2D")
	if paper_doll == null:
		paper_doll = _find_child_of_class(self, "PaperDoll2D")
	if animation_tree == null:
		animation_tree = _find_first(self, AnimationTree)
	if animation_player == null:
		animation_player = _find_first(self, AnimationPlayer)

	if controller and (animation_tree or animation_player):
		_animator = CharacterAnimator.new()
		if animation_tree:
			_animator.bind(animation_tree, controller)
		else:
			_animator.bind_player(animation_player, controller)

	if controller:
		controller.arrived.connect(func(pos: Vector2) -> void: arrived.emit(pos))
		controller.state_changed.connect(func(p: int, n: int) -> void: state_changed.emit(p, n))
	if paper_doll:
		paper_doll.slot_changed.connect(func(slot: String, t: Texture2D) -> void:
			equipped.emit(slot, t))


# ── 對外 API ─────────────────────────────────────────────────────────────

func move_along_path(path: Array) -> void:
	if controller:
		controller.move_along_path(path)


func stop() -> void:
	if controller:
		controller.stop()


func teleport_to_cell(cell: Vector2i) -> void:
	if controller:
		controller.teleport_to_cell(cell)


func equip(slot_name: String, texture: Texture2D) -> void:
	if paper_doll:
		paper_doll.equip(slot_name, texture)


func equip_with_material(slot_name: String, texture: Texture2D,
		material_tex: Texture2D, strength: float = 1.0,
		blend_mode: int = 0, tint: Color = Color.WHITE) -> void:
	if paper_doll:
		paper_doll.equip_with_material(slot_name, texture, material_tex,
				strength, blend_mode, tint)


func unequip(slot_name: String) -> void:
	if paper_doll:
		paper_doll.unequip(slot_name)


func get_state() -> int:
	return controller.state if controller else UnitState.State.IDLE


# 給 selection_highlight.apply_2d 用：回傳所有需要套描邊的 Sprite2D。
func get_outline_targets() -> Array[Sprite2D]:
	var out: Array[Sprite2D] = []
	_collect_sprites(self, out)
	return out


# ── 內部 ──────────────────────────────────────────────────────────────────

static func _find_child_of_class(parent: Node, type_name: String) -> Node:
	for child in parent.get_children():
		if child.get_script() != null and child.get_script().get_global_name() == type_name:
			return child
		if child.get_class() == type_name:
			return child
	return null


static func _find_first(root: Node, type) -> Node:
	for child in root.get_children():
		if is_instance_of(child, type):
			return child
		var nested := _find_first(child, type)
		if nested:
			return nested
	return null


static func _collect_sprites(node: Node, out: Array[Sprite2D]) -> void:
	if node is Sprite2D and (node as Sprite2D).texture != null:
		out.append(node)
	for child in node.get_children():
		_collect_sprites(child, out)
