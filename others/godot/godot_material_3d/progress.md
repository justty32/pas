# godot_material_3d — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的可用初版。

## 一句話：這是什麼

3D Low Poly 的材質工具集。CONCEPT 已經指出 3D 大多用 `StandardMaterial3D` 即可，
這份提供集中 palette + 一致 API 包裝，加一個 ShaderMaterial 範例（rim 描邊）給特殊情境。

## 檔案清單

```
godot_material_3d/
├── gd/
│   ├── palette3d.gd        # 集中色票（武器/稀有度/biome/膚色）
│   └── material3d.gd       # tint / vertex_color / textured / rim 等工廠
├── shaders/
│   └── rim_highlight.gdshader   # spatial 邊緣發光範例
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| Palette3D | 武器 8 種、稀有度 5 級、biome 7 種、膚色 6 種，含 rarity 混色 | ✅ 完成 |
| Material3D 工廠 | `tint()` / `vertex_color()` / `textured()` / `make_rim()` + apply helpers | ✅ 完成 |
| Rim shader | spatial unshaded-ish，邊緣發光 | ✅ 完成 |
| 真機驗證 | 在 Godot 4 編輯器拖 MeshInstance3D 測試 | ⏸ **待真機驗證** |

## 設計重點

### 1. Palette 集中管理（CONCEPT 待決事項已落地）
CONCEPT.md 待決項「程序生成的顏色 palette：集中管理一份 palette」直接做進 `Palette3D`。
要改美術風格只動這支檔，全專案連帶換色。

### 2. Shading 模式集中成三個 enum
Godot 的 shading 在 `StandardMaterial3D` 上分散多個欄位，這裡收斂成 `FLAT_UNSHADED` /
`FLAT_LIT` / `SMOOTH_LIT` 三選一，避免每次新建 material 都翻文件。

> ⚠ 真正的 low poly「flat shading」靠 mesh 法線（每面獨立頂點），不是 material 設定。
> 這在 `material3d.gd:_apply_shading` 旁有註明。`godot_procgen_mesh` 啟動時會在 C++ 端落實。

### 3. `texture_filter` 預設 NEAREST
Low poly 與 pixel 風格幾乎一定要 NEAREST（不要雙線性糊掉），所以 `textured()` 預設 NEAREST。

### 4. 稀有度作為 tint mixer
`Palette3D.mix_with_rarity(base, "legendary", 0.3)` 把基底色與稀有度色混合，
strength 控制混入比例。不污染基底色票。

## 用法範例

```gdscript
# 鋼劍
var mat := Material3D.tint(Palette3D.WEAPON["steel"])
Material3D.apply(sword_mesh, mat)

# 傳奇紫晶劍（基底色 + 稀有度色 + 一點 emission）
var tint_color := Palette3D.mix_with_rarity(Palette3D.WEAPON["crystal"], "legendary", 0.4)
var mat2 := Material3D.tint(tint_color, Material3D.Shading.FLAT_LIT, 0.4)
Material3D.apply(sword_mesh, mat2)

# 多 surface：刃 + 柄分開
var blade := Material3D.tint(Palette3D.WEAPON["steel"])
var handle := Material3D.tint(Palette3D.WEAPON["bone"])
Material3D.apply_per_surface(sword_mesh, [blade, handle] as Array[Material])

# 地形 mesh：用頂點色（mapcore 寫好的 vertex color）
Material3D.apply(terrain_mesh, Material3D.vertex_color())

# 選取 highlight：rim 發光（與 godot_selection_highlight 串接時可複用）
var rim := Material3D.make_rim(Color.CYAN, 2.5, 1.5)
sword_mesh.material_overlay = rim   # 注意是 overlay 不是 override
```

## 整合進真實 Godot 專案

1. 把整個 `godot_material_3d/` 資料夾複製到專案內（建議 `res://addons/godot_material_3d/`）。
2. 若改放別處，修改 `gd/material3d.gd` 的 `RIM_SHADER_PATH` 常數。
3. `class_name Material3D` 與 `Palette3D` 自動全域可用。

## 待決事項（從 CONCEPT.md 帶過來）

- [x] 集中 palette —— 已做進 `Palette3D`。
- [x] 稀有度色調走 tint mixer —— `mix_with_rarity()`。
- [ ] 稀有度是否同時驅動 emission —— 目前 `tint()` 接受 `emission` 參數，但 palette 沒有自動推導。
      若決定「rare 以上才發光」，可在 `Material3D.tint()` 內讀稀有度自動設 emission。
- [ ] flat shading 法線生成 —— 跨庫議題，待 `godot_procgen_mesh` 啟動處理。

## 與其他模組的銜接

- **`godot_selection_highlight`**：rim shader 是該模組「兩 pass outline 之外」的備案。
- **`godot_world_map_3d`**：地形 mesh 走 `vertex_color()`，
  mapcore_godot 端只要在 `ARRAY_COLOR` 通道寫入 biome 顏色（從 `Palette3D.BIOME` 取）即可。
- **`godot_character_3d`**：紙娃娃裝備槽用 `Material3D.tint()` 或 `make_rim()`。

## 下一步（按需）

1. **真機驗證**：在 Godot 4 拖 MeshInstance3D（隨便用 BoxMesh），跑上面四個用法範例。
2. **emission 自動化**：依稀有度自動推 emission 強度（rare 0.1 / epic 0.3 / legendary 0.6）。
3. **三色漸層 palette**：產 1D gradient texture，給 toon shading 用（warm/mid/cool 三段）。
