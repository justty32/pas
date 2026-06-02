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

---

## 深化補充

### 1. TIME 溢出問題分析

`grass.gdshader:62`：
```glsl
float time = TIME * wind_speed;
```

**TIME 的型別與精度**：Godot Shader 中 `TIME` 是 `float`（32 位元單精度浮點數），在所有平台一致（Godot 4 Shading Language 規格）。

IEEE 754 float32 可精確表示到的整數上限為 **2²⁴ = 16,777,216**（約 1677 萬），超過後相鄰浮點數間距 > 1.0，TIME 每秒遞增量無法被精確表示。

計算跳躍點：
- `wind_speed = 1.0`（預設值）時，TIME 本身即為秒數
- 精度喪失點：約 **16,777,216 秒 ≈ 194 天**
- `wind_speed = 4.0`（最大合理值）時，`time = TIME * 4`，但 TIME 本身在 194 天後已失精，乘 4 不改善精度
- 實際遊戲場景下，單次遊戲執行幾乎不會超過數小時，**194 天的精度邊界不構成實際問題**

但需注意：`uv += wind_direction_normalized.xz * time` 中，若 TIME 非常大，`uv` 的值也很大，`floor(p)` 與 `fract(p)` 仍能正常分離整數與小數部分（GLSL `fract` 的行為），**Worley 噪聲本身不受 TIME 溢出影響**，因為它依賴 `fract(p)` 而非 `p` 的絕對值。真正的視覺跳躍風險極低。

**sway_yaw 的正弦問題**（`grass.gdshader:72`）：
```glsl
float sway_yaw = (deg_sway_yaw * DEG2RAD * sin(time) * wind) + INSTANCE_CUSTOM.w;
```
`sin(time)` 在 time 極大時精度問題更嚴重：float 的三角函數對大數值的精度約在 `time > 2^13`（約 8192 秒 ≈ 2.3 小時）後開始衰退，這才是真正可能的問題點。

---

### 2. Worley 噪聲計算成本分析

每株草的 `vertex()` 呼叫路徑（`grass.gdshader:44-56, 65`）：

```glsl
// worley2() 內部：9 次 random2() 調用
for (int y = -1; y <= 1; y++) {      // 3 次
    for (int x = -1; x <= 1; x++) {  // × 3 = 9 次
        vec2 diff = n + random2(i_p + n) - f_p;
    }
}
wind = pow(worley2(uv), 2.0) * UV2.y;
```

每次 `random2()` 包含 2 個 `dot()` + 2 個 `sin()` + `fract()`（`grass.gdshader:38-42`）：
```glsl
vec2 random2(vec2 p) {
    return fract(sin(vec2(
        dot(p, vec2(127.32, 231.4)),
        dot(p, vec2(12.3, 146.3))
    )) * 231.23);
}
```

**計算量估算（count=1000, 每頂點 3 個）**：

| 層次 | 數量 |
|------|------|
| 草株數 | 1000 |
| 每草頂點數 | 3（三角形） |
| 每頂點 worley2() 呼叫 | 1 |
| 每 worley2() 的 random2() | 9 |
| 每 random2() 的 sin() 呼叫 | 2 |
| **總 sin() 呼叫 / 幀** | **1000 × 3 × 9 × 2 = 54,000** |

GPU 的 `sin()` 是硬體指令，54,000 次在現代 GPU 上通常在單一 batch 內完成，實際瓶頸不在此。然而 MultiMesh 本身的 vertex shader 吞吐量限制更可能成為瓶頸（1000 × 3 = 3000 個 VS invocation）。

**優化方向**：

- **BlueNoise texture**：預計算 128×128 的 Worley 噪聲貼圖，vertex shader 改為 `texture(noise_tex, uv)` 一次採樣，消除全部 sin() 呼叫
- **限制 instance 數**：`worley2()` 的代價主要在 sin()，若效能不足可降低 `count`（planter.gd:10）
- **降低頂點數**：目前每草 3 頂點（三角形），若改為 2 頂點（四邊形裁切）反而頂點更多，三角形已是最低幾何

---

### 3. wind_direction 歸一化缺失分析

`grass.gdshader:61`：
```glsl
vec3 wind_direction_normalized = normalize(wind_direction);
```

**傳入 (0,0,0) 的行為**：`normalize(vec3(0,0,0))` 在 GLSL 的結果是**未定義行為**（undefined behavior），實際上多數 GPU 驅動回傳 `(0,0,NaN)` 或 `(NaN,NaN,NaN)`。

後續影響：
- `uv += wind_direction_normalized.xz * time` → NaN 傳入 `worley2()`
- `wind = pow(worley2(uv), 2.0) * UV2.y` → NaN
- `sway_pitch = (...) + INSTANCE_CUSTOM.z` → NaN
- `VERTEX = rot_right * rot_forward * vertex` → 頂點變成 NaN → 草葉消失或產生黑色 artifact

**目前 GDScript 側的保護**：`planter.gd` 完全不處理 `wind_direction`（planter.gd:1-74 均未見相關代碼），`wind_direction` 只透過 Material uniform 設定，**沒有任何 GDScript 側的零向量保護**。

預設值 `vec3(0,0,-1)`（`grass.gdshader:20`）在預設狀態下不會觸發此問題，但若編輯器中 uniform 被手動設為 (0,0,0) 則會出現視覺 bug。

**建議修正方式**：
```glsl
// 在 vertex() 開頭加入保護
vec3 wd = wind_direction;
if (dot(wd, wd) < 0.0001) wd = vec3(0, 0, -1);
vec3 wind_direction_normalized = normalize(wd);
```

---

### 4. UV2.y 高度加權的設定方式（GrassFactory 原始碼核對）

`grass_factory.gd:9-31` 建立三角形網格：

```gdscript
# grass_factory.gd:13-25
verts.push_back(Vector3(-0.5, 0.0, 0.0))   # 左底
uvs.push_back(Vector2(0.0, 0.0))            # UV2 = (0, 0) → y=0 根部

verts.push_back(Vector3(0.5, 0.0, 0.0))    # 右底
uvs.push_back(Vector2(0.0, 0.0))            # UV2 = (0, 0) → y=0 根部

verts.push_back(Vector3(0.0, 1.0, 0.0))    # 頂點
uvs.push_back(Vector2(1.0, 1.0))            # UV2 = (1, 1) → y=1 頂部
```

`grass_factory.gd:22-25`：
```gdscript
arrays[Mesh.ARRAY_VERTEX] = verts
arrays[Mesh.ARRAY_TEX_UV2] = uvs    # 直接寫入 UV2 通道
```

**UV2.y 的對應確認**：
- 底部兩個頂點：`UV2 = (0.0, 0.0)` → `UV2.y = 0` → `wind = pow(...) * 0 = 0`，根部完全不搖
- 頂點：`UV2 = (1.0, 1.0)` → `UV2.y = 1` → `wind = pow(worley2(uv), 2.0) * 1`，頂端最大搖擺
- 顏色漸層：`COLOR = mix(color_bottom, color_top, UV2.y)` → 底部為 color_bottom、頂部為 color_top

**UV2.x 的使用**：shader 中只讀 `UV2.y`（`grass.gdshader:65,82`），`UV2.x` 雖然頂點設為 0 或 1，但完全未被 shader 使用。

注意 `custom_aabb = AABB(Vector3(-0.5, 0.0, -0.5), Vector3(1.0, 1.0, 1.0))`（`grass_factory.gd:29`）：這個 AABB 是**未縮放前的原始大小**，實際每株草透過 INSTANCE_CUSTOM 的 x/y 縮放後，AABB 可能不準確（草可能被過早剔除），但對極小三角形影響不大。

---

### 5. MultiMesh INSTANCE_CUSTOM 資料格式（完整對照）

**GDScript 寫入**（`planter.gd:39-44`）：

```gdscript
multimesh.set_instance_custom_data(index, Color(
    randf_range(width.x, width.y),              # R通道 → 寬度縮放因子
    randf_range(height.x, height.y),            # G通道 → 高度縮放因子
    deg_to_rad(randf_range(sway_pitch.x, sway_pitch.y)),  # B通道 → pitch 靜止偏移（弧度）
    deg_to_rad(randf_range(sway_yaw.x, sway_yaw.y))       # A通道 → yaw 靜止偏移（弧度）
))
```

`multimesh.set_custom_data_format(MultiMesh.CUSTOM_DATA_FLOAT)`（`planter.gd:31`）設定為浮點格式，確保 rgba 各通道為 float32 而非 uint8。

**Shader 讀取**（`grass.gdshader:71-80`）：

| INSTANCE_CUSTOM 通道 | Shader 讀取 | 用途 |
|---------------------|------------|------|
| `.x`（原 Color.r） | `INSTANCE_CUSTOM.x` | `vertex.xy *= INSTANCE_CUSTOM.x`：寬度縮放（x 和 y） |
| `.y`（原 Color.g） | `INSTANCE_CUSTOM.y` | `vertex.y *= INSTANCE_CUSTOM.y`：高度縮放（僅 y） |
| `.z`（原 Color.b） | `INSTANCE_CUSTOM.z` | `sway_pitch = ... + INSTANCE_CUSTOM.z`：靜止 pitch 偏移 |
| `.w`（原 Color.a） | `INSTANCE_CUSTOM.w` | `sway_yaw = ... + INSTANCE_CUSTOM.w`：靜止 yaw 偏移 |

**預設數值範圍**（`planter.gd:9-14`）：

| 參數 | 範圍 | 說明 |
|------|------|------|
| `width` | 0.01 ~ 0.02 | 每株草寬度縮放為原始網格寬（1.0 單位）的 1~2% |
| `height` | 0.04 ~ 0.08 | 高度縮放為 4~8%（極小三角形，視覺上草高約 0.04~0.08 單位） |
| `sway_pitch` | 0° ~ 10° → 0~0.175 rad | 草的靜止前傾角度 |
| `sway_yaw` | 0° ~ 10° → 0~0.175 rad | 草的靜止側傾角度 |

**縮放邏輯的微妙點**：`vertex.xy *= INSTANCE_CUSTOM.x` 同時縮放 x 和 y（但之後 `vertex.y *= INSTANCE_CUSTOM.y` 再次縮放 y），所以最終：
- `vertex.x` 縮放因子 = `INSTANCE_CUSTOM.x`
- `vertex.y` 縮放因子 = `INSTANCE_CUSTOM.x * INSTANCE_CUSTOM.y`（兩次相乘）

height 參數（y 方向）的真實縮放是 width × height 的乘積，而非單獨 height 值。以預設值計算：寬度 0.01~0.02，高度 0.04~0.08，頂點最終 y 值範圍 = 0.01×0.04 ~ 0.02×0.08 = **0.0004 ~ 0.0016 單位**（非常迷你的草）。
