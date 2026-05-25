# Level 3 Analysis: 進階機制與模擬

> 核對於 2026-05-25（Claude Code, Opus 4.7）：AI 統一輸入模型、樹狀實體追蹤、流程狀態機皆與源碼一致；本次修正了波次資料來源（`EnemyManager.wave_queue`）與信號鏈細節，並補上腳本路徑與行號。

## 1. AI 決策鏈與行為模型
AI 系統採用了高度模組化的「感官-決策-執行」架構。

### 1.1 感官：TargetFinder
- **檔案路徑**: `addons/top_down/scripts/actor/bots/TargetFinder.gd`
- 使用 `ShapeCast2D`（`@export var shape_cast`）進行範圍掃描；於 `BotInput.input_update` 信號觸發時才更新（`TargetFinder.gd:17-19`），跳過 `StaticBody2D`（`:26`）。
- 透過 `GameMath.get_closest_node_2d(bot_input.global_position, target_list, target_count)` 找出最接近的目標（`TargetFinder.gd:32`）。

### 1.2 執行：BotInput (抽象輸入)
- **檔案路徑**: `addons/top_down/scripts/actor/bots/BotInput.gd`
- AI 的輸出不是直接的操作，而是填充 `InputResource` 的 `axis` 向量（透過 `resource_node.get_resource("input")`，`BotInput.gd:20`）。
- 以 `process_physics_priority -= 1` 確保在 Mover 之前執行（`BotInput.gd:18`），每物理幀發出 `input_update`（`:37`），驅動 TargetFinder / TargetAim 等下游模組。
- 這使得 AI 與 Player 共用同一條移動鏈，具有物理上的一致性，且易於調試（可隨時人工接管）。

## 2. 敵人波次管理與實體生命週期
- **EnemyWaveManager**（`addons/top_down/scripts/arena/EnemyWaveManager.gd`）: 
    - 以 `fight_mode_resource` (BoolResource) 控制戰鬥狀態，並用三個 IntResource：`wave_number_resource`、`remaining_wave_count_resource`、`enemy_count_resource` 串成信號鏈（`EnemyWaveManager.gd:4-21`）。
    - **波次資料實際來源是 `enemy_manager.wave_queue.waves`**（一個 `SpawnWaveList` 佇列），於 `_init_wave_count()` 讀取其 `size()`，每清空一波 `pop_front()`（`EnemyWaveManager.gd:30,39,53`）。每個 `SpawnWaveList` 帶有 `count` 欄位（`:40`）。
- **分裂實體追蹤 (ActiveEnemy)**（`addons/top_down/scripts/actor/bots/ActiveEnemy.gd`）:
    - 解決了分裂敵人（如 Slime）的計數難題。
    - 使用**靜態**樹狀結構：`static var root:ActiveEnemyResource`、`static var instance_dictionary`、`static var active_instances`（`ActiveEnemy.gd:7-12`）。`ActiveEnemyResource` 為雙向鏈結（`parent` / `children` / `nodes`，`ActiveEnemyResource.gd:5-9`）。
    - `insert_child()` 必須在自身移除前先掛上子節點（`ActiveEnemy.gd:16-24`）；`remove_branch()` 僅在 `nodes` 與 `children` 皆空時觸發 `clear_callback` 並遞迴向上清除（`:27-48`）。
    - 只有當葉子節點（最後的分裂體）消失且沒有子節點時，該分支才算清空（即整株血脈消滅才計為一次擊殺）。

## 3. 地圖導航與 AStar 整合
- **AstarGridResource**（`addons/great_games_library/resources/ValueResource/AstarGridResource.gd`）: 封裝了 `AStarGrid2D` 的參數（啟發式算法、對角線模式）。
- **障礙物自動更新**: 
    - 透過 `nodes/utility/TileAstargridObstacle.gd` 掃描 TileMapLayer 中的特定圖層，搭配 `nodes/Navigation/`（`TileCollisionGenerator`、`TileNavigationSetter` 等）將 TileMap 碰撞數據映射至 AStar 網格，實現導航與視覺同步。

## 4. 遊戲流程狀態機
遊戲的整體進程（戰鬥開始 → 敵人清空 → 下一波 → 勝利/失敗）由一連串資源更新信號驅動（`EnemyWaveManager.gd:19-21` 建立連線）：
1. `fight_mode_resource.changed_true` → `_init_wave_count()`：讀取 `wave_queue.waves.size()` 設定剩餘波數。
2. `remaining_wave_count_resource.updated` → `_reset_enemy_count()`：若剩 0 則結束戰鬥，否則取下一波 `count` 設為待殺敵數。
3. `EnemySpawner` 依當前波生成敵人；`ActiveEnemy` 在血脈整株消滅時遞減 `enemy_count_resource`。
4. `enemy_count_resource.updated` → `_update_wave_count()`：歸零時 `pop_front()` 進下一波並遞增 `wave_number_resource`（`EnemyWaveManager.gd:45-57`）。
5. 資源數值更新觸發 UI 顯示（如 `wave_label.gd`）。
