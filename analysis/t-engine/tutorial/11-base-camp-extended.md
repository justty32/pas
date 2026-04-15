# 教學 11：據點系統擴展版

## 本章目標

在 Tutorial 10 基礎版的據點上加入三個進階功能：

1. **農作計時器**：種植後等待固定回合數自動產出資源，不需要玩家一直在場
2. **建造系統**：消耗採集資源解鎖新設施（農田、儲物箱、強化篝火），設施狀態持久化
3. **NPC 工人**：可指派到農田的工人 NPC，在旁邊加速農作成熟

本章在 Tutorial 09（戰術指令 + 僱傭兵）的基礎上擴展，工人 AI 複用 `commanded_ally` 框架新增 `"work"` 指令分支。

---

## 設計架構

所有據點進度存在掛載於 `game` 物件上的 `camp_state` 表：

```lua
game.camp_state = {
    buildings = {
        farm          = false,   -- 農田是否已建造
        chest         = false,   -- 儲物箱是否已建造
        upgraded_fire = false,   -- 強化篝火是否已建造
    },
    farms = {
        -- 以 "x_y" 字串為 key，支援多格農田
        ["14_10"] = {
            turn_planted  = 12000,   -- 種下的 game.turn
            turns_to_grow = 100,     -- 成熟所需玩家動作次數
            yield         = {HERB=3},-- 成熟後產出
            ready         = false,   -- 是否可收穫
        },
    },
    workers = {
        -- uid = 任務描述字串（用於日誌）
        [42] = "耕種農田",
    },
}
```

**回合計時機制：**

```
Game:onTurn()  ← 引擎每個 game.turn 都呼叫
  └─ 條件：game.turn % 10 == 0（每 10 tick = 1 玩家動作）
       └─ game:updateCamp()
             └─ 遍歷 camp_state.farms
                   └─ (game.turn - turn_planted) >= turns_to_grow * 10
                         → farm.ready = true，提示玩家
```

---

## 完整新增 / 修改檔案結構

```
mygame/
  mod/
    class/
      Game.lua              ← 新增：onTurn 的 updateCamp 呼叫；farmInteract；newGame/save 初始化
      Grid.lua              ← 擴充：on_move 加農田互動分派
    ai/
      commanded_ally.lua    ← 擴充：加入 work 指令分支 + _cmd_work AI
    data/
      grids/
        camp.lua            ← 擴充：農田三態 Grid + BUILD_SITE_* + 強化篝火 + 儲物箱
      npcs/
        camp_npcs.lua       ← 擴充：加入 BUILD_MANAGER_NPC + CAMP_WORKER 模板
      chats/
        build_manager.lua   ← 新增：建造管理員對話（消耗資源、替換 Grid）
      maps/
        camp.lua            ← 修改：加入建造地塊、管理員 NPC 位置
```

---

## 步驟一：農作計時器

### 核心原理

```
game.energy_to_act  = 1000   ← 角色積累到此能量才能行動
game.energy_per_tick = 100   ← 每次 tick 所有角色獲得 100 能量

→ 1 個「玩家動作」需要 10 個 game.turn（1000 / 100）
→ 農田 100 動作後成熟 = 1000 個 game.turn
```

### 修改 `mod/class/Game.lua`

```lua
-- mod/class/Game.lua

-- ── onTurn：引擎每個 tick 呼叫 ────────────────────────────────
function _M:onTurn()
    -- 原有邏輯：每 10 tick 處理地圖特效
    if self.turn % 10 ~= 0 then return end
    self.level.map:processEffects()

    -- 只在據點 Zone 內更新農作計時器
    if self.zone and self.zone.short_name == "camp" then
        self:updateCamp()
    end
end

-- ── updateCamp：農田成熟檢查 + 工人狀態日誌 ──────────────────
function _M:updateCamp()
    local cs = self.camp_state
    if not cs then return end

    -- 農田成熟檢查（遍歷所有農田格）
    if cs.buildings and cs.buildings.farm and cs.farms then
        local ticks_per_act = self.energy_to_act / self.energy_per_tick  -- = 10
        for key, farm in pairs(cs.farms) do
            if not farm.ready and farm.turn_planted > 0 then
                local turns_passed  = self.turn - farm.turn_planted
                local ticks_needed  = farm.turns_to_grow * ticks_per_act
                if turns_passed >= ticks_needed then
                    farm.ready = true
                    -- 把地圖上對應格換為 FARM_READY
                    local x, y = key:match("^(%d+)_(%d+)$")
                    x, y = tonumber(x), tonumber(y)
                    if x and y then
                        local Map = require "engine.Map"
                        self.level.map(x, y, Map.TERRAIN,
                            self.zone.grid_list["FARM_READY"])
                        self.level.map.changed = true
                    end
                    self.logPlayer(self.player,
                        "#LIGHT_GREEN#你的農田（%s）已成熟，可以收穫！（踩上農田按 > 收穫）",
                        key)
                end
            end
        end
    end

    -- 工人狀態日誌（每 50 玩家動作輸出一次）
    if cs.workers then
        local ticks_per_act = self.energy_to_act / self.energy_per_tick
        if self.turn % (50 * ticks_per_act) == 0 then
            for uid, task in pairs(cs.workers) do
                local worker = __uids[uid]
                if worker and not worker.dead then
                    self.logPlayer(self.player,
                        "%s 正在執行任務：%s。", worker.name, task)
                else
                    -- 工人已死亡或消失，清理記錄
                    cs.workers[uid] = nil
                end
            end
        end
    end
end

-- ── farmInteract：農田互動（種植 / 查詢 / 收穫） ──────────────
-- 由 setupCommands 的 CHANGE_LEVEL 鍵呼叫
function _M:farmInteract(terrain, x, y)
    local cs = self.camp_state
    if not cs or not cs.buildings or not cs.buildings.farm then
        self.logPlayer(self.player, "農田尚未建造。先與建造管理員對話吧。")
        return
    end

    cs.farms = cs.farms or {}
    local key = x .. "_" .. y
    local farm = cs.farms[key]

    local ticks_per_act = self.energy_to_act / self.energy_per_tick

    -- ── 空農田：種植 ──
    if terrain.farm_interact == "plant" then
        -- 消耗 1 個草藥種子
        local inven = self.player:getInven("INVEN")
        local found = false
        for i = #inven, 1, -1 do
            if inven[i].define_as == "HERB_SEED" then
                self.player:removeObject(inven, i)
                found = true
                break
            end
        end
        if not found then
            self.logPlayer(self.player,
                "需要草藥種子才能種植。（到野外採集或購買）")
            return
        end
        -- 把地形換成 FARM_GROWING，記錄種植時間
        local Map = require "engine.Map"
        self.level.map(x, y, Map.TERRAIN, self.zone.grid_list["FARM_GROWING"])
        self.level.map.changed = true
        cs.farms[key] = {
            turn_planted  = self.turn,
            turns_to_grow = 100,
            yield         = {HERB = 3},
            ready         = false,
        }
        self.logPlayer(self.player,
            "#LIGHT_GREEN#種植完成！約 100 個動作後成熟。")

    -- ── 生長中：查詢進度 ──
    elseif terrain.farm_interact == "check" then
        if not farm or farm.turn_planted == 0 then
            self.logPlayer(self.player, "農田尚未種植。")
            return
        end
        local elapsed  = self.turn - farm.turn_planted
        local needed   = farm.turns_to_grow * ticks_per_act
        local pct      = math.min(100, math.floor(elapsed / needed * 100))
        self.logPlayer(self.player, "農田生長進度：%d%%。", pct)

    -- ── 可收穫：收穫 ──
    elseif terrain.farm_interact == "harvest" then
        if not farm or not farm.ready then
            local pct = 0
            if farm and farm.turn_planted > 0 then
                local elapsed = self.turn - farm.turn_planted
                local needed  = farm.turns_to_grow * ticks_per_act
                pct = math.min(100, math.floor(elapsed / needed * 100))
            end
            self.logPlayer(self.player, "農田尚未成熟（%d%%）。", pct)
            return
        end
        -- 把產出加入背包
        local Map = require "engine.Map"
        for item_id, qty in pairs(farm.yield or {}) do
            for i = 1, qty do
                local obj = self.zone:makeEntityByName(self.level, "object", item_id)
                if obj then
                    self.player:addObject(self.player:getInven("INVEN"), obj)
                end
            end
        end
        self.logPlayer(self.player, "#LIGHT_GREEN#收穫完成！獲得了資源。")
        -- 把地形重置為空農田，清除種植狀態
        self.level.map(x, y, Map.TERRAIN, self.zone.grid_list["FARM_EMPTY"])
        self.level.map.changed = true
        cs.farms[key] = nil
    end
end

-- ── newGame：初始化據點狀態 ────────────────────────────────────
function _M:newGame()
    -- ... 原有初始化邏輯 ...

    self.camp_state = {
        buildings = {
            farm          = false,
            chest         = false,
            upgraded_fire = false,
        },
        farms   = {},
        workers = {},
    }
end

-- ── save：宣告需要序列化的欄位 ────────────────────────────────
-- 只有在此宣告的欄位才會被 Savefile 序列化
function _M:save()
    return class.save(self, self:defaultSavedFields{
        camp_state = true,   -- ★ 必須宣告，否則存檔後據點進度消失
    }, true)
end
```

> **`defaultSavedFields`**：傳入一個表格，合併到預設存檔欄位（`zone`、`level`、`player` 等）。如果忘記宣告 `camp_state`，建造進度和農作進度在存檔重載後都會消失。

### 擴充 `setupCommands` 支援農田互動

```lua
-- mod/class/Game.lua → setupCommands()（修改 CHANGE_LEVEL 鍵）

CHANGE_LEVEL = function()
    local Map = require "engine.Map"
    local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
    if not e or not self.player:enoughEnergy() then return end

    -- ① 標準樓層 / Zone 切換
    if e.change_level then
        self:changeLevel(
            e.change_zone and e.change_level
                          or self.level.level + e.change_level,
            e.change_zone)

    -- ② 農田互動（種植 / 查詢進度 / 收穫）
    elseif e.farm_interact then
        self:farmInteract(e, self.player.x, self.player.y)

    -- ③ 建造地塊（開啟建造管理員 chat 的替代方案：直接開選單）
    -- 注意：建造通常由建造管理員 NPC 的對話處理，此處留為備用
    elseif e.build_site then
        game.logPlayer(self.player,
            "這是建造地塊。到建造管理員（M）那裡選擇要建造的設施。")
    end
end,
```

---

## 步驟二：農田 Grid 定義

### 農田三態轉換

```
FARM_EMPTY  ──種植──→  FARM_GROWING  ──成熟──→  FARM_READY
（空農田）               （生長中）                （可收穫）
    ↑                                                 ↓
    └─────────────────收穫後重置──────────────────────┘
```

### 修改 `mod/data/grids/camp.lua`（追加以下定義）

```lua
-- ── 農田三態 Grid ──────────────────────────────────────────────

-- 空農田（未種植）
newEntity{
    define_as = "FARM_EMPTY",
    name = "空農田",
    display = ',', color_r=139, color_g=90, color_b=43,
    back_color = colors.DARK_UMBER,
    always_remember = true,

    farm_interact = "plant",   -- 旗標：踩上提示可種植
}

-- 農田：生長中
newEntity{
    define_as = "FARM_GROWING",
    name = "農田（生長中）",
    display = ',', color_r=0, color_g=180, color_b=0,
    back_color = colors.DARK_GREEN,
    always_remember = true,

    farm_interact = "check",   -- 旗標：踩上顯示進度
}

-- 農田：可收穫
newEntity{
    define_as = "FARM_READY",
    name = "農田（可收穫！）",
    display = 'F', color_r=255, color_g=220, color_b=0,
    back_color = colors.DARK_GREEN,
    notice          = true,
    always_remember = true,

    farm_interact = "harvest",  -- 旗標：踩上可收穫
}

-- ── 建造地塊 ──────────────────────────────────────────────────
-- 建造前顯示 ?；建造後被對應設施 Grid 替換

newEntity{
    define_as = "BUILD_SITE_FARM",
    name = "建造地塊（農田）",
    display = '?', color_r=139, color_g=90, color_b=43,
    back_color = colors.DARK_UMBER,
    always_remember = true,
    build_site = true,
    build_tag  = "farm",   -- 與 camp_state.buildings 的 key 對應
}

newEntity{
    define_as = "BUILD_SITE_CHEST",
    name = "建造地塊（儲物箱）",
    display = '?', color_r=180, color_g=180, color_b=100,
    back_color = colors.DARK_GREY,
    always_remember = true,
    build_site = true,
    build_tag  = "chest",
}

newEntity{
    define_as = "BUILD_SITE_FIRE",
    name = "建造地塊（強化篝火）",
    display = '?', color_r=255, color_g=100, color_b=0,
    back_color = colors.DARK_RED,
    always_remember = true,
    build_site = true,
    build_tag  = "upgraded_fire",
}

-- ── 建造完成後的設施 Grid ──────────────────────────────────────

-- 強化篝火（建造後替換 BUILD_SITE_FIRE）
newEntity{
    define_as = "CAMPFIRE_UPGRADED",
    name = "強化篝火",
    display = 'X', color_r=255, color_g=200, color_b=0,
    back_color = colors.DARK_RED,
    always_remember = true,

    camp_heal          = true,
    camp_heal_pct      = 0.10,  -- 治療 10% HP（普通篝火是 5%）
    camp_heal_cooldown = 5,     -- 冷卻縮短為 5 動作（普通是 10）
}

-- 據點儲物箱（建造後替換 BUILD_SITE_CHEST）
-- camp_chest 旗標：踩上按 > 開啟共享儲物 Dialog
newEntity{
    define_as = "CAMP_CHEST",
    name = "據點儲物箱",
    display = 'c', color_r=200, color_g=150, color_b=50,
    back_color = colors.DARK_UMBER,
    notice          = true,
    always_remember = true,

    camp_chest = true,   -- 旗標：由 Grid:on_move 分派儲物互動
}
```

### 擴充 `mod/class/Grid.lua`：農田提示 + 儲物箱互動

```lua
-- mod/class/Grid.lua（在 on_move 中追加）

function _M:on_move(x, y, who, forced)
    if forced then return end

    -- ① 移動投射傷害（原有）
    if who.move_project and next(who.move_project) then
        local DamageType = require "engine.DamageType"
        for typ, dam in pairs(who.move_project) do
            DamageType:get(typ).projector(who, x, y, typ, dam)
        end
    end

    -- ② 篝火治療（Tutorial 10）
    if self.camp_heal and who == game.player then
        self:_campfireHeal(x, y, who)
    end

    -- ③ 農田狀態提示（踩上時顯示當前狀態）
    if self.farm_interact and who == game.player then
        self:_farmStep(x, y, who)
    end

    -- ④ 儲物箱（踩上提示玩家可按 > 開啟）
    if self.camp_chest and who == game.player then
        game.logPlayer(who, "這是據點儲物箱。按 [>] 開啟存放物品。")
    end
end

-- ── 農田踩上提示 ─────────────────────────────────────────────
function _M:_farmStep(x, y, who)
    local fi = self.farm_interact
    if fi == "plant" then
        game.logPlayer(who,
            "這是空農田。按 [>] 種植草藥（需要：草藥種子 ×1）。")
    elseif fi == "check" then
        local cs = game.camp_state
        if cs and cs.farms then
            local farm = cs.farms[x .. "_" .. y]
            if farm and farm.turn_planted > 0 then
                local tpa     = game.energy_to_act / game.energy_per_tick
                local elapsed = game.turn - farm.turn_planted
                local needed  = farm.turns_to_grow * tpa
                local pct     = math.min(100, math.floor(elapsed / needed * 100))
                game.logPlayer(who, "農田生長進度：%d%%。按 [>] 查詢詳情。", pct)
                return
            end
        end
        game.logPlayer(who, "農田正在生長中。按 [>] 查詢進度。")
    elseif fi == "harvest" then
        game.logPlayer(who, "#LIGHT_GREEN#農田已成熟！按 [>] 收穫。")
    end
end
```

---

## 步驟三：建造系統

### 設計原則

1. 建造前：地圖上顯示 `BUILD_SITE_*` 格（`?`）
2. 玩家與建造管理員 NPC 對話，消耗資源
3. 建造後：呼叫 `_applyBuildingToMap(btype)` 掃描地圖，把對應 `build_tag` 的格子替換為設施 Grid
4. `camp_state.buildings[btype] = true` 標記完成
5. Zone 的 `persistent = "zone"` 確保替換後的 Grid 在下次進入時依然存在

### 更新靜態地圖 `mod/data/maps/camp.lua`

```lua
-- mod/data/maps/camp.lua（完整更新版）

defineTile('.', "CAMP_FLOOR")
defineTile('#', "CAMP_WALL")
defineTile('+', "CAMP_DOOR")
defineTile('*', "CAMPFIRE")
defineTile('<', "EXIT_TO_WORLD")
defineTile('t', "CAMP_TREE")
defineTile('~', "CAMP_WATER")
defineTile('f', "BUILD_SITE_FARM")                    -- 農田建造地塊
defineTile('B', "BUILD_SITE_CHEST")                   -- 儲物箱建造地塊
defineTile('F', "BUILD_SITE_FIRE")                    -- 強化篝火建造地塊
defineTile('w', "CAMP_FLOOR", nil, "WORKBENCH_NPC")   -- 合成工作台 NPC
defineTile('M', "CAMP_FLOOR", nil, "BUILD_MANAGER_NPC") -- 建造管理員 NPC

startx = 12
starty = 17

return [[
#########################
#.......................#
#.t...................t.#
#.....##########.......#
#....#+........+#......#
#....#...F......#......#
#....#....*.....#......#
#....#.........M#......#
#....+..........+#.....#
#.....##########.......#
#....f................t#
#.t....w.......B.......#
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

### 新增 `BUILD_MANAGER_NPC` 到 `mod/data/npcs/camp_npcs.lua`

```lua
-- mod/data/npcs/camp_npcs.lua（追加）

-- ── 建造管理員（靜止 NPC） ───────────────────────────────────
newEntity{
    define_as = "BUILD_MANAGER_NPC",
    type = "humanoid", subtype = "human",
    name = "建造管理員",
    display = 'M', color_r=100, color_g=200, color_b=255,
    faction = "players",

    ai       = "none",
    ai_state = {},

    never_move = true,
    exp_worth  = 0,
    max_life   = 9999,
    rank       = 1,
    stats      = {str=15, dex=10, con=15, mag=0, wil=15, cun=15},

    -- 玩家碰撞時觸發建造對話
    on_bump = function(self, who)
        if who ~= game.player then return end
        local Chat = require "engine.Chat"
        Chat.new("mod.data.chats.build_manager", self, who):invoke()
    end,
}
```

### 新增 `mod/data/chats/build_manager.lua`

```lua
-- mod/data/chats/build_manager.lua
-- 建造管理員對話腳本

-- ── 輔助函式（local，不依賴 _M）────────────────────────────────

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

--- 消耗資源並在地圖上替換對應建造地塊
-- @param player  玩家
-- @param cost    {item_id = qty}
-- @param btype   建造類型（需與 Grid 的 build_tag 對應）
local function build(player, cost, btype)
    -- 初始化 camp_state（防禦性初始化）
    game.camp_state = game.camp_state or {
        buildings={}, farms={}, workers={}
    }
    local cs = game.camp_state
    cs.buildings = cs.buildings or {}

    -- 消耗材料（從後往前遍歷避免索引偏移）
    local inven = player:getInven("INVEN")
    for item_id, qty in pairs(cost) do
        local remaining = qty
        for i = #inven, 1, -1 do
            if remaining <= 0 then break end
            local obj = inven[i]
            if obj.define_as == item_id then
                if (obj.stacked or 1) > 1 then
                    obj.stacked = (obj.stacked or 1) - 1
                    remaining = remaining - 1
                else
                    player:removeObject(inven, i)
                    remaining = remaining - 1
                end
            end
        end
    end

    -- 標記建造完成
    cs.buildings[btype] = true

    -- 掃描地圖，把對應 build_tag 的建造地塊替換為設施 Grid
    _applyBuildingToMap(btype)

    game.logPlayer(player, "#LIGHT_GREEN#建造完成：%s！新設施已出現在據點地圖上。", btype)
end

--- 掃描地圖，把所有 build_tag == btype 的格子替換為完成後的設施 Grid
local function _applyBuildingToMap(btype)
    local Map = require "engine.Map"
    local map = game.level.map

    -- 建造類型 → 替換為哪個 Grid（與 camp.lua 的 define_as 一致）
    local replacements = {
        farm          = "FARM_EMPTY",
        chest         = "CAMP_CHEST",
        upgraded_fire = "CAMPFIRE_UPGRADED",
    }
    local new_grid_id = replacements[btype]
    if not new_grid_id then return end

    -- 掃描全圖
    for y = 0, map.h - 1 do
        for x = 0, map.w - 1 do
            local t = map(x, y, Map.TERRAIN)
            if t and t.build_site and t.build_tag == btype then
                local new_grid = game.zone.grid_list[new_grid_id]
                if new_grid then
                    map(x, y, Map.TERRAIN, new_grid)
                    map.changed = true
                end
            end
        end
    end
end

-- ── 對話定義 ─────────────────────────────────────────────────

newChat{
    id = "welcome",
    text = function(npc, player)
        local cs = game.camp_state or {}
        local bs = cs.buildings   or {}
        return ("歡迎，指揮官。\n\n目前據點建造狀況：\n" ..
            "  農田：" ..         (bs.farm          and "✓ 已建造" or "✗ 未建造") .. "\n" ..
            "  儲物箱：" ..       (bs.chest         and "✓ 已建造" or "✗ 未建造") .. "\n" ..
            "  強化篝火：" ..     (bs.upgraded_fire and "✓ 已建造" or "✗ 未建造") .. "\n\n" ..
            "你有：木材 " .. countItem(player, "WOOD") ..
            "，石塊 " ..          countItem(player, "STONE") ..
            " 個。\n\n選擇要建造的設施：")
    end,
    answers = {
        -- 建造農田
        {
            text = "建造農田（木材×5）",
            cond = function(npc, player)
                local bs = (game.camp_state or {}).buildings or {}
                return not bs.farm and countItem(player, "WOOD") >= 5
            end,
            action = function(npc, player)
                build(player, {WOOD=5}, "farm")
            end,
            jump = "built",
        },
        -- 建造儲物箱
        {
            text = "建造儲物箱（木材×3 + 石塊×2）",
            cond = function(npc, player)
                local bs = (game.camp_state or {}).buildings or {}
                return not bs.chest
                   and countItem(player, "WOOD")  >= 3
                   and countItem(player, "STONE") >= 2
            end,
            action = function(npc, player)
                build(player, {WOOD=3, STONE=2}, "chest")
            end,
            jump = "built",
        },
        -- 強化篝火
        {
            text = "強化篝火（石塊×5 + 木材×2）",
            cond = function(npc, player)
                local bs = (game.camp_state or {}).buildings or {}
                return not bs.upgraded_fire
                   and countItem(player, "STONE") >= 5
                   and countItem(player, "WOOD")  >= 2
            end,
            action = function(npc, player)
                build(player, {STONE=5, WOOD=2}, "upgraded_fire")
            end,
            jump = "built",
        },
        -- 農田已建造
        {
            text = "農田已建造。",
            cond = function(npc, player)
                return ((game.camp_state or {}).buildings or {}).farm == true
            end,
            jump = "farm_done",
        },
        {text = "資源不足，先去探索。"},
    },
}

newChat{
    id = "built",
    text = "建造完成！新設施已出現在據點地圖上，請前往查看。",
    answers = {
        {text = "繼續建造…", jump = "welcome"},
        {text = "謝謝。"},
    },
}

newChat{
    id = "farm_done",
    text = "農田已建造完成。記得取得草藥種子後，踩上農田按 [>] 種植。工人可以加速農作成熟。",
    answers = {
        {text = "繼續建造…", jump = "welcome"},
        {text = "明白了。"},
    },
}
```

---

## 步驟四：NPC 工人

### 設計思路

工人延伸 Tutorial 09 的 `commanded_ally` AI，新增 `"work"` 指令類型：

```lua
-- 指派後工人的 AI 狀態
worker.ai_state.command = {type = "work", task = "farm"}
-- AI 行為：找到最近的 FARM_GROWING 格，移動過去後每 20 動作加速農作 5 動作
```

### 新增工人模板到 `mod/data/npcs/camp_npcs.lua`

```lua
-- mod/data/npcs/camp_npcs.lua（追加）

-- ── 據點工人（可招募） ────────────────────────────────────────
-- 透過工人招募 NPC（Worker Recruiter）的 Chat 生成到 party
newEntity{
    define_as = "CAMP_WORKER",
    type = "humanoid", subtype = "human",
    name = "工人",
    display = 'p', color_r=180, color_g=180, color_b=180,
    faction = "players",

    ai       = "commanded_ally",   -- Tutorial 09 定義的指令 AI
    ai_state = {ai_move = "move_simple"},

    level_range = {1, 1},
    exp_worth   = 0,
    rank        = 1,

    max_life    = resolvers.rngrange(30, 50),
    life_rating = 8,
    stats       = {str=10, dex=10, con=10, mag=5, wil=8, cun=8},

    worker_task = nil,   -- 由玩家指派（"farm" / nil）
}
```

### 工人招募方式

工人透過招募 NPC 或特定地點對話加入 party，再手動指派任務：

```lua
-- 在某個 NPC 的 on_bump chat 中（例如大地圖上的招募站）
-- 建立工人實體並加入 party
local worker = game.zone:makeEntityByName(game.level, "actor", "CAMP_WORKER")
if worker then
    worker:resolve()
    game.zone:addEntity(game.level, worker, "actor",
        game.player.x + 1, game.player.y)
    game.party:addMember(worker, {
        control  = "no",
        type     = "ally",
        title    = "據點工人",
        orders   = {"follow", "attack", "standby", "flee", "work"},
    })
    game.logPlayer(game.player,
        "#LIGHT_GREEN#%s 加入了你的隊伍。", worker.name)
end
```

### 擴充 `commanded_ally` AI

```lua
-- mod/ai/commanded_ally.lua（在現有 commanded_ally AI 中追加 work 分支）

newAI("commanded_ally", function(self)
    local cmd = self.ai_state.command

    if not cmd then return self:runAI("_ally_default") end

    -- ★ 新增 work 指令分支
    if cmd.type == "work" then
        return self:runAI("_cmd_work", cmd)
    end

    -- 原有分支（Tutorial 09，保持不變）
    if cmd.type == "attack" then
        if not cmd.target or cmd.target.dead then
            self.ai_state.command = nil
            return self:runAI("_ally_default")
        end
        self:setTarget(cmd.target)
        return self:runAI("dumb_talented_simple")

    elseif cmd.type == "follow" then
        if core.fov.distance(self.x, self.y, game.player.x, game.player.y) > 2 then
            self:moveDirection(game.player.x, game.player.y)
        else
            self:useEnergy()
        end
        return true

    elseif cmd.type == "standby" then
        self:useEnergy()
        return true

    elseif cmd.type == "flee" then
        if self:runAI("target_simple") then
            return self:runAI("flee_simple")
        end
        self:useEnergy()
        return true
    end

    -- 未知指令：切回預設 AI
    self.ai_state.command = nil
    return self:runAI("_ally_default")
end)

-- ── 工作 AI：移動到農田旁，定期加速農作 ──────────────────────
newAI("_cmd_work", function(self, cmd)
    local task = cmd and cmd.task

    if task ~= "farm" then
        -- 未知任務：待命
        self:useEnergy()
        return true
    end

    -- 掃描地圖找最近的 FARM_GROWING 格
    local Map = require "engine.Map"
    local tx, ty, best_dist = nil, nil, math.huge
    for fy = 0, game.level.map.h - 1 do
        for fx = 0, game.level.map.w - 1 do
            local t = game.level.map(fx, fy, Map.TERRAIN)
            if t and t.farm_interact == "check" then  -- FARM_GROWING 的旗標
                local d = core.fov.distance(self.x, self.y, fx, fy)
                if d < best_dist then
                    best_dist, tx, ty = d, fx, fy
                end
            end
        end
    end

    if not tx then
        -- 找不到農田（尚未種植），待命
        self:useEnergy()
        return true
    end

    if best_dist > 1 then
        -- 往農田移動
        self:moveDirection(tx, ty)
        return true
    end

    -- 在農田旁：每 20 玩家動作嘗試加速農作一次
    local boost_key      = "worker_farm_boost_" .. self.uid
    local last_boost     = self.ai_state[boost_key] or 0
    local ticks_per_act  = game.energy_to_act / game.energy_per_tick
    local boost_interval = 20 * ticks_per_act

    if game.turn - last_boost >= boost_interval then
        local cs = game.camp_state
        if cs and cs.farms then
            local farm = cs.farms[tx .. "_" .. ty]
            if farm and farm.turn_planted > 0 and not farm.ready then
                -- 把種植時間往前移 5 個動作（= 加速 5%）
                local speed_up = 5 * ticks_per_act
                farm.turn_planted = math.max(
                    farm.turn_planted - speed_up,
                    0   -- 避免 turn_planted 成為負數
                )
                self.ai_state[boost_key] = game.turn
            end
        end
    end

    self:useEnergy()  -- 停在農田旁等待
    return true
end)

-- ── 預設同伴 AI（Tutorial 09，無變化） ──────────────────────
newAI("_ally_default", function(self)
    if self:runAI("target_simple") then
        return self:runAI("dumb_talented_simple")
    end
    if game.player then
        local d = core.fov.distance(self.x, self.y, game.player.x, game.player.y)
        if d > 3 then
            return self:moveDirection(game.player.x, game.player.y)
        end
    end
    self:useEnergy()
    return true
end)
```

### 指派工人任務

```lua
-- 在 Tutorial 09 的 ActorCommand mixin 中追加（mod/class/interface/ActorCommand.lua）
-- 或直接在指令選單的 action 函式中呼叫

--- 指派工人到農田工作
-- @param worker  工人 Actor
function _M:assignWorkerToFarm(worker)
    local cs = game.camp_state
    if not cs or not (cs.buildings or {}).farm then
        game.logPlayer(self, "農田尚未建造，無法指派工人。")
        return false
    end

    worker.ai_state.command = {type = "work", task = "farm"}

    -- 記錄到 camp_state.workers 以便 updateCamp 的日誌
    cs.workers = cs.workers or {}
    cs.workers[worker.uid] = "耕種農田"

    game.logPlayer(self,
        "已指派 %s 到農田工作。他會自動移動到農田旁並加速農作成熟。",
        worker.name)
    return true
end
```

---

## 步驟五：`camp_state` 的初始化與存檔

### 初始化時機

`camp_state` 掛在 `game` 物件上，隨 `game:save()` 自動序列化。在 `newGame()` 時初始化，確保每個新存檔都有乾淨的起始狀態：

```lua
-- 已在步驟一的 Game.lua 中完整實作，這裡重申關鍵點：
game.camp_state = {
    buildings = {farm=false, chest=false, upgraded_fire=false},
    farms     = {},   -- 以 "x_y" 為 key 的農田狀態表
    workers   = {},   -- uid → 任務描述
}
```

### 存檔欄位宣告

```lua
-- mod/class/Game.lua → save()
function _M:save()
    return class.save(self, self:defaultSavedFields{
        camp_state = true,   -- ★ 必須宣告，否則存檔後據點進度消失
    }, true)
end
```

> **`farms` 使用 `"x_y"` 字串 key 的原因**：Lua table 的整數 key 與字串 key 行為略有不同，而座標組合 `x.."_"..y` 是安全的字串 key，不會因 Lua 的 hash table 特性造成序列化問題。也能輕鬆支援多格農田同時種植。

---

## 步驟六：完整流程展示

```
玩家第一次進入據點
│
├─ camp_state.buildings 全部 false
├─ 地圖上顯示 BUILD_SITE_* 格（?）
│
├─ 玩家到野外採集：木材×5
│
├─ 碰撞建造管理員 NPC（M）→ 建造農田
│   ├─ build() 消耗木材×5
│   ├─ camp_state.buildings.farm = true
│   └─ _applyBuildingToMap("farm")
│       → 掃描到 BUILD_SITE_FARM（build_tag="farm"）
│       → 替換為 FARM_EMPTY
│
├─ 玩家踩上農田（FARM_EMPTY），按 >
│   ├─ farmInteract() 消耗草藥種子×1
│   ├─ 地圖：FARM_EMPTY → FARM_GROWING
│   └─ camp_state.farms["x_y"] = {turn_planted=game.turn, ...}
│
├─ （可選）招募工人，指派到農田
│   └─ worker.ai_state.command = {type="work", task="farm"}
│       → 工人移動到農田旁
│       → 每 20 動作：farm.turn_planted -= 5 * ticks_per_act
│
├─ 每 10 game.turn（= 1 玩家動作）
│   └─ Game:onTurn() → updateCamp()
│       └─ turn - turn_planted >= 100 * 10 = 1000
│             → farm.ready = true
│             → 地圖：FARM_GROWING → FARM_READY
│             → 提示玩家
│
├─ 玩家踩上農田（FARM_READY），按 >
│   ├─ farmInteract() 把 yield 加入背包（HERB×3）
│   ├─ 地圖：FARM_READY → FARM_EMPTY
│   └─ camp_state.farms["x_y"] = nil
│
└─ 玩家離開據點（按 < 使用 EXIT_TO_WORLD）
    ├─ Zone:leaveLevel() → memory_levels[1] = level
    └─ Zone:save() 寫入 .teaz 磁碟檔
        → 地圖 Grid 替換狀態持久化（農田格保留）
        → camp_state 隨 game:save() 持久化（種植進度保留）
```

---

## 測試檢查清單

```lua
-- 按 ` 或 F1 開啟 Cheat Console

-- 1. 給自己測試材料
local inven = game.player:getInven("INVEN")
for _, id in ipairs{"WOOD","STONE","HERB_SEED"} do
    for i = 1, 5 do
        local obj = game.zone:makeEntityByName(game.level, "object", id)
        if obj then game.player:addObject(inven, obj) end
    end
end

-- 2. 碰撞建造管理員對話（手動觸發）
game.camp_state.buildings.farm = true
-- 然後手動呼叫 _applyBuildingToMap
local Map = require "engine.Map"
for y=0,game.level.map.h-1 do
    for x=0,game.level.map.w-1 do
        local t = game.level.map(x,y,Map.TERRAIN)
        if t and t.build_tag == "farm" then
            game.level.map(x,y,Map.TERRAIN, game.zone.grid_list["FARM_EMPTY"])
            print("替換農田 at", x, y)
        end
    end
end

-- 3. 確認農田格存在
-- 走到地圖上的 f 字元位置（約 x=5, y=10），確認顯示為空農田

-- 4. 測試農作計時器（作弊加速）
-- 假設已種植在 (5,10)
game.camp_state.farms = game.camp_state.farms or {}
game.camp_state.farms["5_10"] = {
    turn_planted  = 0,      -- 設為 0 使其立即成熟
    turns_to_grow = 100,
    yield         = {HERB=3},
    ready         = false,
}
game:updateCamp()   -- 應觸發成熟提示並替換 Grid

-- 5. 確認 camp_state 存檔
-- 手動存檔後重載，確認 camp_state 仍存在
print("farm 建造狀態：", game.camp_state.buildings.farm)
```

---

## 常見錯誤排查

| 錯誤現象 | 原因 | 解法 |
|---------|------|------|
| `camp_state` 存檔後消失 | `save()` 未宣告 `camp_state = true` | 在 `defaultSavedFields{}` 加入 `camp_state = true` |
| 建造後地圖沒有變化 | `build_tag` 不一致或 `grid_list` 找不到目標 Grid | 確認 `BUILD_SITE_FARM.build_tag == "farm"` 且 `FARM_EMPTY` 已在 `grid_list` |
| 農田成熟後 Grid 沒有更新為 FARM_READY | `updateCamp` 中座標解析失敗 | 確認 key 格式 `"x_y"` 與 `farmInteract` 中一致 |
| `updateCamp` 不被呼叫 | `onTurn` 條件判斷失誤或 Zone 名稱不符 | 確認 `game.zone.short_name == "camp"` 正確；確認 `_M:onTurn()` 有呼叫 `self:updateCamp()` |
| 工人不移動到農田 | 農田格不是 `FARM_GROWING`（未種植） | 先種植，地形換為 `FARM_GROWING` 後工人才會找到目標 |
| 建造後重進據點 BUILD_SITE 復原 | `persistent = "zone"` 未設定 | 在 Zone 定義加入，讓 Grid 替換狀態持久化 |
| `commanded_ally` AI 無 work 分支 | `mod/ai/commanded_ally.lua` 未更新 | 確認 `newAI("commanded_ally", ...)` 已加入 `work` 分支和 `_cmd_work` AI |
| 招募的工人不執行工作指令 | `ai_state.command` 未正確設定 | 呼叫 `assignWorkerToFarm(worker)` 後確認 `worker.ai_state.command.type == "work"` |
| 農作進度不保留跨存檔 | `camp_state.farms` 未隨存檔保存 | 同 camp_state 存檔問題；確認 `farms` 字段在 `camp_state` 內 |
| Chat 輔助函式找不到 `_M` | 舊版 chat 使用 `_M.func` | 改用 `local function` 定義輔助函式（Chat 環境沒有 `_M`） |

---

## 進階擴展方向

### 1. 多格農田

`camp_state.farms` 已以 `"x_y"` 為 key 設計，天然支援多格農田同時種植，無需額外修改。只需在地圖上放置更多 `BUILD_SITE_FARM` 格即可。

### 2. 工人自動收穫並重新種植

```lua
-- 在 _cmd_work AI 中，若農田已 ready 自動收穫並重新種植
if farm.ready then
    game:farmInteract(
        game.level.map(tx, ty, Map.TERRAIN),  -- FARM_READY grid
        tx, ty
    )
    -- farmInteract 執行收穫後自動重置為 FARM_EMPTY
    -- 若工人背包有種子，可在此再次呼叫 farmInteract 種植
end
```

### 3. 升級樹（多層建造）

把建造系統擴展為多層升級（基礎農田 → 進階農田 → 溫室），在 chat 的 `cond` 中檢查前一層是否完成：

```lua
cond = function(npc, player)
    local bs = (game.camp_state or {}).buildings or {}
    return bs.farm == true           -- 基礎農田已建造
       and not bs.farm_lv2           -- 進階農田尚未建造
       and countItem(player, "IRON") >= 5
end,
action = function(npc, player)
    build(player, {IRON=5}, "farm_lv2")  -- build_tag = "farm_lv2"
end,
```

### 4. 儲物箱共享存儲

```lua
-- 在 Grid:on_move 的 camp_chest 分支中開啟存儲 Dialog
-- 使用 camp_state.chest_contents = {} 存放共享物品清單
if self.camp_chest and who == game.player then
    -- 開啟自訂 Dialog 讓玩家存放 / 取出物品
    local d = require("mod.dialogs.CampChest").new(game.camp_state)
    game:registerDialog(d)
end
```

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| 農作計時器 | `Game:onTurn()` + `camp_state.farms` | `game.turn` 差值；`energy_to_act / energy_per_tick` 轉換 |
| 農田地形三態 | `data/grids/camp.lua` | `farm_interact` 旗標；Grid `on_move` 提示分派 |
| 農田互動（種植/查詢/收穫） | `Game:farmInteract()` + `setupCommands CHANGE_LEVEL` | `map(x,y,Map.TERRAIN, new_grid)` 替換 Grid |
| 建造系統 | `chats/build_manager.lua` + `_applyBuildingToMap()` | `build_tag` 掃描；Grid 替換；`map.changed = true` |
| 建造狀態持久化 | `game.camp_state` + `Game:save()` | `defaultSavedFields{camp_state=true}` |
| 工人 AI | `ai/commanded_ally.lua` + `_cmd_work` | `ai_state.command = {type="work", task="farm"}` |
| 工人加速農作 | `_cmd_work` AI | `farm.turn_planted -= speed_up`（把種植時間往前移） |
| 建造管理員 NPC | `npcs/camp_npcs.lua` + `on_bump` | 與合成工作台相同的 `on_bump` + Chat 模式 |

**三份教學（Tutorial 09 + 10 + 11）的核心主題是狀態管理的三個層次：**

| 層次 | 存放位置 | 生命週期 |
|------|---------|---------|
| 臨時地圖狀態（篝火冷卻） | `game.level.data[key]` | 跟隨 Level，可跨存檔 |
| 跨樓層 / 跨 Zone 進度（建造、農田） | `game.camp_state`（`game:save()` 宣告） | 跟隨整個存檔，永久保留 |
| 地圖 Grid 替換狀態（農田格、設施格） | Zone 的 `persistent = "zone"` + `.teaz` 磁碟檔 | 跟隨 Zone 持久化 |
