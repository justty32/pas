# godot_minimap — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地。

## 一句話：這是什麼

HUD minimap Control：吃 `MapCoreMapData` 自動建四層 TextureRect（terrain / unit / fog /
viewport_rect），點擊發 `map_clicked` signal，視野框追蹤 `camera_rig`。

CONCEPT 推薦的**方案 B**（mapcore 資料直接生 texture，不走 SubViewport 即時渲染）。

## 真相校準

| 來源 | 角色 |
|------|------|
| mapcore C++ `MapCoreWorldMap2DRenderer.generate_terrain_image()` + `draw_rivers()` | 已落地，含河流分級寬度 |
| **本檔 Minimap Control** | 抽出 HUD 整合層：四層堆疊 + 點擊 + 視野框 |
| GDScript 後備渲染 | mapcore .so 不可用時自動 fallback（無河流） |

## 檔案清單

```
godot_minimap/
├── CONCEPT.md
├── gd/
│   ├── minimap_palette.gd   # MinimapPalette：terrain + faction 色票（與場景渲染獨立）
│   └── minimap.gd           # Minimap Control 主類
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| MinimapPalette | 11 terrain 色 + 4 faction 色（與場景色獨立，高對比版） | ✅ 完成 |
| 四層堆疊建立 | terrain / unit / fog / viewport_rect 自動建 TextureRect | ✅ 完成 |
| mapcore 渲染器整合 | use_mapcore_renderer=true 時呼叫 C++ generate_terrain_image + draw_rivers | ✅ 完成 |
| GDScript 後備渲染 | mapcore .so 不可用時走純 GDScript（無河流） | ✅ 完成 |
| update_units | Array of {cell, faction} → 重畫 unit 層 | ✅ 完成 |
| update_fog | PackedByteArray (0/1/2) → 重畫 fog 層 | ✅ 完成 |
| 點擊 signal | `map_clicked(world_pos: Vector2)`，3D 端補 Y=0 即可 | ✅ 完成 |
| 視野框 _draw | 依 camera.get_focus_point + get_zoom_normalized 算位置與比例 | ✅ 完成 |
| 真機驗證 | Godot 4 + mapcore_godot 編好 .so，HUD 拖入跑 | ⏸ **待真機驗證** |

## 設計重點

### 1. 為什麼走方案 B 而非 SubViewport
CONCEPT 已分析：SubViewport 自動同步單位/特效，但多一個場景的渲染開銷。
方案 B 只在「地圖狀態變」時才更新 Image，平常零渲染開銷。對 minimap 這種**靜態 + 偶爾更新**
的 UI 元素是理所當然選擇。本檔不做 SubViewport 版（CONCEPT 已標明備案，未來真要切再開）。

### 2. cell_px 控制 minimap 細節
1 = 一格一像素（最節省，但小地圖看不清細節）；4~8 = 河流線條與 unit dot 都看得清楚。
mapcore `MapCoreWorldMap2DRenderer.generate_terrain_image()` 已支援這個參數，
GDScript 後備版本檔也對齊。

### 3. Minimap 色票故意與場景渲染獨立
mapcore demo MaterialLibrary.BIOME_COLORS 是給 3D 場景頂點色用的（飽和度低、低對比、配合燈光）。
Minimap 在小尺寸下需要**高對比、易辨識**，所以 `MinimapPalette.TERRAIN` 故意做更鮮明。
CONCEPT 明確點到「minimap 顏色可以和實際 3D 場景完全獨立設計（更清晰）」。

### 4. 視野框靠 camera_rig.get_zoom_normalized()
本檔不需要知道相機是 2D 還是 3D——靠 `godot_camera_rig` 的**對外統一介面**：
`get_focus_point()` 回 Vector2 或 Vector3、`get_zoom_normalized()` 回 0~1。
本檔 `_focus_to_grid()` 偵測型別自動換算成格座標。

### 5. 視野框比例隨 zoom 線性插值
`viewport_frac_far`（zoom_n=0 時占多大）與 `viewport_frac_near`（zoom_n=1 時占多大）兩個
@export，linear interpolation。預設 0.7 → 0.15，相機拉遠時框大、拉近時框小，符合直覺。

### 6. 點擊 emit Vector2 而非 Vector3
不寫死 3D。回傳 `(world_x, world_z_or_y)`，呼叫端決定怎麼餵相機：
```gdscript
minimap.map_clicked.connect(func(pos: Vector2) -> void:
    camera_rig_3d.focus(Vector3(pos.x, 0, pos.y))   # 3D
    # 或
    camera_rig_2d.focus(pos * tile_size))             # 2D，補 tile_size 換算
```

## 用法範例

### 場景結構
```
HUDLayer (CanvasLayer)
└── MinimapContainer (Control，固定右下角 200×200)
    └── Minimap (本腳本)
        @export map_data       = (mapcore 生成完餵入)
        @export camera_rig     = $/root/Main/CameraRig3D
        @export cell_px        = 2
```

### 主流程
```gdscript
# 地圖生成完
minimap.mount(map_data)

# 點擊 → 飛相機
minimap.map_clicked.connect(func(pos: Vector2) -> void:
    camera_rig.focus(Vector3(pos.x, 0, pos.y)))

# 每秒更新一次單位位置（不必每幀）
get_tree().create_timer(1.0).timeout.connect(func() -> void:
    minimap.update_units([
        {"cell": Vector2i(unit_a.x, unit_a.z), "faction": "player"},
        {"cell": Vector2i(unit_b.x, unit_b.z), "faction": "enemy"},
    ]))

# 迷霧（如果有可視性系統）
minimap.update_fog(visibility_packed)
```

## 待決事項（從 CONCEPT.md 帶過來）

- [x] **Minimap 尺寸**：本檔 Control，由外部 set size 決定；texture stretch 自動配合。
- [ ] **單位圖示**：目前單像素 dot（`_paint_cell` 用 faction 純色）。CONCEPT 待決事項
      「2–3 像素小圖示」未做，等真要 faction 圖標時補（換成 `Image.blit_rect` 貼圖案）。
- [ ] **地圖外框 UI 裝飾**：純美術，留給呼叫端在 MinimapContainer 外再包一層 Panel。
- [ ] **大地圖局部更新**：目前 `update_units` / `update_fog` 整張重畫。
      `Image.set_pixel()` 64×64 約 4k 寫入毫秒級可接受，256×256（64k 寫入）才會考慮優化。

## 與其他模組的串接

| 模組 | 互動 |
|------|------|
| `mapcore_godot` `MapCoreWorldMap2DRenderer` | terrain + 河流的渲染來源 |
| `mapcore_godot` `MapCoreMapData` | width/height/get_terrain 提供格資料 |
| `godot_camera_rig` | get_focus_point + get_zoom_normalized 給視野框 |
| `godot_character_controller.UnitController3D` | 提供單位 cell，呼叫端聚合後餵 update_units |

## 下一步（按需）

1. **真機驗證**：mapcore_godot 編好 .so 的 Godot 4 專案，HUD 加 Minimap 看效果。
2. **faction 小圖示**：替換單像素 dot 為 2×2 或 3×3 圖案（CONCEPT 待決事項）。
3. **局部 update_units 優化**：大地圖出現效能瓶頸時再做。
