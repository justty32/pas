# 3D 程序生成幾何（Low Poly Mesh）

## 對應 2D 版本

2D 版本（`../godot_procgen_art/`）在 C++ 中逐像素生成 `Image`，再轉為 `ImageTexture`。
3D 版本在 C++ 中逐頂點生成 `ArrayMesh`，直接掛在 `MeshInstance3D` 上。

概念完全平行：**GDExtension 負責生成幾何資料，Godot 只負責顯示。**

---

## 生成管線層次

```
Level 1（基礎）：程序生成基礎幾何（球、柱、盒 + 頂點擾動）
Level 2（中階）：noise displacement + 不規則細分 → 岩石、地形
Level 3（物件組合）：多個基礎幾何拼裝 → 樹木、建築、生物
Level 4（遠期）：L-system / 文法規則驅動複雜植被、城市
```

---

## ArrayMesh 生成（C++ GDExtension）

```cpp
Ref<ArrayMesh> build_mesh(PackedVector3Array verts,
                           PackedVector3Array normals,
                           PackedColorArray   colors,
                           PackedInt32Array   indices) {
    Array arrays;
    arrays.resize(Mesh::ARRAY_MAX);
    arrays[Mesh::ARRAY_VERTEX] = verts;
    arrays[Mesh::ARRAY_NORMAL] = normals;   // 可省略，靠 flat shading
    arrays[Mesh::ARRAY_COLOR]  = colors;
    arrays[Mesh::ARRAY_INDEX]  = indices;

    Ref<ArrayMesh> mesh;
    mesh.instantiate();
    mesh->add_surface_from_arrays(Mesh::PRIMITIVE_TRIANGLES, arrays);
    return mesh;
}
```

GDScript 側：
```gdscript
var mesh: ArrayMesh = ProcGenMesh.generate_rock(RockParams.new())
rock_instance.mesh = mesh
```

---

## 規避工業感的核心技法

程序生成最大問題是千篇一律。技法分兩類：

### 形狀層次的變異

| 技法 | 說明 | 適用 |
|------|------|------|
| **頂點 jitter** | 每個頂點加小範圍 uniform 隨機偏移 | 所有物件 |
| **Noise displacement** | 用 Perlin/Simplex noise 取代純隨機，擾動更連續 | 岩石、地形 |
| **非均勻縮放** | X/Y/Z 各自獨立隨機縮放（0.7x–1.3x），打破球形對稱 | 岩石、樹冠 |
| **隨機旋轉** | 擺放時全角度隨機，不要默認朝同方向 | 所有物件 |
| **少量極端個體** | 偶爾出現特別大或特別高的，打破均勻感 | 岩石群、樹林 |
| **非對稱** | 對本應對稱的形狀加 slight offset | 樹冠、生物 |

### 顏色層次的變異

| 技法 | 說明 |
|------|------|
| **面色調抖動** | 每個三角面的頂點色在基礎色上 ±5% 明度 |
| **高度漸層** | 底部深色，頂部亮色（岩石底部陰暗，頂部受光） |
| **Biome tint** | 乘以生態圈顏色（沙漠 → 偏黃，雪地 → 偏藍白） |

---

## 各類物件生成思路

### 岩石

```cpp
Ref<ArrayMesh> generate_rock(float base_radius, float roughness, int seed) {
    // 1. 從 icosphere 或 subdivided cube 開始（8–20 面）
    // 2. 每個頂點：pos += noise3D(pos * freq) * roughness * base_radius
    // 3. 非均勻縮放：scale = Vector3(rx, ry, rz)，各自 randf_range(0.6, 1.4)
    // 4. 每面頂點色 = base_rock_color * randf_range(0.85, 1.05)
}
```

### 樹木

```cpp
// 分兩部件生成，各自獨立
Ref<ArrayMesh> generate_tree_trunk(float height, float radius, int seed);
Ref<ArrayMesh> generate_tree_foliage(float radius, int cone_count, int seed);

// GDScript 組合：
// trunk MeshInstance3D + foliage MeshInstance3D (稍微偏移中心)
```

樹冠 = 2–4 個互相重疊的錐形或球體，位置隨機偏移，尺寸略有差異。

### 建築（Low Poly 策略風格）

```
基礎：box extrusion
  └── 房屋主體（拉伸的矩形 prism）
  └── 屋頂（三角 prism 或 pyramid）
  └── 窗口（面內縮，vertex offset）
  └── 門（類似窗口）
```

程序參數：寬 / 深 / 高 / 樓層數 / 屋頂類型 → 產生大量不重複建築。

### 生物部件（對應 2D 的程序生物系統）

| 部件 | 3D 生成方式 |
|------|------------|
| 軀幹 | 拉伸橢球 + noise 擾動 |
| 四肢 | Cylinder（漸細）+ 隨機彎曲角度 |
| 頭部 | 球體 + 頂點擾動 |
| 翅膀 | 扁平 mesh，Bezier 輪廓 + 內部幾何細分 |
| 眼睛 | 凸起的半球 mesh，頂部顏色不同 |

部件各自生成，由 GDScript 組合掛在 BoneAttachment3D 上（見 `../godot_character_3d/`）。

---

## 地形物件散佈

```gdscript
# 依 mapcore 資料在地形上散佈物件
func scatter_objects(terrain_data: MapData) -> void:
    for cell in terrain_data.get_cells():
        match cell.terrain:
            TERRAIN_FOREST:
                _place_tree(cell)
            TERRAIN_MOUNTAIN:
                _place_rocks(cell, count=randi_range(2, 5))
            TERRAIN_DESERT:
                _place_cactus_or_dune(cell)

func _place_rocks(cell: TileData, count: int) -> void:
    for i in count:
        var rock_mesh = ProcGenMesh.generate_rock(
            randf_range(0.3, 1.2),   # base_radius
            randf_range(0.1, 0.4),   # roughness
            randi()                   # seed
        )
        var inst = MeshInstance3D.new()
        inst.mesh = rock_mesh
        inst.position = Vector3(
            cell.x + randf_range(-0.4, 0.4),
            cell.hilliness * HEIGHT_SCALE,
            cell.z + randf_range(-0.4, 0.4)
        )
        inst.rotation.y = randf() * TAU
        biome_layer.add_child(inst)
```

---

## 效能考量

大量散佈物件（樹、岩石）應用 **MultiMesh**：

```gdscript
# 同類物件（相同 mesh）用 MultiMesh，GPU instancing
var mm = MultiMesh.new()
mm.mesh = tree_mesh
mm.instance_count = tree_positions.size()
for i in tree_positions.size():
    mm.set_instance_transform(i, Transform3D(...))
multi_mesh_instance.multimesh = mm
```

不同 mesh 變體（不同大小的岩石）預先生成 N 種 mesh，散佈時隨機選一種套 MultiMesh。

---

## 待決定

- [ ] C++ noise 函式庫選型（`stb_perlin.h` / FastNoiseLite / 自實作）
- [ ] icosphere 起始幾何 or 從 cube subdivision 開始（影響 noise 均勻性）
- [ ] 生物骨骼：程序生成 mesh 但骨骼仍用模板，還是也程序生成骨骼
- [ ] MultiMesh 的 mesh 種數：預生成幾種變體合適（岩石 4–8 種夠用？）
- [ ] 程序生成聚落/城市：在世界地圖格子上程序排列建築 mesh（box extrusion + 屋頂類型），以格子為單位，密度/風格由文化/時代參數決定

---

*記錄時間：2026-05-22*
*狀態：概念階段，對應 2D 版本 `../godot_procgen_art/`*
