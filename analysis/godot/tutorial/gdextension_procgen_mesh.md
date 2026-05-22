# 程序生成低多邊形 3D 幾何：ProcGenMeshBuilder + BiomeScatter

## 目標

在 Low Poly 3D 策略遊戲中，用 C++ GDExtension 程序生成岩石、樹幹、樹冠的 ArrayMesh，
再由 GDScript BiomeScatter 透過 MultiMesh 散佈到地形上，保持 draw call 數量恆定。

---

## 核心設計

```
MapCoreProcGenMeshBuilder（C++ RefCounted）
  ├── generate_rock(radius, roughness, seed)  → ArrayMesh
  ├── generate_tree_trunk(height, radius, seed) → ArrayMesh
  └── generate_tree_foliage(radius, cone_count, seed) → ArrayMesh

BiomeScatter（GDScript Node3D）
  ├── scatter(MapCoreMapData) — 一次性呼叫，生成全場岩石 + 樹木
  ├── _scatter_rocks() — MOUNTAIN 格 → rocks_multi_node（MultiMesh）
  ├── _scatter_trees() — FOREST 格 → trees_multi_node（MultiMesh）
  └── _merge_meshes()  — 靜態輔助：合併 trunk + foliage 為單一 ArrayMesh
```

**設計原則**：C++ 生成幾何，GDScript 負責場景組裝與 MultiMesh 管理。

---

## 原始碼位置

- `mapcore_godot/src/procgen_mesh_builder.h`
- `mapcore_godot/src/procgen_mesh_builder.cpp`
- `mapcore_godot/demo/scenes/biome_scatter.gd`

---

## C++ 內部實作細節

### UV Sphere 骨架（岩石基礎）

岩石以 UV sphere 為基礎（4 個緯度環 × 6 個經度段），共 26 個共享頂點、48 個三角面：

```
北極（1）
緯度環 0：6 頂點（phi = π/5）
緯度環 1：6 頂點（phi = 2π/5）
緯度環 2：6 頂點（phi = 3π/5）
緯度環 3：6 頂點（phi = 4π/5）
南極（1）
```

計算公式（單位球，`lat` = 0~3）：
```
phi   = π * (lat+1) / (LAT+1)
y     = cos(phi)
r     = sin(phi)
x,z   = r * cos(theta), r * sin(theta)   // theta = 2π * lon / LON
```

### 頂點擾動（規避工業感的核心）

對每個頂點施加沿法線方向的 noise 位移：
```cpp
float n = hf3(idx * 997 + seed, ...) - 0.5f;  // -0.5 ~ +0.5
Vector3 displaced = v + v.normalized() * n * roughness;
```

接著施加非均勻縮放（各軸 0.6~1.4 倍）：
```cpp
float sx = 0.6f + hf(seed, 1) * 0.8f;   // X 軸縮放
float sy = 0.6f + hf(seed+1, 2) * 0.8f; // Y 軸縮放
float sz = 0.6f + hf(seed+2, 3) * 0.8f; // Z 軸縮放
displaced = Vector3(d.x * sx, d.y * sy, d.z * sz) * base_radius;
```

相同 `seed` 永遠產生相同 mesh（確定性 hash），便於 LOD 快取。

### Flat Shading：非共享頂點

每個三角面用獨立的 3 個頂點（不共享），法線從截面計算：
```cpp
Vector3 n = (b - a).cross(c - a).normalized();
// a, b, c 三頂點都填相同 n → GPU 插值後面色均勻 → flat look
```

### 面色抖動（±12% 亮度）

```cpp
Color rb{0.55f, 0.50f, 0.45f, 1.0f};  // 岩石灰棕基礎色
float s = 0.88f + hf(fi + seed*13, fi*7 + seed) * 0.24f;
Color face_color = {rb.r * s, rb.g * s, rb.b * s, 1.0f};
```

每個面（`fi`）得到略有差異的明度，視覺上有石頭稜角感。

### 樹幹：六稜柱

6 個邊面（每面 2 個三角形），頂端半徑略小：
```cpp
float top_r = radius * (0.40f + hf(seed, 42) * 0.30f);  // 0.40~0.70 倍
```

頂緣各頂點加小量 Y 擾動，避免整齊切口：
```cpp
float jyi = (hf(seed + i*3, i*7 + 1) - 0.5f) * height * 0.06f;
```

### 樹冠：多錐形叢集

`cone_count` 個（建議 2~4）互相重疊的五稜錐：
```cpp
float ox, oz = 隨機 XZ 偏移（± radius * 0.40）
float r      = radius * 0.55 ~ 1.45   // 各錐半徑略有差異
float h      = r * 0.90 ~ 1.50        // 高度比例
float by     = ci / cone_count * radius * 0.35  // 越後面的錐起點越高
```

---

## GDScript 使用範例

### 直接生成單個物件

```gdscript
const RIM_SHADER := preload("res://scenes/shaders/rim_glow.gdshader")

func place_rock(parent: Node3D, pos: Vector3) -> void:
    var builder := MapCoreProcGenMeshBuilder.new()
    var rock := MeshInstance3D.new()
    rock.mesh = builder.generate_rock(
        randf_range(0.3, 1.2),  # base_radius
        randf_range(0.1, 0.4),  # roughness
        randi()                  # seed
    )
    rock.material_override = MaterialLibrary.make_vertex_color()
    rock.position = pos
    rock.rotation.y = randf() * TAU
    parent.add_child(rock)
```

### 生成並組合樹木

```gdscript
func place_tree(parent: Node3D, pos: Vector3, seed: int) -> void:
    var builder := MapCoreProcGenMeshBuilder.new()
    var trunk_h := randf_range(0.8, 1.6)

    # 樹幹
    var trunk := MeshInstance3D.new()
    trunk.mesh = builder.generate_tree_trunk(trunk_h, 0.07, seed)
    trunk.material_override = MaterialLibrary.make_vertex_color()
    trunk.position = pos
    parent.add_child(trunk)

    # 樹冠（放在樹幹頂端）
    var foliage := MeshInstance3D.new()
    foliage.mesh = builder.generate_tree_foliage(
        randf_range(0.4, 0.8),  # radius
        randi_range(2, 4),       # cone_count
        seed + 1000
    )
    foliage.material_override = MaterialLibrary.make_vertex_color()
    foliage.position = pos + Vector3(0, trunk_h * 0.85, 0)
    parent.add_child(foliage)
```

---

## BiomeScatter 場景設置

### 場景結構（.tscn）

```
WorldMap3D (Node3D)
├── MapCoreGenerator
├── MapRenderer3D
│   ├── TerrainMesh (MeshInstance3D)
│   ├── WaterPlane (MeshInstance3D)
│   └── BiomeScatter  ← 掛 biome_scatter.gd
│       ├── RocksMultiMesh (MultiMeshInstance3D)  ← rocks_multi_node
│       └── TreesMultiMesh (MultiMeshInstance3D)  ← trees_multi_node
└── CameraRig
```

### Inspector 設定

| 屬性 | 說明 | 建議值 |
|------|------|--------|
| `rocks_multi_node` | 岩石 MultiMeshInstance3D | 指向場景中節點 |
| `trees_multi_node` | 樹木 MultiMeshInstance3D | 指向場景中節點 |
| `rock_radius` | 代表性岩石半徑 | 0.55 |
| `rock_roughness` | 岩石粗糙度 | 0.25 |
| `rock_per_cell` | MOUNTAIN 格最多幾顆 | 3 |
| `tree_cone_count` | 樹冠錐形數 | 3 |
| `tile_size` | 需與 MapRenderer3D 一致 | 1.0 |
| `height_scale` | 需與 MapRenderer3D 一致 | 3.0 |

### 觸發散佈

`MapRenderer3D` 在 `_on_generated` 中自動呼叫：
```gdscript
# map_renderer_3d.gd（已整合）
func _on_generated(data: MapCoreMapData) -> void:
    _build_terrain(data)
    _build_water(data)
    _populate_biomes(data)   # ← 呼叫 biome_scatter.scatter(data)
```

---

## MultiMesh 效能模型

```
一個 MultiMeshInstance3D = 1 draw call（不論 instance 數量）
                                        ↓
1000 棵樹 = 1 draw call（vs. 1000 MeshInstance3D = 1000 draw calls）
```

每個 instance 透過 `Transform3D`（含旋轉 + 縮放）提供視覺多樣性：
- **岩石**：均勻縮放 0.45x~1.55x + 隨機 Y 旋轉
- **樹木**：均勻縮放 0.65x~1.35x + 隨機 Y 旋轉

---

## 視覺多樣性技法

| 技法 | 實作位置 | 效果 |
|------|---------|------|
| 頂點 noise 位移 | `generate_rock()` C++ | 每顆石頭形狀不同 |
| 非均勻縮放 | `generate_rock()` C++ | 打破球形對稱 |
| 面色明度抖動 | 所有生成函式 C++ | 石頭/樹皮有稜角感 |
| instance 縮放變化 | `biome_scatter.gd` | 大小岩石夾雜 |
| instance 隨機旋轉 | `biome_scatter.gd` | 不規則朝向 |
| 樹幹頂緣 Y 擾動 | `generate_tree_trunk()` C++ | 頂緣不整齊 |
| 多錐形重疊樹冠 | `generate_tree_foliage()` C++ | 自然豐滿感 |

---

## 與 MapRenderer3D 整合

更新後的場景流程：
```
MapCoreGenerator.generate_async()
    ↓ generation_completed
MapRenderer3D._on_generated(data)
    ├── _build_terrain(data)   → TerrainMesh（C++ mesh + vertex color material）
    ├── _build_water(data)     → WaterPlane（PlaneMesh + water material）
    └── _populate_biomes(data) → BiomeScatter.scatter(data)
            ├── 掃描 MOUNTAIN 格 → 岩石 MultiMesh（約 0~3 顆/格）
            └── 掃描 FOREST 格  → 樹木 MultiMesh（1 棵/格）
```

---

## 已知限制

- MultiMesh 所有 instance 共享同一個 mesh，視覺多樣性靠縮放+旋轉
- 若需要多種 mesh 變體（如 3 種形狀的岩石），需要 3 個獨立 `MultiMeshInstance3D`
- 樹木正規縮放（`Basis.scaled`）會使法線在非均勻縮放下輕微失真；低多邊形風格中視覺上可接受

---

*記錄時間：2026-05-22*
*狀態：MapCoreProcGenMeshBuilder（C++）+ BiomeScatter（GDScript）已實作；MapRenderer3D 已整合*
