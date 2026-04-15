# Level 3 Analysis: 進階機制與模擬

## 1. AI 決策鏈與行為模型
AI 系統採用了高度模組化的「感官-決策-執行」架構。

### 1.1 感官：TargetFinder
- 使用 `ShapeCast2D` 進行圓形範圍掃描。
- 透過 `GameMath.get_closest_node_2d` 找出最接近的目標（通常是玩家）。

### 1.2 執行：BotInput (抽象輸入)
- AI 的輸出不是直接的操作，而是填充 `InputResource` 的 `axis` 向量。
- 這使得 AI 與 Player 具有物理上的一致性，且易於調試（可以隨時切換人工接管 AI 角色）。

## 2. 敵人波次管理與實體生命週期
- **EnemyWaveManager**: 
    - 使用 `fight_mode_resource` (BoolResource) 控制戰鬥狀態。
    - 波次定義於 `SpawnWaveList` 資源中。
- **分裂實體追蹤 (ActiveEnemy)**:
    - 解決了分裂敵人（如 Slime）的計數難題。
    - 使用靜態樹狀結構 `ActiveEnemyResource` 紀錄實體血脈。
    - 只有當葉子節點（最後的分裂體）消失且沒有子節點時，該分支才算清空。

## 3. 地圖導航與 AStar 整合
- **AstarGridResource**: 封裝了 `AStarGrid2D` 的參數（啟發式算法、對角線模式）。
- **障礙物自動更新**: 
    - 專案透過 `TileAstargridObstacle` 掃描 TileMap 中的特定圖層。
    - 將 TileMap 的碰撞數據直接映射到 AStar 網格中，實現了導航與視覺的同步。

## 4. 遊戲流程狀態機
遊戲的整體進程（戰鬥開始 -> 敵人清空 -> 下一波 -> 勝利/失敗）是由一連串的資源更新信號驅動的：
1. `fight_mode_resource` 變為 true。
2. `EnemyWaveManager` 初始化波次。
3. `EnemySpawner` 根據 `SpawnWaveList` 生成敵人。
4. `ActiveEnemy` 回報消滅進度。
5. 資源數值更新觸發 UI 顯示。
