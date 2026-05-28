class_name Character3D extends Node3D

# 3D 角色整合 facade：把 UnitController3D（行為）、PaperDoll3D（換裝）、
# CharacterAnimator（動畫切換）三者串起來。
#
# 預期場景結構（節點名稱可在 inspector 改，重點是有這些角色）：
#   Character3D (本腳本)
#   ├── UnitController3D                    ← @export controller
#   ├── Visual (Node3D, 通常從 .glb 展開)
#   │   ├── Skeleton3D
#   │   │   └── (mesh + bones)
#   │   ├── AnimationPlayer
#   │   └── AnimationTree (選用)
#   └── PaperDoll3D                          ← @export paper_doll
#
# 此 facade 不規範 Visual 子樹細節（由 .glb 匯入決定），只提供統一 API。

signal equipped(slot_name: String, mesh: Mesh)
signal arrived(at: Vector3)
signal state_changed(prev: int, next: int)

@export var controller: UnitController3D
@export var paper_doll: PaperDoll3D
@export var animation_player: AnimationPlayer
@export var animation_tree: AnimationTree

var _animator: CharacterAnimator


func _ready() -> void:
	if controller == null:
		controller = _find_child_of_type(self, "UnitController3D")
	if paper_doll == null:
		paper_doll = _find_child_of_type(self, "PaperDoll3D")
	if animation_tree == null:
		animation_tree = _find_first(self, AnimationTree)
	if animation_player == null:
		animation_player = _find_first(self, AnimationPlayer)

	_animator = CharacterAnimator.new()
	if animation_tree:
		_animator.bind(animation_tree, controller)
	elif animation_player:
		_animator.bind_player(animation_player, controller)
	else:
		push_warning("Character3D: 找不到 AnimationTree 或 AnimationPlayer，動畫切換停用")

	if controller:
		controller.arrived.connect(func(pos: Vector3) -> void: arrived.emit(pos))
		controller.state_changed.connect(func(p: int, n: int) -> void: state_changed.emit(p, n))
	if paper_doll:
		paper_doll.slot_changed.connect(func(slot: String, m: Mesh) -> void:
			equipped.emit(slot, m))


# ── 對外 API（一行呼叫）──────────────────────────────────────────────────

func move_along_path(path: Array) -> void:
	if controller:
		controller.move_along_path(path)


func stop() -> void:
	if controller:
		controller.stop()


func teleport_to_cell(cell: Vector2i) -> void:
	if controller:
		controller.teleport_to_cell(cell)


func equip(slot_name: String, mesh: Mesh, material: Material = null) -> void:
	if paper_doll:
		paper_doll.equip(slot_name, mesh, material)


func unequip(slot_name: String) -> void:
	if paper_doll:
		paper_doll.unequip(slot_name)


func get_state() -> int:
	return controller.state if controller else UnitState.State.IDLE


# 給 selection_highlight 用：回傳所有需要套描邊的 MeshInstance3D。
# 包含 paper doll slots + Visual 子樹中的 mesh。
func get_outline_targets() -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	_collect_meshes(self, out)
	return out


# ── 內部 ──────────────────────────────────────────────────────────────────

static func _find_child_of_type(parent: Node, type_name: String) -> Node:
	for child in parent.get_children():
		if child.get_class() == type_name or (child.get_script() != null
				and child.get_script().get_global_name() == type_name):
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


static func _collect_meshes(node: Node, out: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D:
		out.append(node)
	for child in node.get_children():
		_collect_meshes(child, out)
