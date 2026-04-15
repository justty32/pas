# 教學 09：戰術指令系統與僱傭兵招募

## 本章目標

實作兩個緊密相關的系統：

1. **戰術指令系統**：玩家可對隊友下達「攻擊目標」、「跟我來」、「待命」、「撤退」等指令，覆寫 NPC 的 AI 行為
2. **僱傭兵招募系統**：城鎮中有一個招募者 NPC，玩家透過對話花費金幣雇用傭兵，傭兵由模板動態生成並加入隊伍

兩個系統的連接點：所有招募來的傭兵都使用戰術指令 AI，可被玩家即時指揮。

---

## 系統設計概覽

```
玩家按下指令鍵
       ↓
CommandMenu Dialog（選擇隊友 + 選擇指令）
       ↓
設定 ally.ai_state.command = {type="...", target=...}
       ↓
每回合 ally:doAI() → 執行 "commanded_ally" AI
       ↓
commanded_ally 讀取 command，決定行為：
  - "attack" → setTarget + dumb_talented_simple
  - "follow" → 追蹤玩家座標
  - "standby" → 等待（consume energy）
  - "flee"   → target_simple + flee_simple
  - nil      → 預設自主戰鬥
```

```
玩家找到招募者 NPC
       ↓
Chat 腳本：選擇傭兵種類，條件判斷（有無足夠金幣）
       ↓
zone:makeEntityByName → 從模板產生 Actor 實例
       ↓
zone:addEntity → 放到地圖上
       ↓
game.party:addMember → 加入隊伍，可被指令系統控制
```

---

## 完整檔案結構

```
mygame/
  mod/
    ai/
      commanded_ally.lua        ← 自訂 AI（核心）
    class/
      interface/
        ActorCommand.lua        ← 玩家的指令介面 mixin
    dialogs/
      CommandMenu.lua           ← 指令選單 UI
    data/
      npcs/
        mercenaries.lua         ← 傭兵模板定義
      chats/
        recruiter.lua           ← 招募者對話腳本
      zones/
        town.lua                ← 城鎮 Zone（含招募者 NPC）
    class/
      Player.lua                ← 綁定指令鍵
      Game.lua                  ← 載入自訂 AI
```

---

## 步驟一：自訂 AI — `commanded_ally`

### 原理

TE4 的 AI 系統是可組合的函式集合。每個 NPC 有一個 `self.ai` 字串，指向要執行的 AI 函式。`ai_state` 是一個持久化的表格，可以存放任意欄位——我們用它來儲存玩家下達的指令。

```
self.ai = "commanded_ally"        -- 每回合執行哪個 AI
self.ai_state.command = {         -- 玩家設定的指令（可為 nil）
    type = "attack",
    target = <Actor>
}
```

### 檔案：`mod/ai/commanded_ally.lua`

```lua
-- mod/ai/commanded_ally.lua
-- 可接受外部指令的隊友 AI
-- 當有 ai_state.command 時執行指令；否則自主尋敵

-- 注意：這個檔案在 ActorAI:loadDefinition() 時被載入
-- 環境中已提供 newAI 函式和 Map 全域變數

-- ── 主要 AI 入口點 ──────────────────────────────────────────
newAI("commanded_ally", function(self)
    local cmd = self.ai_state.command

    -- ── 有玩家指令時：執行指令 ──────────────────────────────
    if cmd then
        if cmd.type == "attack" then
            return _M.ai_commanded_attack(self, cmd)
        elseif cmd.type == "follow" then
            return _M.ai_commanded_follow(self)
        elseif cmd.type == "standby" then
            return _M.ai_commanded_standby(self)
        elseif cmd.type == "flee" then
            return _M.ai_commanded_flee(self)
        end
    end

    -- ── 無指令時：自主行為（先尋敵，找到就打；否則跟隨玩家） ──
    return _M.ai_default_ally(self)
end)

-- ── 攻擊指定目標 ────────────────────────────────────────────
-- 將 ai_target 設為指令中的目標，然後用現有的 dumb_talented_simple 處理移動+攻擊
newAI("_cmd_attack", function(self, cmd)
    local t = cmd.target
    if not t or t.dead then
        -- 目標已死，清除指令
        self.ai_state.command = nil
        game.logPlayer(self, "%s 的攻擊目標已消滅。", self.name)
        return self:runAI("commanded_ally")  -- 重新決策
    end
    self:setTarget(t)
    self:runAI("dumb_talented_simple")
    return true
end)

-- ── 跟隨玩家 ────────────────────────────────────────────────
-- 距離 > 2 時往玩家方向移動
newAI("_cmd_follow", function(self)
    local px, py = game.player.x, game.player.y
    if core.fov.distance(self.x, self.y, px, py) > 2 then
        self:moveDirection(px, py)
    end
    return true
end)

-- ── 待命（原地等待） ─────────────────────────────────────────
-- 回傳 true 表示已執行動作，不再移動
-- TE4 的 useEnergy() 在 move/useTalent 時自動呼叫
-- 這裡我們手動消耗能量避免卡住
newAI("_cmd_standby", function(self)
    self:useEnergy()
    return true
end)

-- ── 撤退 ────────────────────────────────────────────────────
-- 先用 target_simple 找到敵人，然後向反方向逃跑
newAI("_cmd_flee", function(self)
    if self:runAI("target_simple") then
        self:runAI("flee_simple")
    else
        -- 沒有找到敵人：回到玩家身邊
        local px, py = game.player.x, game.player.y
        if core.fov.distance(self.x, self.y, px, py) > 2 then
            self:moveDirection(px, py)
        end
    end
    return true
end)

-- ── 預設自主行為 ─────────────────────────────────────────────
-- 找到敵人就打；沒有敵人就跟隨玩家
newAI("_ally_default", function(self)
    -- target_simple 會自動避開友方（faction 判斷）
    if self:runAI("target_simple") then
        self:runAI("dumb_talented_simple")
        return true
    end
    -- 無敵人：跟隨玩家
    if game.player then
        local px, py = game.player.x, game.player.y
        if core.fov.distance(self.x, self.y, px, py) > 3 then
            self:moveDirection(px, py)
            return true
        end
    end
    return false
end)
```

> **為什麼把子行為也定義為 newAI？**
> 
> TE4 的 `runAI(name)` 讓你可以組合已命名的 AI 片段。把每個行為獨立命名（加底線前綴表示「內部使用」）有兩個好處：
> 1. 其他 AI 可以重用這些片段（例如別的 AI 也可以 `runAI("_cmd_follow")`）
> 2. 方便日誌除錯（`config.settings.log_detail_ai > 1` 時會印出 AI 名稱）

然而為了教學清晰，上面的程式把子函式寫成局部呼叫（`_M.ai_commanded_*`）的形式。實際上 TE4 的設計建議是全部用 `newAI` 命名，並用 `self:runAI("_cmd_attack", cmd)` 傳入參數。以下是更符合 TE4 慣例的寫法：

```lua
-- 在 commanded_ally.lua 中，將各分支改寫為 runAI 呼叫

newAI("commanded_ally", function(self)
    local cmd = self.ai_state.command
    if not cmd then return self:runAI("_ally_default") end

    if cmd.type == "attack" then
        -- 目標死亡時自動清除
        if not cmd.target or cmd.target.dead then
            self.ai_state.command = nil
            return self:runAI("_ally_default")
        end
        self:setTarget(cmd.target)
        return self:runAI("dumb_talented_simple")

    elseif cmd.type == "follow" then
        local px, py = game.player.x, game.player.y
        if core.fov.distance(self.x, self.y, px, py) > 2 then
            self:moveDirection(px, py)
        end
        return true

    elseif cmd.type == "standby" then
        self:useEnergy()
        return true

    elseif cmd.type == "flee" then
        if self:runAI("target_simple") then
            return self:runAI("flee_simple")
        end
        return true
    end
end)

-- 預設自主行為
newAI("_ally_default", function(self)
    if self:runAI("target_simple") then
        return self:runAI("dumb_talented_simple")
    end
    if game.player then
        local d = core.fov.distance(self.x, self.y, game.player.x, game.player.y)
        if d > 3 then return self:moveDirection(game.player.x, game.player.y) end
    end
end)
```

**這是最終版本，之後所有程式碼使用這個版本。**

---

### 在 Game.lua 中載入自訂 AI

TE4 的 AI 定義必須在載入任何 NPC 之前完成。最佳時機是在 `Game:load()` 中：

```lua
-- mod/class/Game.lua（摘錄，加入 AI 載入）
function _M:load(...)
    engine.GameEnergyBased.load(self, ...)

    -- 載入引擎內建 AI 定義
    self.player_class:loadDefinition("/engine/ai/")

    -- 載入模組自訂 AI
    self.player_class:loadDefinition("/mod/ai/")
end
```

> `loadDefinition(dir)` 會掃描目錄下所有 `.lua` 檔並執行，每個檔案中的 `newAI(name, fn)` 呼叫都會被記錄在 `ActorAI.ai_def` 表格中，全域可用。

---

## 步驟二：指令介面 Mixin — `ActorCommand`

這個 mixin 掛載到玩家身上，提供下達指令的方法。

### 檔案：`mod/class/interface/ActorCommand.lua`

```lua
-- mod/class/interface/ActorCommand.lua
-- 玩家側介面：發出戰術指令給隊友

require "engine.class"
local Map = require "engine.Map"

module(..., package.seeall, class.make)

--- 向指定隊友下達指令
-- @param ally   目標隊友 Actor
-- @param cmd_type  "attack"|"follow"|"standby"|"flee"|"auto"
-- @param target    （僅 attack 模式）攻擊目標 Actor
function _M:issueCommand(ally, cmd_type, target)
    if not game.party or not game.party.members[ally] then
        game.logPlayer(self, "無法對非隊友下達指令。")
        return false
    end
    if ally == self then
        game.logPlayer(self, "無法對自己下達指令。")
        return false
    end

    if cmd_type == "auto" then
        -- 清除指令，回到自主 AI
        ally.ai_state.command = nil
        game.logPlayer(self, "命令 %s 恢復自主行動。", ally.name)
    elseif cmd_type == "attack" then
        if not target or target.dead then
            game.logPlayer(self, "無效的攻擊目標。")
            return false
        end
        ally.ai_state.command = {type = "attack", target = target}
        game.logPlayer(self, "命令 %s 攻擊 %s！", ally.name, target.name)
    elseif cmd_type == "follow" then
        ally.ai_state.command = {type = "follow"}
        game.logPlayer(self, "命令 %s 跟隨你。", ally.name)
    elseif cmd_type == "standby" then
        ally.ai_state.command = {type = "standby"}
        game.logPlayer(self, "命令 %s 原地待命。", ally.name)
    elseif cmd_type == "flee" then
        ally.ai_state.command = {type = "flee"}
        game.logPlayer(self, "命令 %s 撤退！", ally.name)
    end

    return true
end

--- 取得所有可指揮的隊友列表
-- @return table  隊友 Actor 的陣列
function _M:getCommandableAllies()
    if not game.party then return {} end
    local list = {}
    for i, actor in ipairs(game.party.m_list) do
        if actor ~= self and not actor.dead then
            list[#list+1] = actor
        end
    end
    return list
end
```

---

## 步驟三：指令選單 — `CommandMenu`

這是玩家用來發出指令的 Dialog。設計上分兩步：
1. 選擇要指揮的隊友（若只有一個，跳過）
2. 選擇指令類型（若是攻擊，再選擇目標）

### 檔案：`mod/dialogs/CommandMenu.lua`

```lua
-- mod/dialogs/CommandMenu.lua
-- 戰術指令選單：讓玩家對隊友下達指令

require "engine.class"
local Dialog = require "engine.ui.Dialog"
local List   = require "engine.ui.List"
local Map    = require "engine.Map"

module(..., package.seeall, class.inherit(Dialog))

function _M:init(player)
    self.player = player
    self.allies = player:getCommandableAllies()

    Dialog.init(self, "戰術指令", 350, 400)

    if #self.allies == 0 then
        -- 沒有隊友，直接顯示提示並關閉
        self:simplePopup("無可用隊友", "你目前沒有可指揮的隊友。")
        return
    end

    if #self.allies == 1 then
        -- 只有一個隊友，直接進入指令選擇
        self:showCommandFor(self.allies[1])
    else
        -- 多個隊友，先選人
        self:showAllyList()
    end
end

--- 顯示隊友選擇列表
function _M:showAllyList()
    local items = {}
    for i, ally in ipairs(self.allies) do
        items[#items+1] = {
            name = ("%s（HP：%d/%d）"):format(ally.name, ally.life, ally.max_life),
            ally = ally,
        }
    end

    local list = List.new{
        width = self.iw,
        list = items,
        fct = function(item)
            self:showCommandFor(item.ally)
        end,
    }
    self:loadUI{{ui=list, x=0, y=0}}
    self:setupUI(true, true)
end

--- 顯示對指定隊友的指令選擇
-- @param ally 目標隊友 Actor
function _M:showCommandFor(ally)
    local cur_cmd = ally.ai_state.command
    local cur_desc = cur_cmd and cur_cmd.type or "自主"

    local commands = {
        {name = "攻擊（選擇目標）", cmd = "attack"},
        {name = "跟隨我",           cmd = "follow"},
        {name = "原地待命",         cmd = "standby"},
        {name = "撤退",             cmd = "flee"},
        {name = "恢復自主行動",     cmd = "auto"},
    }

    -- 在每個選項後面標注當前狀態
    local items = {}
    for i, c in ipairs(commands) do
        local suffix = (cur_desc == c.cmd) and " ◀ 當前" or ""
        items[#items+1] = {
            name = c.name .. suffix,
            cmd  = c.cmd,
            ally = ally,
        }
    end

    local title_label = ("指揮：%s"):format(ally.name)
    self:setTitle(title_label)

    local list = List.new{
        width = self.iw,
        list = items,
        fct = function(item)
            if item.cmd == "attack" then
                -- 攻擊需要額外選擇目標
                self:showTargetListFor(ally)
            else
                self.player:issueCommand(ally, item.cmd)
                self:unregister()
            end
        end,
    }
    self:loadUI{{ui=list, x=0, y=0}}
    self:setupUI(true, true)
    self:setKeyHandling()
end

--- 顯示可攻擊目標列表（FOV 範圍內的敵人）
-- @param ally 下達命令的隊友
function _M:showTargetListFor(ally)
    -- 從玩家 FOV 收集敵方目標
    local targets = {}
    local seen = self.player.fov and self.player.fov.actors_dist or {}
    for i, act in ipairs(seen) do
        if act and not act.dead and self.player:reactionToward(act) < 0 then
            local dist = core.fov.distance(self.player.x, self.player.y, act.x, act.y)
            targets[#targets+1] = {
                name = ("%s（距離 %d）"):format(act.name, dist),
                actor = act,
            }
        end
    end

    if #targets == 0 then
        self:simplePopup("無目標", "視野內沒有可攻擊的敵人。")
        return
    end

    self:setTitle("選擇攻擊目標")
    local list = List.new{
        width = self.iw,
        list = targets,
        fct = function(item)
            self.player:issueCommand(ally, "attack", item.actor)
            self:unregister()
        end,
    }
    self:loadUI{{ui=list, x=0, y=0}}
    self:setupUI(true, true)
    self:setKeyHandling()
end
```

> **`self:simplePopup(title, text)`** 是 `engine.ui.Dialog` 提供的便利函式，顯示一個只有「確定」按鈕的彈窗。

---

## 步驟四：玩家側綁定指令鍵

在 `mod/class/Player.lua` 中繼承 `ActorCommand` mixin，並綁定按鍵：

```lua
-- mod/class/Player.lua（摘錄）
require "engine.class"
local ActorCommand = require "mod.class.interface.ActorCommand"

module(..., package.seeall, class.inherit(
    engine.Player,
    ActorCommand          -- ← 加入指令介面
))

function _M:init(t, no_default)
    engine.Player.init(self, t, no_default)
end

--- 按鍵處理：在 keyboardHandler 或 act() 中加入
function _M:setupKeys()
    -- 按 'c'（或你偏好的鍵）開啟戰術指令選單
    self.key:addCommand(self.key._c, function()
        local menu = require("mod.dialogs.CommandMenu").new(self)
        game:registerDialog(menu)
    end)
end
```

然後在 `Game:run()` 或玩家初始化後呼叫 `player:setupKeys()`。

---

## 步驟五：傭兵模板

### 站位系統：faction

TE4 用 `faction` 字串決定友敵關係。`Faction:factionReaction(f1, f2)` 回傳 ≥ 0（友好/中立）或 < 0（敵對）。`target_simple` AI 會找 `reactionToward(act) < 0` 的目標攻擊。

將傭兵的 `faction` 設為 `"players"` 即可讓他們自動將所有敵人視為攻擊目標：

```lua
faction = "players"   -- 與玩家同陣營，視 monsters faction 為敵
```

### 檔案：`mod/data/npcs/mercenaries.lua`

```lua
-- mod/data/npcs/mercenaries.lua
-- 可招募的傭兵模板
-- 使用 define_as 讓 zone:makeEntityByName 可以精確找到這個模板

local NPC = require "mod.class.NPC"   -- 使用你模組的 NPC 類別

-- ── 鐵衛士（近戰型） ─────────────────────────────────────────
newEntity{
    define_as = "MERC_WARRIOR",
    type = "humanoid", subtype = "human",
    name = "鐵衛士", -- 招募後可被重命名
    display = "@", color = {r=150, g=200, b=255},

    -- 陣營設為 players，自動敵視 monsters
    faction = "players",

    -- 使用我們的指令 AI
    ai = "commanded_ally",
    ai_state = {
        ai_move = "move_simple",
    },

    -- 屬性與等級
    level_range = {1, 10},
    exp_worth   = 0,    -- 殺死不給玩家經驗（傭兵是隊友不是獎勵）
    rank        = 2,

    max_life    = resolvers.rngrange(80, 120),
    life_rating = 12,
    stats = {str=16, dex=12, con=14, mag=5, wil=8, cun=10},

    -- 自動依等級成長
    autolevel = "warrior",

    -- 出生時裝備（resolvers.equip 在 resolve 時執行）
    resolvers.equip{
        {type="weapon", subtype="longsword", defined="IRON_LONGSWORD", random_art_replace={base_list="mod:data/general/objects/weapons.lua"}},
        {type="armor",  subtype="heavy",     defined="IRON_MAIL_ARMOUR"},
    },
}

-- ── 森林弓手（遠程型） ───────────────────────────────────────
newEntity{
    define_as = "MERC_ARCHER",
    type = "humanoid", subtype = "elf",
    name = "森林弓手",
    display = "@", color = {r=100, g=220, b=100},

    faction    = "players",
    ai         = "commanded_ally",
    ai_state   = {ai_move = "move_simple"},

    level_range = {1, 10},
    exp_worth   = 0,
    rank        = 2,

    max_life    = resolvers.rngrange(55, 80),
    life_rating = 9,
    stats = {str=10, dex=18, con=10, mag=5, wil=10, cun=14},

    autolevel   = "archer",

    resolvers.equip{
        {type="weapon", subtype="longbow", defined="ELM_LONGBOW"},
        {type="ammo",   subtype="arrow",   defined="ARROW", nb_object=resolvers.rngrange(20, 40)},
    },
}

-- ── 流浪法師（魔法型） ───────────────────────────────────────
newEntity{
    define_as = "MERC_MAGE",
    type = "humanoid", subtype = "human",
    name = "流浪法師",
    display = "@", color = {r=200, g=100, b=255},

    faction    = "players",
    ai         = "commanded_ally",
    ai_state   = {ai_move = "move_simple", talent_in = 2}, -- 更常使用技能

    level_range = {1, 10},
    exp_worth   = 0,
    rank        = 2,

    max_life    = resolvers.rngrange(40, 60),
    life_rating = 7,
    stats = {str=8, dex=10, con=8, mag=20, wil=14, cun=12},

    autolevel   = "mage",

    talents = {
        [T_FIREBALL] = 3,
        [T_LIGHTNING] = 2,
    },
}
```

> **`exp_worth = 0`**：傭兵死亡不給玩家額外經驗，避免玩家刻意讓傭兵送死刷 XP。
>
> **`ai_state.talent_in = 2`**：`dumb_talented_simple` AI 每 `talent_in` 回合才用一次技能（預設 6）。設為 2 讓法師更積極施法。

---

## 步驟六：招募者對話腳本

### Chat 系統回顧

Chat 腳本（`engine/Chat.lua`）透過 `newChat{id, text, answers}` 定義對話節點。每個 `answers` 項目可有：
- `cond(npc, player)` — 決定這個選項是否顯示
- `action(npc, player)` — 選擇後執行的函式
- `jump` — 跳轉到哪個 Chat id（`nil` 表示結束對話）

### 傭兵費用與金幣

為保持教學獨立性，我們在玩家身上用一個簡單的 `gold` 欄位表示金幣：

```lua
-- 在玩家 init() 中初始化
self.gold = self.gold or 0

-- 增加 / 減少
player.gold = player.gold + 100
player.gold = player.gold - 200

-- 查詢
player.gold   -- 目前金幣
```

> 如果在 ToME addon 中使用，請改用 `player:getMoney()` / `player:incMoney(-200)`。

### 招募流程核心：`zone:makeEntityByName` + `zone:addEntity`

```lua
-- 1. 從模板產生一個完全解析的實例（clone + resolve）
local merc = game.zone:makeEntityByName(game.level, "actor", "MERC_WARRIOR")
-- 注意：makeEntityByName 會自動 resolve() 所有 resolvers
-- 若找不到模板（define_as 不存在），回傳 nil

-- 2. 找一個玩家附近的空格
local x, y = util.findFreeGrid(player.x, player.y, 5, true, {[Map.ACTOR]=true})
-- 參數：起點(x,y)、搜尋半徑、是否需要 LOS、阻擋條件表

-- 3. 放到地圖上（addEntity 會呼叫 merc:added() 等初始化鉤子）
game.zone:addEntity(game.level, merc, "actor", x, y)

-- 4. 加入隊伍
game.party:addMember(merc, {
    control          = "no",             -- 玩家不能直接切換控制
    title            = "傭兵",
    keep_between_levels = true,          -- 切換樓層時保留（跟著走）
})
-- addMember 會自動設定：
--   merc.ai_state.tactic_leash_anchor = game.player
--   merc.ai_state.tactic_leash = 10
```

### 檔案：`mod/data/chats/recruiter.lua`

```lua
-- mod/data/chats/recruiter.lua
-- 招募者 NPC 的對話腳本
-- 透過 Chat.new("mod.data.chats.recruiter", npc, player) 呼叫

local Map = require "engine.Map"

-- ── 首次見面 ─────────────────────────────────────────────────
newChat{
    id = "welcome",
    text = [[我是僱傭兵公會的布托克。如果你手頭寬裕，我可以為你安排幾位精銳戰士。

每位傭兵的招募費用是 200 金幣。你已有 %d 金幣，最多可再招募 %d 名隊友（上限 3 名）。

你想招募哪種傭兵？]],
    text_resolver = function(npc, player)
        local slots = 3 - (#game.party.m_list - 1)   -- 扣掉玩家本人
        return player.gold, math.min(slots, math.floor(player.gold / 200))
    end,
    answers = {
        -- 鐵衛士
        {text = "招募一名鐵衛士（近戰）— 200 金幣",
         cond = function(npc, player)
             local slots = 3 - (#game.party.m_list - 1)
             return player.gold >= 200 and slots > 0
         end,
         action = function(npc, player)
             _M.recruitMerc(npc, player, "MERC_WARRIOR", "鐵衛士")
         end,
         jump = "hired"},

        -- 森林弓手
        {text = "招募一名森林弓手（遠程）— 200 金幣",
         cond = function(npc, player)
             local slots = 3 - (#game.party.m_list - 1)
             return player.gold >= 200 and slots > 0
         end,
         action = function(npc, player)
             _M.recruitMerc(npc, player, "MERC_ARCHER", "森林弓手")
         end,
         jump = "hired"},

        -- 流浪法師
        {text = "招募一名流浪法師（魔法）— 200 金幣",
         cond = function(npc, player)
             local slots = 3 - (#game.party.m_list - 1)
             return player.gold >= 200 and slots > 0
         end,
         action = function(npc, player)
             _M.recruitMerc(npc, player, "MERC_MAGE", "流浪法師")
         end,
         jump = "hired"},

        -- 沒錢
        {text = "（金幣不足，無法招募）",
         cond = function(npc, player)
             return player.gold < 200
         end,
         jump = "no_money"},

        -- 隊伍已滿
        {text = "（隊伍已滿，無法再招募）",
         cond = function(npc, player)
             return #game.party.m_list > 3
         end,
         jump = "full_party"},

        {text = "沒有，再見。"},
    },
}

-- ── 招募成功 ─────────────────────────────────────────────────
newChat{
    id = "hired",
    text = [[好，已為你安排完畢。記得好好指揮你的隊友。

（提示：按 C 鍵開啟戰術指令選單）]],
    answers = {
        {text = "繼續招募...", jump = "welcome"},
        {text = "謝了，再見。"},
    },
}

-- ── 金幣不足 ─────────────────────────────────────────────────
newChat{
    id = "no_money",
    text = [[我不是在做慈善。至少帶 200 金幣來再說吧。]],
    answers = {{text = "...我去想辦法。"}},
}

-- ── 隊伍已滿 ─────────────────────────────────────────────────
newChat{
    id = "full_party",
    text = [[你已經帶了夠多人了。先讓幾個人離隊再來吧。]],
    answers = {{text = "好的。"}},
}

-- ── 招募執行函式（非對話節點，純 Lua） ────────────────────────
-- Chat 腳本中的函式只能存放在 _M（Chat 物件的 metatable）裡
function _M.recruitMerc(npc, player, template_id, label)
    -- 扣除金幣
    player.gold = player.gold - 200

    -- 從模板生成傭兵
    local merc = game.zone:makeEntityByName(game.level, "actor", template_id)
    if not merc then
        game.logPlayer(player, "#RED#招募失敗：找不到傭兵模板 %s。", template_id)
        player.gold = player.gold + 200   -- 退款
        return
    end

    -- 設定名字（加入隊主名稱以區分）
    merc.name = label

    -- 尋找玩家附近的空格
    local x, y = util.findFreeGrid(player.x, player.y, 5, true, {[Map.ACTOR]=true})
    if not x then
        game.logPlayer(player, "#RED#招募失敗：附近沒有足夠的空間。")
        player.gold = player.gold + 200
        return
    end

    -- 放入地圖
    game.zone:addEntity(game.level, merc, "actor", x, y)

    -- 加入隊伍
    game.party:addMember(merc, {
        control             = "no",
        title               = "傭兵",
        keep_between_levels = true,
    })

    game.logPlayer(player, "#LIGHT_GREEN#%s 加入了你的隊伍！按 C 鍵開啟戰術指令選單。", label)
end
```

> **`text_resolver`** 不是 TE4 原生欄位——標準 Chat 系統的 `text` 是純字串，不支援動態內容。若你需要在對話文字中插入數值，有兩種做法：
> 1. 在 `action` 函式中用 `game.logPlayer` 顯示額外資訊
> 2. 或在進入 Chat 前計算好字串，作為 `text` 傳入（進階做法）
>
> 上面的 `text_resolver` 欄位只是教學標注，實際上你應該把動態內容放到 `game.logPlayer` 或改用方法一。以下是實用版的正確做法：

```lua
-- 實用版：動態文字用 text 函式（TE4 支援 text 為 function）
newChat{
    id = "welcome",
    text = function(npc, player)
        local slots = math.max(0, 3 - (#game.party.m_list - 1))
        return ("我是布托克。費用 200 金幣/人。你有 %d 金幣，可再招募 %d 人。"):format(
            player.gold,
            math.min(slots, math.floor(player.gold / 200))
        )
    end,
    -- ...answers 同上
}
```

> **TE4 的 `text` 欄位支援 function**：引擎在渲染對話時會呼叫 `util.getval(node.text, npc, player)`，若是函式就傳入 npc/player 並取回字串。這是安全的動態文字做法。

---

## 步驟七：城鎮 Zone 設定

在城鎮 Zone 的靜態地圖或 NPC 列表中加入招募者：

### 方法 A：在靜態地圖 Lua 中直接定義 NPC

```lua
-- mod/data/zones/town/map.lua（Static map）
-- 在特定座標放置招募者

-- 地圖格: R = 招募者 NPC
return {
    w = 20, h = 20,
    map = {
        -- ...（省略地形格）
    },
    -- 特殊格子上的 NPC 定義
    add_actor = {
        R = function(x, y)
            local npc = game.zone:makeEntityByName(game.level, "actor", "RECRUITER_BUTOK")
            if npc then
                game.zone:addEntity(game.level, npc, "actor", x, y)
            end
        end,
    },
}
```

### 方法 B：在 Zone 定義中加入固定 NPC 列表

```lua
-- mod/data/zones/town.lua
local Zone = require "engine.Zone"

return Zone.new("town", {
    name        = "洛克港鎮",
    level_range = {1, 1},
    level_scheme = "player",
    max_level   = 1,

    width = 40, height = 40,
    all_remembered   = true,   -- 城鎮全部可見
    all_lited        = true,
    persistent       = "zone", -- 城鎮狀態持久化

    generator = {
        map   = {class="engine.generator.map.Static", map="mod/maps/town"},
        actor = {class="engine.generator.actor.OnceAtCoord",
                 -- 在特定座標放置固定 NPC
                 actors = {
                     {defined="RECRUITER_BUTOK", x=10, y=8},
                 }},
    },

    -- 載入傭兵模板（讓 makeEntityByName 可以找到）
    npc_list  = require("mod.class.NPC"):loadList{
        "mod/data/npcs/town.lua",
        "mod/data/npcs/mercenaries.lua",  -- ← 必須包含
    },
})
```

### 招募者 NPC 定義

```lua
-- mod/data/npcs/town.lua（摘錄）
newEntity{
    define_as   = "RECRUITER_BUTOK",
    type        = "humanoid", subtype = "human",
    name        = "布托克",
    display     = "@", color = {r=255, g=200, b=100},
    faction     = "players",
    level_range = {1, 1},
    exp_worth   = 0,
    rank        = 1,
    
    -- 不自動移動
    ai = "none",
    ai_state = {},
    
    -- 對話腳本路徑
    chat = "mod.data.chats.recruiter",
    
    -- 點擊 / 互動觸發對話
    on_interact = function(self, who)
        local chat = require "engine.Chat"
        local c = chat.new(self.chat, self, who)
        c:invoke()
    end,
    
    stats = {str=12, dex=12, con=12, mag=5, wil=10, cun=10},
    max_life = resolvers.rngrange(50, 70),
}
```

> **`ai = "none"`**：定義在 `simple.lua` 中的一個空 AI（`newAI("none", function(self) end)`），讓 NPC 完全靜止，不尋找目標也不移動。城鎮 NPC 通常使用這個 AI。

---

## 步驟八：持久化考量

### 指令（`ai_state.command`）的存檔

`ai_state` 是普通的 Lua 表，由 TE4 序列化系統（`serial.c`）自動存檔。但 `command.target` 是一個 Actor 參考：

```lua
ally.ai_state.command = {type = "attack", target = <Actor>}
--                                                  ↑ 這是 Actor 物件
```

TE4 的序列化系統使用 `uid` 來重建物件參考。Actor 物件有 `__ATOMIC = true` 標記（見 `engine/Entity.lua`），因此它們**不會被深度複製**，而是透過 `uid` 記錄參考。載入後，弱引用表 `__uids` 會重建這個參考。

**實際上你不需要額外處理**——TE4 已正確處理 Actor 作為表值的存檔。只需注意：如果目標在存檔時已死亡，重載後 `cmd.target.dead == true`，`commanded_ally` AI 會自動清除這個指令。

### 傭兵的跨樓層跟隨

`game.party:addMember(merc, {keep_between_levels=true})` 設定後，`Party:leftLevel()` 函式會在切換樓層時保留此成員（不觸發 `removeMember`）。引擎會在新樓層的安全區域重新放置傭兵。

---

## 步驟九：整合到 `load.lua`

```lua
-- mod/load.lua（摘錄）

-- 確保 Party 系統已初始化
dofile("/mod/class/Party.lua")

-- 載入 NPC 模板（包含傭兵）
-- （通常在 Zone 的 npc_list 中已指定，這裡是確保全域可用）

-- 初始化 game.party（如果你的模組使用 Party 系統）
game.party = require("mod.class.Party").new()
game.party:addMember(game.player, {
    main    = true,
    control = "full",
    title   = "主角",
    keep_between_levels = true,
})
```

---

## 完整測試流程

### 1. 測試 AI 指令

```lua
-- 在 cheat console 測試（按 ` 或 F1 進入）
-- 取得第一個隊友
local ally = game.party.m_list[2]
if ally then
    -- 下達跟隨指令
    ally.ai_state.command = {type = "follow"}
    print("指令設定成功，隊友 AI:", ally.ai)
    
    -- 確認 AI 是否正確
    assert(ally.ai == "commanded_ally", "AI 未設定！")
    
    -- 下達攻擊指令（需要有敵人）
    local enemy = game.level.map(5, 5, require("engine.Map").ACTOR)
    if enemy and game.player:reactionToward(enemy) < 0 then
        ally.ai_state.command = {type = "attack", target = enemy}
    end
end
```

### 2. 測試招募流程

```lua
-- 在 cheat console 給玩家金幣
game.player.gold = 500
print("金幣設定完成:", game.player.gold)

-- 手動觸發招募
local merc = game.zone:makeEntityByName(game.level, "actor", "MERC_WARRIOR")
if merc then
    local x, y = util.findFreeGrid(game.player.x, game.player.y, 5, true,
        {[require("engine.Map").ACTOR]=true})
    game.zone:addEntity(game.level, merc, "actor", x, y)
    game.party:addMember(merc, {control="no", keep_between_levels=true})
    print("招募成功！隊伍人數:", #game.party.m_list)
else
    print("ERROR: 找不到 MERC_WARRIOR 模板！")
    print("確認 mercenaries.lua 已被載入到 zone.npc_list")
end
```

---

## 常見錯誤排查

| 錯誤現象 | 可能原因 | 解法 |
|---------|---------|------|
| `[runAI] UNDEFINED AI "commanded_ally"` | `mod/ai/` 未被載入 | 在 `Game:load()` 中呼叫 `self.player_class:loadDefinition("/mod/ai/")` |
| 傭兵招募後不移動 | `ai = "none"` 設在傭兵身上 | 確認傭兵模板的 `ai = "commanded_ally"` |
| `makeEntityByName` 回傳 nil | 傭兵模板未加入 zone.npc_list | 在 Zone 定義的 `npc_list` 中包含 `mercenaries.lua` |
| 傭兵攻擊玩家 | faction 設定錯誤 | 傭兵模板中設 `faction = "players"` |
| 指令對話框無法開啟 | `ActorCommand` mixin 未繼承 | 在 Player.lua 的 `class.inherit(...)` 中加入 `ActorCommand` |
| 切換樓層後傭兵消失 | `keep_between_levels` 未設為 true | 在 `addMember` 的 def 表格中設 `keep_between_levels = true` |
| 傭兵在 standby 時凍結（能量不消耗） | 沒有呼叫 `useEnergy()` | 在 `_cmd_standby` AI 中確認有 `self:useEnergy()` |
| 攻擊指令無效（目標死後繼續攻擊 nil） | 沒有清除 dead 目標 | `commanded_ally` AI 中 `if not cmd.target or cmd.target.dead then` 清除指令 |

---

## 進階擴展方向

### 1. 指令優先序與指令佇列

目前設計是「最後一個指令覆蓋前一個」。若要支援佇列：

```lua
-- ai_state.command_queue 是一個陣列
ally.ai_state.command_queue = ally.ai_state.command_queue or {}
table.insert(ally.ai_state.command_queue, {type="attack", target=enemy})
-- AI 每次執行完一個指令後 table.remove(queue, 1)
```

### 2. 傭兵等級隨玩家提升

在 `Party:addMember` 後立即同步等級：

```lua
-- 強制傭兵達到玩家等級
if merc.forceLevelup then
    merc:forceLevelup(game.player.level)
end
```

### 3. 傭兵死亡後的處理

在傭兵身上加入 `on_die` 回呼：

```lua
on_die = function(self, who)
    if game.party and game.party.members[self] then
        game.party:removeMember(self)
        game.logPlayer(game.player, "#RED#%s 陣亡了！", self.name)
    end
end,
```

### 4. 多人傭兵的群體指令

```lua
-- 對所有隊友同時下達指令
function Player:issueCommandToAll(cmd_type, target)
    local allies = self:getCommandableAllies()
    for _, ally in ipairs(allies) do
        self:issueCommand(ally, cmd_type, target)
    end
end
```

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| 自訂 AI | `mod/ai/commanded_ally.lua` | `newAI(name, fn)` / `self:runAI(name)` |
| AI 狀態儲存 | `self.ai_state.command` | Lua 表，自動序列化 |
| AI 組合 | `commanded_ally` 呼叫 `dumb_talented_simple`, `flee_simple` | `self:runAI(sub_ai)` |
| 下達指令的介面 | `ActorCommand` mixin | `ally.ai_state.command = {...}` |
| 指令 UI | `CommandMenu` Dialog | `Dialog`, `List`, `game:registerDialog` |
| 傭兵模板 | `mercenaries.lua` | `define_as`, `resolvers.equip` |
| 從模板生成 NPC | Chat action | `zone:makeEntityByName(level, "actor", name)` |
| 放置到地圖 | Chat action | `zone:addEntity(level, e, "actor", x, y)` |
| 加入隊伍 | Chat action | `party:addMember(actor, {control="no", keep_between_levels=true})` |
| 友敵判斷 | 傭兵模板 | `faction = "players"` |

兩個系統的核心思路相同：**用 `ai_state` 作為玩家與 AI 之間的通訊橋樑**。玩家寫入指令，AI 在每回合讀取並執行——這個模式可以延伸到任何需要玩家控制 NPC 行為的場景。
