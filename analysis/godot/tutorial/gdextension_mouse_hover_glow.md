# GDExtension 教學：實現滑鼠懸停發光與描邊效果

本教學將介紹如何在 C++ 中透過 GDExtension 實作當滑鼠移動到物件上時，觸發 Shader 特效。

## 1. 目標導向
- 如何在 C++ 中處理滑鼠進入 (`Mouse Enter`) 與離開 (`Mouse Exit`) 事件。
- 如何動態修改 Shader 的 Uniform 參數。
- 如何結合 `Tween` 實作平滑的視覺過渡。

## 2. 第一步：編寫 2D 描邊 Shader (`outline.gdshader`)
```glsl
shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float width : hint_range(0.0, 10.0) = 0.0; // 預設寬度為 0

void fragment() {
    float size = width * TEXTURE_PIXEL_SIZE.x;
    vec4 t = texture(TEXTURE, UV);
    
    // 簡單的描邊採樣邏輯
    float a = texture(TEXTURE, UV + vec2(size, 0.0)).a;
    a += texture(TEXTURE, UV + vec2(-size, 0.0)).a;
    a += texture(TEXTURE, UV + vec2(0.0, size)).a;
    a += texture(TEXTURE, UV + vec2(0.0, -size)).a;
    
    if (t.a < 0.5 && a > 0.0) {
        COLOR = outline_color;
    } else {
        COLOR = t;
    }
}
```

## 3. 第二步：C++ 互動類別實作
您可以繼承 `Sprite2D` 或 `Button`。

```cpp
class HoverSprite : public Sprite2D {
    GDCLASS(HoverSprite, Sprite2D);

protected:
    void _notification(int p_what) {
        switch (p_what) {
            case NOTIFICATION_MOUSE_ENTER:
                _set_hover_active(true);
                break;
            case NOTIFICATION_MOUSE_EXIT:
                _set_hover_active(false);
                break;
        }
    }

    void _set_hover_active(bool p_active) {
        Ref<ShaderMaterial> mat = get_material();
        if (mat.is_null()) return;

        // 建立一個 Tween 讓寬度變化更平滑
        Ref<SceneTreeTimer> timer; 
        Ref<Tween> tween = get_tree()->create_tween();
        
        float target_width = p_active ? 2.0f : 0.0f;
        
        // 核心：動態修改 Shader 參數
        tween->tween_method(
            callable_mp(this, &HoverSprite::_update_shader_width),
            p_active ? 0.0f : 2.0f, 
            target_width, 
            0.2f
        );
    }

    void _update_shader_width(float p_width) {
        Ref<ShaderMaterial> mat = get_material();
        if (mat.is_valid()) {
            mat->set_shader_parameter("width", p_width);
        }
    }
};
```

## 4. 關鍵機制導航
- **`NOTIFICATION_MOUSE_ENTER/EXIT`**：這是 Godot 內建的通知，當滑鼠與節點的碰撞區域或矩形範圍重疊時觸發。
- **`set_pickable(true)`**：對於 `Sprite2D`，您需要確保對象是可拾取的 (Pickable)，或者掛載一個 `Area2D`。
- **`mouse_filter`**：如果是繼承自 `Control` (如 Button)，請檢查其 `mouse_filter` 屬性是否為 `MOUSE_FILTER_STOP`。

## 5. 進階：全體發光 (Glow)
若要實現真正的發光效果：
1. 在 Shader 中將輸出顏色乘以一個大於 1.0 的係數。
2. 確保場景中有 `WorldEnvironment` 節點且開啟了 **Glow** 功能。
3. C++ 中控制這個乘法係數。

## 6. 驗證方式
1. **材質設定**：在編輯器中手動建立一個 `ShaderMaterial` 並指派上述 Shader 給您的 C++ 節點。
2. **滑鼠測試**：執行場景，滑鼠快速劃過物件，檢查描邊是否平滑地出現與消失。
