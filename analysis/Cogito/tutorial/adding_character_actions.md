# 教學：如何替玩家與 NPC 添加新動作

本教學將引導您如何在 COGITO 中擴充角色的行為，包括為玩家添加「衝刺 (Dash)」機制，以及為 NPC 建立新的「隨機遊走 (Wander)」狀態。

## 前置知識
- 已閱讀 [Level 5E: 玩家完整移動系統](../architecture/level5e_player_movement.md)。
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。
- 瞭解 Godot 的 `CharacterBody3D` 基本物理處理。

---

## 玩家動作：添加「衝刺 (Dash)」

### 原始碼導航
- `addons/cogito/CogitoObjects/cogito_player.gd`

### 實作步驟

1. **定義變數**：在 `cogito_player.gd` 的 `Movement Properties` 分組下新增衝刺參數。
   ```gdscript
   # addons/cogito/CogitoObjects/cogito_player.gd 附近第 100 行
   @export var DASH_SPEED : float = 20.0
   @export var DASH_DURATION : float = 0.2
   var is_dashing : bool = false
   ```

2. **處理輸入**：在 `_unhandled_input(event)` 中監聽衝刺按鍵（假設您已在 Input Map 設定 "dash"）。
   ```gdscript
   if event.is_action_pressed("dash") and !is_dashing and is_on_floor():
       start_dash()
   ```

3. **實作衝刺邏輯**：使用 Timer 或協程處理衝刺狀態。
   ```gdscript
   func start_dash():
       is_dashing = true
       var dash_direction = direction if direction != Vector3.ZERO else -head.global_transform.basis.z
       velocity = dash_direction * DASH_SPEED
       await get_tree().create_timer(DASH_DURATION).timeout
       is_dashing = false
   ```

4. **物理整合**：在 `_physics_process` 中，如果 `is_dashing` 為真，應跳過常規的加速度計算。

---

## NPC 動作：添加「隨機遊走 (Wander)」狀態

COGITO 的 NPC 使用場景樹掛載式的狀態機，新增狀態非常簡單。

### 原始碼導航
- `addons/cogito/CogitoNPC/npc_states/` (狀態腳本存放地)
- `addons/cogito/CogitoNPC/npc_states/npc_state_machine.gd` (狀態機核心)

### 實作步驟

1. **建立狀態腳本**：建立 `npc_state_wander.gd` 並繼承自 `Node`。
   ```gdscript
   # addons/cogito/CogitoNPC/npc_states/npc_state_wander.gd
   extends Node

   var Host # 由狀態機自動賦值
   var States # 由狀態機自動賦值

   func _state_enter():
       # 當進入此狀態時執行
       var random_pos = Host.global_position + Vector3(randf_range(-5,5), 0, randf_range(-5,5))
       Host.set_navigation_target(random_pos)

   func _physics_process(_delta):
       # 檢查是否到達目的地
       if Host.navigation_agent.is_navigation_finished():
           States.goto("idle")
   ```

2. **掛載狀態**：
   - 在 Godot 編輯器中，找到 NPC 下的 `NPC_State_Machine` 節點。
   - 將一個新的 `Node` 加入作為其子節點。
   - 將剛剛寫好的 `npc_state_wander.gd` 掛載到該節點上。
   - 將該節點重新命名為 `wander`（狀態機預設以節點名稱作為狀態名）。

3. **觸發切換**：
   - 修改 `npc_state_idle.gd`，讓它在一段時間後有機率進入 `wander` 狀態：
   ```gdscript
   # 在 npc_state_idle.gd 中
   func _state_enter():
       await get_tree().create_timer(randf_range(2, 5)).timeout
       States.goto("wander")
   ```

---

## 驗證方式

### 玩家衝刺驗證
1. 確保已在 Godot 專案設定的 **Input Map** 加入 `dash` 動作（例如綁定到 `Shift` 或 `Q`）。
2. 運行遊戲，在移動中按下衝刺鍵。
3. 確認角色是否有瞬間加速，且在 `DASH_DURATION` 結束後恢復正常速度。

### NPC 遊走驗證
1. 觀察場景中的 NPC。
2. 確認 NPC 在 `idle` 狀態結束後，會朝向隨機位置移動。
3. 使用 `is_logging = true` 檢查控制台，確認是否有 `Idle state exiting` 與進入新狀態的 Log。
