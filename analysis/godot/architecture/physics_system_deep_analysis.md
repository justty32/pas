# Godot 物理系統深度架構分析 - Level 3 & 5

物理系統是 Godot 保持模擬穩定性的核心，其設計圍繞著「伺服器模型」與「固定步長更新」。

## 1. 核心步進機制 (Tick vs Frame)
Godot 區分了 **Process (渲染影格)** 與 **Physics Tick (物理更新)**。

### 1.1 `physics_step` 的由來
- 在 `main.cpp` 中，引擎透過 `physics_ticks_per_second` (預設 60) 計算出 `physics_step` (約 0.0166s)。
- **時間累積器 (Accumulator)**：`MainTimerSync` 會累積上一幀到現在流逝的真實時間。如果累積時間超過了 `physics_step`，就會觸發一次或多次物理循環。

### 1.2 循環順序：
1. **`_physics_process(delta)`**：腳本與 C++ 節點在此時修改力、速度或位置。
2. **`PhysicsServer::sync()`**：將節點的變動同步到物理伺服器的緩衝區。
3. **`PhysicsServer::step(delta)`**：物理引擎（預設為 GodotPhysics，或插件如 Jolt）執行碰撞檢測與約束求解 (Solver)。
4. **`PhysicsServer::end_sync()`**：將模擬結果（新的位置、旋轉）寫回場景節點。

## 2. 物理伺服器架構 (`PhysicsServer3D`)
- **解耦設計**：`PhysicsServer` 不知道 `Node` 的存在，它只操作 `RID` (Resource ID)。
- **多執行緒安全**：Godot 支援在獨立執行緒運行物理 (`thread_model/physics_common`)。透過雙緩衝機制，渲染執行緒可以讀取舊的物理狀態，而物理執行緒正在計算新的狀態。

## 3. 碰撞檢測與求解
- **Broadphase**：使用動態 AABB 樹 (Dynamic BVH) 快速篩選可能碰撞的物件對。
- **Narrowphase**：執行精確的幾何碰撞計算（如 GJK/EPA 算法）。
- **Island Management**：將彼此接觸的物體劃分為「島嶼」，以便並行處理不同的物理群組。

## 4. 插值機制 (FTI)
當渲染幀率（如 144Hz）高於物理幀率（60Hz）時，物件會顯得閃爍。Godot 4 透過 `physics_interpolation_fraction` 在兩個物理 Tick 之間線性插值物件的 `Transform`，確保視覺上的絲滑感。

---
*檔案參考：`main/main.cpp`, `servers/physics_3d/physics_server_3d.h`, `core/main_timer_sync.cpp`*
