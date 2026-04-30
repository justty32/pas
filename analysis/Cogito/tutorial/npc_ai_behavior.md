# 教學：如何修改與擴充 NPC AI 行為

COGITO 的 NPC 使用基於場景樹的狀態機 (`NPC_State_Machine`)。本教學將教您如何強化 AI，使其具備聽覺、視野判定，以及多個 NPC 之間的協同行為。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。

## 實作步驟

### 1. 強化感知：加入視覺圓錐 (Vision Cone)
預設的 `chase` 狀態通常由一個簡單的 `Area3D` 觸發。為了讓潛行更真實，我們可以在 NPC 頭部加入射線檢測。
1. 在 NPC 節點下建立一個 `RayCast3D`，命名為 `VisionRayCast`，朝向前方。
2. 在 `npc_state_idle.gd` 或 `npc_state_patrol_on_path.gd` 的 `_physics_process` 中加入視線檢查：
   ```gdscript
   func _physics_process(_delta):
       var player = get_tree().get_first_node_in_group("Player")
       if player:
           # 檢查距離與角度
           var dir_to_player = Host.global_position.direction_to(player.global_position)
           var forward_dir = -Host.global_transform.basis.z
           if forward_dir.dot(dir_to_player) > 0.5: # 大約 90 度視角
               $VisionRayCast.target_position = $VisionRayCast.to_local(player.global_position)
               $VisionRayCast.force_raycast_update()
               if $VisionRayCast.get_collider() == player:
                   # 看到玩家，進入追擊
                   Host.attention_target = player
                   States.goto("chase")
   ```

### 2. 強化感知：聽覺 (Hearing Area)
1. 在玩家的腳步聲組件 (`ImpactSounds` 或 `FootstepPlayer`) 中，加入發射全域信號的功能：`SignalBus.noise_made(position, volume)`。
2. 在 NPC 的 `_ready()` 中訂聽此信號：
   ```gdscript
   func _on_noise_made(noise_pos: Vector3, volume: float):
       var distance = global_position.distance_to(noise_pos)
       if distance < volume: # 聲音夠大且夠近
           # 轉向聲音來源並進入警戒狀態 (需自建 npc_state_alert.gd)
           Host.attention_target_pos = noise_pos
           States.goto("alert")
   ```

### 3. 群體協同 (Swarm AI)
讓一隻 NPC 發現玩家時，呼叫附近的同伴：
1. 在 `npc_state_chase.gd` 的 `_state_enter()` 中加入廣播邏輯：
   ```gdscript
   func _state_enter():
       # 原有追擊邏輯...
       alert_allies()

   func alert_allies():
       var allies = get_tree().get_nodes_in_group("Enemy")
       for ally in allies:
           if ally != Host and ally.global_position.distance_to(Host.global_position) < 20.0:
               if ally.npc_state_machine.current != "chase":
                   ally.attention_target = Host.attention_target
                   ally.npc_state_machine.goto("chase")
   ```

## 驗證方式
1. **視覺測試**：在 NPC 背後移動，NPC 不應反應；走到 NPC 正前方，NPC 應立刻轉入 `chase` 狀態。
2. **聽覺測試**：在牆壁後方開槍或跳躍，NPC 應走向發出聲音的位置 (`alert` 狀態)。
3. **協同測試**：放置三隻 NPC，故意被其中一隻看見，確認另外兩隻是否也自動進入追擊狀態。
