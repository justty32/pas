# T-Engine 4 — Lua 引擎層詳細分析

> 所有原始碼位於 `game/engines/te4-1.7.6.teae`（zip 格式），解壓後為 `engine/` 目錄。

---

## 1. OOP 基礎系統 (`engine/class.lua`)

TE4 在 Lua 5.1 上自行實作了一套物件導向系統，是整個引擎的地基。

### 1.1 類別建立

```lua
module(..., package.seeall, class.make)        -- 單繼承/無繼承
module(..., package.seeall, class.inherit(A, B, C))  -- 多重繼承 mixin
```

- **`class.make(c)`**：將 module table 升格為類別，注入 `new()`、`castAs()` 方法。
- **`class.inherit(...bases)`**：多重繼承，將所有 base 的欄位**快取複製**到子類別（而非 `__index` 鏈），避免查找開銷。繼承順序為左到右、後者覆蓋前者。

### 1.2 物件實例化

```lua
local obj = MyClass.new(...)
-- 等同於：
local obj = {}
obj.__CLASSNAME = "module.name"
obj.__ATOMIC = true
setmetatable(obj, {__index = MyClass})
obj:init(...)
```

- `__CLASSNAME`：字串，用於存檔/讀檔時重建 metatable。
- `__ATOMIC = true`：標記此 table 為物件，不做深拷貝。

### 1.3 Clone 機制

| 方法 | 說明 |
|------|------|
| `obj:clone(t)` | 淺拷貝，選擇性合併 `t` |
| `obj:cloneFull()` | 遞迴深拷貝，相同子物件只拷貝一次（cyclic safe），呼叫各子物件的 `:cloned()` |
| `obj:cloneCustom(alt_nodes, type_checker)` | 可自訂跳過/替換特定節點的深拷貝 |
| `obj:cloneForSave()` | 同 cloneFull 但不呼叫 `:cloned()`，僅用於序列化前準備 |
| `obj:cloneReloaded()` | 讀檔後重建 metatable 並呼叫所有 `:loaded()` |
| `obj:replaceWith(t)` | 就地替換物件內容（in-place），不改變引用 |

### 1.4 Hook & Event 系統

```lua
class:bindHook("ActorAI:act", function(self, data) ... end)
self:triggerHook{"ActorAI:act", key=val, ...}
```

- **`bindHook(hook, fct)`**：將 handler 加入指定 hook。每次 bind 後會動態重新生成一個 closure，把所有 handler 串成一個函數（避免 table 查找）。
- **`triggerHook(hook_table)`**：呼叫該 hook 的所有 handler，任一 handler 回傳 `true` 則整體回傳 `true`。
- `__persistent_hooks`：存入存檔的 hook，讀檔時自動重新 bind。

### 1.5 存檔整合

```lua
obj:save(filter, allow)
class.load(str, delayloading)
```

- 存檔：將物件序列化為 Lua 字串並寫入 zip（每個物件一個檔案），由 `engine.Savefile` 管理。
- 讀檔：反序列化字串，根據 `__CLASSNAME` 重設 metatable，呼叫 `:loaded()`。
- `loadNoDelay = true`：強制同步呼叫 `:loaded()`（不延遲），用於 Shader 等需立即初始化的物件。

---

## 2. 實體系統 (`engine/Entity.lua`)

### 2.1 核心屬性

```lua
-- 每個 Entity 都有唯一的 uid
self.uid = next_uid
__uids[self.uid] = self   -- 全局弱引用表，可用 uid 快速查找
```

- `__uids`：弱值 table（`{__mode="v"}`），實體無任何其他引用時自動 GC。
- `__position_aware`：子類別設為 `true` 表示此實體在地圖上有位置（Actor、Trap 等）。

### 2.2 初始化流程

```lua
Entity.new{display='@', color_r=255, name="Player", ...}
```

1. 分配 uid，加入 `__uids`。
2. 將傳入 table 的所有欄位複製到 self（table 類型做 `table.clone`）。
3. 展開顏色 shorthand（`color` → `color_r/g/b`，`tint` → `tint_r/g/b`）。
4. 若有 `embed_particles`，立即附加粒子系統。
5. Debug 模式下檢查 upvalue（禁止實體 definition 裡使用 closure）。

### 2.3 Define / Resolve 兩階段生命週期

實體有兩個階段：
- **Prototype（定義期）**：在 zone/npc.lua 等定義檔中建立，屬性可以是 resolver 佔位符。
- **Instance（實例期）**：從 prototype clone 出來並呼叫 `:resolve()`，resolver 替換為實際值。

```lua
-- 定義期（prototype）
local npc_proto = Actor.define{
    name = "Goblin",
    level = resolvers.rngrange(1, 5),      -- 等 resolve 再算
    talents = resolvers.talents{[T_ATTACK]=1},
}

-- 實例期
local npc = npc_proto:clone()
npc:resolve()  -- 此時 level 變成真實數字，talents 被學習
```

---

## 3. Resolver 系統 (`engine/resolvers.lua`)

Resolver 是一個「延遲計算」框架，讓實體定義可以包含亂數、條件邏輯，直到 resolve 時才實際執行。

### 3.1 Resolver 結構

```lua
resolvers.foo(...)    -- 回傳 {__resolver="foo", ...data...}
resolvers.calc.foo(t, e)  -- 實際計算，t=resolver table，e=entity
```

- `__resolve_instant = true`：在其他 resolver 之前優先執行。

### 3.2 內建 Resolvers

| Resolver | 說明 |
|----------|------|
| `resolvers.rngrange(x, y)` | 隨機整數 [x, y] |
| `resolvers.rngfloat(x, y)` | 隨機浮點數 |
| `resolvers.rngavg(x, y)` | 平均隨機（更集中於中間值） |
| `resolvers.dice(x, y)` | xdy 擲骰 |
| `resolvers.rngtable(t)` | 從 table 隨機取一個值 |
| `resolvers.mbonus(max, add)` | 依當前層數縮放的加成（越深越強） |
| `resolvers.talents(list)` | 學習技能列表 |
| `resolvers.rngtalent(list)` | 從列表隨機學一個技能 |
| `resolvers.rngtalentsets(list)` | 從集合隨機選一組技能 |
| `resolvers.tmasteries(list)` | 設定技能類型熟練度 |
| `resolvers.inventory(list)` | 生成物品放入揹包 |
| `resolvers.drops(list)` | 定義死亡掉落物 |
| `resolvers.equip(list)` | 生成物品並裝備 |
| `resolvers.racial()` | 種族特性 |
| `resolvers.sustains_at_birth()` | 出生時啟動持續技能 |

`resolvers.current_level` 是全局變數，生成前由 Zone 設定，讓 mbonus 等 resolver 感知當前深度。

---

## 4. 世界結構

```
World
 └─ Zone（地區，如「迷宮 A」）
     └─ Level（樓層，如「B1F」）
         └─ Map（地圖格資料）
         └─ [Actor, ...]（本層的角色列表）
```

### 4.1 Map (`engine/Map.lua`)

Map 是一個二維格子，每格可存放多個實體，以「Z 層」區分：

| 常數 | 值 | 說明 |
|------|----|------|
| `Map.TERRAIN` | 1 | 地形/牆壁 |
| `Map.TRAP` | 50 | 陷阱 |
| `Map.ACTOR` | 100 | 角色/怪物 |
| `Map.PROJECTILE` | 500 | 投射物 |
| `Map.OBJECT` | 1000 | 物品 |
| `Map.TRIGGER` | 10000 | 觸發器 |

```lua
map(x, y, Map.TERRAIN)           -- 讀取 (x,y) 的地形
map(x, y, Map.ACTOR, actor)      -- 設定 (x,y) 的 Actor
map:checkAllEntities(x, y, "block_move", self)  -- 遍歷 (x,y) 所有實體，查詢方法
```

**視野顯示**：
- `color_shown = {1,1,1,1}` / `color_obscure = {0.6,0.6,0.6,0.5}`：已看見但不在 FOV 內的格子會以暗色顯示。
- `smooth_scroll`：平滑滾動支援。
- 戰術圖示（`faction_friend/enemy/neutral/danger`）：在 Actor 上方覆蓋陣營顏色標記。

**Viewport**：`setViewPort(x, y, w, h, tile_w, tile_h)` 設定地圖在螢幕上的繪製區域與圖磚大小。

### 4.2 Zone (`engine/Zone.lua`)

Zone 負責：
- 設定要使用哪些 class（`zone:setup{npc_class, grid_class, object_class, ...}`）
- 管理多個 Level（含 sublevel 支援）
- 載入 zone 定義檔（`data/zones/<short_name>/zone.lua`）
- **Ego 系統**：`Zone.ego_rules` 定義如何將 ego（前綴/後綴修飾）套用到實體上，類似物品詞綴。
- **Last Persist Zones**：LRU cache，最近造訪的 zone 保留在記憶體，減少磁碟讀寫。
- **`ood_factor`（Out-of-Depth factor）**：控制生成比當前層深多少的怪物機率。

---

## 5. 遊戲迴圈

### 5.1 GameEnergyBased (`engine/GameEnergyBased.lua`)

核心 tick 邏輯：

```lua
function _M:tick()
    -- 1. 給所有實體加 energy
    for i, e in pairs(self.entities) do
        e.energy.value += energy_per_tick * e.energy.mod * e.global_speed
    end

    -- 2. 讓 energy 足夠的實體行動
    if e.energy.value >= energy_to_act then
        e:act()
    end
end
```

- **預設值**：`energy_to_act = 1000`，`energy_per_tick = 100`。
- **速度機制**：`energy.mod`（個體速度修正），`global_speed`（全局縮放）。
- **全局實體表**：`self.entities`（弱值 table），Actor 進入 Level 時自動加入。

### 5.2 GameTurnBased (`engine/GameTurnBased.lua`)

繼承 GameEnergyBased，加上暫停機制：

```lua
function _M:tick()
    if self.paused then
        -- 若玩家 energy 不足（已行動），自動取消暫停
        if not player:enoughEnergy() then self.paused = false end
        engine.Game.tick(self)   -- 只跑動畫/事件，不推進遊戲時間
    else
        engine.GameEnergyBased.tick(self)
    end
end
```

**回合制流程**：
1. 玩家 `act()` 呼叫時設 `game.paused = true`，等待輸入。
2. 玩家做出行動後（移動/攻擊/…）消耗 energy，設 `game.paused = false`。
3. 引擎繼續 tick，所有 NPC 補充並消耗 energy 直到輪到玩家。

---

## 6. Actor 介面混入 (`engine/interface/`)

所有介面以 mixin 方式注入，Actor 子類別透過 `class.inherit(engine.Actor, interface.ActorTalents, ...)` 組合。

### 6.1 ActorTalents — 技能系統

**靜態定義（全局共用）**：
```lua
-- 定義技能類型（分類）
self:newTalentType{type="spell/fire", name="Fire Spells", points=1}

-- 定義技能
self:newTalent{
    name = "Fireball",
    type = {"spell/fire", 1},
    mode = "activated",   -- activated | sustained | passive
    cooldown = 10,
    use_power = {base=20, add=5, ...},
    action = function(self, t) ... end,
    info = function(self, t) return "Throws a fireball" end,
}
-- 自動生成 T_FIREBALL 常數
```

**實例資料**：
- `self.talents` — `{T_FIREBALL = 3}` 技能 ID → 等級。
- `self.talents_cd` — `{T_FIREBALL = 5}` 目前冷卻剩餘。
- `self.sustain_talents` — `{T_SHIELD = true}` 已開啟的持續技能。
- `self.talents_types` — 技能類型解鎖狀態。
- `self.talents_types_mastery` — 熟練度修正（影響效果縮放）。

**Resolver 整合**：`resolvers.talents{[T_FIREBALL]=2}` 在 resolve 時呼叫 `:learnTalent()`。

### 6.2 ActorTemporaryEffects — Buff/Debuff 系統

**靜態定義**：
```lua
self:newEffect{
    name = "BURNING",
    desc = "On fire",
    type = "magical",
    status = "detrimental",
    decrease = 1,   -- 每回合減少 duration
    activation = function(self, eff) self:setAttr("on_fire", 1) end,
    deactivation = function(self, eff) self:setAttr("on_fire", -1) end,
    on_timeout = function(self, eff) self:takeDamage(eff.power) end,
}
-- 自動生成 EFF_BURNING 常數
```

**實例**：
```lua
self.tmp = {EFF_BURNING = {dur=5, power=10, ...}}
```

每回合呼叫 `:timedEffects()` 倒數，到期呼叫 `deactivation`。

### 6.3 ActorStats — 屬性系統

- 靜態定義屬性（透過 `newStat`）：名稱、最大值、加法/乘法計算。
- `self:getStat("str")` → 考慮 buff/debuff 後的最終值。
- `self:addStat("str", 10)` → 暫時性加成（TemporaryEffects 或裝備使用）。

### 6.4 ActorFOV — 視野

```lua
actor:computeFOV(range, "block_sight", function(x, y, dx, dy, sqdist)
    -- 標記 seen / los
end)
```

- 呼叫 C 層 `core.fov.calc_*`（recursive shadowcasting）。
- `actor:hasLOS(x, y)` 快速查詢兩點間直線視野。
- `actor:lineFOV(x, y)` 取得 FOV 線迭代器（用於投射物路徑）。

### 6.5 ActorProject — 投射與傷害系統

```lua
self:project(
    {type="bolt", range=5, block_path=function(...)end},
    target_x, target_y,
    DamageType.FIRE,   -- 傷害類型
    100,               -- 傷害量
    particles           -- 粒子特效
)
```

`project` 內部流程：
1. 呼叫 `Target:getType(t)` 解析形狀（bolt/beam/ball/cone/…）。
2. 用 `lineFOV` 迭代器逐格推進，判斷 `block_path`。
3. 角落阻擋特例處理（避免死角無法被打到的問題）。
4. 對每個命中格呼叫 `DamageType.project(src, x, y, type, dam)`。
5. 若有 `create_projectile`，生成 Projectile 實體做飛行動畫後再傷害。

### 6.6 ActorInventory — 揹包系統

- `self.inven` — 多個 slot table（`INVEN_MAINHAND`, `INVEN_OFFHAND`, `INVEN_BODY`, …）。
- `self:addObject(inven_id, obj)` / `self:removeObject(inven_id, slot)`。
- `self:wearObject(obj)` — 裝備到適當位置，觸發 `on_wear/on_takeoff` callback。
- Weight/encumbrance、比較物品屬性、自動合併堆疊（stack）。

### 6.7 ActorLife — 生命值與死亡

- `self:takeHit(dam, src)` — 扣血入口，觸發 `on_takehit`、`on_die`。
- `self:die(src)` — 觸發死亡流程：掉落物品、移除陣列、成就判定。
- 分離出 `canBe("dead")` 等 attr 查詢，讓模組可自訂免死條件。

### 6.8 ActorAI — AI 系統

AI 是命名行為的組合：

```lua
-- 定義 AI
newAI("move_simple", function(self)
    if self.ai_target.actor then
        self:moveDirection(self.ai_target.actor.x, self.ai_target.actor.y)
    end
end)

-- 實體使用
npc.ai = "dumb_talented"    -- 主 AI
npc.ai_state = {talent_in=3}  -- AI 狀態參數
```

**內建 AI 行為**（`engine/ai/`）：
| AI 名稱 | 說明 |
|---------|------|
| `move_simple` | 直線朝目標移動 |
| `move_dmap` | 使用距離地圖（Dijkstra）尋路 |
| `flee_simple` | 遠離目標 |
| `target_simple` | 選定最近的敵對 Actor 為目標 |
| `dumb_talented` | 隨機使用可用技能 + move_simple |
| `talented` | 智慧技能選擇（`engine/ai/talented.lua`） |
| `special_movement.*` | 飛行、穿牆、游泳等特殊移動 |

`self:runAI(name, ...)` 呼叫對應的 `ai_def[name](self, ...)`，AI 可互相組合。

**AI 目標與記憶**：
- `self.ai_target.actor` — 當前目標。
- `self.ai_state.target_last_seen` — 最後看見目標的位置（失去 LOS 後仍往此移動）。
- `self.ai_actors_seen` — 曾看見過的所有 Actor（弱引用）。

---

## 7. 傷害類型系統 (`engine/DamageType.lua`)

```lua
DamageType:newDamageType{
    name = "FIRE",
    type = "fire",
    text_color = "#r#",
    projector = function(src, x, y, type, dam)
        -- 對 (x,y) 的 ACTOR 造成 dam 點火焰傷害
        local target = game.level.map(x, y, Map.ACTOR)
        if target then target:takeHit(dam, src) end
    end,
}
-- 自動生成 DamageType.FIRE 常數
```

- 每種傷害類型都有獨立的 projector 函數，由 `ActorProject:project()` 呼叫。
- 模組可自由定義新傷害類型（毒、神聖、冥界、…）。

---

## 8. 目標系統 (`engine/Target.lua`)

```lua
-- 描述投射形狀
{type = "bolt", range = 10}              -- 直線單目標
{type = "beam", range = 10}              -- 直線貫穿
{type = "ball", range = 5, radius = 3}  -- 球形 AOE
{type = "cone", range = 8, cone_angle = 45}  -- 扇形
{type = "hit"}                           -- 直接命中
```

- `Target:getType(t)` 解析 type 描述，回傳包含 `block_path`、`block_radius` 等函數的完整 typ table。
- 目標系統也負責 UI 層的目標選擇顯示（紅色游標、射程顯示）。
- `self.target = {x, y, entity}` 追蹤當前目標，entity 為弱引用（目標死後自動清空）。
- FBO 渲染模式下可做半透明 overlay 效果。

---

## 9. 地圖生成系統 (`engine/generator/`)

### 9.1 Generator 基底

所有 generator 繼承 `engine.Generator`，實作 `:generate(lev, old_lev)` 方法。

```lua
-- Zone 定義中指定 generator
generator = {
    map = {class="engine.generator.map.Roomer", -- 地圖 generator
           floor = "FLOOR", wall = "WALL", ...},
    actor = {class="engine.generator.actor.Random",
             nb_npc = {10, 15}, ...},
    object = {class="engine.generator.object.Random",
              nb_object = {3, 5}, ...},
}
```

### 9.2 主要地圖生成器

**Rooms（`engine/generator/map/Rooms.lua`）**：
- 遞迴 BSP 切割（預設 10 次）產生房間。
- 每個最終房間記錄一個 spot，用於放置出口、NPC。
- 最簡單、效能最高的地牢生成器。

**RoomsLoader（`engine/generator/map/RoomsLoader.lua`）**：
- 從預定義的 room template 檔案（`.lua`）讀取房間形狀。
- 用 MST（最小生成樹）連接所有房間，確保連通性。
- 支援 special rooms（boss 房、寶庫等）。

**Cavern**：
- 隨機洞窟，使用細胞自動機（多次 smooth 迭代）。

**Maze**：
- 標準迷宮演算法（recursive backtracking）。

**Forest**：
- Perlin noise 決定樹木/草地分佈。

**Heightmap**：
- 高度圖轉換為地形（山脈、平原、水域）。

**WaveFunctionCollapse**：
- 呼叫 C++ WFC 核心（`src/wfc/`），從樣本圖案學習並生成一致的地圖。

**Static**：
- 從 `.lua` 腳本直接讀取手工設計的地圖（多用於 boss 房、城鎮）。

**GOL（Game of Life）**：
- 多代細胞自動機生成有機感的洞穴。

### 9.3 Tilemap 中間表示（`engine/tilemaps/`）

部分生成器先產生抽象 tilemap（字元代號），再映射到實際 Entity。`Tilemap.lua` 提供此轉換。

---

## 10. 存檔系統 (`engine/Savefile.lua` + `engine/SavefilePipe.lua`)

### 10.1 存檔格式

每次存檔 = 一個 **zip 檔案**，內含多個 Lua 序列化字串：

```
/save/<player_name>/
    save.lua          -- 頂層 game 物件入口
    <hash1>.lua       -- 某個子物件（Level、Actor、...）
    <hash2>.lua
    ...
```

每個物件序列化為：
```lua
setLoaded("hash1", {
    __CLASSNAME = "game.actor.Player",
    name = "Bob", level = 5,
    _actor_ref_ = loadObject("hash2"),  -- 跨物件引用
    ...
})
```

### 10.2 存檔流程

1. `game:save()` → `Savefile:init(name)` → 建立 zip。
2. `game:save(filter)` → `core.serial.new()` → 序列化根物件。
3. 遞迴遇到子物件 → `addToProcess(t)` → 排隊，後續序列化為獨立檔案。
4. 相同物件引用 → `loadObject(hash)` 取代（避免重複儲存）。
5. 完成後關閉 zip，可選 Steam Cloud 上傳。

### 10.3 讀檔流程

1. `Savefile:load()` → 解壓 zip 到 `/tmp/loadsave/`。
2. `class.load(str)` 反序列化字串，遇到 `loadObject` 就遞迴讀取子物件。
3. 設回 metatable（根據 `__CLASSNAME`）。
4. 延遲呼叫 `:loaded()`（確保相互引用都已建立後才初始化）。

### 10.4 SavefilePipe

後台存檔（background save）：
- 主執行緒繼續遊戲，存檔在 coroutine 中分批進行。
- 每次 yield 讓出控制權，避免卡頓。

### 10.5 MD5 完整性

- 部分類型的存檔啟用 MD5 校驗（`Savefile:setSaveMD5Type(type)`）。
- 讀取時若 MD5 不符記錄到 `bad_md5_loaded`，可用來偵測存檔修改。

---

## 11. UI 框架 (`engine/ui/`)

### 11.1 Base (`engine/ui/Base.lua`)

所有 UI 元件的基底，提供：
- **字型**：`font`（DroidSans 12pt）、`font_mono`（等寬）、`font_bold`。
- **UI 主題**：`ui = "dark"`（可換皮），透過 `loadUIDefinitions(file)` 載入主題設定（顏色、圖片路徑）。
- **材質快取**：`cache` / `tcache`，避免重複載入圖像。
- **音效**：`sounds.button` 等互動音效。

### 11.2 Dialog (`engine/ui/Dialog.lua`)

視窗基底，提供：
```lua
local d = Dialog.new("Title", width, height)
d:loadUI{
    {left=3, top=3, ui=Button.new{...}},
    {right=3, bottom=3, ui=List.new{...}},
}
d:setupUI(auto_w, auto_h)  -- 自動計算大小
game:registerDialog(d)
```

- **Layout**：`{left, right, top, bottom, vcenter, hcenter}` 錨點定位，支援相對座標。
- **Modal 堆疊**：`game.dialogs` 是個堆疊，頂部 dialog 接收輸入。
- **工廠方法**：`simplePopup`, `simpleWaiter`, `simpleWaiterTip` 等快速建立常用對話框。

### 11.3 主要 UI 元件

| 元件 | 特色 |
|------|------|
| `Button` | 點擊回調，可禁用 |
| `List` | 可選清單，支援鍵盤操作，高亮當前行 |
| `ListColumns` | 多欄清單，可調整欄寬 |
| `TreeList` | 可展開/收合的樹狀清單 |
| `Textzone` | 富文本顯示（支援顏色 tag），可滾動 |
| `TextzoneList` | 多段文字 + 條目選擇 |
| `Textbox` | 單行輸入框，支援 Unicode |
| `Numberbox` | 數字輸入框 |
| `Slider` / `NumberSlider` | 滑桿 |
| `Checkbox` | 勾選框 |
| `Dropdown` | 下拉選單 |
| `Tabs` | 標籤頁切換 |
| `ImageList` | 圖像格狀選擇（技能、物品圖示列表） |
| `EquipDoll` | 人形裝備圖（點擊對應部位） |
| `EntityDisplay` | 顯示實體的圖像與描述 |
| `Waitbar` / `Waiter` | 進度條（loading 等） |
| `WebView` | 嵌入網頁（CEF3/Awesomium） |
| `UIContainer` / `UIGroup` | 容器/群組佈局 |
| `SurfaceZone` | 自由繪製區域（GL surface） |

### 11.4 輸入整合

每個 Dialog 持有獨立的 `KeyBind` 和 `Mouse` 實例，`setCurrent()` 後接收事件。

---

## 12. 輸入系統

### 12.1 KeyCommand (`engine/KeyCommand.lua`)

底層按鍵處理：
- `key:addCommands{...}` 直接綁定 SDL keysym → callback。
- `key:setCurrent()` 讓此 handler 成為當前接收者。

### 12.2 KeyBind (`engine/KeyBind.lua`)

虛擬動作系統（在 KeyCommand 上）：

```lua
-- 定義虛擬動作（在 /data/keybinds/move.lua）
defineAction{
    type = "MOVE_LEFT",
    name = "Move Left",
    default = { {"left"}, {"numpad4"} },
}

-- 綁定動作 → callback
key:bindToCommand("MOVE_LEFT", function() player:moveDir(4) end)
```

- 玩家可在設定介面重新映射（`dialogs/KeyBinder.lua`）。
- 重映射存入 `/settings/keybinds2.cfg`。

---

## 13. 任務系統 (`engine/Quest.lua`)

```lua
-- 定義任務
local quest = Quest.new({
    name = "Kill the Dragon",
    desc = "...",
    on_grant = function(self, who) ... end,
    on_status_change = function(self, who, status, sub) ... end,
}, player)

-- 更新子目標
quest:setSubCompleted("find_lair")
quest:setCompleted()  -- 完成整個任務
```

**狀態機**：
- `PENDING (0)` → `COMPLETED (1)` → `DONE (100)`
- `PENDING (0)` → `FAILED (101)`

Hook 整合：`triggerHook{"Quest:init"}`, `triggerHook{"Quest:completed"}` 讓模組監聽任務事件。

---

## 14. 玩家自動化功能

### 14.1 PlayerRest (`engine/interface/PlayerRest.lua`)

```lua
player:restInit(turns, "resting", "rested", on_end_callback)
```

每回合呼叫 `:restCheck()` 判斷是否應停止（受傷、敵人出現、HP/MP 滿等），子類別覆寫此方法。

### 14.2 PlayerExplore (`engine/interface/PlayerExplore.lua`)

Flood-fill 自動探索：
1. 以 BFS/Dijkstra 找出所有可達、但未探索的格子。
2. 對最近的未探索目標走 A*。
3. 若有物品/出口在視野內，優先前往撿取。
4. 每步行動後重新計算（處理門、新視野）。

### 14.3 PlayerRun (`engine/interface/PlayerRun.lua`)

直線快速移動：沿指定方向連續移動，遇到岔路口、敵人、物品停止。

---

## 15. 渲染相關系統

### 15.1 Tiles (`engine/Tiles.lua`)

- 維護圖磚材質 repo（`self.repo`），已載入的圖像以路徑為 key 快取。
- `loadTileset(file)`：載入圖磚集定義（大圖切片），批量定義多個圖磚。
- 支援 addon 路徑（`addonname+gfx/image.png` → `/data-addonname/gfx/image.png`）。

### 15.2 Shader (`engine/Shader.lua`)

```lua
local shader = Shader.new("fire_effect", {require_kind="distort"})
-- 找 /data/gfx/shaders/fire_effect.vert + .frag
```

- **延遲載入**：`delay_load = true` 時，第一次存取 `shader.shad` 才實際編譯。
- **LRU 清理**：`cleanup()` 定期刪除長時間未用的 temp shader。
- `core.shader.allow(kind)` 檢查使用者設定（`shaders_kind_distort` 等）。

### 15.3 Particles (`engine/Particles.lua`)

```lua
local p = Particles.new("flame", radius=1, {size=2, density=50})
actor:addParticles(p)
```

- 粒子定義在 `/data/gfx/particles/*.lua`，描述粒子行為、壽命、顏色曲線。
- C 層維護粒子物理計算（`src/particles.c`）。
- `__particles_gl` 弱引用 table 防止 GC 前仍被渲染。

### 15.4 FlyingText (`engine/FlyingText.lua`)

飄字特效（傷害數字、獲得 XP 等）：
- 建立一個短暫的文字動畫，從指定位置浮起並淡出。

---

## 16. 在線與 Profile 系統

### 16.1 PlayerProfile (`engine/PlayerProfile.lua`)

```lua
profile = PlayerProfile.new()
profile:start()   -- 啟動後台 profile thread
```

- 在獨立 thread 處理與 te4.org 的通訊（防止主執行緒阻塞）。
- 功能：登入、排行榜提交、成就同步、角色 vault 上傳、在線聊天。

### 16.2 UserChat (`engine/UserChat.lua`)

全局頻道聊天，使用 LuaSocket 連接 te4.org 伺服器。

### 16.3 MicroTxn (`engine/MicroTxn.lua`)

Steam DLC 微交易整合，透過 `core.steam` API。

---

## 17. 在地化系統 (`engine/I18N.lua`)

```lua
local I18N = require "engine.I18N"
I18N:loadLocale("/data/locales/engine/zh.lua")
I18N:setLocale("zh")

-- 使用
_t"Hello World"   -- 翻譯字串
_t("Hello %s", name)  -- 帶參數
```

- 翻譯資料以 Lua table 形式儲存（`{["Hello World"] = "你好世界"}`）。
- 技能名稱、效果描述等在 `newTalent/newEffect` 時自動呼叫 `_t()`。

---

## 18. 關鍵設計模式總結

| 模式 | 應用 |
|------|------|
| **Mixin 繼承** | `engine/interface/` 所有介面，Actor 按需組合 |
| **Data-driven 定義** | `newTalent`, `newEffect`, `newDamageType` — 數據與邏輯在同一個定義 table |
| **兩階段初始化** | Entity define（原型）→ resolve（實例），支援延遲亂數計算 |
| **命名行為** | AI 系統以字串 key 組合行為，可在運行時動態切換 |
| **弱引用追蹤** | `__uids`, `entities`, `ai_target`，讓 GC 自然清理已死亡實體 |
| **每物件存一檔** | 存檔用 zip 內多 Lua 檔，跨物件引用用 hash 連結，天然支援 graph 結構 |
| **Hook 系統** | 模組可在不修改引擎的情況下，在任何 hook 點注入邏輯 |
| **延遲載入** | Shader、部分存檔物件，首次使用時才真正初始化 |
