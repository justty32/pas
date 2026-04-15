# 教學 02：加入物品系統

> **目標**：為 `hellodungeon` 模組（教學 01）加入完整的物品系統。玩家能撿起地板上的武器與藥水、裝備武器增加傷害、喝藥水回血，以及擊殺怪物後獲得掉落物。
>
> **前置條件**：已完成教學 01 的 hellodungeon 模組可正常執行。

---

## 目錄

1. [物品系統架構總覽](#1-物品系統架構總覽)
2. [第一步：定義裝備欄位（load.lua）](#2-第一步定義裝備欄位-loadlua)
3. [第二步：建立 Object 類別](#3-第二步建立-object-類別)
4. [第三步：更新 Actor 加入揹包功能](#4-第三步更新-actor-加入揹包功能)
5. [第四步：定義武器物品](#5-第四步定義武器物品)
6. [第五步：定義藥水（消耗品）](#6-第五步定義藥水消耗品)
7. [第六步：建立地區物品清單](#7-第六步建立地區物品清單)
8. [第七步：設定地區物品生成器](#8-第七步設定地區物品生成器)
9. [第八步：NPC 掉落物設定](#9-第八步npc-掉落物設定)
10. [第九步：玩家撿物與使用操作](#10-第九步玩家撿物與使用操作)
11. [第十步：戰鬥整合（裝備武器影響傷害）](#11-第十步戰鬥整合裝備武器影響傷害)
12. [完整檔案結構變更](#12-完整檔案結構變更)
13. [常見錯誤排查](#13-常見錯誤排查)

---

## 1. 物品系統架構總覽

TE4 的物品系統由四個核心概念組成：

```
ActorInventory（揹包介面）
  ├── 揹包槽位（INVEN）    ← 無限格數的主揹包
  └── 裝備槽位（WEAPON 等）← 已裝備的物品，穿上時生效

engine.Object（物品實體）
  ├── slot        ← 可裝備到哪個槽位（對應 defineInventory 的 short_name）
  ├── wielder     ← 裝備後給予 Actor 的臨時屬性加成
  ├── use_simple  ← 使用效果（消耗品）
  └── stacking    ← 是否可堆疊（true = 相同物品合併顯示）

Zone.object_list（物品資料庫）
  └── 從 data/zones/<zone>/objects.lua 載入

generator.object（地圖物品生成器）
  └── engine.generator.object.Random → 隨機散落物品到地板
```

**資料流向**：

```
load.lua
  → defineInventory（定義武器/裝備槽位）
  → Object:loadDefinition（載入物品原型）

zone.lua
  → object_class = "mod.class.Object"
  → generator.object.class = "engine.generator.object.Random"

Actor:init
  → body = { INVEN=20, WEAPON=1 }（初始化揹包）

Player 按鍵 g
  → Actor:pickupFloor()    ← 撿起地板物品
Player 按鍵 e / w
  → Actor:wearObject()     ← 裝備物品（自動呼叫 onWear → 套用 wielder）
Player 按鍵 d
  → Actor:dropFloor()      ← 丟棄物品
```

---

## 2. 第一步：定義裝備欄位（load.lua）

在 `load.lua` 中，使用 `ActorInventory:defineInventory()` 宣告我們的裝備欄位。這個呼叫必須在任何 Actor 被創建**之前**完成（所以放在 `load.lua` 最前面）。

**為什麼需要 defineInventory？**

`ActorInventory` 只有一個預設槽位：`INVEN`（主揹包，`INVEN_INVEN`）。所有「可穿戴」的槽位（武器欄、防具欄…）都必須手動定義。定義後，引擎會自動產生常數 `INVEN_WEAPON`，所有 Actor 類別都能透過這個常數存取欄位。

```lua
-- game/modules/hellodungeon/load.lua

local KeyBind = require "engine.KeyBind"
local DamageType = require "engine.DamageType"
local ActorStats = require "engine.interface.ActorStats"
local ActorResource = require "engine.interface.ActorResource"
local ActorTalents = require "engine.interface.ActorTalents"
local ActorAI = require "engine.interface.ActorAI"
local ActorTemporaryEffects = require "engine.interface.ActorTemporaryEffects"
local ActorInventory = require "engine.interface.ActorInventory"  -- ← 新增
local Birther = require "engine.Birther"

-- 載入預設按鍵綁定（inventory 包含 g/d/e/i 等背包鍵）
KeyBind:load("move,hotkeys,inventory,actions,interface,debug")

-- 定義裝備欄位
-- 參數：short_name, 顯示名稱, is_worn（true=穿戴時觸發 onWear）, 說明, show_equip
ActorInventory:defineInventory("WEAPON", "主武器", true,
    "主武器欄位，裝備武器以增加攻擊力。", true)

-- 傷害類型、技能、效果、屬性（與教學 01 相同）
DamageType:loadDefinition("/data/damage_types.lua")
ActorTalents:loadDefinition("/data/talents.lua")
ActorTemporaryEffects:loadDefinition("/data/timed_effects.lua")

ActorResource:defineResource(
    "Power", "power",
    nil, "power_regen",
    "能量代表你使用特殊技能的能力。"
)

ActorStats:defineStat("Strength",    "str", 10, 1, 100, "力量：影響近戰傷害。")
ActorStats:defineStat("Dexterity",   "dex", 10, 1, 100, "敏捷：影響命中率。")
ActorStats:defineStat("Constitution","con", 10, 1, 100, "體質：影響最大生命值。")

ActorAI:loadDefinition("/engine/ai/")
Birther:loadDefinition("/data/birth/descriptors.lua")

return { require "mod.class.Game" }
```

**defineInventory 參數說明**：

| 參數 | 說明 |
|------|------|
| `"WEAPON"` | short_name，產生常數 `INVEN_WEAPON`，物品的 `slot` 欄位也要填這個 |
| `"主武器"` | 顯示給玩家看的名稱 |
| `true` | `is_worn = true`：物品加入此槽位時自動呼叫 `onWear()`，應用 `wielder` 加成 |
| `true`（最後一個） | `show_equip = true`：裝備視窗中顯示此欄位 |

---

## 3. 第二步：建立 Object 類別

物品需要自己的類別。最小版本只需繼承 `engine.Object` 即可：

```lua
-- game/modules/hellodungeon/class/Object.lua

require "engine.class"
local Object = require "engine.Object"

module(..., package.seeall, class.inherit(Object))

--- 物品顯示顏色
-- 這裡可以依 type 回傳不同顏色，目前統一用白色
function _M:getDisplayColor()
    if self.type == "weapon" then
        return {200, 200, 255}  -- 武器：淡藍
    elseif self.type == "potion" then
        return {100, 255, 100}  -- 藥水：綠
    end
    return {255, 255, 255}      -- 預設：白
end

--- 物品完整描述（按 '/' 或游標懸停時顯示）
function _M:getDesc()
    local str = self.name.."\n"
    if self.desc then
        str = str..self.desc.."\n"
    end
    -- 顯示裝備加成
    if self.wielder then
        if self.wielder.combat_dam then
            str = str..("  傷害 +%d\n"):format(self.wielder.combat_dam)
        end
        if self.wielder.combat_apr then
            str = str..("  穿甲 +%d\n"):format(self.wielder.combat_apr)
        end
    end
    return str
end
```

**engine.Object 提供什麼？**

| 方法/欄位 | 說明 |
|-----------|------|
| `stackable()` / `canStack(o)` | 判斷是否可堆疊（需設 `stacking = true` 或字串） |
| `getNumber()` | 回傳堆疊數量 |
| `stack(o)` / `unstack(n)` | 合併/分離堆疊 |
| `wornInven()` | 依 `self.slot` 回傳對應的 `INVEN_*` ID |
| `getName(t)` | 帶數量的名稱（`{no_count=true}` 不顯示數量） |
| `resolve()` | 執行所有 resolver（物品生成時自動呼叫） |

---

## 4. 第三步：更新 Actor 加入揹包功能

`ActorInventory` 是一個**混入（mixin）**，需要加入 Actor 的 `class.inherit()` 列表，並在 `body` 欄位宣告每個揹包欄的最大格數：

```lua
-- game/modules/hellodungeon/class/Actor.lua

require "engine.class"
local Actor = require "engine.Actor"
local ActorTalents = require "engine.interface.ActorTalents"
local ActorStats = require "engine.interface.ActorStats"
local ActorResource = require "engine.interface.ActorResource"
local ActorTemporaryEffects = require "engine.interface.ActorTemporaryEffects"
local ActorAI = require "engine.interface.ActorAI"
local ActorFOV = require "engine.interface.ActorFOV"
local ActorInventory = require "engine.interface.ActorInventory"   -- ← 新增

module(..., package.seeall, class.inherit(
    Actor,
    ActorTalents,
    ActorStats,
    ActorResource,
    ActorTemporaryEffects,
    ActorAI,
    ActorFOV,
    ActorInventory      -- ← 新增
))

function _M:init(t, no_default)
    -- 宣告揹包欄位格數
    -- body 在 ActorInventory:init() 中被消耗（轉換為 self.inven 表格），之後設為 nil
    -- 格數決定最多能放幾個「格」的物品（堆疊算一格）
    t.body = t.body or {
        INVEN  = 20,    -- 主揹包：20格
        WEAPON = 1,     -- 武器欄：只有 1 個武器
    }

    Actor.init(self, t, no_default)
    ActorTalents.init(self, t)
    ActorStats.init(self, t)
    ActorResource.init(self, t)
    ActorTemporaryEffects.init(self, t)
    ActorInventory.init(self, t)   -- ← 新增，放在所有 init 的最後
end

--- 每回合的行動（能量驅動）
function _M:act()
    if not Actor.act(self) then return end
    self:timedEffects()
    self:useEnergy()
end

--- 用於戰鬥傷害計算：回傳基礎傷害（後面會擴充為讀取武器）
function _M:combatDamage()
    local dam = self.combat_dam or 5
    -- 若主武器欄有武器，加上武器的 combat_dam 加成
    -- （wielder 系統會自動把 combat_dam 加到 Actor 身上，
    --   所以這裡 self.combat_dam 已包含武器加成）
    return dam
end
```

**為什麼 `body` 在 init 之後就消失？**

`ActorInventory:init()` 會讀取 `self.body`，為每個宣告的槽位建立 `self.inven[id]` 表格，然後把 `self.body` 設為 `nil`（釋放記憶體，也避免存檔時重複初始化）。這是引擎的設計：`body` 是「建構參數」，不是持久狀態。

---

## 5. 第四步：定義武器物品

建立物品定義檔。物品原型使用 `newEntity{...}` 語法（與 NPC 和地形相同）：

```lua
-- game/modules/hellodungeon/data/general/objects/weapons.lua

-- ============================================================
-- 武器基底原型
-- define_as：可被其他 newEntity 用 base = "BASE_WEAPON" 繼承
-- slot：對應 defineInventory 的 short_name → 裝備到 WEAPON 欄
-- ============================================================
newEntity{
    define_as = "BASE_WEAPON",
    type = "weapon", subtype = "sword",
    slot = "WEAPON",            -- 裝備到 WEAPON 槽
    display = "/",              -- 地圖上的字元顯示
    color = colors.SLATE,
    encumber = 2,               -- 揹包重量（目前未強制限制，但可自行實作）
    -- rarity 決定此物品在隨機生成時的出現機率
    -- 數字越大越罕見，沒有 rarity 的物品永遠不會隨機出現
    rarity = 5,
    desc = "一把近戰武器。",
}

-- ── 木劍（初級） ──────────────────────────────────────────
newEntity{ base = "BASE_WEAPON",
    name = "木劍",
    level_range = {1, 5},   -- 僅在 1~5 層隨機出現
    rarity = 3,             -- 比較常見
    cost = 5,               -- 商店售價（目前未用）
    -- wielder：裝備後套用到 Actor 的臨時加成
    -- 原理：ActorInventory:onWear() 呼叫 self:addTemporaryValue(k, v)
    --        ActorInventory:onTakeoff() 呼叫 self:removeTemporaryValue(k, id)
    wielder = {
        combat_dam = 3,     -- 傷害加成（Actor.combat_dam 會自動增加）
        combat_apr = 1,     -- 穿甲加成（需在 Combat.lua 中讀取）
    },
}

-- ── 鐵劍（中級） ──────────────────────────────────────────
newEntity{ base = "BASE_WEAPON",
    name = "鐵劍",
    level_range = {3, 10},
    rarity = 5,
    cost = 20,
    wielder = {
        combat_dam = 7,
        combat_apr = 2,
    },
}

-- ── 精鋼劍（高級） ────────────────────────────────────────
newEntity{ base = "BASE_WEAPON",
    name = "精鋼劍",
    level_range = {8, 20},
    rarity = 8,
    cost = 60,
    wielder = {
        combat_dam = 14,
        combat_apr = 4,
    },
}
```

**`wielder` 的工作原理**：

當玩家裝備武器時，`ActorInventory:onWear()` 被呼叫：

```lua
-- engine/interface/ActorInventory.lua (簡化版)
function _M:onWear(o, inven_id)
    o.wielded = {}
    o:check("on_wear", self, inven_id)   -- 呼叫物品的 on_wear 鉤子（若有）
    if o.wielder then
        for k, e in pairs(o.wielder) do
            -- addTemporaryValue 讓屬性可疊加、也可完整移除
            o.wielded[k] = self:addTemporaryValue(k, e)
        end
    end
end
```

`addTemporaryValue("combat_dam", 7)` 會讓 `self.combat_dam` 增加 7，並回傳一個移除用的 ID 存在 `o.wielded` 裡。取下武器時用這個 ID 精確移除加成，不會影響其他來源（例如 buff）。

---

## 6. 第五步：定義藥水（消耗品）

```lua
-- game/modules/hellodungeon/data/general/objects/potions.lua

-- ============================================================
-- 藥水基底
-- stacking = true：相同藥水在揹包中自動堆疊
-- use_simple：定義「使用」效果（按 a 使用物品時觸發）
-- ============================================================
newEntity{
    define_as = "BASE_POTION",
    type = "potion", subtype = "potion",
    display = "!", color = colors.VIOLET,
    encumber = 0.2,
    stacking = true,    -- 可堆疊：多個「治癒藥水」合為一格顯示數量
    rarity = 4,
    desc = "神祕的魔法藥水。",
}

-- ── 治癒藥水 ──────────────────────────────────────────────
newEntity{ base = "BASE_POTION",
    name = "治癒藥水",
    color = colors.RED,
    level_range = {1, 50},
    rarity = 3,
    cost = 10,
    -- use_simple：最基本的使用定義
    -- name：動作描述（顯示在日誌中）
    -- use：回傳一個 function，實際執行使用效果
    use_simple = {
        name = "喝下治癒藥水",
        use = function(self, who)
            local heal = 20 + rng.range(1, 10)
            who:heal(heal, who)
            game.logSeen(who, "%s 喝下治癒藥水，恢復了 %d 點生命！",
                who:getName():capitalize(), heal)
            -- 回傳 true = 使用成功（物品會被消耗掉）
            -- 回傳 false = 使用失敗（物品不消耗）
            return {used=true, id=true}
        end
    },
}

-- ── 力量藥水 ──────────────────────────────────────────────
newEntity{ base = "BASE_POTION",
    name = "力量藥水",
    color = colors.ORANGE,
    level_range = {3, 50},
    rarity = 6,
    cost = 25,
    use_simple = {
        name = "喝下力量藥水",
        use = function(self, who)
            -- 臨時增加 5 點力量，持續 20 回合
            -- 使用 ActorTemporaryEffects 的持續效果系統
            -- （需要在 timed_effects.lua 定義 EFF_STRENGTH_BOOST）
            game.logSeen(who, "%s 喝下力量藥水，力量暫時提升！",
                who:getName():capitalize())
            -- 這裡改用直接增加屬性作為示範（更簡單）
            local id = who:addTemporaryValue("combat_dam", 5)
            -- 20 回合後移除
            who:setEffect(who.EFF_STRENGTH_BOOST, 20, {id=id})
            return {used=true, id=true}
        end
    },
}
```

**`use_simple` vs `use`**：

| 欄位 | 說明 |
|------|------|
| `use_simple.name` | 動作選單顯示的文字 |
| `use_simple.use(self, who)` | `self`=物品, `who`=使用者；回傳 `{used=true}` 消耗物品 |
| `use` | 完整版（可自訂對話框、目標選擇），進階用法 |

> **注意**：力量藥水範例用到了 `EFF_STRENGTH_BOOST`，如果你的 `timed_effects.lua` 沒有定義這個效果，執行時會報錯。可以先只保留治癒藥水測試，或在 `timed_effects.lua` 中補充定義（見附錄）。

---

## 7. 第六步：建立地區物品清單

Zone 在載入時會自動讀取對應目錄下的 `objects.lua`：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/objects.lua

-- load() 是引擎提供的特殊函數，用於在 Entity:loadList() 中載入子檔案
-- 功能等同於在當前上下文中執行那個 lua 檔案，並把 newEntity 定義加進清單

load("/data/general/objects/weapons.lua")
load("/data/general/objects/potions.lua")
```

**為什麼要有這個中間層？**

`Zone:loadBaseLists()` 呼叫 `object_class:loadList("...objects.lua")`，這個函數會執行該檔案，並收集所有 `newEntity{}` 呼叫的結果到一個清單。用 `load()` 轉發到子檔案，讓你可以把物品按類別分開管理，不必塞在同一個大檔案裡。

---

## 8. 第七步：設定地區物品生成器

更新 `zone.lua`，加入三件事：`object_class`、物品生成器設定、`setup()` 加入物品類別：

```lua
-- game/modules/hellodungeon/data/zones/dungeon/zone.lua

return {
    name = "地下城",
    short_name = "dungeon",
    level_range = {1, 10},
    level_scheme = "player",
    max_level = 3,
    decay = {300, 800},
    persistent = "zone",

    -- ← 加入這行：告訴 Zone 用哪個類別來代表物品
    object_class = "mod.class.Object",

    -- Zone:setup() 初始化各類 Entity 的類別
    -- 加入 object_class 讓 Zone 知道要用哪個 Object
    on_setup = function(self)
        self:setup{
            npc_class    = "mod.class.NPC",
            grid_class   = "mod.class.Grid",
            object_class = "mod.class.Object",   -- ← 新增
        }
    end,

    -- 地形、NPC 生成器與教學 01 相同
    generator = {
        map = {
            class = "engine.generator.map.Roomer",
            nb_rooms = 8,
            rooms = {"rect"},
            lite_room_chance = 80,
            floor = "FLOOR",
            wall  = "WALL",
            up    = "UP",
            down  = "DOWN",
        },
        actor = {
            class = "engine.generator.actor.Random",
            nb_npc = {5, 10},
        },
        -- ← 加入物品生成器
        object = {
            class = "engine.generator.object.Random",
            -- 每層地圖隨機散落的物品數量範圍
            nb_object = {3, 7},
        },
    },
}
```

`engine.generator.object.Random` 的工作流程：

1. 呼叫 `zone:makeEntity(level, "object", filter)` 從物品清單中依 `rarity` 隨機選一個
2. 找一個空地板格（不在牆上、不在特殊位置）
3. 呼叫 `zone:addEntity(level, o, "object", x, y)` 把物品放到地圖

---

## 9. 第八步：NPC 掉落物設定

讓怪物死亡後有機率掉落物品，需要在 NPC 定義中加入 `resolvers.drops`。

首先，確認你的模組有載入 ToME 的 resolver（或者用引擎基礎 resolver）。對於 hellodungeon，我們自己實作一個簡化版的 drops：

```lua
-- game/modules/hellodungeon/data/general/npcs/kobold.lua
-- （在教學 01 的科博德定義中加入 drops）

newEntity{
    define_as = "BASE_KOBOLD",
    type = "humanoid", subtype = "kobold",
    display = "k", color = colors.GREEN,
    body = { INVEN=10, WEAPON=1 },
    -- 其他欄位與教學 01 相同...
    ai = "dumb_talented", ai_state = { talent_in=3 },
    energy = { mod=1 },
    autolevel = "warrior",
    stats = { str=8, dex=8, con=8 },
}

newEntity{ base = "BASE_KOBOLD",
    name = "科博德",
    level_range = {1, 5},
    exp_worth = 1,
    max_life = resolvers.rngrange(10, 20),
    life_rating = 8,
    combat = { dam=resolvers.rngrange(2, 5), atk=4, apr=1 },
    -- on_die：Actor 死亡時呼叫的回調函數
    -- 這是最直接的掉落物實作（不依賴 ToME 的 resolvers.drops）
    on_die = function(self, who)
        -- 50% 機率掉落一個物品
        if not rng.percent(50) then return end
        -- 從地區物品清單中隨機生成一個物品
        local o = game.zone:makeEntity(game.level, "object", nil, nil, true)
        if o then
            -- 放到怪物死亡的位置
            game.level.map:addObject(self.x, self.y, o)
            game.logSeen(self, "%s 掉落了 %s！",
                self:getName():capitalize(), o:getName{do_color=true})
        end
    end,
}

newEntity{ base = "BASE_KOBOLD",
    name = "科博德戰士",
    level_range = {3, 8},
    exp_worth = 2,
    max_life = resolvers.rngrange(20, 35),
    life_rating = 10,
    combat = { dam=resolvers.rngrange(5, 10), atk=6, apr=2 },
    on_die = function(self, who)
        -- 80% 機率掉落，更強的怪物掉落率更高
        if not rng.percent(80) then return end
        local o = game.zone:makeEntity(game.level, "object", nil, nil, true)
        if o then
            game.level.map:addObject(self.x, self.y, o)
        end
    end,
}
```

**為什麼不用 `resolvers.drops`？**

`resolvers.drops`（定義在 `mod/resolvers.lua`）是 ToME 模組專屬的 resolver，依賴 ToME 的物品篩選系統（`game.state:entityFilter` 等）。hellodungeon 是獨立模組，直接在 `on_die` 中呼叫 `zone:makeEntity()` 更簡單直接。若要移植到 ToME Addon，才需要改用 `resolvers.drops`。

---

## 10. 第九步：玩家撿物與使用操作

在 `Player.lua` 中加入按鍵處理函數：

```lua
-- game/modules/hellodungeon/class/Player.lua

require "engine.class"
local Actor = require "mod.class.Actor"

module(..., package.seeall, class.inherit(Actor))

function _M:init(t, no_default)
    t.body = t.body or {
        INVEN  = 20,
        WEAPON = 1,
    }
    Actor.init(self, t, no_default)
    self.player = true
end

--- 玩家行動入口（由 Game:tick() 呼叫）
function _M:act()
    if not Actor.act(self) then return end
    self:playerTurn()
end

--- 等待玩家輸入（暫停遊戲回合）
function _M:playerTurn()
    -- 暫停：讓遊戲迴圈等待玩家按鍵
    -- Game:key:on(...) 設定的事件處理器負責呼叫實際動作
    game.paused = true
end

--- 撿起腳下物品
function _M:pickup()
    -- 如果地板上只有一個物品，直接撿
    -- 如果有多個，顯示選擇對話框
    local objs = {}
    for i = Map.OBJECT, Map.OBJECT + 9 do
        local o = game.level.map:getObject(self.x, self.y, i)
        if o then objs[#objs+1] = {obj=o, idx=i - Map.OBJECT + 1} end
    end

    if #objs == 0 then
        game.logPlayer(self, "這裡什麼都沒有。")
        return
    elseif #objs == 1 then
        local o, num = self:pickupFloor(1, true)
        -- pickupFloor 自動顯示撿起訊息（vocal=true）
    else
        -- 多物品：顯示選擇視窗
        self:showPickupFloor("撿起什麼？", nil, function(o, item)
            self:pickupFloor(item, true)
        end)
    end
    self:useEnergy()
end

--- 顯示揹包
function _M:showEquipment_player()
    self:showEquipInven("裝備與揹包",
        nil,  -- filter：nil 表示顯示所有物品
        function(o, inven, item, button)
            if button == "left" then
                -- 左鍵：嘗試裝備（若是裝備欄的物品則卸下）
                local inven_o = self:getInven(inven)
                if inven_o and inven_o.worn then
                    -- 物品已裝備 → 卸下
                    local ro = self:takeoffObject(inven, item)
                    if ro then
                        self:addObject(self.INVEN_INVEN, ro)
                        game.logPlayer(self, "卸下了 %s。", ro:getName{do_color=true})
                        self:useEnergy()
                    end
                else
                    -- 未裝備 → 嘗試裝備
                    local ro, rs = self:wearObject(o, true, true)
                    if ro then
                        -- wearObject 回傳被替換的物品，放回揹包
                        if not self:addObject(self.INVEN_INVEN, ro) then
                            -- 揹包滿了，直接放地板
                            game.level.map:addObject(self.x, self.y, ro)
                        end
                        self:useEnergy()
                    end
                end
            elseif button == "right" then
                -- 右鍵：使用物品（藥水等）
                if o.use_simple then
                    local r = o.use_simple.use(o, self)
                    if r and r.used then
                        -- 從揹包移除一個
                        self:removeObject(inven, item, 1)
                        self:useEnergy()
                    end
                end
            end
        end
    )
end

--- 丟棄選中的物品
function _M:dropItem()
    self:showEquipInven("丟棄什麼？",
        nil,
        function(o, inven, item, button)
            local ro = self:dropFloor(inven, item, true, true)
            if ro then
                self:useEnergy()
            end
        end
    )
end
```

接著在 `Game.lua` 的 `setupKeys()` 中將這些函數綁定到按鍵：

```lua
-- game/modules/hellodungeon/class/Game.lua
-- 在 setupKeys() 函數中加入（或修改）以下按鍵綁定

function _M:setupKeys()
    -- ... 移動按鍵（與教學 01 相同）...

    -- g：撿起腳下的物品
    self.key:addCommands{
        [{"_g"}] = function()
            if game.player then game.player:pickup() end
        end,
    }

    -- i：開啟揹包/裝備介面
    self.key:addCommands{
        [{"_i"}] = function()
            if game.player then game.player:showEquipment_player() end
        end,
    }

    -- d：丟棄物品
    self.key:addCommands{
        [{"_d"}] = function()
            if game.player then game.player:dropItem() end
        end,
    }

    -- a：使用揹包中的物品（快速使用）
    self.key:addCommands{
        [{"_a"}] = function()
            if game.player then
                game.player:showInventory("使用哪個物品？",
                    game.player:getInven("INVEN"),
                    function(o) return o.use_simple ~= nil end,  -- 只顯示可使用物品
                    function(o, item)
                        if o.use_simple then
                            local r = o.use_simple.use(o, game.player)
                            if r and r.used then
                                game.player:removeObject(game.player.INVEN_INVEN, item, 1)
                                game.player:useEnergy()
                            end
                        end
                    end
                )
            end
        end,
    }
end
```

**按鍵說明**：

| 按鍵 | 功能 |
|------|------|
| `g` | 撿起腳下物品 |
| `i` | 開啟裝備/揹包視窗（左鍵裝備/卸下，右鍵使用） |
| `d` | 開啟丟棄視窗 |
| `a` | 使用揹包中的消耗品 |

---

## 11. 第十步：戰鬥整合（裝備武器影響傷害）

教學 01 的 `Combat.lua` 使用固定傷害。現在武器的 `wielder.combat_dam` 會透過 `addTemporaryValue` 自動累加到 `Actor.combat_dam`，所以只需確保 `Combat.lua` 使用的是 `self.combat_dam`：

```lua
-- game/modules/hellodungeon/class/interface/Combat.lua
-- （修改 attackTarget 中的傷害計算部分）

function _M:attackTarget(target)
    -- 命中判定（與教學 01 相同）
    local hit = self:checkHit(self:combatAttack(), target:combatDefense())

    if hit then
        -- 傷害 = Actor 的 combat_dam 屬性
        -- 當武器裝備時，wielder.combat_dam 已透過 addTemporaryValue 加進來
        -- 所以這裡直接讀 self.combat_dam 就包含了武器加成
        local dam = math.max(1, (self.combat_dam or 5) + rng.range(-2, 2))

        target:takeHit(dam, self)
        game.logSeen(self, "%s 攻擊 %s，造成 %d 點傷害！",
            self:getName():capitalize(),
            target:getName():capitalize(),
            dam)
        return true
    else
        game.logSeen(self, "%s 攻擊 %s，但未命中！",
            self:getName():capitalize(),
            target:getName():capitalize())
        return false
    end
end
```

**`addTemporaryValue` 的累加原理**：

```
玩家基礎 combat_dam = 5         （在 Actor init 中設定）
裝備木劍後：
  addTemporaryValue("combat_dam", 3)
  → self.combat_dam = 5 + 3 = 8  （自動累加）
卸下木劍後：
  removeTemporaryValue("combat_dam", id)
  → self.combat_dam = 5           （精確移除，不影響其他加成）
```

引擎的 `addTemporaryValue` 實作在 `engine/Entity.lua`，支援：
- 數字型：直接加減
- 表格型：深度合併（用於複合加成）
- 函數型：每次存取時動態計算

---

## 12. 完整檔案結構變更

相對於教學 01，需要**新增**或**修改**的檔案：

```
game/modules/hellodungeon/
│
├── load.lua                          ← 修改：加入 ActorInventory + defineInventory
│
├── class/
│   ├── Actor.lua                     ← 修改：繼承 ActorInventory，加入 body，呼叫 ActorInventory.init
│   ├── Object.lua                    ← 新增：物品類別
│   ├── Player.lua                    ← 修改：加入 pickup/showEquipment_player/dropItem
│   └── Game.lua                      ← 修改：setupKeys 加入 g/i/d/a 鍵
│
├── class/interface/
│   └── Combat.lua                    ← 修改：傷害計算改讀 self.combat_dam
│
└── data/
    ├── general/
    │   └── objects/                  ← 新增目錄
    │       ├── weapons.lua           ← 新增：武器定義
    │       └── potions.lua           ← 新增：藥水定義
    └── zones/
        └── dungeon/
            ├── zone.lua              ← 修改：加入 object_class + generator.object
            └── objects.lua           ← 新增：地區物品清單（load weapons + potions）
```

**共新增 3 個檔案，修改 5 個檔案**。

---

## 13. 常見錯誤排查

### 錯誤：`attempt to index a nil value (self.inven)`

**原因**：Actor 沒有繼承 `ActorInventory` 或沒有呼叫 `ActorInventory.init(self, t)`。

**解法**：
1. 確認 `class.inherit(...)` 列表包含 `ActorInventory`
2. 確認 `Actor.init()` 中呼叫了 `ActorInventory.init(self, t)`
3. 確認 `t.body` 已在呼叫 `init` **之前**設定好

---

### 錯誤：`inventory slot undefined: WEAPON`

**原因**：`Actor.body` 宣告了 `WEAPON=1`，但 `defineInventory("WEAPON", ...)` 還沒被呼叫。

**解法**：確認 `load.lua` 中的 `ActorInventory:defineInventory("WEAPON", ...)` 在任何 Actor 被創建之前就執行到。`load.lua` 是在遊戲開始前載入，只要放在 `load.lua` 裡面就夠早。

---

### 錯誤：物品不出現在地圖上

**可能原因一**：`zone.lua` 沒有加 `generator.object` 區塊。  
**可能原因二**：所有物品定義都沒有 `rarity` 欄位（沒有 rarity 的物品不會被隨機生成）。  
**可能原因三**：`objects.lua` 的 `load()` 路徑錯誤（注意路徑是虛擬路徑 `/data/...`，不是磁碟路徑）。

---

### 錯誤：`wearObject` 返回 `false`，武器裝備失敗

**原因**：物品的 `slot` 欄位與 `defineInventory` 的 `short_name` 不符合，或 Actor 沒有對應的揹包欄位。

**解法**：
- 確認物品定義有 `slot = "WEAPON"`（大寫）
- 確認 `defineInventory("WEAPON", ...)` 已呼叫
- 確認 Actor 的 `body` 包含 `WEAPON=1`

---

### 錯誤：喝藥水後物品沒有消失

**原因**：`use_simple.use()` 回傳的表格結構不對，或 Player 的處理邏輯中沒有呼叫 `removeObject`。

**解法**：確認 `use_simple.use()` 回傳 `{used=true}`，且你的 Player 程式碼在 `r.used` 為真時有呼叫：

```lua
self:removeObject(inven, item, 1)  -- 從揹包移除 1 個（堆疊時只消耗一個）
```

---

### 進階排查：武器裝備了但傷害沒增加

**原因**：`Combat.lua` 沒有讀取 `self.combat_dam`，或讀取的是舊的固定值。

**診斷方式**：

```lua
-- 在 Player 身上臨時加入除錯輸出
function _M:pickup()
    -- ... 撿物邏輯 ...
    print("目前 combat_dam:", self.combat_dam)
end
```

裝備武器後，`combat_dam` 應該增加對應的 `wielder.combat_dam` 數值。若沒有增加，檢查 `onWear` 是否被呼叫（確認 `defineInventory` 的第三個參數 `is_worn = true`）。

---

## 附錄：力量藥水需要的 timed_effects.lua 補充

若要使用力量藥水的範例，在 `data/timed_effects.lua` 中加入：

```lua
-- 在現有的效果定義後面加入
newEffect{
    name = "STRENGTH_BOOST",
    desc = "力量提升",
    type = "physical",
    subtype = { },
    status = "beneficial",
    parameters = { id=nil },
    -- 效果結束時：移除 addTemporaryValue 加的 combat_dam 加成
    deactivate = function(self, eff)
        if eff.id then
            self:removeTemporaryValue("combat_dam", eff.id)
        end
    end,
}
```

---

## 下一步

完成本教學後，你的 hellodungeon 已具備完整的物品系統：武器、消耗品、撿物、裝備、丟棄。

下一個教學（**教學 03：多地區與世界地圖**）將加入：
- 第二個地區（城鎮）
- 世界地圖（Wilderness）
- 地區切換（`game:changeLevel()`）
- 傳送點地形（觸碰後進入地城）
