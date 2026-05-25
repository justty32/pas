# 架構藍圖：使用 COGITO 復刻「上古卷軸：天際 (Skyrim)」

復刻 Skyrim 是一個極具野心的目標。COGITO 作為一個第一人稱沉浸模擬框架，已經為您打下了堅實的基礎（如：物品欄、基礎任務、物理互動、屬性系統）。本文件針對每個核心系統提供具體的 COGITO 接入點與完整實作代碼。

---

## 總覽：COGITO 現有能力對應 Skyrim 需求

| Skyrim 系統 | COGITO 現狀 | 缺口 |
|---|---|---|
| 開放世界 | 單場景 + 場景切換 | ChunkManager、Terrain3D |
| 輻射 AI | patrol/chase/idle | TimeSystem、ScheduleComponent |
| 角色成長 | 屬性系統（HP/Stamina/Sanity） | SkillManager、技能樹 UI |
| 紙娃娃裝備 | 第一人稱 Wieldable | EquipmentManager、BoneAttachment3D |
| 魔法系統 | 可擴充 Wieldable 基底 | MagickaAttribute（待建）、投射物 |
| 對話任務 | Dialogic 橋接 + CogitoQuestManager | 已具備，須取消注解 + 撰寫 Timeline |

---

## 1. 開放世界與地圖流式加載 (World Streaming)

*Skyrim 的世界是無縫探索的，只有進入地牢或城市才會讀取。*

### COGITO 現狀

`CogitoSceneManager` 的 `load_next_scene()` 透過 `LoadingScene.tscn` 進行硬切換（全螢幕讀取畫面）。每次切換場景，前一場景的 Persist 狀態寫入 `user://temp/`，切換後讀入新場景。

### 升級方向與接入點

完整實作見 `tutorial/open_world_architecture.md`。

**關鍵技術決策**：

1. **浮點精度**：地圖超過 ~5km 需使用 Godot double precision 版本，或實作 Origin Rebasing（`tutorial/open_world_architecture.md` 有完整代碼）。

2. **ChunkManager Autoload**：以 `ResourceLoader.load_threaded_request/get_status/get` 進行非同步區塊載入：

```gdscript
# chunk_manager.gd — 核心非同步載入循環
func _process_loading_queue() -> void:
    if _loading_queue.is_empty():
        return
    var coord = _loading_queue[0]
    var path = chunk_path_format.replace("{x}", str(coord.x)).replace("{z}", str(coord.y))
    var progress := []
    var status = ResourceLoader.load_threaded_get_status(path, progress)
    if status == ResourceLoader.THREAD_LOAD_LOADED:
        _loading_queue.pop_front()
        _instantiate_chunk(coord, ResourceLoader.load_threaded_get(path))
    elif status == ResourceLoader.THREAD_LOAD_FAILED:
        _loading_queue.pop_front()
        push_warning("ChunkManager: 載入失敗 " + path)
```

3. **Chunk 存讀檔整合**：以 Chunk 名稱作為 `save_scene_state()` 的 `_scene_name_to_save` 參數：

```gdscript
func _unload_chunk(coord: Vector2i) -> void:
    var chunk_name = "Chunk_%d_%d" % [coord.x, coord.y]
    CogitoSceneManager.save_scene_state(chunk_name, "autosave")  # 存檔
    loaded_chunks[coord].queue_free()
    loaded_chunks.erase(coord)
```

---

## 2. 輻射 AI 與排程系統 (Radiant AI & Scheduling)

*Skyrim 的 NPC 早上工作、晚上去酒館、半夜睡覺。*

### COGITO 現狀

`NPC_State_Machine` 有 patrol、chase、idle 等狀態。狀態存在各自的腳本中（`npc_state_attack.gd`、`npc_state_patrol.gd` 等），透過 `States.goto("state_name")` 切換。

### 接入點

完整實作見 `tutorial/npc_radiant_ai_schedule.md`。

**核心設計**：`TimeSystem` 是 Autoload，驅動一個 24 小時制的遊戲內時鐘。`ScheduleComponent` 作為 NPC 的子節點，持有每個時段對應的狀態名稱字典：

```gdscript
# time_system.gd (Autoload)
signal hour_changed(new_hour: int)
var game_hour: int = 8
var game_minute: int = 0
var time_scale: float = 60.0  # 1 秒 = 1 遊戲分鐘

func _process(delta: float) -> void:
    game_minute += delta * time_scale
    if game_minute >= 60:
        game_minute -= 60
        game_hour = (game_hour + 1) % 24
        hour_changed.emit(game_hour)
```

```gdscript
# schedule_component.gd — 掛在 CogitoNPC 下
extends Node

# @export 對 Dictionary 只支援 String key，在 _ready() 轉為 int
@export var schedule_string: Dictionary = {
    "8": "work",
    "12": "eat",
    "20": "relax",
    "23": "sleep"
}
var _schedule: Dictionary = {}


func _ready() -> void:
    for key in schedule_string:
        _schedule[int(key)] = schedule_string[key]
    TimeSystem.hour_changed.connect(_on_hour_changed)


func get_current_scheduled_state() -> String:
    return TimeSystem.get_state_for_hour(TimeSystem.game_hour, _schedule)


func _on_hour_changed(new_hour: int) -> void:
    var target_state = TimeSystem.get_state_for_hour(new_hour, _schedule)
    var npc = get_parent()
    # 只在非戰鬥狀態下切換排程
    if npc.npc_state_machine.current not in ["chase", "attack"]:
        npc.npc_state_machine.goto(target_state)
```

**虛擬模擬**：NPC 載入時直接計算「此刻應在哪裡」並傳送到位，無需補算移動過程（`npc.global_position = marker.global_position`）。

---

## 3. RPG 角色成長與技能樹 (Character Progression)

*Skyrim 的特色是「做什麼就升級什麼」（如：一直被打就升級重甲）。*

### COGITO 接入點

| 動作 | 接入位置 | 原始碼 |
|---|---|---|
| 近戰命中 | `wieldable_pickaxe.gd` 的 `_on_body_entered()` | `wieldable_pickaxe.gd:~47` |
| 受到傷害 | `HitboxComponent.damage()` 的 `got_hit.emit()` | `HitboxComponent.gd:48` |
| 使用法術 | `MagickaWieldable.action_primary()` 的消耗點 | 自訂 |
| 鑄造/附魔 | 工作台的 `InteractionComponent.interact()` | 自訂 |

### 完整 SkillManager 實作

```gdscript
# skill_manager.gd (Autoload，名稱：SkillManager)
extends Node

signal skill_level_up(skill_name: String, new_level: int)

# 儲存每個技能的 {xp: float, level: int}
var _skills: Dictionary = {}

# 升級所需 XP = level * xp_per_level_multiplier
@export var xp_per_level_multiplier: float = 100.0


func _ready() -> void:
    # 初始化所有技能
    for skill in ["one_handed", "two_handed", "archery", "light_armor",
                  "heavy_armor", "destruction", "restoration", "sneak"]:
        _skills[skill] = {"xp": 0.0, "level": 1}


func add_xp(skill_name: String, amount: float) -> void:
    if not _skills.has(skill_name):
        return
    _skills[skill_name]["xp"] += amount
    _check_level_up(skill_name)


func get_level(skill_name: String) -> int:
    return _skills.get(skill_name, {"level": 1})["level"]


func get_modifier(skill_name: String) -> float:
    # 每等級提供 2% 加成，最高 +100%（50 級）
    return 1.0 + (get_level(skill_name) - 1) * 0.02


func _check_level_up(skill_name: String) -> void:
    var entry = _skills[skill_name]
    var xp_needed = entry["level"] * xp_per_level_multiplier
    while entry["xp"] >= xp_needed:
        entry["xp"] -= xp_needed
        entry["level"] += 1
        xp_needed = entry["level"] * xp_per_level_multiplier
        skill_level_up.emit(skill_name, entry["level"])


func save() -> Dictionary:
    return _skills.duplicate(true)


func load_from(data: Dictionary) -> void:
    _skills.merge(data, true)
```

### XP 注入：近戰武器

在 `wieldable_pickaxe.gd` 的命中函數中注入（此模式適用所有 Wieldable）：

```gdscript
# 在 _on_body_entered() 命中確認後加入
func _on_body_entered(collider: Node3D) -> void:
    if not animation_player.is_playing():
        return
    if collider.has_method("damage_received"):
        collider.damage_received.emit(
            item_reference.wieldable_damage * SkillManager.get_modifier("one_handed"),
            bullet_direction,
            hit_position
        )
        SkillManager.add_xp("one_handed", 10.0)  # 命中給 XP
```

### XP 注入：受傷升防禦技能

在 `HitboxComponent.gd` 的 `got_hit` 信號處連接：

```gdscript
# 在 CogitoPlayer 的 _ready() 中
func _ready() -> void:
    # ... 其他初始化
    var hitbox = find_child("HitboxComponent", true, false)
    if hitbox:
        hitbox.got_hit.connect(_on_player_hit)


func _on_player_hit() -> void:
    # 根據當前裝備的護甲類型加 XP（簡化版：固定給 light_armor）
    SkillManager.add_xp("light_armor", 5.0)
```

---

## 4. 紙娃娃裝備系統 (Paper Doll & Equipping)

*Skyrim 可以換頭盔、胸甲、手套、鞋子，且裝備會實際顯示在角色身上。*

### COGITO 現狀

COGITO 的玩家沒有第三人稱全身骨架（純第一人稱視角）。武器 Wieldable 掛在 `Camera3D` 下（`cogito_player.gd:~85`），只有手部可見。

### 升級路線

**步驟一：為玩家加入骨架**

在 `CogitoPlayer` 下添加：
```
CogitoPlayer
├── Head (Camera3D)         ← 現有
├── PlayerBody (Skeleton3D) ← 新增：完整人形骨架，用於第三人稱陰影投射
│   ├── BoneAttachment3D ("Spine")    ← 胸甲掛點
│   ├── BoneAttachment3D ("Head")     ← 頭盔掛點
│   ├── BoneAttachment3D ("RightHand") ← 右手武器掛點
│   └── BoneAttachment3D ("LeftHand") ← 左手武器掛點
```

**步驟二：擴充 ItemPD 資源**

為裝備類物品資源新增欄位：

```gdscript
# equipment_item_pd.gd extends ItemPD
class_name EquipmentItemPD extends ItemPD

enum EquipSlot { HEAD, CHEST, HANDS, FEET, LEFT_HAND, RIGHT_HAND }

@export var equip_slot: EquipSlot = EquipSlot.CHEST
@export var equip_mesh: PackedScene        # 裝備後顯示的 Mesh 場景
@export var defense_bonus: float = 0.0     # 防禦加成
@export var attack_bonus: float = 0.0      # 攻擊加成
@export var armor_skill: String = "light_armor"
```

**步驟三：EquipmentManager**

```gdscript
# equipment_manager.gd — 掛在 CogitoPlayer 下
extends Node

# 當前各槽位裝備資源與已實例化的 Mesh
var _equipped: Dictionary = {}   # EquipSlot → EquipmentItemPD
var _meshes: Dictionary = {}     # EquipSlot → MeshInstance3D

@onready var _bone_attachments: Dictionary = {
    EquipmentItemPD.EquipSlot.HEAD:   $"../PlayerBody/BoneAttachment_Head",
    EquipmentItemPD.EquipSlot.CHEST:  $"../PlayerBody/BoneAttachment_Spine",
    EquipmentItemPD.EquipSlot.HANDS:  $"../PlayerBody/BoneAttachment_RightHand",
    EquipmentItemPD.EquipSlot.FEET:   $"../PlayerBody/BoneAttachment_Feet",
}


func equip(item: EquipmentItemPD) -> void:
    var slot = item.equip_slot
    
    # 先卸下舊裝備
    if _equipped.has(slot):
        unequip(slot)
    
    _equipped[slot] = item
    
    # 將 Mesh 附加到對應的 BoneAttachment
    if item.equip_mesh and _bone_attachments.has(slot):
        var mesh_instance = item.equip_mesh.instantiate()
        _bone_attachments[slot].add_child(mesh_instance)
        _meshes[slot] = mesh_instance


func unequip(slot: EquipmentItemPD.EquipSlot) -> void:
    if _meshes.has(slot):
        _meshes[slot].queue_free()
        _meshes.erase(slot)
    _equipped.erase(slot)


func get_total_defense() -> float:
    var total := 0.0
    for slot in _equipped:
        total += _equipped[slot].defense_bonus
    return total
```

**步驟四：在 `decrease_attribute` 中套用防禦**

修改 `cogito_player.gd:297` 的 `decrease_attribute()`：

```gdscript
func decrease_attribute(attribute_name: String, value: float) -> void:
    if attribute_name == "health":
        var equipment_manager = find_child("EquipmentManager", true, false)
        if equipment_manager:
            # 防禦值每點減少 1% 傷害（上限 80%）
            var damage_reduction = min(equipment_manager.get_total_defense() * 0.01, 0.8)
            value *= (1.0 - damage_reduction)
    
    if player_attributes.has(attribute_name):
        player_attributes[attribute_name].subtract(value)
```

---

## 5. 魔法與呼喊系統 (Magic & Shouts)

*一手拿劍，一手放魔法，或是使用獨立冷卻的龍吼。*

### COGITO 現狀

`CogitoWieldable` 的 `action_primary(item, is_released)` 和 `action_secondary(is_released)` 提供完整的輸入鉤子。`CogitoAttribute` 可直接擴充為 `MagickaAttribute`。

### MagickaAttribute 完整實作

完整代碼見 `tutorial/magic_and_magicka_system.md`。核心：

```gdscript
# cogito_magicka_attribute.gd extends CogitoAttribute
class_name CogitoMagickaAttribute extends CogitoAttribute

@export var regen_delay: float = 3.0      # 施法後多久開始回魔
@export var regen_speed: float = 5.0      # 每秒回魔量

var _can_regen: bool = true
var _regen_timer: float = 0.0


func _process(delta: float) -> void:
    if not _can_regen:
        _regen_timer -= delta
        if _regen_timer <= 0.0:
            _can_regen = true
    elif value_current < value_max:
        add(regen_speed * delta)


func notify_cast() -> void:
    _regen_timer = regen_delay
    _can_regen = false
```

**自動整合到 HUD**：在 `CogitoPlayer` 下添加 `CogitoMagickaAttribute` 子節點，設定 `attribute_name = "magicka"` 和 `attribute_visibility = Hud`，`cogito_player.gd:230` 的 `find_children` 掃描會自動發現它，`player_hud_manager.gd:121` 的 `instantiate_player_attribute_ui()` 會自動建立魔力條。

### 法術 Wieldable

```gdscript
# wieldable_fireball.gd extends CogitoWieldable
@export var magicka_cost: float = 20.0
@export var projectile_scene: PackedScene  # 帶 HitboxComponent 的投射物
@export var projectile_speed: float = 15.0

var _player_node: Node3D
var _magicka: CogitoMagickaAttribute


func _ready() -> void:
    _player_node = CogitoSceneManager._current_player_node
    _magicka = _player_node.find_child("MagickaAttribute", true, false)


func action_primary(item: ItemPD, is_released: bool) -> void:
    if is_released:
        return
    if not _magicka or _magicka.value_current < magicka_cost:
        # 魔力不足：播放失敗音效
        return
    
    _magicka.subtract(magicka_cost)
    _magicka.notify_cast()
    _cast_fireball()


func _cast_fireball() -> void:
    var projectile = projectile_scene.instantiate()
    get_tree().current_scene.add_child(projectile)
    
    var camera = _player_node.find_child("Camera3D", true, false)
    projectile.global_position = camera.global_position + camera.global_basis.z * -1.5
    projectile.linear_velocity = -camera.global_basis.z * projectile_speed
```

### 龍吼獨立鍵位

在 `cogito_player.gd` 的 `_unhandled_input()` 中加入（不干擾 Wieldable 的 Primary/Secondary）：

```gdscript
# 在 _unhandled_input(event) 中
if event.is_action_pressed("shout"):  # 在 Input Map 中設定 Z 鍵
    _try_use_shout()


func _try_use_shout() -> void:
    if not _shout_ready:
        return
    if _equipped_shout:
        _equipped_shout.activate(self)
        _shout_ready = false
        _shout_cooldown_timer = _equipped_shout.cooldown
```

---

## 6. 深度對話與任務分支 (Branching Dialogue)

*Skyrim 依賴對話來接任務、買賣、說服。*

### COGITO 現狀

`CogitoQuestManager`（`cogito_quest_manager.gd`）是 Autoload，提供完整的任務管理 API。Dialogic 橋接腳本（`DialogicInteraction.gd`）已預備但**全部被注解**，需手動取消注解（見 `tutorial/ui_modification_dialogue.md`）。

### CogitoQuestManager 實際 API

```gdscript
# start_quest() 接收 CogitoQuest 資源，不是字串 ID
# cogito_quest_manager.gd:34
CogitoQuestManager.start_quest(quest_resource)

# 更新任務計數器（達到目標值自動完成任務）
# cogito_quest_manager.gd:93
CogitoQuestManager.change_quest_counter(quest_resource, value_change)
# 例：殺死一隻敵人
CogitoQuestManager.change_quest_counter(kill_bandits_quest, 1)

# 用 quest_id（int）而非資源操作（適合 Dialogic 呼叫）
# cogito_quest_manager.gd:159
CogitoQuestManager.call_quest_method(quest_id, "update", [])

# 檢查任務狀態
CogitoQuestManager.is_quest_active(quest_resource)    # bool
CogitoQuestManager.is_quest_completed(quest_resource) # bool
```

**注意**：`start_quest()` 需要傳入 `CogitoQuest` 資源物件，**不是**字串名稱或 ID。在 Dialogic 的 `[call]` 指令中通常需要：
1. 將 Quest 資源預載在 Autoload 中。
2. 或透過 `call_quest_method(quest_id, method, args)` 用 ID 操作。

### Dialogic Timeline 接任務範例

```
# npc_guard.dtl（Dialogic Timeline 語法）
John: 你好，冒險者。我們的村子最近鬧盜賊。
[choice]
  + [幫忙調查] → branch_accept
  + [我很忙] → branch_refuse
[/choice]

[label branch_accept]
John: 太感謝了！去東邊的廢墟找找看。
[call node="QuestBridge" method="start_quest_by_name" args={"name": "investigate_ruins"}]
[end_branch]

[label branch_refuse]
John: ...好吧，隨便。
[end_branch]
```

```gdscript
# quest_bridge.gd (Autoload，銜接 Dialogic 與 CogitoQuestManager)
extends Node

# 預先存放所有 Quest 資源
@export var quest_registry: Dictionary = {}  # name → CogitoQuest

func start_quest_by_name(name: String) -> void:
    if quest_registry.has(name):
        CogitoQuestManager.start_quest(quest_registry[name])
```

### 說服系統

說服的結果取決於玩家技能等級（`SkillManager.get_level("speech")`）：

```gdscript
# 在 Dialogic Timeline 中透過條件分支控制
# [if {SkillManager.get_level("speech")} >= 30]
# → 成功說服選項可見
# [/if]

# 或在 QuestBridge 中封裝
func try_persuade(difficulty: int) -> bool:
    var speech_level = SkillManager.get_level("speech")
    var success = speech_level >= difficulty
    if success:
        SkillManager.add_xp("speech", 15.0)  # 成功說服增加技能 XP
    return success
```

---

## 開發迭代順序建議

**不要一開始就想做開放世界**。建議的迭代路線：

### 階段一：地牢核心（2-4 週）
完全在 COGITO 現有能力範圍內：
- 一個封閉室內場景
- 近戰戰鬥：長按攻擊（`tutorial/skyrim_combat_mechanics.md`）
- HP / Stamina / Magicka 屬性消耗
- 搜刮箱子（`CogitoObject` + Inventory）
- 1~2 種法術 Wieldable

**無需修改 COGITO 核心**，全部透過擴充實現。

### 階段二：村莊核心（2-3 週）
- 取消注解 Dialogic 橋接，撰寫 NPC 對話 Timeline
- 接任務 → 完成任務 → 回報任務的完整循環
- `TimeSystem` + `ScheduleComponent`：讓 1~2 個 NPC 有作息
- 商店 NPC（Wieldable 或對話選項觸發物品交換）

### 階段三：RPG 核心（3-4 週）
- `SkillManager` Autoload + XP 注入點
- `EquipmentManager` + `BoneAttachment3D` 顯示裝備 Mesh
- 屬性加成系統（防禦 / 攻擊 modifier）

### 階段四：世界縫合（4+ 週）
- `ChunkManager` Autoload + Terrain3D
- Origin Rebasing（若地圖 > 5km）
- 跨 Chunk Navigation（每個 Chunk 含獨立 `NavigationRegion3D`）
- 世界地圖 UI（`tutorial/open_world_architecture.md`）
