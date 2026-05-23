# 2D 通用 Sprite 素材複用系統：基底 × 材質層 + 細節層

## 目標

用「基底形狀 + 材質疊加層」取代「一物件一貼圖」，解決貼圖數量爆炸：

- 一張灰階「基底形狀」貼圖（劍型 / 護甲輪廓 / tile 地形形狀），透過 `canvas_item` shader 疊加材質層，呈現鐵 / 鋼 / 紫晶等變體。
- **N 種形狀 × M 種材質 = N×M 種外觀，但貼圖只需 N+M 張**。
- 多區域材質（劍刃 + 劍柄各自上色）用 region mask 一次處理。
- 材質貼圖可由 [[gdextension_procgen_art]] 程序生成（純色 / 漸層 / 噪聲），美術只需出基底形狀。

本文是 [[gdextension_character_2d]] 引用之 `sprite_material.gdshader` 的權威規格，也是 [[gdextension_world_map_2d]] tile 著色與 [[gdextension_2d_dyeing_system]] 染色的上位整合。

概念來源：`others/godot/godot_material/CONCEPT.md`。

---

## 概念模型

```
最終顯示 = Base Texture（形狀 + UV，灰階）
          × Material Layer（顏色 / 材質特性）        ← multiply 染色，保留基底明暗
          + Detail Layer（可選：磨損 / 紋章 / 微光）  ← additive / screen 疊加
          ± Rarity Tint（稀有度色調，正交 uniform）   ← 與材質無關，可任意組合
```

範例：鐵劍＝劍型基底 × 灰金屬材質；紫晶劍＝劍型基底 × 紫晶材質 + 微光 detail；草地 tile + 乾旱疊加 → 枯草 tile。

---

## 核心設計

- **基底貼圖只存「形狀 + 明暗」**：用灰階繪製（或程序生成），明暗資訊在 multiply 時保留立體感，色相完全交給材質層。
- **材質層是低頻資訊**：純色 / 漸層 / 噪聲即可，最適合程序生成（見 [[gdextension_procgen_art]]），所以材質「貼圖」往往不是貼圖而是參數。
- **稀有度與材質正交**：做成獨立 uniform，避免「鋼劍普通 / 鋼劍稀有」要各出一張材質圖。
- **shader 集中一支**：所有可染物件共用 `sprite_material.gdshader`，差異全在 `ShaderMaterial` 的 uniform；同材質的多個 Sprite 共用同一個 `ShaderMaterial` 實例以省 uniform 上傳。

---

## 原始碼位置

引擎類別 API 以 `projects/godot-cpp/gdextension/extension_api.json`（Godot Engine v4.6.stable.official）為準。

- 概念來源：`others/godot/godot_material/CONCEPT.md`
- 消費端：[[gdextension_character_2d]]（裝備槽 Sprite2D 掛此 shader）、[[gdextension_world_map_2d]]（tile 著色）
- 材質貼圖生成：[[gdextension_procgen_art]]（程序生成純色 / 漸層 / 噪聲材質）
- 染色 shader 參照：[[gdextension_2d_dyeing_system]]（局部染色，可視為本系統的子集）
- 3D 對應與快取思路：[[gdextension_material_3d]]（MaterialLibrary 快取，`others/gamecore/mapcore_godot/demo/scenes/material_library.gd`）
- 引擎核心類別（皆來自 extension_api.json）：
  - `ShaderMaterial`（inherits `Material`）：`set_shader(Shader)` / `set_shader_parameter(StringName, Variant)` / `get_shader_parameter(StringName)`
  - `CanvasItem`（Sprite2D 祖先）：`set_material(Material)` / `set_self_modulate(Color)`
  - `Sprite2D`：`set_texture(Texture2D)`
  - `Texture2DArray`（inherits `ImageTextureLayered`）：`create_from_images(Array[Image])`；shader 內以 `sampler2DArray` + 層索引採樣
  - `TileMapLayer`（inherits `Node2D`）：`get_cell_tile_data(Vector2i) -> TileData`；`TileData.get_custom_data(String)` 讀逐 tile 自訂資料
  - `Image` / `ImageTexture`：程序生成材質貼圖時使用（見 [[gdextension_procgen_art]]）

---

## 實作細節

### 1. 最簡版：單材質疊加 shader（權威規格）

```glsl
// sprite_material.gdshader  — character_2d / world_map 共用
shader_type canvas_item;

uniform sampler2D material_tex : hint_default_white;
uniform float material_strength : hint_range(0.0, 1.0) = 1.0;
uniform int   blend_mode = 0;            // 0=Multiply, 1=Additive, 2=Screen
uniform vec4  rarity_tint : source_color = vec4(1.0);   // 正交：稀有度色調

void fragment() {
    vec4 base     = texture(TEXTURE, UV);          // 基底（Sprite2D.texture，灰階形狀）
    vec4 material = texture(material_tex, UV);

    vec3 c;
    if (blend_mode == 0) {                          // Multiply：染色，保留明暗
        c = base.rgb * mix(vec3(1.0), material.rgb, material_strength * material.a);
    } else if (blend_mode == 1) {                   // Additive：發光疊加
        c = base.rgb + material.rgb * material_strength * material.a;
    } else {                                        // Screen：提亮
        c = 1.0 - (1.0 - base.rgb) * (1.0 - material.rgb * material_strength);
    }
    c *= rarity_tint.rgb;                            // 稀有度色調（與材質正交）
    COLOR = vec4(c, base.a);
}
```

### 2. 進階版：多材質槽（region mask 分區）

`TileMapLayer` / 單 Sprite 都可用 R/G channel 遮罩把不同區域套不同材質（劍刃 vs 劍柄）：

```glsl
// 例：劍刃 + 劍柄各自材質
uniform sampler2D blade_material_tex;
uniform sampler2D handle_material_tex;
uniform sampler2D region_mask_tex;       // R=劍刃區, G=劍柄區

void fragment() {
    vec3 col   = texture(TEXTURE, UV).rgb;
    vec4 mask  = texture(region_mask_tex, UV);
    col = mix(col, col * texture(blade_material_tex,  UV).rgb, mask.r);
    col = mix(col, col * texture(handle_material_tex, UV).rgb, mask.g);
    COLOR = vec4(col, texture(TEXTURE, UV).a);
}
```

### 3. GDScript：MaterialLibrary2D（換裝 + 共用實例快取）

把同材質的 `ShaderMaterial` 快取共用，避免每個 Sprite 各建一份：

```gdscript
# material_library_2d.gd — 靜態工廠 + 快取（對齊 material_3d 的 MaterialLibrary 思路）
extends RefCounted
class_name MaterialLibrary2D

const SHADER := preload("res://shaders/sprite_material.gdshader")
static var _cache := {}                   # key: "mat_path|mode|strength" → ShaderMaterial

static func get_material(mat_tex: Texture2D, mode := 0, strength := 1.0,
                         rarity := Color.WHITE) -> ShaderMaterial:
    var key := "%s|%d|%.2f|%s" % [mat_tex.resource_path, mode, strength, rarity.to_html()]
    if _cache.has(key):
        return _cache[key]
    var m := ShaderMaterial.new()
    m.shader = SHADER
    m.set_shader_parameter("material_tex", mat_tex)        # ShaderMaterial.set_shader_parameter
    m.set_shader_parameter("blend_mode", mode)
    m.set_shader_parameter("material_strength", strength)
    m.set_shader_parameter("rarity_tint", rarity)
    _cache[key] = m
    return m
```

換裝端（[[gdextension_character_2d]]）只需：

```gdscript
sprite.texture  = base_tex                                   # 形狀：灰階基底
sprite.material = MaterialLibrary2D.get_material(steel_tex, 0, 1.0, RARITY[quality])
```

---

## GDScript 使用範例

```gdscript
# N 種形狀 × M 種材質，貼圖只需 N+M 張
var blade  := preload("res://art/weapons/sword_base.png")     # 形狀
var steel  := preload("res://art/materials/steel.png")        # 材質
var crystal:= preload("res://art/materials/amethyst.png")     # 材質

# 同一把劍 → 鋼劍 / 紫晶傳奇劍
sword_a.texture = blade; sword_a.material = MaterialLibrary2D.get_material(steel,   0)
sword_b.texture = blade; sword_b.material = MaterialLibrary2D.get_material(crystal, 0, 1.0,
                                                Color(1.0, 0.84, 0.0))  # 傳奇金 rarity_tint
```

---

## 適用範疇

| 物件類型 | 基底 | 材質層 | 備註 |
|---------|------|-------|------|
| 武器 | 武器形狀 | 金屬 / 晶體 / 骨骼 | 多槽版可分刃 / 柄（region mask）|
| 護甲 | 護甲輪廓 | 材質 + 稀有度色調 | rarity 用獨立 uniform |
| 建築 | 建築結構 | 時代 / 文化材質（木 / 石 / 大理石）| |
| 角色皮膚 | 角色底圖 | 種族 / 狀態膚色 | 接 [[gdextension_character_2d]] |
| Tile 基底 | 地形形狀 | 生態圈疊加（沙漠 / 凍原）| 接 [[gdextension_world_map_2d]] |

---

## Tilemap 特殊考量

`TileMapLayer` 的 shader **無法逐個 tile 傳不同 uniform**，三條路：

1. **Texture2DArray + custom_data（推薦正式路線）**：所有材質打包成 `Texture2DArray`，tile 的 `TileData.get_custom_data("material_id")` 存材質層索引，shader 內以 `sampler2DArray` 按索引採樣混合。一個 draw call、混合自然。
2. **頂點色 / modulate**：用 tile 的 `modulate` 傳粗略色調，精度有限，僅適合大塊染色。
3. **分層 TileMapLayer**：不同材質各一層疊加（對齊 godot_world_map CONCEPT 的「方向一」），最簡單但 draw call 多、混合受 alpha 限制。

---

## 效能 / 已知限制

- **ShaderMaterial 實例數**：每個獨立 `ShaderMaterial` 都有 uniform 上傳成本；務必用 `MaterialLibrary2D` 快取讓「同材質同參數」共用一份實例。
- **TileMap 整合複雜度**：方案 1（Texture2DArray）通用但需打包貼圖陣列與設 `TileData` custom_data，實作較重；prototype 期可先走方案 3。
- **基底貼圖規範**：基底必須是「灰階 + 中性明度」才能正確被 multiply 染色；若基底已帶強烈色相，染色會偏色。
- **材質「貼圖」常可省**：純色 / 漸層材質直接用 1×1 或小尺寸程序貼圖（[[gdextension_procgen_art]]）即可，不必占用美術出圖。

---

## 待決定

逐項回應 `others/godot/godot_material/CONCEPT.md` 的待決定清單：

- **材質 texture 是藝術家繪製 or 程序生成？**
  - **建議：以程序生成為主（[[gdextension_procgen_art]] 出純色 / 漸層 / 噪聲），藝術家只補關鍵特例。** 理由：材質層是低頻色彩資訊，程序生成質量足夠且零美術成本，與本系統「組合不爆增」初衷及 procgen_art 管線天然銜接；只有少數需要精緻紋理（如特定徽記、招牌神兵）才交美術。

- **稀有度色調是材質 texture 的一部分 or 額外 uniform？**
  - **建議：獨立 uniform `rarity_tint: Color`（必要時加 emission / 微光 detail），不要烤進材質貼圖。** 理由：稀有度與材質正交——同一把鋼劍可普通 / 稀有 / 傳奇；做成 uniform 才能 N 材質 × M 稀有度自由組合而不增貼圖，且能執行期動態調整（升階變色）。本文 `sprite_material.gdshader` 已內建 `rarity_tint` uniform。

- **Tilemap 走哪個方案（Texture2DArray vs 分層）？**
  - **建議：正式製作走 Texture2DArray + custom_data（方案 1）；prototype 期先用分層 TileMapLayer（方案 3）。** 理由：方案 1 對齊 godot_world_map CONCEPT 的「方向二（shader 混合單層）」，一個 draw call、混合最自然、最省效能；分層方案上手快但 draw call 隨層數增、混合受 alpha 限制。先用分層驗證視覺，定案後換 Texture2DArray。

---

*記錄時間：2026-05-23*
*狀態：概念補完為實作教學；API 對齊 Godot v4.6.stable（extension_api.json）；本文為 `sprite_material.gdshader` 權威規格，被 [[gdextension_character_2d]] 引用，上承 [[gdextension_procgen_art]]*
