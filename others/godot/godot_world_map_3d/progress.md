# godot_world_map_3d — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的可拆出薄包裝。

## 一句話：這是什麼

**3D 世界地圖場景的可拆出範本**，吃 `MapCoreMapData` + 一張地形 ArrayMesh，
自動建好 `TerrainMesh + WaterPlane + BiomeLayer`，並在 GDScript 端把 climate
（temperature / rainfall）疊加到 mapcore 烘好的 vertex color 上做生態微調。

## 真相校準（重要）

**核心已在 `mapcore_godot` 端完成、已 commit、已真機驗證**：

| 模組 | 位置 |
|------|------|
| C++ flat shading terrain mesh | `others/gamecore/mapcore_godot/src/terrain_mesh_builder.cpp` |
| C++ procgen mesh（樹/岩石） | `others/gamecore/mapcore_godot/src/procgen_mesh_builder.cpp` |
| demo 場景（含互動） | `others/gamecore/mapcore_godot/demo/scenes/world_map_3d.tscn` |
| demo 端 .gd | `map_renderer_3d.gd` / `biome_scatter.gd` / `material_library.gd` |

**本目錄做什麼**：把 demo 端 .gd 抽成「**可拆出複用、不耦合 demo 場景結構**」的薄包裝，
並落實 memory 提到的「**純 GDScript 從 climate 推導生態**」最小解鎖路徑（demo 端
只依 terrain enum，這裡加上 temperature / rainfall）。

## 檔案清單

```
godot_world_map_3d/
├── gd/
│   ├── world_map_3d.gd            # WorldMap3D Node3D controller（外部 mount(data, mesh)）
│   ├── climate_palette.gd         # ClimatePalette：terrain 粗色 + climate 細色
│   └── biome_scatter_climate.gd   # BiomeScatterClimate：climate-aware 散佈規則
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| WorldMap3D controller | `mount()` / 自動建 children / clim重塗 / scatter 整合 | ✅ 完成 |
| ClimatePalette | base biome 色 + temp 偏色 + rain 飽和度 + mesh 重塗 | ✅ 完成 |
| BiomeScatterClimate | Rule struct + 4 條內建規則（forest/shrub/rocks/cactus）+ compute/build_multimesh | ✅ 完成 |
| 真機驗證 | 在 Godot 4 + mapcore_godot 編好 .so 的專案測試 | ⏸ **待真機驗證** |

## 設計重點

### 1. 「terrain 粗色 + climate 細色」分工
C++ `terrain_mesh_builder` 已烘好基底 vertex color（11 色），但同 enum 在赤道沙漠與
極地沙漠視覺扁平。`ClimatePalette.recolor_terrain_mesh()` 不重生 mesh，只就地重塗
ARRAY_COLOR：
- 溫度低於 5°C 偏冷藍、高於 20°C 偏暖黃（強度遞增）
- 降雨低於 400 mm 降飽和（乾涸感）、高於 1200 mm 提飽和（潮濕鮮綠）

`climate_strength = 0` 退回 demo 原色，`= 1` 完全套用——可漸進啟用，方便比對。

### 2. 散佈規則用 Callable predicate 而非寫死 enum
demo 端 `biome_scatter.gd` 寫死 `terrain == FOREST → 樹 / terrain == MOUNTAIN → 岩石`。
本檔的 `Rule.predicate` 是 `(terrain, temp, rain) -> density`，回傳「每格期望數量」。
四條內建規則：
- `rule_forest()`：FOREST 基礎密度 1.0，降雨 < 600mm 線性減密，溫度 < -5°C 或 > 30°C 邊緣帶減密
- `rule_shrub()`：GRASSLAND / PLAINS 降雨 200~800 mm 稀疏灌木
- `rule_rocks()`：MOUNTAIN 2.5 顆/格、HILL 0.3 顆/格
- `rule_cactus()`：DESERT + 溫度 > 10°C + 降雨 < 300mm

### 3. WorldMap3D 不持有 mesh 來源
`mount(data, terrain_mesh)` 第二參數由外部餵入。原因：
- mesh 可以來自 `MapCoreTerrainMeshBuilder.generate_terrain_mesh()`（C++）
- 也可以是純 GDScript 生成、或從 .glb 載入
- 解耦後本檔不依賴 mapcore 已編好的 .so

scatter 的 mesh 也是外部 `set_scatter_mesh("forest", tree_mesh)` 注入；
未注入的規則自動跳過，不會炸。

### 4. 為什麼不寫 .tscn 範本
`.tscn` 會綁住 `res://` 路徑，反而難以拆出複用。
`WorldMap3D` 是 `Node3D` 子類，外部 `var wm := WorldMap3D.new(); add_child(wm); wm.mount(...)`
就能工作；節點 children 自己建。需要在編輯器拖拉式擺場景時再自行 `WorldMap3D.tscn` 包一層。

## 用法範例

```gdscript
# 假設已有 mapcore_godot GDExtension 載入完成
var data: MapCoreMapData = generator.generate()  # 任何方式取得

var mesh_builder := MapCoreTerrainMeshBuilder.new()
var terrain_mesh := mesh_builder.generate_terrain_mesh(data, 1.0, 3.0, 0.05)

var wm := WorldMap3D.new()
wm.tile_size = 1.0
wm.height_scale = 3.0
wm.climate_strength = 0.7        # 比 demo 多這一條：climate 細色
add_child(wm)

# 注入 scatter mesh（用 mapcore 的 procgen 或自製）
var pg := MapCoreProcGenMeshBuilder.new()
wm.set_scatter_mesh("forest", _build_tree(pg))
wm.set_scatter_mesh("rocks", pg.generate_rock(0.55, 0.25, 42))
wm.set_scatter_mesh("cactus", _build_cactus(pg))

wm.mount(data, terrain_mesh)
```

## 待決事項（從 CONCEPT.md 帶過來）

- [ ] Hex vs Square：目前完全沿用 mapcore Square；切 Hex 要等 mapcore 端先支援。
- [ ] Terrain mesh 更新策略：整塊重生 vs 分塊 chunk —— 大地圖（>256×256）才會痛，目前不處理。
- [x] Delaunay 三角化取代 uniform grid：mapcore demo 已是 uniform grid，不開新路線。
- [ ] LOD：遠處低精度 mesh —— 與 chunk 策略一起做；先擱置。
- [ ] 河流：mapcore 已有 `get_all_river_edges()` 與 `draw_rivers()`（2D Image 端），3D 端
      需要做沿地形貼合的 curve mesh，**未做**。先列待辦。
- [ ] 迷霧系統（Fog of War）：mapcore 端可視性遮罩未實作；本檔只預留 BiomeLayer 上方可疊
      第二層 mesh / decal 的位置。

## 與既有重複內容的關係

`mapcore_godot/demo/scenes/material_library.gd` 與本月剛做的 `godot_material_3d/`
功能高度重疊（色票、tint、vertex_color、water、rim shader）。**目前並存**：

| 來源 | 角色 |
|------|------|
| `material_library.gd` | mapcore demo 內部 utility，含快取，綁定 demo 用 |
| `godot_material_3d/` | 通用 addon，給其他專案抽用 |
| 本檔（WorldMap3D） | 暫時不引用上述兩者，自己 new StandardMaterial3D（最少耦合） |

整合時機未到，暫不收斂。整合方向有兩個（看哪邊先被驅動）：
- 把 demo 的 `MaterialLibrary` 抽出搬到 `godot_material_3d/`，demo 改 import；
- 或把 `godot_material_3d/` 視為 demo 的「對外發布版」，demo 內部維持原樣。

## 下一步（按需）

1. **真機驗證**：找一個有 mapcore_godot 編好 .so 的 Godot 4 專案，把這三支 .gd 拖進去，
   照用法範例跑，確認 climate 重塗視覺有差、scatter 規則行為合理。
2. **河流 3D 渲染**：用 `data.get_all_river_edges()` 串出沿頂點高度的 curve mesh。
3. **material 整合方向決定**：見上節，等下一次有人改 demo 或啟用 godot_material_3d 時收斂。
