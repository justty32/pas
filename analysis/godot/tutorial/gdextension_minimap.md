# GDExtension：Minimap 小地圖系統

## 目標

在 3D 策略遊戲的 HUD 角落放一張小地圖，達到三件事：

1. 一眼看到整張世界地圖的地形分佈（與 2D 全圖同源、同一套 mapcore 查詢 API）。
2. 疊加動態資訊：單位位置、迷霧、當前攝影機視野框。
3. 點擊小地圖即可把主鏡頭平滑飛到該座標（呼叫 [[godot_camera_rig]] 的 `focus()`）。

設計目標是「幾乎零渲染開銷」，因此採用概念文件推薦的**方案 B**（從 mapcore Tile 資料直接生 texture），
方案 A（SubViewport 即時渲染）僅作為需要顯示即時特效時的備選。

---

## 原始碼位置

### 概念來源
- `others/godot/godot_minimap/CONCEPT.md`（方案 A/B 描述、HUD 結構、待決定清單）

### mapcore 資料來源（方案 B 的核心）
- `others/gamecore/mapcore_godot/src/map_data.h`
  - 單格查詢：`get_terrain(x,y)`、`get_hilliness(x,y)`、`get_water_depth(x,y)`、`get_feature_id_at(x,y)`（行 35-56）
  - 批次查詢：`get_terrain_array()` 回傳 row-major flat `PackedInt32Array`，索引 `[y*w+x]`（行 43）
  - 地形常數：`TERRAIN_OCEAN=0` … `TERRAIN_LAKE=10` 共 11 種（行 65-75）
- `others/gamecore/mapcore_godot/src/world_map_2d_renderer.cpp`
  - `generate_terrain_image(data, cell_px)`（行 39-57）：minimap 直接複用此函式，僅 `cell_px` 設小
  - `terrain_color(int t)`（行 20-35）：11 種地形 → linear RGB 顏色表（minimap 顏色應以此為基準）
- 既有 2D 全圖教學（同源資料）：`analysis/godot/tutorial/gdextension_world_map_2d.md`

### Godot 引擎 API（godot-cpp v4.6 stable，標頭由 `gdextension/extension_api.json` 生成於 `gen/include/godot_cpp/classes/`）
- `Image`（`godot_cpp/classes/image.hpp`）
  - 靜態 `Image::create(int w, int h, bool mipmaps, Image::Format fmt) -> Ref<Image>`
  - `Image::set_pixel(int x, int y, Color)`、`Image::fill(Color)`、`Image::fill_rect(Rect2i, Color)`
- `ImageTexture`（`godot_cpp/classes/image_texture.hpp`）
  - 靜態 `ImageTexture::create_from_image(Ref<Image>) -> Ref<ImageTexture>`
  - `ImageTexture::update(Ref<Image>)`（就地更新，**不重新配置 GPU 紋理**，動態疊加層用這個）
- `SubViewport`（`godot_cpp/classes/sub_viewport.hpp`），`get_texture()` 繼承自 `Viewport`，回傳 `ViewportTexture`
- `Camera3D`（`godot_cpp/classes/camera3d.hpp`）：`set_orthogonal(float size, float z_near, float z_far)`

### 鏡頭聯動對象
- `others/gamecore/mapcore_godot/demo/scenes/camera_rig_3d.gd`
  - `focus(world_pos: Vector3, instant := false)`（行 171）、`get_focus_point() -> Vector3`（行 181）、`get_zoom_normalized() -> float`（行 185）
  - 匯出邊界 `map_width`、`map_depth`（行 21-22）——minimap 換算座標需與此一致

---

## 兩種方案比較

| 維度 | 方案 A：SubViewport 即時渲染 | 方案 B：mapcore 資料生 texture（推薦）|
|------|------------------------------|----------------------------------------|
| 渲染成本 | 多一個 3D 場景 pass（額外攝影機 + draw call）| 一次生圖後幾乎為零；只在資料變動時局部改像素 |
| 動態元素（單位/特效）| 自動跟著主場景出現，零維護 | 需自行用疊加層 Image 主動更新 |
| 視覺清晰度 | 等同縮小的 3D 畫面，小尺寸下細節糊成一片 | 可獨立設計清晰色盤（地形對比強，遠看可讀）|
| 解析度與尺寸解耦 | 受 SubViewport 像素數限制 | Image 尺寸 = `w*cell_px`，與螢幕無關 |
| 大地圖擴展性 | 隨地圖變大線性吃 GPU/頻寬 | 與地圖大小無關（生圖一次性，疊加層才是常駐成本）|
| 實作複雜度 | 低（擺好攝影機即可）| 中（要寫顏色映射 + 疊加層更新）|

**為何方案 B 在大地圖時較優（明確論證）：**

1. **渲染成本與地圖大小脫鉤。** 方案 A 每幀都要把整個 3D 場景再渲染一次到 SubViewport，地圖越大、單位越多，這個第二 pass 越貴；而方案 B 的地形圖是「生成一次、之後只讀」的靜態 texture，每幀成本恆定且趨近於零。
2. **動態成本可被局部化。** 方案 B 把會變動的東西（單位、迷霧）分離到獨立疊加層，更新時只改「動到的格子」幾個像素再 `ImageTexture::update()`，與地圖總格數無關（見〈效能模型〉）。方案 A 無法只重畫一角，必須整張 SubViewport 重渲染。
3. **可讀性。** 大地圖縮到 200×200 的小框時，方案 A 的 3D 透視/陰影/低多邊形細節會糊成噪點；方案 B 用高對比色盤，一格一像素，遠看仍能分辨海陸與地形。
4. **與既有資產複用。** `MapCoreWorldMap2DRenderer::generate_terrain_image()` 已存在且驗證過（同一函式驅動 2D 全圖），minimap 直接拿來用，邊際開發成本極低。

方案 A 唯一明顯勝場是「需要在小地圖上看到即時動畫/特效」（如戰鬥火光），這類需求建議用方案 B + 疊加層手動標記即可，不值得為它扛下整個第二渲染 pass。

---

## 方案 B 實作細節

### 步驟一：複用 C++ 生地形底圖（一次性）

minimap 的地形底圖與 2D 全圖**完全同源**，直接呼叫既有的
`MapCoreWorldMap2DRenderer::generate_terrain_image()`（`world_map_2d_renderer.cpp:39`），
差別只在 `cell_px` 設成 1（或 2），讓整張圖剛好落在小地圖框內：

```gdscript
# minimap.gd（掛在 MinimapContainer 上）
var _renderer := MapCoreWorldMap2DRenderer.new()   # RefCounted，直接 .new()
var _terrain_tex: ImageTexture

func build_terrain_layer(data: MapCoreMapData) -> void:
    # cell_px=1 → Image 尺寸恰為 (width × height) 像素；TextureRect 再放大顯示
    var img := _renderer.generate_terrain_image(data, 1)
    _renderer.draw_rivers(img, data, 1, 80)        # 河流選擇性疊加（min_strength=80 濾細流）
    _terrain_tex = ImageTexture.create_from_image(img)
    $TextureLayer.texture = _terrain_tex
    $TextureLayer.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST  # 像素化放大，不糊邊
```

> 重點：`generate_terrain_image` 的 `cell_px` 是「每格幾像素」。minimap 用 1，靠 `TextureRect` 的
> Stretch 把 `width×height` 的小圖放大到框格大小；`TEXTURE_FILTER_NEAREST` 保持格子銳利。

### 逐格欄位 → 像素顏色的映射（mapcore Tile → minimap pixel）

底圖的顏色基準是 `world_map_2d_renderer.cpp:20-35` 的 `terrain_color()`（11 種 `TERRAIN_*` 常數對應 linear RGB）。
若要做 minimap 專屬色盤（更高對比），在 GDScript 端覆寫即可，但**索引務必對齊 `map_data.h:65-75` 的 11 個常數**：

```gdscript
# minimap 專屬高對比色盤；常數來自 MapCoreMapData（C++ 端定義，map_data.h:65-75）
static func terrain_to_minimap_color(t: int) -> Color:
    match t:
        MapCoreMapData.TERRAIN_OCEAN:     return Color(0.06, 0.18, 0.42)  # 深藍
        MapCoreMapData.TERRAIN_COAST:     return Color(0.25, 0.50, 0.75)
        MapCoreMapData.TERRAIN_PLAINS:    return Color(0.72, 0.82, 0.42)
        MapCoreMapData.TERRAIN_GRASSLAND: return Color(0.35, 0.65, 0.30)
        MapCoreMapData.TERRAIN_DESERT:    return Color(0.88, 0.80, 0.45)
        MapCoreMapData.TERRAIN_TUNDRA:    return Color(0.65, 0.70, 0.75)
        MapCoreMapData.TERRAIN_SNOW:      return Color(0.92, 0.95, 0.98)
        MapCoreMapData.TERRAIN_FOREST:    return Color(0.14, 0.38, 0.16)  # 深綠
        MapCoreMapData.TERRAIN_HILL:      return Color(0.60, 0.55, 0.40)
        MapCoreMapData.TERRAIN_MOUNTAIN:  return Color(0.45, 0.40, 0.36)  # 深棕灰
        MapCoreMapData.TERRAIN_LAKE:      return Color(0.20, 0.45, 0.70)
        _:                                return Color(0.5, 0.5, 0.5)
```

> 注意：CONCEPT.md（行 51-58）示意用的 `TERRAIN_PLAIN / TERRAIN_MOUNTAIN` 等只有 5 種、且名稱（`PLAIN`）
> 與真實常數（`PLAINS`，複數）不符。實作以 `map_data.h` 為準的 **11 種**為主。

#### 純 GDScript 版逐格生圖（不改 C++）

若不想動 C++，可用批次查詢 `get_terrain_array()`（`map_data.h:43`，row-major `[y*w+x]`）在 GDScript 端逐格 `set_pixel`：

```gdscript
func build_terrain_layer_gdscript(data: MapCoreMapData) -> void:
    var w := data.get_width()
    var h := data.get_height()
    var arr := data.get_terrain_array()          # PackedInt32Array，長度 w*h
    var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
    for y in h:
        for x in w:
            img.set_pixel(x, y, terrain_to_minimap_color(arr[y * w + x]))
    _terrain_tex = ImageTexture.create_from_image(img)
    $TextureLayer.texture = _terrain_tex
```

> 取捨：純 GDScript 對 256×256 地圖約 65k 次 `set_pixel`，生圖一次性、可接受；但大地圖（如 1024²）
> 建議走 C++ 的 `fill_rect` 路徑（`world_map_2d_renderer.cpp:51`），速度差一個量級。

#### 進階：用 hilliness / water_depth 做明暗（可選）

要讓 minimap 有立體感，可讀 `get_hilliness(x,y)`（`map_data.h:36`，0~5）對基礎色做明度微調，
或用 `get_water_depth(x,y)`（行 37）讓深海更暗：

```gdscript
var base := terrain_to_minimap_color(arr[y * w + x])
var hill := data.get_hilliness(x, y)              # 0=UNDEFINED … 5=IMPASSABLE
var shade := 1.0 + (hill - 2) * 0.06              # 越高越亮一點點
img.set_pixel(x, y, base * shade)
```

### 步驟二：單位疊加層（動態，獨立 Image）

單位**不寫進**地形底圖，另用一張同尺寸 `FORMAT_RGBA8` Image，透明背景，只標記有單位的格子。
更新時用 `ImageTexture::update()` 就地刷新（不重配 GPU 紋理）：

```gdscript
var _unit_img: Image
var _unit_tex: ImageTexture

func _init_unit_layer(w: int, h: int) -> void:
    _unit_img = Image.create(w, h, false, Image.FORMAT_RGBA8)
    _unit_tex = ImageTexture.create_from_image(_unit_img)
    $UnitLayer.texture = _unit_tex

func update_unit_overlay(units: Array) -> void:
    _unit_img.fill(Color.TRANSPARENT)
    for u in units:
        _unit_img.set_pixel(u.grid_x, u.grid_z, _faction_color(u.faction))
    _unit_tex.update(_unit_img)        # 就地更新，比重新 create_from_image 便宜
```

### 步驟三：迷霧遮罩層（動態，獨立 Image）

同樣獨立一張 Image：未探索塗不透明黑、已探索塗半透明黑、可視塗透明。
`visibility` 為 row-major `PackedByteArray`（與 `get_terrain_array()` 同索引慣例 `i = y*w + x`）：

```gdscript
func update_fog_overlay(visibility: PackedByteArray, w: int, h: int) -> void:
    for i in visibility.size():
        var x := i % w
        var y := i / w
        match visibility[i]:
            0: _fog_img.set_pixel(x, y, Color(0, 0, 0, 1.0))     # hidden 全黑
            1: _fog_img.set_pixel(x, y, Color(0, 0, 0, 0.5))     # explored 半透明
            2: _fog_img.set_pixel(x, y, Color.TRANSPARENT)        # visible 透明
    _fog_tex.update(_fog_img)
```

### HUD 節點結構（方案 B）

對齊 CONCEPT.md（行 92-101），三張 texture 由下而上疊在同一個固定角落容器：

```
CanvasLayer (HUD)
└── MinimapContainer (Control, anchor 右下角, 固定尺寸)
    ├── TextureRect [TextureLayer]    ← 地形底圖（_terrain_tex, NEAREST filter）
    ├── TextureRect [UnitLayer]       ← 單位疊加（透明背景）
    ├── TextureRect [FogLayer]        ← 迷霧疊加（透明背景）
    └── Control     [ViewportRect]    ← 視野框（_draw 畫空心矩形，見後）
```

三個 `TextureRect` 同位置同尺寸、`mouse_filter` 設 IGNORE（點擊事件交給 `MinimapContainer` 統一處理）。

---

## 方案 A 實作要點

僅在需要小地圖反映即時 3D 特效時採用。核心是一台正交攝影機從正上方俯拍整個地形場景。

### 節點結構

```
SubViewport (size = 256×256, render_target_update_mode = UPDATE_ALWAYS 或排程)
└── Camera3D (current=true)
        rotation.x = -90°（垂直下看）
        正交投影：set_orthogonal(map_width, 0.1, 1000)  # size 涵蓋整張地圖
        position = (map_width*0.5, 高度H, map_depth*0.5)  # 置於地圖中心正上方
TextureRect [MinimapView]（HUD 層）
    texture = SubViewport.get_texture()  # 繼承自 Viewport，回傳 ViewportTexture
```

### 關鍵設定

- **正交而非透視**：用 `Camera3D::set_orthogonal(size, z_near, z_far)`（`camera3d.hpp`），`size` 設為地圖較大邊長，
  讓整張地圖無透視變形地填滿畫面（俯瞰圖正確比例的前提）。
- **垂直俯視**：`rotation.x = deg_to_rad(-90)`，相機 `-Z` 朝下；`position.y` 設足夠高（> 地形最大高度）。
- **取得輸出貼到 HUD**：`texture_rect.texture = sub_viewport.get_texture()`（`get_texture()` 在 `Viewport`，
  `SubViewport` 繼承之，回傳 `ViewportTexture`）。
- **更新節流**：`SubViewport.render_target_update_mode` 不要恆設 `UPDATE_ALWAYS`，改 `UPDATE_WHEN_VISIBLE`
  或用程式碼每 N 幀手動觸發一次，避免白白每幀重渲染（見〈效能模型〉）。

### 與場景共存的攝影機問題

SubViewport 內的 Camera3D 若 `current=true` 不會搶走主場景鏡頭（兩者在不同 Viewport），
但要確保地形/單位節點同時被主場景與 SubViewport 看見——
最簡單是讓 SubViewport 透過 `World3D` 共用同一個 3D 世界（將 SubViewport 的 `world_3d`
指向主場景的 World3D），避免重複擺放場景。

---

## 視窗框 / 點擊定位 / 與 CameraRig 的聯動

### 座標換算的單一事實來源

所有換算都建立在「minimap 像素座標 ↔ 世界 XZ 座標」的線性映射上。
3D 世界邊界取自 [[godot_camera_rig]] 的匯出值 `map_width` / `map_depth`（`camera_rig_3d.gd:21-22`）：

```
minimap 比例 r = local_pos / minimap_container.size      # (0,0)~(1,1)
world.x = r.x * cam_rig.map_width
world.z = r.y * cam_rig.map_depth
```

> 注意 minimap 的 Y 像素軸對應世界的 **Z** 軸（俯視圖慣例），不是 Y。

### 點擊 minimap → 主鏡頭飛過去

`MinimapContainer` 接收左鍵點擊，換算成世界座標後呼叫 `cam_rig.focus()`（`camera_rig_3d.gd:171`，內建 0.5s cubic tween）：

```gdscript
@export var cam_rig: Node3D            # 指向場景中的 CameraRig3D

func _gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton \
            and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
        var r := get_local_mouse_position() / size      # (0,0)~(1,1)
        var world := Vector3(r.x * cam_rig.map_width, 0.0, r.y * cam_rig.map_depth)
        cam_rig.focus(world)          # 平滑飛過去；focus(world, true) 則瞬移
```

> 用 `_gui_input` 而非 `_input`，事件只在點到容器範圍內才觸發，且座標已是容器局部座標。

### 視野框（反向：世界 → minimap）

每幀讀主鏡頭中心 `get_focus_point()`（`camera_rig_3d.gd:181`）與縮放 `get_zoom_normalized()`（行 185，0=遠 1=近），
反算成 minimap 局部座標畫一個空心矩形：

```gdscript
func _process(_delta: float) -> void:
    queue_redraw()        # 觸發 _draw

func _draw() -> void:
    var focus := cam_rig.get_focus_point()                        # Vector3 (x,0,z)
    var center := Vector2(focus.x / cam_rig.map_width,
                          focus.z / cam_rig.map_depth) * size      # → minimap 局部像素
    # zoom_n 越大（越近）視野越小；用它推矩形大小（係數依實測調）
    var zoom_n := cam_rig.get_zoom_normalized()
    var view_frac := lerp(0.45, 0.12, zoom_n)                      # 遠:大框 近:小框
    var rect_size := size * view_frac
    draw_rect(Rect2(center - rect_size * 0.5, rect_size),
              Color.WHITE, false, 1.5)                             # filled=false → 空心
```

> `view_frac` 的兩個端值需用實機目視校準（鏡頭仰角會影響地面可視範圍），CONCEPT.md（行 128-132）也標為待調。

---

## 效能模型

### 方案 B 的成本拆解

| 操作 | 頻率 | 成本 |
|------|------|------|
| 生地形底圖 | 地圖生成時一次（地形變動才重生）| `O(w*h)`，但只發生一次 |
| 單位疊加更新 | 單位移動時 | `O(單位數)`，再 `update()` 一張 texture |
| 迷霧疊加更新 | 視野變動時 | `O(變動格數)`，最差 `O(w*h)` |
| 視野框 `_draw` | 每幀 | `O(1)`（畫一個矩形）|

關鍵：**地形底圖一次性、與每幀無關**；常駐每幀成本只有一個 `draw_rect`。

### 更新頻率建議

- 單位/迷霧疊加層**不要每幀重建**。改成事件驅動（單位 `position_changed`、視野 `fog_updated` signal）或低頻節流（每 0.2~0.5s 一次）。
- `ImageTexture::update()` 重用同一張 GPU 紋理，比每次 `create_from_image()` 重新配置便宜得多；疊加層一律走 `update()`。

### 大地圖策略（對應 CONCEPT.md 行 141）

- **疊加層只刷動到的格子**：迷霧/單位更新時帶上 dirty rect，只 `set_pixel` 變動格，避免整張 `fill` 再全掃。
- **底圖固定不重生**：除非地形真的改變（如玩家造地），否則底圖生成後永久重用。
- **超大地圖降採樣**：當 `w*h` 過大（如 >512²）使 minimap 像素超過顯示框，生圖時每 N 格取樣一格
  （minimap 不需要逐格精度），底圖尺寸壓到框格大小附近即可。

### 方案 A 的成本

每次 SubViewport 更新 = 一次完整 3D pass（含 minimap 內所有可見物的 draw call）。
務必把 `render_target_update_mode` 設成節流模式或手動每 N 幀觸發；恆 `UPDATE_ALWAYS` 在大地圖會明顯吃幀。

---

## 待決定

逐項回應 CONCEPT.md（行 136-142）的待決定清單，並補上方案抉擇與座標細節。

- **方案 A vs B（總綱）**——**建議：採方案 B。** 理由：渲染成本與地圖大小脫鉤、可獨立設計高對比色盤、
  且能複用既有 `MapCoreWorldMap2DRenderer::generate_terrain_image()`，邊際成本極低（見〈兩種方案比較〉論證）。
  只有「小地圖需顯示即時 3D 特效」這一需求才回頭考慮方案 A，且仍建議用方案 B + 疊加層標記取代。

- **Minimap 尺寸：固定像素 vs 跟地圖長寬比縮放**——**建議：固定外框、內部 texture 維持地圖長寬比（letterbox）。**
  理由：HUD 角落空間是設計常數，框大小應固定；但地圖未必是正方形，若強行拉滿會變形破壞俯視可讀性。
  作法：`TextureRect.stretch_mode = STRETCH_KEEP_ASPECT_CENTERED`，框內留邊。
  座標換算須改用「實際貼圖矩形」而非整個容器，否則點擊定位會偏。

- **單位圖示：單像素 vs 2~3 像素小圖示**——**建議：依縮放分級。** minimap 多半放大顯示，單像素在小框會難以辨識；
  建議單位用 2~3 像素的 faction 色塊（在疊加層用 `fill_rect(Rect2i(x-1,y-1,3,3), col)`），重要單位（英雄/首都）再用小圖標 sprite 疊在最上層。
  理由：單像素只在像素密度極高的大地圖才夠用，一般情況可讀性不足。

- **地圖外框與 UI 裝飾風格**——**建議：用 `NinePatchRect` 做外框、`StyleBox` 統一描邊，與其他 HUD 元件同一套主題。**
  理由：裝飾屬美術主題範疇，不應寫死在 minimap 邏輯；用 `NinePatchRect` 可隨框尺寸自由縮放邊角不失真。
  這純為視覺，不影響座標換算。

- **大地圖效能：只在視野附近動態更新，遠處靜態**——**建議：底圖永久靜態 + 疊加層 dirty-rect 局部更新 + 超大圖降採樣。**
  理由（見〈效能模型〉）：地形底圖本就一次性，無「遠近」之分；真正需要節流的是疊加層，
  作法是事件驅動 + 只刷變動格，而非每幀全掃。遠處單位/迷霧更新可進一步降頻（玩家不會盯著 minimap 遠角看細節變化）。

- **（補充）minimap Y 軸對世界軸向**——**建議：minimap 像素 Y 軸固定對應世界 Z 軸**（俯視圖慣例），
  且座標邊界統一取 `camera_rig_3d.gd` 的 `map_width`/`map_depth`，避免 minimap 與 CameraRig 各持一份地圖尺寸而漂移。

- **（補充）河流是否畫進 minimap 底圖**——**建議：小框時用 `min_strength` 拉高（如 120~160）只保留大河，或乾脆不畫。**
  理由：`draw_rivers`（`world_map_2d_renderer.cpp:59`）在 `cell_px=1` 下河流線只有 1 像素，細流會變雜訊；
  大地圖小框上保留大河當地標即可。

---

*記錄時間：2026-05-23*
*狀態：概念補完為實作教學；推薦方案 B（複用 MapCoreWorldMap2DRenderer，cell_px=1 + 動態疊加層）。API 對齊 godot-cpp v4.6 stable 與 map_data.h 11 種地形常數*
