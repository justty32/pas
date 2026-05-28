class_name PaperDoll3D extends Node3D

# 紙娃娃換裝管理。掛在 Skeleton3D 同層或其下，初始化時依 slot_specs 自動建立
# BoneAttachment3D + MeshInstance3D 結構。
#
# slot_specs 定義範例：
#   {
#     "weapon_main": {"bone": "Hand_R", "offset": Vector3(0, 0, 0)},
#     "helmet":      {"bone": "Head"},
#     "armor_chest": {"bone": "Chest"},
#     "armor_legs":  {"bone": "Thigh_L"},  # 護腿用 L 骨，R 對稱掛
#     "shield":      {"bone": "Hand_L"},
#   }
#
# 換裝 API：
#   doll.equip("weapon_main", sword_mesh, iron_material)
#   doll.unequip("helmet")
#   doll.set_slot_material("armor_chest", legendary_material)

signal slot_changed(slot_name: String, mesh: Mesh)

@export var skeleton: Skeleton3D
## slot 規範：name → {bone: String, offset?: Vector3, rotation?: Vector3}
@export var slot_specs: Dictionary = {}


class Slot:
	var attachment: BoneAttachment3D
	var mesh_instance: MeshInstance3D
	var bone_name: String


var _slots: Dictionary = {}  # slot_name: String → Slot


func _ready() -> void:
	if skeleton == null:
		# 嘗試從父節點或第一個子節點找 Skeleton3D
		skeleton = _find_skeleton()
	if skeleton == null:
		push_warning("PaperDoll3D: 找不到 Skeleton3D，紙娃娃功能停用")
		return
	for slot_name in slot_specs:
		_create_slot(slot_name, slot_specs[slot_name])


# ── 公開 API ──────────────────────────────────────────────────────────────

func equip(slot_name: String, mesh: Mesh, material: Material = null) -> void:
	var slot := _get_or_create_slot(slot_name)
	if slot == null:
		return
	slot.mesh_instance.mesh = mesh
	if material:
		slot.mesh_instance.material_override = material
	slot_changed.emit(slot_name, mesh)


func unequip(slot_name: String) -> void:
	var slot: Slot = _slots.get(slot_name)
	if slot == null:
		return
	slot.mesh_instance.mesh = null
	slot.mesh_instance.material_override = null
	slot_changed.emit(slot_name, null)


func set_slot_material(slot_name: String, material: Material) -> void:
	var slot: Slot = _slots.get(slot_name)
	if slot == null:
		return
	slot.mesh_instance.material_override = material


func get_slot_mesh(slot_name: String) -> Mesh:
	var slot: Slot = _slots.get(slot_name)
	return slot.mesh_instance.mesh if slot else null


func get_all_slots() -> Array[String]:
	var out: Array[String] = []
	for k in _slots.keys():
		out.append(k)
	return out


# 給 selection_highlight 用：回傳所有 MeshInstance3D（含 slot mesh），方便套描邊。
func get_all_meshes() -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	for slot_name in _slots:
		var slot: Slot = _slots[slot_name]
		if slot.mesh_instance.mesh != null:
			out.append(slot.mesh_instance)
	return out


# ── 內部 ──────────────────────────────────────────────────────────────────

func _find_skeleton() -> Skeleton3D:
	if get_parent() is Skeleton3D:
		return get_parent()
	for child in get_children():
		if child is Skeleton3D:
			return child
	# 同層搜尋
	if get_parent():
		for sibling in get_parent().get_children():
			if sibling is Skeleton3D:
				return sibling
	return null


func _get_or_create_slot(slot_name: String) -> Slot:
	if _slots.has(slot_name):
		return _slots[slot_name]
	if slot_specs.has(slot_name):
		return _create_slot(slot_name, slot_specs[slot_name])
	push_warning("PaperDoll3D: slot '" + slot_name + "' 未定義於 slot_specs")
	return null


func _create_slot(slot_name: String, spec: Dictionary) -> Slot:
	var bone_name: String = spec.get("bone", "")
	if bone_name.is_empty():
		push_warning("PaperDoll3D: slot '" + slot_name + "' 缺 bone 欄位")
		return null

	var bone_idx := skeleton.find_bone(bone_name)
	if bone_idx < 0:
		push_warning("PaperDoll3D: 骨骼 '" + bone_name + "' 在 Skeleton3D 中不存在")
		return null

	var attach := BoneAttachment3D.new()
	attach.name = "Attach_" + slot_name
	attach.bone_idx = bone_idx
	attach.bone_name = bone_name
	skeleton.add_child(attach)

	var mi := MeshInstance3D.new()
	mi.name = "Mesh_" + slot_name
	if spec.has("offset"):
		mi.position = spec["offset"]
	if spec.has("rotation"):
		mi.rotation = spec["rotation"]
	attach.add_child(mi)

	var slot := Slot.new()
	slot.attachment = attach
	slot.mesh_instance = mi
	slot.bone_name = bone_name
	_slots[slot_name] = slot
	return slot
