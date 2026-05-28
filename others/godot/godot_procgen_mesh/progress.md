# godot_procgen_mesh — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地。

## 一句話：這是什麼

3D Low Poly 程序生成 mesh 工具。聚焦 **mapcore C++ 已做之外**的部分：
建築（box extrusion + 屋頂）、共用幾何工具（flat normalize / noise displacement / face color jitter）、
MultiMesh 變體散佈 helper。

## 真相校準

**mapcore_godot 端 C++ 已實作**：

| 模組 | 位置 |
|------|------|
| `MapCoreProcGenMeshBuilder::generate_rock` | `others/gamecore/mapcore_godot/src/procgen_mesh_builder.cpp` |
| `::generate_tree_trunk` | 同上 |
| `::generate_tree_foliage` | 同上 |
| demo 端散佈整合 | `others/gamecore/mapcore_godot/demo/scenes/biome_scatter.gd`（已 commit、真機驗證） |

本檔**不重複實作**岩石/樹幹/樹冠（mapcore C++ 已是事實標準）。
聚焦 C++ 沒做、CONCEPT 待決事項點到的部分：

| CONCEPT 待決事項 | 處理 |
|-----------------|-----|
| 程序生成聚落/城市（box extrusion + 屋頂） | ✅ `ProcBuilding`（flat/gable/pyramid 三種屋頂） |
| MultiMesh 變體（4–8 種岩石預生成 + 散佈） | ✅ `MultiMeshVariants` 通用 helper |
| C++ noise 函式庫選型 | N/A（純 GDScript 端用 FastNoiseLite，C++ 端歸 mapcore_cpp_square 決定） |
| 生物部件（軀幹/四肢/頭/翅膀） | ⏸ 未做（與 character_3d「純 GDScript 程序人形」待辦對齊） |
| icosphere vs cube subdivision | ⏸ 未做（純 GDScript 後備版岩石未啟動） |

## 檔案清單

```
godot_procgen_mesh/
├── CONCEPT.md
├── gd/
│   ├── proc_geometry.gd        # 共用工具：flat_normalize / noise_displacement / face_color_jitter / build_mesh
│   ├── proc_building.gd        # 建築 box + 三種屋頂 + variants
│   └── multimesh_variants.gd   # 變體生成 + 隨機分桶 + MultiMeshInstance3D 一鍵
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| ProcGeometry.flat_normalize | 任意 mesh → per-face 獨立頂點 + face normal | ✅ 完成 |
| ProcGeometry.apply_noise_displacement | FastNoiseLite Simplex per-vertex | ✅ 完成 |
| ProcGeometry.apply_face_color_jitter | 規避工業感「面色調抖動」 | ✅ 完成 |
| ProcGeometry.build_mesh | verts/indices/normals/colors → ArrayMesh | ✅ 完成 |
| ProcBuilding 三種屋頂 | FLAT / GABLE / PYRAMID | ✅ 完成 |
| ProcBuilding.make_variants | base params + size_jitter → N 個 mesh | ✅ 完成 |
| MultiMeshVariants pipeline | make_variants / distribute / build_instances / scatter | ✅ 完成 |
| 純 GDScript 後備版岩石/樹 | mapcore C++ 已做，本檔不重複 | ✋ 跳過 |
| 生物部件 | 量大、與 character_3d 程序人形對齊 | ⏸ 待辦 |
| 真機驗證 | Godot 4 跑 building + 變體散佈 | ⏸ **待真機驗證** |

## 設計重點

### 1. ProcGeometry.flat_normalize 是 Low Poly 視覺核心
CONCEPT 與 godot_material_3d 都強調：flat shading 真正靠**每三角面三頂點獨立 + 面法線**，
不是 StandardMaterial3D 開關。本檔提供通用 helper：任何共享頂點 mesh 進來，
每個 face 拆成獨立頂點、算 cross product 求面法線、複製對應 vertex color。

副作用：頂點數膨脹成 `face_count × 3`。Low poly 因為面數少（建築幾十面、岩石十多面）所以無妨。

### 2. ProcBuilding 用「直接 push per-tri verts」而非 SurfaceTool
SurfaceTool 寫起來像 OpenGL immediate mode 較囉嗦。本檔直接 push `PackedVector3Array`
然後丟 flat_normalize 一次算完法線，邏輯更直白。

### 3. 三種屋頂的選擇邏輯
- **FLAT**：現代/沙漠平頂房屋，最簡（一個 quad）
- **GABLE**：山牆雙斜面 + 兩三角山牆，中世紀/歐風常見
- **PYRAMID**：四面金字塔屋頂，東方塔樓或防禦建築

CONCEPT 點到「文化/時代參數決定密度/風格」——這個 enum 可被聚落生成器（更上層）用文化參數
驅動（例如「中世紀文化 70% GABLE / 20% FLAT / 10% PYRAMID」）。

### 4. MultiMeshVariants 三段式
- `make_variants(generator, n)`：產 N 種變體 mesh（generator 可以是 ProcBuilding.generate
  或 MapCoreProcGenMeshBuilder.generate_rock 等任何 `(seed) -> Mesh`）
- `distribute(transforms, n)`：把 transforms 隨機分到 N 個桶
- `build_instances(variants, buckets)`：每桶建一個 MultiMeshInstance3D

或者 `scatter(generator, n, transforms)` 一行做完。

故意拆三段是因為**變體 mesh 可以重複利用**——一個城市裡多個區域用同一組 4 種建築 mesh，
只是 transforms 不同。重新跑 generator 浪費。

## 用法範例

### 散佈建築群（用 mapcore data 決定位置）
```gdscript
# 假設 city_cells: Array[Vector2i] 是城市格清單
var base := ProcBuilding.Params.new()
base.wall_color = Color(0.85, 0.78, 0.65)  # 沙岩色
base.roof_color = Color(0.55, 0.30, 0.20)
base.color_jitter = 0.08

var generator := func(seed: int) -> Mesh:
    var p := ProcBuilding.Params.new()
    p.width = randf_range(1.5, 3.0)
    p.depth = randf_range(2.0, 4.0)
    p.height = randf_range(2.0, 3.5)
    p.roof_type = randi_range(0, 2)
    p.wall_color = base.wall_color
    p.roof_color = base.roof_color
    p.color_jitter = base.color_jitter
    p.seed = seed
    return ProcBuilding.generate(p)

var transforms: Array[Transform3D] = []
for cell in city_cells:
    var pos := Vector3(cell.x + 0.5, 0, cell.y + 0.5)
    transforms.append(Transform3D(Basis.from_euler(Vector3(0, randf() * TAU, 0)), pos))

var mat := StandardMaterial3D.new()
mat.vertex_color_use_as_albedo = true
mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL  # 想看 flat 法線

var instances := MultiMeshVariants.scatter(generator, 6, transforms, mat)
for inst in instances:
    city_node.add_child(inst)
```

### 規避工業感工具鏈
```gdscript
# 自己生 mesh 後套兩件
var mesh := ProcGeometry.flat_normalize(my_raw_mesh)
mesh = ProcGeometry.apply_face_color_jitter(mesh, base_color, 0.05, seed)
```

## 與其他模組的關係

| 模組 | 角色 |
|------|------|
| mapcore C++ `MapCoreProcGenMeshBuilder` | 岩石/樹幹/樹冠的事實標準 |
| `godot_world_map_3d.BiomeScatterClimate` | climate-aware 散佈規則（透過 `compute()` 回傳 transforms） |
| **本檔 MultiMeshVariants** | 餵 BiomeScatterClimate 算出的 transforms 進 MultiMesh |
| `godot_material_3d` / mapcore demo MaterialLibrary | 散佈 instance 的 material_override 來源 |
| **本檔 ProcBuilding** | 城市/聚落格的建築 mesh 生成（mapcore C++ 沒做這塊） |

## 待決事項（從 CONCEPT.md 帶過來）

- [x] 程序生成聚落/城市：`ProcBuilding` + `MultiMeshVariants.scatter` 完成。
- [x] MultiMesh 預生成幾種變體（4–8 種）：`MultiMeshVariants.make_variants(n)` 完成。
- [ ] 純 GDScript 後備版岩石/樹幹/樹冠：mapcore C++ 已是事實標準，本檔不做。
      未來若有專案不想編 mapcore .so，可補後備版。
- [ ] 生物部件（軀幹/四肢/頭/翅膀）：與 `godot_character_3d` 「純 GDScript 程序人形」待辦對齊。
- [ ] icosphere vs cube subdivision：等真要做純 GDScript 岩石時再決。

## 下一步（按需）

1. **真機驗證**：Godot 4 跑 `ProcBuilding.generate()` 看三種屋頂，
   再跑 `MultiMeshVariants.scatter` 撒幾十棟建築看 GPU instancing 是否正確。
2. **與 godot_world_map_3d 整合**：定義 `TerrainID.CITY`（或 feature_id）→ 散佈建築規則，
   接 `BiomeScatterClimate` 同樣的 transform pipeline。
3. **生物部件 → character_3d 程序人形解鎖**：軀幹（橢球 + noise）/ cylinder 四肢 / 球頭，
   骨骼仍手寫 rest pose，作為「純 GDScript 可動人形」雛形。
