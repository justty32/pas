# 教學：紙娃娃裝備系統（Paper Doll & EquipmentManager）

本教學說明如何在 COGITO 中實作裝備槽系統：穿上護甲後改變防禦數值、武器附加到骨架對應位置、裝備欄 UI。

## 前置知識
- 已閱讀 [Level 3A: 屬性系統](../architecture/level3_attributes.md)。
- 已完成 [教學：Skyrim 升級系統](./skyrim_leveling_system.md)（`LevelManager` 已存在）。

---

## 一、EquipmentItemPD：擴充物品資源

COGITO 的物品繼承自 `InventoryItemPD`（`InventoryItemPD.gd`）。建立新資源類型：

建立 `res://scripts/equipment_item_pd.gd`：

```gdscript
# res://scripts/equipment_item_pd.gd
extends InventoryItemPD
class_name EquipmentItemPD

enum EquipSlot {
    HEAD,      # 頭盔
    CHEST,     # 胸甲
    HANDS,     # 手套
    FEET,      # 靴子
    RIGHT_HAND, # 右手武器
    LEFT_HAND,  # 左手/盾牌
}

## 裝備位置
@export var equip_slot: EquipSlot = EquipSlot.CHEST
## 裝備後附加到骨架的場景（含 MeshInstance3D）
@export var equip_mesh: PackedScene
## 防禦加成（減少傷害的固定值）
@export var defense_bonus: float = 0.0
## 攻擊加成（加算到武器傷害）
@export var attack_bonus: float = 0.0
## 升級時獲得 XP 的技能名稱（對應 LevelManager）
@export var armor_skill: String = "light_armor"
## 裝備重量（影響耐力消耗，選填）
@export var weight: float = 1.0
```

在 Godot Editor 中，`右鍵 → New Resource → EquipmentItemPD` 即可建立裝備資源。

---

## 二、為玩家加入骨架

COGITO 預設是純第一人稱、無全身骨架。開放世界或第三人稱切換需要加入：

**節點結構**（在 `CogitoPlayer` 下加入）：
```
CogitoPlayer
├── Head (Camera3D)            ← 現有
├── Body (CharacterBody3D)     ← 現有
├── PlayerSkeleton (Skeleton3D) ← 新增：載入人形骨架 Mesh
│   ├── BoneAttachment3D       ← 各裝備掛點
│   │   (bone_name: "Head")    name: "Attach_Head"
│   ├── BoneAttachment3D
│   │   (bone_name: "Spine")   name: "Attach_Chest"
│   ├── BoneAttachment3D
│   │   (bone_name: "RightHand") name: "Attach_RightHand"
│   └── BoneAttachment3D
│       (bone_name: "LeftHand")  name: "Attach_LeftHand"
```

**設定 BoneAttachment3D**：選取 BoneAttachment3D → Inspector → `Bone Name` 設為對應骨骼名稱（需與 Skeleton3D 的骨骼名稱一致）。

若只需第一人稱（不顯示身體），`PlayerSkeleton` 可設定：
- `Visibility Layer` 移除 Layer 1，加入只有鏡子/陰影用的 Layer
- 或直接 `visible = false`（純數值計算，無需顯示）

---

## 三、EquipmentManager：核心管理器

建立 `res://scripts/equipment_manager.gd`，作為 `CogitoPlayer` 的子節點（**不是** Autoload，因為需要存取玩家的骨架）：

```gdscript
# res://scripts/equipment_manager.gd
extends Node
class_name EquipmentManager

## 各槽位對應的 BoneAttachment3D 節點路徑
@export var attach_head: NodePath
@export var attach_chest: NodePath
@export var attach_right_hand: NodePath
@export var attach_left_hand: NodePath
@export var attach_feet: NodePath

## 目前各槽位裝備資源
var _equipped: Dictionary = {}   # EquipmentItemPD.EquipSlot → EquipmentItemPD
## 目前各槽位已實例化的 Mesh 節點
var _meshes: Dictionary = {}     # EquipmentItemPD.EquipSlot → Node3D

var _attachments: Dictionary = {}


func _ready() -> void:
    # 建立 slot → BoneAttachment 對應表
    _attachments = {
        EquipmentItemPD.EquipSlot.HEAD:       get_node_or_null(attach_head),
        EquipmentItemPD.EquipSlot.CHEST:      get_node_or_null(attach_chest),
        EquipmentItemPD.EquipSlot.RIGHT_HAND: get_node_or_null(attach_right_hand),
        EquipmentItemPD.EquipSlot.LEFT_HAND:  get_node_or_null(attach_left_hand),
        EquipmentItemPD.EquipSlot.FEET:       get_node_or_null(attach_feet),
    }


func equip(item: EquipmentItemPD) -> void:
    var slot = item.equip_slot
    # 先卸下同槽位舊裝備
    if _equipped.has(slot):
        unequip(slot)

    _equipped[slot] = item

    # 附加 Mesh 到骨架掛點
    if item.equip_mesh != null and _attachments.get(slot) != null:
        var mesh_node = item.equip_mesh.instantiate()
        _attachments[slot].add_child(mesh_node)
        _meshes[slot] = mesh_node


func unequip(slot: EquipmentItemPD.EquipSlot) -> EquipmentItemPD:
    if not _equipped.has(slot):
        return null
    var removed = _equipped[slot]

    # 移除 Mesh
    if _meshes.has(slot):
        _meshes[slot].queue_free()
        _meshes.erase(slot)
    _equipped.erase(slot)
    return removed


func get_total_defense() -> float:
    var total := 0.0
    for slot in _equipped:
        total += _equipped[slot].defense_bonus
    return total


func get_total_attack_bonus() -> float:
    var total := 0.0
    for slot in _equipped:
        total += _equipped[slot].attack_bonus
    return total


func get_equipped(slot: EquipmentItemPD.EquipSlot) -> EquipmentItemPD:
    return _equipped.get(slot, null)


func is_slot_occupied(slot: EquipmentItemPD.EquipSlot) -> bool:
    return _equipped.has(slot)
```

---

## 四、串接傷害系統

### 防禦減少受傷

修改 `cogito_player.gd:297` 的 `decrease_attribute()`（加在原有邏輯前）：

```gdscript
# cogito_player.gd - decrease_attribute() 修改版
func decrease_attribute(attribute_name: String, value: float) -> void:
    if attribute_name == "health":
        var eq_manager = find_child("EquipmentManager", true, false)
        if eq_manager:
            # 每點防禦減少 1% 傷害，上限 75%
            var reduction = min(eq_manager.get_total_defense() * 0.01, 0.75)
            value *= (1.0 - reduction)
            # 受傷升防禦技能
            if value > 0:
                LevelManager.add_xp("light_armor", value * 0.3)

    if player_attributes.has(attribute_name):
        player_attributes[attribute_name].subtract(value)
```

### 攻擊加算武器加成

在武器的命中計算中取得加成（以 `wieldable_pickaxe.gd` 為例）：

```gdscript
# 在命中邏輯中
func _on_body_entered(collider: Node3D) -> void:
    if not animation_player.is_playing():
        return
    var player = CogitoSceneManager._current_player_node
    var eq_manager = player.find_child("EquipmentManager", true, false)
    var attack_bonus = eq_manager.get_total_attack_bonus() if eq_manager else 0.0
    
    var final_damage = item_reference.wieldable_damage + attack_bonus
    if collider.has_signal("damage_received"):
        collider.damage_received.emit(final_damage, bullet_direction, hit_position)
```

---

## 五、從物品欄觸發裝備

在 `EquipmentItemPD` 中 override `use()` 函數，讓玩家在物品欄右鍵使用時觸發裝備：

```gdscript
# 在 equipment_item_pd.gd 中加入
func use(target) -> bool:
    var player = target if target else CogitoSceneManager._current_player_node
    var eq_manager = player.find_child("EquipmentManager", true, false)
    if not eq_manager:
        push_warning("EquipmentItemPD: EquipmentManager not found on player")
        return false

    if eq_manager.is_slot_occupied(equip_slot):
        # 同槽已有裝備 → 卸下並放回物品欄
        var removed = eq_manager.unequip(equip_slot)
        # 放回背包（建立 InventorySlotPD 並 pick_up）
        var slot_data = InventorySlotPD.new()
        slot_data.inventory_item = removed
        slot_data.quantity = 1
        player.inventory_data.pick_up_slot_data(slot_data)

    eq_manager.equip(self)
    # 從背包移除此物品
    for slot in player.inventory_data.inventory_slots:
        if slot and slot.inventory_item == self:
            player.inventory_data.remove_item_from_stack(slot)
            break
    return true
```

---

## 六、存讀檔整合

`EquipmentManager` 的狀態需存入 `CogitoPlayerState`，最簡單方式是在 `CogitoPlayer.save()` 中追加（或掛在現有的 `player_attributes` 機制旁）：

```gdscript
# 在 cogito_player.gd 的存讀檔擴充中
# 存檔：呼叫時機為 save_player_state() 之後
func get_equipment_save_data() -> Dictionary:
    var eq_manager = find_child("EquipmentManager", true, false)
    if not eq_manager:
        return {}
    var data := {}
    for slot in eq_manager._equipped:
        # 儲存資源路徑（ResourceSaver 可識別）
        data[str(slot)] = eq_manager._equipped[slot].resource_path
    return data


func load_equipment_save_data(data: Dictionary) -> void:
    var eq_manager = find_child("EquipmentManager", true, false)
    if not eq_manager or data.is_empty():
        return
    for slot_str in data:
        var slot = int(slot_str) as EquipmentItemPD.EquipSlot
        var item = load(data[slot_str]) as EquipmentItemPD
        if item:
            eq_manager.equip(item)
```

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 物品欄右鍵裝備護甲 | 護甲 Mesh 出現在骨架對應位置 |
| 再次右鍵同槽裝備 | 舊護甲卸下並回到物品欄，新護甲裝上 |
| 穿上護甲後被攻擊 | 傷害數值降低（依 defense_bonus 計算）|
| `get_total_defense()` | Console 輸出正確總防禦值 |
| 存檔讀檔後 | 裝備狀態恢復，Mesh 重新附加 |
