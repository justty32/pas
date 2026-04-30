# 教學：實作 Skyrim 風格戰鬥機制 (格擋、重擊與失衡)

本教學將引導您如何擴充 COGITO 的近戰系統，加入格擋 (Blocking)、消耗耐力的重擊 (Power Attack) 以及讓敵人失衡 (Stagger) 的機制。

## 前置知識
- 已閱讀 [Level 3C: Wieldable 玩家動作](../architecture/level3_wieldables.md)。
- 瞭解 `wieldable_pickaxe.gd` 的基本結構。

---

## 1. 格擋機制 (Blocking)

我們利用 `action_secondary`（預設為滑鼠右鍵）來實作格擋。

### 實作步驟
1. **修改近戰武器腳本**：建立 `wieldable_sword.gd`。
2. **新增狀態變數**：
   ```gdscript
   var is_blocking : bool = false
   @export var block_damage_reduction : float = 0.5 # 減傷 50%
   ```
3. **實作 `action_secondary`**：
   ```gdscript
   func action_secondary(is_released: bool):
       if is_released:
           is_blocking = false
           animation_player.play("idle") # 停止格擋動畫
       else:
           is_blocking = true
           animation_player.play("block_pose") # 播放格擋姿勢
   ```
4. **傷害攔截**：在玩家的 `HitboxComponent` 或 `cogito_player.gd` 的受傷邏輯中：
   ```gdscript
   func apply_damage(amount: float):
       if current_weapon.is_blocking:
           amount *= (1.0 - current_weapon.block_damage_reduction)
           # 扣除格擋耐力
           decrease_attribute("stamina", 5)
       super.apply_damage(amount)
   ```

---

## 2. 消耗耐力的重擊 (Power Attack)

重擊是透過長按攻擊鍵觸發，造成更高傷害並可能使敵人失衡。

### 實作步驟
1. **區分輕重擊**：
   在 `action_primary` 中使用計時器判定按壓時間。
   ```gdscript
   var attack_press_time : float = 0.0
   
   func action_primary(_item, is_released: bool):
       if !is_released:
           attack_press_time = Time.get_unix_time_from_system()
       else:
           var duration = Time.get_unix_time_from_system() - attack_press_time
           if duration > 0.4: # 長按超過 0.4 秒
               perform_power_attack()
           else:
               perform_light_attack()
   ```
2. **重擊效果**：
   ```gdscript
   func perform_power_attack():
       if player_stamina.value_current >= 20:
           player_stamina.subtract(20)
           animation_player.play("heavy_attack")
           # 增加傷害倍率並傳遞 stagger 標記
           current_damage = base_damage * 2.0
   ```

---

## 3. 敌人失衡 (Stagger)

利用 COGITO NPC 內建的 `apply_knockback()` 方法。

### 實作步驟
1. **觸發失衡**：在武器命中敵人的回呼中：
   ```gdscript
   func _on_body_entered(collider):
       if is_power_attack and collider is CogitoNPC:
           # 計算擊退方向
           var dir = (collider.global_position - Host.global_position).normalized()
           collider.apply_knockback(dir * 5.0) # 5.0 為力道
           collider.animation_tree.set("parameters/Transition/transition_request", "stagger")
   ```

---

## 驗證方式
1. **格擋測試**：觀察被敵人擊中時，血量下降速度是否變慢，且耐力條是否有減少。
2. **重擊測試**：長按攻擊鍵，確認是否播放了不同的動畫且耐力消耗正確。
3. **失衡測試**：使用重擊擊中 NPC，確認 NPC 是否有明顯的後退動作。
