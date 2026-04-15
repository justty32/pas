# GDExtension 教學：2D 裝備染色系統 (2D Sprite Dyeing)

本教學將介紹如何在 2D 遊戲中，利用 C++ 與 Shader 實作角色精靈的局部染色。

## 1. 目標導向
- 如何在 2D 精靈上使用區域遮罩進行染色。
- 如何透過 C++ 統一控制角色全身多個精靈組件（如頭、身、腿）的顏色。

## 2. 核心概念
在 2D 中，我們通常使用 **灰階基底 (Grayscale Base)** + **遮罩** 的方式。
- **基底圖**：裝備的明暗與紋理細節。
- **顏色變數**：由 C++ 動態傳入。

## 3. 實作步驟

### 步驟 A：2D 染色 Shader (`sprite_dye.gdshader`)
```glsl
shader_type canvas_item;

uniform sampler2D mask_tex;
uniform vec4 primary_dye : source_color;
uniform vec4 secondary_dye : source_color;

void fragment() {
    vec4 color = texture(TEXTURE, UV);
    vec4 mask = texture(mask_tex, UV);
    
    // R 頻道控制主色，G 頻道控制副色
    vec3 dyed = color.rgb;
    if (mask.r > 0.5) {
        dyed = color.rgb * primary_dye.rgb;
    } else if (mask.g > 0.5) {
        dyed = color.rgb * secondary_dye.rgb;
    }
    
    COLOR = vec4(dyed, color.a);
}
```

### 步驟 B：C++ 角色管理器實作
當角色有多個部分時，我們需要遍歷所有 Sprite。

```cpp
void MyCharacter::update_equipment_colors(Color p_primary, Color p_secondary) {
    // 假設角色下有多個 Sprite2D 節點
    LocalVector<String> parts;
    parts.push_back("Head");
    parts.push_back("Body");
    parts.push_back("Legs");

    for (const String &part : parts) {
        Sprite2D *s = Object::cast_to<Sprite2D>(get_node_or_null(part));
        if (s) {
            Ref<ShaderMaterial> mat = s->get_material();
            if (mat.is_valid()) {
                mat->set_shader_parameter("primary_dye", p_primary);
                mat->set_shader_parameter("secondary_dye", p_secondary);
            }
        }
    }
}
```

## 4. 進階技巧：調色盤切換 (Palette Swap)
對於像素遊戲，更進階的做法是使用 **調色盤索引**：
1. 原始貼圖僅使用特定的索引顏色。
2. Shader 讀取一張 1xN 的調色盤貼圖。
3. C++ 負責更換這張調色盤貼圖或修改調色盤中的像素。

## 5. 驗證方式
1. **Shader 預覽**：在編輯器中手動調整 `ShaderMaterial` 的 `Uniforms`，確認染色區域正確。
2. **C++ 調用**：從 GDScript 呼叫 `update_equipment_colors`，觀察角色是否即時變色。
