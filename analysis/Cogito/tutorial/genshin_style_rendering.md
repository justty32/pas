# 教學：實作「原神風格」渲染（Anime / Cel-Shading）

原神風格的核心是 **Cel-Shading（三渲二）**、**描邊（Outline）**、**Rim Light（邊緣光）** 與**風格化環境**。本教學提供可直接在 Godot 4 使用的完整 Shader 代碼。

## 前置知識
- 已閱讀 [教學：畫面表現設定](./visual_presentation_and_rendering.md)。
- 了解 Godot 4 ShaderMaterial 的基本操作。

---

## 一、三渲二材質（Toon Shader）

建立 `res://shaders/toon_character.gdshader`：

```glsl
// res://shaders/toon_character.gdshader
shader_type spatial;
render_mode unshaded;  // 關閉預設 PBR 光照，完全自訂

uniform sampler2D albedo_texture : source_color;
uniform vec4 albedo_color : source_color = vec4(1.0);

// 明暗分界：0.5 = 水平切割；調高讓亮部更多
uniform float shadow_threshold : hint_range(0.0, 1.0) = 0.5;
// 分界線柔化程度：0 = 完全銳利，0.1 = 稍微柔化
uniform float shadow_smoothness : hint_range(0.0, 0.2) = 0.02;
// 暗部顏色
uniform vec4 shadow_color : source_color = vec4(0.3, 0.3, 0.4, 1.0);

// Rim Light 參數
uniform float rim_power : hint_range(0.5, 8.0) = 3.0;
uniform float rim_strength : hint_range(0.0, 1.0) = 0.4;
uniform vec4 rim_color : source_color = vec4(0.8, 0.9, 1.0, 1.0);


void fragment() {
    vec4 tex = texture(albedo_texture, UV) * albedo_color;
    ALBEDO = tex.rgb;
    ALPHA = tex.a;
}


void light() {
    // 計算漫反射（dot product of normal and light direction）
    float NdotL = dot(NORMAL, LIGHT);

    // 將連續漫反射值轉為銳利的 0/1 色階（smoothstep 提供可調柔化）
    float ramp = smoothstep(
        shadow_threshold - shadow_smoothness,
        shadow_threshold + shadow_smoothness,
        NdotL
    );

    // 混合亮部/暗部顏色
    vec3 diffuse = mix(shadow_color.rgb, vec3(1.0), ramp);

    // Rim Light（邊緣光）：基於視角方向與法線的夾角
    float rim = 1.0 - clamp(dot(normalize(VIEW), NORMAL), 0.0, 1.0);
    rim = pow(rim, rim_power) * rim_strength;
    vec3 rim_contribution = rim_color.rgb * rim * LIGHT_COLOR * ATTENUATION;

    // 最終輸出
    DIFFUSE_LIGHT += ALBEDO * diffuse * LIGHT_COLOR * ATTENUATION + rim_contribution;
    SPECULAR_LIGHT = vec3(0.0);  // 關閉 PBR 高光
}
```

**套用方式**：
1. 選取角色的 `MeshInstance3D`。
2. Material → 新建 `ShaderMaterial` → Shader 指向上方的 `.gdshader` 檔案。
3. 設定 `albedo_texture` 為角色的底色貼圖，`albedo_color` 為整體色調。

---

## 二、描邊（Backface Expansion Outline）

建立 `res://shaders/toon_outline.gdshader`：

```glsl
// res://shaders/toon_outline.gdshader
shader_type spatial;
render_mode cull_front, unshaded;  // 只渲染背面

uniform float outline_width : hint_range(0.0, 0.05) = 0.003;
uniform vec4 outline_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
// 距離縮放：讓遠處描邊保持視覺粗細一致
uniform bool use_distance_scale : hint_default_true;


void vertex() {
    vec3 normal_clip = normalize(
        (PROJECTION_MATRIX * vec4(NORMAL, 0.0)).xyz
    );

    float width = outline_width;
    if (use_distance_scale) {
        // 根據距離縮放描邊寬度（使遠近視覺粗細一致）
        float clip_depth = (PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).w;
        width *= clip_depth;
    }

    POSITION = PROJECTION_MATRIX * MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
    POSITION.xy += normal_clip * width;
}


void fragment() {
    ALBEDO = outline_color.rgb;
    ALPHA = outline_color.a;
}
```

**套用到 Next Pass**：
1. 選取角色 `MeshInstance3D`。
2. Material → 最底下找到 `Next Pass` → 新建 `ShaderMaterial`。
3. 指向 `toon_outline.gdshader`。

`render_mode cull_front` 讓描邊 Shader 只渲染背面，配合主材質的正面渲染，形成黑色外框效果。

---

## 三、SDF 面部陰影（進階）

原神的面部陰影不使用一般燈光，而是使用一張 SDF 貼圖控制陰影形狀，確保在任何角度都美觀。這需要在 3D 工具中手動繪製 SDF 貼圖，此為進階技術；基礎實作可跳過此部分，用 Toon Shader 的 `shadow_threshold` 替代。

---

## 四、風格化環境設定

### WorldEnvironment 設定
```
WorldEnvironment
└── Environment 資源：
    ├── Background
    │   ├── Mode: Sky
    │   └── Sky: ProceduralSkyMaterial
    │       ├── Sky Top Color: (0.15, 0.4, 0.9)    # 鮮艷天藍
    │       ├── Sky Horizon Color: (0.7, 0.85, 1.0) # 淺藍地平線
    │       └── Ground Bottom Color: (0.3, 0.25, 0.2)
    ├── Tonemap: Mode = Linear（保持色彩飽和）
    ├── Glow: Enabled（讓發光材質有光暈效果）
    │   ├── Intensity = 0.5
    │   └── Bloom: 0.1（輕微泛光）
    └── SSAO: Disabled（風格化不需要環境光遮蔽）
```

### 風格化草地 Shader（Wind Sway）

建立 `res://shaders/stylized_grass.gdshader`：

```glsl
// res://shaders/stylized_grass.gdshader
shader_type spatial;
render_mode cull_disabled;  // 雙面渲染

uniform sampler2D grass_texture : source_color;
uniform float wind_strength : hint_range(0.0, 1.0) = 0.15;
uniform float wind_speed : hint_range(0.0, 5.0) = 1.5;
// 坡度顏色偏移（山坡處偏深綠）
uniform float slope_color_influence : hint_range(0.0, 1.0) = 0.3;


void vertex() {
    // 只讓草葉頂部搖擺（UV.y 越高，擺動越大）
    float sway = sin(TIME * wind_speed + VERTEX.x * 2.0 + VERTEX.z * 1.5);
    VERTEX.x += sway * wind_strength * UV.y;
    VERTEX.z += sway * wind_strength * 0.5 * UV.y;
}


void fragment() {
    vec4 tex = texture(grass_texture, UV);
    // 使用法線 Y 分量判斷是否為坡面（Y 越小 = 越陡）
    float slope = 1.0 - NORMAL.y;
    vec3 slope_tint = vec3(0.05, 0.15, 0.05);  # 偏深綠色
    ALBEDO = mix(tex.rgb, tex.rgb - slope_tint, slope * slope_color_influence);
    ALPHA = tex.a;
}
```

---

## 五、渲染選項建議

| 設定 | 建議值 | 說明 |
|---|---|---|
| `SSAO` | 關閉 | 風格化不需要真實遮蔽 |
| `SSIL` | 關閉 | 同上 |
| `MSAA` | 4x | 二次元風格對鋸齒敏感 |
| `Tonemapping` | Linear | 保持色彩飽和 |
| `Glow` | 開啟（輕微）| 讓發光材質有光暈 |
| `Depth of Field` | 關閉或輕微 | 過深景深與動漫風格不搭 |

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 角色旋轉至光源背面 | 陰影銳利切換（不是漸層），符合 `shadow_threshold` 設定 |
| 角色邊緣 | 黑色描邊清晰可見（背面擴張法）|
| 遠處角色描邊 | 視覺粗細與近處大致相同（use_distance_scale 生效）|
| 角色邊緣有光照時 | Rim Light 讓邊緣略微發光（淡藍色）|
| 草地場景 | 草葉輕微搖擺，山坡處顏色偏深 |
| 天空 | 鮮艷的動漫藍天，無過度真實感 |
