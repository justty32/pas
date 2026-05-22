# 3D 大世界地圖（Low Poly Terrain）

## 對應 2D 版本

2D 版本（`../godot_world_map/`）需要多層 TileMapLayer + shader 混合來表現地形層次。
3D 版本直接用幾何高度 + 材質取代，更直覺，表現力更強。

---

## 架構概念

```
GDScript（Godot 場景）
│
├── TerrainMesh (MeshInstance3D)    ← mapcore 資料 → ArrayMesh
├── WaterPlane  (MeshInstance3D)    ← 固定 Y 高度的透明平面
├── BiomeLayer  (Node3D)            ← 散佈的樹木、岩石等 3D 物件
└── MapCamera   (Camera3D)          ← 俯視視角（可縮放旋轉）
```

---

## mapcore 資料 → 3D 地形對應

| mapcore 輸出 | 2D 用途 | 3D 用途 |
|-------------|--------|--------|
| `terrain` (int) | TileMap tile 類型 | vertex color / material index |
| `hilliness` (float) | shader 疊加層 | **vertex Y 高度** |
| `water_depth` (float) | shader | 水面 plane 是否覆蓋 |
| river 邊列表 | Polyline2D | 3D curve mesh（沿地形貼合） |
| feature_id | tile 特殊圖示 | 觸發 BiomeLayer 放置物件 |

C++ 核心不變，僅 GDExtension 橋接層改為輸出 ArrayMesh。

---

## Terrain Mesh 生成（C++ GDExtension）

```cpp
Ref<ArrayMesh> generate_terrain_mesh(const MapData& data,
                                      float tile_size,
                                      float height_scale,
                                      float jitter_amp) {
    PackedVector3Array verts;
    PackedColorArray   colors;
    PackedInt32Array   indices;

    for (int z = 0; z < data.height; z++) {
        for (int x = 0; x < data.width; x++) {
            const Tile& t = data.tile_at(x, z);
            float y = t.hilliness * height_scale;
            y += rng.randf_range(-jitter_amp, jitter_amp);  // 有機感

            verts.push_back(Vector3(x * tile_size, y, z * tile_size));
            colors.push_back(terrain_to_color(t.terrain));
        }
    }

    // 每個格子切成兩個三角形
    for (int z = 0; z < data.height - 1; z++) {
        for (int x = 0; x < data.width - 1; x++) {
            int i = z * data.width + x;
            indices.push_back(i);               indices.push_back(i + data.width);    indices.push_back(i + 1);
            indices.push_back(i + 1);           indices.push_back(i + data.width);    indices.push_back(i + data.width + 1);
        }
    }

    Array arrays;
    arrays.resize(Mesh::ARRAY_MAX);
    arrays[Mesh::ARRAY_VERTEX] = verts;
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
var mesh: ArrayMesh = MapCoreGDExt.generate_terrain_mesh(map_data, 1.0, 2.0, 0.05)
terrain_node.mesh = mesh
```

---

## Flat Shading（Low Poly 視覺關鍵）

Low poly 視覺依賴 **per-face flat shading**——每個三角面是純色，沒有平滑法線插值。

做法：生成 mesh 時不共享頂點（每個三角面各有 3 個獨立頂點），法線設定為面法線。

```cpp
// 不共享頂點版本（flat shading）：
// 每個三角形單獨生成 3 個頂點，而非 index 共享
// → 面數 × 3 個頂點，但法線計算正確
```

或在 StandardMaterial3D 啟用：
- `shading_mode = SHADING_MODE_UNSHADED`（純色，無燈光）
- 或保留燈光但用 flat normal（在 SurfaceTool 中 call `generate_normals(true)` 啟用 flat）

---

## 生態圈（Biome Layer）

不再需要 shader 混合，直接在格子上方程序放置 3D 物件：

```gdscript
func populate_biome(map_data: MapData) -> void:
    for cell in map_data.get_cells():
        if cell.terrain == TERRAIN_FOREST:
            var tree = TREE_SCENE.instantiate()
            tree.position = Vector3(cell.x + randf_range(-0.3, 0.3),
                                    cell.hilliness * HEIGHT_SCALE,
                                    cell.z + randf_range(-0.3, 0.3))
            tree.rotation.y = randf() * TAU      # 隨機朝向
            tree.scale = Vector3.ONE * randf_range(0.8, 1.2)
            biome_layer.add_child(tree)
```

樹木、岩石等物件本身也是程序生成（見 `../godot_procgen_mesh/`）。

---

## 水面

```gdscript
# 固定 Y 的透明平面，覆蓋 water_depth > 0 的區域
var water_mat = StandardMaterial3D.new()
water_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
water_mat.albedo_color  = Color(0.2, 0.5, 0.8, 0.6)
water_plane.material_override = water_mat
```

進階：波浪 ShaderMaterial（用 sin/cos + TIME 驅動頂點位移）。

---

## 與 mapcore_cpp_square 的關係

mapcore_cpp_square 輸出的資料結構完全不需更動。
只有 GDExtension 橋接層（`mapcore_godot/src/`）需要新增 `generate_terrain_mesh()` 函式，
原有的 PackedArray 傳輸介面可保留（debug 或 minimap 仍可用）。

---

## 待決定

- [ ] Hex vs Square 格子（影響 mesh 切割方式）
- [ ] Terrain mesh 更新策略：整塊重生成 or 分塊 chunk（影響大地圖效能）
- [ ] Delaunay 三角化取代 uniform grid → 更有機感但實作複雜
- [ ] LOD：遠處用低精度 mesh
- [ ] 河流：沿地形貼合的 curve mesh，或單純藍色帶狀 mesh
- [ ] 迷霧系統（Fog of War）：mapcore 在 C++ 維護每格的可見性遮罩（visible / explored / hidden），Godot 側在地形 mesh 上疊一層半透明遮罩 mesh 或 decal，explored 格用暗色、hidden 格用全黑

---

*記錄時間：2026-05-22*
*狀態：概念階段，對應 2D 版本 `../godot_world_map/`*
