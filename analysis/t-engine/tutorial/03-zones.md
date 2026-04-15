# 教學 03：多地區與地區切換

> **目標**：為 `hellodungeon` 加入第二個地區（城鎮），並實作「進入地城 ↔ 返回城鎮」的雙向切換。理解 `Zone`、`changeLevel`、`change_level`/`change_zone` 地形欄位的完整工作原理。
>
> **前置條件**：完成教學 01 + 02。

---

## 目錄

1. [架構總覽：Zone、Level、Map 的關係](#1-架構總覽)
2. [第一步：changeLevel 工作原理](#2-第一步-changelevel-工作原理)
3. [第二步：建立城鎮地區](#3-第二步建立城鎮地區)
4. [第三步：傳送地形（進入/離開地城）](#4-第三步傳送地形)
5. [第四步：更新 Game.lua 支援多地區切換](#5-第四步更新-gamelua-支援多地區切換)
6. [第五步：起始地區設為城鎮](#6-第五步起始地區設為城鎮)
7. [第六步：地區切換時保留玩家位置](#7-第六步地區切換時保留玩家位置)
8. [第七步：on_enter 與 on_leave 回調](#8-第七步-on_enter-與-on_leave-回調)
9. [完整檔案結構變更](#9-完整檔案結構變更)
10. [常見錯誤排查](#10-常見錯誤排查)

---

## 1. 架構總覽

```
Game（全域）
 ├── game.zone   ← 當前 Zone 物件
 └── game.level  ← 當前 Level 物件（Zone 的一個樓層）
       └── game.level.map  ← 當前地圖

Zone（地區，如 "dungeon"、"town"）
 ├── short_name   ← 用於 changeLevel 的識別字串
 ├── max_level    ← 最多有幾個樓層
 └── [level 1], [level 2], ...  ← 每個樓層是一個 Level 物件

Level（樓層）
 ├── level        ← 樓層編號（1 = 第一層）
 ├── map          ← Map 物件（二維地形格陣列）
 ├── default_up   ← {x, y}：從下方進來時的出現點
 └── default_down ← {x, y}：從上方進來時的出現點
```

**地區切換流程**：

```
玩家踩上 change_level / change_zone 地形
  → Game:changeLevel(lev, zone_name)
       → zone:leaveLevel()         ← 儲存當前樓層狀態
       → Zone.new(zone_name)       ← 建立（或從快取讀取）新地區
       → zone:getLevel(lev)        ← 取得目標樓層（不存在就生成）
       → player:move(default_up/down)  ← 玩家移動到預設出現位置
       → level:addEntity(player)   ← 玩家加入新樓層
```

---

## 2. 第一步：changeLevel 工作原理

在 `example/class/Game.lua` 中已有完整的基礎實作：

```lua
function _M:changeLevel(lev, zone)
    local old_lev = (self.level and not zone) and self.level.level or -1000
    if zone then
        -- 離開舊地區
        if self.zone then
            self.zone:leaveLevel(false, lev, old_lev)
            self.zone:leave()
        end
        -- 建立新地區
        if type(zone) == "string" then
            self.zone = Zone.new(zone)
        else
            self.zone = zone
        end
    end
    -- 進入目標樓層
    self.zone:getLevel(self, lev, old_lev)

    -- 玩家出現在適當位置
    if lev > old_lev then
        self.player:move(self.level.default_up.x, self.level.default_up.y, true)
    else
        self.player:move(self.level.default_down.x, self.level.default_down.y, true)
    end
    self.level:addEntity(self.player)
end
```

**關鍵參數**：

| 情況 | `lev` | `zone` |
|------|-------|--------|
| 同地區下一層 | 當前層+1 | nil |
| 同地區上一層 | 當前層-1 | nil |
| 切換到新地區第1層 | 1 | `"zone_name"` |
| 切換到新地區特定層 | n | `"zone_name"` |

**地形觸發欄位**：

地形實體（Grid）上的兩個欄位控制切換行為：

```lua
change_level = 1,        -- 正數：往深處走（default_down 出現）
                          -- 負數：往上走（default_up 出現）
change_zone = "town",     -- 字串：切換到另一個地區（優先使用）
```

`Game:tick()` 或 `CHANGE_LEVEL` 按鍵動作讀取玩家腳下地形：

```lua
local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
if e.change_level then
    self:changeLevel(
        e.change_zone and e.change_level or self.level.level + e.change_level,
        e.change_zone
    )
end
```

注意：`e.change_zone` 存在時，`e.change_level` 是**目標地區的樓層號碼**（不是相對差值）。

---

## 3. 第二步：建立城鎮地區

城鎮是一個簡單的 Zone，只有 1 層，用 `Static`（靜態地圖）生成器，或暫時用 `Roomer` 也可以。

### 3.1 city/zone.lua

```lua
-- game/modules/hellodungeon/data/zones/town/zone.lua

return {
    name = "賢者城鎮",
    short_name = "town",
    level_range = {1, 1},
    level_scheme = "player",
    max_level = 1,

    -- 城鎮永久保存（玩家離開後地圖狀態不重置）
    persistent = "zone",

    -- 城鎮所有格子都亮著
    all_lited = true,

    -- 城鎮 NPC 不重新生成
    decay = {300, 800, no_respawn=true},

    -- 告訴 Zone 使用哪些類別
    on_setup = function(self)
        self:setup{
            npc_class    = "mod.class.NPC",
            grid_class   = "mod.class.Grid",
            object_class = "mod.class.Object",
        }
    end,

    generator = {
        map = {
            class = "engine.generator.map.Roomer",
            nb_rooms = 5,
            rooms = {"rect"},
            lite_room_chance = 100,
            floor = "FLOOR",
            wall  = "WALL",
            up    = "EXIT_TOWN",    -- 城鎮出口（進入地城）
            down  = "EXIT_TOWN",    -- 單層地區不需要向下
        },
        actor = {
            class = "engine.generator.actor.Random",
            nb_npc = {3, 5},        -- 幾個城鎮 NPC（村民等）
        },
        object = {
            class = "engine.generator.object.Random",
            nb_object = {0, 2},
        },
    },
}
```

### 3.2 town/grids.lua

```lua
-- game/modules/hellodungeon/data/zones/town/grids.lua

-- 載入共用地形
load("/data/general/grids/basic.lua")

-- 城鎮出口（進入地城第 1 層）
newEntity{
    define_as = "EXIT_TOWN",
    name = "地城入口",
    display = '>', color_r=200, color_g=100, color_b=50,
    always_remember = true,
    notice = true,
    -- change_zone：進入 "dungeon" 地區
    -- change_level：目標地區的第幾層（1 = 第一層）
    change_level = 1,
    change_zone = "dungeon",
}
```

### 3.3 town/npcs.lua 和 town/objects.lua

```lua
-- game/modules/hellodungeon/data/zones/town/npcs.lua
-- 暫時空白，或加入村民 NPC
```

```lua
-- game/modules/hellodungeon/data/zones/town/objects.lua
-- 暫時空白
```

### 3.4 更新地城地形：加入返回城鎮的出口

在 `data/zones/dungeon/grids.lua` 中更新 UP 地形，讓它能帶玩家回城鎮：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/grids.lua

load("/data/general/grids/basic.lua")

-- 覆蓋 UP 地形：第一層的上樓會回到城鎮
-- （需要在 Game:changeLevel 中判斷第一層特殊處理）
newEntity{
    define_as = "UP",
    name = "返回城鎮",
    display = '<', color_r=255, color_g=200, color_b=50,
    always_remember = true,
    notice = true,
    -- 第一層的 UP 指向城鎮，其他層指向上一層
    -- 具體邏輯在 CHANGE_LEVEL 事件中處理（見第四步）
    change_level = -1,      -- 預設：上一層（Game:changeLevel 會做特殊判斷）
}
```

更優雅的方式是在第一層放一個專用地形（`DUNGEON_EXIT`）：

```lua
newEntity{
    define_as = "DUNGEON_EXIT",
    name = "離開地城",
    display = '<', color_r=255, color_g=200, color_b=50,
    always_remember = true,
    notice = true,
    change_level = 1,       -- 城鎮只有 1 層
    change_zone = "town",   -- 回到城鎮
}
```

並在 `zone.lua` 的生成器中把第 1 層的 `up` 改為 `"DUNGEON_EXIT"`（可在 `post_process` 中動態替換）。

---

## 4. 第四步：更新 Game.lua 支援多地區切換

在 `Game.lua` 中把 `changeLevel` 和 `CHANGE_LEVEL` 按鍵綁定複製自 example 模組，加入必要修改：

```lua
-- game/modules/hellodungeon/class/Game.lua
-- （加入或修改以下函數）

function _M:changeLevel(lev, zone)
    local old_lev = (self.level and not zone) and self.level.level or -1000

    -- 離開舊地區前保存位置
    if self.level then
        local level = self.level
        if old_lev > lev then
            -- 往上走：記錄下行出現點
            level.exited = level.exited or {}
            level.exited.down = {x=self.player.x, y=self.player.y}
        else
            -- 往下走：記錄上行出現點
            level.exited = level.exited or {}
            level.exited.up = {x=self.player.x, y=self.player.y}
        end
        level:removeEntity(self.player)
    end

    if zone then
        if self.zone then
            self.zone:leaveLevel(false, lev, old_lev)
            self.zone:leave()
        end
        if type(zone) == "string" then
            self.zone = Zone.new(zone)
        else
            self.zone = zone
        end
    end

    self.zone:getLevel(self, lev, old_lev)

    -- 若舊地區有記錄返回位置，優先使用
    if lev > old_lev then
        local pos = self.level.exited and self.level.exited.up
        if pos then
            self.player:move(pos.x, pos.y, true)
        else
            self.player:move(self.level.default_up.x, self.level.default_up.y, true)
        end
    else
        local pos = self.level.exited and self.level.exited.down
        if pos then
            self.player:move(pos.x, pos.y, true)
        else
            self.player:move(self.level.default_down.x, self.level.default_down.y, true)
        end
    end

    self.level:addEntity(self.player)

    -- 重新計算玩家視野
    self.player:playerFOV()
end
```

在 `setupCommands()` 中加入 `CHANGE_LEVEL` 動作：

```lua
-- 在 Game:setupCommands() 的 key:addCommands 表格中加入：

CHANGE_LEVEL = function()
    local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
    if self.player:enoughEnergy() and e.change_level then
        -- change_zone 存在：切換到新地區，change_level 是目標層號
        -- change_zone 不存在：同地區，change_level 是相對差值
        self:changeLevel(
            e.change_zone and e.change_level or self.level.level + e.change_level,
            e.change_zone
        )
    else
        self.log("這裡沒有出口。")
    end
end,
```

確認 `load.lua` 載入了 `KeyBind:load("move,hotkeys,inventory,actions,interface,debug")`，其中 `actions` 包含 `CHANGE_LEVEL` 的預設按鍵（通常是 `<` 和 `>` 或 Enter）。

---

## 5. 第五步：起始地區設為城鎮

在 `Game:run()` 中將初始 `changeLevel` 改為從城鎮開始：

```lua
-- game/modules/hellodungeon/class/Game.lua

function _M:run()
    -- ... （初始化程式碼，與教學 01 相同）...

    -- 從城鎮開始，而不是直接進入地城
    self:changeLevel(1, "town")

    -- ... （其他初始化）...
end
```

---

## 6. 第六步：地區切換時保留玩家位置

**問題**：玩家進入地城後打了 5 層，回到城鎮，再進入地城，會從第幾層開始？

**引擎行為**：`Zone:getLevel(game, lev, old_lev)` 如果對應樓層已存在（`zone.memory_levels[lev]`），就直接讀取快取，不重新生成。所以玩家會回到第 1 層（城鎮出口指定 `change_level=1`）。

**如果想讓玩家回到「最後一次離開地城的那一層」**，需要追蹤這個狀態：

```lua
-- 在 Game.lua 中加入輔助功能：
function _M:changeLevel(lev, zone)
    -- ... 原本的程式碼 ...

    -- 特殊處理：記住玩家離開地城時在哪一層
    if zone and zone ~= (self.zone and self.zone.short_name) then
        if self.zone and self.zone.short_name == "dungeon" then
            -- 離開地城時記錄層數
            self.player.last_dungeon_level = self.level and self.level.level
        end
    end
end
```

---

## 7. 第七步：on_enter 與 on_leave 回調

Zone 支援進入/離開時的生命週期回調，放在 `zone.lua` 中：

```lua
-- data/zones/town/zone.lua

return {
    -- ... 其他欄位 ...

    -- 進入城鎮時觸發
    on_enter = function(self, lev, old_lev, zone)
        -- self = Zone 物件
        -- lev  = 要進入的樓層號
        -- zone = 來源地區（離開前的 Zone 物件，可能是 nil）
        game.log("#YELLOW#歡迎回到賢者城鎮！")
    end,

    -- 離開城鎮時觸發
    on_leave = function(self, lev, new_lev, new_zone)
        -- self = 即將離開的 Zone
        -- new_zone = 目標地區名稱（字串）
        if new_zone == "dungeon" then
            game.log("#RED#你進入了黑暗的地城…小心！")
        end
    end,
}
```

這兩個回調在 `Zone:getLevel()` 和 `Zone:leaveLevel()` 中被呼叫：

```lua
-- engine/Zone.lua（簡化版）
function _M:getLevel(game, lev, old_lev)
    -- ...生成或載入樓層...
    if self.on_enter then self:on_enter(lev, old_lev, old_zone) end
end

function _M:leaveLevel(no_close, lev, old_lev)
    if self.on_leave then self:on_leave(old_lev, lev, nil) end
    -- ...儲存樓層狀態...
end
```

---

## 8. 完整檔案結構變更

```
game/modules/hellodungeon/
├── class/
│   └── Game.lua                  ← 修改：changeLevel、CHANGE_LEVEL、run 起始地區
│
└── data/zones/
    ├── dungeon/
    │   ├── grids.lua             ← 修改：加入 DUNGEON_EXIT 地形
    │   └── zone.lua              ← 修改：UP 指向 DUNGEON_EXIT（或靠 Game 判斷）
    └── town/                     ← 新增目錄
        ├── zone.lua              ← 新增：城鎮地區設定
        ├── grids.lua             ← 新增：城鎮地形（含 EXIT_TOWN）
        ├── npcs.lua              ← 新增：城鎮 NPC（可暫時空白）
        └── objects.lua           ← 新增：城鎮物品（可暫時空白）
```

**共新增 4 個檔案，修改 2 個檔案**。

---

## 9. 常見錯誤排查

### 錯誤：`Zone.new: no such zone 'town'`

**原因**：Zone 是從 `data/zones/<short_name>/zone.lua` 載入的，路徑錯誤或拼寫不符。

**解法**：
- 確認目錄名稱為 `data/zones/town/`（與 `change_zone = "town"` 一致）
- 確認 `zone.lua` 中有 `short_name = "town"`

---

### 錯誤：玩家進入新地區後出現在 (0,0)

**原因**：Zone 生成時找不到 `default_up`/`default_down` 位置，預設落在 (0,0)。

**解法**：
- 地圖生成器必須設定 `up` 和 `down` 欄位，對應 `grids.lua` 中定義的地形 define_as
- `engine.generator.map.Roomer` 會自動找地形 `notice=true` 的格子作為起點/終點

---

### 錯誤：切換地區後地圖沒有更新（仍顯示舊地圖）

**原因**：`game.level.map.changed` 沒有被設為 `true`，或 FOV 沒有重新計算。

**解法**：在 `changeLevel` 末尾加入：

```lua
self.player:playerFOV()
self.level.map.changed = true
```

---

### 錯誤：`self.level.exited` 在重新生成地區後消失

**原因**：`level.exited` 需要在 `persistent = "zone"` 的設定下才會持久化。

**解法**：如果城鎮設了 `persistent = "zone"`，`level.exited` 就會在存檔時保留。地城若沒有設 persistent，每次重新進入都會重新生成樓層，`exited` 自然消失（符合 roguelike 風格）。

---

## 下一步

完成本教學後，hellodungeon 有兩個地區（城鎮 + 地城）可以互相切換。

下一個教學（**教學 04：任務系統與 NPC 對話**）將加入：
- 村長 NPC 給予討伐任務
- 對話腳本（Chat）
- Quest 狀態追蹤
- 擊殺頭目觸發任務完成
