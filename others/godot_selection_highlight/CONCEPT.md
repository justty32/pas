# 單位選取 Highlight 系統

## 問題

Godot 3D 沒有原生 outline 效果。選中單位需要自己實作視覺回饋。

---

## 方案比較

| 方案 | 效果 | 實作難度 | 適合 Low Poly |
|------|------|---------|--------------|
| **兩 Pass Outline Shader** | 外框線，清晰 | 中 | ✅ 最適合 |
| Decal | 地面投影圓圈 | 低 | ✅ 好補充 |
| WorldEnvironment Glow | 全畫面泛光 | 低 | △ 不精準 |
| 替換 material（tint） | 顏色閃爍 | 極低 | △ 廉價感 |

**推薦組合：兩 Pass Outline + 地面 Decal**
- Outline：精確標示選中的物體邊緣
- Decal：地面投影圓，額外確認位置（尤其多層地形時）

---

## 方案 A：兩 Pass Outline Shader

原理：
1. **Pass 1（正常）**：正常渲染角色 mesh
2. **Pass 2（描邊）**：略微放大 mesh + 反轉面剔除（只畫背面）→ 從正面看只露出外圍一圈

```gdscript
# 選取時在 MeshInstance3D 加上第二個 surface 材質（outline material）
func select_unit(unit: MeshInstance3D) -> void:
    unit.set_surface_override_material(OUTLINE_SURFACE_IDX, OUTLINE_MATERIAL)

func deselect_unit(unit: MeshInstance3D) -> void:
    unit.set_surface_override_material(OUTLINE_SURFACE_IDX, null)
```

### Outline Shader

```glsl
// outline.gdshader
shader_type spatial;
render_mode cull_front, unshaded, depth_draw_always;
// cull_front = 只畫背面 → 正面看只看到外圍邊緣

uniform vec4  outline_color : source_color = vec4(1.0, 0.8, 0.0, 1.0);
uniform float outline_width : hint_range(0.0, 0.1) = 0.02;

void vertex() {
    // 沿法線方向膨脹頂點
    VERTEX += NORMAL * outline_width;
}

void fragment() {
    ALBEDO = outline_color.rgb;
}
```

### 使用方式

MeshInstance3D 需要兩個 surface：
- Surface 0：正常角色材質
- Surface 1：outline 材質（平時為 null，選取時設定）

若 mesh 只有一個 surface，可以在程序生成 mesh 時刻意加第二個空 surface，或是在 Blender 加一個 outline 材質 slot。

---

## 方案 B：地面 Decal（輔助用）

```gdscript
# 選取時在單位腳下放一個 Decal 節點
var decal = Decal.new()
decal.texture_albedo = SELECTION_CIRCLE_TEX  # 白色/黃色圓圈
decal.size = Vector3(2.0, 1.0, 2.0)
decal.position = unit.position + Vector3(0, 0.05, 0)
unit.add_child(decal)
```

Decal 投影在地形 mesh 上，不受單位 mesh 形狀影響，額外增強位置感。

---

## 多選狀態管理

策略遊戲通常有單選 / 多選兩種狀態：

```gdscript
class SelectionManager:
    var selected: Array[Node3D] = []

    func select(unit: Node3D, add_to_selection: bool = false) -> void:
        if not add_to_selection:
            _clear_all()
        selected.append(unit)
        _apply_highlight(unit)

    func deselect(unit: Node3D) -> void:
        selected.erase(unit)
        _remove_highlight(unit)

    func _clear_all() -> void:
        for u in selected:
            _remove_highlight(u)
        selected.clear()

    func _apply_highlight(unit: Node3D) -> void:
        # 設定 outline material + 放 decal

    func _remove_highlight(unit: Node3D) -> void:
        # 移除 outline material + 移除 decal
```

---

## Hover（滑鼠懸停）vs Select（點擊選取）

兩種狀態視覺要區分：

| 狀態 | Outline 顏色 | Decal |
|------|------------|-------|
| Hover | 白色，細 | 無 |
| Selected（我方） | 黃色/綠色，粗 | 有 |
| Selected（敵方） | 紅色，粗 | 有 |
| 移動目標格 | 藍色 decal | 只有 decal |

---

## 2D 版本

2D 不需要 shader，直接：
- Outline：Sprite2D 疊加一張 outline texture，或用 `draw_*` 方法在 CanvasItem 上畫外框
- 或 `modulate` 顏色閃爍（最簡單）
- Godot 4 的 2D 也支援 ShaderMaterial，可以做像素等寬的外框

---

## 待決定

- [ ] Outline 粗細是固定世界空間（`outline_width` 單位是 m）還是螢幕空間（zoom 變化時粗細不變）
- [ ] Low poly 頂點數少，outline 可能在尖銳邊緣有缺口——是否需要 smooth normal 修正
- [ ] 選取框拖曳（框選多個單位）：2D 矩形框 + Raycast/Overlap 查詢

---

*記錄時間：2026-05-22*
*狀態：概念階段；推薦兩 Pass Outline + Decal 組合*
