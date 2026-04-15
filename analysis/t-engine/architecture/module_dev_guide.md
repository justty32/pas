# T-Engine 4 — 模組開發指南

> 本文件基於 `game/modules/example/` 範例模組分析，說明如何從零開始建立一個 TE4 遊戲模組。

---

## 1. 模組生命週期

```
1. 啟動引擎 (bootstrap/boot.lua)
   → 掛載 /game/engines/te4-1.7.6.teae 到 /engine/
   → 掛載 /game/modules/<模組名>/ 到 /mod/

2. 引擎初始化 (/engine/init.lua)
   → 載入 Addon 基礎設施
   → 掛載已啟用的 Addon (.teaa) 到 /mod/addons/<addon>/

3. 載入器 (game/loader/init.lua, pre-init.lua)
   → 設定自訂 Lua package.loaders（含 superload 攔截）
   → 註冊 RNG、table 序列化、基礎工具函數

4. 模組入口 (init.lua → starter → load.lua)
   → 載入鍵位定義、傷害類型、技能、效果、出生設定
   → 回傳 Game 類別

5. 遊戲啟動 (Game:newGame)
   → 角色創建 (Birther)
   → 載入第一個 Zone/Level
   → 進入主迴圈
```

---

## 2. 檔案結構

一個完整模組的目錄結構：

```
game/modules/mymod/
├── init.lua                    # 模組元資料
├── load.lua                    # 資料載入入口
│
├── class/                      # 類別定義
│   ├── Game.lua                # 遊戲主控制器（必要）
│   ├── Actor.lua               # 角色/怪物基底
│   ├── Player.lua              # 玩家角色
│   ├── NPC.lua                 # NPC（加入 AI）
│   ├── Grid.lua                # 地形格
│   ├── Object.lua              # 物品（若需要）
│   └── interface/
│       └── Combat.lua          # 自訂戰鬥介面
│
├── data/
│   ├── damage_types.lua        # 傷害類型定義
│   ├── talents.lua             # 技能定義
│   ├── timed_effects.lua       # Buff/Debuff 定義
│   ├── birth/
│   │   └── descriptors.lua     # 角色創建選項
│   ├── general/                # 全域共用實體
│   │   ├── grids/
│   │   │   └── basic.lua       # 基本地形（地板、牆、門…）
│   │   └── npcs/
│   │       └── kobold.lua      # NPC 模板
│   ├── zones/                  # 區域定義
│   │   └── dungeon/
│   │       ├── zone.lua        # 區域設定與生成器
│   │       ├── grids.lua       # 本區地形載入
│   │       ├── npcs.lua        # 本區 NPC 載入
│   │       ├── objects.lua     # 本區物品載入
│   │       └── traps.lua       # 本區陷阱載入
│   ├── rooms/                  # 房間模板（供地圖生成器使用）
│   │   ├── simple.lua
│   │   └── pilar.lua
│   └── gfx/particles/          # 粒子特效定義
│       └── acid.lua
│
├── dialogs/                    # UI 對話框
│   ├── DeathDialog.lua
│   └── Quit.lua
│
└── data/locales/               # 在地化翻譯
    └── ja_JP.lua
```

---

## 3. init.lua — 模組元資料

```lua
-- game/modules/mymod/init.lua
name = "My Roguelike"
long_name = "My First T-Engine4 Roguelike"
short_name = "mymod"
author = { "Author Name", "email@example.com" }
homepage = "https://example.com"
version = {1, 0, 0}
engine = {1, 7, 6, "te4"}       -- 所需引擎最低版本
starter = "mod.load"             -- 入口函數（對應 load.lua）
show_only_on_cheat = false       -- true = 在正常選單中隱藏
no_hierarchical_saves = true     -- true = 不使用階層式存檔
allow_hierarchical_saves = false
```

關鍵欄位：
- **`short_name`**：用作存檔資料夾名稱、虛擬路徑識別符。
- **`engine`**：`{major, minor, patch, "te4"}`，引擎會驗證相容性。
- **`starter`**：Lua 模組路徑，引擎呼叫此路徑對應的 `load.lua` 檔案。

---

## 4. load.lua — 資料載入入口

`load.lua` 負責在遊戲開始前載入所有定義（傷害、技能、效果等），最後回傳 Game 類別。

```lua
-- game/modules/mymod/load.lua

-- 引入引擎元件
local KeyBind = require "engine.KeyBind"
local DamageType = require "engine.DamageType"
local ActorStats = require "engine.interface.ActorStats"
local ActorResource = require "engine.interface.ActorResource"
local ActorTalents = require "engine.interface.ActorTalents"
local ActorTemporaryEffects = require "engine.interface.ActorTemporaryEffects"
local ActorAI = require "engine.interface.ActorAI"
local Birther = require "engine.Birther"

-- 1. 載入鍵位綁定（引擎內建組合）
KeyBind:load("move,hotkeys,inventory,actions,interface,debug")

-- 2. 載入遊戲資料定義
DamageType:loadDefinition("/data/damage_types.lua")
ActorTalents:loadDefinition("/data/talents.lua")
ActorTemporaryEffects:loadDefinition("/data/timed_effects.lua")

-- 3. 定義角色資源（自訂的 MP、怒氣、能量…）
ActorResource:defineResource("Power", "power", nil, "power_regen",
    "Power is used to fuel special talents.")

-- 4. 定義角色屬性
ActorStats:defineStat("Strength",     "str", 10, 1, 100, "Physical power")
ActorStats:defineStat("Dexterity",    "dex", 10, 1, 100, "Agility")
ActorStats:defineStat("Constitution",  "con", 10, 1, 100, "Health")

-- 5. 載入 AI 行為定義（使用引擎內建 AI）
ActorAI:loadDefinition("/engine/ai/")

-- 6. 載入角色創建描述
Birther:loadDefinition("/data/birth/descriptors.lua")

-- 7. 若為即時制，啟用即時模式
-- core.game.setRealtime(20)  -- 每秒 20 tick

-- 8. 回傳 Game 類別（引擎會呼叫 Game.new()）
return { require "mod.class.Game" }
```

---

## 5. 類別定義

### 5.1 Actor.lua — 角色基底

```lua
-- game/modules/mymod/class/Actor.lua
require "engine.class"
local Map = require "engine.Map"
require "engine.Actor"
require "engine.Autolevel"
require "engine.interface.ActorTemporaryEffects"
require "engine.interface.ActorLife"
require "engine.interface.ActorProject"
require "engine.interface.ActorLevel"
require "engine.interface.ActorStats"
require "engine.interface.ActorTalents"
require "engine.interface.ActorResource"
require "engine.interface.ActorFOV"
require "mod.class.interface.Combat"

module(..., package.seeall, class.inherit(
    engine.Actor,
    engine.interface.ActorTemporaryEffects,
    engine.interface.ActorLife,
    engine.interface.ActorProject,
    engine.interface.ActorLevel,
    engine.interface.ActorStats,
    engine.interface.ActorTalents,
    engine.interface.ActorResource,
    engine.interface.ActorFOV,
    mod.class.interface.Combat
))

function _M:init(t, no_default)
    -- 設定預設值（在 engine.Actor.init 之前）
    t.max_life = t.max_life or 10
    t.max_stamina = t.max_stamina or 10

    engine.Actor.init(self, t, no_default)
    engine.interface.ActorTemporaryEffects.init(self, t, no_default)
    engine.interface.ActorLife.init(self, t, no_default)
    engine.interface.ActorProject.init(self, t, no_default)
    engine.interface.ActorLevel.init(self, t, no_default)
    engine.interface.ActorStats.init(self, t, no_default)
    engine.interface.ActorTalents.init(self, t, no_default)
    engine.interface.ActorResource.init(self, t, no_default)
    engine.interface.ActorFOV.init(self, t, no_default)
end

function _M:act()
    if not self:enoughEnergy() then return false end

    -- 每回合處理
    self:regenLife()
    self:regenResources()
    self:cooldownTalents()
    self:timedEffects()

    return true  -- 回傳 true 表示可以行動
end

function _M:move(x, y, force)
    local moved = engine.Actor.move(self, x, y, force)
    if not moved then return false end
    self:useEnergy()  -- 消耗行動點
    return true
end

function _M:tooltip()
    return ([[%s
#00ff00#Level: %d
#ff0000#HP: %d / %d]]):format(
        self.name, self.level or 1,
        self.life, self.max_life
    )
end
```

**重要模式**：
- `_M` 是 `module()` 建立的模組 table，即類別本身。
- 所有 mixin 的 `init` 必須在建構時呼叫。
- `act()` 回傳 `true` 表示角色有能力行動（energy 足夠）。

### 5.2 Player.lua — 玩家角色

```lua
require "engine.class"
require "mod.class.Actor"
require "engine.interface.PlayerRest"
require "engine.interface.PlayerRun"
require "engine.interface.PlayerMouse"
require "engine.interface.PlayerHotkeys"

module(..., package.seeall, class.inherit(
    mod.class.Actor,
    engine.interface.PlayerRest,
    engine.interface.PlayerRun,
    engine.interface.PlayerMouse,
    engine.interface.PlayerHotkeys
))

function _M:init(t, no_default)
    t.player = true
    t.faction = t.faction or "players"
    mod.class.Actor.init(self, t, no_default)
    self.lite = t.lite or 0  -- 玩家照明範圍
end

function _M:act()
    if not mod.class.Actor.act(self) then return false end

    -- 處理自動行為（休息、奔跑）
    if self.resting then self:restStep() return false end
    if self.running then self:runStep() return false end

    -- 暫停遊戲等待玩家輸入
    game.paused = true
end

function _M:move(x, y, force)
    local moved = mod.class.Actor.move(self, x, y, force)
    if moved then
        -- 移動後更新地圖視口（以玩家為中心）
        game.level.map:moveViewSurround(self.x, self.y, 8, 8)
    end
    return moved
end

function _M:playerFOV()
    self:computeFOV(self.sight or 20, "block_sight", function(x, y)
        game.level.map:apply(x, y)   -- 標記格子為可見
        game.level.map.seens(x, y, true)  -- 記住已看見
    end, true, false, true)
end

function _M:die(src)
    -- 玩家死亡時顯示死亡對話框（而非直接移除）
    game:registerDialog(require("mod.dialogs.DeathDialog").new(self))
end
```

**關鍵差異**：
- 玩家 `act()` 設定 `game.paused = true` 等待輸入。
- 移動後呼叫 `moveViewSurround` 捲動地圖視口。
- 死亡不直接移除角色，而是顯示 DeathDialog。

### 5.3 NPC.lua — AI 角色

```lua
require "engine.class"
require "mod.class.Actor"
require "engine.interface.ActorAI"

module(..., package.seeall, class.inherit(
    mod.class.Actor,
    engine.interface.ActorAI
))

function _M:init(t, no_default)
    mod.class.Actor.init(self, t, no_default)
    engine.interface.ActorAI.init(self, t, no_default)
end

function _M:act()
    if not mod.class.Actor.act(self) then return false end

    -- 計算視野
    self:computeFOV(self.sight or 20)
    -- 執行 AI 決策
    self:doAI()
end

-- 受傷時鎖定攻擊者為目標
function _M:onTakeHit(value, src)
    if src and src.player then
        self.ai_target.actor = src
    end
    return value
end
```

### 5.4 Grid.lua — 地形

```lua
require "engine.class"
require "engine.Grid"

module(..., package.seeall, class.inherit(engine.Grid))

function _M:init(t, no_default)
    engine.Grid.init(self, t, no_default)
end

-- 控制移動阻擋
function _M:block_move(x, y, e, act, couldpass)
    -- 門：碰到自動開啟
    if self.door_opened and act then
        game.level.map(x, y, engine.Map.TERRAIN,
            game.zone.grid_list[self.door_opened])
        return true  -- 消耗移動但通過
    end
    return self.does_block_move
end
```

### 5.5 Combat.lua — 戰鬥介面

```lua
-- game/modules/mymod/class/interface/Combat.lua
require "engine.class"
local DamageType = require "engine.DamageType"

module(..., package.seeall, class.make)

-- 碰撞邏輯：撞到敵人 = 攻擊
function _M:bumpInto(target)
    if target:reactionToward(self) < 0 then
        return self:attackTarget(target)
    end
end

-- 實際攻擊計算
function _M:attackTarget(target, mult)
    mult = mult or 1
    local dam = self.combat.dam * mult
    -- 傷害 = 攻擊力 + 力量加成 - 護甲
    dam = dam + self:getStr()
    dam = dam - (target.combat_armor or 0)
    if dam < 0 then dam = 0 end

    DamageType:get(DamageType.PHYSICAL).projector(
        self, target.x, target.y, DamageType.PHYSICAL, dam)
    self:useEnergy()
    return true
end
```

### 5.6 Game.lua — 遊戲控制器

Game 是模組中最複雜的類別，負責整個遊戲生命週期：

```lua
require "engine.class"
require "engine.GameTurnBased"
require "engine.interface.GameTargeting"
local Map = require "engine.Map"
local Level = require "engine.Level"
local Zone = require "engine.Zone"
local Birther = require "engine.Birther"

module(..., package.seeall, class.inherit(
    engine.GameTurnBased,
    engine.interface.GameTargeting
))

function _M:init()
    engine.GameTurnBased.init(self,
        engine.KeyBind.new(),   -- 鍵盤
        engine.Mouse.new(),     -- 滑鼠
        "mymod",                -- 存檔目錄名
        12, 14                  -- energy_to_act, energy_per_tick
    )
    self.paused = true  -- 回合制從暫停開始
end

function _M:run()
    -- 建立 UI 元件
    self.log = engine.LogDisplay.new(0, self.h * 0.80, self.w * 0.5, self.h * 0.20, nil, nil, nil, {255,255,255}, {30,30,30})
    self.logSeen = function(e, style, ...) if e and self.level.map.seens(e.x, e.y) then self.log(style, ...) end end
    self.hotkeys_display = engine.HotkeysDisplay.new(nil, self.w * 0.5, self.h * 0.80, self.w * 0.5, self.h * 0.20, {30,30,30})
    self.tooltip = engine.Tooltip.new(nil, nil, {255,255,255}, {30,30,30})
    self.flyers = engine.FlyingText.new()

    -- 設定操作
    self:setupCommands()
    self:setupMouse()

    -- 若是新遊戲，啟動角色創建
    if not self.player then self:newGame() end
end

function _M:newGame()
    -- Birther 系統處理角色創建
    self.player = require("mod.class.Player").new{
        name = "Player", faction = "players",
    }
    self:setupPlayer(self.player)
    -- 或使用 Birther 對話框：
    -- self:registerDialog(Birther.new(self.player, ...))
end

-- 切換關卡
function _M:changeLevel(lev, zone)
    -- 離開當前關卡
    if self.level then
        self:leaveLevel(self.level, lev)
    end

    -- 載入/生成新關卡
    if zone then
        self.zone = Zone.new(zone)
    end
    self.level = self.zone:getLevel(self, lev)

    -- 放置玩家到入口
    local spot = self.level:pickSpot{type="up"}
    if spot then
        self.player:move(spot.x, spot.y, true)
    end

    -- 將玩家加入關卡
    self.level:addEntity(self.player)

    -- 初始化地圖顯示
    self.level.map:moveViewSurround(self.player.x, self.player.y, 8, 8)
end

function _M:leaveLevel(level, lev)
    -- 儲存玩家在此關卡的位置
    self.player.x_old, self.player.y_old = self.player.x, self.player.y
    level:removeEntity(self.player)
end

function _M:tick()
    if self.paused then return true end
    engine.GameTurnBased.tick(self)
    -- 玩家行動後自動暫停
    if self.player and not self.player:enoughEnergy() then
        self.paused = true
    end
    return true
end

function _M:display(nb_keyframe)
    -- 繪製地圖
    if self.level and self.level.map then
        self.level.map:display()
    end
    -- 繪製 UI 元件
    self.log:display()
    self.hotkeys_display:display()
end

function _M:setupCommands()
    -- 綁定鍵位到動作
    self.key:addBinds{
        MOVE_LEFT  = function() self.player:move(self.player.x-1, self.player.y) end,
        MOVE_RIGHT = function() self.player:move(self.player.x+1, self.player.y) end,
        MOVE_UP    = function() self.player:move(self.player.x, self.player.y-1) end,
        MOVE_DOWN  = function() self.player:move(self.player.x, self.player.y+1) end,

        REST = function() self.player:restInit(100, "resting", "rested") end,
        RUN  = function() self.player:runInit() end,

        USE_TALENT = function()
            self:registerDialog(require("engine.dialogs.UseTalents").new(self.player))
        end,

        CHANGE_LEVEL = function()
            local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
            if e.change_level then
                self:changeLevel(
                    self.level.level + e.change_level,
                    e.change_zone
                )
            end
        end,
    }
end
```

---

## 6. 資料定義

### 6.1 傷害類型 (`data/damage_types.lua`)

```lua
-- 設定預設投射器（處理未自訂的傷害類型）
setDefaultProjector(function(src, x, y, type, dam)
    local target = game.level.map(x, y, Map.ACTOR)
    if target then
        game.logSeen(target, "%s hits %s for #RED#%d %s#LAST# damage.",
            src.name:capitalize(), target.name, dam, DamageType:get(type).name)
        target:takeHit(dam, src)
    end
end)

-- 基礎傷害類型
newDamageType{ name = "physical", type = "PHYSICAL" }
newDamageType{ name = "fire",     type = "FIRE",  text_color = "#LIGHT_RED#" }
newDamageType{ name = "cold",     type = "COLD",  text_color = "#1133F3#" }
newDamageType{ name = "acid",     type = "ACID",  text_color = "#GREEN#" }

-- 帶自訂投射器的傷害類型（例：酸液燃燒 debuff）
newDamageType{
    name = "acidburn", type = "ACIDBURN",
    projector = function(src, x, y, type, dam)
        local target = game.level.map(x, y, Map.ACTOR)
        if target then
            -- 施加 ACIDBURN 效果，持續 3 回合
            target:setEffect(target.EFF_ACIDBURN, 3, {
                src = src,
                power = dam / 3,
            })
        end
    end,
}
```

### 6.2 技能 (`data/talents.lua`)

```lua
-- 定義技能類型（分類）
newTalentType{ type = "role/combat", name = "combat", description = "Combat techniques" }

newTalent{
    name = "Kick",
    type = {"role/combat", 1},  -- {類型, 最低等級}
    points = 1,                  -- 學習所需技能點
    cooldown = 6,                -- 冷卻回合數
    power = 2,                   -- 消耗的 power 資源
    range = 1,
    action = function(self, t)
        -- 選擇目標
        local tg = {type = "hit", range = self:getTalentRange(t)}
        local x, y, target = self:getTarget(tg)
        if not target then return nil end
        if core.fov.distance(self.x, self.y, x, y) > 1 then return nil end

        -- 擊退目標
        target:knockback(self.x, self.y, 2 + self:getDex())
        return true  -- 回傳 true 表示技能成功使用
    end,
    info = function(self, t)
        return "Kicks the target, knocking it back."
    end,
}
```

技能使用流程：
1. Actor 呼叫 `self:useTalent(T_KICK)`
2. 引擎呼叫 `self:preUseTalent(t)` 檢查資源/冷卻
3. 執行 `t.action(self, t)`
4. 引擎呼叫 `self:postUseTalent(t, ret)` 扣除資源、設冷卻

### 6.3 Buff/Debuff (`data/timed_effects.lua`)

```lua
newEffect{
    name = "ACIDBURN",
    desc = "Burning from acid",
    type = "physical",
    status = "detrimental",       -- "beneficial" 或 "detrimental"
    parameters = { power = 1 },   -- 預設參數
    on_gain = function(self, err) return "#Target# is covered in acid!", "+Acid" end,
    on_lose = function(self, err) return "#Target# is free from the acid.", "-Acid" end,
    on_timeout = function(self, eff)
        -- 每回合觸發：造成酸液傷害
        DamageType:get(DamageType.ACID).projector(
            eff.src or self, self.x, self.y, DamageType.ACID, eff.power)
    end,
}
```

施加效果：`target:setEffect(target.EFF_ACIDBURN, duration, {power=10, src=self})`

### 6.4 角色創建 (`data/birth/descriptors.lua`)

```lua
-- base 類型：所有角色共有的基礎屬性
newBirthDescriptor{
    type = "base",
    name = "base",
    experience = 1.0,
    copy = {
        -- 直接複製到角色屬性
        max_level = 10,
        lite = 4,
        max_life = 25,
        resolvers.equip{
            {type="weapon", subtype="longsword", name="iron longsword"},
        },
    },
}

-- role 類型：職業選擇
newBirthDescriptor{
    type = "role",
    name = "Destroyer",
    desc = { "A powerful warrior." },
    stats = { str = 3, con = 2 },
    talents = { [ActorTalents.T_KICK] = 1 },
    copy = {
        max_life = 50,
        power_regen = 0.5,
    },
}
```

Birther 依 `type` 分組，玩家逐層選擇（base → role → …），所有選擇的 `copy`、`stats`、`talents` 累加到角色上。

---

## 7. Zone 定義

### 7.1 zone.lua — 區域設定

```lua
-- data/zones/dungeon/zone.lua
return {
    name = "Old Ruins",
    level_range = {1, 1},     -- NPC 等級範圍
    max_level = 10,            -- 最大樓層數
    decay = {300, 800},        -- 離開後多久可清除（遊戲時間 tick）
    width = 50, height = 50,   -- 地圖尺寸
    persistent = "zone",       -- 持久化策略: "zone" | "level" | false

    generator = {
        map = {
            class = "engine.generator.map.Roomer",
            nb_rooms = 10,
            rooms = {"simple", "pilar"},  -- 對應 data/rooms/*.lua
            lite_room_chance = 100,
            ['.'] = "FLOOR",              -- 字元 → Grid define_as 映射
            ['#'] = "WALL",
            up = "UP",
            down = "DOWN",
            door = "DOOR",
        },
        actor = {
            class = "engine.generator.actor.Random",
            nb_npc = {20, 30},            -- 每層生成 NPC 數量
        },
        object = {
            class = "engine.generator.object.Random",
            nb_object = {3, 5},
        },
        trap = {
            class = "engine.generator.trap.Random",
            nb_trap = {6, 9},
        },
    },

    -- 逐層覆蓋設定
    levels = {
        [10] = {
            -- 最終層特殊設定
            generator = {
                map = {
                    class = "engine.generator.map.Static",
                    map = "zones/dungeon/boss_room",
                },
            },
        },
    },
}
```

### 7.2 資料載入檔

Zone 自動載入同目錄下的 `grids.lua`、`npcs.lua`、`objects.lua`、`traps.lua`：

```lua
-- data/zones/dungeon/grids.lua
load("/data/general/grids/basic.lua")  -- 載入全域共用地形
-- 可追加區域特有地形：
-- newEntity{ define_as = "LAVA", ... }

-- data/zones/dungeon/npcs.lua
load("/data/general/npcs/kobold.lua")  -- 載入 kobold 系列 NPC
```

### 7.3 房間模板 (`data/rooms/*.lua`)

房間模板回傳一個工廠函數，在地圖生成時被呼叫：

```lua
-- data/rooms/pilar.lua
return function(gen, id)
    local w = rng.range(7, 12)
    local h = rng.range(7, 12)
    return { name="pilar"..w.."x"..h, w=w, h=h,
        generator = function(self, x, y, is_lit)
            -- 生成房間外框（牆壁）
            for i = 1, self.w do for j = 1, self.h do
                if i == 1 or i == self.w or j == 1 or j == self.h then
                    gen.map.room_map[i-1+x][j-1+y].can_open = true
                    gen.map(i-1+x, j-1+y, Map.TERRAIN, gen.grid_list[gen:resolve('#')])
                else
                    gen.map.room_map[i-1+x][j-1+y].room = id
                    gen.map(i-1+x, j-1+y, Map.TERRAIN, gen.grid_list[gen:resolve('.')])
                end
                if is_lit then gen.map.lites(i-1+x, j-1+y, true) end
            end end

            -- 放置四根柱子
            local pilars = {{1,1},{self.w-2,1},{1,self.h-2},{self.w-2,self.h-2}}
            for _, p in ipairs(pilars) do
                gen.map(p[1]+x, p[2]+y, Map.TERRAIN, gen.grid_list[gen:resolve('#')])
            end
        end
    }
end
```

---

## 8. 實體定義模式

### 8.1 基礎定義

```lua
newEntity{
    define_as = "FLOOR",           -- 全域唯一 ID，用於 zone.lua 映射
    name = "floor",
    image = "terrain/marble_floor.png",
    display = '.',                 -- ASCII 字元表示
    color_r = 255, color_g = 255, color_b = 255,
    back_color = colors.DARK_GREY,
}
```

### 8.2 繼承（base）

```lua
-- 定義基底模板
newEntity{
    define_as = "BASE_NPC_KOBOLD",
    type = "humanoid", subtype = "kobold",
    display = "k",
    ai = "dumb_talented_simple",
    ai_state = { talent_in = 3 },
    stats = { str = 5, dex = 5, con = 5 },
}

-- 繼承基底，只覆寫差異
newEntity{ base = "BASE_NPC_KOBOLD",
    name = "kobold warrior",
    color = colors.GREEN,
    level_range = {1, 4},
    exp_worth = 1,
    rarity = 4,                    -- 生成稀有度（越大越少見）
    max_life = resolvers.rngavg(5, 9),
    combat = { dam = 2 },
}
```

### 8.3 Resolver 使用

```lua
newEntity{ base = "BASE_NPC_KOBOLD",
    name = "kobold chief",
    max_life = resolvers.rngavg(20, 30),       -- 隨機生命值
    combat = { dam = resolvers.rngrange(3, 6) }, -- 隨機攻擊力
    resolvers.equip{                              -- 隨機裝備
        {type = "weapon", subtype = "longsword"},
    },
    resolvers.talents{                            -- 學習技能
        [ActorTalents.T_KICK] = 1,
    },
    resolvers.drops{                              -- 死亡掉落
        chance = 50,
        nb = 1,
        {type = "potion"},
    },
}
```

---

## 9. 粒子特效 (`data/gfx/particles/*.lua`)

```lua
-- data/gfx/particles/acid.lua
return {
    base = 1000,                   -- 最大粒子數
    angle    = { 0, 360 },        -- 初始角度範圍
    anglev   = { 2000, 4000 },    -- 角速度
    anglea   = { 200, 600 },      -- 角加速度
    life     = { 5, 10 },         -- 粒子壽命（frame）
    size     = { 3, 6 },          -- 粒子大小
    sizev    = { 0, 0 },
    r = {0, 0}, rv = {0, 0}, ra = {0, 0},       -- 紅色通道
    g = {80, 200}, gv = {0, 10}, ga = {0, 0},   -- 綠色通道
    b = {0, 0}, bv = {0, 0}, ba = {0, 0},       -- 藍色通道
    a = {255, 255}, av = {0, 0}, aa = {0, 0},   -- 透明度
}, function(self)
    -- 發射控制函數（每幀呼叫）
    self.nb = (self.nb or 0) + 1
    if self.nb < 4 then
        self.ps:emit(100)  -- 發射 100 個粒子
    end
end
```

使用方式：`actor:addParticles(engine.Particles.new("acid", 1))`

---

## 10. 對話框

```lua
-- dialogs/DeathDialog.lua
require "engine.class"
require "engine.ui.Dialog"
local List = require "engine.ui.List"

module(..., package.seeall, class.inherit(engine.ui.Dialog))

function _M:init(actor)
    self.actor = actor
    engine.ui.Dialog.init(self, "Death!", 400, 200)

    local list = List.new{
        width = 350,
        list = {
            {name = "Resurrect", action = "resurrect"},
            {name = "Exit to menu", action = "exit"},
        },
        fct = function(item)
            if item.action == "resurrect" then
                self:resurrect()
            elseif item.action == "exit" then
                util.showMainMenu()
            end
        end,
    }

    self:loadUI{ {left = 3, top = 3, ui = list} }
    self:setupUI(true, true)
end

function _M:resurrect()
    self.actor.life = self.actor.max_life
    game:unregisterDialog(self)
end
```

---

## 11. 在地化 (`data/locales/`)

```lua
-- data/locales/ja_JP.lua
locale "ja_JP"

-- 指定來源檔案（用於管理翻譯完整性）
section "mod-example/class/Actor.lua"
t("You do not have enough power to activate %s.",
  "　%sを起動するリソースがない。",
  "logPlayer")

section "mod-example/data/damage_types.lua"
t("physical", "物理")
t("fire", "火焰")
```

啟用：在 `load.lua` 中呼叫 `I18N:loadLocale("/data/locales/ja_JP.lua")`，之後 `_t"physical"` 自動回傳翻譯。

---

## 12. Addon 開發

Addon 以 `.teaa` 壓縮包發佈，放入 `game/addons/` 目錄。

### 12.1 Addon 結構

```
my-addon.teaa (zip)
└── my-addon/
    ├── init.lua               # Addon 元資料
    ├── superload/             # 覆蓋/擴充模組檔案
    │   └── mod/
    │       └── class/
    │           └── Actor.lua  # 攔截並修改 Actor 類別
    ├── hooks/                 # Hook 註冊
    ├── data/                  # Addon 專用資料
    └── overload/              # 資源覆蓋（圖片、音效…）
```

### 12.2 Superload 機制

引擎在 `game/loader/init.lua` 註冊了自訂 `package.loaders`。當模組 `require "mod.class.Actor"` 時：

1. 先載入原始 `/mod/class/Actor.lua`
2. 依 `__addons_superload_order` 順序，檢查每個 addon 是否有 `/mod/addons/<addon>/superload/mod/class/Actor.lua`
3. 若有，執行 superload 檔案，傳入原始模組結果
4. Superload 函數可呼叫 `loadPrevious()` 取得原始模組

```lua
-- superload/mod/class/Actor.lua
local _M = loadPrevious(...)  -- 取得原始 Actor 類別

-- 保存原方法
local old_init = _M.init

-- 覆寫方法
function _M:init(t, no_default)
    old_init(self, t, no_default)
    -- 加入 addon 專用邏輯
    self.my_addon_data = {}
end

return _M
```

### 12.3 Hook 機制

Addon 可透過 hook 系統注入邏輯，而不需覆寫整個方法：

```lua
-- hooks/my_hooks.lua
class:bindHook("Actor:act", function(self, data)
    -- 在每個 Actor 行動時觸發
    if self:hasEffect(self.EFF_MY_CUSTOM_EFFECT) then
        -- 做某些事
    end
end)
```

引擎/模組端使用 `self:triggerHook{"Actor:act", ...}` 觸發所有已註冊的 hook handler。

---

## 13. 虛擬檔案系統路徑對照

| 虛擬路徑 | 實體來源 |
|----------|---------|
| `/engine/` | `game/engines/te4-1.7.6.teae` 解壓 |
| `/mod/` | `game/modules/<模組名>/` 或 `.team` 解壓 |
| `/mod/addons/<name>/` | `game/addons/<name>.teaa` 解壓 |
| `/data/` | 當前模組的 `data/` 子目錄 |
| `/save/` | 使用者存檔目錄 |
| `/settings/` | 使用者設定目錄 |

所有路徑透過 PhysFS 統一存取，不區分磁碟檔案或 zip 壓縮包。

---

## 14. 從範例模組開始

最快的開發方式：

1. 複製 `game/modules/example/` 為 `game/modules/mymod/`
2. 修改 `init.lua` 中的 `name`、`short_name`、`version`
3. 修改 `class/interface/Combat.lua` 自訂戰鬥公式
4. 在 `data/` 下新增自訂的傷害類型、技能、效果
5. 在 `data/zones/` 下設計新的區域
6. 在 `data/general/npcs/` 下定義新的怪物
7. 修改 `data/birth/descriptors.lua` 設計職業系統
8. 執行引擎，在模組選單中選擇你的模組

即時制模組只需在 `load.lua` 中加入 `core.game.setRealtime(20)`，其餘結構完全相同。
