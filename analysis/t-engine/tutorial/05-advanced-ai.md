# 教學 05：進階 AI 系統

> **目標**：理解 TE4 的 AI 架構，從最簡單的移動 AI 到 ToME 的戰術評分系統（`improved_tactical`），並學會為你的 NPC 撰寫自訂 AI。
>
> **相關原始碼**：
> - `game/engines/engine/interface/ActorAI.lua` — AI 介面基礎（`doAI`、`runAI`、`newAI`）
> - `game/engines/engine/ai/simple.lua` — 引擎內建移動/目標 AI
> - `game/engines/engine/ai/talented.lua` — `dumb_talented`、`improved_talented`
> - `game/modules/tome-1.7.6/mod/ai/improved_tactical.lua` — ToME 戰術評分 AI（核心）
> - `game/modules/tome-1.7.6/mod/ai/target.lua` — ToME 目標選擇覆蓋

---

## 目錄

1. [AI 系統全局架構](#1-ai-系統全局架構)
2. [AI 的基本組件](#2-ai-的基本組件)
3. [引擎內建 AI 清單](#3-引擎內建-ai-清單)
4. [NPC 定義中的 AI 設定](#4-npc-定義中的-ai-設定)
5. [ai_state：AI 的記憶與設定](#5-ai_stateai-的記憶與設定)
6. [自訂簡單 AI](#6-自訂簡單-ai)
7. [技能的戰術表（tactical table）](#7-技能的戰術表-tactical-table)
8. [improved_tactical：三步評分系統](#8-improved_tactical三步評分系統)
9. [ai_tactic：NPC 的戰術偏好](#9-ai_tacticnpc-的戰術偏好)
10. [完整 NPC 範例：從簡單到進階](#10-完整-npc-範例從簡單到進階)
11. [自訂新戰術（Tactic）](#11-自訂新戰術-tactic)
12. [AI 除錯技巧](#12-ai-除錯技巧)
13. [常見問題](#13-常見問題)

---

## 1. AI 系統全局架構

TE4 的 AI 是**函式組合系統**（composable AI functions）。每個 AI 是一個具名函式，可以呼叫其他 AI，類似管線：

```
NPC:act()
  → self:computeFOV()          ← 先更新視野
  → self:doAI()               ← 主入口
      → self:runAI(self.ai)   ← 執行 NPC 指定的 AI
          → 可以再 runAI 其他 AI（組合）
```

**三層分工**：

```
目標選擇 AI        移動 AI              技能使用 AI
─────────────  +  ────────────  +  ──────────────────
target_simple      move_simple      dumb_talented
target_closest     move_dmap        improved_talented
target_player      move_astar       use_tactical
                   flee_simple      use_improved_tactical
                   flee_dmap
```

大多數頂層 AI（如 `simple`、`dumb_talented_simple`）會依序呼叫這三類 AI。

**AI 定義語法**：

```lua
-- 在 AI 定義檔中（engine/ai/*.lua 或 mod/ai/*.lua）
newAI("ai_name", function(self, ...)
    -- self = 這個 NPC Actor
    -- 回傳 true/false 表示是否成功行動
end)
```

**執行 AI**：

```lua
-- 在任何 Actor 方法中
self:runAI("ai_name")          -- 執行指定 AI
self:runAI("ai_name", arg1)    -- 帶參數
```

---

## 2. AI 的基本組件

### 2.1 AI 的狀態（ai_state 與 ai_target）

每個 NPC 都有兩個 AI 用的 table：

```lua
self.ai_state = {
    -- 靜態設定（在 NPC 定義中設定，存檔後保留）
    ai_target = "target_simple",   -- 目標選擇 AI 名稱
    ai_move   = "move_simple",     -- 移動 AI 名稱
    talent_in = 3,                 -- dumb_talented 的技能使用頻率（1/N 機率）
    no_talents = false,            -- 設為 true/1 則禁止使用技能
    -- 動態狀態（由 AI 在運行中修改）
    blocked_turns = nil,           -- move_complex 使用的卡住計數
    target_last_seen = {x, y, turn}, -- 最後一次看到目標的位置
}

self.ai_target = {
    actor = <Actor>,    -- 當前 AI 目標（弱引用，GC 不阻止）
}

self.ai_state_volatile = {
    -- 不存檔的揮發狀態（每次載入時重設）
    _want = {},     -- improved_tactical 的 WANT 表
    _avail = {},    -- improved_tactical 的 AVAIL 表
    _actions = {},  -- improved_tactical 的可行動列表
}
```

### 2.2 FOV（視野）

AI 執行前 NPC 必須先計算 FOV，才能知道能看到哪些 Actor：

```lua
-- NPC:act() 中（standard pattern）
self:computeFOV(self.sight or 20)  -- 計算視野半徑 20 格

-- 計算後可用
self.fov.actors_dist  -- 依距離排序的可見 Actor 列表
self.fov.actors[act]  -- actor → {sqdist=...} 的 table（sqdist = 距離平方）
```

### 2.3 目標追蹤：aiSeeTargetPos

AI 不總是能精確知道目標位置（目標可能在視線外）：

```lua
-- 取得 AI 認為目標在哪裡
local tx, ty = self:aiSeeTargetPos(self.ai_target.actor)
-- 目標在視線內 → 回傳精確座標
-- 目標在視線外 → 回傳帶誤差的估計位置（誤差隨時間增大）
```

這讓 NPC 的記憶系統更真實：失去視線 10 回合後，NPC 的目標位置估計誤差可達 10 格。

---

## 3. 引擎內建 AI 清單

### 目標選擇類

| AI 名稱 | 說明 |
|---------|------|
| `target_simple` | 找最近的敵人，90% 機率保持當前目標 |
| `target_closest` | 永遠鎖定最近的敵人（不保持當前目標）|
| `target_player` | 永遠以玩家為目標 |
| `target_player_radius` | 在 `ai_state.sense_radius` 格內攻擊玩家 |

**ToME 覆蓋版**（`mod/ai/target.lua`）的 `target_simple` 額外支援：
- 夜視（`infravision`）/ 增強感知（`heightened_senses`）
- 無敵目標跳過（`invulnerable`）
- 死亡召喚物轉攻擊召喚者

### 移動類

| AI 名稱 | 說明 | 特點 |
|---------|------|------|
| `move_simple` | 向目標最後已知位置直線移動 | 最快，但容易卡牆 |
| `move_dmap` | 使用 Dijkstra Map 找路 | 需要目標生成距離地圖 |
| `move_astar` | A* 尋路 | 最可靠，但計算量大 |
| `move_wander` | 隨機遊蕩 | 無目標時用 |
| `flee_simple` | 向相反方向逃跑 | 方向計算簡單 |
| `flee_dmap` | Dijkstra 逃跑 | 更可靠的逃跑 |
| `move_complex` | 智能複合移動 | A*/dmap/wander 按情況切換 |

### 技能使用類

| AI 名稱 | 說明 |
|---------|------|
| `dumb_talented` | 隨機使用一個可用技能（不智能）|
| `improved_talented` | 改良版：最多嘗試 5 次不同技能 |
| `dumb_talented_simple` | 目標選擇 + 1/N 機率用技能 + 移動（最常用基礎 AI）|
| `use_tactical` | 戰術評分系統（舊版）|
| `use_improved_tactical` | **戰術評分系統（新版，ToME 主要 NPC 使用）**|

### 複合頂層 AI

| AI 名稱 | 說明 |
|---------|------|
| `simple` | `target_simple` + `move_simple` |
| `dmap` | `target_simple` + `move_dmap` |
| `dumb_talented_simple` | target + 技能（1/N 機率）+ 移動 |
| `improved_tactical` | target + 技能（戰術評分）+ 移動（完整版）|

---

## 4. NPC 定義中的 AI 設定

NPC 的 AI 在實體定義中指定：

```lua
newEntity{
    name = "goblin archer",
    -- ...

    -- 設定主 AI（頂層入口）
    ai = "dumb_talented_simple",

    -- AI 的參數設定
    ai_state = {
        ai_target = "target_simple",   -- 目標選擇 AI（預設已是 target_simple）
        ai_move   = "move_simple",     -- 移動 AI（預設 move_simple）
        talent_in = 3,                 -- 平均每 3 回合用一次技能（1/3 機率）
    },
}
```

### 常用 ai 值與建議用途

| `ai` 值 | 適用 NPC 類型 |
|---------|-------------|
| `"dumb_talented_simple"` | 普通雜兵（隨機技能）|
| `"improved_tactical"` | 稀有/菁英（智能技能選擇）|
| `"move_simple"` | 純近戰移動怪（無技能）|
| `"none"` | 靜止不動（植物、水晶）|

---

## 5. ai_state：AI 的記憶與設定

`ai_state` 是 NPC 的 AI 記憶體，分兩類：

### 靜態設定（在 NPC 定義中設定）

```lua
ai_state = {
    -- 基本
    ai_target  = "target_simple",  -- 目標 AI（可改為 "target_closest" 等）
    ai_move    = "move_simple",    -- 移動 AI（可改為 "move_dmap" 等）
    talent_in  = 4,                -- dumb AI 用：平均每 N 回合使用技能
    no_talents = false,            -- true = 不用技能

    -- 戰術 AI 用
    self_compassion   = 5,  -- 自傷技能的懲罰係數（預設 5）
    ally_compassion   = 1,  -- 友傷技能的懲罰係數（預設 1）
    tactical_random_range = 0.5,  -- 隨機化幅度（預設 0.5）

    -- 進階移動
    sense_radius = 10,  -- target_player_radius 用的感知半徑
}
```

### 動態狀態（由 AI 在運行時修改）

```lua
-- 由 AI 自動寫入，不需手動設定
self.ai_state.target_last_seen = {x=10, y=20, turn=1500}
self.ai_state.blocked_turns    = 5   -- 被卡住的回合數
self.ai_state._fight_data      = {actions=10, attacks=7}  -- 戰鬥統計
```

---

## 6. 自訂簡單 AI

### 6.1 撰寫第一個自訂 AI

將 AI 定義放在你的模組的 AI 載入目錄中：

```lua
-- game/modules/mygame/mod/ai/custom.lua

-- 巡邏 AI：無目標時遊蕩，有目標時追擊
newAI("patrol_then_chase", function(self)
    -- 步驟 1：尋找目標
    if not self:runAI(self.ai_state.ai_target or "target_simple") then
        -- 沒有目標：隨機遊蕩
        self:runAI("move_wander")
        return
    end

    -- 步驟 2：有目標 → 追擊或使用技能
    if not self.energy.used then
        -- 先嘗試使用技能（1/5 機率）
        if rng.chance(5) then
            self:runAI("dumb_talented")
        end
        -- 若未行動，則移動接近目標
        if not self.energy.used then
            self:runAI(self.ai_state.ai_move or "move_simple")
        end
    end
end)
```

### 6.2 在 load.lua 中載入

```lua
-- game/modules/mygame/load.lua
local ActorAI = require "engine.interface.ActorAI"

-- 載入自訂 AI 定義
ActorAI:loadDefinition("/mod/ai/")
-- 如果也要引擎 AI，先載入引擎的
ActorAI:loadDefinition("/engine/ai/")
```

### 6.3 帶狀態的 AI（計數器、記憶）

```lua
newAI("rage_mode", function(self)
    -- 血量低於 30% 時切換到狂暴模式
    local hp_pct = self.life / self.max_life

    if hp_pct < 0.3 then
        -- 狂暴：永遠追擊，每回合必定使用技能
        if self:runAI("target_simple") then
            self:runAI("dumb_talented")   -- 嘗試用技能
            if not self.energy.used then
                self:runAI("move_simple") -- 沒用成功就移動
            end
        end
    else
        -- 普通模式
        self:runAI("dumb_talented_simple")
    end
end)
```

### 6.4 組合 AI：逃跑 + 技能

```lua
-- 玻璃砲 AI：受傷就跑，安全時狙擊
newAI("glass_cannon", function(self)
    if not self:runAI("target_simple") then return end

    local hp_pct = self.life / self.max_life
    local target = self.ai_target.actor
    local dist = target and core.fov.distance(self.x, self.y, target.x, target.y)

    if hp_pct < 0.5 then
        -- 血量低：逃跑
        self:runAI("flee_simple")
    elseif dist and dist <= 3 then
        -- 目標太近：先跑開
        self:runAI("flee_dmap")
    else
        -- 安全距離：使用遠程技能
        if not self:runAI("dumb_talented") then
            -- 沒有可用技能就等待（消耗 energy）
            self:useEnergy()
        end
    end
end)
```

---

## 7. 技能的戰術表（tactical table）

`tactical` 是讓**智能 AI**（`use_tactical`、`use_improved_tactical`）理解技能用途的關鍵。

### 7.1 基本格式

```lua
newTalent{
    name = "Fireball",
    -- ...

    -- 戰術表：告訴 AI 這個技能做什麼
    tactical = {
        TACTIC_NAME = weight,
        -- 或分細的傷害類型
        TACTIC_NAME = { DAMAGE_TYPE = weight },
    },
}
```

### 7.2 所有可用的戰術分類（Tactics）

#### 傷害類

| Tactic | 說明 | 典型值 |
|--------|------|--------|
| `attack` | 對一個目標傷害 | `{FIRE=2}` |
| `attackarea` | 對多個目標 AOE 傷害 | `{COLD=3}` |
| `attackall` | 傷害所有（大範圍）| `2` |

#### 生存類

| Tactic | 說明 | 典型值 |
|--------|------|--------|
| `heal` | 恢復生命值 | `2` |
| `cure` | 移除負面效果 | `2` |
| `defend` | 提升防禦/抗性 | `2` |
| `escape` | 增加與目標的距離 | `2` |

#### 戰略類

| Tactic | 說明 | 典型值 |
|--------|------|--------|
| `buff` | 增強自己或友軍 | `2` |
| `disable` | 控制/削弱目標 | `{stun=2}` |
| `closein` | 縮短與目標的距離 | `3` |
| `surrounded` | 被包圍時有用 | `3` |
| `protect` | 保護召喚者 | `3` |

#### 資源類

| Tactic | 說明 |
|--------|------|
| `stamina` | 恢復體力 |
| `mana` | 恢復魔力 |
| `ammo` | 補充彈藥 |
| `special` | 自訂（固定 want=1）|

### 7.3 戰術值的含義

戰術值代表技能在此戰術上的**效果強度**：

```lua
tactical = {
    attack = 2,      -- 標準攻擊強度（大多數攻擊用 2）
    attack = 4,      -- 強力攻擊（對 AI 更有吸引力）
    attack = 0.5,    -- 弱攻擊（附帶傷害）
}
```

**細分傷害類型（影響目標抗性計算）**：

```lua
tactical = {
    attack = { FIRE = 2 },        -- 火焰 AOE 攻擊
    attack = { PHYSICAL = 3 },    -- 物理重擊
    disable = { stun = 1, slow = 1 }, -- 暈眩+減速
}
```

當目標對火焰有高抗性時，AI 會降低這個技能的吸引力。

### 7.4 函式形式

戰術值也可以是函式，根據情況動態計算：

```lua
newTalent{
    name = "Chain Lightning",
    -- ...
    tactical = function(self, t, aitarget)
        -- 根據附近敵人數量決定戰術值
        local nb_foes = 0
        for _, act in ipairs(self.fov.actors_dist) do
            if self:reactionToward(act) < 0 then nb_foes = nb_foes + 1 end
        end
        return {
            attackarea = nb_foes >= 3 and 4 or 2,  -- 敵人多時更有吸引力
        }
    end,
}
```

### 7.5 實際範例

```lua
-- 治療技能
newTalent{
    name = "Minor Heal",
    tactical = { heal = 2 },          -- AI 在低血量時會使用
}

-- 火球（AOE）
newTalent{
    name = "Fireball",
    tactical = {
        attackarea = { FIRE = 2 },    -- 主要是 AOE 傷害
    },
}

-- 衝刺（靠近 + 攻擊）
newTalent{
    name = "Rush",
    tactical = {
        closein = 3,                   -- 主要用途：縮短距離
        attack = 1,                    -- 附帶傷害
    },
}

-- 屏障（純防禦）
newTalent{
    name = "Stone Skin",
    mode = "sustained",
    tactical = {
        defend = 2,                    -- 提升防禦
        buff = 1,                      -- 算作自身 buff
    },
}

-- 暈眩
newTalent{
    name = "Stunning Blow",
    tactical = {
        attack = { PHYSICAL = 1 },    -- 有傷害
        disable = { stun = 2 },       -- 主要用途：暈眩
    },
}

-- 傳送逃跑
newTalent{
    name = "Phase Door",
    tactical = {
        escape = 2,                   -- AI 在危急時使用
    },
}
```

---

## 8. improved_tactical：三步評分系統

這是 ToME 最進階的 AI，用於稀有/Boss NPC。理解它的三步計算：

### 8.1 三步流程

```
第一步：計算 TACTIC WEIGHT（每個技能對各戰術的貢獻值）
          ↓
第二步：計算 WANT VALUE（AI 當前對每個戰術的需求程度）
          ↓
第三步：計算 FINAL TACTICAL SCORE（得分 = WEIGHT × WANT × 偏好）
          → 選擇得分最高的技能執行
```

### 8.2 第一步：TACTIC WEIGHT

每個技能的 `tactical` 表經過處理後，變成 **TACTIC WEIGHT**（技能貢獻值）：

```lua
-- 原始 tactical 表
tactical = { attack = {FIRE=2}, disable = {stun=1} }

-- 引擎分析後，考慮目標的火焰抗性（-50%）：
tacts = { attack = 1.0, disable = 1.0 }
-- attack 從 2 降到 1（目標火焰抗 50%）
-- disable 保持 1（不受抗性影響）
```

**影響 TACTIC WEIGHT 的因素**：
- 目標對該傷害類型的抗性
- 技能打到的目標數量（AOE）
- 是否打到友軍（懲罰）
- 是否打到自己（由 `self_compassion` 懲罰）

### 8.3 第二步：WANT VALUE

**WANT** 代表 AI 對每個戰術的「渴望程度」（-10 到 +10），由 AI 自動計算：

| 戰術 | WANT 計算邏輯 | 典型值 |
|------|-------------|--------|
| `attack` | 固定 2，眩暈/麻痺時減半 | 1-2 |
| `heal` | 血量越低越高（血剩 40% 時約 4）| 0-10 |
| `cure` | 負面效果越多越高 | 0-10 |
| `defend` | 附近敵人越多越高 | 0.1-10 |
| `escape` | 血量 + 距離觸發（血剩 25% 時 ≈ 2）| -5 到 10 |
| `closein` | 距離遠於理想攻擊範圍時升高 | -10 到 2.5 |
| `disable` | 戰鬥持久度估計（打長了越高）| 0-10 |
| `buff` | 依攻擊機會和戰鬥長度動態計算 | 0.1 以上 |

**WANT 是自動算的**——你不需要手動設定（ai_tactic 除外）。

### 8.4 第三步：FINAL TACTICAL SCORE

```
RAW SCORE = Σ( TACTIC_WEIGHT[t] × WANT[t] × ai_tactic[t] )

FINAL SCORE = RAW SCORE × level_adjustment × random_range / speed
```

其中：
- `level_adjustment = 1 + talent_level × 0.2`（高等級技能得分更高）
- `random_range = 1 + (0.5 的隨機值)`（預設增加最多 50% 隨機性）
- `speed = 技能速度`（即時技能不懲罰速度）

**只有 FINAL SCORE > 0.1 的技能才會被考慮。**

### 8.5 完整示例計算

```
情境：火焰法師 NPC，血量剩 40%，目標在旁邊
技能：Fireball（tactical = {attackarea={FIRE=2}, escape=1}）

Step 1 - TACTIC WEIGHT：
  目標火焰抗性 = 0%（不影響）
  打到 3 個敵人
  tacts = {attackarea = 2.0, escape = 1.0}

Step 2 - WANT VALUE：
  want.attackarea = 2.0（基礎）
  want.escape = 3.2（血量 40% → want.life ≈ 8 → escape = 8/2-1 = 3）

Step 3 - FINAL TACTICAL SCORE：
  RAW = 2.0×2.0 + 1.0×3.2 = 4.0+3.2 = 7.2
  level_adjustment = 1 + 3×0.2 = 1.6（技能等級 3）
  random_range = 1.3（隨機）
  speed = 1.0
  FINAL = 7.2 × 1.6 × 1.3 / 1.0 = 14.98 ✓（選擇此技能！）
```

### 8.6 啟用 improved_tactical

```lua
-- 在 NPC 定義中
newEntity{
    name = "elite fire mage",
    ai = "improved_tactical",   -- 使用進階戰術 AI
    ai_state = {
        ai_target = "target_simple",
        ai_move   = "move_simple",
        self_compassion = 5,     -- 自傷懲罰（預設 5）
        ally_compassion = 1,     -- 友傷懲罰（預設 1）
        tactical_random_range = 0.3,  -- 降低隨機性（預設 0.5）
    },
    -- 技能必須有 tactical 表才會被此 AI 使用
    talents = { [T_FIREBALL]=3, [T_MANA_SHIELD]=1 },
}
```

---

## 9. ai_tactic：NPC 的戰術偏好

`ai_tactic` 是 NPC 的**個性設定**——乘以每個 WANT 值，讓 NPC 偏好特定戰術風格：

```lua
newEntity{
    name = "aggressive berserker",
    -- ...

    -- 乘數（預設 1，不影響）
    ai_tactic = {
        attack   = 3,   -- 攻擊欲望翻 3 倍（非常侵略性）
        escape   = 0,   -- 永不逃跑
        defend   = 0.5, -- 不太在乎防禦
        disable  = 2,   -- 喜歡控制技能

        -- 安全距離：低於此距離會觸發逃跑欲望
        safe_range = 4, -- 試圖保持在 4 格外（遠程 NPC 用）
    },
}
```

### 常見風格模板

#### 近戰侵略型

```lua
ai_tactic = {
    attack  = 3,
    closein = 2,
    escape  = 0,
    defend  = 0.5,
}
```

#### 遠程狙擊型

```lua
ai_tactic = {
    attack     = 2,
    escape     = 2,
    closein    = 0.5,
    safe_range = 5,   -- 保持 5 格距離
}
```

#### 支援治療型

```lua
ai_tactic = {
    heal    = 3,
    defend  = 2,
    attack  = 0.5,
    escape  = 2,
}
```

#### 控制削弱型

```lua
ai_tactic = {
    disable = 3,
    attack  = 1.5,
    buff    = 1,
}
```

#### Boss 型（多才多藝）

```lua
ai_tactic = {
    attack    = 2,
    disable   = 2,
    buff      = 2,
    heal      = 2,
    escape    = 1,
    safe_range = 3,
}
```

---

## 10. 完整 NPC 範例：從簡單到進階

### 10.1 等級 1：純近戰（無技能）

```lua
newEntity{
    name = "cave troll",
    type = "giant", subtype = "troll",
    display = "T", color = colors.GREEN,

    level_range = {5, 12}, exp_worth = 1,
    max_life = resolvers.rngavg(50, 70),
    rank = 2,

    -- 最簡單的 AI：找目標，直線衝
    ai = "simple",
    ai_state = { ai_move = "move_simple" },

    stats = {str=18, dex=8, con=16},
    combat = {dam=12, atk=8},
    combat_armor = 5,
}
```

### 10.2 等級 2：會技能的普通怪（dumb_talented_simple）

```lua
newEntity{
    name = "fire goblin shaman",
    type = "humanoid", subtype = "goblin",
    display = "g", color = colors.RED,

    level_range = {8, 15}, exp_worth = 1.2,
    max_life = resolvers.rngavg(30, 45),
    rank = 2,

    -- 每 4 回合隨機用一個技能
    ai = "dumb_talented_simple",
    ai_state = { talent_in = 4 },

    stats = {str=8, dex=12, con=10, mag=16},
    combat = {dam=4},

    -- 技能（dumb AI 不看 tactical，只要技能可用就隨機選）
    talents = {
        [T_FIREBALL]   = 2,
        [T_FIRE_SHIELD] = 1,
    },
    -- 技能冷卻從第 1 回合開始隨機化（避免所有怪同時開技能）
    talent_cd_reduction = {
        [T_FIREBALL] = resolvers.rngrange(0, 3),
    },
}
```

### 10.3 等級 3：智能戰術 AI（improved_tactical）

```lua
-- 技能定義（必須有 tactical table）
newTalent{
    name = "Soul Drain",
    type = {"necromancy/drain", 1},
    points = 5, cooldown = 5,
    range = 7,
    requires_target = true,

    action = function(self, t)
        local tg = {type="bolt", range=self:getTalentRange(t)}
        local x, y, target = self:getTarget(tg)
        if not x or not y or not target then return nil end
        -- 造成傷害並恢復自己的生命
        local dam = 20 + self:getMag() * 2
        target:takeHit(dam, self)
        self:heal(dam * 0.5)
        return true
    end,

    -- ★ 關鍵：tactical table 讓 improved_tactical 知道怎麼用這個技能
    tactical = {
        attack = { DARKNESS = 2 },  -- 主要傷害
        heal   = 1,                 -- 附帶回血（自己）
    },

    info = function(self, t) return "汲取目標靈魂，造成黑暗傷害並恢復生命。" end,
}

-- NPC 定義
newEntity{
    name = "lich",
    type = "undead", subtype = "lich",
    display = "L", color = colors.WHITE,

    level_range = {30, 45}, exp_worth = 3,
    max_life = resolvers.rngavg(300, 400),
    rank = 3.5,  -- 3.5 = 稀有/菁英等級

    -- ★ 使用智能戰術 AI
    ai = "improved_tactical",
    ai_state = {
        ai_target = "target_simple",
        ai_move   = "move_complex",   -- 智能移動（A*/dmap/wander 複合）
        self_compassion = 5,           -- 標準自傷懲罰
        tactical_random_range = 0.3,   -- 稍微降低隨機性，更穩定
    },

    -- ★ 戰術偏好：法師風格（保持距離、使用控制）
    ai_tactic = {
        attack    = 2,
        disable   = 2,
        escape    = 1.5,
        safe_range = 5,   -- 嘗試保持 5 格距離
    },

    stats = {str=10, dex=12, con=16, mag=24, wil=18},
    combat = {dam=6, atk=15},
    combat_armor = 10,

    resists = {
        [DamageType.COLD]    = 100,  -- 冰抗
        [DamageType.DARKNESS]= 50,   -- 暗抗
    },

    -- ★ 所有技能都要有 tactical table
    talents = {
        [T_SOUL_DRAIN]       = 3,
        [T_BONE_SHIELD]      = 2,
        [T_RAISE_DEAD]       = 2,
        [T_PHASE_DOOR]       = 1,
    },
}
```

### 10.4 等級 4：Boss（高度客製化 AI）

```lua
-- 自訂 Boss AI：三個戰鬥階段
newAI("dragon_boss", function(self)
    if not self:runAI("target_simple") then return end

    local hp_pct = self.life / self.max_life

    if hp_pct > 0.6 then
        -- 第一階段（60%+ 血量）：普通攻擊模式
        self.ai_state.ai_move = "move_simple"
        self:runAI("use_improved_tactical")
        if not self.energy.used then self:runAI("move_simple") end

    elseif hp_pct > 0.3 then
        -- 第二階段（30-60% 血量）：啟動狂暴
        if not self.ai_state._phase2_triggered then
            self.ai_state._phase2_triggered = true
            -- 觸發特殊效果
            game.log("#CRIMSON#The dragon RAGES!", self.name)
            self:setEffect(self.EFF_RAGE, 9999, {power=1.5})
        end
        self:runAI("use_improved_tactical")
        if not self.energy.used then self:runAI("move_simple") end

    else
        -- 第三階段（低於 30% 血量）：拼死反擊
        self.ai_state.safe_range = nil     -- 取消安全距離
        self.ai_tactic.escape = 0          -- 不逃跑
        self.ai_tactic.attack = 5          -- 全力攻擊
        self:runAI("use_improved_tactical")
        if not self.energy.used then self:runAI("move_simple") end
    end
end)

newEntity{
    name = "Ancient Dragon",
    unique = true,
    -- ...
    ai = "dragon_boss",
    ai_state = {
        ai_target = "target_simple",
        self_compassion = 3,  -- 稍低，更願意用自傷技能
    },
    ai_tactic = {
        attack     = 2,
        attackarea = 3,  -- 偏好 AOE
        safe_range = 4,
    },
}
```

---

## 11. 自訂新戰術（Tactic）

`improved_tactical` 支援擴充新的戰術分類：

```lua
-- 在你的 mod 中（例如透過 ToME:load hook 或直接在載入時執行）
local ActorAI = require "mod.class.interface.ActorAI"

-- 步驟 1：定義利益係數
-- +1 = 對自己有益（heal、defend 等）
-- -1 = 對敵人有害（attack、disable 等，預設值）
ActorAI.AI_TACTICS.taunt = 1   -- taunt 是對敵人的效果（-1 = 不改益損視角）

-- 步驟 2：定義 WANT 計算函式
ActorAI.AI_TACTICS_WANTS.taunt = function(self, want, actions, avail)
    -- 附近敵人越多，嘲諷需求越高
    local nb_foes = 0
    for _, act in ipairs(self.fov.actors_dist) do
        if self:reactionToward(act) < 0 then nb_foes = nb_foes + 1 end
    end
    -- 1 個敵人 want=1, 3 個 want=2, 6 個 want=3
    return math.min(10, nb_foes * 0.5)
end
```

之後在技能中使用：

```lua
newTalent{
    name = "Provoke",
    tactical = {
        taunt = 3,    -- AI 在多敵時使用
        defend = 1,   -- 也算防禦
    },
    -- ...
}
```

---

## 12. AI 除錯技巧

### 12.1 開啟 AI 詳細日誌

在遊戲設定或 Lua console 中設定：

```lua
-- Lua console 中輸入（F1 開啟 console）
config.settings.log_detail_ai = 2
-- 0 = 關閉, 1 = 基本, 2 = 詳細, 3 = 非常詳細, 4 = 超詳細
```

日誌會顯示到 console：

```
[use_tactical AI]==##== RUNNING turn 1523 42 fire goblin ...
[use_tactical AI] COMPUTED TACTIC WEIGHTs for: T_FIREBALL
---	attack: 1.5
---	attackarea: 2.0
[use_tactical AI] T_FIREBALL USEFUL TACTIC: attack 1.5
```

### 12.2 在 Lua Console 檢查 AI 狀態

```lua
-- 選中一個 NPC，檢查它的 AI 狀態
local npc = game.level.map(10, 10, engine.Map.ACTOR)
print("AI:", npc.ai)
print("Target:", npc.ai_target.actor and npc.ai_target.actor.name)
table.print(npc.ai_state, "ai_state: ")
table.print(npc.ai_tactic, "ai_tactic: ")

-- 查看 improved_tactical 的計算結果
table.print(npc.ai_state_volatile._want, "WANT: ")
table.print(npc.ai_state_volatile._avail, "AVAIL: ")
```

### 12.3 手動觸發 AI

```lua
-- 強制一個 NPC 執行 AI（在 console 中）
local npc = game.level.map(10, 10, engine.Map.ACTOR)
npc:computeFOV(20)
npc:doAI()
```

### 12.4 常見 AI 失效原因

| 問題 | 原因 | 排解 |
|------|------|------|
| 技能從不被 `improved_tactical` 使用 | 技能沒有 `tactical` 表 | 加上 `tactical = {...}` |
| 技能從不被 `improved_tactical` 使用 | 技能設了 `no_npc_use = true` | 移除此旗標 |
| 技能偶爾用，但 `improved_tactical` 不用 | 技能設了 `no_dumb_use = true` | 只有 dumb AI 受此影響 |
| NPC 停在原地不動 | AI 沒有正確消耗能量 | 確認 AI 函式有呼叫 `self:useEnergy()` |
| NPC 不攻擊玩家 | 陣營設定錯誤 | 確認 `faction` 欄位正確 |
| `target_simple` 找不到玩家 | FOV 問題 | 確認有先呼叫 `self:computeFOV()` |

---

## 13. 常見問題

### Q：`dumb_talented` 和 `improved_tactical` 怎麼選？

| 情境 | 建議 |
|------|------|
| 普通雜兵（rank 2）| `dumb_talented_simple`（快速、低開銷）|
| 稀有/菁英（rank 3）| `improved_talented`（仍然隨機，但更聰明）|
| Boss/特殊（rank 4+）| `improved_tactical`（完整戰術評分）|

### Q：`self_compassion` 和 `ally_compassion` 是什麼？

這兩個值控制 AI 對「傷到自己/友軍」的容忍度：

- `self_compassion = 5`（預設）：AOE 打到自己的技能，傷害值懲罰 ×5
- `ally_compassion = 1`（預設）：打到友軍的技能，傷害值懲罰 ×1

設為 `false` 則完全不在乎傷到自己/友軍：

```lua
ai_state = { self_compassion = false }  -- 完全不顧自傷
```

### Q：如何讓 NPC 保持距離？

使用 `ai_tactic.safe_range`：

```lua
ai_tactic = {
    escape    = 2,    -- 基礎逃跑欲望
    safe_range = 5,   -- 試圖保持 5 格距離
}
```

距離比 `safe_range` 近時，`want.escape` 會大幅提升，推動 AI 選擇逃跑技能或移動。

### Q：`tactical_random_range` 如何調整？

```lua
ai_state = { tactical_random_range = 0.0 }  -- 完全決定論（每次選最優）
ai_state = { tactical_random_range = 0.5 }  -- 預設（最多 50% 隨機浮動）
ai_state = { tactical_random_range = 1.0 }  -- 高隨機性（AI 更混亂）
```

### Q：能讓 NPC 只在特定條件下使用技能嗎？

用 `on_pre_use_ai` 回呼：

```lua
newTalent{
    name = "Desperate Strike",
    -- ...
    -- 只有血量低於 30% 時 AI 才使用
    on_pre_use_ai = function(self, t, silent, fake)
        return self.life / self.max_life < 0.3
    end,
    tactical = { attack = 4 },  -- 高戰術值確保被優先選
}
```

---

## 學完這篇教學後，你應該能：

- 理解 TE4 AI 的組合式架構
- 設定不同難度 NPC 的 AI（`simple` → `dumb_talented` → `improved_tactical`）
- 為技能正確撰寫 `tactical` 表
- 用 `ai_tactic` 調整 NPC 的戰術個性
- 撰寫自訂 AI 函式處理特殊行為
- 擴充新的戰術分類
- 使用日誌系統除錯 AI 問題
