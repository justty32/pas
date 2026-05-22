# 2D vs Low Poly 3D 取捨分析

## 背景

原始預想是先做 2D 遊戲再挑戰 3D。但在規劃 2D tilemap 大世界地圖與程序藝術系統時，發現 low poly 3D 在部分工作量上反而比 2D 更低。

---

## 取捨對比

| 需求 | 2D 方案 | Low Poly 3D 方案 | 優勢方 |
|------|---------|-----------------|--------|
| 地形高低差 | 丘陵 shader 疊加層，視覺有限 | poly 高度直接表現，燈光自動加深 | **3D** |
| 生態圈/植被 | 每種 tile 需 shader 混合 | 3D 物件直接擺放，密度隨機即可 | **3D** |
| 角色換裝 | Sprite2D 多層貼圖拼接 | Blender 骨骼 + 材質，工具鏈成熟 | 平手 |
| 材質複用 | 需自訂 shader overlay 系統 | 標準 UV + albedo，天生如此 | **3D** |
| 程序生成素材 | 像素操作（C++ GDExtension） | 多邊形操作（C++ 生成 mesh） | 平手 |
| 2D UI / HUD | 原生 | Control 節點，同樣原生 | 平手 |
| 美術門檻 | 像素畫 or 程序像素 | low poly 建模 or 程序 mesh | 略偏 2D |

**結論：大世界地圖和生態系那塊，3D 反而是「理所當然就這樣做」，2D 的分層方案反而需要更多設計。**

> **2026-05-22 決定：採用 Low Poly 3D 方案。**

---

## 程序生成 Low Poly 幾何

Low poly 3D 不需要手工建模，可以完全程序生成。

### 地形 Mesh 生成

```cpp
// mapcore 輸出的 grid 資料直接轉換成 3D mesh
// hilliness (float) → vertex Y offset
// terrain_type → vertex color / material index

void generate_terrain_mesh(ArrayMesh* mesh, const MapData& data) {
    PackedVector3Array verts;
    PackedColorArray colors;
    PackedInt32Array indices;

    for (int y = 0; y < data.height; y++) {
        for (int x = 0; x < data.width; x++) {
            const Tile& t = data.tile_at(x, y);
            float height = t.hilliness * HEIGHT_SCALE;

            // 4 頂點 + 加入隨機擾動（防止工業感）
            float jitter = rng.randf_range(-JITTER, JITTER);
            verts.push_back(Vector3(x, height + jitter, y));
            // ...
        }
    }
}
```

> **已實作**：`mapcore_godot/src/terrain_mesh_builder.h/.cpp`（`MapCoreTerrainMeshBuilder`）
> - 非共享頂點 flat shading
> - 確定性 seed jitter（每格頂點加 `±jitter_amp` 擾動）
> - 地形類型 → 頂點色直接映射

### 規避工業感的技巧

程序生成最大問題是「千篇一律」的工業感。對策：

| 技法 | 說明 | 實作狀態 |
|------|------|---------|
| **頂點擾動 (vertex jitter)** | 對每個頂點加上小範圍隨機偏移，打破完美網格感 | ✅ terrain_mesh_builder |
| **Noise displacement** | 用 hash noise 而非純隨機，擾動更有機感 | ✅ procgen_mesh_builder |
| **不規則面細分** | 避免均勻四邊形格子，改用不規則三角形分割 | 未實作（目前 uniform grid）|
| **尺度變化** | 同類物件加入隨機旋轉 + 縮放，0.8x–1.2x | ✅ biome_scatter.gd（0.45x~1.55x）|
| **少量極端個體** | 偶爾出現特別高的岩石、特別大的樹 | △ 部分（靠縮放變化）|
| **非對稱** | 細微偏移讓形狀「幾乎對稱但不完全對稱」 | ✅ procgen_mesh_builder（非均勻 XYZ 縮放）|
| **面色調變化** | 每個三角面略微偏移顏色（±12%） | ✅ procgen_mesh_builder（hf hash per face）|

### 岩石程序生成範例思路

```
1. 從球體或立方體開始（低精度，8–16 面）
2. 對每個頂點：position += noise3D(position * freq) * amplitude
3. 隨機縮放 XYZ 各自獨立（讓它扁平、高挑或渾圓）
4. 隨機旋轉後擺放
→ 每顆岩石都不同，但風格一致
```

> **已實作**：`procgen_mesh_builder.cpp::generate_rock()`
> - UV sphere（4 緯度環 × 6 經度段）+ hf3 hash noise 位移
> - 非均勻 XYZ 縮放（各軸 0.6~1.4 倍）
> - 面色明度抖動（±12%）

### 樹木程序生成思路

```
trunk: cylinder (很少面，4–6邊)
foliage: 幾個重疊的錐形或球體，位置/大小略偏隨機
→ L-system 可以更豐富，但 icon-style low poly 用簡單幾何就夠
```

> **已實作**：`procgen_mesh_builder.cpp::generate_tree_trunk()` + `generate_tree_foliage()`
> - 六稜柱樹幹（頂緣 Y 擾動 ±6%）
> - 多錐形叢集樹冠（2~4 個五稜錐重疊，各自隨機偏移/尺寸）

---

## 對現有 mapcore_cpp_square 的影響

mapcore_cpp_square 輸出的資料（terrain, hilliness, water_depth, features）完全適合驅動 3D 地形，**C++ 核心邏輯不需更動**。

需要改動的是 GDExtension 橋接層：

| 現在（2D）| 改成 3D | 狀態 |
|---------|--------|------|
| `PackedInt32Array` terrain → TileMapLayer | terrain → vertex color / material | ✅ 已轉換（terrain_mesh_builder）|
| `PackedFloat32Array` hilliness → shader 疊加 | hilliness → vertex Y height | ✅ 已轉換 |
| `PackedFloat32Array` water_depth → shader | water_depth → 水平面 mesh | ✅ PlaneMesh（map_renderer_3d.gd）|
| `TypedArray<Dict>` 河流 → Polyline2D | 河流 → 3D curve mesh | ❌ 尚未實作 |

---

## 未決定事項（狀態更新）

- [x] ~~方向確認：確定選 low poly 3D~~ → **已決定採用 3D**（2026-05-22）
- [x] ~~地形 mesh 細分策略~~ → **採用 uniform grid + vertex jitter**（terrain_mesh_builder）
- [x] ~~水面~~ → **靜態半透明 PlaneMesh + make_water() 材質**
- [ ] 角色是否 low poly 3D vs billboard 2D sprite → 待決定（godot_character_3d 概念文件中）
- [ ] Godot 3D pipeline 驗證 → 已部分驗證（terrain/procgen mesh 系統完整），待實際跑完整 demo

---

## 已實作系統索引

| 系統 | 位置 | 說明 |
|------|------|------|
| 地形 Mesh 生成 | `mapcore_godot/src/terrain_mesh_builder.h/.cpp` | C++ GDExtension，flat shading + jitter + 顏色映射 |
| 地圖渲染器 | `mapcore_godot/demo/scenes/map_renderer_3d.gd` | GDScript，整合地形 + 水面 + 生態散佈 |
| 材質工廠 | `mapcore_godot/demo/scenes/material_library.gd` | 靜態工廠 + 快取，多種材質類型 |
| 程序岩石/樹 | `mapcore_godot/src/procgen_mesh_builder.h/.cpp` | C++ GDExtension，UV sphere 岩石 + 樹 |
| 生態圈散佈 | `mapcore_godot/demo/scenes/biome_scatter.gd` | GDScript，MultiMesh GPU instancing |
| 鏡頭控制 | `mapcore_godot/demo/scenes/camera_rig_3d.gd` | Pivot+Arm，Pan/Zoom/Rotate/邊緣滾動 |
| 選取高亮（3D）| `mapcore_godot/demo/shaders/selection_outline.gdshader` | cull_front 沿法線膨脹描邊 |
| 邊緣發光 | `mapcore_godot/demo/shaders/rim_glow.gdshader` | Fresnel rim glow shader |

---

*記錄時間：2026-05-22*
*狀態：已決定採用 Low Poly 3D；核心系統（地形/程序 mesh/材質/散佈/鏡頭/選取）已實作*
