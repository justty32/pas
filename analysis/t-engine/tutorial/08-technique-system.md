# 教學 08：全新技能系統——連技體系（Technique System）

> **目標**：設計並實作一套與 TE4 現有技能樹（TalentType/Talent）**完全獨立**的技能系統——「連技體系」。玩家透過戰鬥、訓練師或掉落物獲得「連技」，裝填到最多 5 個槽位，按順序施展可累積連擊計數，並以終結技收割強化效果。系統擁有自己的橫條 HUD，不使用現有的技能樹 UI，但仍完整接入 TE4 的戰鬥屬性（`combat_dam`、`getStat()`、`project()`）。
>
> **設計哲學**：與現有技能樹的核心差異不在於「效果」，而在於**取得方式**、**排列組合**和**狀態機**。技能樹靠「加點」進化；連技靠「習得與熟練」，並透過連擊順序產生乘算效果。

---

## 目錄

1. [系統設計總覽](#1-系統設計總覽)
2. [資料結構定義](#2-資料結構定義)
3. [ActorTechnique 混入](#3-actortechnique-混入)
4. [連技定義檔格式](#4-連技定義檔格式)
5. [五個範例連技（完整程式碼）](#5-五個範例連技)
6. [連技 HUD（橫條顯示器）](#6-連技-hud橫條顯示器)
7. [整合到 Game.lua 與 Player.lua](#7-整合到-gamelua-與-playerlua)
8. [連技的取得方式](#8-連技的取得方式)
9. [熟練度系統](#9-熟練度系統)
10. [完整檔案結構](#10-完整檔案結構)
11. [常見錯誤排查](#11-常見錯誤排查)

---

## 1. 系統設計總覽

### 1.1 與現有技能樹的對比

| 面向 | 技能樹（Talent） | 連技（Technique） |
|------|-----------------|------------------|
| 取得 | 創建角色選職業，消耗點數加點 | 從世界獲得（掉落/訓練師/事件） |
| 進化 | 加到 5 點，每點效果增加 | 使用次數累積熟練度（0→100%） |
| 結構 | 樹狀依賴，有前置技能 | 自由槽位（5 格），無依賴限制 |
| 執行 | 每個技能獨立冷卻，順序無關 | 有連擊計數，順序影響效果 |
| UI | 垂直技能樹視窗 | 橫條 HUD（始終顯示在畫面底部） |
| 資源 | mana / stamina（按技能設計） | 共用「氣（Ki）」資源池 |

### 1.2 連技狀態機

```
idle（無連擊）
  → [使用任意連技]
       → combo（連擊中，連擊數 +1）
           → [3 回合內繼續使用連技] → combo（繼續累積）
           → [使用終結技] → burst（結算加成，清空計數）→ idle
           → [3 回合未行動] → [連擊計數清零] → idle
```

### 1.3 連技類型

| 類型 | 說明 | 連擊效果 |
|------|------|----------|
| `starter` （起手） | 低消耗，可從 idle 狀態使用 | 建立第 1 個連擊計數 |
| `linker`  （中繼） | 只有在 combo 狀態才能使用 | 連擊計數 +1 |
| `finisher`（終結） | 連擊計數越高效果越強 | 清空計數，觸發 burst 效果 |
| `free`    （自由） | 任何狀態皆可使用，不影響計數 | 不累積，不中斷連擊 |

---

## 2. 資料結構定義

### 2.1 Actor 上的連技狀態

```lua
actor.techniques = {
    -- 5 個槽位（1~5），每個儲存一個連技 ID
    slots = {nil, nil, nil, nil, nil},
    -- 已習得的連技清單 { id = {proficiency=0,...} }
    known = {},
}

actor.combo_state = {
    count  = 0,      -- 當前連擊計數
    timer  = 0,      -- 距離連擊超時還有幾回合
    active = false,  -- 是否在 combo 狀態
}
```

### 2.2 全域連技定義表

```lua
-- 類似 ActorTalents.talents_def，存在全域
_G.techniques_def = {}   -- key = technique id, value = 定義表格
```

### 2.3 單一連技定義結構

```lua
{
    id          = "T_SWIFT_SLASH",   -- 自動產生（"T_" + short_name）
    name        = "迅斬",
    short_name  = "SWIFT_SLASH",
    type        = "starter",         -- starter / linker / finisher / free
    ki_cost     = 10,                -- 消耗氣值
    cooldown    = 3,                 -- 冷卻（回合數）
    -- 熟練度：0（剛習得）→ 1.0（完全熟練）
    -- 影響效果公式
    action      = function(self, t, combo)
        -- self = Actor, t = 連技定義, combo = 當前連擊計數
    end,
    info        = function(self, t)
        return "說明文字"
    end,
}
```

---

## 3. ActorTechnique 混入

這是核心模組，管理所有連技狀態：

```lua
-- game/modules/hellodungeon/class/interface/ActorTechnique.lua

require "engine.class"

module(..., package.seeall, class.make)

-- ═══════════════════════════════════════════════════
-- 初始化
-- ═══════════════════════════════════════════════════

function _M:initTechniques(t)
    self.techniques = t.techniques or {
        slots = {nil, nil, nil, nil, nil},
        known = {},
        cooldowns = {},
    }
    self.combo_state = {
        count  = 0,
        timer  = 0,
        active = false,
    }
end

-- ═══════════════════════════════════════════════════
-- 連技習得
-- ═══════════════════════════════════════════════════

--- 習得一個連技
function _M:learnTechnique(id)
    if not techniques_def[id] then
        error("[Technique] 未知連技 ID: "..tostring(id))
        return false
    end
    if self.techniques.known[id] then
        game.logPlayer(self, "你已經知道「%s」了。", techniques_def[id].name)
        return false
    end
    self.techniques.known[id] = { proficiency = 0, uses = 0 }
    game.logPlayer(self, "#YELLOW#你習得了新連技：「%s」！", techniques_def[id].name)
    return true
end

--- 是否已習得
function _M:knowsTechnique(id)
    return self.techniques.known[id] ~= nil
end

-- ═══════════════════════════════════════════════════
-- 槽位管理
-- ═══════════════════════════════════════════════════

--- 將連技裝填到指定槽位
function _M:setTechniqueSlot(slot, id)
    assert(slot >= 1 and slot <= 5, "槽位必須是 1~5")
    if id and not self:knowsTechnique(id) then
        game.logPlayer(self, "你還不知道這個連技。")
        return false
    end
    self.techniques.slots[slot] = id
    self.changed = true
    return true
end

--- 取得指定槽位的連技定義
function _M:getTechniqueInSlot(slot)
    local id = self.techniques.slots[slot]
    return id and techniques_def[id]
end

-- ═══════════════════════════════════════════════════
-- 使用連技
-- ═══════════════════════════════════════════════════

--- 檢查是否可以使用這個連技
function _M:canUseTechnique(t)
    if not t then return false, "連技不存在" end
    -- 冷卻中
    if self.techniques.cooldowns[t.id] and self.techniques.cooldowns[t.id] > 0 then
        return false, ("冷卻中：%d 回合"):format(self.techniques.cooldowns[t.id])
    end
    -- 氣值不足
    local ki = self:getResource("ki") or 0
    if ki < t.ki_cost then
        return false, ("氣值不足（需要 %d，現有 %d）"):format(t.ki_cost, ki)
    end
    -- 狀態限制
    if t.type == "linker" or t.type == "finisher" then
        if not self.combo_state.active then
            return false, "需要先建立連擊（使用起手技）"
        end
    end
    return true
end

--- 使用槽位中的連技
function _M:useTechniqueInSlot(slot)
    local t = self:getTechniqueInSlot(slot)
    if not t then
        game.logPlayer(self, "槽位 %d 沒有連技。", slot)
        return false
    end
    local ok, reason = self:canUseTechnique(t)
    if not ok then
        game.logPlayer(self, "#RED#無法使用「%s」：%s", t.name, reason)
        return false
    end

    -- 消耗資源
    self:incResource("ki", -t.ki_cost)

    -- 設定冷卻
    self.techniques.cooldowns[t.id] = t.cooldown or 0

    -- 執行效果
    local combo_before = self.combo_state.count
    local result = t.action(self, t, self.combo_state.count)

    -- 更新連擊狀態
    if result ~= false then
        self:updateComboState(t)
    end

    -- 熟練度提升
    self:gainTechniqueProficiency(t.id, 1)

    -- 消耗一個行動
    self:useEnergy()
    return true
end

-- ═══════════════════════════════════════════════════
-- 連擊狀態管理
-- ═══════════════════════════════════════════════════

--- 使用連技後更新連擊狀態
function _M:updateComboState(t)
    if t.type == "starter" then
        self.combo_state.active = true
        self.combo_state.count  = self.combo_state.count + 1
        self.combo_state.timer  = 3  -- 3 回合內不行動就清空
    elseif t.type == "linker" then
        self.combo_state.count = self.combo_state.count + 1
        self.combo_state.timer = 3
    elseif t.type == "finisher" then
        -- 終結技清空連擊
        self.combo_state.active = false
        self.combo_state.count  = 0
        self.combo_state.timer  = 0
    elseif t.type == "free" then
        -- 不影響連擊狀態
        if self.combo_state.active then
            self.combo_state.timer = 3  -- 重置計時
        end
    end
    self.changed = true
end

--- 每回合呼叫（倒數連擊計時器）
function _M:techniqueTurn()
    -- 更新冷卻
    for id, cd in pairs(self.techniques.cooldowns) do
        if cd > 0 then
            self.techniques.cooldowns[id] = cd - 1
        end
    end
    -- 連擊超時
    if self.combo_state.active then
        self.combo_state.timer = self.combo_state.timer - 1
        if self.combo_state.timer <= 0 then
            self.combo_state.active = false
            self.combo_state.count  = 0
            game.logPlayer(self, "#GREY#連擊中斷。")
        end
    end
    self.changed = true
end

-- ═══════════════════════════════════════════════════
-- 熟練度
-- ═══════════════════════════════════════════════════

--- 使用連技後增加熟練度
-- proficiency 範圍：0~100（100 = 完全熟練）
function _M:gainTechniqueProficiency(id, amount)
    local entry = self.techniques.known[id]
    if not entry then return end
    entry.uses = (entry.uses or 0) + 1
    -- 越熟練漲得越慢（邊際遞減）
    local gain = amount * (1 - entry.proficiency / 120)
    entry.proficiency = math.min(100, (entry.proficiency or 0) + gain)
end

--- 取得熟練度（0.0~1.0）
function _M:getTechniqueProficiency(id)
    local entry = self.techniques.known[id]
    if not entry then return 0 end
    return (entry.proficiency or 0) / 100
end
```

在 `Actor.lua` 中整合：

```lua
-- class/Actor.lua

local ActorTechnique = require "mod.class.interface.ActorTechnique"

module(..., package.seeall, class.inherit(
    Actor,
    -- ... 其他混入 ...
    ActorTechnique      -- ← 加入
))

function _M:init(t, no_default)
    -- ... 其他 init ...
    ActorTechnique.initTechniques(self, t)

    -- 加入氣（Ki）資源
    -- （需要在 load.lua 中 ActorResource:defineResource("Ki", "ki", ...)）
    self.max_ki = t.max_ki or 60
    self.ki     = t.ki or self.max_ki
    self.ki_regen = t.ki_regen or 3  -- 每回合回復 3 點
end

function _M:act()
    if not Actor.act(self) then return end
    self:techniqueTurn()  -- ← 每回合更新連技冷卻和連擊計時
    -- 氣值回復
    self:incResource("ki", self.ki_regen or 3)
    self:timedEffects()
    self:useEnergy()
end
```

---

## 4. 連技定義檔格式

```lua
-- game/modules/hellodungeon/data/techniques/slash.lua

-- ═══════════════════════════════════════════════════
-- 全域定義函數（類似 newTalent 的 newTechnique）
-- ═══════════════════════════════════════════════════

-- 在 load.lua 中定義這個函數：
-- function newTechnique(t)
--     t.short_name = t.short_name or t.name:upper():gsub(" ", "_")
--     t.id = "T_TECH_" .. t.short_name
--     techniques_def[t.id] = t
-- end

newTechnique{
    name       = "迅斬",
    short_name = "SWIFT_SLASH",
    type       = "starter",
    ki_cost    = 8,
    cooldown   = 2,
    -- display：在 HUD 槽位中顯示的符號（若無圖檔）
    display    = "/",
    color      = {100, 200, 255},

    action = function(self, t, combo)
        -- 取得目標（相鄰格）
        local tg = {type="hit", range=1}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return false end  -- 取消使用

        -- 傷害 = 基礎攻擊 × (0.8 + 熟練度 × 0.4)
        local prof = self:getTechniqueProficiency(t.id)
        local dam  = self:combatDamage() * (0.8 + prof * 0.4)

        self:project(tg, x, y, engine.DamageType.PHYSICAL, dam)
        game.logSeen(self, "%s 迅斬！", self:getName():capitalize())
        return true
    end,

    info = function(self, t)
        local prof = self:getTechniqueProficiency(t.id)
        local dam  = self:combatDamage() * (0.8 + prof * 0.4)
        return ("快速斬擊，造成 %.0f 傷害，建立第一個連擊計數。\n"..
               "熟練度：%.0f%%（熟練後傷害最高可達攻擊力的 1.2 倍）"):format(
               dam, prof * 100)
    end,
}
```

---

## 5. 五個範例連技

```lua
-- game/modules/hellodungeon/data/techniques/combo.lua

-- ── 1. 迅斬（起手）────────────────────────────────
newTechnique{
    name = "迅斬", short_name = "SWIFT_SLASH",
    type = "starter", ki_cost = 8, cooldown = 2,
    display = "╱", color = {150, 200, 255},
    action = function(self, t, combo)
        local tg = {type="hit", range=1}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return false end
        local prof = self:getTechniqueProficiency(t.id)
        local dam  = self:combatDamage() * (0.8 + prof * 0.4)
        self:project(tg, x, y, engine.DamageType.PHYSICAL, dam)
        game.logSeen(self, "%s 迅斬！（連擊 +1）",
            self:getName():capitalize())
        return true
    end,
    info = function(self, t)
        return ("快速斬擊，建立連擊。傷害 = 攻擊力 × %.1f"):format(
               0.8 + self:getTechniqueProficiency(t.id) * 0.4)
    end,
}

-- ── 2. 踏步切（起手）─────────────────────────────
newTechnique{
    name = "踏步切", short_name = "STEP_CUT",
    type = "starter", ki_cost = 12, cooldown = 3,
    display = "→", color = {255, 220, 100},
    action = function(self, t, combo)
        local tg = {type="hit", range=2}  -- 更長射程
        local x, y, target = self:getTarget(tg)
        if not x or not target then return false end
        local dam = self:combatDamage() * 1.0
        self:project(tg, x, y, engine.DamageType.PHYSICAL, dam)
        -- 踏步：玩家移動到目標旁邊（teleport adjacent）
        local tx, ty = util.adjacentCoord(x, y, self.x, self.y)
        if tx and not game.level.map:checkEntity(tx, ty, engine.Map.TERRAIN, "block_move") then
            self:move(tx, ty, true)
        end
        game.logSeen(self, "%s 踏步切！", self:getName():capitalize())
        return true
    end,
    info = function(self, t)
        return "踏步衝刺後斬擊，射程 2 格，並移動到目標旁邊。\n建立連擊計數。"
    end,
}

-- ── 3. 旋風斬（中繼）─────────────────────────────
newTechnique{
    name = "旋風斬", short_name = "SPIN_SLASH",
    type = "linker", ki_cost = 15, cooldown = 4,
    display = "✦", color = {100, 255, 180},
    action = function(self, t, combo)
        -- 中繼技：hit all adjacent
        local tg = {type="ball", radius=1, selffire=false}
        local dam = self:combatDamage() * (0.6 + combo * 0.1)
        self:project(tg, self.x, self.y, engine.DamageType.PHYSICAL, dam)
        game.logSeen(self, "%s 旋風斬！（連擊計數 %d，傷害倍率 %.1f×）",
            self:getName():capitalize(), combo,
            (0.6 + combo * 0.1))
        return true
    end,
    info = function(self, t)
        return ("對周圍所有敵人造成攻擊，需要先建立連擊。\n"..
               "傷害隨連擊計數增加（每層 +10%%）。")
    end,
}

-- ── 4. 穿甲刺（中繼）─────────────────────────────
newTechnique{
    name = "穿甲刺", short_name = "ARMOR_PIERCE",
    type = "linker", ki_cost = 18, cooldown = 5,
    display = "▶", color = {255, 120, 80},
    action = function(self, t, combo)
        local tg = {type="hit", range=1}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return false end

        -- 臨時降低目標護甲（持續 2 回合）
        local reduce = 5 + combo * 3
        local id = target:addTemporaryValue("combat_armor", -reduce)
        -- 計畫在 2 回合後移除（使用 setEffect 更優雅，這裡簡化）
        -- TODO: 完整版應使用 ActorTemporaryEffects

        local dam = self:combatDamage() * 0.9
        self:project(tg, x, y, engine.DamageType.PHYSICAL, dam)
        game.logSeen(self, "%s 穿甲刺！降低目標護甲 %d 點。",
            self:getName():capitalize(), reduce)
        return true
    end,
    info = function(self, t)
        return ("刺穿目標護甲，降低其護甲值。連擊越高降低越多。\n需要已有連擊計數。")
    end,
}

-- ── 5. 斬裂衝（終結）─────────────────────────────
newTechnique{
    name = "斬裂衝", short_name = "BURST_CLEAVE",
    type = "finisher", ki_cost = 25, cooldown = 8,
    display = "★", color = {255, 60, 60},
    action = function(self, t, combo)
        local tg = {type="hit", range=1}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return false end

        -- 終結技：連擊數越高，額外傷害乘數越大
        -- combo=1 → 1.5×, combo=2 → 2.0×, combo=5 → 3.5×
        local multiplier = 1.0 + combo * 0.5
        local dam        = self:combatDamage() * multiplier

        -- 視覺效果（若有粒子系統）
        -- game.level.map:particleEmitter(x, y, 1, "blood")

        self:project(tg, x, y, engine.DamageType.PHYSICAL, dam)
        game.logSeen(self, "#CRIMSON#%s 斬裂衝！%d 連擊，%.1f 倍傷害！#LAST#",
            self:getName():capitalize(), combo, multiplier)

        -- 終結技特效：回復一定氣值（獎勵完整連擊）
        if combo >= 3 then
            self:incResource("ki", combo * 3)
            game.logPlayer(self, "完整連擊！回復 %d 點氣。", combo * 3)
        end

        return true
    end,
    info = function(self, t)
        return ("連擊終結技。傷害 = 攻擊力 × (1.0 + 連擊數 × 0.5)。\n"..
               "3 連擊以上追加回復氣值。\n"..
               "需要先建立至少 1 個連擊計數。")
    end,
}
```

---

## 6. 連技 HUD（橫條顯示器）

這是與現有技能樹 UI 最大的差異點。我們建立一個**常駐橫條**，顯示 5 個槽位和連擊狀態：

```lua
-- game/modules/hellodungeon/class/ui/TechniqueBar.lua

require "engine.class"

module(..., package.seeall, class.make)

local SLOT_W = 80    -- 每個槽位寬度（像素）
local SLOT_H = 50    -- 槽位高度
local SLOT_PAD = 4   -- 槽位間距
local COMBO_W = 120  -- 連擊計數區寬度

--- 建立連技橫條
-- @param x, y 左上角座標（通常貼近螢幕底部）
-- @param actor 玩家 Actor
function _M:init(actor, x, y)
    self.actor = actor
    self.display_x = x
    self.display_y = y
    -- 總寬度：5槽位 + 連擊區
    self.w = (SLOT_W + SLOT_PAD) * 5 + COMBO_W
    self.h = SLOT_H + 20  -- 20 像素給文字標籤

    -- 字型
    self.font = core.display.newFont("/data/font/DroidSans.ttf", 11)
    self.font_h = self.font:lineSkip()

    -- 快取 surface
    self.surface = core.display.newSurface(self.w, self.h)
    self.texture = nil
    self.texture_w, self.texture_h = 0, 0
end

--- 重新繪製 surface（僅在 actor.changed 時）
function _M:display()
    local a = self.actor
    if not a or not a.changed then return end

    -- 清空背景（半透明黑）
    self.surface:erase(20, 20, 20)

    -- ── 繪製 5 個槽位 ─────────────────────────────────
    for slot = 1, 5 do
        local sx = (slot - 1) * (SLOT_W + SLOT_PAD)
        local t  = a:getTechniqueInSlot(slot)

        -- 槽位外框
        local border_r, border_g, border_b = 80, 80, 80
        if t then
            -- 有連技：依類型顯示不同框色
            if t.type == "starter"  then border_r, border_g, border_b = 60, 120, 220 end
            if t.type == "linker"   then border_r, border_g, border_b = 60, 200, 120 end
            if t.type == "finisher" then border_r, border_g, border_b = 220, 60, 60  end
            if t.type == "free"     then border_r, border_g, border_b = 180, 180, 60 end
        end
        -- 外框（1 像素邊框用四個矩形模擬）
        self.surface:drawRect(sx, 0, SLOT_W, SLOT_H, border_r, border_g, border_b)
        self.surface:drawRect(sx+1, 1, SLOT_W-2, SLOT_H-2, 25, 25, 35)

        if t then
            -- 冷卻遮罩
            local cd = a.techniques.cooldowns[t.id] or 0
            if cd > 0 then
                -- 半透明黑色覆蓋
                self.surface:drawRect(sx+1, 1, SLOT_W-2, SLOT_H-2, 0, 0, 0)
                -- 冷卻數字
                local cds = tostring(cd)
                local tw, th = self.font:size(cds)
                local tex = self.font:draw(cds, SLOT_W, 255, 80, 80)[1]
                self.surface:merge(tex._tex_data or tex, sx + (SLOT_W - tw) / 2, (SLOT_H - th) / 2)
            else
                -- 顯示連技符號（或名稱縮寫）
                local sym = t.display or t.name:sub(1,2)
                local cr, cg, cb = table.unpack(t.color or {200, 200, 200})
                local tex = self.font:draw(sym, SLOT_W, cr, cg, cb)[1]
                local tw, th = self.font:size(sym)
                self.surface:merge(tex._tex_data or tex, sx + (SLOT_W - tw) / 2, (SLOT_H - th) / 2)
            end

            -- 槽位編號（左上角小字）
            local num_tex = self.font:draw(tostring(slot), 20, 150, 150, 150)[1]
            self.surface:merge(num_tex._tex_data or num_tex, sx + 3, 2)

            -- 技能名稱（底部小字）
            local short_name = t.name:sub(1, 4)  -- 最多 4 字
            local nm_tex = self.font:draw(short_name, SLOT_W, 200, 200, 200)[1]
            self.surface:merge(nm_tex._tex_data or nm_tex, sx + 2, SLOT_H - self.font_h - 1)
        else
            -- 空槽位標示
            local empty_tex = self.font:draw(tostring(slot).." --", SLOT_W, 60, 60, 60)[1]
            self.surface:merge(empty_tex._tex_data or empty_tex, sx + 5, SLOT_H / 2 - self.font_h / 2)
        end
    end

    -- ── 連擊狀態區 ────────────────────────────────────
    local cx = 5 * (SLOT_W + SLOT_PAD)
    local combo = a.combo_state

    -- 連擊計數背景（連擊中閃爍橙色）
    local bg_r, bg_g, bg_b = 30, 30, 30
    if combo.active then
        bg_r, bg_g, bg_b = 80, 50, 20
    end
    self.surface:drawRect(cx, 0, COMBO_W, SLOT_H, bg_r, bg_g, bg_b)

    -- 連擊數字（大字）
    local count_str = combo.active and tostring(combo.count) or "0"
    local cr, cg, cb = combo.active and 255 or 80, combo.active and 150 or 80, combo.active and 0 or 80
    local big_font = core.display.newFont("/data/font/DroidSans-Bold.ttf", 22)
    local count_tex = big_font:draw(count_str, COMBO_W, cr, cg, cb)[1]
    local ctw = big_font:size(count_str)
    self.surface:merge(count_tex._tex_data or count_tex,
        cx + (COMBO_W - ctw) / 2, 4)

    -- 「連擊」標籤
    local label = combo.active
        and ("COMBO  ⏱%d"):format(combo.timer)
        or  "COMBO"
    local label_tex = self.font:draw(label, COMBO_W, 160, 160, 160)[1]
    self.surface:merge(label_tex._tex_data or label_tex, cx + 5, SLOT_H - self.font_h - 1)

    -- 更新 GL 紋理
    self.texture, self.texture_w, self.texture_h = self.surface:glTexture()
end

--- 渲染到螢幕
function _M:toScreen()
    self:display()
    if self.texture then
        self.texture:toScreenFull(
            self.display_x, self.display_y,
            self.w, self.h,
            self.texture_w, self.texture_h
        )
    end
end

--- 滑鼠點擊（傳入的是絕對螢幕座標）
function _M:mouseEvent(button, mx, my)
    -- 轉換為相對座標
    local rx = mx - self.display_x
    local ry = my - self.display_y
    if rx < 0 or ry < 0 or rx > self.w or ry > self.h then return false end

    -- 判斷點的是哪個槽位
    for slot = 1, 5 do
        local sx = (slot - 1) * (SLOT_W + SLOT_PAD)
        if rx >= sx and rx < sx + SLOT_W then
            if button == "left" then
                -- 左鍵：使用此槽位的連技
                self.actor:useTechniqueInSlot(slot)
            elseif button == "right" then
                -- 右鍵：顯示連技說明
                self:showTechniqueTooltip(slot, mx, my)
            end
            return true
        end
    end
    return false
end

--- 顯示工具提示
function _M:showTechniqueTooltip(slot, x, y)
    local t = self.actor:getTechniqueInSlot(slot)
    if not t then return end
    local Dialog = require "engine.ui.Dialog"
    local Textzone = require "engine.ui.Textzone"
    local info = t.info and t:info(self.actor, t) or t.name
    local prof = self.actor:getTechniqueProficiency(t.id)
    local full_text = ("#YELLOW#%s#LAST# [%s]\n"):format(t.name, t.type)..
                      ("氣耗：%d  冷卻：%d 回合\n"):format(t.ki_cost, t.cooldown)..
                      ("熟練度：%.0f%%\n\n"):format(prof * 100)..
                      info
    local d = Dialog.new(t.name, 300, 200)
    local tz = Textzone.new{width=d.iw, height=d.ih, text=full_text}
    d:loadUI{{left=0, top=0, ui=tz}}
    d:setupUI()
    game:registerDialog(d)
end
```

> **注意**：`surface:drawRect`、`surface:merge`、`font:draw` 這些是 TE4 的 C 層 SDL surface API。實際渲染時，`font:draw` 回傳的物件結構依引擎版本略有差異；上面的程式碼以 te4-1.7.6 的標準 API 為準，可能需要根據實際回傳值微調 `_tex_data` 或 `_tex` 欄位名稱。

---

## 7. 整合到 Game.lua 與 Player.lua

### 7.1 在 Game.lua 中建立 HUD 並渲染

```lua
-- game/modules/hellodungeon/class/Game.lua

function _M:run()
    -- ... 原有初始化 ...

    -- 建立連技橫條（放在螢幕底部中央）
    local TechniqueBar = require "mod.class.ui.TechniqueBar"
    local bar_w = (80 + 4) * 5 + 120  -- 與 TechniqueBar 的常數一致
    local bar_x = (self.w - bar_w) / 2
    local bar_y = self.h - 80         -- 距離底部 80 像素
    self.technique_bar = TechniqueBar.new(self.player, bar_x, bar_y)

    -- ... 繼續其他初始化 ...
end

function _M:display(nb_keyframe)
    -- ... 其他繪製 ...

    -- 繪製連技橫條（放在地圖和其他 HUD 之後）
    if self.technique_bar then
        self.technique_bar:toScreen()
    end

    -- ... 其他繪製 ...
end

-- 在滑鼠事件處理中轉發點擊
function _M:mouseEvent(button, mx, my, xrel, yrel)
    if self.technique_bar and self.technique_bar:mouseEvent(button, mx, my) then
        return  -- 橫條消化了這個點擊
    end
    -- ... 其他滑鼠事件處理 ...
end
```

### 7.2 在 Player.lua 加入數字鍵 1~5 直接使用槽位

```lua
-- game/modules/hellodungeon/class/Game.lua（setupCommands 中）

-- 數字鍵 1~5：使用對應槽位的連技
for slot = 1, 5 do
    local s = slot  -- 閉包捕獲
    self.key:addCommands{
        [{"_"..tostring(s), shift=false}] = function()
            if self.player then
                self.player:useTechniqueInSlot(s)
            end
        end,
    }
end

-- T 鍵：開啟連技管理介面（槽位裝填）
self.key:addCommands{
    [{"_t"}] = function()
        if self.player then
            self:showTechniqueManagement()
        end
    end,
}
```

### 7.3 連技管理介面（槽位裝填）

```lua
-- game/modules/hellodungeon/class/Game.lua

function _M:showTechniqueManagement()
    local Dialog = require "engine.ui.Dialog"
    local List = require "engine.ui.List"
    local Textzone = require "engine.ui.Textzone"

    local p = self.player
    local d = Dialog.new("連技管理", 600, 400)

    -- 左側：已習得的連技清單
    local known_list = {}
    for id, entry in pairs(p.techniques.known) do
        local t = techniques_def[id]
        if t then
            known_list[#known_list+1] = {
                id   = id,
                name = ("%s [%s] 熟練:%.0f%%"):format(
                    t.name, t.type, entry.proficiency),
                def  = t,
            }
        end
    end
    table.sort(known_list, function(a, b) return a.name < b.name end)

    -- 右側：目前槽位狀態
    local slot_list = {}
    for i = 1, 5 do
        local t = p:getTechniqueInSlot(i)
        slot_list[#slot_list+1] = {
            slot = i,
            name = ("槽位 %d：%s"):format(i, t and t.name or "（空白）"),
        }
    end

    local selected_technique = nil

    local c_known = List.new{width=260, height=d.ih-40,
        list = known_list,
        fct = function(item) selected_technique = item end,
    }
    local c_slots = List.new{width=260, height=d.ih-40,
        list = slot_list,
        fct = function(item)
            if selected_technique then
                -- 將選中的連技放入此槽位
                p:setTechniqueSlot(item.slot, selected_technique.id)
                -- 更新槽位清單文字
                item.name = ("槽位 %d：%s"):format(
                    item.slot, selected_technique.def.name)
                c_slots:regenList()
                selected_technique = nil
            end
        end,
    }

    d:loadUI{
        {left=0,  top=0, ui=c_known},
        {right=0, top=0, ui=c_slots},
    }
    d:setupUI()

    -- 提示文字
    d.key:addCommands{
        _DELETE = function()
            -- 在槽位清單選中時，按 Delete 清空
            local sel = c_slots.sel
            if sel then
                p:setTechniqueSlot(slot_list[sel].slot, nil)
                slot_list[sel].name = ("槽位 %d：（空白）"):format(slot_list[sel].slot)
                c_slots:regenList()
            end
        end,
    }
    game:registerDialog(d)
end
```

---

## 8. 連技的取得方式

### 8.1 作為掉落物（Object）

連技捲軸是一種消耗品，使用後習得連技：

```lua
-- data/general/objects/technique_scrolls.lua

newEntity{
    define_as = "BASE_TECHNIQUE_SCROLL",
    type = "scroll", subtype = "technique",
    display = "?", color = colors.CYAN,
    stacking = false,   -- 每個捲軸都是唯一的
    rarity = 8,
    desc = "記載著某種連技的羊皮紙卷。",
    use_simple = {
        name = "研讀連技捲軸",
        use = function(self, who)
            if not self.technique_id then return {used=false} end
            if who:knowsTechnique(self.technique_id) then
                game.logPlayer(who, "你已經知道這個連技了。")
                return {used=false}
            end
            who:learnTechnique(self.technique_id)
            return {used=true, id=true}
        end,
    },
}

newEntity{ base = "BASE_TECHNIQUE_SCROLL",
    name = "迅斬秘笈",
    technique_id = "T_TECH_SWIFT_SLASH",
    level_range = {1, 5},
    rarity = 5,
    color = colors.LIGHT_BLUE,
    desc = "記載「迅斬」連技的入門秘笈。",
}

newEntity{ base = "BASE_TECHNIQUE_SCROLL",
    name = "斬裂衝真傳",
    technique_id = "T_TECH_BURST_CLEAVE",
    level_range = {6, 20},
    rarity = 15,
    color = colors.CRIMSON,
    desc = "記載終極連技「斬裂衝」的稀有典籍。",
}
```

### 8.2 訓練師 NPC

在城鎮加入一個訓練師 NPC，提供付費學習：

```lua
-- data/zones/town/npcs.lua

newEntity{
    define_as = "TRAINER",
    name = "連技訓練師 Wu",
    display = "T", color = colors.LIGHT_GREEN,
    ai = "simple", never_move = 1,
    chat = "trainer",  -- data/chats/trainer.lua
    rarity = false,
}
```

```lua
-- data/chats/trainer.lua

newChat{ id="welcome",
    text = "我可以傳授你連技。你想學什麼？",
    answers = {
        {
            "教我「迅斬」（費用：50 金）",
            cond = function(npc, player)
                return not player:knowsTechnique("T_TECH_SWIFT_SLASH")
            end,
            action = function(npc, player)
                if (player.money or 0) < 50 then
                    game.logPlayer(player, "金幣不足。")
                    return
                end
                player.money = player.money - 50
                player:learnTechnique("T_TECH_SWIFT_SLASH")
            end,
        },
        { "再見。" },
    }
}

return "welcome"
```

### 8.3 戰鬥中頓悟（事件觸發）

在 Actor 的 `attackTarget` 中，有機率在擊殺後習得連技：

```lua
-- class/interface/Combat.lua

function _M:attackTarget(target)
    local hit, dam = -- ... 原有攻擊邏輯 ...

    if target.dead and rng.percent(5) then  -- 5% 機率頓悟
        -- 隨機選一個未習得的連技
        local candidates = {}
        for id, t in pairs(techniques_def) do
            if not self:knowsTechnique(id) then
                candidates[#candidates+1] = id
            end
        end
        if #candidates > 0 then
            local id = rng.table(candidates)
            game.logPlayer(self, "#GOLD#在激戰中，你頓悟了「%s」！",
                techniques_def[id].name)
            self:learnTechnique(id)
        end
    end
end
```

---

## 9. 熟練度系統

熟練度（0%~100%）影響連技效果，透過使用累積：

### 9.1 熟練度影響效果的標準公式

```lua
-- 在每個 action 函數中使用：
local prof = self:getTechniqueProficiency(t.id)  -- 0.0~1.0
local dam = base_dam * (1 + prof)
-- prof=0（剛學）：1.0× 傷害
-- prof=1（完全熟練）：2.0× 傷害
```

### 9.2 熟練度進度顯示

在 `showTechniqueManagement` 或工具提示中顯示進度條：

```lua
-- 以文字模擬進度條（10 格）
local function profBar(prof)
    local filled = math.floor(prof * 10)
    return ("[%s%s]"):format(
        string.rep("█", filled),
        string.rep("░", 10 - filled)
    )
end
-- 使用：("熟練 %s %.0f%%"):format(profBar(prof), prof*100)
```

### 9.3 熟練度里程碑

可在 `gainTechniqueProficiency` 中加入里程碑提示：

```lua
function _M:gainTechniqueProficiency(id, amount)
    local entry = self.techniques.known[id]
    if not entry then return end

    local before = math.floor(entry.proficiency / 25)  -- 0~3
    local gain = amount * (1 - entry.proficiency / 120)
    entry.proficiency = math.min(100, entry.proficiency + gain)
    local after = math.floor(entry.proficiency / 25)

    -- 每 25% 一個里程碑
    if after > before then
        local milestones = {
            [1] = "入門", [2] = "熟練", [3] = "精通", [4] = "完美"
        }
        local t = techniques_def[id]
        game.logPlayer(self, "#YELLOW#「%s」熟練度提升：%s！",
            t.name, milestones[after] or "完美")
    end
end
```

---

## 10. 完整檔案結構

```
game/modules/hellodungeon/
│
├── load.lua                    ← 修改：定義 newTechnique()、載入連技、定義 ki 資源
│
├── class/
│   ├── Actor.lua               ← 修改：繼承 ActorTechnique，initTechniques
│   ├── Game.lua                ← 修改：建立 technique_bar，數字鍵綁定，showTechniqueManagement
│   └── interface/
│       └── ActorTechnique.lua  ← 新增：連技混入（initTechniques/learnTechnique/useTechniqueInSlot 等）
│
├── class/ui/
│   └── TechniqueBar.lua        ← 新增：連技橫條 HUD
│
└── data/
    ├── techniques/             ← 新增目錄
    │   └── combo.lua           ← 新增：五個連技定義
    ├── general/
    │   └── objects/
    │       └── technique_scrolls.lua  ← 新增：連技捲軸物品
    ├── chats/
    │   └── trainer.lua         ← 新增：訓練師對話
    └── zones/
        └── town/
            └── npcs.lua        ← 修改：加入訓練師 NPC
```

在 `load.lua` 加入：

```lua
-- load.lua

-- 定義氣（Ki）資源
ActorResource:defineResource("Ki", "ki", "max_ki", "ki_regen",
    "氣是使用連技的能量，每回合自然回復。")

-- 定義全域連技表與 newTechnique 函數
_G.techniques_def = {}
function newTechnique(t)
    t.short_name = t.short_name or t.name:upper():gsub("[%s'%-]", "_")
    t.id = "T_TECH_" .. t.short_name
    assert(not techniques_def[t.id],
        "連技已存在：" .. t.id)
    techniques_def[t.id] = t
end

-- 載入所有連技定義
dofile("/data/techniques/combo.lua")
```

---

## 11. 常見錯誤排查

### 錯誤：`attempt to call nil value (global 'newTechnique')`

**原因**：`newTechnique` 尚未定義就執行了 `dofile`。

**解法**：確認 `load.lua` 中定義 `newTechnique` 的程式碼**在** `dofile` 之前執行。

---

### 錯誤：HUD 不顯示（畫面上看不到橫條）

**原因**：`Game:display()` 中沒有呼叫 `technique_bar:toScreen()`，或 `self.technique_bar` 是 nil。

**解法**：
1. 確認 `Game:run()` 有建立 `self.technique_bar`
2. 確認 `Game:display()` 的呼叫位置在地圖繪製**之後**（否則會被蓋住）
3. 檢查座標：`bar_y = self.h - 80` 是否在可見範圍內

---

### 錯誤：`linker`/`finisher` 技能顯示「需要先建立連擊」但連擊計數不是 0

**原因**：`combo_state.active` 沒有被設為 `true`，或 Actor 的 `act()` 忘記呼叫 `techniqueTurn()`（導致計時器沒有倒數、狀態沒有更新）。

**解法**：確認 `Actor:act()` 有呼叫 `self:techniqueTurn()`。

---

### 錯誤：`incResource("ki", ...)` 報錯

**原因**：`ActorResource` 的 `incResource` 需要資源名稱與 `defineResource` 的第二個參數（內部名稱）一致。

**解法**：確認 `defineResource("Ki", "ki", ...)` 和 `incResource("ki", ...)` 用的是同一個小寫名稱。

---

### 效能問題：HUD 每幀都重繪

**原因**：`actor.changed` 沒有在連技狀態改變後設為 `true`，導致 `display()` 的提早退出條件失效，反而每幀都進入繪製。

**解法**：確認在 `useTechniqueInSlot`、`updateComboState`、`techniqueTurn` 的末尾都有設定 `self.changed = true`，且在 `Game:display()` 的最後把 `self.player.changed = false` 重置。

---

## 小結

本教學實作了一個在 TE4 框架內、與現有技能樹**完全平行**的技能系統：

| 設計決策 | 原因 |
|----------|------|
| 獨立的 `techniques_def` | 不污染 `talents_def`，可獨立序列化 |
| `ActorTechnique` 混入 | 符合 TE4 混入慣例，可選擇性加入任何 Actor |
| 橫條 HUD 而非樹狀視窗 | 視覺上清楚傳達「順序性」設計哲學 |
| 連擊計數機制 | 讓玩家在一個回合內有策略性選擇（而非只是點技能） |
| 仍使用 `combatDamage()`/`project()` | 不需重寫戰鬥核心，新系統的傷害直接受現有裝備/屬性影響 |
