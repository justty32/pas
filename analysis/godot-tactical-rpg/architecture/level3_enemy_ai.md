# Level 3 — 敵人 AI 決策鏈

> 路徑相對於 `projects/godot-tactical-rpg/`。前置：`level3_grid_pathfinding.md`（BFS、最近目標搜尋）、`level3_turn_and_combat.md`（stage 機）。

README 自嘲是「super basic (and stupid) enemy AI」。它確實簡單，但完整呈現了一條「選棋 → 找最近敵人 → 移動到鄰格 → 選最弱目標 → 攻擊」的決策鏈，是學習戰棋 AI 骨架的好範例。

---

## 1. AI 的 stage 流程（0~4 全自動）

對手（`TacticsOpponent`）共用同一套 `stage`，但 handler 是 `handle_opponent_turn`（`turn.gd:55-66`），只跑 stage 0~4，且每影格自動推進（無需輸入）。`turn.gd:58` 的 `if res.stage > 4: res.stage = 0` 確保 AI 不會誤入玩家專屬的 stage 5~7。

```mermaid
stateDiagram-v2
    [*] --> S0
    S0: stage0 choose_pawn\n挑一個還能動且活著的 pawn
    S1: stage1 chase_nearest_enemy\n算移動範圍→找最近敵人鄰格→存路徑
    S2: stage2 is_pawn_done_moving\n等 tilestack 清空
    S3: stage3 choose_pawn_to_attack\n標攻擊範圍→挑最弱可打目標
    S4: stage4 attack_pawn\n結算傷害→換下一隻
    S0 --> S1 --> S2 --> S3 --> S4 --> S0
```

每一步對應 `TacticsOpponent` 的方法（`tactics_opponent.gd`），再轉發給 `TacticsOpponentService`（`opponent_service/service.gd`）。

---

## 2. 決策鏈逐步拆解

### Stage 0 — 選一隻 pawn：`choose_pawn`
`opponent_service/service.gd:42-48`
```gdscript
for p in opponent.get_children():
    if p.can_act() and p.is_alive():
        res.curr_pawn = p
        res.stage = STAGE_SHOW_ACTIONS  # → 1
        return
```
**策略：第一個能行動的就選**——按節點順序，無優先級評估（不看血量/位置/威脅）。

### Stage 1 — 追擊最近敵人：`chase_nearest_enemy`
`opponent_service/service.gd:55-71`，這是 AI 最核心的一步：
1. 用 BFS 算出 `curr_pawn` 的移動範圍：`process_surrounding_tiles(起點, movement, 友軍)` + `mark_reachable_tiles`。
2. 找「最近的、緊鄰某個玩家 pawn 的可達格」：`get_nearest_target_adjacent_tile`（見下）。
3. 把到該格的路徑存進 `curr_pawn.res.pathfinding_tilestack`，並把 `camera.target` 設成目標格（鏡頭跟著看）。
4. `stage = STAGE_SHOW_MOVEMENTS`（→ 2）。

若 pawn 已不能移動（只剩攻擊），直接回 stage 0。

#### 「最近敵人鄰格」搜尋：`get_nearest_target_adjacent_tile`
`arena/service/service.gd:86-103`
```gdscript
for _p in target_pawns:                          # 走訪所有玩家 pawn
    if _p.curr_health <= 0: continue             # 跳過已死
    for _n in _p.get_tile().get_neighbors(jump): # 該敵人四周的格子
        if (沒有最近目標 or _n.pf_distance < 最近.pf_distance):
            if _n.pf_distance > 0 and not _n.is_taken():
                最近 = _n                          # 取 BFS 距離最小者
while 最近 and not 最近.reachable:                # 若超出移動力
    最近 = 最近.pf_root                            # 沿路徑退到能到的最遠格
return 最近 if 最近 else pawn.get_tile()          # 找不到就原地不動
```
**精髓**：以 `pf_distance` 衡量「離我多遠」，挑離自己最近的「敵人旁邊空格」。若該格超過移動力（`not reachable`），就沿 `pf_root` 一路退到「在移動力內、最靠近目標」的格子——即「能走多近就走多近」。

### Stage 2 — 等移動完成：`is_pawn_done_moving`
`opponent_service/service.gd:75-79`：每影格檢查 `pathfinding_tilestack.is_empty()`，空了就進 stage 3。實際移動由 pawn 的 movement service 執行（與玩家共用，見 `level3_turn_and_combat.md` 第 3 節）。

### Stage 3 — 選最弱目標：`choose_pawn_to_attack`
`opponent_service/service.gd:83-98`
1. 以 `curr_pawn` 為中心標出攻擊範圍（`process_surrounding_tiles` + `mark_attackable_tiles`，距離 = `attack_range`）。
2. `get_weakest_attackable_pawn(玩家全員)` 挑目標：
   `arena/service/service.gd:109-117`
   ```gdscript
   for _p in pawn_arr:
       if (沒有最弱 or _p.curr_health < 最弱.curr_health):
           if _p.curr_health > 0 and _p.get_tile().attackable:  # 活著且在攻擊格內
               最弱 = _p
   ```
   **策略：射程內血量最低者**（集火殘血）。
3. 找到就把 `res.attackable_pawn` 設好、鏡頭聚焦目標；找不到則 `attackable_pawn` 維持 null。`stage = STAGE_MOVE_PAWN`（→ 4）。

### Stage 4 — 攻擊：`attack_pawn`（共用玩家的 combat service）
`participant/service/combat.gd:30-52`，`is_player=false`：
- 有目標 → `curr_pawn.attack_target_pawn(attackable_pawn, delta)` 結算傷害（同一套傷害公式）。
- 無目標 → `curr_pawn.res.can_attack = false`（放棄攻擊）。
- 結束後因 `is_player=false`，一律 `stage = STAGE_SELECT_PAWN`（→ 0）換下一隻 pawn。

當 AI 所有 pawn 都 `can_act()=false` 時，`TacticsLevel` 偵測到雙方都不能動 → 重置回合，控制權回到玩家。

---

## 3. AI 行為特徵與已知侷限

| 特徵 | 說明 | 程式位置 |
|---|---|---|
| 選棋無策略 | 按子節點順序挑第一個能動的 | `opponent_service/service.gd:44` |
| 移動目標 = 最近敵人旁 | 用 BFS `pf_distance` 衡量距離 | `arena/service/service.gd:92` |
| 攻擊目標 = 射程內最弱 | 集火殘血，不算「能否反殺」「威脅值」 | `arena/service/service.gd:113` |
| 走不到就盡量靠近 | 沿 `pf_root` 退到可達最近格 | `arena/service/service.gd:96-97` |
| 不考慮地形優勢/陣型 | 純距離與血量啟發式 | — |
| 不會原地等待/防守 | 永遠主動推進 | — |

> `strategy` 欄位（`stats_res.gd:13`，列舉 Tank/Flank/Physical/Distance/Support）目前在 AI 決策中**完全未被使用**——是預留給日後實作不同 AI 性格的 hook。詳見 `others/observations.md`。

AI 過程的除錯輸出（`DebugLog.debug_enabled` 為真時）會印出「moving to / Through / Weakest target detected / No target detected」等彩色訊息（`opponent_service/service.gd:64-67, 90-96`），方便觀察決策。

---

## 4. 擴充 AI 的切入點

若要做更聰明的 AI，最小侵入的改法是替換 `TacticsOpponentService` 內三個啟發式函式：
- **選棋**：改 `choose_pawn`（`opponent_service/service.gd:42`）加入威脅/距離評分。
- **移動目標**：改 `arena/service/service.gd::get_nearest_target_adjacent_tile`，或在 `chase_nearest_enemy` 內換成自訂目標選擇。
- **攻擊目標**：改 `arena/service/service.gd::get_weakest_attackable_pawn`，例如改成「能一擊擊殺者優先」或依 `strategy` 分流。

由於 AI 與玩家共用 BFS、標色、移動、戰鬥 service，只要不動這些共用層，AI 的「規則」是相對獨立、好替換的。
