# 通用 Sprite 素材複用系統

## 核心問題

傳統做法：每個物件變體出一張貼圖（鐵劍、鋼劍、紫晶劍各一張）。
問題：貼圖數量爆炸，品質維護成本高，無法動態生成變體。

**目標**：用「基底形狀 + 材質疊加層」取代一對一貼圖。

---

## 概念模型

```
最終顯示 = Base Texture（形狀 + UV）
          × Material Layer（顏色/材質特性）
          + Detail Layer（可選：磨損、紋章、特效）
```

**範例**：
- 鐵劍 = 劍型基底 + 灰色金屬材質
- 紫晶劍 = 劍型基底 + 紫色晶體材質 + 微光 detail
- 精英哥布林 = 哥布林基底 + 深綠皮膚材質 + 頭盔 detail
- 草地tile + 乾旱疊加 → 枯草tile

---

## Shader 實作方案（Godot 2D）

### 最簡版：單材質疊加

```glsl
// sprite_material.gdshader
shader_type canvas_item;

uniform sampler2D material_tex : hint_default_white;
uniform float material_strength : hint_range(0.0, 1.0) = 1.0;
uniform int blend_mode = 0;  // 0=Multiply, 1=Additive, 2=Screen

void fragment() {
    vec4 base     = texture(TEXTURE, UV);           // 基底（Sprite2D.texture）
    vec4 material = texture(material_tex, UV);

    vec3 blended;
    if (blend_mode == 0) {
        // Multiply：染色，保留基底明暗
        blended = base.rgb * mix(vec3(1.0), material.rgb, material_strength * material.a);
    } else if (blend_mode == 1) {
        // Additive：發光疊加
        blended = base.rgb + material.rgb * material_strength * material.a;
    } else {
        // Screen：提亮
        blended = 1.0 - (1.0 - base.rgb) * (1.0 - material.rgb * material_strength);
    }

    COLOR = vec4(blended, base.a);
}
```

### 進階版：多材質槽

```glsl
// 例：劍刃 + 劍柄各自材質
uniform sampler2D blade_material_tex;
uniform sampler2D handle_material_tex;
uniform sampler2D region_mask_tex;  // R channel = 劍刃區, G channel = 劍柄區

void fragment() {
    vec4 base   = texture(TEXTURE, UV);
    vec4 mask   = texture(region_mask_tex, UV);
    vec4 blade  = texture(blade_material_tex, UV);
    vec4 handle = texture(handle_material_tex, UV);

    vec3 col = base.rgb;
    col = mix(col, col * blade.rgb,  mask.r);  // 劍刃區域套用 blade 材質
    col = mix(col, col * handle.rgb, mask.g);  // 劍柄區域套用 handle 材質

    COLOR = vec4(col, base.a);
}
```

### GDScript 換裝

```gdscript
func apply_material(sprite: Sprite2D, mat_tex: Texture2D,
                    strength: float = 1.0, mode: int = 0) -> void:
    if not sprite.material:
        sprite.material = ShaderMaterial.new()
        sprite.material.shader = preload("res://shaders/sprite_material.gdshader")
    sprite.material.set_shader_parameter("material_tex", mat_tex)
    sprite.material.set_shader_parameter("material_strength", strength)
    sprite.material.set_shader_parameter("blend_mode", mode)
```

---

## 適用範疇

| 物件類型 | 基底 | 材質層 | 備註 |
|---------|------|-------|------|
| 武器 | 武器形狀 | 材質類型（金屬/晶體/骨骼） | 多槽版可分刃/柄 |
| 護甲 | 護甲輪廓 | 材質 + 稀有度色調 | |
| 建築 | 建築結構 | 時代/文化材質（木/石/大理石） | |
| 角色皮膚 | 角色底圖 | 種族/狀態膚色 | |
| Tile 基底 | 地形形狀 | 生態圈疊加（沙漠/凍原/... ） | 見 world_map |
| Tile 地物 | 植被/岩石形狀 | 季節/氣候材質 | |

---

## 與其他系統的關係

- **紙娃娃系統**（`../godot_character/`）：裝備槽 Sprite2D 直接掛此 shader
- **世界地圖**（`../godot_world_map/`）：TileMapLayer 的 tile shader 用同樣原理
- **素材管線**：基底 texture 由美術出圖，材質 texture 可程序生成（純色、漸層、噪聲）

---

## Tilemap 特殊考量

TileMapLayer 的 shader 無法直接針對個別 tile 傳不同 uniform。解法：

1. **Texture Array**：把所有材質打包成 Texture2DArray，tile 的 custom_data 儲存材質 index，shader 內 index 採樣
2. **頂點色 (vertex color)**：用 tile 的 modulate 傳遞粗略色調（精度有限）
3. **分層 TileMapLayer**：不同材質各一層（見 world_map CONCEPT）

方案 1（Texture2DArray + custom_data）是最通用的，但實作較複雜。

---

## 待決定

- [ ] 材質 texture 是藝術家繪製 or 程序生成（噪聲 + 色相旋轉）
- [ ] 稀有度色調是材質 texture 的一部分 or 額外 uniform（`rarity_tint: Color`）
- [ ] Tilemap 走哪個方案（Texture2DArray vs 分層）

---

*記錄時間：2026-05-22*
