# 教學 17：自訂動畫

TE4 的「動畫」分為幾個完全獨立的層次，每層有不同的用途和 API。本教學逐一說明並提供可直接使用的範例。

---

## 動畫系統一覽

| 系統 | 位置 | 用途 |
|------|------|------|
| 精靈圖序列（`entity.anim`） | C 層 map object | 實體在地圖上逐幀播放 |
| 移動動畫（`setMoveAnim`） | C 層 map object | 滑動 / 攻擊搖晃 |
| `tween` 補間 | Lua thirdparty | 數值平滑過渡（UI 元素動畫） |
| `FlyingText` 飄字 | `engine.FlyingText` | 傷害數字、浮動提示文字 |
| `displayCallback` | C 層 map object | 實體每幀自訂渲染 |
| OpenGL 變換（glTranslate/Scale/Rotate） | `core.display.*` | 任意 2D 幾何動畫 |

---

## 一、精靈圖序列動畫（Sprite Sheet）

### 1.1 原理

把 N 張動畫幀水平排列在**同一張 PNG** 上，然後在 entity 定義中加上 `anim` 欄位，引擎的 C 層會自動計算 UV 偏移並逐幀播放。

```
frame1 | frame2 | frame3 | frame4     ← 一張 256×64 的 sprite strip（每幀 64×64）
```

### 1.2 Entity 定義

```lua
newEntity{
    define_as = "FIRE_TRAP",
    type = "trap", subtype = "fire",
    name = "fire trap",

    -- sprite strip：4 幀、每幀 64×64，整張圖是 256×64
    image = "trap/fire_anim.png",

    anim = {
        max   = 4,    -- 幀數（texture 寬度 / 每幀寬度）
        speed = 2,    -- 每幾個 render frames 前進一幀（越小越快）
        loop  = -1,   -- -1=無限循環，0=播一次後停，N=播N次後停
    },
    ...
}
```

### 1.3 注意事項

- `image` 必須是水平精靈圖（所有幀左右排列）
- `anim.max` = 幀數（不是像素寬）；引擎內部做 `btexx / anim.max` 計算每幀 UV
- Entity 實體化時若要動態改變動畫（例如切換「行走」↔「攻擊」幀段），需要呼叫 C 層 `_mo:setAnim(start, max, speed, loop)`，但這需要直接操作 map object，通常不推薦

---

## 二、移動動畫（`setMoveAnim`）

### 2.1 滑動動畫（角色移動）

每次 actor 成功移動到新位置後，呼叫 `setMoveAnim` 讓它看起來是「滑」過去的，而不是瞬間跳格：

```lua
-- 在 mod/class/Actor.lua 的 move() 中
function _M:move(x, y, force)
    local ox, oy = self.x, self.y
    local moved = engine.Actor.move(self, x, y, force)

    if moved and ox and oy and (ox ~= self.x or oy ~= self.y) then
        -- speed=3：動畫持續 3 個 render frames（約 0.1 秒）
        self:setMoveAnim(ox, oy, 3)
    end
    return moved
end
```

`setMoveAnim(oldx, oldy, speed, blur, twitch_dir, twitch)` 完整參數：

| 參數 | 預設 | 說明 |
|------|------|------|
| `oldx, oldy` | — | 動畫起點（舊座標） |
| `speed` | — | 動畫幀數（render frames） |
| `blur` | `0` | 動態模糊殘影幀數（`nil` 或 `0` = 無模糊） |
| `twitch_dir` | `0` | 搖晃方向（numpad 方向，0=上方） |
| `twitch` | `0` | 搖晃幅度（0.0–1.0，單位：格） |

### 2.2 攻擊搖晃動畫

攻擊時讓攻擊者短暫往目標方向「衝刺」後彈回：

```lua
function _M:attackTarget(target)
    -- 往目標方向搖晃 0.2 格，持續 3 幀
    self:setMoveAnim(
        self.x, self.y,       -- 起點（原位置）
        3,                    -- 速度
        nil,                  -- 無模糊
        util.getDir(target.x, target.y, self.x, self.y),  -- 攻擊方向
        0.2                   -- 搖晃幅度
    )
    -- 傷害計算...
end
```

### 2.3 停止移動動畫

```lua
self:resetMoveAnim()   -- 立即停止，不等動畫播完
```

---

## 三、`tween` 補間（UI 動畫）

### 3.1 基本用法

`tween` 庫位於 `game/thirdparty/tween.lua`，由 `Game:tick()` 每幀自動更新：

```lua
local tween = require "tween"

-- 基本格式：tween(幀數, 目標物件, {目標值}, 緩動名稱, 完成回調)
local id = tween(60, self, {alpha=0}, "outQuad", function()
    -- 動畫完成後執行
    self.visible = false
end)

-- 取消動畫
tween.stop(id)
```

`subject`（目標物件）的對應欄位會被平滑更新至 `target_table` 中的值。欄位必須是**數字**。

### 3.2 緩動函式

| 名稱 | 效果 |
|------|------|
| `"linear"` | 勻速 |
| `"inQuad"` / `"outQuad"` | 加速入 / 減速出（二次方） |
| `"inCubic"` / `"outCubic"` | 加速入 / 減速出（三次方） |
| `"inSine"` / `"outSine"` | 正弦緩動 |
| `"inQuint"` / `"outQuint"` | 強加速入 / 強減速出 |
| `"inBounce"` / `"outBounce"` | 彈跳 |
| `"inElastic"` / `"outElastic"` | 彈性 |
| `"inOutQuad"` | 前半加速、後半減速 |

### 3.3 範例：BigNews 大字通知（帶縮放漸出）

```lua
-- 仿 mod/class/BigNews.lua 的寫法
local tween = require "tween"

local Notif = {}

function Notif:show(text, duration)
    self.text = text
    self.scale = 1.0    -- 從 1.0 縮到 0
    self.alpha = 1.0
    if self.tw then tween.stop(self.tw) end
    -- 60 幀後縮小消失
    self.tw = tween(duration or 60, self, {scale=0, alpha=0}, "inQuint", function()
        self.text = nil
    end)
end

function Notif:display()
    if not self.text then return end
    local cx, cy = game.w / 2, game.h / 4

    core.display.glTranslate(cx, cy, 0)
    core.display.glScale(self.scale, self.scale, self.scale)

    -- 繪製文字（略）
    self.tex:toScreenFull(-self.tw/2, -self.th/2, self.tw, self.th,
        self.ttw, self.tth, 1, 1, 1, self.alpha)

    core.display.glScale()           -- 恢復 scale
    core.display.glTranslate(-cx, -cy, 0)  -- 恢復 translate
end
```

---

## 四、`FlyingText` 飄字

### 4.1 初始化（在 Game:load 中）

```lua
local FlyingText = require "engine.FlyingText"

function _M:load(...)
    ...
    -- 建立飄字系統
    self.flyers = FlyingText.new("/data/font/DroidSans.ttf", 14,
                                 "/data/font/DroidSans-Bold.ttf", 16)
    self.flyers:enableShadow(0.6)
    self:setFlyingText(self.flyers)
end
```

### 4.2 顯示飄字

```lua
-- 取得角色的螢幕像素座標
local function actorScreenPos(actor)
    local map = game.level.map
    local sx = map.display_x + (actor.x - map.mx) * map.tile_w
    local sy = map.display_y + (actor.y - map.my) * map.tile_h
    return sx, sy
end

-- 在受到傷害時顯示傷害數字
function _M:onTakeHit(value, src)
    local sx, sy = actorScreenPos(self)
    game.flyers:add(
        sx, sy,                          -- 螢幕位置
        30,                              -- 持續 30 幀
        (rng.range(0,2)-1) * 0.5,       -- 水平速度（-0.5 ~ 0.5）
        -3,                              -- 向上飄（負 y）
        tostring(math.ceil(value)),      -- 顯示文字
        {255, 80, 80},                   -- 紅色
        false                            -- 不使用大字
    )
    return value
end

-- 等級提升提示
local sx, sy = actorScreenPos(game.player)
game.flyers:add(sx, sy, 80, 0.5, -2, "LEVEL UP!", {0, 255, 255}, true)
```

`FlyingText:add` 參數：

| 參數 | 說明 |
|------|------|
| `x, y` | 螢幕像素座標 |
| `duration` | 持續幀數 |
| `xvel` | 水平速度（像素/幀） |
| `yvel` | 垂直速度（負值=向上） |
| `str` | 顯示文字 |
| `color` | `{r,g,b}` 表（0–255） |
| `bigfont` | `true` = 使用大號字 |

---

## 五、`displayCallback`（逐幀自訂渲染）

### 5.1 用途

`displayCallback` 在**每個 render frame** 、Entity 的 Map Object（`_mo`）被繪製時呼叫，適合：
- 在 entity 上方顯示血條
- 動態光暈、閃爍效果
- 自訂指標或圖示

### 5.2 實作血條

```lua
-- 在 Actor 子類中覆寫 defineDisplayCallback
function _M:defineDisplayCallback()
    -- 先呼叫父類（處理粒子、陣營顏色）
    engine.Actor.defineDisplayCallback(self)

    if not self._mo then return end

    -- 避免 cyclic reference 導致 GC 問題：用 weak table
    local weak = setmetatable({[1]=self}, {__mode="v"})
    local prev_cb = nil  -- 若需要保留父類 callback，先儲存

    self._mo:displayCallback(function(x, y, w, h)
        local self = weak[1]
        if not self then return end

        -- 繪製半透明黑色底條
        local bar_w = w * 0.8
        local bar_h = 4
        local bx = x + (w - bar_w) / 2
        local by = y - bar_h - 2

        core.display.drawQuad(bx, by, bar_w, bar_h, 0, 0, 0, 180)

        -- 繪製紅色血量條
        if self.life and self.max_life and self.max_life > 0 then
            local pct = math.max(0, self.life / self.max_life)
            core.display.drawQuad(bx, by, bar_w * pct, bar_h, 255, 50, 50, 220)
        end

        return true  -- 必須 return true
    end)
end
```

> **注意**：`core.display.drawQuad(x, y, w, h, r, g, b, a)` — 最後 `a` 是 0–255 的透明度。

### 5.3 閃爍效果

```lua
-- 讓 entity 以固定頻率閃爍（如受傷時）
function _M:startFlash(duration)
    self._flash_timer = duration
end

function _M:defineDisplayCallback()
    local weak = setmetatable({[1]=self}, {__mode="v"})
    self._mo:displayCallback(function(x, y, w, h)
        local self = weak[1]
        if not self then return end
        -- 閃爍時以白色半透明圖層蓋住
        if self._flash_timer and self._flash_timer > 0 then
            local alpha = math.sin(self._flash_timer * 0.5) * 128 + 128
            core.display.drawQuad(x, y, w, h, 255, 255, 255, alpha)
            self._flash_timer = self._flash_timer - 1
        end
        return true
    end)
end
```

每回合在 `act()` 中驅動：`self:defineDisplayCallback()` 在修改 `_flash_timer` 後不需要重新呼叫，callback 本身已透過 weak reference 自動讀取最新值。

---

## 六、OpenGL 變換動畫（畫面空間）

### 6.1 API 說明

這些函式操作 OpenGL 變換矩陣，影響之後的所有繪製指令：

```lua
core.display.glTranslate(dx, dy, 0)    -- 平移
core.display.glScale(sx, sy, sz)       -- 縮放
core.display.glRotate(deg, 0, 0, 1)    -- 繞 Z 軸旋轉（2D 常用）

-- 恢復（TE4 沒有矩陣 push/pop，要手動逆變換）
core.display.glScale(1/sx, 1/sy, 1/sz) -- 或 core.display.glScale()（重設為 1）
core.display.glTranslate(-dx, -dy, 0)
```

> **注意**：`core.display.glScale()` 不帶參數等同於 `glScale(1,1,1)`，重設縮放但**不**恢復 translate。變換順序：**先 translate、再 scale/rotate**，恢復時**先 scale/rotate、再 translate**。

### 6.2 搖晃畫面（受擊反饋）

```lua
-- 在 UISet:displayUI 或 Game:display 中呼叫
local tween = require "tween"

function _M:screenShake(intensity, duration)
    self._shake = {x=0, y=0, intensity=intensity}
    tween(duration or 20, self._shake, {intensity=0}, "outCubic")
end

function _M:display(nb_keyframes)
    if self._shake and self._shake.intensity > 0 then
        local ox = (rng.float(-1, 1)) * self._shake.intensity
        local oy = (rng.float(-1, 1)) * self._shake.intensity
        core.display.glTranslate(ox, oy, 0)
    end

    -- 正常畫面渲染...
    engine.Game.display(self, nb_keyframes)

    if self._shake and self._shake.intensity > 0 then
        core.display.glTranslate(-self._shake.intensity, -self._shake.intensity, 0)  -- 近似恢復
    end
end
```

### 6.3 對話框彈出動畫

在 Dialog 子類中，覆寫 `display` 做縮放彈出效果：

```lua
local tween = require "tween"

module(..., package.seeall, class.inherit(engine.ui.Dialog))

function _M:init(title, w, h)
    engine.ui.Dialog.init(self, title, w, h)
    self._popup_scale = 0.1
    self._popup_alpha = 0
    tween(15, self, {_popup_scale=1, _popup_alpha=1}, "outBack")
end

function _M:display()
    local cx = self.display_x + self.w / 2
    local cy = self.display_y + self.h / 2
    local s  = self._popup_scale

    core.display.glTranslate(cx, cy, 0)
    core.display.glScale(s, s, s)
    core.display.glTranslate(-cx, -cy, 0)

    engine.ui.Dialog.display(self)   -- 繪製 Dialog 本體

    core.display.glTranslate(cx, cy, 0)
    core.display.glScale()           -- 重設
    core.display.glTranslate(-cx, -cy, 0)
end
```

---

## 七、完整範例：技能命中特效系統

結合以上所有系統，實作一套「技能命中時：飄字 + 攻擊搖晃 + 粒子 + 螢幕震動」的效果：

```lua
-- mod/class/interface/Combat.lua（或在技能 action 中呼叫）

local FlyingText = require "engine.FlyingText"
local tween = require "tween"

-- 通用的命中特效函式
function _M:hitEffect(target, damage, dtype)
    local map = game.level.map
    local sx = map.display_x + (target.x - map.mx) * map.tile_w
    local sy = map.display_y + (target.y - map.my) * map.tile_h

    -- 1. 傷害飄字
    local color
    if dtype == DamageType.FIRE   then color = {255, 120,  30}
    elseif dtype == DamageType.ICE then color = { 80, 200, 255}
    else                               color = {255, 255,  80} end

    game.flyers:add(sx, sy - map.tile_h/2,
        35,
        (rng.range(0,2)-1) * 0.3, -2.5,
        tostring(math.ceil(damage)), color, false)

    -- 2. 攻擊搖晃（攻擊者往目標方向衝刺）
    self:setMoveAnim(self.x, self.y, 4, nil,
        util.getDir(target.x, target.y, self.x, self.y), 0.25)

    -- 3. 粒子效果
    map:particleEmitter(target.x, target.y, 1, "melee_attack",
        {color = target.blood_color or {255, 0, 0}})

    -- 4. 大傷害時震動螢幕
    if damage > 50 then
        game.uiset:screenShake(damage / 20, 15)  -- 假設 UISet 有 screenShake 方法
    end
end
```

---

## 八、總結與選用指引

| 需求 | 使用系統 |
|------|---------|
| 地圖上的 NPC/怪物逐幀動畫 | `entity.anim = {max, speed, loop}` |
| 角色移動滑動效果 | `actor:setMoveAnim(ox, oy, speed)` |
| 攻擊動作（往前衝） | `actor:setMoveAnim(x, y, speed, nil, dir, 0.2)` |
| UI 元素淡入/淡出/縮放 | `tween(frames, obj, {field=target}, easing, cb)` |
| 傷害數字 / 狀態提示 | `game.flyers:add(sx, sy, dur, vx, vy, str, color)` |
| 自訂血條 / 每幀 entity 特效 | `entity._mo:displayCallback(fn)` |
| 全螢幕震動 / Dialog 彈出 | `core.display.glTranslate/Scale/Rotate` + tween |
| 持續特效（光暈、粒子環） | `actor:addParticles(Particles.new(...))` （見教學 14） |
