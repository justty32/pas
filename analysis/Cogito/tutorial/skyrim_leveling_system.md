# 教學：實作 Skyrim 風格升級系統 (Learn by Doing)

Skyrim 的核心特色是「技能隨使用而成長」。本教學建立全域技能管理器，並與 COGITO 的武器傷害信號和屬性系統正確整合。

## 前置知識
- 已閱讀 [Level 3C: Wieldable 玩家動作](../architecture/level3_wieldables.md)。
- 瞭解 GDScript Autoload 基礎。

---

## 一、建立 LevelManager Autoload

建立 `res://scripts/level_manager.gd`，並在 **Project Settings → Autoload** 加入（名稱：`LevelManager`）：

```gdscript
# res://scripts/level_manager.gd
extends Node

## 技能升級時發射
signal skill_leveled_up(skill_name: String, new_level: int)

## 技能定義：名稱 → {level, xp, xp_next}
var skills : Dictionary = {
    "one_handed": {"level": 1, "xp": 0.0, "xp_next": 100.0},
    "archery":    {"level": 1, "xp": 0.0, "xp_next": 100.0},
    "heavy_armor":{"level": 1, "xp": 0.0, "xp_next": 100.0},
    "restoration":{"level": 1, "xp": 0.0, "xp_next": 100.0},
}


func add_xp(skill_name: String, amount: float) -> void:
    if not skills.has(skill_name):
        push_warning("LevelManager: Unknown skill: " + skill_name)
        return
    
    var s : Dictionary = skills[skill_name]
    s.xp += amount
    CogitoGlobals.debug_log(true, "LevelManager", "%s +%.1f XP (%.1f/%.1f)" % [skill_name, amount, s.xp, s.xp_next])
    
    while s.xp >= s.xp_next:
        s.xp -= s.xp_next
        _level_up(skill_name)


func _level_up(skill_name: String) -> void:
    var s : Dictionary = skills[skill_name]
    s.level += 1
    s.xp_next = round(s.xp_next * 1.25)  # 每級增加 25% 所需經驗
    skill_leveled_up.emit(skill_name, s.level)
    CogitoGlobals.debug_log(true, "LevelManager", skill_name + " 升至 Lv." + str(s.level))


func get_level(skill_name: String) -> int:
    return skills.get(skill_name, {}).get("level", 1)


## 技能修正值（Lv.1=0, Lv.50=+0.49）：level 越高傷害倍率越高
func get_damage_multiplier(skill_name: String) -> float:
    var level = get_level(skill_name)
    return 1.0 + (level - 1) * 0.01  # 每級 +1%


## 存讀檔（與 CogitoSceneManager 整合需另行處理）
func save_to_dict() -> Dictionary:
    return skills.duplicate(true)

func load_from_dict(data: Dictionary) -> void:
    for key in data:
        if skills.has(key):
            skills[key] = data[key]
```

---

## 二、串接近戰武器

在 `wieldable_pickaxe.gd` 的 `_on_body_entered` 成功命中後加入 XP（`wieldable_pickaxe.gd:58-80`）：

```gdscript
# addons/cogito/Wieldables/wieldable_pickaxe.gd（修改）
func _on_body_entered(collider):
    if collider.has_signal("damage_received"):
        var player = player_interaction_component.get_parent()
        # ... 原有命中偵測邏輯 ...
        collider.damage_received.emit(item_reference.wieldable_damage, bullet_direction, hit_position)
        
        # 命中有效目標（NPC 或可受傷物件）→ 增加技能 XP
        if collider.is_in_group("Enemy"):
            LevelManager.add_xp("one_handed", item_reference.wieldable_damage * 0.5)
```

---

## 三、串接弓箭/投射物

在 `wieldable_toy_pistol.gd` 或自訂的弓箭腳本中，監聽彈丸命中：

```gdscript
# wieldable_archer.gd（自訂弓箭，繼承 CogitoWieldable）
func action_primary(_item, _is_released):
    if _is_released: return
    # ... 發射邏輯 ...
    var arrow = arrow_prefab.instantiate()
    # 連接箭矢的命中信號
    arrow.body_entered.connect(_on_arrow_hit)
    # ...

func _on_arrow_hit(collider):
    if collider.has_signal("damage_received"):
        LevelManager.add_xp("archery", 8.0)
```

---

## 四、技能等級影響傷害

在武器腳本中，使用 `LevelManager.get_damage_multiplier()` 修正最終傷害：

```gdscript
# 在 wieldable_pickaxe.gd 的命中計算中
func _on_body_entered(collider):
    if collider.has_signal("damage_received"):
        # ... 取得 hit_position, bullet_direction ...
        var raw_damage = item_reference.wieldable_damage
        var final_damage = raw_damage * LevelManager.get_damage_multiplier("one_handed")
        
        collider.damage_received.emit(final_damage, bullet_direction, hit_position)
        LevelManager.add_xp("one_handed", raw_damage * 0.5)
```

---

## 五、升級 UI 提示

`send_hint()` 正確呼叫路徑是透過 `PlayerInteractionComponent`（`PlayerInteractionComponent.gd:328`）：

```gdscript
# res://scripts/level_manager.gd 中的升級通知
func _level_up(skill_name: String) -> void:
    # ... 升級邏輯 ...
    
    # 透過 CogitoSceneManager 取得玩家的 PIC
    var player = CogitoSceneManager._current_player_node
    if player and player.player_interaction_component:
        player.player_interaction_component.send_hint(
            null,  # Texture2D icon，可傳入技能圖示
            "%s 升至 Lv.%d！" % [skill_name.capitalize(), skills[skill_name].level]
        )
```

**`CogitoSceneManager._current_player_node`**：Autoload 中保存的當前玩家節點引用，所有 Autoload 腳本都可安全存取。

---

## 六、技能影響其他屬性（進階）

以「重甲技能降低耐力消耗」為例，在 `cogito_player.gd` 的耐力扣除點加入修正：

```gdscript
# cogito_player.gd 的快跑耐力消耗（約第 900 行）
if stamina_attribute and is_sprinting:
    var stamina_drain = sprint_stamina_drain
    # 重甲技能每級降低 0.5% 耐力消耗
    var armor_level = LevelManager.get_level("heavy_armor")
    stamina_drain *= (1.0 - (armor_level - 1) * 0.005)
    decrease_attribute("stamina", stamina_drain * delta)
```

---

## 七、存讀檔整合

COGITO 的存檔系統目前只處理場景物件，玩家技能需另外持久化。推薦掛在玩家的 `save()/set_state()` 上：

```gdscript
# cogito_player.gd 的 save() 擴充
func save():
    var data = {
        # ... 原有資料 ...
        "skill_data": LevelManager.save_to_dict()
    }
    return data

func set_state():
    # ... 原有邏輯 ...
    if CogitoSceneManager.player_state_data.has("skill_data"):
        LevelManager.load_from_dict(CogitoSceneManager.player_state_data["skill_data"])
```

---

## 八、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 攻擊 NPC 5 次（近戰） | Console：`one_handed +X XP` |
| 累積足夠攻擊後 | HUD 顯示「One Handed 升至 Lv.2！」|
| Lv.50 近戰武器傷害 vs Lv.1 | Lv.50 傷害提高約 49% |
| 存檔讀檔後 | 技能等級保持（前提：`save()/set_state()` 整合完成）|
