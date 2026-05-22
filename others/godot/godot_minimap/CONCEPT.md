# Minimap 系統

## 兩種實作方案

### 方案 A：SubViewport 即時渲染（重量級）

```
SubViewport
└── Camera3D（正交投影，從正上方看，rotation.x = -90°）
    → 渲染整個地形場景
SubViewportContainer / TextureRect（HUD 層）
    → 顯示 SubViewport 的輸出
```

優點：自動顯示單位、特效、動態變化，不需要額外維護。
缺點：多一個場景的渲染開銷，大地圖時效能較差。

### 方案 B：從 mapcore 資料直接生成 texture（輕量級，推薦）

```
C++ GDExtension 或 GDScript
    → 讀取 mapcore 格子資料
    → 逐像素填色（terrain type → color）
    → 產生 Image → ImageTexture
TextureRect（HUD 層）
    → 顯示這張靜態 texture
動態疊加層（另一張 Image 或 shader）
    → 單位位置、迷霧遮罩
```

優點：幾乎零渲染開銷；minimap 顏色可以和實際 3D 場景完全獨立設計（更清晰）。
缺點：需要在單位移動 / 地圖狀態改變時主動更新 texture。

**本專案推薦方案 B**——mapcore 資料已在 C++ 中，直接生成 minimap texture 是自然延伸。

---

## 方案 B 實作細節

### Minimap Texture 生成（GDExtension 或 GDScript）

```gdscript
func generate_minimap_texture(map_data: MapData) -> ImageTexture:
    var img = Image.create(map_data.width, map_data.height, false, Image.FORMAT_RGBA8)
    for z in map_data.height:
        for x in map_data.width:
            var cell = map_data.get_cell(x, z)
            img.set_pixel(x, z, terrain_to_minimap_color(cell.terrain))
    return ImageTexture.create_from_image(img)

func terrain_to_minimap_color(terrain: int) -> Color:
    match terrain:
        TERRAIN_OCEAN:   return Color(0.1, 0.3, 0.6)
        TERRAIN_PLAIN:   return Color(0.6, 0.75, 0.3)
        TERRAIN_FOREST:  return Color(0.2, 0.5, 0.2)
        TERRAIN_DESERT:  return Color(0.85, 0.75, 0.4)
        TERRAIN_MOUNTAIN:return Color(0.55, 0.5, 0.45)
        _:               return Color.GRAY
```

地圖生成後呼叫一次，之後只在地圖狀態改變時局部更新（`img.set_pixel` 單格更新）。

### 單位疊加層

單位不寫進 terrain texture，另用一張同尺寸的 Image 疊加（shader 合併，或兩個 TextureRect 重疊）：

```gdscript
func update_unit_overlay(units: Array) -> void:
    unit_img.fill(Color.TRANSPARENT)
    for unit in units:
        var px = Vector2i(unit.grid_x, unit.grid_z)
        unit_img.set_pixel(px.x, px.y, unit_color(unit.faction))
    unit_overlay_texture.update(unit_img)
```

### 迷霧遮罩疊加

同樣另一張 Image，unexplored 格塗黑、explored 格塗半透明灰：

```gdscript
func update_fog_overlay(visibility: PackedByteArray, w: int, h: int) -> void:
    for i in visibility.size():
        var x = i % w; var z = i / w
        match visibility[i]:
            0: fog_img.set_pixel(x, z, Color(0, 0, 0, 1.0))    # hidden
            1: fog_img.set_pixel(x, z, Color(0, 0, 0, 0.5))    # explored
            2: fog_img.set_pixel(x, z, Color.TRANSPARENT)       # visible
```

---

## HUD 節點結構

```
CanvasLayer (HUD)
└── MinimapContainer (Control, 固定右下角)
    ├── TextureRect [terrain_layer]    ← terrain texture
    ├── TextureRect [unit_layer]       ← unit overlay（透明背景）
    ├── TextureRect [fog_layer]        ← fog overlay（透明背景）
    └── TextureRect [viewport_rect]   ← 當前攝影機視野框（空心矩形）
```

---

## 點擊 Minimap 移動鏡頭

```gdscript
func _on_minimap_clicked(event: InputEventMouseButton) -> void:
    if event.button_index != MOUSE_BUTTON_LEFT or not event.pressed:
        return
    var local_pos = minimap_container.get_local_mouse_position()
    var map_ratio = local_pos / minimap_container.size           # (0,0)~(1,1)
    var world_pos = Vector3(
        map_ratio.x * map_width,
        0,
        map_ratio.y * map_height
    )
    camera_rig.focus(world_pos)
```

---

## 攝影機視野框

在 minimap 上疊一個空心矩形，顯示當前 Camera3D 的可視範圍：

```gdscript
func _process(_delta: float) -> void:
    var cam_focus = camera_rig.get_focus_point()
    var zoom_n    = camera_rig.get_zoom_normalized()  # 0=遠, 1=近
    # 依 zoom 計算視野矩形大小，更新 viewport_rect 的位置與尺寸
```

---

## 待決定

- [ ] Minimap 尺寸：固定像素（如 200×200）還是跟隨地圖長寬比縮放
- [ ] 單位圖示：單像素點 or 2–3 像素小圖示（faction 圖標）
- [ ] 地圖外框與 UI 裝飾風格
- [ ] 大地圖效能：只在視野附近動態更新，遠處靜態

---

*記錄時間：2026-05-22*
*狀態：概念階段；推薦方案 B（mapcore 資料直接生成 texture）*
