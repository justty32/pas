# GDExtension 教學：程序化生成粒子特效 (Particles)

本教學將介紹如何在 C++ 中從零開始建立並配置 `GPUParticles3D` 系統，實現動態的程序化特效。

## 1. 目標導向
- 如何在執行時建立 `GPUParticles3D` 節點。
- 如何透過 C++ 設定粒子的發射行為（速度、擴散、生命週期）。
- 如何為粒子套用程序化的顏色與尺寸曲線。

## 2. 前置知識
- 已了解 `Node` 生命週期與 `Resource` 管理。
- 了解 Godot 的粒子發射機制（`ProcessMaterial` vs `DrawPass`）。

## 3. 原始碼導航 (核心參考)
- **粒子節點**: `scene/3d/gpu_particles_3d.h`
- **粒子材質**: `scene/resources/particle_process_material.h` (L50+: 各種屬性 Setter)
- **曲線資源**: `scene/resources/curve.h` (用於控制隨時間變化的屬性)

## 4. 實作步驟

### 步驟 A：建立粒子發射器
```cpp
GPUParticles3D* MyEffectManager::create_explosion(Vector3 p_position) {
    // 1. 建立粒子節點
    GPUParticles3D *particles = memnew(GPUParticles3D);
    particles->set_position(p_position);
    particles->set_amount(100); // 粒子數量
    particles->set_lifetime(1.5);
    particles->set_one_shot(true); // 僅發射一次
    particles->set_explosiveness_ratio(1.0); // 同時噴出
    
    // 2. 設定粒子的外觀 (Draw Pass)
    // 我們建立一個簡單的四邊形 Mesh
    Ref<QuadMesh> mesh = memnew(QuadMesh);
    mesh->set_size(Vector2(0.2, 0.2));
    particles->set_draw_pass_mesh(0, mesh);

    // 3. 配置處理材質 (Process Material)
    particles->set_process_material(create_explosion_material());

    add_child(particles);
    particles->set_emitting(true); // 開始發射
    
    return particles;
}
```

### 步驟 B：程序化配置 ParticleProcessMaterial
```cpp
Ref<ParticleProcessMaterial> MyEffectManager::create_explosion_material() {
    Ref<ParticleProcessMaterial> mat = memnew(ParticleProcessMaterial);

    // 設定發射方向與速度
    mat->set_direction(Vector3(0, 1, 0)); // 向上
    mat->set_spread(180.0); // 全方位擴散
    mat->set_initial_velocity_min(5.0);
    mat->set_initial_velocity_max(10.0);
    
    // 設定重力
    mat->set_gravity(Vector3(0, -9.8, 0));

    // 設定顏色隨時間變化 (Color Ramp)
    Ref<Gradient> gradient = memnew(Gradient);
    gradient->add_point(0.0, Color(1, 1, 0)); // 起始黃色
    gradient->add_point(1.0, Color(1, 0, 0, 0)); // 結束變紅並消失
    
    Ref<GradientTexture1D> ramp = memnew(GradientTexture1D);
    ramp->set_gradient(gradient);
    mat->set_color_ramp(ramp);

    return mat;
}
```

### 步驟 C：建立尺寸縮放曲線
粒子通常在消失前會變小：
```cpp
void setup_scale_curve(Ref<ParticleProcessMaterial> p_mat) {
    Ref<Curve> curve = memnew(Curve);
    curve->add_point(Vector2(0, 1)); // 開始時大小為 1
    curve->add_point(Vector2(1, 0)); // 結束時大小為 0
    
    Ref<CurveTexture> curve_tex = memnew(CurveTexture);
    curve_tex->set_curve(curve);
    p_mat->set_param_texture(ParticleProcessMaterial::PARAM_SCALE, curve_tex);
}
```

## 5. 進階應用：粒子與 Shader 整合
您可以為粒子的 `DrawPass` 套用自定義的 `ShaderMaterial`：
```cpp
Ref<ShaderMaterial> particle_draw_mat = memnew(ShaderMaterial);
particle_draw_mat->set_shader(my_particle_shader);
mesh->set_material(particle_draw_mat);
```
這允許您在粒子上實作高級效果，如火焰扭曲或溶解動畫。

## 6. 效能提示
1. **物件池 (Object Pooling)**：頻繁 `memnew` 與 `memdelete` 粒子節點會造成效能壓力。建議預先建立一組粒子實例並重複使用。
2. **GPU vs CPU**：
    - `GPUParticles3D`：效能極高，支援數百萬粒子，但難以在 C++ 中精確讀取單個粒子的位置。
    - `CPUParticles3D`：若您需要 C++ 邏輯與每個粒子互動，請改用此類別。
3. **自動清理**：對於 `one_shot` 粒子，可以連接 `finished` 信號到 `queue_free()` 以自動釋放。
