# 草地 Shader 深入分析（grass.gdshader）

## 渲染設定

```glsl
shader_type spatial;
render_mode cull_disabled;   // 雙面渲染，草葉正反都可見
```

---

## Uniform 參數（可在編輯器調整）

| 參數 | 類型 | 預設值 | 用途 |
|------|------|--------|------|
| `color_top` | vec4 | 白色 | 草葉頂端顏色 |
| `color_bottom` | vec4 | 黑色 | 草葉底部顏色 |
| `deg_sway_pitch` | float | 80.0° | 前後搖擺最大角度 |
| `deg_sway_yaw` | float | 45.0° | 左右搖擺最大角度 |
| `wind_scale` | float | 4.0 | Worley 噪聲採樣縮放（越小風場越大） |
| `wind_speed` | float | 1.0 | 風的流動速度 |
| `wind_direction` | vec3 | (0,0,-1) | 風向（世界座標） |

---

## INSTANCE_CUSTOM 通道（來自 Planter.gd）

MultiMesh 的每個草葉實例透過 `set_instance_custom_data()` 傳入 Color（rgba=4個float）：

```gdscript
# planter.gd:39-44
multimesh.set_instance_custom_data(index, Color(
    randf_range(width.x, width.y),   # R → INSTANCE_CUSTOM.x = 寬度縮放
    randf_range(height.x, height.y), # G → INSTANCE_CUSTOM.y = 高度縮放
    deg_to_rad(randf_range(...)),     # B → INSTANCE_CUSTOM.z = pitch 偏移
    deg_to_rad(randf_range(...))      # A → INSTANCE_CUSTOM.w = yaw 偏移
))
```

Shader 中讀取（vertex()）：
```glsl
vertex.xy *= INSTANCE_CUSTOM.x;   // 縮放寬度（x,y分量）
vertex.y  *= INSTANCE_CUSTOM.y;   // 縮放高度（只影響y）

float sway_pitch = ... + INSTANCE_CUSTOM.z;  // 加入個體靜止偏移
float sway_yaw   = ... + INSTANCE_CUSTOM.w;  // 每株草的基礎傾斜不同
```

**效果**：1000株草各有不同的寬高比例與靜止姿態，避免機械式重複感。

---

## Worley 噪聲風場

```glsl
// 2D Worley（細胞噪聲）計算
float worley2(vec2 p) {
    float dist = 1.0;
    vec2 i_p = floor(p);
    vec2 f_p = fract(p);
    // 遍歷 3x3 鄰格，取最近細胞點距離
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 n = vec2(float(x), float(y));
            vec2 diff = n + random2(i_p + n) - f_p;
            dist = min(dist, length(diff));
        }
    }
    return dist;
}
```

**Worley 噪聲特性**：產生「泡泡狀」紋路，模擬風以陣風形式吹過草地的自然感（而非均勻搖擺）。

採樣方式：
```glsl
float time = TIME * wind_speed;
vec2 uv = (MODEL_MATRIX * vec4(vertex, -1.0)).xz * wind_scale;
uv += wind_direction_normalized.xz * time;   // UV 隨時間移動 = 風場流動
wind = pow(worley2(uv), 2.0) * UV2.y;        // 平方增強對比，乘高度使底部不搖
```

- `UV2.y`：草葉網格的第二 UV 通道（從 GrassFactory 設定）= 頂點在草葉上的高度比例（底部=0, 頂部=1）
- 底部 `UV2.y=0` → `wind=0`，根部固定不動
- 頂部 `UV2.y=1` → wind 值最大，頂端搖擺最劇烈

---

## 旋轉計算（Vertex Shader）

```glsl
// 從世界空間風向轉換到模型空間
mat3 to_model = inverse(mat3(MODEL_MATRIX));
vec3 wind_forward = to_model * wind_direction_normalized;
vec3 wind_right = normalize(cross(wind_forward, UP));   // 垂直於風向的水平軸

// 計算兩個搖擺角度
float sway_pitch = (deg_sway_pitch * DEG2RAD * wind) + INSTANCE_CUSTOM.z;
float sway_yaw   = (deg_sway_yaw   * DEG2RAD * sin(time) * wind) + INSTANCE_CUSTOM.w;
//                                            ↑ sin(time) 使 yaw 來回搖擺

// 建立旋轉矩陣（Rodrigues 公式）
mat3 rot_right   = mat3_from_axis_angle(sway_pitch, wind_right);   // 前後彎
mat3 rot_forward = mat3_from_axis_angle(sway_yaw,   wind_forward); // 左右搖

// 先縮放，再旋轉
vertex.xy *= INSTANCE_CUSTOM.x;   // 寬度
vertex.y  *= INSTANCE_CUSTOM.y;   // 高度
VERTEX = rot_right * rot_forward * vertex;
```

**旋轉順序**：先 rot_forward（yaw）再 rot_right（pitch），確保彎曲方向與風向一致。

---

## Fragment Shader

```glsl
void fragment() {
    float side = FRONT_FACING ? 1.0 : -1.0;
    NORMAL = NORMAL * side;       // 雙面渲染時法線翻轉，確保背面也有正確光照
    ALBEDO = COLOR.rgb;           // 從 vertex COLOR 取顏色（上下漸層）
    SPECULAR = 0.5;               // 固定高光
    ROUGHNESS = clamp(1.0 - (wind * 2.0), 0.0, 1.0);  // 風大 = 草葉更光滑
}
```

**動態 ROUGHNESS 效果**：
- 無風（wind≈0）→ ROUGHNESS≈1（粗糙，無高光）
- 強風（wind≈0.5+）→ ROUGHNESS≈0（光滑，閃光感）
- 視覺上：強風吹過時草地會出現光澤閃爍，模擬草葉被風壓平的光反射

---

## 顏色漸層

```glsl
// Vertex Shader 末尾
COLOR = mix(color_bottom, color_top, UV2.y);
// UV2.y=0（根部）= color_bottom（深色）
// UV2.y=1（頂部）= color_top（亮色）
```

結合 Fragment 的 `ALBEDO = COLOR.rgb`，草葉底部深、頂部亮，符合自然光照規律。

---

## 效能分析

| 面向 | 說明 |
|------|------|
| Draw Call | 1000 株草 = 1 次 Draw Call（MultiMeshInstance3D） |
| 每草頂點 | 3 個（三角形），極低幾何複雜度 |
| GPU 計算 | Worley 噪聲在 VS 中計算（9次 random2 per 草葉） |
| CPU 負擔 | Planter 只在初始化執行一次，運行時零 CPU 開銷 |
| 可見性 | custom_aabb 手動設定，確保視錐剪裁正確 |

---

## 草地材質（grass_material.tres）

```
[node name="Grass" type="MultiMeshInstance3D"]
    ← 使用 grass_material.tres 覆蓋網格材質
    ← 材質中指定此 gdshader 為 shader
    ← 暴露 uniform 讓編輯器可調整顏色與風力參數
```

實際顏色在 grass_material.tres 中設定（非 Shader 預設值），允許場景設計師調整草地外觀。
