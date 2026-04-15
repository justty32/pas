# 教學 14：技能視覺特效（粒子系統 + 自訂貼圖）

## 本章目標

為技能加入完整的視覺特效，包含：

1. **飛彈拖尾**：飛行中的投射物帶有火焰或冰晶效果
2. **落點爆炸**：投射物命中後在目標格爆發粒子
3. **持續光環**：持續技能（SUSTAINED）在施法者身上產生旋繞光環
4. **自訂粒子貼圖**：使用自製 PNG 取代內建的圓形粒子

所有粒子定義都用**冰刺術（Ice Spike）**這個技能示範，從零寫起。

---

## 系統核心概念

### 粒子系統架構

TE4 的粒子系統由三個層次組成：

```
Lua 定義檔（data/gfx/particles/xxx.lua）
  └─ 描述「每顆粒子長什麼樣」和「多快噴出粒子」
      ↓  loadfile 後傳到 C 層
C 粒子引擎（src/particles.c）
  └─ 在獨立執行緒中每幀更新所有粒子的物理狀態
      ↓
OpenGL 渲染（display_sdl.c）
  └─ 用 GPU 批次繪製所有粒子點 / 線
```

粒子計算在**獨立 C 執行緒**中進行，不影響遊戲邏輯幀率。

### 粒子定義檔的返回格式

```lua
-- 返回 4 個值（第 4 個可省略）：
return 
    { generator = function() ... end, ... },  -- ① 粒子生成器定義表
    function(self) ... end,                    -- ② 更新函式（每幀呼叫）
    max_particles,                             -- ③ 總粒子上限
    "texture/path"                             -- ④ 貼圖路徑（可省略，預設 particle.png）
```

### 粒子參數完整列表

| 參數 | 說明 | 單位 |
|------|------|------|
| `x, xv, xa` | X 位置、速度、加速度 | 像素 |
| `y, yv, ya` | Y 位置、速度、加速度 | 像素 |
| `dir, dirv, dira` | 運動方向（弧度）、角速度、角加速度 | rad |
| `vel, velv, vela` | 速度大小、速度加速度、加加速 | px/幀 |
| `size, sizev, sizea` | 粒子大小、大小變化速率 | 像素 |
| `r, rv, ra` | 紅色通道（0~1）、變化速率 | 歸一化 |
| `g, gv, ga` | 綠色通道 | 歸一化 |
| `b, bv, ba` | 藍色通道 | 歸一化 |
| `a, av, aa` | 透明度（0~1）、變化速率 | 歸一化 |
| `life` | 生命週期（幀數） | 幀 |
| `trail` | `1` = 有拖尾；`0` = 無；負數 = 連接到第 N 號粒子（ENGINE_LINES 用） | - |

> **規律**：每幀更新：`x += xv; xv += xa`（Position → Velocity → Acceleration）。顏色同理：`r += rv; rv += ra`。這讓你只需指定初始值和加速度，物理自動計算。

---

## 完整檔案結構

```
mygame/
  mod/
    data/
      talents/
        ice.lua                            ← 冰系技能定義
      gfx/
        particles/
          ice_bolt.lua                     ← 冰錐飛行粒子
          ice_explosion.lua                ← 冰錐爆炸粒子
          ice_aura.lua                     ← 冰護盾光環粒子
        particles_images/
          ice_shard.png                    ← 自訂冰晶貼圖（32×32 PNG）
```

---

## 步驟一：粒子貼圖（PNG 規格）

### 規格要求

| 屬性 | 要求 |
|------|------|
| 格式 | PNG，RGBA 四通道 |
| 尺寸 | 正方形，建議 32×32 或 64×64 |
| 背景 | 完全透明（Alpha = 0） |
| 中心 | 粒子的「原點」在圖片中心 |
| 顏色 | 全白（1,1,1,1）讓 Lua 的 r/g/b 欄位完整控制顏色 |

### 為什麼建議全白？

TE4 粒子引擎的著色公式是：

```
最終顏色 = 貼圖像素顏色 × 粒子 r/g/b/a 參數
```

如果貼圖本身是藍色，設定 `r=1,g=0,b=0`（紅色）不會生效，因為貼圖的藍色通道會覆蓋掉。使用**全白貼圖**讓 Lua 的顏色參數完全控制最終顏色。

### `ice_shard.png` 的建立方式

使用任何圖像工具（GIMP / Krita / Aseprite）：

1. 建立 32×32 透明畫布
2. 在中心畫一個細長的菱形（冰晶形狀），顏色純白（#FFFFFF）
3. 對邊緣做高斯模糊（半徑 1px），讓邊緣柔和
4. 以 `ice_shard.png` 儲存到 `mod/data/gfx/particles_images/` 目錄

> **路徑映射**：粒子定義檔第 4 個返回值的路徑是相對 `/data/gfx/` 的虛擬路徑。`"particles_images/ice_shard"` 對應到 `data/gfx/particles_images/ice_shard.png`（不需要寫 `.png` 副檔名）。

---

## 步驟二：飛行粒子（ice_bolt.lua）

### 效果目標

冰錐飛行時留下一條**藍白色冰晶拖尾**，粒子從飛行方向往兩側散開，快速消失。

### 檔案：`mod/data/gfx/particles/ice_bolt.lua`

```lua
-- mod/data/gfx/particles/ice_bolt.lua
-- 冰錐飛行拖尾粒子

-- ── 頂層設定（在 return 之前設定） ───────────────────────────
base_size = 32   -- 粒子大小隨格子尺寸縮放（32 = 標準格大小）

-- ── 生成器定義 ────────────────────────────────────────────────
return {
    -- BLEND_SHINY = 加法混色（疊加更亮），適合火、冰、電等光效
    blend_mode = core.particles.BLEND_SHINY,

    generator = function()
        -- 從飛行方向（往 tx, ty 的方向）散開
        -- tx, ty 是 Particles.new 的 args 傳入的目標偏移（格數）
        local base_angle = math.atan2(
            ty * engine.Map.tile_h,
            tx * engine.Map.tile_w
        )

        -- 粒子從飛行路徑兩側隨機偏移噴出
        local side_angle = base_angle + math.rad(rng.range(-60, 60))
        local speed = rng.float(0.5, 2.0)

        return {
            -- 生命週期：8~16 幀（短暫的拖尾）
            life = rng.range(8, 16),
            trail = 0,

            -- 大小：4~8px，逐漸縮小至消失
            size  = rng.range(4, 8), sizev = -0.3, sizea = 0,

            -- 初始位置：在飛行路徑附近小範圍隨機
            x  = rng.range(-4, 4), xv = 0, xa = 0,
            y  = rng.range(-4, 4), yv = 0, ya = 0,

            -- 運動方向：往兩側散開
            dir  = side_angle,
            dirv = math.rad(rng.range(-2, 2)),  -- 微小的方向漂移
            dira = 0,
            vel  = speed, velv = -0.05, vela = 0,

            -- 顏色：藍白混合（冰晶感）
            -- 白色高光核心：r,g,b 都接近 1
            -- 外圍轉為冰藍色：g 逐漸降低，b 保持高
            r = rng.float(0.6, 1.0),  rv = -0.02, ra = 0,
            g = rng.float(0.8, 1.0),  gv = -0.03, ga = 0,
            b = 1.0,                  bv =  0.00, ba = 0,
            a = rng.float(0.5, 0.9),  av = -0.05, aa = 0,
        }
    end,
},
-- ── 更新函式：每幀呼叫，控制噴出速率 ─────────────────────────
function(self)
    -- 飛行中持續噴出：每幀噴 3 顆粒子
    self.ps:emit(3)
end,
-- ── 最大粒子數量 ──────────────────────────────────────────────
-- 飛行最長 range=20 格，每格約 10 幀，共約 200 幀 × 3 顆 = 600
600,
-- ── 貼圖路徑（自訂冰晶形狀） ─────────────────────────────────
"particles_images/ice_shard"
```

---

## 步驟三：爆炸粒子（ice_explosion.lua）

### 效果目標

冰錐命中目標時，在目標格爆發一圈**向外飛散的冰晶碎片**，並有一個**短暫的冰白色閃光**。

### 檔案：`mod/data/gfx/particles/ice_explosion.lua`

```lua
-- mod/data/gfx/particles/ice_explosion.lua
-- 冰爆炸（命中時的爆散效果）

-- radius 由 particleEmitter 呼叫時傳入
local sradius = (radius + 0.5) * (engine.Map.tile_w + engine.Map.tile_h) / 2
local nb_emitted = 0   -- 記錄已噴出的批次數（用於一次性爆炸）

return {
    blend_mode = core.particles.BLEND_SHINY,

    generator = function()
        -- 隨機方向向外爆炸
        local angle  = math.rad(rng.float(0, 360))
        local radius_pct = rng.float(0.3, 1.0)  -- 0.3~1.0 倍半徑
        local r_dist = sradius * radius_pct

        return {
            life = rng.range(10, 25),
            trail = 1,   -- 帶拖尾

            -- 從中心向外爆炸：初始位置在中心附近
            size  = rng.range(3, 10), sizev = -0.3, sizea = 0,
            x  = rng.range(-4, 4),  xv = 0, xa = 0,
            y  = rng.range(-4, 4),  yv = 0, ya = 0,

            -- 方向：向外四散，速度隨距離遞減
            dir  = angle, dirv = 0, dira = 0,
            vel  = r_dist / 15,        -- 在 15 幀內飛到邊緣
            velv = -r_dist / 15 / 15,  -- 逐漸減速
            vela = 0,

            -- 顏色：白色核心 → 冰藍色邊緣 → 透明消失
            r = rng.float(0.7, 1.0),  rv = -0.03, ra = 0,
            g = rng.float(0.8, 1.0),  gv = -0.02, ga = 0,
            b = 1.0,                  bv =  0.00, ba = 0,
            a = rng.float(0.7, 1.0),  av = -0.04, aa = 0,
        }
    end,
},
function(self)
    -- 一次性爆炸：只在第一幀噴出大量粒子，之後不再噴
    if nb_emitted == 0 then
        -- 爆炸粒子數量與半徑成正比（半徑越大越壯觀）
        self.ps:emit(math.max(50, radius * 80))
        nb_emitted = 1
    end
end,
-- 最大粒子數：一次爆出，設定足夠大
math.max(50, radius * 80 + 10),
"particles_images/ice_shard"
```

---

## 步驟四：持續光環（ice_aura.lua）

### 效果目標

施法者持續施展冰護盾時，身上環繞著**旋轉的冰晶碎片**，慢慢繞圈移動，提示這是一個 SUSTAINED 技能。

### 檔案：`mod/data/gfx/particles/ice_aura.lua`

```lua
-- mod/data/gfx/particles/ice_aura.lua
-- 冰護盾持續光環

can_shift = true   -- 允許隨實體移動（走路時粒子跟著移動）
base_size = 32     -- 大小隨格子縮放

return {
    blend_mode = core.particles.BLEND_SHINY,

    generator = function()
        -- 在圓環上隨機選一個起始角度
        local angle = math.rad(rng.float(0, 360))
        local orbit_r = rng.range(14, 20)  -- 軌道半徑（像素）
        -- 每顆粒子繞圈方向：逆時針 dirv = -math.rad(2)
        local dir = angle + math.rad(90)   -- 切線方向（垂直於半徑）

        return {
            life = rng.range(20, 40),
            trail = 0,

            -- 初始位置：在軌道圓上
            x  = orbit_r * math.cos(angle),  xv = 0, xa = 0,
            y  = orbit_r * math.sin(angle),  yv = 0, ya = 0,

            -- 繞圈運動：向切線方向前進，方向持續轉動（產生圓形路徑）
            dir  = dir,
            dirv = -math.rad(rng.float(1.5, 2.5)),  -- 旋轉速度（負 = 逆時針）
            dira = 0,
            vel  = rng.float(0.8, 1.5), velv = 0, vela = 0,

            -- 大小：中等，逐漸縮小至消失
            size  = rng.range(3, 7), sizev = -0.05, sizea = 0,

            -- 顏色：冰藍色，逐漸淡出
            r = rng.float(0.3, 0.7),  rv = 0,     ra = 0,
            g = rng.float(0.7, 1.0),  gv = 0,     ga = 0,
            b = 1.0,                  bv = 0,     ba = 0,
            a = rng.float(0.5, 0.9),  av = -0.02, aa = 0,
        }
    end,
},
function(self)
    -- 持續光環：每幀穩定噴出（讓圓環看起來是連續的）
    self.ps:emit(2)
end,
-- 最大粒子數：持續光環需要足夠多（200 顆讓圓環看起來飽滿）
200,
"particles_images/ice_shard"
```

---

## 步驟五：技能定義（整合特效）

### 三種附加粒子的方式

| 方式 | 使用時機 | API |
|------|---------|-----|
| **投射物拖尾** | `project`/`projectile` 的飛行過程 | `tg.display = {particle="name", trail="name"}` |
| **落點爆炸** | 命中格子後（`project` callback 或技能 `action`） | `game.level.map:particleEmitter(x, y, radius, "name", {args})` |
| **持續光環** | SUSTAINED 技能的 activate/deactivate | `self:addParticles(Particles.new("name", radius, args))` |

### 檔案：`mod/data/talents/ice.lua`

```lua
-- mod/data/talents/ice.lua
-- 冰系技能：展示三種粒子附加方式

local Particles = require "engine.Particles"

newTalentType{
    type        = "spell/ice",
    name        = "冰系魔法",
    description = "操控寒氣的冰系魔法。",
}

-- ─────────────────────────────────────────────────────────────
-- 技能一：冰錐術（方式 A：投射物拖尾 + 方式 B：落點爆炸）
-- ─────────────────────────────────────────────────────────────
newTalent{
    name    = "冰錐術",
    type    = {"spell/ice", 1},
    points  = 5,
    cooldown = 4,
    range   = 10,
    proj_speed    = 8,         -- 投射物飛行速度（越高越快）
    requires_target = true,
    reflectable   = true,      -- 可被反射牆彈回

    action = function(self, t)
        -- ★ 定義投射物目標（飛行時使用 ice_bolt 拖尾）
        local tg = {
            type  = "bolt",
            range = self:getTalentRange(t),
            talent = t,

            -- ── 方式 A：投射物飛行時的粒子 ──
            display = {
                -- particle：投射物頭部的粒子系統
                particle = "ice_bolt",
                -- trail：投射物拖尾（也用 ice_bolt，也可分開）
                -- 注意：trail 是附加在投射物每個路徑格的粒子
                trail    = "ice_bolt",
            },
        }

        local x, y = self:getTarget(tg)
        if not x or not y then return nil end

        -- 計算傷害：基礎 + 每技能等級遞增
        local dam = (15 + self:getTalentLevel(t) * 10)

        -- ★ 方式 B：project 完成後呼叫 callback 在落點爆炸
        self:project(tg, x, y, DamageType.COLD, dam, function(px, py)
            -- 在命中格爆發冰晶特效（radius = 0 代表單格爆炸）
            game.level.map:particleEmitter(
                px, py,
                0,            -- 半徑（0 = 只在命中格）
                "ice_explosion",
                {
                    radius = 0,   -- 傳給粒子 Lua 的 args
                    tx = px,      -- 命中格座標（部分特效需要）
                    ty = py,
                }
            )
        end)

        return true
    end,

    info = function(self, t)
        local dam = 15 + self:getTalentLevel(t) * 10
        return ("向目標發射一根冰錐，造成 %d 點寒冷傷害。"):format(dam)
    end,
}

-- ─────────────────────────────────────────────────────────────
-- 技能二：冰霜爆裂（方式 B：直接落點爆炸，無投射物）
-- ─────────────────────────────────────────────────────────────
newTalent{
    name    = "冰霜爆裂",
    type    = {"spell/ice", 2},
    points  = 5,
    cooldown = 8,
    range   = 8,
    requires_target = true,

    action = function(self, t)
        local tg = {
            type   = "ball",
            range  = self:getTalentRange(t),
            radius = 1 + math.floor(self:getTalentLevelRaw(t) / 2),
            talent = t,
            selffire = false,
        }

        local x, y = self:getTarget(tg)
        if not x or not y then return nil end

        -- 直接 project，不用投射物（瞬間施放）
        self:project(tg, x, y, DamageType.COLD,
            20 + self:getTalentLevel(t) * 8)

        -- ★ 落點爆炸特效（球形，半徑與技能範圍一致）
        game.level.map:particleEmitter(
            x, y,
            tg.radius,       -- radius 傳給粒子 Lua 的 sradius 計算
            "ice_explosion",
            {
                radius = tg.radius,
                tx = x,
                ty = y,
            }
        )
        return true
    end,

    info = function(self, t)
        local r = 1 + math.floor(self:getTalentLevelRaw(t) / 2)
        return ("在目標位置製造半徑 %d 格的冰霜爆炸。"):format(r)
    end,
}

-- ─────────────────────────────────────────────────────────────
-- 技能三：冰護盾（方式 C：SUSTAINED + 持續光環）
-- ─────────────────────────────────────────────────────────────
newTalent{
    name    = "冰護盾",
    type    = {"spell/ice", 3},
    points  = 5,
    mode    = "sustained",   -- ★ SUSTAINED：開啟/關閉切換型技能
    cooldown = 20,
    sustain_power = 10,      -- 維持成本（每回合消耗的能量/法力）

    activate = function(self, t)
        -- ★ 方式 C：開啟時在施法者身上附加粒子光環
        -- Particles.new(def, radius, args, shader)
        -- radius 影響 base_size 的縮放（1 = 正常大小）
        local particle = self:addParticles(
            Particles.new("ice_aura", 1, {})
        )

        -- 把粒子 handle 存在 eff（effect 狀態表）裡
        -- 以便 deactivate 時取消
        return {
            particle = particle,
            absorb   = 5 + self:getTalentLevel(t) * 3,  -- 防護值
        }
    end,

    deactivate = function(self, t, p)
        -- ★ 關閉時移除粒子光環
        self:removeParticles(p.particle)
        return true
    end,

    info = function(self, t)
        local absorb = 5 + self:getTalentLevel(t) * 3
        return ("持續消耗能量，形成冰護盾吸收 %d 點傷害。"):format(absorb)
    end,
}
```

> **`activate` 的返回值**：SUSTAINED 技能的 `activate` 必須 `return {...}` 一個狀態表（即使是空表 `{}`）——這個表就是 `p`（eff 狀態），會傳給 `deactivate` 和 `on_timeout`。如果 `return nil` 或沒有 return，技能會立刻被取消。

---

## 步驟六：`particleEmitter` 的完整簽名

```lua
game.level.map:particleEmitter(
    x,          -- 格座標 X（不是像素）
    y,          -- 格座標 Y
    radius,     -- 半徑（格數，用於 sradius 計算；0 = 單格）
    "def_name", -- 粒子定義檔名稱（不含 .lua，相對 data/gfx/particles/）
    {           -- args 表格：在粒子 Lua 中作為全域變數可用
        radius = radius,   -- → 粒子 Lua 中的 radius 變數
        tx = x,            -- → tx 變數
        ty = y,            -- → ty 變數
        color = {r=1,g=0,b=0},  -- 自訂（粒子 Lua 中自行讀取）
        -- 任何你想傳的額外參數都可以加在這裡
    }
)
```

> `args` 表格的內容在粒子 Lua 環境中作為**全域變數**存在。`bolt_fire.lua` 能讀到 `tx`、`ty` 是因為 `Particles:loaded()` 用 `setfenv` 把 `args` 表設為函式環境：
> ```lua
> setfenv(f, setmetatable(t, {__index=_G}))
> ```
> 所以 `args.tx` 在粒子 Lua 中直接寫成 `tx` 即可存取。

---

## 步驟七：粒子圖片放置路徑

粒子定義的第 4 個返回值是相對於**虛擬檔案系統根目錄 `/data/gfx/`** 的路徑（不含 `.png`）：

```lua
-- 寫這個：
"particles_images/ice_shard"

-- 引擎會找：
"/data/gfx/particles_images/ice_shard.png"

-- 物理路徑（你的模組）：
"mod/data/gfx/particles_images/ice_shard.png"
```

內建可用貼圖：

| 路徑（省略 `/data/gfx/`） | 外觀描述 |
|--------------------------|---------|
| `particle`（預設）| 圓形高斯模糊光點 |
| `particle_cloud` | 較大的雲狀光點 |
| `particle_torus` | 環形（donut）形狀 |
| `particles_images/beam` | 細長光束片段（用於直線效果） |

---

## 步驟八：調整技巧

### 讓特效在低效能設備上正常縮放

玩家可以在設定中調整粒子密度（`config.settings.particles_density`，0~100%）。引擎的 C 層會根據這個值縮減 `emit` 的數量。你不需要手動處理，只需確保在最高密度時的粒子數量合理（建議不超過 1000 顆）。

### 常見調整參數

```lua
-- 讓粒子「向心」匯聚（從外往內飛）
vel  = sradius / 10,   -- 初始速度（向外）
velv = -sradius / 100, -- 逐幀減速
vela = 0,

-- 讓粒子「離心」爆散（從內往外飛）
vel  = 0,
velv = sradius / 20,   -- 逐幀加速往外

-- 讓粒子「旋轉」：改變 dir 而不是 x/y
dir  = math.rad(rng.float(0, 360)),
dirv = math.rad(rng.range(2, 5)),  -- 每幀旋轉 2~5 度

-- 讓粒子「閃爍」：透明度先增後減
a  = 0,
av = 0.1,      -- 先變亮
aa = -0.01,    -- 加速度讓 av 漸減 → 最終反轉 → 變暗
```

### 觀察現有特效調參的訣竅

```lua
-- 在 Cheat Console 中即時添加粒子到當前格子測試
game.level.map:particleEmitter(
    game.player.x, game.player.y,
    2,
    "ice_explosion",     -- 替換成你正在調整的粒子名稱
    {radius=2, tx=game.player.x, ty=game.player.y}
)
```

---

## 常見錯誤排查

| 錯誤現象 | 原因 | 解法 |
|---------|------|------|
| 粒子完全不顯示 | 粒子 Lua 語法錯誤，或貼圖路徑找不到 | 查看 Cheat Console 錯誤訊息；確認貼圖路徑和 PNG 存在 |
| 粒子顯示但立即消失 | `life` 太小（< 5）或 `av` 太大（每幀透明度扣太多） | 增大 `life`；減小 `av` 的絕對值 |
| 光環粒子不跟隨角色移動 | 未設定 `can_shift = true` | 在粒子 Lua 頂層加 `can_shift = true` |
| 自訂貼圖顯示為方形 | PNG 背景不透明 | 確認 PNG 背景完全透明（Alpha = 0） |
| 自訂貼圖顏色不對 | 貼圖不是全白，Lua 顏色乘法不符合預期 | 把貼圖畫成純白，讓 r/g/b 參數控制顏色 |
| 爆炸粒子只出現在格左上角 | `particleEmitter` 座標傳的是格座標（整數）是正確的，問題可能在粒子 Lua 中 x/y 偏移計算 | 確認 `sradius` 是用像素計算的：`(radius + 0.5) * (tile_w + tile_h) / 2` |
| SUSTAINED 技能開啟後光環立即消失 | `activate` 沒有 `return {...}` | 確認 `activate` 最後有 `return {particle=particle, ...}` |
| `addParticles` 後移動時粒子抖動 | `can_shift = true` 但 `shift` 被呼叫時更新不及時 | 這是 TE4 已知行為，通常在高移動速度時才明顯，一般可接受 |

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| 粒子定義檔格式 | `data/gfx/particles/*.lua` | 返回 `{generator=fn}`, update fn, max, texture |
| 粒子每幀物理 | generator 的欄位 | `v` 後綴 = 速度；`a` 後綴 = 加速度 |
| 飛行拖尾 | 技能 `tg.display` | `{particle="name", trail="name"}` |
| 落點爆炸 | 技能 `action` 中 | `map:particleEmitter(x, y, r, "name", args)` |
| 持續光環 | SUSTAINED `activate`/`deactivate` | `addParticles(Particles.new(...))` / `removeParticles()` |
| 自訂貼圖 | 粒子 Lua 第 4 返回值 | 放 PNG 到 `data/gfx/particles_images/`，全白背景透明 |
| args 傳遞 | `particleEmitter` / `Particles.new` | args 表在粒子 Lua 中作為全域變數可用 |
