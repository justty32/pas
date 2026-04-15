# 教學 12：自訂大地圖（World Map）

## 本章目標

建立一個完整的自訂世界——一張玩家可自由走動的**大地圖**，地圖上散佈著可進入的地點：

- **起點村莊**：玩家出生的城鎮
- **野外據點**：Tutorial 10/11 的 Base Camp
- **森林地牢**：有多層的隨機地牢
- **山區要塞**：特殊 Boss 地牢
- **海邊港口**：另一個城鎮

玩家在大地圖上移動到地點標記後按 `>` 進入，子地圖內有出口可返回大地圖，且記得上次在大地圖上的位置。

---

## 系統核心概念

### 大地圖只是一個特殊的 Zone

TE4 沒有「World Map 系統」這個獨立概念——大地圖就是一個設定了特殊屬性的普通 Zone：

| 屬性 | 說明 |
|------|------|
| `all_remembered = true` | 所有格子從一開始就顯示在 minimap 上 |
| `all_lited = true` | 不需要光源，整張地圖都可見 |
| `persistent = "zone"` | 離開後保留玩家走過的路、踩過的地形狀態 |
| 靜態地圖 | 手工設計（ASCII），不隨機生成 |

### 地點進入機制（`change_zone` + `change_level`）

大地圖上的「地點標記」是普通地形 Grid，但帶有兩個特殊欄位：

```lua
change_level = 1,           -- 進入目標 Zone 的第幾層
change_zone  = "town_a",    -- 目標 Zone 的 short_name
```

引擎的 `CHANGE_LEVEL` 按鍵（預設 `>`）掃描玩家所站的地形，若發現這兩個欄位就呼叫 `game:changeLevel()`。

### 返回大地圖

子地圖（城鎮、地牢）的出口地形也是同樣機制，只是 `change_zone = "wilderness"`：

```lua
-- 子地圖出口
change_level = 1,
change_zone  = "wilderness",
-- 玩家返回大地圖時，會出現在進入時所在的座標（由 level.last_exit 記錄）
```

### 玩家返回位置的記錄

`game:changeLevel(lev, zone_name)` 內部會把**離開時的座標**存入新 Zone 的 Level 資料中，讓玩家從子地圖返回時出現在正確位置，而不是重回 `startx`/`starty`。

---

## 完整檔案結構

```
mygame/
  mod/
    class/
      Game.lua                      ← 修改 newGame() 起始於大地圖
    data/
      grids/
        wilderness.lua              ← 大地圖地形（草地、森林、山、水、路、地點標記）
      zones/
        wilderness/
          zone.lua                  ← 大地圖 Zone 定義
        town_a/
          zone.lua                  ← 起點村莊 Zone
        town_b/
          zone.lua                  ← 海邊港口 Zone
        dungeon_forest/
          zone.lua                  ← 森林地牢 Zone
        dungeon_fortress/
          zone.lua                  ← 山區要塞 Zone
      maps/
        wilderness.lua              ← 大地圖靜態 ASCII（50×30）
        town_a.lua                  ← 起點村莊靜態地圖
```

---

## 步驟一：大地圖地形定義

### 檔案：`mod/data/grids/wilderness.lua`

大地圖地形分兩類：
1. **背景地形**：草地、森林、山脈、水域、道路（可走 / 不可走）
2. **地點標記**：帶 `change_zone` 的特殊地形（城鎮入口、地牢入口）

```lua
-- mod/data/grids/wilderness.lua
-- 大地圖地形定義

-- ── 可通行地形 ──────────────────────────────────────────────────

newEntity{
    define_as = "GRASS",
    name = "草地",
    display = '.', color_r=80,  color_g=160, color_b=50,
    back_color = colors.DARK_GREEN,
    always_remember = true,
}

newEntity{
    define_as = "ROAD",
    name = "道路",
    display = '+', color_r=200, color_g=180, color_b=130,
    back_color = colors.DARK_UMBER,
    always_remember = true,
    -- 道路讓移動稍快（可選：設定 movement_speed_factor）
}

newEntity{
    define_as = "SHALLOW_WATER",
    name = "淺灘",
    display = '~', color_r=80,  color_g=150, color_b=220,
    back_color = colors.DARK_BLUE,
    always_remember = true,
    -- 淺灘可通行但速度減慢（簡化版：視為可通行）
}

-- ── 不可通行地形 ────────────────────────────────────────────────

newEntity{
    define_as = "DEEP_WATER",
    name = "深水",
    display = '~', color_r=0,   color_g=80,  color_b=200,
    back_color = colors.DARK_BLUE,
    always_remember = true,
    does_block_move = true,
}

newEntity{
    define_as = "MOUNTAIN",
    name = "山脈",
    display = '^', color_r=160, color_g=150, color_b=130,
    back_color = colors.DARK_GREY,
    always_remember = true,
    does_block_move = true,
    block_sight     = true,
}

newEntity{
    define_as = "FOREST",
    name = "森林",
    display = 'T', color_r=0,   color_g=120, color_b=30,
    back_color = colors.DARK_GREEN,
    always_remember = true,
    -- 森林可通行（不阻擋移動），但阻擋視線
    block_sight     = true,
}

-- ── 地點標記（帶 change_zone / change_level） ─────────────────
-- 玩家站上後按 > 進入對應 Zone

newEntity{
    define_as = "TOWN_A_ENTRANCE",
    name = "起點村莊",
    display = 'A', color_r=255, color_g=220, color_b=50,
    back_color = colors.DARK_UMBER,
    notice          = true,
    always_remember = true,
    change_level = 1,
    change_zone  = "town_a",
}

newEntity{
    define_as = "TOWN_B_ENTRANCE",
    name = "海邊港口",
    display = 'B', color_r=100, color_g=200, color_b=255,
    back_color = colors.DARK_BLUE,
    notice          = true,
    always_remember = true,
    change_level = 1,
    change_zone  = "town_b",
}

newEntity{
    define_as = "CAMP_ENTRANCE",
    name = "野外據點",
    display = 'C', color_r=0,   color_g=255, color_b=150,
    back_color = colors.DARK_GREEN,
    notice          = true,
    always_remember = true,
    change_level = 1,
    change_zone  = "camp",
}

newEntity{
    define_as = "DUNGEON_FOREST_ENTRANCE",
    name = "森林地牢",
    display = 'D', color_r=200, color_g=80,  color_b=80,
    back_color = colors.DARK_RED,
    notice          = true,
    always_remember = true,
    change_level = 1,
    change_zone  = "dungeon_forest",
}

newEntity{
    define_as = "DUNGEON_FORTRESS_ENTRANCE",
    name = "山區要塞",
    display = 'F', color_r=255, color_g=100, color_b=0,
    back_color = colors.DARK_GREY,
    notice          = true,
    always_remember = true,
    change_level = 1,
    change_zone  = "dungeon_fortress",
}
```

---

## 步驟二：大地圖靜態地圖

### 檔案：`mod/data/maps/wilderness.lua`

設計原則：
- 地圖至少要能讓所有地點看起來「有距離感」，建議 50×30 以上
- 用道路（`+`）串連主要地點，讓玩家有方向感
- 山脈和水域劃分不同區域，增加探索感
- `startx`/`starty` 設在起點村莊旁邊

```lua
-- mod/data/maps/wilderness.lua
-- 大地圖（50 寬 × 30 高）
--
-- 圖例：
--   .  = 草地      T  = 森林      ^  = 山脈
--   ~  = 深水       +  = 道路      -  = 淺灘（河流）
--   A  = 起點村莊   B  = 海邊港口  C  = 野外據點
--   D  = 森林地牢   F  = 山區要塞

defineTile('.', "GRASS")
defineTile('T', "FOREST")
defineTile('^', "MOUNTAIN")
defineTile('~', "DEEP_WATER")
defineTile('-', "SHALLOW_WATER")
defineTile('+', "ROAD")
defineTile('A', "TOWN_A_ENTRANCE")
defineTile('B', "TOWN_B_ENTRANCE")
defineTile('C', "CAMP_ENTRANCE")
defineTile('D', "DUNGEON_FOREST_ENTRANCE")
defineTile('F', "DUNGEON_FORTRESS_ENTRANCE")

-- 玩家出生在起點村莊（A）旁邊一格
startx = 11
starty = 20

return [[
..................................................
..................................................
....TTTTTTTTT.....................................
...TTTTTTTTTTT....................................
...TTTTTTTTTTT...^^^^^^^^^^^^^^^^^................
....TTTTTTTTT....^^^^^^^^^^^^^^^^^^...............
.............D...^^^^^^^^^^^^^^^^^^^..............
..............TTTT^^^^^^^^^^^^^^^^^^^.............
..............TTTT^^^^^^^^^^^^^^^^^^..............
...............TTTF^^^^^^^^^^^^^^^^^..............
................TTT^^^^^^^^^^^^^^^^^^.............
................TTT^^^^^^^^^^^^^^^^^^.............
.................TT^^^^^^^^^.....^^^..............
....................^^^^^^^.......^^^..............
..C..................^^^^^^.......^^^.............~
..+..................^^^^^........^^^............~~
..+.................^^^^^^......................~~~
..+.................^^^^^^^^^.................~~~~
..+...................^^^^^^^^...............~~~~~
..+......................^^^^^............~~~~~~~~
..+..A.....++++++++......^^^^..........~~~~~~~~~~
..+++++++++.........++++++++++.....B.~~~~~~~~~~~.
..........................+++++++++++~~~~~~~~~~~~.
...................................~~~~~~~~~~~~~~.
...................................~~~~~~~~~~~~~~.
....................................~~~~~~~~~~~~~.
.....................................~~~~~~~~~~~~.
......................................~~~~~~~~~~..
.........................................~~~~~~~..
..................................................
]]
```

> **設計說明：**
> - 西北角是茂密森林，森林內有 `D`（森林地牢）
> - 中央偏北是連綿山脈，山中有 `F`（山區要塞）
> - 西南有 `C`（野外據點），透過道路 `+` 向東連接
> - `A`（起點村莊）在西側道路旁，玩家起始位置在其右側
> - 道路向東延伸到 `B`（海邊港口），港口位於東南水域旁
> - 東側是大片水域，不可通行

---

## 步驟三：大地圖 Zone 定義

### 檔案：`mod/data/zones/wilderness/zone.lua`

```lua
-- mod/data/zones/wilderness/zone.lua
-- 大地圖 Zone：整個世界的俯瞰地圖

local Zone = require "engine.Zone"

return Zone.new("wilderness", {
    name      = "世界地圖",
    level_range = {1, 1},
    max_level   = 1,

    -- 地圖尺寸必須與 wilderness.lua 的 ASCII 一致
    width  = 50,
    height = 30,

    -- ★ 大地圖通常設為持久化
    -- 若大地圖有動態地點解鎖（如摧毀敵營後地形改變），需要 persistent
    persistent = "zone",

    -- 整張地圖從一開始就全部可見
    all_remembered = true,
    all_lited      = true,

    -- 只載入大地圖地形（不需要 NPC / Object 列表）
    grid_list = require("mod.class.Grid"):loadList{
        "mod/data/grids/wilderness.lua",
    },
    npc_list    = {},   -- 大地圖上不放置 NPC（或可加入旅行商人）
    object_list = {},

    generator = {
        map = {
            class = "engine.generator.map.Static",
            map   = "wilderness",   -- 對應 data/maps/wilderness.lua
        },
        actor = {
            class = "engine.generator.actor.OnceAtCoord",
        },
    },

    -- 進入大地圖時的提示
    on_enter = function(lev, old_lev)
        if old_lev then  -- 從子地圖返回
            game.logPlayer(game.player,
                "你回到了世界地圖。")
        else             -- 首次進入（遊戲開始）
            game.logPlayer(game.player,
                "#LIGHT_GREEN#歡迎來到這個世界。按 [>] 進入地點，按 [方向鍵] 在地圖上移動。")
        end
    end,
})
```

---

## 步驟四：起點村莊 Zone

### 檔案：`mod/data/zones/town_a/zone.lua`

城鎮使用靜態地圖（手工設計），並設定持久化。

```lua
-- mod/data/zones/town_a/zone.lua
-- 起點村莊

local Zone = require "engine.Zone"

return Zone.new("town_a", {
    name        = "起點村莊",
    level_range = {1, 1},
    max_level   = 1,

    width  = 30,
    height = 25,

    persistent    = "zone",
    all_remembered = true,
    all_lited      = true,

    grid_list = require("mod.class.Grid"):loadList{
        "mod/data/grids/general.lua",
        "mod/data/grids/town.lua",    -- 城鎮專用地形
    },
    npc_list = require("mod.class.NPC"):loadList{
        "mod/data/npcs/town_a_npcs.lua",  -- 村莊居民、商人
    },
    object_list = require("mod.class.Object"):loadList{
        "mod/data/objects/consumables.lua",
        "mod/data/objects/equipment.lua",
    },

    generator = {
        map   = {class = "engine.generator.map.Static", map = "town_a"},
        actor = {class = "engine.generator.actor.OnceAtCoord"},
    },

    on_enter = function(lev, old_lev)
        game.logPlayer(game.player, "#YELLOW#你進入了起點村莊。")
    end,
})
```

### 城鎮出口地形（`mod/data/grids/town.lua` 摘錄）

每個城鎮都需要一個「出口」地形，讓玩家返回大地圖：

```lua
-- mod/data/grids/town.lua（摘錄）

-- 城鎮通用地板 / 牆壁
newEntity{define_as="TOWN_FLOOR", name="石板地",
    display='.', color_r=180, color_g=180, color_b=160,
    back_color=colors.DARK_GREY}

newEntity{define_as="TOWN_WALL", name="石牆",
    display='#', color_r=150, color_g=150, color_b=150,
    back_color=colors.DARK_GREY,
    always_remember=true, does_block_move=true, block_sight=true}

-- ★ 關鍵：城鎮出口 → 返回大地圖
newEntity{
    define_as = "TOWN_EXIT",
    name = "城鎮出口",
    display = '<', color_r=255, color_g=255, color_b=0,
    back_color = colors.DARK_GREY,
    notice          = true,
    always_remember = true,

    -- 返回 wilderness Zone 的第 1 層
    change_level = 1,
    change_zone  = "wilderness",
}
```

### 城鎮靜態地圖（`mod/data/maps/town_a.lua`）

```lua
-- mod/data/maps/town_a.lua
-- 起點村莊（30×25）

defineTile('.', "TOWN_FLOOR")
defineTile('#', "TOWN_WALL")
defineTile('+', "TOWN_DOOR")
defineTile('<', "TOWN_EXIT")
defineTile('t', "TOWN_TREE")
defineTile('s', "TOWN_FLOOR", nil, "SHOPKEEPER_NPC")  -- 商人
defineTile('q', "TOWN_FLOOR", nil, "QUEST_GIVER_NPC") -- 任務發布者

startx = 15
starty = 22   -- 玩家進入時出現在出口附近

return [[
##############################
#............................#
#............................#
#....t....#######....t.......#
#.........#.....#............#
#.........#..s..#............#
#.........#.....#............#
#.........+.....+............#
#..........#####.............#
#............................#
#......#########.............#
#......#.......#.............#
#......#...q...#.............#
#......#.......#.............#
#......+.......+.............#
#......#########.............#
#............................#
#............................#
#..t.......................t.#
#............................#
#............................#
#............................#
#............................#
#...............<............#
##############################
]]
```

---

## 步驟五：地牢 Zone（隨機生成）

與城鎮不同，地牢使用**隨機生成**（`Roomer` 演算法），有多層，且不持久化（每次進入重新生成）。

### 檔案：`mod/data/zones/dungeon_forest/zone.lua`

```lua
-- mod/data/zones/dungeon_forest/zone.lua
-- 森林地牢（3 層，隨機生成）

local Zone = require "engine.Zone"

return Zone.new("dungeon_forest", {
    name        = "森林地牢",
    level_range = {1, 3},   -- 第 1 ~ 3 層
    max_level   = 3,

    width  = 50,
    height = 50,

    -- 地牢不需要持久化：每次進入重新生成（更有新鮮感）
    -- 若要保留探索狀態，設為 persistent = "zone"
    persistent = false,

    -- 地牢黑暗，需要光源 / FOV
    all_remembered = false,
    all_lited      = false,

    grid_list = require("mod.class.Grid"):loadList{
        "mod/data/grids/dungeon_forest.lua",
    },
    npc_list = require("mod.class.NPC"):loadList{
        "mod/data/npcs/forest_monsters.lua",
    },
    object_list = require("mod.class.Object"):loadList{
        "mod/data/objects/consumables.lua",
        "mod/data/objects/equipment.lua",
        "mod/data/objects/materials.lua",
    },

    -- 隨機地圖產生
    generator = {
        map = {
            class  = "engine.generator.map.Roomer",
            floor  = "DUNGEON_FLOOR",
            wall   = "DUNGEON_WALL",
            door   = "DUNGEON_DOOR",
            up     = "DUNGEON_STAIRS_UP",
            down   = "DUNGEON_STAIRS_DOWN",
            -- 房間數量與尺寸
            rooms  = {6, 12},
            lite_room = false,
        },
        actor = {
            class    = "engine.generator.actor.Random",
            nb_npc   = {5, 10},    -- 每層 5~10 個敵人
            guardian = "FOREST_BOSS",  -- 最後一層有 Boss（可選）
        },
        object = {
            class  = "engine.generator.object.Random",
            nb_obj = {3, 6},
        },
    },

    -- 最深層（第 3 層）的進入回呼
    on_enter = function(lev, old_lev)
        if lev == 3 then
            game.logPlayer(game.player,
                "#RED#你感受到一股強烈的邪惡氣息……這裡住著什麼強大的東西。")
        end
    end,
})
```

### 地牢的樓梯地形（`mod/data/grids/dungeon_forest.lua` 摘錄）

地牢各層之間用樓梯連接，最底層（第 3 層）的向上樓梯返回大地圖：

```lua
-- mod/data/grids/dungeon_forest.lua（摘錄）

newEntity{define_as="DUNGEON_FLOOR", name="泥土地板",
    display='.', color_r=100, color_g=80, color_b=60,
    back_color=colors.DARK_UMBER}

newEntity{define_as="DUNGEON_WALL", name="泥土牆壁",
    display='#', color_r=80, color_g=60, color_b=40,
    back_color=colors.DARK_UMBER,
    always_remember=true, does_block_move=true, block_sight=true}

newEntity{define_as="DUNGEON_DOOR", name="木門",
    display='+', color_r=140, color_g=100, color_b=60,
    back_color=colors.DARK_UMBER,
    notice=true, always_remember=true, block_sight=true,
    door_opened="DUNGEON_DOOR_OPEN"}

newEntity{define_as="DUNGEON_DOOR_OPEN", name="木門（開）",
    display="'", color_r=140, color_g=100, color_b=60,
    back_color=colors.DARK_GREY, always_remember=true,
    door_closed="DUNGEON_DOOR"}

-- 向下樓梯（進入下一層）
newEntity{
    define_as = "DUNGEON_STAIRS_DOWN",
    name = "向下的樓梯",
    display = '>', color_r=200, color_g=200, color_b=200,
    back_color = colors.DARK_GREY,
    notice=true, always_remember=true,
    change_level = 1,   -- +1 層（相對值，非 change_zone 時用此）
}

-- 向上樓梯（返回上一層，或從第 1 層返回大地圖）
newEntity{
    define_as = "DUNGEON_STAIRS_UP",
    name = "向上的樓梯",
    display = '<', color_r=200, color_g=200, color_b=200,
    back_color = colors.DARK_GREY,
    notice=true, always_remember=true,
    change_level = -1,  -- -1 層（相對值）
    -- 注意：在第 1 層時，change_level = -1 會讓 changeLevel 呼叫
    -- game:changeLevel(0, nil)，引擎會自動解析為返回大地圖
    -- 若要更明確控制，可在 on_enter 中動態修改此欄位
}
```

> **樓梯相對值 vs. 絕對值：**
>
> - `change_level = 1`（正數）：下一層（相對）
> - `change_level = -1`（負數）：上一層（相對）
> - `change_level = 1, change_zone = "wilderness"`：回大地圖的**絕對**指定
>
> 如果希望地牢第 1 層的向上樓梯**明確**回到大地圖，最安全的做法是在 Zone 的 `on_enter` 中，動態把第 1 層的向上樓梯替換為帶 `change_zone` 的版本：

```lua
-- dungeon_forest/zone.lua → on_enter（精確控制版）
on_enter = function(lev, old_lev)
    if lev == 1 and (not old_lev or old_lev > 1) then
        -- 讓第 1 層的所有向上樓梯明確指向大地圖
        local Map = require "engine.Map"
        for y = 0, game.level.map.h - 1 do
            for x = 0, game.level.map.w - 1 do
                local t = game.level.map(x, y, Map.TERRAIN)
                if t and t.define_as == "DUNGEON_STAIRS_UP" then
                    -- 複製一份並修改 change_zone
                    local exit_tile = t:clone()
                    exit_tile.change_level = 1
                    exit_tile.change_zone  = "wilderness"
                    game.level.map(x, y, Map.TERRAIN, exit_tile)
                end
            end
        end
    end
end,
```

---

## 步驟六：讓遊戲從大地圖開始

### 修改 `mod/class/Game.lua`

預設情況下，TE4 模組可能從地牢或其他 Zone 開始。要讓玩家**出生在大地圖的起點村莊旁**，修改 `newGame()`：

```lua
-- mod/class/Game.lua

function _M:newGame()
    -- 建立玩家角色（保留原有的 newGame 邏輯）
    self.player = self:createPlayer()
    self.player:resolve()

    -- 初始化 party
    self.party = require("mod.class.Party").new{}
    self.party:addMember(self.player, {
        control = "player",
        type    = "player",
        title   = "英雄",
    })

    -- 初始化據點狀態（Tutorial 10/11）
    self.camp_state = {
        buildings = {farm=false, chest=false, upgraded_fire=false},
        farms     = {},
        workers   = {},
    }

    -- ★ 起始於大地圖（wilderness Zone 的第 1 層）
    -- 玩家出現在 wilderness.lua 中設定的 startx, starty 位置
    self:changeLevel(1, "wilderness")
end
```

> **為什麼不在 `load()` 中設定？**  
> `newGame()` 只在「新遊戲」時呼叫一次；`load()` 在讀取存檔時呼叫。`changeLevel` 只需要在 `newGame()` 執行，存檔記錄了玩家當時所在的 Zone/Level，讀檔後自動恢復。

---

## 步驟七：完整 Zone 連結圖

```
wilderness（大地圖）
│
├─ TOWN_A_ENTRANCE（A）  ──>  town_a Zone (lev 1)
│                                  └─ TOWN_EXIT <  ──> wilderness
│
├─ TOWN_B_ENTRANCE（B）  ──>  town_b Zone (lev 1)
│                                  └─ TOWN_EXIT <  ──> wilderness
│
├─ CAMP_ENTRANCE（C）    ──>  camp Zone (lev 1)      [Tutorial 10]
│                                  └─ EXIT_TO_WORLD < ──> wilderness
│
├─ DUNGEON_FOREST（D）   ──>  dungeon_forest Zone
│                                  ├─ lev 1  >─────> lev 2
│                                  ├─ lev 2  >─────> lev 3
│                                  ├─ lev 3（Boss）
│                                  └─ lev 1  <（from lev 1）──> wilderness
│
└─ DUNGEON_FORTRESS（F） ──>  dungeon_fortress Zone
                                   └─ ...（同上結構）
```

---

## 步驟八：玩家返回位置的精確控制

TE4 的 `changeLevel` 預設行為：

```
從 wilderness → town_a：
  記錄 last_exit_x = player.x, last_exit_y = player.y 到 town_a Level 的 data
從 town_a → wilderness：
  讀取 wilderness Level 的 last_exit，玩家出現在上次離開 wilderness 的位置
```

若需要精確控制「從城鎮離開後回到大地圖的哪個位置」，可以在 `on_enter` 中設定：

```lua
-- wilderness/zone.lua → on_enter（精確控制返回位置）
on_enter = function(lev, old_lev)
    -- 從 town_a 返回，強制讓玩家出現在城鎮入口旁
    if game.zone.short_name == "wilderness" then
        local prev = game.__current_level_source  -- 前一個 Zone 名稱
        local spawn_positions = {
            town_a            = {x=11, y=21},  -- TOWN_A_ENTRANCE 旁
            town_b            = {x=42, y=21},  -- TOWN_B_ENTRANCE 旁
            camp              = {x= 2, y=15},  -- CAMP_ENTRANCE 旁
            dungeon_forest    = {x=14, y= 6},  -- DUNGEON_FOREST 旁
            dungeon_fortress  = {x=15, y= 9},  -- DUNGEON_FORTRESS 旁
        }
        local pos = prev and spawn_positions[prev]
        if pos then
            game.player:move(pos.x, pos.y, true)
        end
    end
end,
```

> **更常見的做法**是讓引擎的預設行為處理（返回上次離開位置），只在必要時覆蓋。對多數用途，預設行為已足夠。

---

## 步驟九：動態地點解鎖（進階）

有時需要根據遊戲進度解鎖新地點（例如完成任務後大地圖出現新城鎮）。

### 在 `camp_state`（或 `game.flags`）中記錄解鎖狀態

```lua
-- 在任務完成回呼中：
game.flags = game.flags or {}
game.flags.town_b_unlocked = true

-- 在大地圖地形的 on_move 中，解鎖地點標記
-- 注意：這需要動態替換地圖 Grid
```

### 動態在大地圖上添加新地點

```lua
-- 任務完成後呼叫（可在 Quest on_complete 中執行）
function _M:unlockWorldLocation(x, y, grid_id)
    -- 只在玩家當前在大地圖時立即生效；否則存為 pending，下次進入大地圖時套用
    if game.zone and game.zone.short_name == "wilderness" then
        local Map = require "engine.Map"
        local new_grid = game.zone.grid_list[grid_id]
        if new_grid then
            game.level.map(x, y, Map.TERRAIN, new_grid)
            game.level.map.changed = true
            game.logPlayer(game.player,
                "#LIGHT_BLUE#大地圖上出現了新的地點！")
        end
    else
        -- 存入 pending，下次進入 wilderness 時套用
        game.pending_world_unlocks = game.pending_world_unlocks or {}
        table.insert(game.pending_world_unlocks, {x=x, y=y, grid=grid_id})
    end
end
```

```lua
-- wilderness/zone.lua → on_enter（套用 pending 解鎖）
on_enter = function(lev, old_lev)
    if game.pending_world_unlocks then
        local Map = require "engine.Map"
        for _, unlock in ipairs(game.pending_world_unlocks) do
            local new_grid = game.zone.grid_list[unlock.grid]
            if new_grid then
                game.level.map(unlock.x, unlock.y, Map.TERRAIN, new_grid)
            end
        end
        game.level.map.changed = true
        game.pending_world_unlocks = nil   -- 清除 pending 列表
    end
end,
```

---

## 測試檢查清單

```lua
-- 按 ` 或 F1 開啟 Cheat Console

-- 1. 確認從大地圖開始
print("當前 Zone：", game.zone.short_name)   -- 應為 "wilderness"
print("地圖尺寸：", game.level.map.w, game.level.map.h)  -- 應為 50 30

-- 2. 確認地點標記存在（查 ASCII 地圖中 A 的位置）
local Map = require "engine.Map"
local t = game.level.map(10, 20, Map.TERRAIN)   -- A 在 (10,20)
print("地點標記：", t and t.name, t and t.change_zone)
-- 預期：起點村莊  town_a

-- 3. 進入城鎮
game:changeLevel(1, "town_a")
print("Zone：", game.zone.short_name)   -- 應為 "town_a"

-- 4. 返回大地圖
game:changeLevel(1, "wilderness")
print("Zone：", game.zone.short_name)   -- 應為 "wilderness"
print("玩家位置：", game.player.x, game.player.y)  -- 應在上次離開位置

-- 5. 進入地牢（多層測試）
game:changeLevel(1, "dungeon_forest")
print("地牢 Zone：", game.zone.short_name)   -- "dungeon_forest"
print("當前層：", game.level.level)           -- 1

-- 進入第 2 層
game:changeLevel(2, nil)   -- nil 表示同 Zone
print("第 2 層：", game.level.level)          -- 2

-- 6. 確認 persistent
game:changeLevel(1, "wilderness")
-- 重進大地圖，確認地形狀態保留
local t2 = game.level.map(10, 20, Map.TERRAIN)
print("持久化後地點仍存在：", t2 and t2.name)

-- 7. 動態解鎖測試
game:unlockWorldLocation(25, 5, "DUNGEON_FOREST_ENTRANCE")
-- 查看大地圖 (25,5) 是否出現地牢標記
```

---

## 常見錯誤排查

| 錯誤現象 | 原因 | 解法 |
|---------|------|------|
| 遊戲開始時黑畫面或進入錯誤 Zone | `newGame()` 的 `changeLevel(1, "wilderness")` 失敗 | 確認 `wilderness/zone.lua` 存在且路徑正確；確認 `mod/load.lua` 已載入所有 Zone |
| 大地圖字元全部顯示為空 | `defineTile` 的 Grid 找不到 | 確認 `grid_list` 載入了 `wilderness.lua`；確認 `define_as` 拼字一致 |
| 站在地點標記按 `>` 沒有反應 | `change_zone` 欄位錯誤，或 Zone 路徑找不到 | 確認 `change_zone` 的值與 `Zone.new("short_name", ...)` 的第一個參數一致 |
| 返回大地圖後玩家位置不對 | 引擎預設行為（無問題），或 `on_enter` 覆蓋有誤 | 移除 `on_enter` 中的手動 `move()`，先讓引擎預設處理 |
| 地牢最底層無法返回大地圖 | `change_level = -1` 在第 1 層計算為 0 層，引擎行為未定義 | 用 `on_enter` 動態把第 1 層的向上樓梯改為 `change_zone = "wilderness"` |
| 每次進入城鎮都重新生成（NPC 消失） | 城鎮 Zone 未設 `persistent = "zone"` | 在城鎮 Zone 加入 `persistent = "zone"` |
| 地圖寬高與 ASCII 不符造成崩潰 | Zone 的 `width`/`height` 與 ASCII 地圖實際行列數不一致 | 數 ASCII 地圖的列數（每行字元數）= `width`；行數 = `height` |
| 動態解鎖的地點重進大地圖後消失 | `pending_world_unlocks` 套用後未存檔，或 `persistent = "zone"` 未設定 | 確認大地圖 `persistent = "zone"`；確認 `pending_world_unlocks` 有在 `Game:save()` 的 `defaultSavedFields` 中宣告 |

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| 大地圖 Zone | `zones/wilderness/zone.lua` | `all_remembered`, `all_lited`, `persistent = "zone"` |
| 靜態大地圖 | `maps/wilderness.lua` | `defineTile`, ASCII return, `startx`/`starty` |
| 地點標記地形 | `grids/wilderness.lua` | `change_level` + `change_zone` 欄位 |
| 地牢多層連接 | `grids/dungeon_forest.lua` | `change_level = 1`（相對）/ `change_zone`（絕對） |
| 子地圖返回大地圖 | `grids/town.lua` | `change_level=1, change_zone="wilderness"` |
| 遊戲起始 Zone | `class/Game.lua → newGame()` | `self:changeLevel(1, "wilderness")` |
| 動態解鎖地點 | `Game:unlockWorldLocation()` + `on_enter` pending | `map(x,y,Map.TERRAIN, new_grid)` |

**大地圖的本質**：大地圖和普通地圖的唯一區別，是 `all_remembered`、`all_lited` 和靜態地圖設計三件事的組合。整個 Zone 切換機制（`change_zone` + `change_level`）在大地圖和普通地圖上的工作方式完全一致，這也是 TE4 架構最優雅的地方之一。
