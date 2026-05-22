# GDExtension：3D 大世界地圖（Low Poly Terrain Mesh）

## 目標

從 C++ mapcore 資料直接生成 `ArrayMesh`，在 Godot 場景渲染 Low Poly 3D 地形。
不使用 TileMap，不依賴任何外部 3D 素材。

---

## 核心架構

```
MapCoreGenerator（已有）
    → generate_async() → emit generation_completed(data)
MapCoreTerrainMeshBuilder（新增 C++ class）
    → generate_terrain_mesh(data, ...) → ArrayMesh
MapRenderer3D（新增 GDScript）
    → 接收 signal → 建立 TerrainMesh + WaterPlane
```

C++ 負責所有幾何計算，GDScript 只做節點組裝。

---

## 新增 C++ 類別：`MapCoreTerrainMeshBuilder`

### 原始碼位置

- Header: `mapcore_godot/src/terrain_mesh_builder.h`
- Impl:   `mapcore_godot/src/terrain_mesh_builder.cpp`
- 已在:   `mapcore_godot/src/register_types.cpp` 中 `GDREGISTER_CLASS`

### 類別設計

繼承 `RefCounted`（無需掛到場景樹，直接 `.new()` 使用）。

公開方法：

```gdscript
# 所有參數都有預設值，最簡可直接傳 data
var builder := MapCoreTerrainMeshBuilder.new()
var mesh: ArrayMesh = builder.generate_terrain_mesh(
    data,          # MapCoreMapData（必填）
    1.0,           # tile_size：每格世界單位大小（m）
    3.0,           # height_scale：heightmap 0~1 → 世界 Y 倍率
    0.05           # jitter_amp：頂點高度擾動幅度
)
```

### Flat Shading 原理

每個 quad（格子）生成 **兩個三角形，共 6 個獨立頂點**（不共享）。
因此每個三角面有自己的法線 → GPU 插值時每面都是純色 → Low Poly 視覺。

```
格子 (x, z) 的四個角：
  TL = (x,   Y_TL, z)      TR = (x+1, Y_TR, z)
  BL = (x,   Y_BL, z+1)    BR = (x+1, Y_BR, z+1)

三角形 1（TL, BL, TR）：法線 = (BL-TL).cross(TR-TL).normalized()
三角形 2（TR, BL, BR）：法線 = (BL-TR).cross(BR-TR).normalized()
```

### 頂點高度來源

使用 `data.get_height_array()`（連續 float 0~1）乘以 `height_scale`，
再疊加 deterministic jitter（基於座標 hash），避免過於整齊的格子感。

### 顏色映射

| 地形 | RGBA（linear） |
|------|---------------|
| OCEAN | (0.08, 0.25, 0.55) |
| COAST | (0.20, 0.45, 0.70) |
| PLAINS | (0.65, 0.70, 0.35) |
| GRASSLAND | (0.30, 0.60, 0.25) |
| DESERT | (0.80, 0.70, 0.38) |
| TUNDRA | (0.60, 0.65, 0.70) |
| SNOW | (0.85, 0.90, 0.95) |
| FOREST | (0.15, 0.40, 0.15) |
| HILL | (0.55, 0.48, 0.35) |
| MOUNTAIN | (0.60, 0.58, 0.55) |
| LAKE | (0.15, 0.40, 0.65) |

每個三角面另有 ±8% 明度抖動（`vary_color`），避免千篇一律。

### `PackedColorArray` 如何顯示

在 GDScript 端：

```gdscript
var mat := StandardMaterial3D.new()
mat.vertex_color_use_as_albedo = true
terrain_mesh_node.material_override = mat
```

`vertex_color_use_as_albedo = true` 讓 C++ 填入的 `PackedColorArray` 直接作為 albedo 顏色，
無需 texture，無需 UV。

---

## GDScript 渲染器：`MapRenderer3D`

原始碼：`mapcore_godot/demo/scenes/map_renderer_3d.gd`

### 預期場景結構

```
WorldMap3D (Node3D)
├── MapCoreGenerator             ← Inspector 掛到 generator 屬性
└── MapRenderer3D（此腳本）
    ├── TerrainMesh (MeshInstance3D)   ← terrain_mesh_node
    ├── WaterPlane  (MeshInstance3D)   ← water_plane_node
    └── BiomeLayer  (Node3D)           ← biome_layer（目前為佔位）
```

### 水面實作

水面用 Godot 內建 `PlaneMesh`（不需要 C++ 生成）：

```gdscript
var plane := PlaneMesh.new()
plane.size = Vector2(map_w, map_h)
water_plane_node.mesh = plane
water_plane_node.position = Vector3(map_w * 0.5, sea_level_y, map_h * 0.5)
```

`sea_level_y` 預設 `1.2 = 0.4 (sea_level) × 3.0 (height_scale)`，
需與 `MapCoreGenerator.sea_level` × `height_scale` 保持一致。

---

## 編譯

`SConstruct` 使用 `Glob("src/*.cpp")` 自動包含所有 `.cpp`，
新增 `terrain_mesh_builder.cpp` 無需修改 `SConstruct`。

```powershell
cd others\gamecore\mapcore_godot
scons platform=windows target=template_debug
```

---

## 使用流程

1. 場景中放置上述節點結構
2. Inspector 設定 `generator`, `terrain_mesh_node`, `water_plane_node`
3. 調整 `height_scale`（建議 2.0~5.0）、`jitter_amp`（建議 0.02~0.1）
4. 執行場景，`generate_async()` 完成後自動渲染

---

## 效能

64×48 地圖 = 3,023 quads = 18,138 頂點，生成極快（C++ 單次計算）。
更大地圖（256×256）= 約 390K 頂點，建議分 chunk 更新（未來擴展）。

---

## 待實作

- [ ] BiomeLayer：FOREST/MOUNTAIN 格子散佈 3D 物件（待 `godot_procgen_mesh` 完成）
- [ ] 河流 mesh：沿地形貼合的藍色帶狀 mesh（目前 `get_all_river_edges()` 已有資料）
- [ ] FOW（迷霧）overlay mesh：在地形上方疊加可見度遮罩
- [ ] Chunk 更新策略：大地圖只重生成修改的區塊

---

*記錄時間：2026-05-22*
*狀態：C++ TerrainMeshBuilder + GDScript MapRenderer3D 已實作*
