# GDExtension 教學：自定義與高效能 A* 尋路算法

本教學將介紹如何在 C++ 中擴充 Godot 的導航系統，實作自定義權重的 A* 或完全獨立的高效能尋路引擎。

## 1. 目標導向
- 如何自定義 A* 的啟發式函數 (Heuristic) 以處理複雜的地形權重。
- 如何在 C++ 中實作一個不依賴虛擬函數 call 的高效能格位 A*。
- 如何透過 `WorkerThreadPool` 進行非同步尋路。

## 2. 前置知識
- 已完成「多執行緒處理」教學。
- 基礎的 A* 算法邏輯 (G Score, H Score, F Score)。

## 3. 原始碼導航 (核心參考)
- **內建 AStar**: `core/math/a_star.h` (L45: `AStar3D` 類別定義)
- **虛擬方法**: `core/math/a_star.cpp` (搜尋 `_compute_cost` 與 `_estimate_cost`)
- **高效能容器**: `core/templates/local_vector.h`

## 4. 方案一：擴充內建 AStar3D
適合需要 Godot 幫您管理點位連結，但您想自定義權重的情況。

### 實作步驟：
```cpp
class MyCustomAStar : public AStar3D {
    GDCLASS(MyCustomAStar, AStar3D);

protected:
    // 計算兩點間的實際移動開銷
    double _compute_cost(int64_t p_from_id, int64_t p_to_id) const override {
        double dist = get_point_position(p_from_id).distance_to(get_point_position(p_to_id));
        
        // 範例：如果點位有自定義權重（如泥濘地形），則增加開銷
        // 可以透過 get_point_weight_scale() 獲取
        return dist * get_point_weight_scale(p_to_id);
    }

    // 計算預估值 (啟發式)
    double _estimate_cost(int64_t p_from_id, int64_t p_to_id) const override {
        // 使用曼哈頓距離或歐幾里得距離
        return get_point_position(p_from_id).distance_to(get_point_position(p_to_id));
    }
};
```

## 5. 方案二：實作原生高效能 Grid A* (C++ 實作)
如果您在製作 RTS 或大規模體素 (Voxel) 遊戲，內建的 AStar3D 可能因虛擬函數調用而有瓶頸。

### 核心實作想法：
使用 `std::priority_queue` 與平面陣列索引。

```cpp
struct Node {
    int x, y;
    float g, h;
    Node* parent;
    float f() const { return g + h; }
};

// C++ 快速尋路函數
Vector<Vector2i> FastGridAStar::find_path(Vector2i p_start, Vector2i p_end) {
    // 1. 使用 LocalVector 與預分配空間減少記憶體分配
    LocalVector<Node*> open_list;
    // ... 實作 A* 核心循環 ...
    // 注意：在 C++ 中直接存取二維陣列數據，避免過多的 Variant 轉換
}
```

## 6. 非同步尋路 (Async Pathfinding)
尋路通常很耗時，應在子執行緒中執行。

```cpp
void MyPathManager::request_path(Vector3 p_from, Vector3 p_to) {
    WorkerThreadPool::get_singleton()->add_task(
        callable_mp(this, &MyPathManager::_compute_path_async)
    );
}

void MyPathManager::_compute_path_async() {
    // 執行尋路邏輯
    PackedVector3Array path = my_astar->get_point_path(start_id, end_id);
    
    // 回到主執行緒回報結果
    call_deferred("emit_signal", "path_computed", path);
}
```

## 7. 效能優化建議
1. **快取 (Caching)**：對於靜態地圖，快取常用的路徑。
2. **分層 A* (HPA*)**：將地圖分為多個區塊 (Chunks)，先在區塊間尋路，再在區塊內細化。
3. **向量化 (SIMD)**：對於大規模距離計算，可考慮使用 Godot 的 `Vector3` 內建的優化。
4. **JPS (Jump Point Search)**：若為對稱格位地圖，JPS 算法通常比原生 A* 快數倍。

## 8. 驗證方式
1. **基準測試 (Benchmarking)**：在 C++ 中記錄尋路時間，與 GDScript 實作進行對比。
2. **視覺化**：在編輯器中使用 `_draw()` 函數或 `MeshInstance3D` (線段) 繪製出路徑，確認其符合權重邏輯。
