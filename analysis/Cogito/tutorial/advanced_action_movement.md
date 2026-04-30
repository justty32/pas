# 教學：如何實現進階動作 (快跑、蹲下、趴下、翻滾、瞄準)

本教學將引導您如何在 COGITO 中微調現有的移動機制，並添加動作遊戲中常見的進階動作，如「趴下 (Prone)」、「手動翻滾 (Dodge Roll)」以及「瞄準時減速」。

## 前置知識
- 已閱讀 [Level 5E: 玩家完整移動系統](../architecture/level5e_player_movement.md)。
- 熟悉 `cogito_player.gd` 中的物理流程。

---

## 1. 微調內建動作 (Sprint, Crouch, Slide)

COGITO 已經內建了基本的快跑、蹲下與滑步。

### 調整參數
在 `cogito_player.gd` 的 Inspector 中，您可以直接修改：
- **快跑**：`SPRINTING_SPEED` (速度), `stamina_attribute` (是否耗耐力)。
- **蹲下**：`CROUCHING_SPEED` (速度), `CROUCHING_DEPTH` (相機下降深度)。
- **滑步**：`SLIDING_SPEED` (滑行初速), `SLIDE_JUMP_MOD` (滑跳加成)。

---

## 2. 添加「趴下 (Prone)」動作

趴下是比蹲下更低、更慢的狀態。

### 實作步驟
1. **新增變數**：在 `cogito_player.gd` 定義趴下參數。
   ```gdscript
   @export var PRONING_SPEED : float = 1.5
   @export var PRONING_DEPTH : float = -1.4
   var is_proning : bool = false
   ```

2. **新增碰撞形狀**：
   - 在 `CogitoPlayer` 場景中，複製 `CrouchingCollisionShape` 並命名為 `ProningCollisionShape`。
   - 縮小其高度（例如 Height = 0.5）。
   - 在腳本頂部連結它：`@onready var proning_collision_shape = $ProningCollisionShape`。

3. **處理輸入與切換**：
   在 `_physics_process` 的蹲下邏輯附近增加趴下判定。通常邏輯是：站立 → 蹲下 → 趴下。
   ```gdscript
   # 偽代碼示例
   if Input.is_action_just_pressed("crouch"):
       if !is_crouching:
           enter_crouch()
       else:
           enter_prone()
   ```

4. **更新物理狀態**：
   在處理速度與相機高度時，加入 `is_proning` 的判定，並關閉其他碰撞形狀。

---

## 3. 手動觸發「翻滾 (Dodge Roll)」

COGITO 內建了落地的滾動動畫，我們可以將其改為手動觸發的閃避動作。

### 實作步驟
1. **處理輸入**：
   ```gdscript
   if Input.is_action_just_pressed("dodge") and is_on_floor():
       animationPlayer.play("roll")
       # 給予一個瞬間衝量
       velocity += direction * 10.0 
   ```

2. **無敵時間 (I-Frames)**：
   若要加入無敵時間，可以在播放動畫時暫時關閉受擊判定：
   ```gdscript
   func _on_roll_started():
       player_interaction_component.is_invulnerable = true
       await get_tree().create_timer(0.5).timeout
       player_interaction_component.is_invulnerable = false
   ```

---

## 4. 瞄準 (ADS) 與移動速度整合

預設情況下，瞄準 (Secondary Action) 只會縮放 FOV。我們希望瞄準時玩家會減速。

### 實作步驟
1. **玩家端監聽**：在 `cogito_player.gd` 監聽當前武器的瞄準狀態。
2. **修改速度計算**：
   在 `_physics_process` 中計算 `current_speed` 時：
   ```gdscript
   var ads_multiplier = 0.5 # 瞄準時速度減半
   if player_interaction_component.get_current_wieldable().is_aiming:
       target_speed *= ads_multiplier
   ```
   *(註：需在具體武器腳本如 `wieldable_toy_pistol.gd` 中新增 `is_aiming` 變數並在 `action_secondary` 中切換)*

---

## 5. 滑步閃避 (Slide Dodge)

您可以將 Dash 與 Slide 結合。

### 實作步驟
1. **邏輯**：當玩家在快跑中按下閃避鍵，強制進入 Slide 狀態但給予更高的初始推力。
2. **代碼**：
   ```gdscript
   if is_sprinting and Input.is_action_just_pressed("dodge"):
       sliding_timer.start()
       velocity += direction * SLIDING_SPEED * 1.5
   ```

---

## 驗證方式

1. **趴下測試**：確認趴下時碰撞盒正確縮小，能鑽過蹲下鑽不過去的縫隙。
2. **翻滾測試**：觀察翻滾時是否有明顯的位移加成，且動畫播放正確。
3. **瞄準減速測試**：裝備手槍並按住右鍵，確認移動速度是否明顯變慢。
