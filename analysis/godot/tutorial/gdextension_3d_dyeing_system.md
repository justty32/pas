# GDExtension 教學：3D 裝備染色系統 (Equipment Dyeing)

本教學將介紹如何使用 C++ 與 Shader 實作一個高效的 3D 裝備染色系統。

## 1. 目標導向
- 如何實作支援多區域染色的 3D Shader。
- 如何在 C++ 中動態修改 `MeshInstance3D` 的材質參數。
- 如何透過遮罩貼圖 (Mask Map) 隔離不同的染色區域。

## 2. 核心技術：遮罩混合 (Mask Blending)
我們不為每種顏色建立貼圖，而是使用一張 **遮罩貼圖**：
- **R 頻道**：金屬裝飾區域。
- **G 頻道**：主要布料區域。
- **B 頻道**：皮革/細節區域。

## 3. 實作步驟

### 步驟 A：編寫基礎染色 Shader (`equipment_dye.gdshader`)
```glsl
shader_type spatial;

uniform sampler2D albedo_tex : source_color;
uniform sampler2D mask_tex; // 遮罩貼圖

uniform vec4 dye_color_1 : source_color = vec4(1.0);
uniform vec4 dye_color_2 : source_color = vec4(1.0);
uniform vec4 dye_color_3 : source_color = vec4(1.0);

void fragment() {
    vec4 base = texture(albedo_tex, UV);
    vec4 mask = texture(mask_tex, UV);
    
    // 根據遮罩頻道混合顏色
    vec3 final_color = base.rgb;
    final_color = mix(final_color, final_color * dye_color_1.rgb, mask.r);
    final_color = mix(final_color, final_color * dye_color_2.rgb, mask.g);
    final_color = mix(final_color, final_color * dye_color_3.rgb, mask.b);
    
    ALBEDO = final_color;
}
```

### 步驟 B：C++ 染色控制器實作
```cpp
void MyEquipment::set_dye_color(int p_slot, Color p_color) {
    // 1. 取得 MeshInstance3D 的材質
    MeshInstance3D *mesh_inst = Object::cast_to<MeshInstance3D>(get_node_or_null("Mesh"));
    if (!mesh_inst) return;

    // 2. 確保是 ShaderMaterial 並獲取唯一實例 (避免影響其他同類裝備)
    Ref<ShaderMaterial> mat = mesh_inst->get_surface_override_material(0);
    if (mat.is_null()) {
        // 若尚未覆蓋，則建立或複製
        mat = mesh_inst->get_active_material(0)->duplicate();
        mesh_inst->set_surface_override_material(0, mat);
    }

    // 3. 根據插槽設定參數
    String param_name = "dye_color_" + itos(p_slot + 1);
    mat->set_shader_parameter(param_name, p_color);
}
```

## 4. 實務提示
- **材質唯一化**：務必呼叫 `duplicate()`，否則修改一個玩家的裝備顏色會導致全伺服器穿同樣衣服的 NPC 全部變色。
- **效能優化**：遮罩貼圖可以與法線貼圖或粗糙度貼圖合併在不同的頻道中（如法線在 RG，遮罩在 B），以減少貼圖採樣次數。
