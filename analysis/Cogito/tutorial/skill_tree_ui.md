# 教學：技能樹 UI（Skill Tree UI）

本教學說明如何為 `LevelManager`（`skyrim_leveling_system.md`）建立可操作的技能樹介面：顯示技能等級、解鎖天賦（Perk），以及天賦效果如何影響遊戲數值。

## 前置知識
- 已完成 [教學：Skyrim 升級系統](./skyrim_leveling_system.md)（`LevelManager` 已存在）。
- 了解 Godot 4 `Control` 節點基礎。

---

## 一、資料結構：PerkData 資源

天賦是掛在技能樹節點上的資料，建立 `res://scripts/perk_data.gd`：

```gdscript
# res://scripts/perk_data.gd
extends Resource
class_name PerkData

## 天賦唯一 ID（如 "one_handed_power_strike"）
@export var perk_id: String
## 顯示名稱
@export var perk_name: String
## 描述
@export_multiline var description: String
## 解鎖所需技能等級
@export var required_level: int = 10
## 前置天賦（必須先解鎖此天賦才能解鎖本天賦）
@export var prerequisite_perk_id: String = ""
## 天賦效果類型
enum EffectType { DAMAGE_MULTIPLIER, STAMINA_REDUCTION, CRITICAL_CHANCE, CUSTOM }
@export var effect_type: EffectType = EffectType.DAMAGE_MULTIPLIER
## 效果數值
@export var effect_value: float = 0.1
## 圖示
@export var icon: Texture2D
```

---

## 二、PerkManager：天賦狀態管理

擴充 `LevelManager`（或建立獨立 Autoload `PerkManager`）：

```gdscript
# res://scripts/perk_manager.gd (Autoload: PerkManager)
extends Node

signal perk_unlocked(perk: PerkData)

## 所有可用天賦，在 Inspector 中填入
@export var all_perks: Array[PerkData] = []

## 已解鎖的天賦 ID 集合
var _unlocked_perks: Array[String] = []


func can_unlock(perk: PerkData) -> bool:
    # 已解鎖
    if is_unlocked(perk.perk_id):
        return false
    # 技能等級不夠
    var skill_name = _get_skill_from_perk(perk)
    if LevelManager.get_level(skill_name) < perk.required_level:
        return false
    # 前置天賦未解鎖
    if perk.prerequisite_perk_id != "" and not is_unlocked(perk.prerequisite_perk_id):
        return false
    return true


func unlock(perk: PerkData) -> bool:
    if not can_unlock(perk):
        return false
    _unlocked_perks.append(perk.perk_id)
    perk_unlocked.emit(perk)
    return true


func is_unlocked(perk_id: String) -> bool:
    return perk_id in _unlocked_perks


## 取得某效果類型的加總數值
func get_total_effect(effect_type: PerkData.EffectType) -> float:
    var total := 0.0
    for perk_id in _unlocked_perks:
        var perk = _find_perk(perk_id)
        if perk and perk.effect_type == effect_type:
            total += perk.effect_value
    return total


func _find_perk(perk_id: String) -> PerkData:
    for perk in all_perks:
        if perk.perk_id == perk_id:
            return perk
    return null


func _get_skill_from_perk(perk: PerkData) -> String:
    # 依命名慣例取得技能名（"one_handed_power_strike" → "one_handed"）
    return perk.perk_id.split("_")[0] + "_" + perk.perk_id.split("_")[1]


func save_to_dict() -> Dictionary:
    return {"unlocked": _unlocked_perks.duplicate()}


func load_from_dict(data: Dictionary) -> void:
    _unlocked_perks = data.get("unlocked", [])
```

---

## 三、技能樹 UI 場景結構

在 `player_hud_manager.gd` 的 UI 下建立技能樹面板（與物品欄同層級，透過 Tab 切換）：

```
SkillTreePanel (PanelContainer)
└── MarginContainer
    └── HBoxContainer
        ├── SkillList (VBoxContainer)   ← 左欄：技能選擇
        │   ├── SkillButton_OneHanded
        │   ├── SkillButton_Archery
        │   └── ...
        └── PerkGrid (GridContainer)    ← 右欄：選定技能的天賦
            └── (動態填入 PerkNode)
```

---

## 四、PerkNode：單一天賦節點

建立 `res://ui/perk_node.tscn`：

```
PerkNode (PanelContainer)  ← perk_node.gd
├── TextureRect (icon)
├── Label (perk_name)
└── Label (level_req, e.g. "需要 Lv.10")
```

```gdscript
# res://ui/perk_node.gd
extends PanelContainer

signal perk_pressed(perk: PerkData)

var _perk_data: PerkData = null

@onready var icon_rect: TextureRect = $TextureRect
@onready var name_label: Label = $PerkName
@onready var level_label: Label = $LevelReq


func setup(perk: PerkData) -> void:
    _perk_data = perk
    if perk.icon:
        icon_rect.texture = perk.icon
    name_label.text = perk.perk_name
    level_label.text = "Lv." + str(perk.required_level)
    _refresh_state()


func _refresh_state() -> void:
    if PerkManager.is_unlocked(_perk_data.perk_id):
        # 已解鎖：金色外框
        add_theme_stylebox_override("panel", _make_panel(Color(0.9, 0.7, 0.1)))
    elif PerkManager.can_unlock(_perk_data):
        # 可解鎖：亮色
        modulate = Color(1.0, 1.0, 1.0)
    else:
        # 鎖定：半透明灰色
        modulate = Color(0.5, 0.5, 0.5, 0.7)


func _make_panel(border_color: Color) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.border_color = border_color
    style.set_border_width_all(2)
    return style


func _gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
        perk_pressed.emit(_perk_data)
```

---

## 五、SkillTreeUI：主控腳本

```gdscript
# res://ui/skill_tree_ui.gd
extends Control

@export var perk_node_scene: PackedScene  # 指向 perk_node.tscn

@onready var skill_list: VBoxContainer = $MarginContainer/HBoxContainer/SkillList
@onready var perk_grid: GridContainer = $MarginContainer/HBoxContainer/PerkGrid
@onready var skill_name_label: Label = $MarginContainer/HBoxContainer/PerkGrid/SkillTitle
@onready var perk_points_label: Label = $MarginContainer/HBoxContainer/SkillList/PerkPoints

var _current_skill: String = "one_handed"

# 每個技能有哪些天賦（依 perk_id 前綴分組）
var _skill_perks: Dictionary = {}


func _ready() -> void:
    # 按技能分組天賦
    for perk in PerkManager.all_perks:
        var skill = perk.perk_id.split("_", 2)[0] + "_" + perk.perk_id.split("_", 2)[1]
        # 簡化：取第一個底線前的部分
        var prefix = perk.perk_id.substr(0, perk.perk_id.find("_", perk.perk_id.find("_") + 1))
        if not _skill_perks.has(prefix):
            _skill_perks[prefix] = []
        _skill_perks[prefix].append(perk)

    _build_skill_buttons()
    PerkManager.perk_unlocked.connect(_on_perk_unlocked)
    LevelManager.skill_leveled_up.connect(_on_skill_leveled_up)


func _build_skill_buttons() -> void:
    for skill_name in LevelManager.skills.keys():
        var btn = Button.new()
        btn.text = skill_name.capitalize().replace("_", " ")
        btn.pressed.connect(_on_skill_selected.bind(skill_name))
        skill_list.add_child(btn)


func _on_skill_selected(skill_name: String) -> void:
    _current_skill = skill_name
    _refresh_perk_grid()


func _refresh_perk_grid() -> void:
    for child in perk_grid.get_children():
        child.queue_free()

    skill_name_label.text = _current_skill.capitalize().replace("_", " ") + \
                            "  Lv." + str(LevelManager.get_level(_current_skill))

    var perks_for_skill = _get_perks_for_skill(_current_skill)
    for perk in perks_for_skill:
        var node = perk_node_scene.instantiate()
        perk_grid.add_child(node)
        node.setup(perk)
        node.perk_pressed.connect(_on_perk_pressed)


func _get_perks_for_skill(skill_name: String) -> Array:
    # 找 perk_id 開頭符合 skill_name 的所有天賦
    var result := []
    for perk in PerkManager.all_perks:
        if perk.perk_id.begins_with(skill_name):
            result.append(perk)
    return result


func _on_perk_pressed(perk: PerkData) -> void:
    if PerkManager.unlock(perk):
        _refresh_perk_grid()
    else:
        var player = CogitoSceneManager._current_player_node
        if player and player.player_interaction_component:
            var msg := ""
            if PerkManager.is_unlocked(perk.perk_id):
                msg = "此天賦已解鎖"
            elif LevelManager.get_level(_current_skill) < perk.required_level:
                msg = "技能等級不足（需要 Lv." + str(perk.required_level) + "）"
            elif perk.prerequisite_perk_id != "" and not PerkManager.is_unlocked(perk.prerequisite_perk_id):
                msg = "需先解鎖前置天賦"
            player.player_interaction_component.send_hint(null, msg)


func _on_perk_unlocked(_perk: PerkData) -> void:
    _refresh_perk_grid()


func _on_skill_leveled_up(skill_name: String, _new_level: int) -> void:
    if skill_name == _current_skill:
        _refresh_perk_grid()
```

---

## 六、天賦效果套用

在遊戲邏輯的計算點加入 `PerkManager.get_total_effect()`：

```gdscript
# 近戰傷害加成（在武器命中時）
var base_damage = item_reference.wieldable_damage
var perk_mult = 1.0 + PerkManager.get_total_effect(PerkData.EffectType.DAMAGE_MULTIPLIER)
var final_damage = base_damage * perk_mult * LevelManager.get_damage_multiplier("one_handed")
collider.damage_received.emit(final_damage, direction, hit_pos)

# 耐力消耗減少（在 cogito_player.gd 的快跑消耗處）
var stamina_reduction = PerkManager.get_total_effect(PerkData.EffectType.STAMINA_REDUCTION)
var final_drain = sprint_stamina_drain * (1.0 - stamina_reduction)
decrease_attribute("stamina", final_drain * delta)
```

---

## 七、開啟技能樹的輸入

在 `cogito_player.gd` 的 `_unhandled_input()` 加入，或在 `player_hud_manager.gd` 的 `_input()` 監聽：

```gdscript
# player_hud_manager.gd
func _input(event: InputEvent) -> void:
    if event.is_action_pressed("open_skill_tree"):  # Input Map: K
        if skill_tree_panel.visible:
            skill_tree_panel.hide()
        else:
            skill_tree_ui.visible = true
            skill_tree_ui._refresh_perk_grid()
            # 暫停遊戲或進入介面模式
            CogitoSceneManager._current_player_node.toggled_interface.emit(true)
```

---

## 八、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 按 K 開啟技能樹 | 面板顯示，玩家無法移動 |
| 點選左欄技能 | 右欄顯示對應天賦節點 |
| 等級不足的天賦 | 顯示為半透明灰色，點擊提示「等級不足」|
| 達到等級後點選天賦 | 天賦解鎖，顯示金色外框 |
| 解鎖傷害天賦後攻擊 | 實際傷害數值提升（Console 可驗證）|
| 存讀檔後 | 已解鎖天賦保持（需整合到 player state 存讀）|
