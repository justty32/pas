# GDExtension 教學：使用 C++ 程序化建立動畫

本教學將介紹如何在 C++ 中從零開始建立一個 `Animation` 資源，並將其套用到場景中的 `AnimationPlayer`。

## 1. 目標導向
- 如何實例化 `Animation` 資源。
- 如何新增 3D 變換軌道與屬性值軌道。
- 如何插入關鍵幀並設定插值與緩動。
- 如何將動畫整合進 `AnimationLibrary` 供播放器使用。

## 2. 前置知識
- 已了解 `NodePath` 的格式（如 `"MeshInstance3D:position"`）。
- 了解 Godot 4 的動畫庫 (`AnimationLibrary`) 概念。

## 3. 原始碼導航
- **資源操作**: `scene/resources/animation.h` (搜尋 `add_track`, `track_set_path`)
- **關鍵幀插入**: `scene/resources/animation.cpp` (搜尋 `position_track_insert_key`, `track_insert_key`)

## 4. 實作步驟

### 步驟 A：建立基礎動畫資源
```cpp
Ref<Animation> MyAnimCreator::create_move_anim() {
    Ref<Animation> anim = memnew(Animation);
    anim->set_length(2.0); // 設定總長度為 2 秒
    anim->set_loop_mode(Animation::LOOP_LINEAR);
    return anim;
}
```

### 步驟 B：新增 3D 變換軌道 (Position/Rotation)
這是針對 3D 節點優化的軌道。

```cpp
void add_transform_tracks(Ref<Animation> p_anim) {
    // 1. 新增 Position 軌道，路徑指向自身 "."
    int pos_idx = p_anim->add_track(Animation::TYPE_POSITION_3D);
    p_anim->track_set_path(pos_idx, "."); 

    // 2. 插入關鍵幀 (索引, 時間, 數值)
    p_anim->position_track_insert_key(pos_idx, 0.0, Vector3(0, 0, 0));
    p_anim->position_track_insert_key(pos_idx, 1.0, Vector3(0, 5, 0)); // 1秒時上升
    p_anim->position_track_insert_key(pos_idx, 2.0, Vector3(0, 0, 0));
}
```

### 步驟 C：新增屬性軌道 (Value Track)
用於控制如顏色、能量、可見性等屬性。

```cpp
void add_value_tracks(Ref<Animation> p_anim) {
    // 控制子節點 Mesh 的透明度
    int val_idx = p_anim->add_track(Animation::TYPE_VALUE);
    p_anim->track_set_path(val_idx, "MeshInstance3D:modulate");
    
    // 設定插值方式為線性
    p_anim->track_set_interpolation_type(val_idx, Animation::INTERPOLATION_LINEAR);

    // 插入關鍵幀 (索引, 時間, Variant數值)
    p_anim->track_insert_key(val_idx, 0.0, Color(1, 1, 1, 1));
    p_anim->track_insert_key(val_idx, 1.0, Color(1, 1, 1, 0)); // 消失
    p_anim->track_insert_key(val_idx, 2.0, Color(1, 1, 1, 1));
}
```

### 步驟 D：註冊並播放
Godot 4 規定動畫必須存在於 `AnimationLibrary` 中。

```cpp
void MyAnimCreator::apply_and_play(AnimationPlayer *p_player) {
    if (!p_player) return;

    Ref<Animation> my_anim = create_move_anim();
    add_transform_tracks(my_anim);
    add_value_tracks(my_anim);

    // 1. 建立或取得動畫庫
    Ref<AnimationLibrary> lib;
    if (p_player->has_animation_library("")) {
        lib = p_player->get_animation_library("");
    } else {
        lib = memnew(AnimationLibrary);
        p_player->add_animation_library("", lib);
    }

    // 2. 加入動畫
    lib->add_animation("procedural_move", my_anim);

    // 3. 播放
    p_player->play("procedural_move");
}
```

## 5. 進階：方法調用軌道 (Method Track)
您可以在動畫中呼叫 C++ 方法：
```cpp
int meth_idx = anim->add_track(Animation::TYPE_METHOD);
anim->track_set_path(meth_idx, ".");
anim->method_track_insert_key(meth_idx, 1.5, "my_cpp_callback_function", Array());
```

## 6. 驗證與偵錯
1. **遠端檢查**：執行遊戲後，在編輯器的「遠端 (Remote)」場景樹選中 `AnimationPlayer`，檢查其 `AnimationLibrary` 是否正確出現了 `procedural_move`。
2. **長度檢查**：確保最後一個關鍵幀的時間不超過 `set_length` 設定的值，否則最後一段將無法播放。
