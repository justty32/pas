# GDExtension 教學：實現局部慢動作 (Local Slow Motion)

本教學將介紹如何在 Godot 4 中針對特定節點實現慢動作效果，而不影響全域的 `Engine.time_scale`。

## 1. 目標導向
- 理解全域時間縮放與局部時間縮放的限制。
- 學習如何對特定節點的動畫、粒子與補間動畫 (Tween) 進行速度縮放。
- 學習如何在 C++ 中處理具備局部時間意識的邏輯與物理運動。

## 2. 核心概念：全域 vs 局部
- **全域慢動作**：`Engine::get_singleton()->set_time_scale(0.1)`。這會影響整個引擎（包括 UI 與背景），簡單但缺乏靈活性。
- **局部慢動作**：保持全域縮放為 1.0，手動調整目標物件的內部速度參數。

## 3. 原始碼導航 (核心參考)
- **動畫播放器**: `scene/animation/animation_mixer.h` (L100: `set_speed_scale`)
- **粒子系統**: `scene/3d/gpu_particles_3d.h` (屬性 `speed_scale`)
- **補間動畫**: `scene/animation/tween.h` (L150: `set_speed_scale`)

## 4. 實作步驟

### 步驟 A：建立一個時間控制器 (`TimeController`)
我們建議建立一個組件來統一管理特定節點的分支。

```cpp
void LocalTimeScaler::apply_slow_motion(Node *p_root, double p_scale) {
    if (!p_root) return;

    // 1. 處理動畫播放器 (AnimationPlayer/AnimationTree)
    AnimationMixer *mixer = Object::cast_to<AnimationMixer>(p_root);
    if (mixer) {
        mixer->set_speed_scale(p_scale);
    }

    // 2. 處理粒子系統 (GPUParticles3D)
    GPUParticles3D *particles = Object::cast_to<GPUParticles3D>(p_root);
    if (particles) {
        particles->set_speed_scale(p_scale);
    }

    // 3. 遞迴處理子節點
    for (int i = 0; i < p_root->get_child_count(); i++) {
        apply_slow_motion(p_root->get_child(i), p_scale);
    }
}
```

### 步驟 B：處理自定義 C++ 邏輯
對於您在 `_process` 中撰寫的代碼，您需要手動乘上縮放係數。

```cpp
void MyEnemy::_process(double delta) {
    // 使用局部 delta
    double local_delta = delta * my_local_time_scale;
    
    // 所有的移動與計時邏輯都使用 local_delta
    Vector3 velocity = Vector3(0, 0, 10) * local_delta;
    set_position(get_position() + velocity);
}
```

### 步驟 C：處理物理體 (CharacterBody3D)
物理系統的 `_physics_process` 同樣依賴 `delta`。

```cpp
void MyPlayer::_physics_process(double delta) {
    double local_delta = delta * my_local_time_scale;
    
    // 計算重力與輸入
    if (!is_on_floor()) {
        velocity.y -= gravity * local_delta;
    }
    
    // 注意：move_and_slide 內部會自動處理全域 delta
    // 如果要實現局部慢動作，通常需要手動處理移動
    Vector3 motion = velocity * local_delta;
    move_and_collide(motion); 
}
```

## 5. 處理補間動畫 (Tween)
當您在特定節點上建立 Tween 時，務必設定其速度：

```cpp
Ref<Tween> tween = get_tree()->create_tween();
tween->set_speed_scale(my_local_time_scale);
tween->tween_property(this, "position", target_pos, 1.0);
```

## 6. 進階：使用 Shader 實現慢動作視覺效果
有時慢動作需要配合視覺濾鏡（如色差或殘影）：
- 在 `CanvasItem` (2D) 或 `GeometryInstance3D` (3D) 上套用材質。
- 在 C++ 中將 `time_scale` 作為參數傳給 Shader。

```cpp
material->set_shader_parameter("local_time_scale", my_local_time_scale);
```

## 7. 實務提示
1. **音訊處理**：局部慢動作通常不包含音訊。若要讓音效也變慢，需存取 `AudioStreamPlayer` 的 `pitch_scale`。
2. **物理同步**：局部慢動作的物理體與正常速度的物理體發生碰撞時，可能會有視覺上的抖動，因為物理伺服器 (PhysicsServer) 仍以全域步長運行。
3. **組件化**：建議將 `local_time_scale` 定義為自定義 Node 的一個屬性，並在 `_bind_methods` 中暴露，方便在編輯器或 AnimationPlayer 中對其進行動畫化。
