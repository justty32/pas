# 教學：實作 Skyrim 風格升級系統 (Learn by Doing)

Skyrim 的核心特色是「技能隨使用而成長」。本教學將引導您如何建立一個全域等級管理器，並將其與 COGITO 的戰鬥與屬性系統串接。

## 1. 建立技能管理器 (LevelManager)

建立一個 Autoload 腳本 `LevelManager.gd`。

### 實作步驟
1. **定義技能數據**：
   ```gdscript
   extends Node
   
   signal skill_leveled_up(skill_name, new_level)

   var skills = {
       "one_handed": {"level": 15, "xp": 0, "xp_next": 100},
       "archery": {"level": 15, "xp": 0, "xp_next": 100},
       "restoration": {"level": 15, "xp": 0, "xp_next": 100}
   }

   func add_xp(skill_name: String, amount: float):
       var s = skills[skill_name]
       s.xp += amount
       if s.xp >= s.xp_next:
           level_up(skill_name)

   func level_up(skill_name: String):
       var s = skills[skill_name]
       s.level += 1
       s.xp = 0
       s.xp_next *= 1.1 # 提升下一級所需經驗
       skill_leveled_up.emit(skill_name, s.level)
       CogitoGlobals.debug_log(true, "LevelManager", skill_name + " 升級至 " + str(s.level))
   ```

---

## 2. 串接戰鬥系統

在武器腳本中，當成功命中目標時增加經驗。

### 原始碼導航
- `addons/cogito/Wieldables/wieldable_pickaxe.gd` (或其他近戰武器)

### 實作步驟
1. 在 `_on_body_entered` 函數中：
   ```gdscript
   func _on_body_entered(collider):
       if collider.has_signal("damage_received"):
           # 成功命中，增加單手武器經驗
           LevelManager.add_xp("one_handed", 5.0)
   ```

---

## 3. 技能影響屬性 (Modifiers)

讓技能等級實際影響遊戲數值。

### 實作步驟
在計算傷害或耐力消耗時，引入技能倍率：
```gdscript
# 在 wieldable_sword.gd 中
func get_damage() -> float:
    var skill_level = LevelManager.skills["one_handed"].level
    var multiplier = 1.0 + (skill_level - 15) * 0.02 # 每級增加 2% 傷害
    return base_damage * multiplier
```

---

## 4. UI 反饋

當升級時，在畫面上顯示提示。
1. 在 `LevelManager.gd` 中監聽 `skill_leveled_up` 信號。
2. 呼叫 `player_hud_manager.gd` 中的 `send_hint` 方法：
   ```gdscript
   func _on_skill_up(skill_name, level):
       var hud = get_tree().get_first_node_in_group("PlayerHUD")
       hud.send_hint(null, skill_name + " 升級至 " + str(level), 3.0)
   ```

---

## 驗證方式
1. 開啟偵錯日誌 (`is_logging = true`)。
2. 連續攻擊敵人，確認控制台是否輸出經驗值增加的訊息。
3. 當累積足夠次數後，確認是否有「技能升級」的 HUD 提示，並檢查武器造成的傷害是否提升。
