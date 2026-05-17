# 教學：實作魔法系統 (魔力與法術施放)

本教學說明如何在 COGITO 中添加魔力 (Magicka) 屬性，並將「法術」實作為一種特殊的持用物件 (Wieldable)。

## 1. 添加魔力屬性 (Magicka Attribute)

### 實作步驟
1. 在 `CogitoPlayer` 的 `Attributes` 容器下，新增一個 `CogitoAttribute` 節點。
2. 命名為 `Magicka`。
3. 設定 `value_max = 100`, `value_start = 100`。
4. 勾選 `auto_regenerate` 並設定 `regen_speed` (例如 2.0)，讓魔力隨時間恢復。

---

## 2. 建立法術預製件 (Spell Wieldable)

法術在本質上是「不顯示模型」或「顯示手部特效」的 `Wieldable`。

### 實作步驟
1. 複製 `wieldable_toy_pistol.gd` 並更名為 `wieldable_spell_fireball.gd`。
2. 修改 `action_primary`：
   ```gdscript
   func action_primary(_passed_item_reference, _is_released: bool):
       if _is_released: return
       
       # 檢查魔力
       var player = player_interaction_component.get_parent()
       var magicka = player.find_child("Magicka")
       if magicka.value_current < 20:
           return
       
       magicka.subtract(20) # 消耗魔力
       
       # 播放施法動畫與音效
       animation_player.play("cast_fireball")
       
       # 生成火球投射物
       var fireball = projectile_prefab.instantiate()
       get_tree().current_scene.add_child(fireball)
       fireball.global_position = bullet_point.global_position
       # ... 設定飛行方向 ...
   ```

---

## 3. 不同類型的法術實作

- **瞬發法術 (Projectile)**：如上所述，發射一個火球。
- **持續法術 (Channeling)**：
    - 監聽 `_is_released == false`。
    - 在 `_process` 中持續扣除魔力。
    - 開啟一個長形的 `Area3D` 或射線，對重疊的敵人持續造成傷害。
- **自我強化 (Buff)**：
    - 使用後直接修改玩家的 `speed` 或 `armor` 屬性，並在 N 秒後還原。

---

## 4. 法術切換與 UI 顯示

1. **法術作為物品**：在 `InventoryPD` 中建立 `InventoryItemPD`，類別選為 `Wieldable`。
2. **快捷鍵綁定**：玩家可以像切換武器一樣，透過數字鍵快速切換「火球術」或「治療術」。
3. **魔力條顯示**：
   - 參考 [教學：如何自訂互動提示與 HUD](./ui_modification_interaction.md)。
   - 在 `Player_HUD` 中為 `Magicka` 屬性添加一個藍色的進度條。

---

## 驗證方式
1. 裝備「火球術」法術。
2. 按下攻擊鍵，確認魔力條是否有扣除。
3. 確認火球是否有正確射出並在命中敵人時造成傷害。
4. 停止施法後，確認魔力條是否會慢慢恢復。
