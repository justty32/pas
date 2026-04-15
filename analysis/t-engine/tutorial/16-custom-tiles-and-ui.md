# 教學 16：地塊貼圖與自訂 UI 風格

---

## 第一部分：地圖地塊（Grid）貼圖

### 1.1 基本 Grid 顯示欄位

每個地形實體（Grid entity）有以下顯示相關欄位：

```lua
newEntity{
    define_as = "FLOOR",
    type = "floor", subtype = "floor",
    name  = "floor",

    -- 主貼圖，路徑相對於 /data/gfx/
    image = "terrain/marble_floor.png",

    -- ASCII 模式下的字元（fallback）
    display     = '.',
    color_r     = 255, color_g = 255, color_b = 255,
    back_color  = colors.DARK_GREY,

    -- Z 層級：1=地板，3=牆壁，18=牆頂蓋（顯示在角色之上）
    z = 1,
}
```

### 1.2 多層貼圖：`add_mos` 與 `add_displays`

| 欄位 | 用途 | 渲染方式 |
|------|------|---------|
| `add_mos` | 在同一 z 層疊加多張圖片（如裝飾圖案） | 同一渲染批次 |
| `add_displays` | 額外的虛擬實體，各自有獨立的 z/image | 分別進入渲染佇列 |

`add_mos` 範例（在地板上疊加出口標記）：
```lua
newEntity{
    define_as = "STAIRS_DOWN",
    type = "floor", subtype = "floor",
    name  = "stairs down",
    image = "terrain/marble_floor.png",
    add_mos = {
        {image = "terrain/dungeon_stairs_down.png"},
    },
    notice = true,
    change_level = 1,
}
```

`add_displays` 範例（牆壁 + 頂部蓋片）：
```lua
newEntity{
    define_as = "WALL_NORTH",
    base  = "WALL",
    -- 牆壁本體在 z=3
    image = "terrain/granite_wall1_1.png", z = 3,
    -- 牆頂蓋片在 z=18（渲染在角色之上，製造 3D 效果）
    add_displays = {
        class.new{image = "terrain/granite_wall3.png", z = 18, display_y = -1},
    },
}
```

> `display_y = -1`：圖片向上偏移一格顯示，`display_h = 2` 表示高度佔 2 格。這是 TE4 偽 3D 牆頂的關鍵技法。

---

### 1.3 簡單變體：隨機地板紋路

最基本的「讓地板看起來更豐富」做法是準備多張紋路圖，讓 NicerTiles 隨機選一張：

```lua
newEntity{
    define_as = "GRASS",
    type = "floor", subtype = "grass",
    name  = "grass",
    image = "terrain/grass/grass_main_01.png",
    display = '.', color = colors.LIGHT_GREEN,
    -- NicerTiles 以 nice_tiler.replace 隨機替換為 GRASS_PATCH1 ~ GRASS_PATCH14
    nice_tiler = { method="replace", base={"GRASS_PATCH", 100, 1, 14} },
}
-- 批次產生 14 個變體
for i = 1, 14 do
    newEntity{
        base       = "GRASS",
        define_as  = "GRASS_PATCH"..i,
        image      = ("terrain/grass/grass_main_%02d.png"):format(i),
    }
end
```

`nice_tiler.base` 格式：`{前綴, 出現機率%, 最小編號, 最大編號}`
- `{"GRASS_PATCH", 100, 1, 14}` → 必定替換，從 `GRASS_PATCH1` ~ `GRASS_PATCH14` 隨機選一個

---

### 1.4 `nice_tiler` 方法總覽

NicerTiles 在地圖生成後（`postProcessLevelTiles`）遍歷每個格子，依 `nice_tiler.method` 進行後處理：

| 方法 | 說明 | 典型用途 |
|------|------|---------|
| `"replace"` | 按機率隨機替換為一組變體 | 地板紋路隨機化 |
| `"wall3d"` | 偵測周圍格子，替換為正確的牆壁方向（柱子/北壁/南壁…） | 石牆、地牢牆壁 |
| `"wall3dSus"` | 進階牆壁，偵測對角格子，支援圓角 | 高精細地牢 |
| `"door3d"` | 門的方向偵測（水平門/垂直門） | 門 |
| `"singleWall"` | 單像素牆 | 特殊地形 |
| `"water"` | 水岸過渡（偵測周圍是否為草地/沙地） | 水岸邊緣 |
| `"genericBorders"` | 通用邊框過渡 | 任意兩種地形的邊界 |
| `"mountain3d"` | 山地地形 3D 效果 | 山嶺 |

### 1.5 `wall3d` 方法詳解

`wall3d` 是最常用的方法，它偵測 4 個方向（NSWE），根據鄰居類型選取對應的牆壁 Grid：

```lua
newEntity{
    define_as = "WALL",
    type = "wall", subtype = "cave",
    name  = "wall",
    image = "terrain/cave_wall1.png",
    z     = 3,
    nice_tiler = {
        method       = "wall3d",
        -- 牆壁包圍（內部）
        inner        = {"CAVE_WALL", 100, 1, 5},
        -- 北側有地板（牆頂暴露）
        north        = {"CAVE_WALL_NORTH", 100, 1, 3},
        -- 南側有地板（低邊）
        south        = {"CAVE_WALL_SOUTH", 100, 1, 5},
        -- 北南都有地板（獨立一格牆）
        north_south  = "CAVE_WALL_NORTH_SOUTH",
        -- 獨立小柱子（四邊都是地板）
        small_pillar = "CAVE_WALL_SMALL_PILLAR",
        -- 東西南都有地板（北邊牆）
        pillar_2     = "CAVE_WALL_PILLAR_2",
        -- 其他柱子形狀
        pillar_8     = {"CAVE_WALL_PILLAR_8", 100, 1, 3},
        pillar_4     = "CAVE_WALL_PILLAR_4",
        pillar_6     = "CAVE_WALL_PILLAR_6",
    },
    does_block_move = true,
    block_sight     = true,
    dig             = "CAVE_FLOOR",
}
```

接著定義所有被 `wall3d` 引用的 Grid 變體：
```lua
-- 內部牆（被牆包圍），5 個紋路
for i = 1, 5 do
    newEntity{ base="WALL", define_as="CAVE_WALL"..i,
        image = ("terrain/cave_wall1_%d.png"):format(i), z=3 }
end
-- 北牆（頂部有牆頂蓋）
for i = 1, 3 do
    newEntity{ base="WALL", define_as="CAVE_WALL_NORTH"..i,
        image = ("terrain/cave_wall1_%d.png"):format(i), z=3,
        add_displays = {
            class.new{image="terrain/cave_wall3.png", z=18, display_y=-1},
        },
    }
end
-- 南牆
for i = 1, 5 do
    newEntity{ base="WALL", define_as="CAVE_WALL_SOUTH"..i,
        image = ("terrain/cave_wall2_%d.png"):format(i), z=3 }
end
newEntity{ base="WALL", define_as="CAVE_WALL_NORTH_SOUTH",
    image="terrain/cave_wall2.png", z=3,
    add_displays={class.new{image="terrain/cave_wall3.png",z=18,display_y=-1}}}
-- 其他柱子略...
```

### 1.6 `nice_editer`：不替換只疊加邊框

`nice_editer` 不替換整個格子，而是在現有格子上疊加邊框裝飾（如草地和石地的接縫）：

```lua
local grass_editer = { method="borders_def", def="grass" }

newEntity{
    define_as = "GRASS",
    type = "floor", subtype = "grass",
    ...
    nice_tiler  = { method="replace", base={"GRASS_PATCH", 100, 1, 14} },
    nice_editer = grass_editer,   -- 疊加草地邊框（與其他 subtype 的接縫）
}
```

`borders_def` 使用在 `NicerTiles.lua` 中 `local defs` 表預先定義的邊框規則：
```lua
-- NicerTiles.lua 中的定義（節錄）
defs.grass = {
    method = "borders",
    type   = "grass",
    forbid = {lava=true, rock=true},
    -- 南側有非草地 → 疊加北側草邊
    default8 = {add_mos={{image="terrain/grass/grass_2_%02d.png", display_y=-1}}, min=1, max=2},
    -- 北側有非草地 → 疊加南側草邊
    default2 = {add_mos={{image="terrain/grass/grass_8_%02d.png", display_y=1}},  min=1, max=2},
    ...
}
```

若要新增自訂的 `borders_def`，只需在模組自己的 NicerTiles 繼承類中擴充 `defs` 表。

### 1.7 PNG 檔案規格（地塊）

- 尺寸：**64×64** 像素（TE4 標準格子大小）
- 格式：RGBA（可有透明區域）
- 命名慣例：`terrain/CATEGORY/TILENAME_NN.png`（NN 為 2 位數字補零）
- 牆頂蓋片（`display_y=-1` 用）尺寸可以是 64×64 或更高

---

## 第二部分：自訂 UI 風格

### 2.1 UI 主題系統原理

TE4 的所有 UI 元件都繼承自 `engine.ui.Base`，使用 **9-slice** 技術繪製可縮放的框架。

主題名稱（如 `"dark"`、`"metal"`、`"stone"`）決定 PNG 的查找路徑：

```
getUITexture("ui/dialogframe_1.png")
  ├─ 先找 /data/gfx/{ui_name}-ui/dialogframe_1.png
  └─ 找不到就 fallback → /data/gfx/{defaultui}-ui/dialogframe_1.png
```

例如主題為 `"dark"` 時，查找路徑是 `/data/gfx/dark-ui/dialogframe_1.png`。

### 2.2 主題定義檔

主題除了 PNG 外，還需要一個 Lua 配置檔說明框架的邊距和陰影：

```lua
-- 格式：在 ui/definitions/*.lua 中（setfenv 到 ui_conf）
mytheme = {
    frame_shadow = {x=10, y=10, a=0.5},  -- 陰影偏移和透明度（nil=不顯示陰影）
    frame_alpha  = 0.95,                  -- 整體透明度
    frame_ox1    = -42,                   -- 左/上邊外擴距離（像素）
    frame_ox2    =  42,                   -- 右/下邊外擴距離
    frame_oy1    = -42,
    frame_oy2    =  42,
    title_bar    = {x=0, y=-18, w=4, h=25},  -- 標題欄配置（可省略）
}
```

> `frame_ox` 控制框架圖片相對於對話框內容區域的外擴量。`dark` 主題的 42px 對應其華麗的邊框圖。若使用簡單邊框，設小一些（如 2px）。

### 2.3 建立自訂 UI 主題（逐步說明）

**步驟一：建立 PNG 資料夾**

```
mod/data/gfx/mytheme-ui/
    dialogframe_1.png   ← 左下角
    dialogframe_2.png   ← 下邊（水平平鋪）
    dialogframe_3.png   ← 右下角
    dialogframe_4.png   ← 左邊（垂直平鋪）
    dialogframe_5.png   ← 中央（水平+垂直平鋪）
    dialogframe_6.png   ← 右邊（垂直平鋪）
    dialogframe_7.png   ← 左上角
    dialogframe_8.png   ← 上邊（水平平鋪）
    dialogframe_9.png   ← 右上角
    button1.png ~ button9.png        ← 按鈕（9-slice）
    button_sel1.png ~ button_sel9.png ← 按鈕（懸停/選中態）
    [其餘元件，可從 dark-ui 複製後修改]
```

9-slice 角位置圖示（對應數字鍵盤位置）：
```
7 ─ 8 ─ 9
│       │
4   5   6
│       │
1 ─ 2 ─ 3
```

**步驟二：建立主題定義檔**

```lua
-- mod/data/gfx/ui/definitions/mytheme.lua
mytheme = {
    frame_shadow = {x=8, y=8, a=0.4},
    frame_alpha  = 1.0,
    frame_ox1    = -6,
    frame_ox2    =  6,
    frame_oy1    = -6,
    frame_oy2    =  6,
}
```

**步驟三：在遊戲載入時註冊主題**

```lua
-- mod/load.lua（模組入口）
local UIBase = require "engine.ui.Base"

-- 載入主題定義
UIBase:loadUIDefinitions("/data/gfx/ui/definitions/mytheme.lua")

-- 將全域預設 UI 切換為新主題
UIBase:changeDefault("mytheme")
```

### 2.4 只對特定對話框套用自訂主題

不需要全域切換，也可以在建立 Dialog 時指定 `ui` 欄位：

```lua
local d = require("engine.ui.Dialog").new(
    "我的對話框", 400, 300,
    nil, nil,
    "mytheme"    -- 只有這個 dialog 使用自訂主題
)
d:loadUI{
    ...
}
```

或在模組自己的 Dialog 子類中設定預設值：

```lua
module(..., package.seeall, class.inherit(engine.ui.Dialog))

_M.ui = "mytheme"   -- 此類所有對話框都使用 mytheme
```

### 2.5 完整 UI 主題 PNG 清單

以下是 `dark-ui` 主題中完整的 PNG 清單，建立新主題時可以參考（只需提供想修改的，其餘自動 fallback）：

**對話框框架**（9 片）：
```
dialogframe_1.png ~ dialogframe_9.png
title_dialogframe_7.png / _8.png / _9.png  ← 有標題欄時的頂邊變體
```

**按鈕**（各 9 片）：
```
button1.png ~ button9.png           ← 普通態
button_sel1.png ~ button_sel9.png   ← 選中/懸停態
```

**列表選擇器**（各 9 片）：
```
selector1-9.png        ← 普通選擇條
selector-sel1-9.png    ← 選中態
selector-green1-9.png  ← 綠色變體（用於確認類操作）
heading1-9.png         ← 標題行
heading-sel1-9.png     ← 標題行選中態
```

**文字輸入框**（各 9 片 + 游標）：
```
textbox1-9.png
textbox-sel1-9.png
textbox-cursor.png
```

**捲軸**：
```
scrollbar.png / scrollbar-sel.png
scrollbar_top.png / scrollbar_bottom.png
```

**其他**：
```
checkbox.png / checkbox-ok.png
minus.png / plus.png
border_hor_left/middle/right.png
border_vert_top/middle/bottom.png
bar_title_left/middle/right.png
```

**子資料夾**：
```
tooltip/1-9.png + tooltip/frame1-9.png  ← tooltip 框架
icon-frame/frame1-9.png                 ← 技能/物品圖示邊框
waiter/left_basic.png + right_basic.png ← 進度條
```

### 2.6 最小可用主題

若只想替換對話框框架，其餘元件保持預設，只需提供 9 張圖：

```
mod/data/gfx/mytheme-ui/
    dialogframe_1.png ~ dialogframe_9.png
```

定義檔：
```lua
mytheme = {
    frame_shadow = {x=5, y=5, a=0.3},
    frame_alpha  = 0.95,
    frame_ox1    = -8,
    frame_ox2    =  8,
    frame_oy1    = -8,
    frame_oy2    =  8,
}
```

其他元件（按鈕、選擇器等）會自動 fallback 到 `dark-ui/` 的對應 PNG。

---

## 第三部分：完整範例

### 3.1 範例：建立洞穴主題地塊

```lua
-- mod/data/general/grids/cave.lua

-- 地板（14 種隨機紋路）
newEntity{
    define_as = "CAVE_FLOOR",
    type = "floor", subtype = "cave",
    name = "cave floor",
    image = "terrain/cave/floor_01.png",
    display = '.', color = colors.GREY,
    nice_tiler = { method="replace", base={"CAVE_FLOOR", 100, 1, 14} },
}
for i = 1, 14 do
    newEntity{ base="CAVE_FLOOR", define_as="CAVE_FLOOR"..i,
        image=("terrain/cave/floor_%02d.png"):format(i) }
end

-- 牆壁（使用 wall3d 方法）
newEntity{
    define_as  = "CAVE_WALL",
    type       = "wall", subtype = "cave",
    name       = "cave wall",
    image      = "terrain/cave/wall1_01.png",
    display    = '#', color = colors.GREY,
    z          = 3,
    nice_tiler = {
        method       = "wall3d",
        inner        = {"CAVE_WALL_INNER", 100, 1, 5},
        north        = {"CAVE_WALL_NORTH", 100, 1, 3},
        south        = {"CAVE_WALL_SOUTH", 100, 1, 5},
        north_south  = "CAVE_WALL_NS",
        small_pillar = "CAVE_WALL_PILLAR_SMALL",
        pillar_2     = "CAVE_WALL_PILLAR_2",
        pillar_8     = {"CAVE_WALL_PILLAR_8", 100, 1, 3},
        pillar_4     = "CAVE_WALL_PILLAR_4",
        pillar_6     = "CAVE_WALL_PILLAR_6",
    },
    does_block_move = true,
    block_sight     = true,
    always_remember = true,
    dig             = "CAVE_FLOOR",
}

-- 牆壁內部（被牆包圍）
for i = 1, 5 do
    newEntity{ base="CAVE_WALL", define_as="CAVE_WALL_INNER"..i, z=3,
        image=("terrain/cave/wall1_%02d.png"):format(i) }
end

-- 北牆（頂部有牆蓋）
local wall_top = class.new{image="terrain/cave/wall3.png", z=18, display_y=-1}
for i = 1, 3 do
    newEntity{ base="CAVE_WALL", define_as="CAVE_WALL_NORTH"..i, z=3,
        image=("terrain/cave/wall1_%02d.png"):format(i),
        add_displays={wall_top} }
end

-- 南牆
for i = 1, 5 do
    newEntity{ base="CAVE_WALL", define_as="CAVE_WALL_SOUTH"..i, z=3,
        image=("terrain/cave/wall2_%02d.png"):format(i) }
end

-- 北南牆（獨立橫條）
newEntity{ base="CAVE_WALL", define_as="CAVE_WALL_NS", z=3,
    image="terrain/cave/wall2.png", add_displays={wall_top} }

-- 柱子（略，同上模式）

-- 樓梯
newEntity{
    define_as    = "CAVE_STAIRS_DOWN",
    type         = "floor", subtype = "cave",
    name         = "stairs down",
    image        = "terrain/cave/floor_01.png",
    add_mos      = {{image="terrain/dungeon_stairs_down.png"}},
    display      = '>', color = colors.YELLOW,
    notice       = true,
    always_remember = true,
    change_level = 1,
}
```

### 3.2 範例：羊皮紙主題 UI

```lua
-- mod/data/gfx/ui/definitions/parchment_custom.lua
parchment_custom = {
    frame_shadow = {x=6, y=6, a=0.35},
    frame_alpha  = 1.0,
    frame_ox1    = -12,
    frame_ox2    =  12,
    frame_oy1    = -12,
    frame_oy2    =  12,
}
```

```
-- 所需 PNG 目錄結構
mod/data/gfx/parchment_custom-ui/
    dialogframe_1.png   ← 羊皮紙左下角
    dialogframe_2.png   ← 下邊（平鋪）
    ...（共 9 張）
```

```lua
-- mod/load.lua
local UIBase = require "engine.ui.Base"
UIBase:loadUIDefinitions("/data/gfx/ui/definitions/parchment_custom.lua")
UIBase:changeDefault("parchment_custom")
```

只針對特定對話框：
```lua
-- 在 Dialog subclass 或 Dialog.new 呼叫時
self.ui = "parchment_custom"
```

---

## 重點總結

**地塊貼圖**
- `image` 欄位 → `/data/gfx/` 相對路徑的 PNG
- `add_mos` → 在同 z 層疊加裝飾圖
- `add_displays` → 在不同 z 層新增子實體（牆頂蓋用 z=18, display_y=-1）
- `nice_tiler = {method="replace", base={"PREFIX", 100, 1, N}}` → 隨機地板紋路
- `nice_tiler = {method="wall3d", inner=..., north=..., south=...}` → 自動牆壁方向偵測

**UI 主題**
- PNG 放在 `/data/gfx/THEMENAME-ui/` 資料夾
- 定義檔設定 `frame_ox`、`frame_shadow` 等參數
- `UIBase:loadUIDefinitions(file)` → 載入定義
- `UIBase:changeDefault("mytheme")` → 全域切換
- `Dialog.new(title, w, h, nil, nil, "mytheme")` → 單一對話框使用特定主題
- 缺少的 PNG 自動 fallback 到 `dark-ui/`，可以只提供想修改的部分
