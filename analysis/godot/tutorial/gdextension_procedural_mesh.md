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

## 5. 進階應用：建立動態地形
對於大量數據，建議在子執行緒中計算頂點數據，然後回到主執行緒調用 `st->commit()`。

### 效能提示：
- 若 Mesh 需要頻繁更新，請考慮使用 `Mesh::update_surface_region`。
- 確保在 `st->begin()` 之前呼叫 `st->clear()` 若要重複使用同一個工具實例。
