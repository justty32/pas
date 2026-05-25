# 教學 — 如何自訂一張戰棋地圖

> 目標：做出一張新的戰棋場地並讓它能被本範本「自動格子化」、可走訪、可載入遊玩。
> 路徑相對於 `projects/godot-tactical-rpg/`。

---

## 1. 前置知識

- 地圖如何變成可走訪格子：`architecture/level3_grid_pathfinding.md` 第 1、2 節（**必讀**）。
- 關卡/場地節點結構：`architecture/level1_overview.md` 第「場景節點概觀」與 `level2` 第 5 節。

核心觀念：**你只需要擺好一堆方塊 mesh，引擎執行時自動把它們轉成帶碰撞與腳本的格子**（`TacticsTileService.tiles_into_staticbodies`，`data/models/world/combat/arena/tile_service/service.gd:10`）。格子間的鄰接與高低差靠射線在執行期判定，不需要你手填座標。

官方另有圖文並茂的 Blender 製圖教學：`docs/tutorials/how-to-create-maps/README.md`（含 60+ 張截圖）。本篇聚焦「方塊 → 可玩關卡」的 Godot 端整合與驗收。

---

## 2. 地圖的硬性結構要求

一張可用的 arena 場景（參考 `assets/maps/level/arena/test_arena.tscn`）必須滿足：

```
Arena (Node3D, 掛 tactics_arena.gd)
├── (光源，可選，如 DirectionalLight3D)
└── Tiles (Node3D)              ← 名字必須叫 "Tiles"
    ├── Tile     (MeshInstance3D)   每個方塊一格
    ├── Tile001  (MeshInstance3D)
    └── ...                          （test_arena 約 200 格）
```

關鍵約束（來自轉換與走訪程式）：
- `Tiles` 節點名稱固定為 `"Tiles"`（`arena/service/service.gd:31,38` 寫死 `get_node("Tiles")`）。
- 每格是一個 **`MeshInstance3D`**，直接掛在 `Tiles` 下（轉換程式走訪 `Tiles` 的直接子節點，`tile_service/service.gd:21`）。
- 每格建議邊長 **1m**、格心對齊整數座標（pawn 用 `RayCast3D` 找腳下 tile、移動以格距 ~1 為基準）。
- **高低差即地形**：相鄰格的 Y 差會被 `get_neighbors(height)` 用來判斷能否跨越（高度差 > pawn 跳躍力就走不過去）。要做台階/障礙就拉高某些格的 Y。

> 不需要手動加 `CollisionShape3D`、不需要給格子掛腳本——`configure_tiles()` 會在關卡 `_ready` 時自動做完（`tactics_level.gd:39`）。

---

## 3. 實作步驟

### 路線 A：用 Blender 做（官方推薦，支援自動辨識）
1. 依 `docs/tutorials/how-to-create-maps/README.md`：在 Blender 用 1m 方塊拼出網格地形，每個可站立面是一個方塊。
2. 用 Godot Blender Exporter 匯出，或匯出 `.glb` 後在 Godot 匯入。
3. 在 Godot 中把匯入結果整理成上節的 `Arena → Tiles → Tile*` 結構（確保每格是 `Tiles` 下的 `MeshInstance3D`）。

### 路線 B：直接在 Godot 編輯器拼
1. 複製 `assets/maps/level/arena/test_arena.tscn` 成 `my_arena.tscn`。
2. 在 `Tiles` 下增刪 `MeshInstance3D`（用同一個 1m BoxMesh），擺出你的地形；要高低差就調 Y。
3. 確保根節點仍掛 `tactics_arena.gd`（`class_name TacticsArena`）。

### 步驟：包成一個關卡（level）
關卡（`assets/maps/level/test_level.tscn`，掛 `tactics_level.gd`）負責把 arena + 雙方 pawn 組起來：
1. 複製 `test_level.tscn` 成 `my_level.tscn`。
2. 把其中的 `TacticsArena` 子節點換成你的 `my_arena.tscn` instance。
3. 調整 `TacticsParticipant/TacticsPlayer` 與 `TacticsOpponent` 下各 pawn 的位置，讓它們站在你地圖的合法格子上方。
4. （可選）在 `TacticsLevel` 的 Inspector 調 `camera_boundary_radius`（`tactics_level.gd:11`）以配合地圖大小。

### 步驟：讓主選單能載入它
`data/main.gd::load_level`（`data/main.gd:36-41`）用固定路徑樣板載關卡：
```gdscript
var level_path = "res://assets/maps/level/%s_level.tscn" % level_name
```
- 最快：把你的關卡命名為 `<name>_level.tscn`（例 `my_level.tscn`），再改 `main.gd:23` 的 `load_level("test")` 為 `load_level("my")`。
- 或：複製 `LoadMap0` 按鈕 → 新增 `_on_load_map_1_pressed()` 呼叫 `load_level("my")`（`main.gd` 是 placeholder loader，作者明示可自由替換）。

---

## 4. 驗證方式

1. F5 執行 → 載入你的關卡。
2. **格子化成功**：滑鼠移過地形，格子應出現白色 hover 高亮（代表 mesh 已被轉成 `TacticsTile` 且 `_process` 在跑）。若完全無高亮，多半是 `Tiles` 命名錯或方塊不是 `Tiles` 的直接子節點。
3. **走訪正確**：選一隻 pawn 按 Move，藍色可達範圍應沿地形連通；被另一隻 pawn 佔住的格不該變藍（`is_taken()` 排除）。
4. **高低差**：在地圖中放一個比周圍高 1m 以上的格，確認移動力不足時走不上去；高度差在跳躍力內時 pawn 會播 JUMP 動畫跳上（`pawn/service/movement.gd:88-90`）。
5. **不會穿掉地板**：pawn 落下時應穩穩停在格上（若會穿過，注意這是歷史 bug，已由 `GRAVITY_STRENGTH=6` 修正，見 commit `0b88379`）。
6. 開 `DebugLog.visual_debug = true`（`data/models/config/debug.gd:10`）可看到滑鼠射線，協助診斷拾取問題。

---

## 5. 常見坑

| 症狀 | 原因 | 解法 |
|---|---|---|
| 格子無 hover、無法選 | `Tiles` 命名不符或 mesh 非其直接子節點 | 確認結構為 `Arena/Tiles/Tile*` |
| 鄰格之間走不通 | 相鄰格高度差過大或有縫隙 | 縮小高度差，或提高 pawn `movement/jump` |
| pawn 浮空/陷地 | mesh 高度與格心不一致 | 統一 1m 方塊、格心對齊整數座標 |
| 載入按鈕沒反應 | 關卡檔名不符 `%s_level.tscn` 樣板 | 改檔名或改 `main.gd` 的 `load_level` 參數 |
