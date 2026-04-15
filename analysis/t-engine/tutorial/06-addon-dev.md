# 教學 06：製作第一個 ToME Addon

> **目標**：從零開始製作一個 ToME Addon，學會三種整合機制（hooks / superload / overload），並以一個完整的「新增職業」範例貫穿全程。
>
> **前置**：閱讀 [教學 01](./01-hello-dungeon.md) 了解 TE4 基礎結構；熟悉 Lua 的 `require`、閉包、metatables。

---

## 1. Addon 是什麼

ToME 的 Addon 機制讓你在**不修改遊戲原始碼**的情況下：

- 新增職業、種族、技能樹、天賦
- 替換或擴充現有的 Lua 類別方法
- 注入回調至遊戲生命週期的特定時刻
- 覆蓋資源檔案（圖片、地圖、對話腳本）

Addon 是放在 `game/addons/<short_name>/` 的目錄（開發期間），或封裝成 `.team` zip 檔案（發布時）。引擎啟動後，`bootstrap/boot.lua` 會自動掃描並掛載啟用的 Addons。

---

## 2. 目錄結構

一個完整的 Addon 結構如下（全部可選，按需使用）：

```
game/addons/my-addon/
├── init.lua          ← 必須；Addon 元資料
├── hooks/
│   └── load.lua      ← 遊戲事件 hook（最常用）
├── superload/
│   └── mod/class/Actor.lua   ← 攔截並包裝現有 Lua 模組
├── overload/
│   └── mod/class/MyClass.lua ← 完全替換現有 Lua 模組
└── data/
    ├── birth/                ← 職業/種族描述符
    ├── talents/              ← 天賦定義
    └── ...                   ← 任意遊戲資料
```

---

## 3. `init.lua`：Addon 元資料

`init.lua` 是唯一必要的檔案。引擎讀取它來決定是否載入此 Addon。

```lua
-- game/addons/my-addon/init.lua

long_name  = "My First Addon"   -- 顯示名稱（主選單）
short_name = "my-addon"         -- 唯一識別碼（ASCII，不含空白）
for_module = "tome"             -- 目標模組，必須吻合才會載入

version    = {1, 0, 0}          -- 你的 Addon 版本
author     = { "你的名字", "email@example.com" }
homepage   = "https://example.com"
description = [[這個 Addon 新增一個強大的職業。]]

-- 宣告你需要哪些機制（設 true 才會被引擎掃描載入）
hooks     = true   -- 允許 hooks/load.lua
superload = true   -- 允許 superload/ 目錄
overload  = true   -- 允許 overload/ 目錄
data      = true   -- 允許 data/ 目錄

weight = 1         -- 數字越小越早載入（預設 1，DLC 通常 5+）

-- cheat_only = true  -- 僅在作弊模式啟用（如 tome-addon-dev）
-- dlc = 5            -- 標記為 DLC，需要線上驗證（如 tome-possessors）
```

### 關鍵欄位說明

| 欄位 | 說明 |
|------|------|
| `for_module` | 必須是 `"tome"` 才能用於 ToME；用於獨立模組時填自己的 `short_name` |
| `weight` | 決定 Addon 載入順序；多個 Addon 衝突時，weight 小的先載入 |
| `hooks` / `superload` / `overload` / `data` | 只宣告你實際使用的機制，未宣告的目錄不會被掃描 |

---

## 4. 三種整合機制

### 4.1 Hooks（事件注入）

**最常用**。在遊戲生命週期的特定時間點執行你的程式碼，不影響原始程式流程。

```lua
-- hooks/load.lua

class:bindHook("ToME:run", function(self, data)
    -- 遊戲啟動時執行（在主選單顯示之前）
    print("My addon is active!")
end)
```

`bindHook` 的第一個參數是事件名稱，第二個是回調函式。`self` 是觸發 hook 的物件（因事件而異）。

#### 常用 Hook 列表

| Hook 名稱 | 觸發時機 | `self` 物件 |
|-----------|----------|-------------|
| `ToME:run` | 遊戲啟動、主選單顯示前 | `class`（類別表） |
| `ToME:load` | `mod/load.lua` 最後執行時 | `class` |
| `ToME:runDone` | `run()` 完成後 | `class` |
| `ToME:birthDone` | 角色創建完成後 | `class` |
| `Entity:loadList` | 每次載入 Entity 列表（NPC、物品等）| 載入的 Entity 原型物件 |
| `MapGeneratorStatic:subgenRegister` | 靜態地圖子產生器註冊時 | 地圖產生器 |
| `Game:changeLevel` | 玩家切換樓層時 | `game` 物件 |
| `Game:alterGameMenu` | 遊戲選單開啟時 | `game` 物件 |
| `Actor:move` | Actor 移動後 | 移動的 Actor |
| `Actor:onWear` | Actor 裝備物品時 | Actor |
| `Actor:preUseTalent` | 使用天賦前（可取消）| Actor |
| `Actor:tooltip` | 顯示 Actor tooltip 時 | Actor |
| `Actor:actBase:Effects` | 每回合 Effect 計算時 | Actor |

#### 範例：用 `ToME:load` 載入新天賦定義

```lua
-- hooks/load.lua

class:bindHook("ToME:load", function(self, data)
    local ActorTalents = require "engine.interface.ActorTalents"
    local Birther = require "engine.Birther"

    -- 載入天賦定義檔
    ActorTalents:loadDefinition("/data-my-addon/talents/my-class.lua")

    -- 載入職業描述符
    Birther:loadDefinition("/data-my-addon/birth/my-class.lua")
end)
```

> **注意**：`data/` 目錄在 Addon 內被映射到 `/data-<short_name>/`（例如 `my-addon` → `/data-my-addon/`）。

#### 範例：用 `Entity:loadList` 注入額外實體

```lua
class:bindHook("Entity:loadList", function(self, data)
    -- data.file 是正在載入的檔案路徑
    -- data.res  是已載入的實體列表（table）
    if data.file == "/data/general/npcs/undead.lua" then
        -- 把自己的 NPC 加進同一個列表
        self:loadList("/data-my-addon/npcs/extra-undead.lua", nil, data.res)
    end
end)
```

---

### 4.2 Superload（方法包裝）

**用來修改現有類別的方法**。Superload 在原始模組之後執行，可以透過 `loadPrevious()` 取得原始模組，然後包裝它的方法。

```
原始模組 → superload 包裝層 → require 的呼叫者取得包裝後的模組
```

**範例**：修改 Actor 的 `gainExp` 讓某些狀態下阻止經驗獲取：

```lua
-- superload/mod/class/Actor.lua

-- loadPrevious() 觸發原始 mod/class/Actor.lua 的載入，
-- 並返回 package.loaded["mod.class.Actor"]
local _M = loadPrevious(...)

-- 儲存原始方法的引用
local orig_gainExp = _M.gainExp

-- 用新函式替換，保留對原始的呼叫
function _M:gainExp(value)
    -- 自訂前置邏輯
    if self.my_special_status then
        return  -- 阻止獲取經驗
    end
    -- 呼叫原始方法
    return orig_gainExp(self, value)
end

return _M  -- 必須 return _M
```

#### Superload 規則

1. **路徑對應**：`superload/mod/class/Actor.lua` → 攔截 `require "mod.class.Actor"`
2. **`loadPrevious(...)`**：呼叫時必須傳入 `...`（讓引擎知道模組名稱）
3. **必須 `return _M`**：否則模組變成 `nil`，遊戲崩潰
4. **多個 Addon**：載入順序由 `weight` 決定，每個 Superload 的 `loadPrevious` 指向前一層的版本（形成鏈）
5. **Engine 類別也可以 superload**：`superload/engine/Actor.lua` 可攔截 `require "engine.Actor"`

#### 什麼時候用 Superload？

- 修改現有方法的行為（加入額外邏輯）
- 在不破壞其他 Addon 的前提下擴充方法

---

### 4.3 Overload（完全替換）

**直接替換整個 Lua 模組檔案**，不呼叫原始版本。謹慎使用，容易與其他 Addon 衝突。

```lua
-- overload/mod/class/SomeClass.lua
-- 這個檔案完全替換 mod/class/SomeClass.lua

local class = require "engine.class"
local Parent = require "engine.SomeParent"

module(..., package.seeall, class.inherit(Parent))

function _M:someMethod()
    -- 完全替換的實作
end
```

#### 什麼時候用 Overload？

- 你需要添加完全新的類別（而不是修改現有的）
- 你需要替換整個 UI 對話框邏輯
- 添加新的遊戲資源（圖片、地圖等，放在 `overload/data/` 中）

**覆蓋遊戲資源**（圖片、地圖等）：

```
overload/data/gfx/my_custom_tile.png
overload/data/maps/my-zone/mymap.lua
```

---

## 5. `data/` 目錄

`data/` 下的檔案不被直接 `require`，而是透過各系統的 `loadDefinition`、`loadList` 等函式載入。在掛載後，路徑是 `/data-<short_name>/`。

```
data/
├── birth/          ← Birther:loadDefinition() 使用
├── talents/        ← ActorTalents:loadDefinition() 使用
├── timed_effects.lua ← ActorTemporaryEffects:loadDefinition() 使用
├── achievements/   ← WorldAchievements:loadDefinition() 使用
├── zones/          ← Zone 實例化時讀取
└── npcs/           ← Entity:loadList() 使用
```

---

## 6. 完整範例：新增一個職業

以下製作一個叫做「暗影刺客」（Shadow Assassin）的新職業，擴充現有的「亡靈」陣營。

### 步驟一：目錄結構

```
game/addons/my-shadow/
├── init.lua
├── hooks/
│   └── load.lua
└── data/
    ├── birth/
    │   └── shadow.lua
    └── talents/
        └── shadow/
            ├── shadow.lua         ← 天賦類型定義
            └── stealth-arts.lua   ← 天賦定義
```

### 步驟二：`init.lua`

```lua
-- game/addons/my-shadow/init.lua

long_name  = "Shadow Assassin Class"
short_name = "my-shadow"
for_module = "tome"
version    = {1, 0, 0}
author     = { "你的名字", "" }
description = [[Adds the Shadow Assassin class.]]

hooks = true
data  = true
```

### 步驟三：`hooks/load.lua`

```lua
-- game/addons/my-shadow/hooks/load.lua

class:bindHook("ToME:load", function(self, data)
    local ActorTalents = require "engine.interface.ActorTalents"
    local Birther = require "engine.Birther"

    -- 載入天賦類型（必須先於天賦定義）
    ActorTalents:loadDefinition("/data-my-shadow/talents/shadow/shadow.lua")
    -- 載入具體天賦
    ActorTalents:loadDefinition("/data-my-shadow/talents/shadow/stealth-arts.lua")

    -- 載入職業描述符（newBirthDescriptor）
    Birther:loadDefinition("/data-my-shadow/birth/shadow.lua")
end)
```

### 步驟四：天賦類型定義

```lua
-- game/addons/my-shadow/data/talents/shadow/shadow.lua

-- 宣告天賦類型分組
newTalentType{
    type   = "shadow/stealth-arts",
    name   = "Stealth Arts",
    -- 這個類型是否預設可見
    generic = false,
    description = "The art of moving unseen and striking from the shadows.",
}
```

### 步驟五：天賦定義

```lua
-- game/addons/my-shadow/data/talents/shadow/stealth-arts.lua

newTalent{
    name    = "Shadow Step",
    type    = {"shadow/stealth-arts", 1},  -- 類型 / 最低精通需求
    require = { stat = { dex=16 }, },
    points  = 5,     -- 最大等級
    cooldown = 8,
    stamina = 15,
    range   = function(self, t) return math.floor(3 + t.getLevel(self, t)) end,
    -- 讓 AI 知道這個技能的用途
    tactical = { CLOSEIN = 2, ESCAPE = 1 },

    action = function(self, t)
        -- 選取目標位置
        local tg = { type="hit", range=self:getTalentRange(t) }
        local x, y = self:getTarget(tg)
        if not x or not y then return nil end

        -- 瞬移到目標旁邊
        local block_actor = function(_, bx, by)
            return game.level.map:checkEntity(bx, by, Map.TERRAIN, "block_move")
        end
        local tx, ty = util.findFreeGrid(x, y, 1, true, {[Map.ACTOR]=true})
        if not tx then
            game.logPlayer(self, "没有可落腳的空位！")
            return nil
        end
        self:move(tx, ty, true)

        game.logSeen(self, "%s 瞬間消失在陰影中！", self:getName():capitalize())
        return true
    end,

    info = function(self, t)
        return ([[即刻傳送至目標附近（最遠 %d 格）。
消耗 %d 體力，冷卻 %d 回合。]]):format(
            self:getTalentRange(t),
            t.stamina,
            t.cooldown
        )
    end,
}

newTalent{
    name    = "Backstab",
    type    = {"shadow/stealth-arts", 2},
    require = { stat = { dex=20, cun=16 }, },
    points  = 5,
    cooldown = 5,
    stamina = 20,

    -- 傷害隨等級成長的輔助函式
    getDamage = function(self, t)
        return self:combatTalentWeaponDamage(t, 1.2, 2.5)
    end,

    tactical = { ATTACK = { weapon = 2 }, DISABLE = { stun = 1 } },

    action = function(self, t)
        local tg = { type="hit", range=1 }
        local x, y, target = self:getTarget(tg)
        if not x or not y or not target then return nil end

        -- 必須相鄰
        if core.fov.distance(self.x, self.y, x, y) > 1 then return nil end

        -- 攻擊
        local dam = t.getDamage(self, t)
        self:attackTarget(target, DamageType.PHYSICAL, dam, true)

        -- 暈眩
        if target:canBe("stun") then
            target:setEffect(target.EFF_STUNNED, 2 + math.floor(t.getLevel(self, t)/2), {})
        end

        return true
    end,

    info = function(self, t)
        return ([[背刺鄰近目標，造成 %d%% 武器傷害，並暈眩 %d 回合。]]):format(
            t.getDamage(self, t) * 100,
            2 + math.floor(self:getTalentLevelRaw(t)/2)
        )
    end,
}
```

### 步驟六：職業描述符

```lua
-- game/addons/my-shadow/data/birth/shadow.lua

-- 允許「亡靈」陣營選擇此職業
-- （如果不想限制，可以不寫這行，預設所有陣營可選）
getBirthDescriptor("class", "Rogue").descriptor_choices.subclass["Shadow Assassin"] = "allow"

newBirthDescriptor{
    type = "subclass",
    name = "Shadow Assassin",

    desc = {
        "暗影刺客是潛行與瞬殺的大師，他們在黑暗中穿梭，在目標察覺之前便已結束戰鬥。",
        "他們的核心屬性是：靈巧（Dexterity）與狡黠（Cunning）",
        "#GOLD#屬性加成：",
        "#LIGHT_BLUE# * +2 敏捷、+3 靈巧、+2 狡黠、-1 體質",
        "#GOLD#每級生命：#LIGHT_BLUE# -3",
    },

    -- 可選的陣營限制（"allow" | "disallow" | "never"）
    -- 這裡不設限，讓所有陣營都能選
    -- descriptor_choices = { ... },

    power_source = {technique=true, antimagic=false},

    stats = { str=0, dex=2, con=-1, mag=0, wil=0, cun=3 },

    -- 可學的天賦類型與初始精通
    talents_types = {
        -- {true/false=是否預設解鎖, 0.3=精通加成}
        ["shadow/stealth-arts"] = {true,  0.3},
        ["technique/combat-training"] = {true,  0},
        ["cunning/survival"]    = {true,  0},
        ["cunning/stealth"]     = {true,  0.3},
    },

    -- 出生時學會的天賦
    talents = {
        [ActorTalents.T_SHADOW_STEP] = 1,
        [ActorTalents.T_WEAPON_COMBAT] = 1,
        [ActorTalents.T_STEALTH] = 1,
    },

    -- 出生時的屬性直接修改
    copy = {
        max_life = 90,
        -- 裝備
        resolvers.equipbirth{ id=true,
            {type="weapon", subtype="dagger", name="iron dagger", autoreq=true, ego_chance=-1000},
            {type="armor",  subtype="light",  name="rough leather armour", autoreq=true, ego_chance=-1000},
        },
    },

    copy_add = {
        life_rating = -3,
    },
}
```

---

## 7. 測試開發中的 Addon

### 方法一：直接放目錄

開發時不需要打包，直接把 Addon 目錄放在：

```
game/addons/my-shadow/
```

ToME 啟動後，在主選單進入「Addons」，勾選你的 Addon，重啟即生效。

### 方法二：使用 tome-addon-dev

啟用 `tome-addon-dev` Addon 後，遊戲內有 Debug 選單（按 F1 或進入 Debug > Addon Developer），提供：

- **FSHelper**：瀏覽 PhysFS 虛擬檔案系統，確認路徑是否正確掛載
- **NPCDesign**：即時測試 NPC 定義
- **TalentFinder**：搜尋所有天賦
- **ExampleAddonMaker**：快速生成 Addon 骨架

### 常見錯誤排查

```lua
-- 在 hooks/load.lua 或天賦 action 中加 print
print("Loading my talent definition...")

-- 確認天賦常數是否產生
-- 天賦 "Shadow Step" → T_SHADOW_STEP
-- 在遊戲 console (F1 LUA CONSOLE) 中執行：
-- print(ActorTalents.T_SHADOW_STEP)
```

| 錯誤情況 | 可能原因 |
|----------|----------|
| Addon 不出現在清單 | `for_module` 與遊戲模組不符；`init.lua` 語法錯誤 |
| 天賦不在職業選單 | `hooks` 未設 `true`；`ToME:load` hook 內路徑錯誤 |
| `T_SHADOW_STEP` 為 nil | 天賦定義未被 `ActorTalents:loadDefinition` 載入 |
| superload 崩潰 | 忘了 `return _M`；或 `loadPrevious(...)` 缺了 `...` |
| 路徑找不到 | `data/` 的真實路徑是 `/data-my-shadow/`，不是 `/data/` |

---

## 8. Superload 鏈（多個 Addon 同時存在時）

當多個 Addon 都 superload 同一個模組時，引擎按 `weight` 從小到大串聯：

```
原始 Actor.lua
  └─ addon-A (weight=1) 的 superload → 呼叫 loadPrevious() 得到原始
      └─ addon-B (weight=2) 的 superload → 呼叫 loadPrevious() 得到 addon-A 的版本
          └─ require "mod.class.Actor" 返回最外層（addon-B 的版本）
```

這意味著：
- **每個 superload 必須呼叫 `loadPrevious()`**，否則斷鏈，前面的 Addon 失效
- **方法替換時必須儲存原始方法再呼叫**（如範例中的 `orig_gainExp`）
- 越後載入（weight 越大）的 Addon，包裝在最外層，優先執行

---

## 9. 打包發布

開發完成後，將 Addon 目錄壓縮成 `.team` 格式：

```bash
# 進入 Addon 目錄的父目錄
cd game/addons/

# 使用 zip 打包（.team 就是標準 zip）
zip -r my-shadow-1.0.0.team my-shadow/
```

發布時：
- 放在 [te4.org](https://te4.org) 的 Addon 頁面
- 或直接分發 `.team` 檔案，玩家放入 `~/.t-engine/4.0/game/addons/` 即可

---

## 10. 參考：實際 Addon 分析

| Addon | 使用機制 | 主要功能 |
|-------|----------|----------|
| `tome-addon-dev` | hooks + overload + superload | 開發工具（FSHelper、NPCDesign 等），僅 cheat 模式可用 |
| `tome-possessors` | hooks + superload + data | 完整 DLC 職業：hooks 載入天賦，superload/Actor.lua 攔截 gainExp |
| `tome-items-vault` | hooks + overload + data | 線上物品保管庫：hooks 注入地圖子產生器與實體列表 |

### tome-possessors 的載入流程

```
init.lua (hooks=true, superload=true, overload=true, data=true)
    │
    ├─ hooks/load.lua
    │      bindHook("ToME:load", PO.hookLoad)
    │
    ├─ superload/mod/class/Actor.lua
    │      loadPrevious(...)  ← 取得原始 Actor
    │      _M.gainExp = 包裝版（遇到 EFF_POSSESSION 時阻止經驗）
    │
    └─ overload/mod/class/PossessorsDLC.lua  ← 新類別（不覆蓋任何現有類別）
           hookLoad():
               ActorTalents:loadDefinition("/data-possessors/talents/...")
               ActorTemporaryEffects:loadDefinition("/data-possessors/timed_effects.lua")
               Birther:loadDefinition("/data-possessors/birth/psionic.lua")
```

---

## 11. 小結

| 機制 | 適用情境 | 風險 |
|------|----------|------|
| `hooks` | 注入生命週期、載入新定義 | 低；多個 Addon 共存沒問題 |
| `superload` | 修改現有方法行為 | 中；需正確呼叫 loadPrevious 維持鏈 |
| `overload` | 添加全新類別/替換資源 | 高；兩個 Addon 覆蓋同一檔案會衝突 |

**最佳實踐**：
1. 盡量用 `hooks/ToME:load` 載入定義，避免 superload
2. 必須修改現有方法時才用 superload，且一定要呼叫原始方法
3. 新增的類別放在 `overload/` 用獨特的路徑（如 `mod/class/MyAddonClass.lua`）
4. 資料檔案放在 `data/`，透過 `/data-<short_name>/` 路徑存取

---

**下一步**：→ [教學 07：為 ToME 新增職業與技能樹（進階）](./07-class-and-talents.md)
