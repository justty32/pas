# mapcore_godot 進度

> 最後更新：2026-05-23。此檔是「明天接手用」的進度快照。

## 一句話現況

mapcore_godot 已是可運行的雛形：同一份 C++ 生成的地圖資料，有 **2D**（完整互動）與 **3D**（渲染+導覽）兩個 Godot 前端，皆已實機驗證並 commit。

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

### 2D：`demo/scenes/world_map_2d.tscn`（目前的 main scene）
- 腳本：`world_map_2d.gd` + `map_overlay_2d.gd`（互動視覺層）
- 互動：滑鼠懸停即時資訊、左鍵選格+feature 邊界輪廓高亮、Shift+左鍵路徑預覽（顯示步數/成本）、L 切換標籤、右鍵清除、中鍵拖曳/滾輪平移縮放
- 單位：生成時隨機放 3 個單位，左鍵選單位→點格下移動令，成本感知 `find_path` 規劃、`_process` 每 0.12s 逐格走
- 可調 `@export`：`river_min_strength`(80)、`river_crossing_cost`(0.05)、`label_min_size`(40)、`label_max_count`(24)

### 3D：`demo/scenes/world_map_3d.tscn`（用 F6 執行；main scene 仍是 2D）
- 腳本：`map_renderer_3d.gd` / `biome_scatter.gd` / `camera_rig_3d.gd` / `material_library.gd`
- 內容：低多邊形地形 mesh（C++ `MapCoreTerrainMeshBuilder`）+ 半透明水面 + 山上岩石/森林樹木（`MapCoreProcGenMeshBuilder` + MultiMesh）+ 策略相機
- 相機操作：WASD/方向鍵平移、Q/E 旋轉、R/F 仰角、滾輪或 =/- 縮放、中鍵拖曳平移、右鍵拖曳旋轉
- 目前只有渲染+導覽，**還沒有互動**

## 建置 / 執行

- GDExtension C++ 已編出 `demo/bin/libmapcore_godot.linux.template_debug.x86_64.so`（已 gitignore，不入版控）。
- 重編（**改 C++ 後才需要**）：
  ```
  cd others/gamecore/mapcore_godot
  /tmp/sconsenv/bin/scons platform=linux target=template_debug -j$(nproc)
  ```
  - `godot-cpp` 是 submodule（commit a7770ef），已 init 在 `mapcore_godot/godot-cpp`。
  - `scons` 裝在 venv `/tmp/sconsenv`（**/tmp 可能重開機後消失**，屆時需 `python3 -m venv /tmp/sconsenv && /tmp/sconsenv/bin/pip install scons`）。
- 在 Godot 開啟 `demo/`：2D 直接 F5、3D 開 `world_map_3d.tscn` 按 F6。
- **踩過的坑（避免重蹈）**：
  1. `.tscn` 裏 exported 的「節點參照」屬性必須在 `[node]` 表頭宣告 `node_paths=PackedStringArray(...)`，否則載入後為 Nil。
  2. 改了 C++ 重編 `.so` 後，**Godot 要重啟**才會重載 GDExtension（純 GDScript 改動只需重跑）。
  3. godot-cpp 預設 `-fno-exceptions`，但 square 核心用 throw → `SConstruct` 已加 `disable_exceptions=no`。
  4. C++ 自建的地形 ArrayMesh 三角面繞序使正面朝下 → 地形材質設為雙面（CULL_DISABLED）避免俯視看穿。

## 下一步（待辦，未動工）

- **3D 互動**：把 2D 的互動搬到 3D —— 從相機射線點選地形格子（地形 mesh 目前無 collision，需加 StaticBody/CollisionShape 或用數學投影）、3D 單位標記與逐格移動、路徑用 3D 線條（如 ImmediateMesh / 多段 mesh）呈現。`selection_manager.gd` + `selection_outline.gdshader` 是當初為此預留的素材。
- **真正的「回合」概念**：單位每回合移動點數上限（非無限走）、回合推進。
- **單位間互動**：佔據/相遇/阻擋。
- 把 `river_crossing_cost`／地形成本接到 UI 即時調參看路徑變化。

## 關鍵檔案

- C++ 橋接：`src/map_data.{h,cpp}`（含 `find_path` / `path_cost`）、`map_generator.*`、`world_map_2d_renderer.*`、`terrain_mesh_builder.*`、`procgen_mesh_builder.*`、`register_types.cpp`
- 2D：`demo/scenes/world_map_2d.gd`、`map_overlay_2d.gd`、`world_map_2d.tscn`
- 3D：`demo/scenes/world_map_3d.gd`(無，主腳本為 map_renderer_3d.gd)、`map_renderer_3d.gd`、`biome_scatter.gd`、`camera_rig_3d.gd`、`material_library.gd`、`world_map_3d.tscn`
- 建置：`SConstruct`、`demo/project.godot`（含 InputMap）、`demo/bin/mapcore_godot.gdextension`
