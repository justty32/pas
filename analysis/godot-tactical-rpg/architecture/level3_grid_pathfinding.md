# Level 3 — 格子地圖、移動範圍計算與 Pathfinding

> 路徑相對於 `projects/godot-tactical-rpg/`。前置：`level2_core_modules.md` 第 1、5、6 節。

這是戰棋系統最核心的部分：地圖如何成為可走訪的格子、如何算出「移動範圍／攻擊範圍」、以及怎麼回溯出一條移動路徑。

---

## 1. 地圖怎麼變成格子：執行期把 mesh 轉成 StaticBody3D

地圖（`assets/maps/level/arena/test_arena.tscn`）在編輯器裡只是 `Tiles` 節點底下約 200 個 `MeshInstance3D`（Blender 匯出的方塊，命名 `Tile`、`Tile001`…）。它們**沒有碰撞、沒有腳本**。真正的「格子」是在執行期由 `TacticsTileService.tiles_into_staticbodies` 動態生成的。

**轉換流程**（`data/models/world/combat/arena/tile_service/service.gd:10-37`）：對每個 `MeshInstance3D`：
1. `create_trimesh_collision()` 自動生成一個帶 `CollisionShape3D` 的 `StaticBody3D` 子節點。
2. 把該 `StaticBody3D` 抽出來、繼承原 mesh 的位置；原 mesh 改名為 `Tile`、歸零位置、塞進 StaticBody 底下。
3. 給 StaticBody **掛上 `tactics_tile.gd`**（`set_script(TacticsTile)`），呼叫 `configure_tile()` 初始化。

結果：每個原始 mesh 都變成
```
StaticBody3D (TacticsTile 腳本)
├── Tile (原 MeshInstance3D，當作可視高亮層)
├── CollisionShape3D
└── RayCasting (configure_tile 時 instantiate)
```

由 `TacticsArena.configure_tiles`（`tactics_arena.gd:25` → `arena/service/service.gd:37`）在 `TacticsLevel._ready` 時觸發。

> 設計意義：地圖作者只要在 Blender 擺好方塊，無需手動加碰撞或腳本；引擎自動「格子化」。這正是 README 所說的「Blender map recognition」。

---

## 2. 一個格子知道誰是鄰居：射線探測（不用座標索引）

本專案**不維護 `(x, y)` 格子陣列或鄰接表**。一個 tile 要找鄰居，是靠子節點 `RayCasting` 下掛的多條 `RayCast3D`（四方向）做物理偵測。

`TacticsTileRaycast.get_all_neighbors(height)`（`data/modules/tactics/level/arena/tile/raycast/tile_raycasting.gd:13-24`）：
- 走訪 `$Neighbors` 下每條射線的 collider；
- 只有當鄰居 tile 與自己的高度差 `abs(Δy) <= height` 時才算「可達鄰居」。

`height` 由呼叫端傳入——通常是該 pawn 的**跳躍力 `jump` 或移動力 `movement`**。這就是「**台階高低差會限制能否走過去**」的實作來源：高度差超過跳躍力的鄰居，射線雖打得到，但被 `height` 過濾掉。

另外兩條輔助查詢（`tactics_tile.gd:71-77`）：
- `get_tile_occupier()`：向上的 `$Above` 射線回傳站在這格上的物件（pawn）。
- `is_taken()`：該格是否已被佔據。

---

## 3. 移動範圍計算：BFS flood-fill

「這隻 pawn 能走到哪些格子」用**廣度優先搜尋（BFS）** 從起點 tile 向外擴散，記錄每格的「距離」與「從哪格來」。

**核心**：`TacticsArenaService.process_surrounding_tiles`（`data/models/world/combat/arena/service/service.gd:47-64`）

```gdscript
func process_surrounding_tiles(root_tile, height, allies_on_map=[]):
    var _q = [root_tile]
    while not _q.is_empty():
        var _curr = _q.pop_front()
        for _neighbor in _curr.get_neighbors(height):     # 射線找鄰居（受高度限制）
            if not _neighbor.pf_root and _neighbor != root_tile:
                if not _neighbor.is_taken():               # 空格 → 加入佇列
                    _neighbor.pf_root = _curr              # 記「從哪來」
                    _neighbor.pf_distance = _curr.pf_distance + 1  # 記「距離」
                    _q.push_back(_neighbor)
                elif ... allies_on_map ...                 # 友軍格可穿越（見下）
```

每個 tile 兩個 pathfinding 欄位（`tactics_tile.gd:21-24`）：
- `pf_root: TacticsTile` — 回溯指標（BFS 樹的父節點），用來重建路徑。
- `pf_distance: float` — 從起點走幾步。

> 注意：這個 BFS **不限制擴散距離**——它把整張連通圖都標上 `pf_distance`。實際的「移動力上限」是在標色階段才用 `pf_distance <= distance` 過濾（見第 4 節）。`get_pathfinding_tilestack` 回溯時也不檢查步數，因此玩家流程靠 UI 只准點 `reachable` 格子來間接限制。

### 友軍可穿越邏輯
`allies_on_map` 參數讓「被己方 pawn 佔住的格子可以走過去（但不能停）」。傳入時機：
- 玩家顯示移動範圍：`show_available_movements`（`player_service/service.gd:73`）傳入 `p.get_parent().get_children()`（同隊全員）。
- AI 追擊：`chase_nearest_enemy`（`opponent_service/service.gd:58`）傳入 `opponent.get_children()`。

> 觀察：`service.gd:62` 的條件 `elif not (allies_on_map.size() > 0)` 邏輯看起來有瑕疵（當有友軍時整個 elif 反而不成立），疑為 bug，詳見 `others/observations.md`。

---

## 4. 把範圍畫出來：reachable / attackable / hover 標色

BFS 標好 `pf_distance` 後，由兩個函式依距離上限決定哪些格子高亮：

**可移動格**：`mark_reachable_tiles`（`arena/service/service.gd:135-142`）
```gdscript
_t.reachable = (_t.pf_distance > 0 and _t.pf_distance <= distance and not _t.is_taken()) or (_t == root)
```
`distance` = pawn 的 `stats.movement`（移動力）。

**可攻擊格**：`mark_attackable_tiles`（`arena/service/service.gd:149-155`）
```gdscript
_t.attackable = (_t.pf_distance > 0 and _t.pf_distance <= distance) or (_t == root)
```
`distance` = pawn 的 `stats.attack_range`（攻擊距離）；注意攻擊範圍**不排除被佔據的格**（要打的就是站人的格）。

每個 tile 的 `_process`（`tactics_tile.gd:38-60`）依 `hover / reachable / attackable` 三個 bool 的組合，從 `TacticsConfig.mat_color` 字典挑半透明材質覆蓋上去：

| 狀態 | 顏色（`tactics_config.gd:19-25`） |
|---|---|
| hover（純滑鼠懸停） | 半透明白 |
| reachable | 半透明藍（blue_cola） |
| reachable + hover | 亮藍（blue_bolt） |
| attackable | 半透明紅（rosso_corsa） |
| attackable + hover | 珊瑚紅（coral_red） |

`reset_all_tile_markers`（`arena/service/service.gd:30`）在每次切換動作前清空所有 tile 的標記。

---

## 5. 重建一條路徑：pathfinding tilestack

選好落點後，要把「起點→落點」的逐格座標列出來給 pawn 沿著走。靠 `pf_root` 一路回溯：

`TacticsArenaService.get_pathfinding_tilestack`（`arena/service/service.gd:70-79`）：
```gdscript
func get_pathfinding_tilestack(to):
    var stack = []
    while to:
        to.hover = true
        stack.push_front(to.global_position)   # 用 push_front → 起點在最前
        to = to.pf_root                         # 往父節點回溯
    return stack                                # Array[Vector3] 世界座標
```

結果是一個 `Array[Vector3]`（世界座標），存入 `pawn.res.pathfinding_tilestack`。pawn 的移動 service 會逐一 `pop_front` 消化它（見 `level3_turn_and_combat.md` 與 `pawn/service/movement.gd`）。

---

## 6. 完整資料流：玩家「看到藍格 → 點落點 → 走過去」

```mermaid
sequenceDiagram
    participant PS as TacticsPlayerService
    participant A as TacticsArenaService
    participant T as TacticsTile(×N)
    participant Sel as SelectionService
    participant Pw as TacticsPawn(movement)

    Note over PS: stage=2 show_available_movements
    PS->>A: process_surrounding_tiles(起點, movement, 友軍)
    A->>T: BFS 設 pf_root / pf_distance
    PS->>A: mark_reachable_tiles(起點, movement)
    A->>T: 依 pf_distance<=movement 設 reachable=true（變藍）
    Note over Sel: stage=3 玩家點選 reachable 格
    Sel->>A: get_pathfinding_tilestack(目標格)
    A->>T: 沿 pf_root 回溯 → Array[Vector3]
    Sel->>Pw: pawn.res.pathfinding_tilestack = 路徑; stage=4
    loop 每物理影格
        Pw->>Pw: move_along_path() pop_front 逐格前進
    end
```

---

## 7. 關鍵設計總結

- **無格座標系統**：完全用 3D 物理射線判定鄰接與佔據，因此天然支援不規則地形、高低差、斜坡，代價是每次都要打射線（效能取捨偏向開發便利）。
- **高度差即跳躍門檻**：`get_neighbors(height)` 的 `height` 參數把「能不能跨上下一格」交給 pawn 的 `jump`／`movement`。
- **BFS 全圖標記 + 事後距離過濾**：擴散不設上限，移動/攻擊範圍差異只體現在標色階段的 `distance`，因此同一份 BFS 結果可同時服務「移動」與「攻擊」兩種範圍。
- **路徑是世界座標陣列**：pawn 不認 tile 物件，只認 `Vector3` 串列，移動邏輯與地圖結構解耦。
