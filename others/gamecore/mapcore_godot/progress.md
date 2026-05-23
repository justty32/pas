# mapcore_godot 進度

> 最後更新：2026-05-23。此檔是「明天接手用」的進度快照。

## 一句話現況

mapcore_godot 已是可運行的雛形：同一份 C++ 生成的地圖資料，有 **2D** 與 **3D** 兩個 Godot 前端，**兩者互動功能已對等**（懸停/選格/feature 高亮/單位選取+成本感知尋路逐格走/路徑預覽/標籤），皆已實機驗證並 commit。

## 範圍約定（重要）

- mapcore 系列**只有 `mapcore_godot` 是活線**；`mapcore_py` / `mapcore_cpp` / `mapcore_*_square` 全部忽略、不開發。
- 但 `mapcore_cpp_square/` 是 mapcore_godot 的**建置依賴**（`SConstruct` 引用其 `src/` 與 `include/`），**不可刪、也不主動改**它的程式碼。需要調整生成/演算法行為時，改在 mapcore_godot 這端（橋接層或渲染器）。

## 已完成（本階段 commit 序）

| commit | 內容 |
| --- | --- |
| `22875bc` | 首次建置打通 + 可運行的 2D 世界地圖 demo |
| `2ef9372` | 2D 互動層（懸停/選取/feature 輪廓/標籤） |
| `7c9906e` | 成本感知尋路 + 世界地圖單位移動 |
| `ab82366` | 可運行的 3D 低多邊形世界地圖場景 |
| (本次)   | 3D 互動層：射線點選 + 懸停/選格/feature 輪廓/單位移動/路徑預覽/標籤（對齊 2D） |

### 2D：`demo/scenes/world_map_2d.tscn`（目前的 main scene）
- 腳本：`world_map_2d.gd` + `map_overlay_2d.gd`（互動視覺層）
- 互動：滑鼠懸停即時資訊、左鍵選格+feature 邊界輪廓高亮、Shift+左鍵路徑預覽（顯示步數/成本）、L 切換標籤、右鍵清除、中鍵拖曳/滾輪平移縮放
- 單位：生成時隨機放 3 個單位，左鍵選單位→點格下移動令，成本感知 `find_path` 規劃、`_process` 每 0.12s 逐格走
- 可調 `@export`：`river_min_strength`(80)、`river_crossing_cost`(0.05)、`label_min_size`(40)、`label_max_count`(24)

### 3D：`demo/scenes/world_map_3d.tscn`（**目前的 main scene**，F5 執行）
- 渲染腳本：`map_renderer_3d.gd` / `biome_scatter.gd` / `camera_rig_3d.gd` / `material_library.gd`
- 互動腳本：`world_map_3d_interaction.gd`（掛在 `Interaction` 節點）
- 內容：低多邊形地形 mesh（C++ `MapCoreTerrainMeshBuilder`）+ 半透明水面 + 山上岩石/森林樹木（`MapCoreProcGenMeshBuilder` + MultiMesh）+ 策略相機
- 相機操作：WASD/方向鍵平移、Q/E 旋轉、R/F 仰角、滾輪或 =/- 縮放、中鍵拖曳平移、右鍵拖曳旋轉
- **互動（已對齊 2D）**：
  - 點選機制＝地形 mesh 加 `create_trimesh_shape()` 碰撞 + 相機射線；命中點 `round(world/tile_size)` 換回格子
  - 懸停黃框 + 資訊面板、左鍵選格(青框)+feature 3D 邊界輪廓、左鍵選單位(白圓盤)→點格下移動令(逐格走、剩餘路線浮空線)
  - Shift+左鍵 路徑預覽(綠/紅圓盤+白線+步數/成本)、`L` 切換 billboard 標籤、`C`/`Esc` 清除（右鍵留給相機旋轉故改鍵盤）
- **3D 互動的踩坑**：地形三角面正面朝下（見下「踩過的坑」#4），俯視射線會打到背面 → `ConcavePolygonShape3D.backface_collision = true` 讓射線不分正反都命中

## 建置 / 執行

- GDExtension C++ 已編出 `demo/bin/libmapcore_godot.linux.template_debug.x86_64.so`（已 gitignore，不入版控）。
- 重編（**改 C++ 後才需要**）：
  ```
  cd others/gamecore/mapcore_godot
  /tmp/sconsenv/bin/scons platform=linux target=template_debug -j$(nproc)
  ```
  - `godot-cpp` 是 submodule（commit a7770ef），已 init 在 `mapcore_godot/godot-cpp`。
  - `scons` 裝在 venv `/tmp/sconsenv`（**/tmp 可能重開機後消失**，屆時需 `python3 -m venv /tmp/sconsenv && /tmp/sconsenv/bin/pip install scons`）。
- 在 Godot 開啟 `demo/`：main scene 已設為 3D，直接 F5 跑 3D；2D 開 `world_map_2d.tscn` 按 F6。
- **踩過的坑（避免重蹈）**：
  1. `.tscn` 裏 exported 的「節點參照」屬性必須在 `[node]` 表頭宣告 `node_paths=PackedStringArray(...)`，否則載入後為 Nil。
  2. 改了 C++ 重編 `.so` 後，**Godot 要重啟**才會重載 GDExtension（純 GDScript 改動只需重跑）。
  3. godot-cpp 預設 `-fno-exceptions`，但 square 核心用 throw → `SConstruct` 已加 `disable_exceptions=no`。
  4. C++ 自建的地形 ArrayMesh 三角面繞序使正面朝下 → 地形材質設為雙面（CULL_DISABLED）避免俯視看穿。

## 下一步（待辦，未動工）

- **3D 互動視覺打磨**（功能已完成，可選優化）：3D 線寬只有 1px（Godot 限制），路徑/輪廓在遠距偏細，要更醒目可改用 ribbon/管狀 mesh 或 MultiMesh 點陣；高亮方塊在陡坡會與地形交穿，可改貼地 Decal。
- **真正的「回合」概念**：單位每回合移動點數上限（非無限走）、回合推進。
- **單位間互動**：佔據/相遇/阻擋。
- 把 `river_crossing_cost`／地形成本接到 UI 即時調參看路徑變化。

## 複合式地圖：現役 3D map 表現力分析（2026-05-23）

> 背景：使用者的目標地圖模型是**複合式（多層疊加）**——一格＝基底材質＋地形起伏＋生態圈，例如「沙漠基底＋丘陵地形＋樹林生態圈」可同格並存（對應 `plans/008` 世界圖層資料集；非當前要動的工作，為未來方向）。

**結論：渲染架構「已經是分層的」，瓶頸只在資料驅動方式，不在渲染能力。** 現役 3D map 有三個互不干擾、可同畫面共存的通道：

| 複合層 | 對應 3D 渲染通道 | 現在誰驅動 | 已獨立？ |
| --- | --- | --- | --- |
| 地形起伏（丘陵）| 地形 mesh 頂點 Y（高度浮雕）| `height_array`，**與 enum 無關** | ✅ 真正獨立 |
| 基底材質（沙漠）| 地形頂點色 `terrain_to_color()`（terrain_mesh_builder.cpp）| 單一 `terrain` enum | ❌ 綁死 enum |
| 生態圈（樹林）| 樹/石 MultiMesh 疊在地表（biome_scatter.gd）| 單一 `terrain` enum | ⚠️ 疊加層本身獨立，但放置條件綁 enum |

- 畫面上本就是三明治：拉高的 mesh（起伏）＋表面著色（材質）＋疊上的植被/岩石（生態）→「沙漠丘陵上長樹林」**渲染上百分百表現得出來**。
- **但現狀畫不出那個組合**：`biome_scatter.gd:103` 撒樹條件是 `terrain==TERRAIN_FOREST`，沙漠格（`==DESERT`）永遠不撒樹；頂點色也由同一 enum 決定。單一 enum 同時驅動材質與生態兩通道，逼人二選一。

**最小解鎖（純 GDScript，不改 C++、不破壞 enum 流程）**：把這兩個通道的「驅動來源」從 enum 抽換為獨立判斷，並用既有 climate 即時推導當佔位資料——
- substrate ≈ f(降水, 溫度)（`get_rainfall`/`get_temperature`，低降水高溫→沙漠色）
- ecology ≈ g(降水, 溫度, 高度)（中等降水→可長樹，無關 base 是否沙漠）
- landform 已是高度，免費

即可在 Godot 端讓三層獨立、當場驗證跨層組合觀感。正式化才需在生成端輸出真多通道（會碰到凍結的 `mapcore_cpp_square` 核心，需與「不主動改 square」約定權衡）；完整版則由 `plans/008` 環節三「生態系形成」隨時間演化生態層，而非生成時定死。另有純渲染解法：頂點色是 RGBA，可一格同時編碼多層（base 色＋第二層植被覆蓋用 detail 貼花/半透明 ground-cover）。

## 關鍵檔案

- C++ 橋接：`src/map_data.{h,cpp}`（含 `find_path` / `path_cost`）、`map_generator.*`、`world_map_2d_renderer.*`、`terrain_mesh_builder.*`、`procgen_mesh_builder.*`、`register_types.cpp`
- 2D：`demo/scenes/world_map_2d.gd`、`map_overlay_2d.gd`、`world_map_2d.tscn`
- 3D：`map_renderer_3d.gd`（建地形+發 `terrain_ready` 訊號）、`world_map_3d_interaction.gd`（互動層全部邏輯）、`biome_scatter.gd`、`camera_rig_3d.gd`、`material_library.gd`、`world_map_3d.tscn`
- 建置：`SConstruct`、`demo/project.godot`（含 InputMap）、`demo/bin/mapcore_godot.gdextension`
