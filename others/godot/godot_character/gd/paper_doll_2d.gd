class_name PaperDoll2D extends Node2D

# 2D 紙娃娃換裝。對應 PaperDoll3D，但底層是 Bone2D + Sprite2D 而非 Skeleton3D + BoneAttachment3D。
#
# slot_specs 範例：
#   {
#     "weapon_main": {"bone_path": "Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R/Hand_R",
#                     "z_index": 5, "offset": Vector2.ZERO},
#     "armor_chest": {"bone_path": "Skeleton2D/Hip/Torso", "z_index": 2},
#     "helmet":      {"bone_path": "Skeleton2D/Hip/Torso/Head", "z_index": 4},
#   }
#
# Sprite2D 直接 add_child 到對應 Bone2D 下（不需要 BoneAttachment 中介）。
# 換裝時可選 SpriteMaterial（godot_material/）套材質疊加 shader。

signal slot_changed(slot_name: String, texture: Texture2D)

@export var skeleton: Skeleton2D
@export var slot_specs: Dictionary = {}


class Slot:
	var sprite: Sprite2D
	var bone: Bone2D
	var spec: Dictionary


var _slots: Dictionary = {}


func _ready() -> void:
	if skeleton == null:
		skeleton = _find_skeleton()
	if skeleton == null:
		push_warning("PaperDoll2D: 找不到 Skeleton2D，紙娃娃功能停用")
		return
	for slot_name in slot_specs:
		_create_slot(slot_name, slot_specs[slot_name])


# ── 公開 API ──────────────────────────────────────────────────────────────

func equip(slot_name: String, texture: Texture2D) -> void:
	var slot := _get_or_create_slot(slot_name)
	if slot == null:
		return
	slot.sprite.texture = texture
	slot_changed.emit(slot_name, texture)


# 帶 SpriteMaterial 套材質疊加（呼叫端要先載入 godot_material/）。
# material_tex / blend_mode / strength 對應 SpriteMaterial.apply 參數。
func equip_with_material(slot_name: String, texture: Texture2D,
		material_tex: Texture2D, strength: float = 1.0, blend_mode: int = 0,
		tint: Color = Color.WHITE) -> void:
	var slot := _get_or_create_slot(slot_name)
	if slot == null:
		return
	slot.sprite.texture = texture
	# SpriteMaterial 是 godot_material 提供，呼叫端確保已載入
	if ClassDB.class_exists("SpriteMaterial") or _has_class("SpriteMaterial"):
		SpriteMaterial.apply(slot.sprite, material_tex, strength, blend_mode, tint)
	slot_changed.emit(slot_name, texture)


func unequip(slot_name: String) -> void:
	var slot: Slot = _slots.get(slot_name)
	if slot == null:
		return
	slot.sprite.texture = null
	slot.sprite.material = null
	slot_changed.emit(slot_name, null)


func get_slot_sprite(slot_name: String) -> Sprite2D:
	var slot: Slot = _slots.get(slot_name)
	return slot.sprite if slot else null


# 給 selection_highlight 用：所有有 texture 的 sprite。
func get_all_sprites() -> Array[Sprite2D]:
	var out: Array[Sprite2D] = []
	for slot_name in _slots:
		var slot: Slot = _slots[slot_name]
		if slot.sprite.texture != null:
			out.append(slot.sprite)
	return out


# ── 內部 ──────────────────────────────────────────────────────────────────

func _find_skeleton() -> Skeleton2D:
	if get_parent() is Skeleton2D:
		return get_parent()
	for child in get_children():
		if child is Skeleton2D:
			return child
	if get_parent():
		for sibling in get_parent().get_children():
			if sibling is Skeleton2D:
				return sibling
	return null


func _get_or_create_slot(slot_name: String) -> Slot:
	if _slots.has(slot_name):
		return _slots[slot_name]
	if slot_specs.has(slot_name):
		return _create_slot(slot_name, slot_specs[slot_name])
	push_warning("PaperDoll2D: slot '" + slot_name + "' 未定義於 slot_specs")
	return null


func _create_slot(slot_name: String, spec: Dictionary) -> Slot:
	var bone_path: String = spec.get("bone_path", "")
	if bone_path.is_empty():
		push_warning("PaperDoll2D: slot '" + slot_name + "' 缺 bone_path")
		return null

	# bone_path 相對於 skeleton 的父節點
	var search_root := skeleton.get_parent() if skeleton.get_parent() else skeleton
	var bone_node := search_root.get_node_or_null(bone_path)
	if bone_node == null:
		# 嘗試從 skeleton 自己出發
		bone_node = skeleton.get_node_or_null(bone_path)
	if bone_node == null or not (bone_node is Bone2D):
		push_warning("PaperDoll2D: 找不到 Bone2D '" + bone_path + "'")
		return null

	var sprite := Sprite2D.new()
	sprite.name = "Slot_" + slot_name
	sprite.z_index = spec.get("z_index", 0)
	sprite.position = spec.get("offset", Vector2.ZERO)
	sprite.rotation = spec.get("rotation", 0.0)
	(bone_node as Bone2D).add_child(sprite)

	var slot := Slot.new()
	slot.sprite = sprite
	slot.bone = bone_node
	slot.spec = spec
	_slots[slot_name] = slot
	return slot


# 安全檢查 SpriteMaterial 是否被載入（class_name 不一定能即時被 ClassDB 看到）
func _has_class(name: String) -> bool:
	return ResourceLoader.exists("res://addons/godot_material/gd/sprite_material.gd")
