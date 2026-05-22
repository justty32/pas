# 3D 材質系統：MaterialLibrary + Rim Glow Shader

## 目標

在 Low Poly 3D 策略遊戲中，管理所有材質變體（地形、物品稀有度、陣營色、選取高亮），
避免散落在各個腳本中重複建立 `StandardMaterial3D`。

---

## 核心設計

```
MaterialLibrary（靜態類別，GDScript）
  ├── 調色盤常數：BIOME_COLORS / RARITY_COLORS / FACTION_COLORS
  ├── 靜態工廠方法：make_unshaded / make_lit / make_vertex_color / make_water / make_emission / make_rim
  └── 材質快取：Dictionary，相同參數只建立一份 StandardMaterial3D

rim_glow.gdshader（spatial shader）
  └── Rim Glow 邊緣發光效果（選取高亮、傳奇單位）
```

**設計原則**：C++ 生成幾何，GDScript 只做材質組裝；材質透過 MaterialLibrary 集中管理。

---

## 原始碼位置

- `mapcore_godot/demo/scenes/material_library.gd`
- `mapcore_godot/demo/shaders/rim_glow.gdshader`

---

## MaterialLibrary 用法

### 無光照（Unshaded）— Low Poly 卡通感

```gdscript
# 直接使用調色盤常數
mesh.material_override = MaterialLibrary.make_unshaded(
    MaterialLibrary.RARITY_COLORS["legendary"]
)

# 或自訂顏色
mesh.material_override = MaterialLibrary.make_unshaded(Color(0.6, 0.3, 0.1))
```

### 頂點色（Vertex Color）— 地形 Mesh

```gdscript
# C++ terrain_mesh_builder 填入 ARRAY_COLOR 通道，此材質直接讀取
terrain_mesh.material_override = MaterialLibrary.make_vertex_color()

# unshaded=false → 保留 PBR 燈光（有陰影）
terrain_mesh.material_override = MaterialLibrary.make_vertex_color(false)
```

### 水面

```gdscript
# 預設：海藍色 alpha=0.60，roughness=0.1，metallic_specular=0.5
water_plane.material_override = MaterialLibrary.make_water()

# 自訂顏色（如淡水湖較清澈）
water_plane.material_override = MaterialLibrary.make_water(Color(0.20, 0.55, 0.45), 0.5)
```

### 自發光（Emission）— 稀有物品、特效

```gdscript
# 傳奇物品：金色底色 + 白色自發光
weapon.material_override = MaterialLibrary.make_emission(
    MaterialLibrary.RARITY_COLORS["legendary"],
    Color.WHITE,
    1.5   # energy_multiplier
)
```

### 多 Surface Mesh — 劍的刃 + 柄

```gdscript
# 劍 mesh 有兩個 surface：[0] = 刃, [1] = 柄
sword.set_surface_override_material(
    0, MaterialLibrary.make_unshaded(MaterialLibrary.RARITY_COLORS["rare"])
)
sword.set_surface_override_material(
    1, MaterialLibrary.make_unshaded(Color(0.4, 0.25, 0.1))  # 深棕木柄
)
```

### 陣營色 Tint — 單位與建築

```gdscript
unit.material_override = MaterialLibrary.make_unshaded(
    MaterialLibrary.FACTION_COLORS["enemy"]
)
```

---

## Rim Glow Shader 用法

### 基本使用

```gdscript
# preload 只需一次（通常放在腳本頂部）
const RIM_SHADER := preload("res://scenes/shaders/rim_glow.gdshader")

# 選取單位時套用
func on_unit_selected(unit: MeshInstance3D) -> void:
    unit.material_override = MaterialLibrary.make_rim(
        RIM_SHADER,
        MaterialLibrary.FACTION_COLORS["player"],  # 本體顏色
        Color.WHITE,   # rim 邊緣顏色
        2.0,           # rim_power（越小越寬）
        0.8            # rim_strength（0~1）
    )

func on_unit_deselected(unit: MeshInstance3D) -> void:
    unit.material_override = MaterialLibrary.make_unshaded(
        MaterialLibrary.FACTION_COLORS["player"]
    )
```

### Rim Shader 參數效果

| `rim_power` | `rim_strength` | 效果 |
|------------|---------------|------|
| 4.0 | 0.9 | 細而亮的邊緣光 |
| 2.0 | 0.8 | 中等寬度，選取感 |
| 1.5 | 0.6 | 寬柔邊緣，魔法光暈 |

---

## 快取行為

`make_unshaded` / `make_lit` / `make_vertex_color` / `make_water` / `make_emission` **有快取**：
- 相同參數 → 回傳同一個 `StandardMaterial3D` 物件
- 修改材質屬性會影響所有使用同一材質的 Mesh
- 若需要獨立動畫（如閃爍），呼叫後 `.duplicate()`：

```gdscript
var mat := MaterialLibrary.make_unshaded(Color.RED).duplicate() as StandardMaterial3D
# 現在可以安全地修改 mat，不影響其他物件
```

`make_rim` **無快取**（per-instance ShaderMaterial）。

---

## 與 MapRenderer3D 整合

`map_renderer_3d.gd` 已更新，改用：

```gdscript
# 地形（原本手動建立 StandardMaterial3D）
terrain_mesh_node.material_override = MaterialLibrary.make_vertex_color()

# 水面（原本 5 行 StandardMaterial3D 設定）
water_plane_node.material_override = MaterialLibrary.make_water()
```

---

## 何時各用哪種方法

| 物件 | 推薦方法 | 理由 |
|------|---------|------|
| 地形 mesh（C++ 生成） | `make_vertex_color()` | C++ 填入 ARRAY_COLOR |
| 水面 | `make_water()` | 半透明 + 反射預設 |
| 武器、建築（單色） | `make_unshaded(color)` | 卡通感，無需燈光 |
| 角色、裝備（PBR） | `make_lit(color)` | 有陰影深度感 |
| 傳奇 / 特效物件 | `make_emission()` | 自發光吸引注意 |
| 選取高亮 | `make_rim(shader, ...)` | 邊緣光效果 |
| 迷霧 overlay | `make_transparent()` | 通用半透明 |

---

## 場景切換時清理快取

```gdscript
# 在場景 _exit_tree 或全域事件中呼叫
MaterialLibrary.clear_cache()
```

---

*記錄時間：2026-05-22*
*狀態：MaterialLibrary 靜態工廠 + rim_glow.gdshader 已實作；map_renderer_3d.gd 已整合*
