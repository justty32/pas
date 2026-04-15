# GDExtension 教學：將 .jpg 檔案轉換為運行中的 Sprite

本教學將介紹如何在 C++ 中動態載入磁碟上的圖像檔案，並將其顯示在場景中。

## 1. 目標導向
- 如何從磁碟路徑載入 `.jpg` 或 `.png` 檔案。
- 如何將原始圖像數據轉換為 GPU 可用的 `Texture`。
- 如何動態建立 `Sprite2D` 節點並指派貼圖。

## 2. 前置知識
- 已了解 `Ref<T>` 資源管理。
- 了解 `Image` 與 `Texture2D` 的區別。

## 3. 原始碼導航
- **圖像處理**: `core/io/image.h` (L50+: `load`)
- **貼圖資源**: `scene/resources/image_texture.h` (L45: `create_from_image`)
- **精靈節點**: `scene/2d/sprite_2d.h`

## 4. 實作步驟

### 步驟 A：載入圖片檔案
Godot 的 `Image` 類別可以處理 CPU 端的原始像素數據。

```cpp
Ref<Image> MyLoader::load_external_image(String p_path) {
    Ref<Image> img = memnew(Image);
    Error err = img->load(p_path);
    
    if (err != OK) {
        UtilityFunctions::print("無法載入圖片：", p_path);
        return nullptr;
    }
    
    return img;
}
```

### 步驟 B：轉換為 ImageTexture
若要在 GPU 上渲染，必須將 `Image` 轉換為 `Texture2D` (具體為 `ImageTexture`)。

```cpp
Ref<Texture2D> MyLoader::create_texture_from_image(Ref<Image> p_img) {
    if (p_img.is_null()) return nullptr;
    
    // 從 Image 建立 ImageTexture
    Ref<ImageTexture> tex = ImageTexture::create_from_image(p_img);
    return tex;
}
```

### 步驟 C：建立並顯示 Sprite
```cpp
void MyLoader::spawn_sprite_from_file(String p_path) {
    // 1. 載入並建立貼圖
    Ref<Image> img = load_external_image(p_path);
    Ref<Texture2D> tex = create_texture_from_image(img);

    if (tex.is_valid()) {
        // 2. 建立 Sprite2D 節點
        Sprite2D *sprite = memnew(Sprite2D);
        sprite->set_texture(tex);
        sprite->set_position(Vector2(500, 300));
        
        // 3. 加入場景樹
        add_child(sprite);
    }
}
```

## 5. 處理 GIF 或序列幀 (AnimatedSprite2D)
如果您要動態建立 `AnimatedSprite2D`：
```cpp
void MyLoader::setup_animated_sprite(Ref<Texture2D> p_sheet) {
    AnimatedSprite2D *as = memnew(AnimatedSprite2D);
    Ref<SpriteFrames> sf = memnew(SpriteFrames);
    
    sf->add_animation("default");
    sf->add_frame("default", p_sheet); // 加入每一幀
    
    as->set_sprite_frames(sf);
    add_child(as);
    as->play("default");
}
```

## 6. 效能與安全提示
1. **快取**：不要在 `_process` 中重複載入圖片。圖片載入應在初始階段或後台執行緒完成。
2. **記憶體**：`ImageTexture` 會佔用 GPU 顯存。若不再需要，確保 `Ref<Texture2D>` 被正確釋放。
3. **路徑安全性**：若路徑來自使用者輸入，務必進行格式檢查以防止惡意存取。
