# godot_selection_highlight — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地。

## 一句話：這是什麼

2D + 3D 單位選取／懸停描邊 + 框選 helper，不耦合 mapcore demo 結構，可拆出複用。

## 真相校準

mapcore_godot demo 端已有 `selection_manager.gd` + `selection_manager_2d.gd` +
`selection_outline.gdshader` + `selection_outline_2d.gdshader`，含 hover/select 雙狀態、
我方/敵方雙色、Decal 圓圈，並真機驗證。本目錄做的差異與補強：

| 差異點 | demo 版 | 本檔版 |
|--------|---------|--------|
| 3D outline 寬度 | 只有世界空間 | 世界 + **螢幕空間恆定**雙 shader（CONCEPT 待決事項） |
| 3D 多 mesh 角色 | 只挑第一個 MeshInstance3D | `apply_3d_recursive()` 全套（紙娃娃多 mesh 適用） |
| 2D outline 採樣 | 8 點固定 | 4 邊／4 角／8 點三選一 + **脈動** uniform |
| 選取狀態管理 | demo 端 SelectionManager 自管 | 本檔不管，純 apply/remove API，狀態交呼叫端 |
| 框選拖曳 | demo 沒做 | `BoxSelector` Control（落實 CONCEPT 待決事項） |

## 檔案清單

```
godot_selection_highlight/
├── shaders/
│   ├── outline_world.gdshader    # 3D 世界空間 outline（同 demo 版）
│   ├── outline_screen.gdshader   # 3D 螢幕空間恆定粗細 outline
│   └── outline_2d.gdshader       # 2D sprite outline，4邊/4角/8點 + 脈動
├── gd/
│   ├── selection_highlight.gd    # SelectionHighlight：apply/remove 通用 helper
│   └── box_selector.gd           # BoxSelector：框選 Control
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| 3D 世界空間 outline shader | 與 demo 版一致 | ✅ 完成 |
| 3D 螢幕空間 outline shader | clip space normal 推 + NDC per pixel 換算 | ✅ 完成 |
| 2D outline shader | 三種採樣 pattern + 脈動 TIME | ✅ 完成 |
| SelectionHighlight static | apply/remove 3D 單 + recursive、apply/remove 2D | ✅ 完成 |
| BoxSelector Control | 左鍵拖曳框 + Shift 加選 + Callable 注入候選與投影 | ✅ 完成 |
| 真機驗證 | Godot 4 跑兩種 3D shader + 2D + box selector | ⏸ **待真機驗證** |

## 設計重點

### 1. 螢幕空間恆定粗細的 outline shader 原理
CONCEPT 待決事項。`outline_screen.gdshader` 的關鍵是把 NORMAL 推到 clip space 後，
偏移量乘以 `clip_pos.w`（透視除法的倒數補償）：

```glsl
float ndc_per_pixel = 2.0 / 1080.0;     // NDC y 範圍 = 2，1080p
float offset = pixel_width * ndc_per_pixel * clip_pos.w;
clip_pos.xy += clip_normal.xy * offset;
```

因為 NDC.x/y 最終會除以 w，所以乘上 w 後抵消，視覺寬度與深度無關 = 鏡頭拉遠也一樣粗。
缺點：1080 寫死，其他解析度需要 multiplier 微調（或改用 `VIEWPORT_SIZE`）。

### 2. 不管理選取狀態
demo 版的 SelectionManager 維護 `selected: Array`、`hovered: Node3D`。
本檔的 `SelectionHighlight` 純 apply/remove 工具，**選取邏輯交呼叫端**。

原因：選取狀態強烈耦合遊戲規則（誰能選、能否多選、選了之後怎樣），不該寫死在 highlight 層。
通常呼叫端會有自己的 `Unit` 資料結構，掛在哪個 controller 上、是否敵方、能不能多選都
依專案定義。本檔給最薄的工具，呼叫端用 `apply_3d_recursive(unit, my_color, ...)` 即可。

### 3. BoxSelector 用兩個 Callable 注入解耦
`candidates_provider` 回傳所有候選 unit、`world_pos_extractor` 把 unit 投影到螢幕座標。
本檔不知道 unit 是什麼型別、也不知道相機在哪。signal 回傳框內 unit 陣列 + 是否 additive
（Shift），呼叫端決定怎麼套到自己的選取狀態。

### 4. 2D outline 用 `material` 取代而非 overlay
Sprite2D 沒有 `material_overlay`（那是 3D GeometryInstance 才有）。直接 `material =` 取代，
取代前用 meta 存原 material，移除時還原。**不會無聲覆蓋使用者的自訂材質**。

## 用法範例

### 3D 單選 + 螢幕空間描邊
```gdscript
SelectionHighlight.apply_3d(unit, Color.YELLOW, 3.0,
		SelectionHighlight.Style3D.SCREEN_SPACE)  # 3 px 寬，zoom 不變
# 取消
SelectionHighlight.remove_3d(unit)
```

### 3D 紙娃娃多 mesh
```gdscript
# 角色根 Node3D 下有 Body / Helmet / Weapon 多個 MeshInstance3D
SelectionHighlight.apply_3d_recursive(character_root, Color.YELLOW)
```

### 2D 選取脈動
```gdscript
SelectionHighlight.apply_2d(sprite, Color.YELLOW, 2.5,
		SelectionHighlight.Pattern2D.FULL, 0.4)  # 脈動 40%
```

### 框選
```gdscript
var box := BoxSelector.new()
box.candidates_provider = func() -> Array: return all_units
box.world_pos_extractor = func(unit) -> Vector2:
	return camera.unproject_position(unit.global_position)
box.selection_committed.connect(func(units: Array, additive: bool) -> void:
	if not additive:
		_clear_selection()
	for u in units:
		_add_to_selection(u))
$CanvasLayer.add_child(box)
```

## 待決事項（從 CONCEPT.md 帶過來）

- [x] **世界 vs 螢幕空間寬度**：兩支 shader 都有，呼叫端選。
- [ ] **Low poly 尖銳邊缺口**：smooth normal 修正需要把平滑法線預烘焙進 UV2，
      程序生成 mesh 可在 C++ 端順便算；Blender 匯出的 .glb 需要 import 設定。
      本檔暫不處理，靠 mesh 細節邊緣不要太尖即可。
- [x] **選取框拖曳**：`BoxSelector` Control。

## 下一步（按需）

1. **真機驗證**：丟一個 Box mesh 到 Godot 4 場景，分別套 world / screen / 2D 三支 shader 看效果。
2. **與 godot_character_controller 整合**：unit controller 的 selected 狀態改變時
   觸發 `SelectionHighlight.apply_3d_recursive()`。
3. **smooth normal 烘焙**：等真的看到 outline 缺口時再做。
