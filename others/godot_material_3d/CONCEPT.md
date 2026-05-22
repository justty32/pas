# 3D 材質複用系統

## 對應 2D 版本

2D 版本（`../godot_material/`）需要自訂 shader 才能做「基底 texture × 材質疊加層」。
3D 版本的材質系統是 Godot 的原生設計，**大部分需求用 StandardMaterial3D 即可滿足**，
自訂 shader 只用在特殊效果上。

---

## 核心概念對應

| 2D 概念 | 3D 對應 |
|--------|--------|
| 基底 Texture（形狀 + UV） | 3D Mesh + UV unwrap |
| 材質疊加 shader（Multiply 染色） | StandardMaterial3D albedo tint |
| region_mask（多槽） | 多個 mesh surface，各自獨立材質 |
| 換裝替換 texture | 換裝替換 material 或 mesh |

3D 的 mesh 本身已帶有形狀，「基底形狀」不再是 texture 的工作，直接是幾何體。

---

## StandardMaterial3D 基礎用法

Low poly 遊戲通常用最簡單的設定就夠：

```gdscript
var mat = StandardMaterial3D.new()
mat.albedo_color  = Color(0.6, 0.3, 0.1)   # 棕色木頭
mat.shading_mode  = BaseMaterial3D.SHADING_MODE_UNSHADED  # 不受燈光影響（卡通感）
# 或保留燈光但用 flat shading：
mat.shading_mode  = BaseMaterial3D.SHADING_MODE_PER_PIXEL

mesh_instance.material_override = mat
```

---

## Flat Shading：Low Poly 視覺關鍵

Low poly 視覺風格靠 **per-face 純色（flat shading）** 產生：
- 每個三角面是純色，邊緣銳利，無漸層
- Godot 預設是平滑法線（Smooth Shading），需要改成 Flat

**方法 1：在 mesh 中嵌入 flat 法線**（C++ 生成 mesh 時每面獨立頂點，不共享）

```cpp
// 每個三角形 3 個獨立頂點（不 index 共享）
// 法線全部設為面法線
// → flat shading 自動正確
```

**方法 2：匯入時設定**（Blender .glb）
- Blender：選 mesh → 右鍵 → Shade Flat
- Godot import 設定：Normal → Flat

---

## 材質變體系統

### 方案 A：顏色 Tint（最簡單）

同一個 mesh，套用不同顏色 material → 不同品質/種族：

```gdscript
const WEAPON_COLORS = {
    "iron":    Color(0.6, 0.6, 0.6),
    "steel":   Color(0.8, 0.85, 0.9),
    "crystal": Color(0.6, 0.3, 0.9),
    "bone":    Color(0.9, 0.85, 0.7),
}

func set_weapon_material(type: String) -> void:
    var mat = StandardMaterial3D.new()
    mat.albedo_color = WEAPON_COLORS[type]
    mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    weapon_slot.material_override = mat
```

### 方案 B：Vertex Color 染色

把顏色資訊烘焙進 mesh 頂點色，讓 StandardMaterial3D 讀取：

```gdscript
var mat = StandardMaterial3D.new()
mat.vertex_color_use_as_albedo = true  # 直接用頂點色
mesh_instance.material_override = mat
```

C++ 生成 mesh 時，在 `ARRAY_COLOR` 通道填入顏色即可。
優點：單一 mesh 可以有多種顏色區域（刃 / 柄 / 護手各自不同色），不需要多個 surface。

### 方案 C：Texture + UV（進階）

需要更複雜的材質圖案時（金屬紋路、花紋）：

```gdscript
var mat = StandardMaterial3D.new()
mat.albedo_texture = load("res://textures/metal_iron.png")
mesh_instance.material_override = mat
```

Low poly 的 texture 可以很小（16x16 甚至 4x4 色板），程序生成也容易。

### 方案 D：ShaderMaterial（特殊效果）

需要發光、溶解、描邊等效果時才用自訂 shader：

```glsl
// 簡單發光邊緣效果
shader_type spatial;
render_mode unshaded;

uniform vec4 albedo : source_color = vec4(1.0);
uniform float rim_power = 2.0;

void fragment() {
    float rim = 1.0 - dot(NORMAL, VIEW);
    rim = pow(rim, rim_power);
    ALBEDO = albedo.rgb + vec3(rim);
}
```

---

## 多 Surface Mesh（多槽材質）

一個 mesh 可以有多個 surface，每個 surface 獨立材質——對應 2D 的 region_mask 多槽方案：

```gdscript
# 劍 mesh 有兩個 surface：[0] = 刃, [1] = 柄
sword_mesh_instance.set_surface_override_material(0, blade_material)
sword_mesh_instance.set_surface_override_material(1, handle_material)
```

Blender 中對不同部位指定不同 material slot，匯出 .glb 後自動保留。

---

## 適用範疇

| 物件類型 | mesh | 材質方案 |
|---------|------|---------|
| 武器 | 程序生成或 Blender | 顏色 tint（品質）+ multi-surface（刃/柄） |
| 護甲 | BoneAttachment3D mesh | 顏色 tint（稀有度）|
| 建築 | 程序生成幾何 | 顏色 tint（時代/文化）|
| 角色皮膚 | 基底角色 mesh | 頂點色（種族/狀態）|
| 地形 tile | 地形 mesh 頂點色 | vertex_color_use_as_albedo |
| 植被/岩石 | 程序 mesh | 顏色 tint（季節/生態）|

---

## 與 2D 系統的主要差異

2D 需要自訂 shader 做「基底 × 材質疊加」是因為 sprite 天生只有一張 texture。
3D 的材質系統本來就是這樣設計的（mesh 形狀與材質分離），**3D 版本反而更 native**，
大多數情況不需要寫 shader。

---

## 待決定

- [ ] 顏色 tint vs 頂點色 vs texture：依物件複雜度決定
- [ ] 程序生成的顏色 palette：集中管理一份 palette，所有 tint 從中取色
- [ ] 稀有度色調是 material 的一部分 or 額外 emission（發光感）

---

*記錄時間：2026-05-22*
*狀態：概念階段，對應 2D 版本 `../godot_material/`*
