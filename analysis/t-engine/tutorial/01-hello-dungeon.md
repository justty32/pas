# 教學 01：製作一個最簡單的地城遊戲（Hello Dungeon）

> **目標**：從零開始，建立一個可以實際執行的 TE4 遊戲模組。玩家能在隨機生成的地城中移動、攻擊科博德、使用技能，並在死亡後看到死亡畫面。
>
> **參考**：本教學直接以 `game/modules/example/` 為範本說明。

---

## 目錄

1. [TE4 模組是什麼？](#1-te4-模組是什麼)
2. [最終的檔案結構](#2-最終的檔案結構)
3. [第一步：模組入口（init.lua）](#3-第一步模組入口-initlua)
4. [第二步：系統載入（load.lua）](#4-第二步系統載入-loadlua)
5. [第三步：地形定義（grids/）](#5-第三步地形定義-grids)
6. [第四步：地區設定（zone.lua）](#6-第四步地區設定-zonelua)
7. [第五步：定義 NPC（npcs/）](#7-第五步定義-npc-npcs)
8. [第六步：定義技能（talents.lua）](#8-第六步定義技能-talentslua)
9. [第七步：定義傷害類型（damage_types.lua）](#9-第七步定義傷害類型-damage_typeslua)
10. [第八步：定義角色創建（birth/descriptors.lua）](#10-第八步定義角色創建-birthdescriptorslua)
11. [第九步：Actor 基礎類別](#11-第九步actor-基礎類別)
12. [第十步：Player 類別](#12-第十步player-類別)
13. [第十一步：NPC 類別](#13-第十一步npc-類別)
14. [第十二步：Grid 類別](#14-第十二步grid-類別)
15. [第十三步：戰鬥介面（Combat.lua）](#15-第十三步戰鬥介面-combatlua)
16. [第十四步：Game 主控制器](#16-第十四步game-主控制器)
17. [第十五步：死亡對話框](#17-第十五步死亡對話框)
18. [執行你的模組](#18-執行你的模組)
19. [常見錯誤與排解](#19-常見錯誤與排解)

---

## 1. TE4 模組是什麼？

TE4（T-Engine 4）是一個 **Lua 驅動的 Roguelike 引擎**。你的遊戲是一個「模組」（module），放在：

```
game/modules/<你的模組名稱>/
```

引擎載入時會掃描這個目錄，找到 `init.lua`，然後按照你的設定啟動遊戲。

**整體啟動流程**：

```
bootstrap/boot.lua
  → game/loader/init.lua     ← 引擎版本選擇 + Addon superload 設置
    → game/modules/<mod>/init.lua   ← 你的模組元資料
      → game/modules/<mod>/load.lua ← 定義遊戲系統
        → mod.class.Game:run()     ← 遊戲主迴圈開始
```

---

## 2. 最終的檔案結構

我們要建立的模組叫做 `hellodungeon`：

```
game/modules/hellodungeon/
│
├── init.lua                          ← 模組元資料（名稱、版本、授權）
├── load.lua                          ← 載入所有遊戲系統
│
├── class/                            ← 核心類別
│   ├── Actor.lua                     ← 所有可動實體的基底
│   ├── Player.lua                    ← 玩家（Actor 子類）
│   ├── NPC.lua                       ← AI 敵人（Actor 子類）
│   ├── Grid.lua                      ← 地形
│   ├── Game.lua                      ← 主遊戲控制器
│   └── interface/
│       └── Combat.lua                ← 戰鬥邏輯（混入）
│
├── data/                             ← 內容資料
│   ├── damage_types.lua              ← 傷害種類定義
│   ├── talents.lua                   ← 技能定義
│   ├── timed_effects.lua             ← 持續效果（狀態異常）
│   │
│   ├── birth/
│   │   └── descriptors.lua          ← 角色創建選項（職業/種族）
│   │
│   ├── general/
│   │   └── npcs/
│   │       └── kobold.lua            ← 科博德敵人
│   │
│   └── zones/
│       └── dungeon/
│           ├── zone.lua              ← 地區設定（地圖生成規則）
│           ├── grids.lua             ← 此地區使用的地形
│           └── npcs.lua              ← 此地區使用的 NPC
│
└── dialogs/
    └── DeathDialog.lua               ← 死亡畫面
```

**共 16 個檔案**。我們一個一個建立。

---

## 3. 第一步：模組入口（init.lua）

這是引擎最先讀取的檔案，告訴引擎「這個模組是什麼」：

```lua
-- game/modules/hellodungeon/init.lua

name = "Hello Dungeon"
long_name = "Hello Dungeon - My First TE4 Game"
short_name = "hellodungeon"

author = { "你的名字", "your@email.com" }
version = {1, 0, 0}

-- 指定需要的引擎版本（必須與 te4-X.Y.Z.teae 一致）
engine = {1, 7, 6, "te4"}

description = [[
我的第一個 TE4 地城探索遊戲。
探索隨機地城，擊敗科博德！
]]

-- 遊戲啟動後要執行的 Lua 路徑（對應 load.lua）
starter = "mod.load"
```

**重點說明**：

| 欄位 | 說明 |
|------|------|
| `short_name` | 小寫字母，作為存檔目錄名稱、模組 ID |
| `engine` | 版本號必須與 `game/engines/te4-X.Y.Z.teae` 一致 |
| `starter` | `"mod.load"` 對應 `load.lua`（`mod.` 前綴表示模組根目錄）|
| `show_only_on_cheat` | 設為 `true` 可隱藏，開發時很有用 |

---

## 4. 第二步：系統載入（load.lua）

`load.lua` 負責初始化所有遊戲系統（屬性、技能、AI 等），並回傳 Game 類別：

```lua
-- game/modules/hellodungeon/load.lua

local KeyBind = require "engine.KeyBind"
local DamageType = require "engine.DamageType"
local ActorStats = require "engine.interface.ActorStats"
local ActorResource = require "engine.interface.ActorResource"
local ActorTalents = require "engine.interface.ActorTalents"
local ActorAI = require "engine.interface.ActorAI"
local ActorTemporaryEffects = require "engine.interface.ActorTemporaryEffects"
local Birther = require "engine.Birther"

-- 載入預設按鍵綁定（移動、快捷鍵、背包、動作、介面、除錯）
KeyBind:load("move,hotkeys,inventory,actions,interface,debug")

-- 載入傷害類型定義
DamageType:loadDefinition("/data/damage_types.lua")

-- 載入技能定義
ActorTalents:loadDefinition("/data/talents.lua")

-- 載入持續效果（Buff/Debuff）定義
ActorTemporaryEffects:loadDefinition("/data/timed_effects.lua")

-- 定義資源池：Power（能量），用來施展技能
-- 參數：顯示名稱, 內部名稱, 最大值欄位名, 回復速度欄位名, 說明
ActorResource:defineResource(
    "Power", "power",
    nil, "power_regen",
    "能量代表你使用特殊技能的能力。"
)

-- 定義基本屬性
-- 參數：名稱, 縮寫, 預設值, 最小值, 最大值, 說明
ActorStats:defineStat("Strength",    "str", 10, 1, 100,
    "力量：影響近戰傷害與攜帶重量。")
ActorStats:defineStat("Dexterity",   "dex", 10, 1, 100,
    "敏捷：影響命中率、閃避與輕武器傷害。")
ActorStats:defineStat("Constitution","con", 10, 1, 100,
    "體質：影響最大生命值。")

-- 載入引擎內建 AI 腳本
ActorAI:loadDefinition("/engine/ai/")

-- 載入角色創建描述符（職業/種族選擇）
Birther:loadDefinition("/data/birth/descriptors.lua")

-- 最後一行：回傳 Game 類別，這是模組的遊戲入口
return { require "mod.class.Game" }
```

**注意**：
- 路徑 `/data/...` 是**虛擬路徑**，對應模組的 `data/` 目錄
- `return { require "mod.class.Game" }` 是必須的，告訴引擎要用哪個 Game 類別

---

## 5. 第三步：地形定義（grids/）

地形（Grid）是地圖的基礎元素。我們在 `data/zones/dungeon/grids.lua` 定義此地城使用的地形：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/grids.lua

-- 上一層樓梯（回到上一層）
newEntity{
    define_as = "UP",
    name = "previous level",
    display = '<', color_r=255, color_g=255, color_b=0,
    back_color = colors.DARK_GREY,
    notice = true,           -- 玩家奔跑時會注意到
    always_remember = true,  -- 即使離開 FOV 也保持記憶
    change_level = -1,       -- 往上走（-1 = 上一層）
}

-- 下一層樓梯
newEntity{
    define_as = "DOWN",
    name = "next level",
    display = '>', color_r=255, color_g=255, color_b=0,
    back_color = colors.DARK_GREY,
    notice = true,
    always_remember = true,
    change_level = 1,        -- 往下走（+1 = 下一層）
}

-- 地板
newEntity{
    define_as = "FLOOR",
    name = "floor",
    display = '.', color_r=200, color_g=200, color_b=200,
    back_color = colors.DARK_GREY,
}

-- 牆壁
newEntity{
    define_as = "WALL",
    name = "wall",
    display = '#', color_r=255, color_g=255, color_b=255,
    back_color = colors.GREY,
    always_remember = true,
    does_block_move = true,       -- 阻擋移動
    can_pass = {pass_wall=1},     -- 穿牆技能可通過
    block_sight = true,           -- 阻擋視線
    air_level = -20,              -- 此格無空氣（地下）
    dig = "FLOOR",                -- 挖掘後變成地板
}

-- 門（關閉）
newEntity{
    define_as = "DOOR",
    name = "door",
    display = '+', color_r=238, color_g=154, color_b=77,
    back_color = colors.DARK_UMBER,
    notice = true,
    always_remember = true,
    block_sight = true,
    door_opened = "DOOR_OPEN",   -- 開啟後替換為此定義
    dig = "DOOR_OPEN",
}

-- 門（開啟）
newEntity{
    define_as = "DOOR_OPEN",
    name = "open door",
    display = "'", color_r=238, color_g=154, color_b=77,
    back_color = colors.DARK_GREY,
    always_remember = true,
    door_closed = "DOOR",        -- 關閉後替換為此定義
}
```

**`define_as`** 是一個全大寫的識別符，讓你在 `zone.lua` 中用字元對應（`['.'] = "FLOOR"`）。

---

## 6. 第四步：地區設定（zone.lua）

Zone 定義了「一個地城區域」的生成規則：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/zone.lua

return {
    name = _t"古老遺跡",       -- 地區名稱（_t 包裝支援多語言）
    level_range = {1, 1},      -- 怪物等級範圍（Resolver 使用）
    max_level = 10,            -- 最多幾層
    decay = {300, 800},        -- 關卡在快取中存活的回合數範圍
    width = 50, height = 50,   -- 地圖尺寸（格）

    -- 是否在記憶體中持久保存此 zone（不是 level）
    persistent = "zone",

    -- 地圖生成設定
    generator = {
        map = {
            class = "engine.generator.map.Roomer",  -- 使用房間生成器
            nb_rooms = 10,                          -- 生成約 10 間房
            rooms = {"simple", "pilar"},            -- 使用的房間模板
            lite_room_chance = 100,                 -- 100% 房間有燈光

            -- 字元 → Grid define_as 對應
            ['.'] = "FLOOR",
            ['#'] = "WALL",
            up    = "UP",     -- 向上樓梯使用的 Grid
            down  = "DOWN",   -- 向下樓梯使用的 Grid
            door  = "DOOR",
        },
        actor = {
            class = "engine.generator.actor.Random",  -- 隨機生成 NPC
            nb_npc = {20, 30},                        -- 每層生成 20~30 個
        },
    },

    -- 逐層覆蓋設定（可選，若需要讓特定層有不同規則）
    levels = {
        -- [5] = { name = "Boss Floor" },  -- 第 5 層使用不同名稱
    },
}
```

**地圖生成器選項**（`Roomer` 的主要參數）：

| 參數 | 說明 |
|------|------|
| `nb_rooms` | 房間數量 |
| `rooms` | 使用的房間模板（`"simple"` = 矩形，`"pilar"` = 柱廊）|
| `lite_room_chance` | 房間預先點亮的機率（0~100）|
| `['.']` / `['#']` | 字元到 Grid 定義的映射 |

---

## 7. 第五步：定義 NPC（npcs/）

先建立全域 NPC 庫（`data/general/npcs/kobold.lua`），再在地區中引用它。

**全域庫（`data/general/npcs/kobold.lua`）**：

```lua
-- game/modules/hellodungeon/data/general/npcs/kobold.lua

local Talents = require("engine.interface.ActorTalents")

-- 科博德基礎定義（所有科博德的共同屬性）
newEntity{
    define_as = "BASE_NPC_KOBOLD",
    type = "humanoid", subtype = "kobold",
    display = "k", color = colors.WHITE,
    desc = _t[[醜陋的綠色小傢伙！]],

    -- AI：使用內建的 "dumb_talented_simple"
    -- talent_in=3 表示平均每 3 回合使用一次技能
    ai = "dumb_talented_simple", ai_state = { talent_in = 3 },

    stats = { str=5, dex=5, con=5 },
    combat_armor = 0,
}

-- 具體的科博德戰士（繼承自 BASE_NPC_KOBOLD）
newEntity{ base = "BASE_NPC_KOBOLD",
    name = "kobold warrior", color = colors.GREEN,
    level_range = {1, 4},
    exp_worth = 1,      -- 擊殺獲得的經驗值倍率
    rarity = 4,         -- 稀有度（越高越少見）
    max_life = resolvers.rngavg(5, 9),  -- 生命值（隨機平均）
    combat = { dam = 2 },               -- 近戰基礎傷害
}

-- 重甲科博德（較強版本，出現在更高層）
newEntity{ base = "BASE_NPC_KOBOLD",
    name = "armoured kobold", color = colors.AQUAMARINE,
    level_range = {5, 10},
    exp_worth = 1,
    rarity = 4,
    max_life = resolvers.rngavg(10, 12),
    combat_armor = 3,   -- 護甲值（減少受到的傷害）
    combat = { dam = 5 },
}
```

**地區 NPC 引用（`data/zones/dungeon/npcs.lua`）**：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/npcs.lua

-- 載入全域 NPC 定義到此地區
load("/data/general/npcs/kobold.lua")

-- 你也可以在這裡加入只有這個地區才有的 NPC
-- newEntity{ base = "BASE_NPC_KOBOLD",
--     name = "dungeon kobold champion", ...
-- }
```

**NPC 屬性速查**：

| 屬性 | 說明 |
|------|------|
| `define_as` | 唯一識別符（大寫），用於 `base` 繼承和 `guardian` 指定 |
| `base` | 繼承的基底定義（複製全部屬性後覆蓋）|
| `display` | 顯示字元（ASCII 模式）|
| `level_range` | 出現的樓層等級範圍 |
| `rarity` | 稀有度（越高越少出現）|
| `exp_worth` | 擊殺給予的經驗值係數 |
| `ai` | AI 類型（`"dumb_talented_simple"` 是最常用的基礎 AI）|
| `combat.dam` | 裸手近戰傷害 |
| `combat_armor` | 護甲值 |
| `max_life` | 最大生命值（可用 `resolvers.rngavg(min, max)` 隨機）|

---

## 8. 第六步：定義技能（talents.lua）

技能是玩家（和 NPC）可以使用的特殊能力：

```lua
-- game/modules/hellodungeon/data/talents.lua

-- 定義技能類型（用來分組顯示）
newTalentType{
    type = "role/combat",
    name = "combat",
    description = "戰鬥技巧"
}

-- 踢擊技能：將目標擊退
newTalent{
    name = "Kick",
    type = {"role/combat", 1},  -- 屬於 "role/combat" 組，第一個位置
    points = 1,                  -- 最多學習幾點
    cooldown = 6,                -- 冷卻時間（回合數）
    power = 2,                   -- 消耗的能量

    -- 目標選擇：近戰（range=1 的 hit 類型）
    -- 技能執行邏輯
    action = function(self, t)
        local tg = {type="hit", range=self:getTalentRange(t)}
        local x, y, target = self:getTarget(tg)
        if not x or not y or not target then return nil end
        -- 必須在射程內
        if core.fov.distance(self.x, self.y, x, y) > 1 then return nil end

        -- 擊退目標
        target:knockback(self.x, self.y, 2 + self:getDex())
        return true  -- 必須回傳 true 才會消耗能量和觸發冷卻
    end,

    -- 技能說明（顯示在 Tooltip 中）
    info = function(self, t)
        return ("踢開目標，將其擊退 %d 格。"):format(2 + self:getDex())
    end,
}

-- 酸液噴射技能：範圍傷害
newTalent{
    name = "Acid Spray",
    type = {"role/combat", 1},
    points = 1,
    cooldown = 6,
    power = 2,
    range = 6,

    action = function(self, t)
        -- ball 類型：以目標點為中心的圓形範圍
        local tg = {type="ball", range=self:getTalentRange(t), radius=1, talent=t}
        local x, y = self:getTarget(tg)
        if not x or not y then return nil end

        -- 對範圍內所有實體造成 ACID 傷害
        self:project(tg, x, y, DamageType.ACID, 1 + self:getDex(), {type="acid"})
        return true
    end,

    info = function(self, t)
        return ("向目標噴射酸液，造成 %d 點酸液傷害。"):format(1 + self:getDex())
    end,
}
```

**技能定義速查**：

| 欄位 | 說明 |
|------|------|
| `type` | `{技能組名, 需求等級}` |
| `mode` | `"activated"`（主動，預設）/ `"sustained"`（持續）/ `"passive"`（被動）|
| `cooldown` | 冷卻回合數 |
| `power` | 消耗的 Power 資源 |
| `range` | 使用距離 |
| `action(self, t)` | 技能執行（回傳 `true` = 成功消耗能量）|
| `info(self, t)` | 技能說明文字（支援動態計算）|

**投射形狀（`tg.type`）**：

| 形狀 | 說明 |
|------|------|
| `"hit"` | 單一目標（近戰/遠程）|
| `"ball"` | 圓形範圍（需要 `radius`）|
| `"beam"` | 直線穿透 |
| `"cone"` | 扇形（需要 `cone_angle`）|
| `"bolt"` | 直線彈道（不穿透）|

---

## 9. 第七步：定義傷害類型（damage_types.lua）

```lua
-- game/modules/hellodungeon/data/damage_types.lua

-- 物理傷害（預設就有，但需要在這裡定義才能使用）
newDamageType{
    name = "physical", type = "PHYSICAL",
    projector = function(src, x, y, type, dam)
        local target = game.level.map(x, y, Map.ACTOR)
        if target then
            -- 直接造成物理傷害
            target:takeHit(dam, src)
            game.logSeen(target, "%s takes %d physical damage!", target.name:capitalize(), dam)
        end
    end,
}

-- 酸液傷害
newDamageType{
    name = "acid", type = "ACID",
    projector = function(src, x, y, type, dam)
        local target = game.level.map(x, y, Map.ACTOR)
        if target then
            target:takeHit(dam, src)
            game.logSeen(target, "%s is burned by acid for %d damage!", target.name:capitalize(), dam)
            -- 施加持續效果（燃燒）
            if not target:attr("acid_immune") then
                target:setEffect(target.EFF_ACIDBURN, 3, {power=dam/3, src=src})
            end
        end
    end,
}
```

---

## 10. 第八步：定義角色創建（birth/descriptors.lua）

`Birther` 是 TE4 的角色創建流程。你需要定義描述符（職業/種族）讓玩家選擇：

```lua
-- game/modules/hellodungeon/data/birth/descriptors.lua

-- 基礎描述符：所有角色共有的基本屬性
newBirthDescriptor{
    type = "base",
    name = "base",
    desc = {},              -- 說明文字（顯示在角色創建畫面）
    experience = 1.0,       -- 經驗值倍率

    -- 直接複製這些屬性到玩家身上
    copy = {
        max_level = 10,
        lite = 4,           -- 照明範圍（格）
        max_life = 25,
    },
}

-- 職業選項 1：破壞者（近戰）
newBirthDescriptor{
    type = "role",
    name = "Destroyer",
    desc = {
        "以蠻力席捲一切！",
        "起始技能：踢擊",
    },
    -- 出生時學習的技能
    talents = {
        [ActorTalents.T_KICK] = 1,
    },
    -- 直接複製到角色的屬性
    copy = {
        stats = {str=14, dex=8, con=12},
    },
}

-- 職業選項 2：酸液狂（法術）
newBirthDescriptor{
    type = "role",
    name = "Acid-maniac",
    desc = {
        "以酸液溶解一切！",
        "起始技能：酸液噴射",
    },
    talents = {
        [ActorTalents.T_ACID_SPRAY] = 1,
    },
    copy = {
        stats = {str=8, dex=14, con=10},
    },
}
```

**角色創建流程**：引擎自動生成選擇畫面，玩家依序從各 `type` 中選一個描述符，最後合併所有 `copy` 和 `talents`。

在 `Game.lua` 中啟動 Birther 時，指定需要選擇哪些 `type`：

```lua
-- 讓玩家依序選擇 "base" 和 "role" 兩個描述符
Birther.new(nil, self.player, {"base", "role"}, function()
    -- 角色創建完成後的回呼
    self:changeLevel(1, "dungeon")
end)
```

---

## 11. 第九步：Actor 基礎類別

`Actor` 是所有可動實體（玩家、NPC）的基底類別：

```lua
-- game/modules/hellodungeon/class/Actor.lua

require "engine.class"
require "engine.Actor"
require "engine.interface.ActorTemporaryEffects"
require "engine.interface.ActorLife"
require "engine.interface.ActorProject"
require "engine.interface.ActorLevel"
require "engine.interface.ActorStats"
require "engine.interface.ActorTalents"
require "engine.interface.ActorResource"
require "engine.interface.ActorFOV"
require "mod.class.interface.Combat"     -- 你自己的戰鬥介面

local Map = require "engine.Map"

-- 繼承引擎 Actor 和所有需要的介面混入
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
    -- 基礎戰鬥屬性
    self.combat_armor = 0

    -- 預設資源回復速度
    t.power_regen = t.power_regen or 1       -- 每回合回復 1 點 Power
    t.life_regen = t.life_regen or 0.25      -- 生命回復很慢

    -- 裸手近戰傷害
    self.combat = { dam = 1 }

    -- 依次呼叫所有繼承介面的 init
    engine.Actor.init(self, t, no_default)
    engine.interface.ActorTemporaryEffects.init(self, t)
    engine.interface.ActorLife.init(self, t)
    engine.interface.ActorProject.init(self, t)
    engine.interface.ActorTalents.init(self, t)
    engine.interface.ActorResource.init(self, t)
    engine.interface.ActorStats.init(self, t)
    engine.interface.ActorLevel.init(self, t)
    engine.interface.ActorFOV.init(self, t)
end

-- 每個 Actor 每「回合」呼叫一次（當其能量值足夠時）
function _M:act()
    if not engine.Actor.act(self) then return end

    self.changed = true   -- 標記需要重繪

    -- 每回合進行：技能冷卻 → 資源回復 → 持續效果
    self:cooldownTalents()
    self:regenLife()
    self:regenResources()
    self:timedEffects()

    -- 如果能量不夠了，停止行動
    if self.energy.value < game.energy_to_act then return false end

    return true
end

-- 移動（帶能量消耗）
function _M:move(x, y, force)
    local moved = false
    local ox, oy = self.x, self.y
    if force or self:enoughEnergy() then
        moved = engine.Actor.move(self, x, y, force)
        -- 非強制移動且真的移動了，才消耗能量
        if not force and moved and (self.x ~= ox or self.y ~= oy) and not self.did_energy then
            self:useEnergy()
        end
    end
    self.did_energy = nil
    return moved
end

-- 滑鼠 Tooltip 顯示
function _M:tooltip()
    return ([[%s%s
#00ffff#等級: %d
#ff0000#HP: %d (%d%%)
屬性: STR%d / DEX%d / CON%d]]):format(
        self:getDisplayString(),
        self.name,
        self.level,
        self.life, self.life * 100 / self.max_life,
        self:getStr(), self:getDex(), self:getCon()
    )
end

-- 受傷時呼叫（可在這裡添加防禦計算）
function _M:onTakeHit(value, src)
    return value  -- 回傳實際受到的傷害
end

-- 死亡
function _M:die(src)
    engine.interface.ActorLife.die(self, src)
    -- 給殺手經驗值
    if src and src.gainExp then
        src:gainExp(self:worthExp(src))
    end
    return true
end

-- 升級時呼叫
function _M:levelup()
    self.max_life = self.max_life + 2
    self:incMaxPower(3)
    self.life = self.max_life
    self.power = self.max_power
end

-- 屬性變化時呼叫
function _M:onStatChange(stat, v)
    if stat == self.STAT_CON then
        self.max_life = self.max_life + 2
    end
end

-- 碰撞攻擊
function _M:attack(target)
    self:bumpInto(target)
end

-- 技能使用前的檢查（能量、資源）
function _M:preUseTalent(ab, silent)
    if not self:enoughEnergy() then return false end

    if ab.mode == "sustained" then
        if ab.sustain_power and self.max_power < ab.sustain_power
                and not self:isTalentActive(ab.id) then
            game.logPlayer(self, "你沒有足夠的能量來啟動 %s。", ab.name)
            return false
        end
    else
        if ab.power and self:getPower() < ab.power then
            game.logPlayer(self, "你沒有足夠的能量來使用 %s。", ab.name)
            return false
        end
    end

    if not silent then
        if ab.mode == "sustained" and not self:isTalentActive(ab.id) then
            game.logSeen(self, "%s 啟動了 %s。", self.name:capitalize(), ab.name)
        elseif ab.mode == "sustained" and self:isTalentActive(ab.id) then
            game.logSeen(self, "%s 停用了 %s。", self.name:capitalize(), ab.name)
        else
            game.logSeen(self, "%s 使用了 %s。", self.name:capitalize(), ab.name)
        end
    end
    return true
end

-- 技能使用後的處理（消耗資源、觸發冷卻）
function _M:postUseTalent(ab, ret)
    if not ret then return end

    self:useEnergy()  -- 消耗行動能量

    if ab.mode == "sustained" then
        if not self:isTalentActive(ab.id) then
            if ab.sustain_power then self.max_power = self.max_power - ab.sustain_power end
        else
            if ab.sustain_power then self.max_power = self.max_power + ab.sustain_power end
        end
    else
        if ab.power then self:incPower(-ab.power) end
    end

    return true
end

-- 能夠看見目標嗎？（處理隱身等效果）
function _M:canSee(actor, def, def_pct)
    if not actor then return false, 0 end

    if actor:attr("stealth") and actor ~= self then
        local hit, chance = self:checkHit(
            self.level / 2 + self:getCun(25),
            actor:attr("stealth") + (actor:attr("inc_stealth") or 0),
            0, 100)
        if not hit then return false, chance end
    end

    if def ~= nil then return def, def_pct
    else return true, 100
    end
end

-- 能否被施加特定效果？
function _M:canBe(what)
    if what == "poison"    and rng.percent(100 * (self:attr("poison_immune") or 0))    then return false end
    if what == "confusion" and rng.percent(100 * (self:attr("confusion_immune") or 0)) then return false end
    if what == "blind"     and rng.percent(100 * (self:attr("blind_immune") or 0))     then return false end
    if what == "stun"      and rng.percent(100 * (self:attr("stun_immune") or 0))      then return false end
    return true
end

-- 此 Actor 值多少經驗值
function _M:worthExp(target)
    if not target.level or self.level < target.level - 3 then return 0 end
    local mult = 2
    if self.unique then mult = 6
    elseif self.egoed then mult = 3 end
    return self.level * mult * self.exp_worth
end
```

---

## 12. 第十步：Player 類別

`Player` 繼承 `Actor`，加上玩家特有的輸入處理與介面：

```lua
-- game/modules/hellodungeon/class/Player.lua

require "engine.class"
require "mod.class.Actor"
require "engine.interface.PlayerRest"    -- 自動休息
require "engine.interface.PlayerRun"     -- 自動奔跑
require "engine.interface.PlayerMouse"   -- 滑鼠移動
require "engine.interface.PlayerHotkeys" -- 快捷鍵系統

local Map = require "engine.Map"
local DeathDialog = require "mod.dialogs.DeathDialog"

module(..., package.seeall, class.inherit(
    mod.class.Actor,
    engine.interface.PlayerRest,
    engine.interface.PlayerRun,
    engine.interface.PlayerMouse,
    engine.interface.PlayerHotkeys
))

function _M:init(t, no_default)
    -- 玩家固定顯示為 '@'，白色
    t.display = t.display or '@'
    t.color_r  = t.color_r  or 230
    t.color_g  = t.color_g  or 230
    t.color_b  = t.color_b  or 230

    t.player   = true        -- 標記為玩家
    t.type     = "humanoid"
    t.subtype  = "player"
    t.faction  = "players"   -- 陣營名稱
    t.lite     = t.lite or 0 -- 燈光範圍（載入時設定）

    mod.class.Actor.init(self, t, no_default)
    engine.interface.PlayerHotkeys.init(self, t)

    self.descriptor = {}  -- 角色創建的描述符記錄
end

-- 移動時讓視角跟著玩家
function _M:move(x, y, force)
    local moved = mod.class.Actor.move(self, x, y, force)
    if moved then
        game.level.map:moveViewSurround(self.x, self.y, 8, 8)
    end
    return moved
end

-- 玩家每回合行動
function _M:act()
    if not mod.class.Actor.act(self) then return end

    -- 清空閃光訊息
    game.flash:empty()

    -- 執行自動休息/奔跑，若都沒有則暫停等待輸入
    if not self:restStep() and not self:runStep() and self.player then
        game.paused = true
    end
end

-- 消耗能量時，解除暫停（讓其他 Actor 繼續行動）
function _M:useEnergy(val)
    mod.class.Actor.useEnergy(self, val)
    if self.player and self.energy.value < game.energy_to_act then
        game.paused = false
    end
end

-- 計算玩家視野（FOV）
local fovdist = {}
for i = 0, 30 * 30 do
    fovdist[i] = math.max((20 - math.sqrt(i)) / 14, 0.6)
end

function _M:playerFOV()
    game.level.map:cleanFOV()
    -- 正常視野（受地形阻擋）
    self:computeFOV(self.sight or 20, "block_sight", function(x, y, dx, dy, sqdist)
        game.level.map:apply(x, y, fovdist[sqdist])
    end, true, false, true)
    -- 燈光範圍（無視黑暗但受牆壁阻擋）
    self:computeFOV(self.lite, "block_sight", function(x, y, dx, dy, sqdist)
        game.level.map:applyLite(x, y)
    end, true, true, true)
end

-- 受傷時停止休息/奔跑
function _M:onTakeHit(value, src)
    self:runStop(_t"受到傷害")
    self:restStop(_t"受到傷害")
    local ret = mod.class.Actor.onTakeHit(self, value, src)
    -- 血量低於 30% 時顯示警告飄字
    if self.life < self.max_life * 0.3 then
        local sx, sy = game.level.map:getTileToScreen(self.x, self.y)
        game.flyers:add(sx, sy, 30, 0, 2, _t"血量危險！", {255, 0, 0}, true)
    end
    return ret
end

-- 玩家死亡
function _M:die(src)
    if self.game_ender then
        engine.interface.ActorLife.die(self, src)
        game.paused = true
        self.energy.value = game.energy_to_act
        game:registerDialog(DeathDialog.new(self))  -- 顯示死亡對話框
    else
        mod.class.Actor.die(self, src)
    end
end

-- 設定角色名稱（同時設定存檔名稱）
function _M:setName(name)
    self.name = name
    game.save_name = name
end

-- 升級飄字
function _M:levelup()
    mod.class.Actor.levelup(self)
    local x, y = game.level.map:getTileToScreen(self.x, self.y)
    game.flyers:add(x, y, 80, 0.5, -2, _t"升級了！", {0, 255, 255})
    game.log("#00ffff#歡迎來到第 %d 等級！", self.level)
end

-- 取得目標（委派給 Game 的瞄準系統）
function _M:getTarget(typ)
    return game:targetGetForPlayer(typ)
end

function _M:setTarget(target)
    return game:targetSetForPlayer(target)
end

-- 休息條件：無敵人且資源未滿
function _M:restCheck()
    -- 先檢查是否有敵人在視野內
    local seen = false
    core.fov.calc_circle(self.x, self.y, game.level.map.w, game.level.map.h, 20,
        function(_, x, y) return game.level.map:opaque(x, y) end,
        function(_, x, y)
            local actor = game.level.map(x, y, game.level.map.ACTOR)
            if actor and self:reactionToward(actor) < 0
               and self:canSee(actor) and game.level.map.seens(x, y) then
                seen = true
            end
        end, nil)
    if seen then return false, "發現敵人" end

    -- 檢查是否需要回復
    if self:getPower() < self:getMaxPower() and self.power_regen > 0 then return true end
    if self.life < self.max_life and self.life_regen > 0 then return true end

    return false, "所有資源已滿"
end

-- 奔跑條件：無敵人且無有趣地形
function _M:runCheck()
    local seen = false
    core.fov.calc_circle(self.x, self.y, game.level.map.w, game.level.map.h, 20,
        function(_, x, y) return game.level.map:opaque(x, y) end,
        function(_, x, y)
            local actor = game.level.map(x, y, game.level.map.ACTOR)
            if actor and self:reactionToward(actor) < 0
               and self:canSee(actor) and game.level.map.seens(x, y) then
                seen = true
            end
        end, nil)
    if seen then return false, "發現敵人" end

    local noticed = false
    self:runScan(function(x, y)
        local grid = game.level.map(x, y, Map.TERRAIN)
        if grid and grid.notice then noticed = "有趣地形" end
    end)
    if noticed then return false, noticed end

    self:playerFOV()
    return engine.interface.PlayerRun.runCheck(self)
end
```

---

## 13. 第十一步：NPC 類別

NPC 繼承 `Actor`，加上 AI 決策：

```lua
-- game/modules/hellodungeon/class/NPC.lua

require "engine.class"
local ActorAI = require "engine.interface.ActorAI"
require "mod.class.Actor"

module(..., package.seeall, class.inherit(mod.class.Actor, engine.interface.ActorAI))

function _M:init(t, no_default)
    mod.class.Actor.init(self, t, no_default)
    ActorAI.init(self, t)
end

-- NPC 每回合行動
function _M:act()
    if not mod.class.Actor.act(self) then return end

    -- 計算 FOV（NPC 需要知道能看到什麼）
    self:computeFOV(self.sight or 20)

    -- 讓 AI 做決策
    self:doAI()

    -- 若 AI 沒有消耗能量，自動消耗（避免卡住）
    if not self.energy.used then self:useEnergy() end
end

-- 受傷時自動鎖定攻擊者
function _M:onTakeHit(value, src)
    if not self.ai_target.actor and src.targetable then
        self.ai_target.actor = src
    end
    return mod.class.Actor.onTakeHit(self, value, src)
end

-- NPC Tooltip（顯示 AI 目標）
function _M:tooltip()
    return mod.class.Actor.tooltip(self) ..
        ("\n目標: %s\nUID: %d"):format(
            self.ai_target.actor and self.ai_target.actor.name or "無",
            self.uid)
end
```

---

## 14. 第十二步：Grid 類別

Grid 通常不需要大幅修改，繼承引擎 Grid 就足夠了：

```lua
-- game/modules/hellodungeon/class/Grid.lua

require "engine.class"
require "engine.Grid"

module(..., package.seeall, class.inherit(engine.Grid))

-- 可以在這裡覆寫 block_move 等行為
-- 例如讓門可以被玩家開啟（引擎 Grid 已內建此邏輯）
```

---

## 15. 第十三步：戰鬥介面（Combat.lua）

戰鬥邏輯作為「混入」（mixin）：

```lua
-- game/modules/hellodungeon/class/interface/Combat.lua

require "engine.class"
local DamageType = require "engine.DamageType"
local Map = require "engine.Map"

-- 使用 class.make 建立一個純混入（不繼承任何基底）
module(..., package.seeall, class.make)

-- 碰撞處理：根據陣營關係決定攻擊還是交換位置
function _M:bumpInto(target)
    local reaction = self:reactionToward(target)
    if reaction < 0 then
        -- 敵人：攻擊
        return self:attackTarget(target)
    elseif reaction >= 0 then
        -- 友善：嘗試交換位置
        if self.move_others then
            game.level.map:remove(self.x, self.y, Map.ACTOR)
            game.level.map:remove(target.x, target.y, Map.ACTOR)
            game.level.map(self.x, self.y, Map.ACTOR, target)
            game.level.map(target.x, target.y, Map.ACTOR, self)
            self.x, self.y, target.x, target.y = target.x, target.y, self.x, self.y
        end
    end
end

-- 簡單的攻擊邏輯：力量 + 武器傷害 - 護甲
function _M:attackTarget(target, mult)
    if self.combat then
        local dam = (self.combat.dam or 0) + self:getStr() - target.combat_armor
        DamageType:get(DamageType.PHYSICAL).projector(
            self, target.x, target.y,
            DamageType.PHYSICAL,
            math.max(0, dam)
        )
    end
    self:useEnergy(game.energy_to_act)
end
```

---

## 16. 第十四步：Game 主控制器

`Game.lua` 是最複雜的部分，控制整個遊戲迴圈：

```lua
-- game/modules/hellodungeon/class/Game.lua

require "engine.class"
require "engine.GameTurnBased"
require "engine.interface.GameTargeting"
require "engine.KeyBind"

local Savefile  = require "engine.Savefile"
local DamageType = require "engine.DamageType"
local Zone      = require "engine.Zone"
local Map       = require "engine.Map"
local Level     = require "engine.Level"
local Birther   = require "engine.Birther"

-- 你的自訂類別
local Grid      = require "mod.class.Grid"
local Actor     = require "mod.class.Actor"
local Player    = require "mod.class.Player"
local NPC       = require "mod.class.NPC"

-- UI 元件
local HotkeysDisplay  = require "engine.HotkeysDisplay"
local ActorsSeenDisplay = require "engine.ActorsSeenDisplay"
local LogDisplay      = require "engine.LogDisplay"
local LogFlasher      = require "engine.LogFlasher"
local DebugConsole    = require "engine.DebugConsole"
local FlyingText      = require "engine.FlyingText"
local Tooltip         = require "engine.Tooltip"
local QuitDialog      = require "engine.dialogs.GameMenu"

-- 繼承回合制遊戲 + 瞄準系統
module(..., package.seeall, class.inherit(
    engine.GameTurnBased,
    engine.interface.GameTargeting
))

-- 初始化（首次載入）
function _M:init()
    -- 初始化回合制引擎
    -- 參數：KeyBind, 能量上限, 每回合獲得的能量
    engine.GameTurnBased.init(self, engine.KeyBind.new(), 1000, 100)

    self.paused = true  -- 從暫停狀態開始
    self:loaded()       -- 執行載入後的初始化
end

-- 遊戲啟動
function _M:run()
    -- 建立 UI 元件
    -- LogFlasher：頂部閃光訊息
    self.flash = LogFlasher.new(0, 0, self.w, 20, nil, nil, nil, {255,255,255}, {0,0,0})
    -- LogDisplay：底部訊息日誌
    self.logdisplay = LogDisplay.new(
        0, self.h * 0.8,
        self.w * 0.5, self.h * 0.2,
        nil, nil, nil, {255,255,255}, {30,30,30}
    )
    -- HotkeysDisplay：快捷鍵列
    self.hotkeys_display = HotkeysDisplay.new(
        nil, self.w * 0.5, self.h * 0.8,
        self.w * 0.5, self.h * 0.2, {30,30,0}
    )
    -- ActorsSeenDisplay：視野內的 Actor 列表
    self.npcs_display = ActorsSeenDisplay.new(
        nil, self.w * 0.5, self.h * 0.8,
        self.w * 0.5, self.h * 0.2, {30,30,0}
    )
    self.tooltip = Tooltip.new(nil, nil, {255,255,255}, {30,30,30})
    self.flyers = FlyingText.new()
    self:setFlyingText(self.flyers)

    -- 建立便捷的 log 函數
    self.log = function(style, ...)
        if type(style) == "number" then
            self.logdisplay(...)
            self.flash(style, ...)
        else
            self.logdisplay(style, ...)
            self.flash(self.flash.NEUTRAL, style, ...)
        end
    end
    self.logSeen = function(e, style, ...)
        if e and self.level.map.seens(e.x, e.y) then self.log(style, ...) end
    end
    self.logPlayer = function(e, style, ...)
        if e == self.player then self.log(style, ...) end
    end

    self.log(self.flash.GOOD, "歡迎來到 #00FF00#Hello Dungeon！")

    -- 設定輸入
    self:setupCommands()
    self:setupMouse()

    -- 若無存檔，開始新遊戲
    if not self.player then self:newGame() end

    self.hotkeys_display.actor = self.player
    self.npcs_display.actor = self.player

    -- 啟動瞄準系統
    engine.interface.GameTargeting.init(self)

    -- 啟動遊戲引擎
    self:setCurrent()

    if self.level then self:setupDisplayMode() end
end

-- 新遊戲
function _M:newGame()
    self.player = Player.new{name=self.player_name, game_ender=true}
    Map:setViewerActor(self.player)
    self:setupDisplayMode()

    -- 開啟角色創建畫面
    self.creating_player = true
    local birth = Birther.new(nil, self.player, {"base", "role"}, function()
        -- 創建完成後：進入第 1 層
        self:changeLevel(1, "dungeon")
        self.player:resolve()       -- 解析所有 resolver（隨機屬性等）
        self.player:resolve(nil, true)
        self.player.energy.value = self.energy_to_act
        self.paused = true
        self.creating_player = false
    end)
    self:registerDialog(birth)
end

-- 從存檔載入後的初始化
function _M:loaded()
    engine.GameTurnBased.loaded(self)
    -- 告訴 Zone 使用哪些類別
    Zone:setup{
        npc_class  = "mod.class.NPC",
        grid_class = "mod.class.Grid",
    }
    Map:setViewerActor(self.player)
    -- 設定視口（地圖顯示區域）
    -- 參數：x, y, 寬, 高, 磁磚寬, 磁磚高, 字型, 視野距離, 使用背景色
    Map:setViewPort(200, 20, self.w - 200, math.floor(self.h * 0.80) - 20, 32, 32, nil, 22, true)
    self.key = engine.KeyBind.new()
end

-- 設定顯示模式
function _M:setupDisplayMode()
    Map:setViewPort(200, 20, self.w - 200, math.floor(self.h * 0.80) - 20, 32, 32, nil, 22, true)
    Map:resetTiles()
    Map.tiles.use_images = false  -- false = ASCII 模式，true = 圖片模式

    if self.level then
        self.level.map:recreate()
        engine.interface.GameTargeting.init(self)
        self.level.map:moveViewSurround(self.player.x, self.player.y, 8, 8)
    end
end

-- 儲存遊戲
function _M:save()
    return class.save(self, self:defaultSavedFields{}, true)
end

-- 存檔描述（顯示在存檔選擇畫面）
function _M:getSaveDescription()
    return {
        name = self.player.name,
        description = ("[Level %d of %s]"):format(self.level.level, self.zone.name),
    }
end

-- 離開關卡時保存玩家位置
function _M:leaveLevel(level, lev, old_lev)
    if level:hasEntity(self.player) then
        level.exited = level.exited or {}
        if lev > old_lev then
            level.exited.down = {x=self.player.x, y=self.player.y}
        else
            level.exited.up = {x=self.player.x, y=self.player.y}
        end
        level.last_turn = game.turn
        level:removeEntity(self.player)
    end
end

-- 換層/換地區
function _M:changeLevel(lev, zone)
    local old_lev = (self.level and not zone) and self.level.level or -1000
    if zone then
        if self.zone then
            self.zone:leaveLevel(false, lev, old_lev)
            self.zone:leave()
        end
        self.zone = Zone.new(zone)  -- 載入地區（對應 data/zones/<zone>/zone.lua）
    end
    self.zone:getLevel(self, lev, old_lev)

    -- 根據移動方向放置玩家在對應的樓梯旁
    if lev > old_lev then
        self.player:move(self.level.default_up.x, self.level.default_up.y, true)
    else
        self.player:move(self.level.default_down.x, self.level.default_down.y, true)
    end
    self.level:addEntity(self.player)
end

function _M:getPlayer() return self.player end

function _M:isLoadable()
    return not self:getPlayer(true).dead
end

-- 遊戲 tick（核心迴圈）
function _M:tick()
    if self.level then
        self:targetOnTick()
        engine.GameTurnBased.tick(self)
    end
    -- 暫停時回傳 true（等待玩家輸入）
    if self.paused and not savefile_pipe.saving then return true end
end

-- 每回合回呼
function _M:onTurn()
    if self.turn % 10 ~= 0 then return end
    self.level.map:processEffects()
end

-- 每幀渲染
function _M:display(nb_keyframe)
    if self.change_res_dialog then
        engine.GameTurnBased.display(self, nb_keyframe)
        return
    end

    if self.level and self.level.map and self.level.map.finished then
        -- 重計 FOV
        if self.level.map.changed then
            self.player:playerFOV()
        end

        -- 繪製地圖
        self.level.map:display(nil, nil, nb_keyframe)

        -- 繪製瞄準游標
        self.target:display()

        -- 繪製小地圖（右上角）
        self.level.map:minimapDisplay(
            self.w - 200, 20,
            util.bound(self.player.x - 25, 0, self.level.map.w - 50),
            util.bound(self.player.y - 25, 0, self.level.map.h - 50),
            50, 50, 0.6)
    end

    -- 繪製 UI
    self.flash:toScreen(nb_keyframe)
    self.logdisplay:toScreen()
    if self.show_npc_list then
        self.npcs_display:toScreen()
    else
        self.hotkeys_display:toScreen()
    end
    if self.player then self.player.changed = false end

    self:targetDisplayTooltip()
    engine.GameTurnBased.display(self, nb_keyframe)
end

-- 設定鍵盤輸入
function _M:setupCommands()
    self.normal_key = self.key
    self:targetSetupKey()
    self.key:unicodeInput(true)

    self.key:addBinds{
        -- 移動（方向鍵 / 小鍵盤）
        MOVE_LEFT      = function() self.player:moveDir(4) end,
        MOVE_RIGHT     = function() self.player:moveDir(6) end,
        MOVE_UP        = function() self.player:moveDir(8) end,
        MOVE_DOWN      = function() self.player:moveDir(2) end,
        MOVE_LEFT_UP   = function() self.player:moveDir(7) end,
        MOVE_LEFT_DOWN = function() self.player:moveDir(1) end,
        MOVE_RIGHT_UP  = function() self.player:moveDir(9) end,
        MOVE_RIGHT_DOWN= function() self.player:moveDir(3) end,
        MOVE_STAY      = function() self.player:useEnergy() end,  -- 等待一回合

        -- 奔跑（Shift + 方向）
        RUN_LEFT       = function() self.player:runInit(4) end,
        RUN_RIGHT      = function() self.player:runInit(6) end,
        RUN_UP         = function() self.player:runInit(8) end,
        RUN_DOWN       = function() self.player:runInit(2) end,

        -- 快捷鍵（1~12）
        HOTKEY_1  = function() self.player:activateHotkey(1) end,
        HOTKEY_2  = function() self.player:activateHotkey(2) end,
        HOTKEY_3  = function() self.player:activateHotkey(3) end,
        HOTKEY_4  = function() self.player:activateHotkey(4) end,
        HOTKEY_5  = function() self.player:activateHotkey(5) end,
        HOTKEY_6  = function() self.player:activateHotkey(6) end,
        HOTKEY_7  = function() self.player:activateHotkey(7) end,
        HOTKEY_8  = function() self.player:activateHotkey(8) end,
        HOTKEY_9  = function() self.player:activateHotkey(9) end,
        HOTKEY_10 = function() self.player:activateHotkey(10) end,
        HOTKEY_11 = function() self.player:activateHotkey(11) end,
        HOTKEY_12 = function() self.player:activateHotkey(12) end,

        -- 換層（站在樓梯上按 >/<）
        CHANGE_LEVEL = function()
            local e = self.level.map(self.player.x, self.player.y, Map.TERRAIN)
            if self.player:enoughEnergy() and e.change_level then
                self:changeLevel(
                    e.change_zone and e.change_level or self.level.level + e.change_level,
                    e.change_zone)
            else
                self.log("這裡沒有出口。")
            end
        end,

        -- 休息（等待直到資源回滿）
        REST = function() self.player:restInit() end,

        -- 使用技能
        USE_TALENTS = function() self.player:useTalents() end,

        -- 存檔
        SAVE_GAME = function() self:saveGame() end,

        -- 離開（ESC）
        QUIT_GAME = function() self:onQuit() end,

        -- 截圖
        SCREENSHOT = function() self:saveScreenshot() end,

        -- 遊戲選單
        EXIT = function()
            local menu = require("engine.dialogs.GameMenu").new{
                "resume", "keybinds", "video", "save", "quit"
            }
            self:registerDialog(menu)
        end,

        -- Lua 除錯主控台（開發用）
        LUA_CONSOLE = function()
            self:registerDialog(DebugConsole.new())
        end,

        -- 切換 NPC 列表
        TOGGLE_NPC_LIST = function()
            self.show_npc_list = not self.show_npc_list
            self.player.changed = true
        end,
    }
    self.key:setCurrent()
end

-- 設定滑鼠輸入
function _M:setupMouse(reset)
    if reset then self.mouse:reset() end
    self.mouse:registerZone(
        Map.display_x, Map.display_y,
        Map.viewport.width, Map.viewport.height,
        function(button, mx, my, xrel, yrel, bx, by, event)
            if self:targetMouse(button, mx, my, xrel, yrel, event) then return end
            self.player:mouseHandleDefault(self.key, self.key == self.normal_key,
                button, mx, my, xrel, yrel, event)
        end)
    self.mouse:registerZone(
        self.logdisplay.display_x, self.logdisplay.display_y,
        self.w, self.h,
        function(button)
            if button == "wheelup"   then self.logdisplay:scrollUp(1) end
            if button == "wheeldown" then self.logdisplay:scrollUp(-1) end
        end, {button=true})
    self.mouse:setCurrent()
end

-- 離開遊戲確認
function _M:onQuit()
    self.player:restStop()
    if not self.quit_dialog then
        self.quit_dialog = require("engine.dialogs.GameMenu").new{
            "resume", "save", "quit"
        }
        self:registerDialog(self.quit_dialog)
    end
end

-- 存檔（將自身推入存檔管線）
function _M:saveGame()
    savefile_pipe:push(self.save_name, "game", self)
    self.log("儲存遊戲中...")
end
```

---

## 17. 第十五步：死亡對話框

```lua
-- game/modules/hellodungeon/dialogs/DeathDialog.lua

require "engine.class"
local Dialog = require "engine.Dialog"
local Map = require "engine.Map"

module(..., package.seeall, class.inherit(Dialog))

function _M:init(actor)
    Dialog.init(self, "你死了！", 400, 200)
    self.actor = actor

    self:addText(("你在第 %d 層倒下了。"):format(game.level.level), "red")
    self:addText(" ")
    self:addButton("重試（返回主選單）", function()
        self:unregisterDialog(self)
        -- 刪除存檔並返回主選單
        game:setPlayerDead()
    end)
end
```

**或者使用最簡單版本**（直接讓玩家重新開始）：

```lua
-- 最簡版死亡對話框
require "engine.class"
local Dialog = require "engine.Dialog"
module(..., package.seeall, class.inherit(Dialog))

function _M:init(actor)
    Dialog.init(self, _t"死亡", 400, 150)
    self:addText(_t"你已死亡，遊戲結束。")
    self:addButton(_t"確認", function()
        game:setPlayerDead()  -- 引擎的標準死亡處理
        self:unregisterDialog(self)
    end)
end
```

---

## 18. 執行你的模組

### 放置模組

將整個 `hellodungeon/` 目錄放到：

```
game/modules/hellodungeon/
```

### 執行引擎

```bash
# 先生成構建檔案
cd /path/to/t-engine4-src-1.7.6
premake4 gmake

# 編譯
make -C build

# 執行（Debug 版本）
./bin/Debug/t-engine
```

### 讓模組在清單中顯示

`init.lua` 預設沒有 `show_only_on_cheat`，所以會直接顯示在遊戲選擇畫面。

如果設定了 `show_only_on_cheat = true`，需要在設定中開啟 Cheat 模式，或直接移除這行。

---

## 19. 常見錯誤與排解

### 錯誤：模組不出現在清單中

- 檢查 `init.lua` 的 `engine` 版本是否與 `game/engines/te4-X.Y.Z.teae` 一致
- 確認 `short_name` 只包含小寫字母和數字（無空格）

### 錯誤：`attempt to index a nil value` in load.lua

- 確認所有 `require` 的路徑正確
- `DamageType:loadDefinition("/data/damage_types.lua")` — 路徑需要是虛擬路徑（`/data/...`）

### 錯誤：地圖生成後看不到 NPC

- 確認 `zone.lua` 的 `generator.actor` 已設定 `class`
- 確認 `data/zones/dungeon/npcs.lua` 有 `load(...)` 引用 NPC 定義
- 確認 NPC 的 `level_range` 與 zone 的 `level_range` 有重疊

### 錯誤：技能無法使用

- 確認 `load.lua` 有 `ActorTalents:loadDefinition("/data/talents.lua")`
- 確認技能在 `newTalentType` 中宣告了類型
- 確認 `descriptors.lua` 的 `[ActorTalents.T_KICK]` 常數名稱與技能 `name` 轉換後一致（`T_` + 大寫名稱，空格換成 `_`）

### 錯誤：玩家無法換層

- 確認 Grid 有設定 `change_level = 1` 或 `-1`
- 確認 `Game.lua` 的 `CHANGE_LEVEL` 按鍵綁定存在
- 確認 `zone.lua` 的生成器設定了 `up` 和 `down` 鍵對應

---

## 下一步

完成這個基礎模組後，可以繼續學習：

- **教學 02**：加入物品系統（揹包、裝備、消耗品）
- **教學 03**：加入多個地區（世界地圖）
- **教學 04**：加入任務系統
- **教學 05**：加入更豐富的 AI（戰術評分系統）
- **教學 06**：製作 Addon（在 ToME 上添加內容）
