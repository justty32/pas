# GDExtension 教學：程序化生成動畫 (Animation)

本教學將介紹如何在 C++ 中動態建立 `Animation` 資源並使用 `AnimationPlayer` 播放。

## 1. 目標導向
- 如何從零建立一個 `Animation` 資源。
- 如何在動畫中新增位置、旋轉或縮放軌道 (Tracks)。
- 如何插入關鍵幀 (Keyframes) 並設定插值方式。

## 2. 前置知識
- 已了解 `AnimationPlayer` 節點的基本用法。
- 了解 `NodePath` 的概念。

## 3. 原始碼導航
- **動畫資源**: `scene/resources/animation.h` (L100+: 軌道操作 API)
- **播放器**: `scene/animation/animation_player.h`

## 4. 實作步驟

### 步驟 A：建立 Animation 資源並新增軌道
```cpp
Ref<Animation> MyNode3D::create_walk_animation() {
    Ref<Animation> anim = memnew(Animation);
    anim->set_length(1.0); // 動畫長度 1 秒
    anim->set_loop_mode(Animation::LOOP_LINEAR);

    // 1. 新增一個 3D 變換軌道 (對應此節點的 position)
    // 軌道路徑通常是 "." (自身) 或子節點路徑
    int track_idx = anim->add_track(Animation::TYPE_POSITION_3D);
    anim->track_set_path(track_idx, "."); // 控制自身

    // 2. 插入關鍵幀 (時間, 數值)
    anim->position_track_insert_key(track_idx, 0.0, Vector3(0, 0, 0));
    anim->position_track_insert_key(track_idx, 0.5, Vector3(0, 2, 0)); // 向上移動
    anim->position_track_insert_key(track_idx, 1.0, Vector3(0, 0, 0));

    return anim;
}
```

### 步驟 B：使用 AnimationPlayer 播放
```cpp
void MyNode3D::play_procedural_animation() {
    // 1. 確保有 AnimationPlayer
    AnimationPlayer *ap = memnew(AnimationPlayer);
    add_child(ap);

    // 2. 建立動畫庫 (Godot 4 新機制)
    Ref<AnimationLibrary> library = memnew(AnimationLibrary);
    library->add_animation("bounce", create_walk_animation());
    
    // 3. 將庫加入播放器
    ap->add_animation_library("", library); // 使用空字串作為預設庫名
    
    // 4. 播放
    ap->play("bounce");
}
```

## 5. 進階：屬性軌道 (Property Track)
除了變換軌道，您還可以控制任何屬性（如材質顏色）：
```cpp
int color_track = anim->add_track(Animation::TYPE_VALUE);
anim->track_set_path(color_track, "MeshInstance3D:material_override:albedo_color");
anim->track_insert_key(color_track, 0.0, Color(1, 1, 1));
anim->track_insert_key(color_track, 1.0, Color(1, 0, 0));
```

## 6. 實務提示
- **NodePath**：動畫路徑必須相對於 `AnimationPlayer` 的 `root_node`。
- **混合**：您可以透過代碼設定 `AnimationMixer` 的播放權重來實現動態動畫混合。
