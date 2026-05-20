# turnmap_cpp — 標準回合制方格地圖示範

一個**零依賴、純終端機 (ASCII)** 的最小回合制 2D 方格地圖 (square tilemap) 範例，
目的是把「一個標準回合制 tilemap 是怎麼運作的」用最少的程式碼講清楚。

玩家是 `@`，要避開或擊敗哥布林 `g`，走到出口 `>` 即可逃脫。

```
  ############
  #@...#....>#
  #....#.###.#
  #.##...#...#
  #.#..g.#.#.#
  #.#.##.#.#.#
  #...~~...#.#
  ############
  HP: 20   敵人: 1
  圖例: @ 你   g 哥布林   # 牆   ~ 水   > 出口
```

---

## 建置與執行

需要 CMake 3.17+ 與支援 C++17 的編譯器。

```bash
cmake -B build
cmake --build build
./build/turnmap
```

每個回合輸入一個方向鍵後按 Enter：

| 按鍵 | 動作 |
| --- | --- |
| `w` / `a` / `s` / `d` | 上 / 左 / 下 / 右 移動 |
| （朝敵人移動） | 攻擊該單位（bump-to-attack） |
| `q` | 離開 |

---

## 一個「標準回合制 tilemap」由哪些部分組成？

整個示範刻意拆成幾個互相獨立的層次，這也是大多數回合制遊戲的通用結構：

### 1. 地形層 — `TileMap`
`include/turnmap/tile.hpp`、`include/turnmap/tilemap.hpp`、`src/tilemap.cpp`

- 用一維 `std::vector` 以**行優先 (row-major)** 儲存二維格子：`index = y * width + x`
  （`TileMap::at()` / `set()`，`src/tilemap.cpp`）。
- 每格是一個 `TileType`（地板 / 牆 / 水 / 出口），地形自帶
  `tileWalkable()` 屬性決定能不能踏入（`tile.hpp`）。
- `inBounds()` 邊界檢查 + `isWalkable()` 是所有移動的第一道關卡
  （`TileMap::isWalkable`, `src/tilemap.cpp`）。
- `fromAscii()` 讓你直接用字串手繪關卡（`src/tilemap.cpp`）。

### 2. 單位層 — `Entity`
`include/turnmap/entity.hpp`

- 單位的**位置與地形是分開的兩層資料**：地形存在 `TileMap`，
  單位另外放在一個清單裡。渲染時把單位「疊」在地形之上。
- 每個單位有座標、字元、HP、攻擊力與陣營 (`Team::Player` / `Team::Enemy`)。

### 3. 回合迴圈 — `Game`
`include/turnmap/game.hpp`、`src/game.cpp`

整局遊戲的骨架就是 `Game::run()`（`src/game.cpp`）裡這個迴圈：

```cpp
while (running_) {
    render();              // 1. 畫出目前狀態（地形層 + 單位層）
    if (!handlePlayerTurn()) break;  // 2. 停下來等玩家輸入並結算
    handleEnemyTurns();    // 3. 所有敵人依序各行動一次
    ++turn_;
    checkEndConditions();  // 玩家是否陣亡？
}
```

**這就是「回合制」的核心**：遊戲在 `handlePlayerTurn()` 主動停下來等輸入
（`std::getline`），不像即時遊戲靠時間軸推進。
「玩家行動一次 + 所有敵人各行動一次」構成一個完整回合 (round)。

### 4. 行動結算 — `Game::tryAct()`
`src/game.cpp`

玩家與敵人共用同一套「往某方向行動」的規則，依序判斷：

1. 目標格能不能走（邊界 + 地形）→ 不能就無效（撞牆不耗回合）。
2. 目標格有沒有別的單位 → 敵對就**攻擊**、同隊就擋路。
3. 都沒有 → **移動**；玩家踩到出口即獲勝。

回傳值代表「這次行動有沒有真的用掉一個回合」，讓撞牆/按錯鍵不浪費回合。

### 5. 尋路 — A\*
`include/turnmap/pathfinding.hpp`、`src/pathfinding.cpp`

`findPath()` 在方格上用 **A\*** 找最短路徑（四方向、每步成本 1）：

- `g_score` / `came_from` / `closed` 全用 flat 一維陣列，open set 用
  `std::priority_queue` 當最小堆（依 `f = g + h` 排序）。
- heuristic 用 **Manhattan 距離**，在四方向 + 單位成本下不會高估（admissible），
  所以保證找到最短路徑。
- 回傳「不含 start、含 goal」的格子序列，`path.front()` 就是下一步。
- 特例：goal 那格即使被佔據也允許當終點 —— 讓敵人能把玩家所在格當目標。

### 6. 敵人 AI — `Game::handleEnemyTurns()`
`src/game.cpp`

每個敵人每回合都用 `findPath()` 重新規劃一條到玩家的路徑，**只踏出第一步**。
因為每回合重算，玩家移動後敵人會即時修正路線、繞過牆與水，不會卡在牆角。
路徑第一步若落在玩家所在格，`tryAct()` 會自動判定為攻擊（bump-to-attack）。

> 註：A\* 只規劃在**地形**上的路（`isWalkable`）；多個單位互相擋路這種
> 「動態障礙」交由每一步的 `tryAct()` 處理 —— 走不過去該回合就停在原地。

---

## 想再往下做的方向（練習用）

- 讓 A\* 支援**不同地形成本**（如水可走但較慢），把每步成本從固定 1 改成查表。
- 加入**行動點數 / 速度**，讓不同單位一回合能走不同步數。
- 加入**視野 / 戰爭迷霧**（只渲染玩家看得見的格子）。
- 把渲染層抽換成圖形後端（如 raylib），邏輯層完全不用動 ——
  這正是把地形/單位/回合迴圈分層的好處。
