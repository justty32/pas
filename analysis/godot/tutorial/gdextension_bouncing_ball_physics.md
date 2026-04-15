# GDExtension 教學：使用 C++ 建立物理彈力球場景

本教學將介紹如何在 C++ 中透過代碼建構一個基本的物理模擬場景：一個掉落在地面上的彈力球。

## 1. 目標導向
- 如何建立 `RigidBody3D` 與 `StaticBody3D`。
- 如何為物理物件新增碰撞形狀 (`CollisionShape3D`)。
- 如何配置 `PhysicsMaterial` 以實現彈性 (Bounce)。
- 如何在 C++ 中施加物理力。

## 2. 前置知識
- 已了解節點建立與 `add_child` 流程。
- 已閱讀「物理系統深度分析」。

## 3. 實作步驟

### 步驟 A：建立地面 (StaticBody3D)
地面不應受到力影響，因此使用靜態體。

```cpp
void MyPhysicsManager::create_ground() {
    StaticBody3D *ground = memnew(StaticBody3D);
    ground->set_name("Ground");

    // 1. 建立碰撞形狀 (平面)
    CollisionShape3D *shape = memnew(CollisionShape3D);
    Ref<BoxShape3D> box = memnew(BoxShape3D);
    box->set_size(Vector3(20, 1, 20)); // 20x1x20 的地面
    shape->set_shape(box);
    
    ground->add_child(shape);
    ground->set_position(Vector3(0, -0.5, 0)); // 讓表面對齊 Y=0
    
    add_child(ground);
}
```

### 步驟 B：建立彈力球 (RigidBody3D)
```cpp
void MyPhysicsManager::create_bouncing_ball() {
    RigidBody3D *ball = memnew(RigidBody3D);
    ball->set_name("BouncingBall");

    // 1. 設定物理屬性 (重心與質量)
    ball->set_mass(1.0);

    // 2. 核心：建立彈性材質
    Ref<PhysicsMaterial> phys_mat = memnew(PhysicsMaterial);
    phys_mat->set_bounce(0.8); // 彈性係數 (0.0~1.0)
    phys_mat->set_friction(0.1);
    ball->set_physics_material_override(phys_mat);

    // 3. 新增球體碰撞形狀
    CollisionShape3D *shape = memnew(CollisionShape3D);
    Ref<SphereShape3D> sphere = memnew(SphereShape3D);
    sphere->set_radius(0.5);
    shape->set_shape(sphere);
    ball->add_child(shape);

    // 4. 設定初始位置
    ball->set_position(Vector3(0, 5, 0)); // 從 5 米高處落下
    
    add_child(ball);
}
```

### 步驟 C：施加初始衝量
如果您希望球一開始就有速度：
```cpp
void MyPhysicsManager::launch_ball(RigidBody3D *p_ball) {
    if (p_ball) {
        // 參數：(衝量向量, 作用點相對於中心的偏移)
        p_ball->apply_central_impulse(Vector3(2, 0, 0)); 
    }
}
```

## 4. 關鍵方法導航
- `set_physics_material_override()`：切換不同的物理特性（如滑冰、彈跳）。
- `set_lock_rotation()`：防止物件翻滾。
- `set_collision_layer()` 與 `set_collision_mask()`：控制哪些物件可以碰撞。

## 5. 驗證與偵錯
1. **Debug 視圖**：在編輯器選單選中「偵錯 (Debug) -> 可視化碰撞形狀 (Visible Collision Shapes)」。
2. **重力檢查**：若球不掉落，檢查「專案設定 -> 物理 -> 3D -> 預設重力」。
3. **睡眠狀態**：若 RigidBody 停止不動一段時間會進入 Sleep 模式以節省效能，可透過 `set_sleeping(false)` 喚醒。
