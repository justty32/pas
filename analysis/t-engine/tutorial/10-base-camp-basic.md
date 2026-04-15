# 教學 10：據點系統基礎版

## 本章目標

建立一個玩家可反覆進出、**狀態完整持久化**的野外據點（Base Camp）。據點由手工設計的靜態地圖構成，包含：

- **篝火**：踩上後自動恢復 HP（有冷卻，用旗標驅動）
- **合成工作台**：透過 NPC 對話合成物品（消耗材料 → 產出產品）
- **出口**：傳送回大地圖（Wilderness）

玩家在大地圖找到據點入口進入後，可使用各設施；離開後再回來，地圖狀態完整保留（NPC 位置、已消耗物品等不重置）。

---

## 系統核心概念

### `persistent = "zone"` 如何運作

TE4 的 Zone 有四種持久化模式：

| 值 | 行為 |
|----|------|
| `false`（預設） | 離開即重新生成，不保留任何狀態 |
| `"memory"` | 存在 `game.memory_levels` 中，存檔後消失 |
| `"zone"` | 整個 Zone 以 `.teaz` 檔儲存，下次進入從檔案載入 |
| `true` | 每一層都獨立存檔 |

據點使用 `"zone"`：Zone 離開時把每一層的 Level 物件存入 `self.memory_levels[level_num]`，並在 Zone 存檔時寫入磁碟。下次 `zone:getLevel()` 時優先從 `memory_levels` 取出，而不是重新生成。

**結果**：你在據點放下的箱子、NPC 的當前狀態，下次進入都還在。

### Static Map 產生器

靜態地圖由一個 Lua 檔描述。產生器讀取這個檔案並把 ASCII 字元對映到具體的 Grid / NPC / Object 實體：

```lua
defineTile(char, grid_define_as, object_define_as, actor_define_as, trap_define_as)
-- 後三個參數可傳 nil 表示「不放置」
return [[
  ASCII地圖字串
]]
```

### 旗標驅動行為 vs. 函式欄位

TE4 的序列化系統**無法序列化匿名函式**。如果在 `newEntity{}` 裡直接寫 `on_move = function(...) end`，存檔重載後這個函式將遺失。

正確模式：
- **資料放在實體欄位**（`camp_heal = true`）
- **行為放在有名稱的類別方法**（`Grid:on_move()` 根據旗標分派）

---

## 完整檔案結構

```
mygame/
  mod/
    class/
      Grid.lua                          ← 覆寫 on_move，根據旗標分派行為
    data/
      grids/
        camp.lua                        ← 據點專用地形（篝火、出口、門…）
      npcs/
        camp_npcs.lua                   ← 工作台 NPC 定義
      chats/
        workbench.lua                   ← 工作台對話（含合成邏輯）
      zones/
        camp/
          zone.lua                      ← 據點 Zone 定義
      maps/
        camp.lua                        ← 靜態地圖（ASCII）
```

---

## 步驟一：據點 Zone 定義

### 檔案：`mod/data/zones/camp/zone.lua`

```lua
-- mod/data/zones/camp/zone.lua
-- 據點 Zone：玩家的野外基地

local Zone = require "engine.Zone"

return Zone.new("camp", {
    name        = "野外據點",
    level_range = {1, 1},
    max_level   = 1,

    -- 地圖尺寸（必須與 data/maps/camp.lua 的 ASCII 地圖一致）
    width  = 25,
    height = 20,

    -- ★ 關鍵：整個 Zone 狀態持久化
    -- 離開時把 Level 物件存入 memory_levels，Zone 存檔時寫入磁碟
    persistent = "zone",

    -- 城鎮 / 據點：全部可見、全部有光
    all_remembered = true,
    all_lited      = true,

    -- 載入地形列表（通用地形 + 據點專用地形）
    grid_list = require("mod.class.Grid"):loadList{
        "mod/data/grids/general.lua",
        "mod/data/grids/camp.lua",
    },

    -- 載入 NPC 列表（據點工作人員）
    npc_list = require("mod.class.NPC"):loadList{
        "mod/data/npcs/camp_npcs.lua",
    },

    -- 載入物品列表（合成產品 + 據點材料）
    object_list = require("mod.class.Object"):loadList{
        "mod/data/objects/consumables.lua",  -- 藥水等消耗品（含合成產品）
        "mod/data/objects/materials.lua",    -- 材料（草藥、空瓶等）
    },

    generator = {
        -- 使用靜態地圖，不做隨機生成
        map = {
            class = "engine.generator.map.Static",
            map   = "camp",   -- 對應 data/maps/camp.lua
        },
        -- Static 產生器讀取地圖中的 actor defineTile 欄位自動放置 NPC
        -- 因此 actor 產生器設定為空
        actor = {
            class = "engine.generator.actor.OnceAtCoord",
        },
    },

    -- 進入 / 離開回呼（可選）
    on_enter = function(lev, old_lev)
        game.logPlayer(game.player, "#LIGHT_GREEN#你回到了你的野外據點。")
    end,
    on_leave = function(lev, old_lev)
        game.logPlayer(game.player, "你離開了據點。")
    end,
})
```

> **`all_remembered = true`**：讓地圖一開始就全部顯示在 minimap 上，不需要玩家親自走過每格。城鎮和據點通常開啟這個選項。

---

## 步驟二：靜態地圖

### 檔案：`mod/data/maps/camp.lua`

靜態地圖檔案在一個特殊環境中執行（由 `Static:getLoader()` 注入 `defineTile`、`addSpot` 等函式）。

```lua
-- mod/data/maps/camp.lua
-- 據點靜態地圖（25 寬 × 20 高）

-- ── 地形映射 ─────────────────────────────────────────────────
defineTile('.', "CAMP_FLOOR")                       -- 普通地板
defineTile('#', "CAMP_WALL")                        -- 木牆
defineTile('+', "CAMP_DOOR")                        -- 木門
defineTile('*', "CAMPFIRE")                         -- 篝火（踩上恢復 HP）
defineTile('<', "EXIT_TO_WORLD")                    -- 出口（返回大地圖）
defineTile('t', "CAMP_TREE")                        -- 裝飾樹木
defineTile('~', "CAMP_WATER")                       -- 裝飾水池

-- 第四參數 = actor define_as → 在 CAMP_FLOOR 上放置 NPC
defineTile('w', "CAMP_FLOOR", nil, "WORKBENCH_NPC") -- 合成工作台

-- ── 起點設定 ─────────────────────────────────────────────────
-- 玩家進入時出現的座標
startx = 12
starty = 17

-- ── ASCII 地圖（25 寬 × 20 高） ────────────────────────────
-- 索引從 0 開始：左上角 = (0,0)，右下角 = (24,19)
return [[
#########################
#.......................#
#.t...................t.#
#.....##########.......#
#....#+........+#......#
#....#..........#......#
#....#....*.....#......#
#....#..........#......#
#....+..........+#.....#
#.....##########.......#
#.....................t.#
#.t....w...............#
#......................#
#......................#
#......................#
#.....~.~..............#
#......................#
#......................#
#............<.........#
#########################
]]
```

> **地圖說明：**
> - 外圍 `#` 是圍牆；中央小屋內有 `*` 篝火
> - `w` 是工作台 NPC 的位置（地板上）
> - `<` 在底部，是返回大地圖的出口
> - `t`/`~` 是裝飾物件

---

## 步驟三：地形實體定義

### 檔案：`mod/data/grids/camp.lua`

```lua
-- mod/data/grids/camp.lua
-- 據點專用地形定義

-- ── 基礎地形 ──────────────────────────────────────────────────
newEntity{
    define_as = "CAMP_FLOOR",
    name = "地板",
    display = '.', color_r=200, color_g=180, color_b=140,
    back_color = colors.DARK_GREY,
}

newEntity{
    define_as = "CAMP_WALL",
    name = "木牆",
    display = '#', color_r=139, color_g=90, color_b=43,
    back_color = colors.DARK_UMBER,
    always_remember   = true,
    does_block_move   = true,
    block_sight       = true,
    dig               = "CAMP_FLOOR",
}

newEntity{
    define_as = "CAMP_DOOR",
    name = "木門",
    display = '+', color_r=180, color_g=120, color_b=60,
    back_color = colors.DARK_UMBER,
    notice          = true,
    always_remember = true,
    block_sight     = true,
    door_opened     = "CAMP_DOOR_OPEN",
}

newEntity{
    define_as = "CAMP_DOOR_OPEN",
    name = "木門（開）",
    display = "'", color_r=180, color_g=120, color_b=60,
    back_color = colors.DARK_GREY,
    always_remember = true,
    door_closed     = "CAMP_DOOR",
}

newEntity{
    define_as = "CAMP_TREE",
    name = "樹",
    display = 't', color_r=0, color_g=150, color_b=0,
    back_color = colors.DARK_GREY,
    always_remember = true,
    does_block_move = true,
    block_sight     = true,
}

newEntity{
    define_as = "CAMP_WATER",
    name = "水池",
    display = '~', color_r=0, color_g=100, color_b=200,
    back_color = colors.DARK_BLUE,
    always_remember = true,
    does_block_move = true,
}

-- ── 篝火（帶 camp_heal 旗標） ──────────────────────────────────
-- 不在這裡放 on_move 函式（函式無法序列化）
-- 行為邏輯統一在 mod/class/Grid.lua 的 on_move 中根據旗標分派
newEntity{
    define_as = "CAMPFIRE",
    name = "篝火",
    display = '*', color_r=255, color_g=150, color_b=0,
    back_color = colors.DARK_RED,
    notice          = true,
    always_remember = true,

    camp_heal          = true,   -- 旗標：觸發治療
    camp_heal_pct      = 0.05,   -- 每次治療 5% 最大 HP
    camp_heal_cooldown = 10,     -- 冷卻：10 個玩家動作才能再次觸發
}

-- ── 出口（返回大地圖） ─────────────────────────────────────────
-- change_level + change_zone 欄位由 Game:setupCommands 的 CHANGE_LEVEL 鍵讀取
newEntity{
    define_as = "EXIT_TO_WORLD",
    name = "據點出口",
    display = '<', color_r=255, color_g=255, color_b=0,
    back_color = colors.DARK_GREY,
    notice          = true,
    always_remember = true,

    change_level = 1,            -- 目標層
    change_zone  = "wilderness", -- 目標 Zone short_name
}
```

---

## 步驟四：Grid 類別的 `on_move` 擴充

### 為什麼在類別方法中分派？

TE4 的序列化系統使用 `__CLASSNAME` 重建物件的 class metatable，但**匿名函式無法序列化**。如果把 `on_move = function(...) end` 直接放在 `newEntity{}` 裡，存檔後重載時這個函式會遺失。

正確做法：把行為邏輯放在**有名稱的類別方法**中，實體只攜帶**旗標資料**。

### 修改 `mod/class/Grid.lua`

```lua
-- mod/class/Grid.lua
-- 繼承引擎 Grid，在 on_move 中加入旗標分派

require "engine.class"
require "engine.Grid"

module(..., package.seeall, class.inherit(engine.Grid))

function _M:init(t, no_default)
    engine.Grid.init(self, t, no_default)
end

-- block_move：處理開門、障礙物
function _M:block_move(x, y, e, act, couldpass)
    -- 玩家主動移動且格子是關閉的門 → 開門
    if self.door_opened and act then
        game.level.map(x, y, engine.Map.TERRAIN,
            game.zone.grid_list[self.door_opened])
        return true
    elseif self.door_opened and not couldpass then
        return true
    end
    -- 可通行特殊地形（water_pass 等）
    if e and self.can_pass and e.can_pass then
        for what, check in pairs(e.can_pass) do
            if self.can_pass[what] and self.can_pass[what] <= check then
                return false
            end
        end
    end
    return self.does_block_move
end

-- ── on_move 分派中心 ──────────────────────────────────────────
-- 每當 Actor 進入此格時被呼叫（forced = true 表示被強制傳送，不觸發）
function _M:on_move(x, y, who, forced)
    if forced then return end

    -- ① 移動投射傷害（原有功能）
    if who.move_project and next(who.move_project) then
        local DamageType = require "engine.DamageType"
        for typ, dam in pairs(who.move_project) do
            DamageType:get(typ).projector(who, x, y, typ, dam)
        end
    end

    -- ② 篝火治療（僅對玩家觸發）
    if self.camp_heal and who == game.player then
        self:_campfireHeal(x, y, who)
    end
end

-- ── 篝火治療邏輯 ──────────────────────────────────────────────
-- 使用 game.level.data 存放冷卻時間戳，跟隨 Level 一起序列化
function _M:_campfireHeal(x, y, who)
    local cd_key = "campfire_heal_cd_" .. x .. "_" .. y
    local last_heal = game.level.data[cd_key] or 0
    local cooldown  = self.camp_heal_cooldown or 10

    -- cooldown 單位是「玩家動作次數」
    -- 1 玩家動作 = energy_to_act / energy_per_tick 個 game.turn
    local ticks_per_act = game.energy_to_act / game.energy_per_tick
    if game.turn - last_heal < cooldown * ticks_per_act then
        return  -- 冷卻中，靜默不提示
    end

    -- 治療量 = camp_heal_pct * 最大 HP（預設 5%）
    local pct  = self.camp_heal_pct or 0.05
    local heal = math.floor(who.max_life * pct)

    if who.life >= who.max_life then
        game.logPlayer(who, "篝火溫暖了你，但生命值已滿。")
        return
    end

    who:heal(heal)
    game.level.data[cd_key] = game.turn
    game.logPlayer(who,
        "#LIGHT_GREEN#篝火的溫暖讓你恢復了 %d 點生命值（%.0f%%）。",
        heal, pct * 100)
end
```

> **`game.level.data[cd_key]`** 是 TE4 中非常常用的模式：把臨時狀態存在 `level.data` 表裡，它隨 Level 物件序列化，可以跨存檔保留（但不跨 Level）。這裡用它記錄上次治療的 `game.turn`，避免篝火每步都觸發。

---

## 步驟五：合成工作台（NPC 方式）

工作台本質上是一個**靜止 NPC**，透過玩家「碰撞進入」（on_bump）觸發對話腳本，提供合成功能。

使用 on_bump 而非 on_interact 的原因：TE4 玩家移入友方 NPC 的格子時，引擎呼叫 `npc:bumpInto(player)` → 最終呼叫 `npc.on_bump`，這是最通用且在存檔前後都能正確觸發的方式。

### 合成配方

```
治療藥水：草藥 × 2 + 空瓶 × 1 → POTION_HEALING
強效藥水：草藥 × 5 + 空瓶 × 1 → POTION_GREATER_HEALING
```

### 檔案：`mod/data/npcs/camp_npcs.lua`

```lua
-- mod/data/npcs/camp_npcs.lua
-- 據點 NPC 定義

-- ── 合成工作台（靜止 NPC） ───────────────────────────────────
newEntity{
    define_as = "WORKBENCH_NPC",
    type = "object", subtype = "workbench",
    name = "合成工作台",
    display = 'T', color_r=150, color_g=100, color_b=50,
    faction = "players",

    -- 靜止不動，不尋找目標
    ai       = "none",
    ai_state = {},

    -- 防止被攻擊：友方且不是有效攻擊目標
    never_move = true,
    exp_worth  = 0,
    max_life   = 9999,
    rank       = 1,
    stats      = {str=20, dex=20, con=20, mag=0, wil=20, cun=20},

    -- 玩家碰撞進入（嘗試移動到此格）時觸發對話
    on_bump = function(self, who)
        if who ~= game.player then return end
        local Chat = require "engine.Chat"
        Chat.new("mod.data.chats.workbench", self, who):invoke()
    end,
}
```

> **為什麼 `on_bump` 可以序列化？**  
> 因為 `on_bump` 不是匿名函式，而是在 `newEntity{}` 原型定義中宣告的具名函式——原型本身不需要序列化（它由 `loadList` 在載入時重建），只有**實例**才需要序列化。只要實例沒有把 `on_bump` 複製到自己身上（不呼叫 `entity:resolve()`），就不存在序列化問題。

### 檔案：`mod/data/chats/workbench.lua`

```lua
-- mod/data/chats/workbench.lua
-- 合成工作台對話腳本
-- 注意：Chat 環境沒有 _M，輔助函式使用 local function 定義

-- ── 輔助函式 ─────────────────────────────────────────────────

--- 計算玩家背包中某物品的數量（依 define_as 比對）
local function countItem(player, item_id)
    local inven = player:getInven("INVEN")
    if not inven then return 0 end
    local count = 0
    for _, obj in ipairs(inven) do
        if obj.define_as == item_id then
            count = count + (obj.stacked or 1)
        end
    end
    return count
end

--- 消耗材料並產生產品
-- @param player  玩家 Actor
-- @param cost    {define_as = 數量} 消耗表
-- @param result  產品的 define_as
-- @param amount  產品數量
local function craft(player, cost, result, amount)
    -- 1. 消耗材料（從後往前遍歷避免索引偏移）
    local inven = player:getInven("INVEN")
    for item_id, qty in pairs(cost) do
        local remaining = qty
        for i = #inven, 1, -1 do
            if remaining <= 0 then break end
            local obj = inven[i]
            if obj.define_as == item_id then
                if (obj.stacked or 1) > 1 then
                    obj.stacked = (obj.stacked or 1) - 1
                    remaining   = remaining - 1
                else
                    player:removeObject(inven, i)
                    remaining = remaining - 1
                end
            end
        end
    end

    -- 2. 產生產品
    for i = 1, (amount or 1) do
        local obj = game.zone:makeEntityByName(game.level, "object", result)
        if obj then
            player:addObject(player:getInven("INVEN"), obj)
            game.logPlayer(player, "合成了 %s！", obj:getName{do_color=true})
        else
            game.logPlayer(player,
                "#RED#合成失敗：找不到產品模板 [%s]。請確認 object_list 已包含此物品。",
                result)
        end
    end
end

-- ── 對話定義 ─────────────────────────────────────────────────

newChat{
    id = "welcome",
    text = function(npc, player)
        return ("歡迎使用合成工作台。\n\n你的背包：\n" ..
            "  草藥   × " .. countItem(player, "HERB")         .. "\n" ..
            "  空瓶   × " .. countItem(player, "EMPTY_BOTTLE") .. "\n\n" ..
            "選擇要合成的物品：")
    end,
    answers = {
        -- 合成治療藥水
        {
            text = "合成治療藥水（草藥×2 + 空瓶×1）",
            cond = function(npc, player)
                return countItem(player, "HERB") >= 2
                   and countItem(player, "EMPTY_BOTTLE") >= 1
            end,
            action = function(npc, player)
                craft(player, {HERB=2, EMPTY_BOTTLE=1}, "POTION_HEALING", 1)
            end,
            jump = "crafted",
        },
        -- 合成強效治療藥水
        {
            text = "合成強效治療藥水（草藥×5 + 空瓶×1）",
            cond = function(npc, player)
                return countItem(player, "HERB") >= 5
                   and countItem(player, "EMPTY_BOTTLE") >= 1
            end,
            action = function(npc, player)
                craft(player, {HERB=5, EMPTY_BOTTLE=1}, "POTION_GREATER_HEALING", 1)
            end,
            jump = "crafted",
        },
        -- 材料不足
        {
            text = "材料不足，先去探索吧。",
            cond = function(npc, player)
                return countItem(player, "HERB") < 2
                    or countItem(player, "EMPTY_BOTTLE") < 1
            end,
            jump = "no_mats",
        },
        {text = "不用了，再見。"},
    },
}

newChat{
    id = "crafted",
    text = "合成完成！請查看你的背包。",
    answers = {
        {text = "繼續合成…", jump = "welcome"},
        {text = "謝了。"},
    },
}

newChat{
    id = "no_mats",
    text = "材料不足，無法合成。到野外多採集一些吧。",
    answers = {{text = "好的。"}},
}
```

---

## 步驟六：從大地圖進入據點

### 大地圖上的「據點入口」地形

在大地圖（Wilderness）的地形列表中加入一個特殊地形，玩家站上後按 `>` 即可進入：

```lua
-- mod/data/grids/wilderness.lua（在現有檔案中追加）
newEntity{
    define_as = "CAMP_ENTRANCE",
    name = "野外據點入口",
    display = 'C', color_r=0, color_g=255, color_b=150,
    back_color = colors.DARK_GREY,
    notice          = true,
    always_remember = true,

    -- 按下 CHANGE_LEVEL 鍵（預設 >）時：切換到 "camp" Zone 的第 1 層
    change_level = 1,
    change_zone  = "camp",
}
```

在大地圖靜態地圖中用字元 `C` 放置這個格子即可。

### Zone 進入後的玩家位置

`changeLevel` 結束後，玩家的初始位置由 Level 的 `default_up` / `default_down` 決定。Static 地圖產生器會自動把 `startx`/`starty` 設定為 `level.default_up`：

```lua
-- Static 產生器內部邏輯（引擎已實作）
level.default_up   = {x = startx, y = starty}
level.default_down = {x = startx, y = starty}
```

因此在 `camp.lua` 中設定 `startx = 12, starty = 17`（出口附近），進入據點時玩家就會出現在那裡。

---

## 步驟七：切換流程整合

### `Game.lua` 不需要修改

`change_zone` + `change_level` 欄位的觸發由原本的 `CHANGE_LEVEL` 鍵處理（引擎預設行為）：

```lua
-- 引擎 Game:setupCommands() 的 CHANGE_LEVEL 按鍵（原始邏輯示意）
CHANGE_LEVEL = function()
    local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
    if self.player:enoughEnergy() and e and e.change_level then
        self:changeLevel(
            e.change_zone and e.change_level
                          or self.level.level + e.change_level,
            e.change_zone
        )
    end
end,
```

**進入 camp 的完整流程：**

```
玩家站在 CAMP_ENTRANCE（change_level=1, change_zone="camp"）按 >
→ game:changeLevel(1, "camp")
→ 若 camp Zone 不存在 → 建立新 Zone，Static 產生器生成地圖
→ 若 camp Zone 已存在（.teaz 檔）→ 從磁碟載入
→ zone:getLevel(1)：優先從 memory_levels[1] 取出
→ 玩家出現在 startx=12, starty=17
```

**離開 camp 的完整流程：**

```
玩家站在 EXIT_TO_WORLD（change_level=1, change_zone="wilderness"）按 >
→ game:changeLevel(1, "wilderness")
→ camp Zone：leaveLevel() 把 Level 物件存入 memory_levels[1]
→ Zone:save() 把整個 Zone（含 memory_levels）寫入 .teaz 磁碟檔
→ wilderness Zone 載入
```

---

## 測試檢查清單

```lua
-- 按 ` 或 F1 開啟 Cheat Console

-- 1. 進入據點
game:changeLevel(1, "camp")
print(game.zone.short_name)           -- 應印出 "camp"

-- 2. 確認持久化模式
print(game.zone.persistent)           -- 應印出 "zone"

-- 3. 確認地圖尺寸
print(game.level.map.w, game.level.map.h)   -- 應印出 25  20

-- 4. 確認篝火地形（查 ASCII 地圖中 * 的位置）
local Map     = require "engine.Map"
local terrain = game.level.map(8, 6, Map.TERRAIN)   -- * 在 (8,6)
print(terrain and terrain.name, terrain and terrain.camp_heal)
-- 預期：篝火  true

-- 5. 確認工作台 NPC（查 ASCII 地圖中 w 的位置）
local npc = game.level.map(7, 11, Map.ACTOR)        -- w 在 (7,11)
print(npc and npc.name)
-- 預期：合成工作台

-- 6. 測試持久化（離開再進來）
game:changeLevel(1, "wilderness")
game:changeLevel(1, "camp")
print("level 物件 uid:", game.level.uid)   -- 兩次進入應相同
```

---

## 常見錯誤排查

| 錯誤現象 | 原因 | 解法 |
|---------|------|------|
| 每次進入據點都重新生成 | 未設 `persistent = "zone"` | 在 Zone 定義加入 `persistent = "zone"` |
| 靜態地圖字元顯示為空或問號 | `defineTile` 的 `define_as` 找不到 | 確認 `grid_list` 已載入 `camp.lua`；確認 `define_as` 拼字正確 |
| 篝火不觸發治療 | `on_move` 未被呼叫或未分派 | 確認 `mod/class/Grid.lua` 已繼承並 override `on_move`；確認地形有 `camp_heal = true` |
| 篝火每步都觸發 | 冷卻邏輯錯誤 | 確認 `game.level.data[cd_key]` 正確讀寫；`ticks_per_act` = 1000/100 = 10 |
| 工作台 NPC 不出現 | `defineTile` 的 actor 找不到 | 確認 `npc_list` 已載入 `camp_npcs.lua`；確認 `WORKBENCH_NPC` 拼字正確 |
| 碰撞工作台沒有反應 | `on_bump` 未觸發 | 確認 NPC 的 `faction = "players"`；確認 Game 的碰撞邏輯呼叫 `npc:bumpInto(player)` |
| 合成時找不到產品 | 產品不在 `object_list` | 在 Zone 的 `object_list` 中包含含有該物品的清單 |
| 地圖尺寸不符崩潰 | ASCII 行數/列數與 Zone 的 `width`/`height` 不一致 | 數 ASCII 地圖的行列數，更新 Zone 定義的 `width`/`height` |

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| Zone 持久化 | Zone 定義 `persistent = "zone"` | `leaveLevel()` 寫 `memory_levels`；`Zone:save()` 寫磁碟 |
| 靜態地圖 | `data/maps/camp.lua` | `defineTile`, `startx`/`starty`, ASCII return |
| 地形行為（旗標模式） | `data/grids/camp.lua` + `class/Grid.lua` | 實體定義旗標；Grid class `on_move` 分派 |
| 臨時狀態存儲 | `game.level.data[key]` | 跟隨 Level 序列化，持久且安全 |
| 合成工作台 | `npcs/camp_npcs.lua` + `chats/workbench.lua` | `on_bump` 觸發 Chat；local 輔助函式操作物品 |
| 區域切換 | `grids/camp.lua` + `grids/wilderness.lua` | `change_level` + `change_zone`；`CHANGE_LEVEL` 鍵觸發 |
