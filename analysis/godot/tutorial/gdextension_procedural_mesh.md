# GDExtension 教學：程序化生成 3D 模型 (Mesh)

本教學將介紹如何在 C++ 中使用 `SurfaceTool` 動態生成 3D 幾何資料。

## 1. 目標導向
- 如何在執行時建立自定義的頂點、法線與 UV 座標。
- 如何使用 `ArrayMesh` 封裝幾何資料。
- 如何實作一個簡單的程序化三角形或平面。

## 2. 前置知識
- 已了解 `MeshInstance3D` 節點的作用。
- 基礎的 3D 座標概念 (Vector3)。

## 3. 原始碼導航
- **幾何工具**: `scene/resources/surface_tool.h` (高階封裝，推薦使用)
- **Mesh 資源**: `scene/resources/mesh.h` (底層資料結構)

## 4. 實作步驟

### 步驟 A：使用 SurfaceTool 建立幾何體
`SurfaceTool` 提供了一個簡單的狀態機風格 API 來建立 Mesh。

```cpp
Ref<ArrayMesh> MyNode3D::create_triangle_mesh() {
    Ref<SurfaceTool> st = memnew(SurfaceTool);
    
    // 1. 開始作業，指定原始類型 (如三角形)
    st->begin(Mesh::PRIMITIVE_TRIANGLES);
    
    // 2. 設定目前的屬性（法線、UV 等，必須在 add_vertex 之前設定）
    st->set_normal(Vector3(0, 0, 1));
    st->set_uv(Vector2(0, 0));
    st->add_vertex(Vector3(0, 0, 0)); // 第一個點

    st->set_uv(Vector2(1, 0));
    st->add_vertex(Vector3(1, 0, 0)); // 第二個點

    st->set_uv(Vector2(0.5, 1));
    st->add_vertex(Vector3(0.5, 1, 0)); // 第三個點

    // 3. (選用) 自動索引與平滑法線
    // st->index(); 
    // st->generate_normals();

    // 4. 提交到 ArrayMesh
    return st->commit();
}
```

### 步驟 B：將 Mesh 套用到節點
```cpp
void MyNode3D::apply_procedural_mesh() {
    MeshInstance3D *mi = memnew(MeshInstance3D);
    mi->set_mesh(create_triangle_mesh());
    add_child(mi);
}
```

## 5. 重要：法線生成順序

法線決定光照方向，**必須**在 `commit()` 之前設定：

| 方式 | 適用情境 |
|------|----------|
| `st->set_normal(n)` 手動設定，每頂點呼叫一次 | 已知法線方向（如球面、法線貼圖配合） |
| `st->generate_normals()` 自動從三角面計算 | 快速建立，不需精細控制；需在 `commit()` 前呼叫 |

```cpp
// 若使用 generate_normals，不需手動 set_normal
st->begin(Mesh::PRIMITIVE_TRIANGLES);
st->add_vertex(Vector3(0, 0, 0));
// ... 其他頂點
// generate_normals 必須在 commit() 之前，且需先 index()
st->index();             // (選用) 合併重複頂點，減少 GPU 工作量
st->generate_normals();  // 從面計算頂點法線
Ref<ArrayMesh> mesh = st->commit();
```

## 6. 進階應用：程序化平面地形

以下是一個完整的 NxN 格位平面 Mesh 範例，示範 UV 映射與材質設定：

```cpp
Ref<ArrayMesh> MyNode3D::create_plane_mesh(int grid_size, float cell_size) {
    Ref<SurfaceTool> st = memnew(SurfaceTool);
    st->begin(Mesh::PRIMITIVE_TRIANGLES);

    for (int z = 0; z < grid_size; z++) {
        for (int x = 0; x < grid_size; x++) {
            float x0 = x * cell_size, x1 = (x + 1) * cell_size;
            float z0 = z * cell_size, z1 = (z + 1) * cell_size;

            // 每格兩個三角形（順時針，法線朝上）
            // 三角形 1
            st->set_uv(Vector2((float)x / grid_size, (float)z / grid_size));
            st->add_vertex(Vector3(x0, 0, z0));

            st->set_uv(Vector2((float)(x+1) / grid_size, (float)z / grid_size));
            st->add_vertex(Vector3(x1, 0, z0));

            st->set_uv(Vector2((float)x / grid_size, (float)(z+1) / grid_size));
            st->add_vertex(Vector3(x0, 0, z1));

            // 三角形 2
            st->set_uv(Vector2((float)(x+1) / grid_size, (float)z / grid_size));
            st->add_vertex(Vector3(x1, 0, z0));

            st->set_uv(Vector2((float)(x+1) / grid_size, (float)(z+1) / grid_size));
            st->add_vertex(Vector3(x1, 0, z1));

            st->set_uv(Vector2((float)x / grid_size, (float)(z+1) / grid_size));
            st->add_vertex(Vector3(x0, 0, z1));
        }
    }

    st->generate_normals(); // 自動計算向上的法線

    // 套用材質後再 commit
    Ref<StandardMaterial3D> mat = memnew(StandardMaterial3D);
    mat->set_albedo(Color(0.4, 0.7, 0.3)); // 草地綠色
    st->set_material(mat);

    return st->commit();
}
```

## 7. 效能提示
- 重複使用同一個 `SurfaceTool` 時，在 `begin()` 前呼叫 `st->clear()` 清空狀態。
- 若 Mesh 幾何形狀固定但材質需要更新，應直接操作 `MeshInstance3D` 的 `surface_override_material`，而不是重建整個 Mesh。
- 大型地形建議在子執行緒中計算頂點數據，再回到主執行緒呼叫 `st->commit()`。
