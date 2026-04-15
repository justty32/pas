# T-Engine 4 — engine/ 原始碼詳細分析

> 原始碼位於 `game/engines/te4-1.7.6/engine/`（解壓自 `te4-1.7.6.teae`）。

---

## 目錄

1. [OOP 基礎系統 (class.lua)](#1-oop-基礎系統-classlua)
2. [實體系統](#2-實體系統)
   - Entity、Actor、Grid、Object、Trap、Projectile
3. [世界結構](#3-世界結構)
   - World、Zone、Level、Map、MapEffect
4. [遊戲迴圈](#4-遊戲迴圈)
   - Game、GameEnergyBased、GameTurnBased
5. [Resolver 延遲計算系統 (resolvers.lua)](#5-resolver-延遲計算系統-resolverslua)
6. [Actor 介面混入 (interface/)](#6-actor-介面混入-interface)
7. [玩家介面混入](#7-玩家介面混入)
8. [傷害類型系統 (DamageType.lua)](#8-傷害類型系統-damagetypelua)
9. [目標系統 (Target.lua)](#9-目標系統-targetlua)
10. [程序地圖生成系統 (generator/)](#10-程序地圖生成系統-generator)
11. [AI 系統 (ai/)](#11-ai-系統-ai)
12. [演算法 (algorithms/)](#12-演算法-algorithms)
13. [Tilemap 中間表示 (tilemaps/)](#13-tilemap-中間表示-tilemaps)
14. [存檔系統 (Savefile.lua)](#14-存檔系統-savefilelua)
15. [渲染支援系統](#15-渲染支援系統)
16. [UI 框架 (ui/)](#16-ui-框架-ui)
17. [輸入系統](#17-輸入系統)
18. [支援系統](#18-支援系統)
19. [關鍵設計模式總結](#19-關鍵設計模式總結)

---

## 1. OOP 基礎系統 (class.lua)

T-Engine 4 在 Lua 5.1 上自行實作了一套物件導向系統，是整個引擎的地基。

### 類別建立

```lua
module(..., package.seeall, class.make)               -- 無繼承
module(..., package.seeall, class.inherit(A, B, C))   -- 多重繼承 mixin
```

| 方法 | 說明 |
|------|------|
| `class.make(c)` | 將 module table 升格為類別，注入 `new()`、`castAs()` |
| `class.inherit(...bases)` | 多重繼承：將所有 base 欄位**快取複製**到子類別（非 `__index` 鏈），左到右、後者覆蓋 |
| `getClassName()`, `getClass()`, `isClassName(name)` | 類別自省 |

### 物件實例化

```lua
local obj = MyClass.new(...)
-- 等同：obj.__CLASSNAME = "module.name"; setmetatable(obj, {__index=MyClass}); obj:init(...)
```

- `__CLASSNAME`：字串，存檔/讀檔時重建 metatable 用
- `__ATOMIC = true`：標記此 table 為物件，不做深拷貝

### Clone 機制

| 方法 | 說明 |
|------|------|
| `obj:clone(t)` | 淺拷貝，選擇性合併 `t` |
| `obj:cloneFull(post_copy)` | 遞迴深拷貝，cyclic safe，呼叫子物件 `:cloned()` |
| `obj:cloneCustom(alt_nodes, type_checker)` | 可自訂跳過/替換特定節點的深拷貝 |
| `obj:cloneForSave()` | 同 cloneFull 但不呼叫 `:cloned()`，用於序列化前 |
| `obj:cloneReloaded()` | 讀檔後重建 metatable 並呼叫所有 `:loaded()` |
| `obj:replaceWith(t)` | 就地替換物件內容（in-place），不改變引用 |

### Hook & Event 系統

```lua
class:bindHook("ActorAI:act", function(self, data) ... end)
self:triggerHook{"ActorAI:act", key=val, ...}
```

- `bindHook`：每次 bind 後動態重新生成一個 closure，把所有 handler 串成一個函數（避免 table 查找）
- `triggerHook`：任一 handler 回傳 `true` 則整體回傳 `true`
- `__persistent_hooks`：存入存檔的 hook，讀檔時自動重新 bind

### 存檔整合

- 存檔：序列化為 Lua 字串寫入 zip（每個物件一個檔案），由 `engine.Savefile` 管理
- 讀檔：反序列化字串，根據 `__CLASSNAME` 重設 metatable，呼叫 `:loaded()`
- `_no_save_fields`：排除在序列化之外的欄位列表

---

## 2. 實體系統

### Entity.lua — 所有遊戲物件的基底

**核心屬性**
- `uid`：唯一識別碼；加入全域弱值表 `__uids[uid] = self`（GC 安全）
- `__position_aware`：子類別設 `true` 表示此實體在地圖上有位置

**初始化流程**（`Entity.new{...}`）
1. 分配 uid、加入 `__uids`
2. 複製傳入 table 所有欄位（table 類型做 `table.clone`）
3. 展開顏色 shorthand（`color` → `color_r/g/b`）
4. 若有 `embed_particles`，立即附加粒子系統
5. Debug 模式下檢查 upvalue（禁止 closure 在 definition 內）

**Define / Resolve 兩階段生命週期**

| 階段 | 說明 |
|------|------|
| Prototype（定義期） | 屬性可為 resolver 佔位符；在 zone/npc.lua 中建立 |
| Instance（實例期） | clone 後呼叫 `:resolve()`，resolver 替換為實際值 |

**臨時值系統**

```lua
local id = self:addTemporaryValue("combat_def", 10)  -- 加成
self:removeTemporaryValue("combat_def", id)           -- 撤銷（ID 追蹤）
```

支援多種應用模式：`add`、`mult`、`mult0`、`perc_inv`、`inv1`、`highest`、`lowest`、`last`。

**主要方法**

| 方法 | 說明 |
|------|------|
| `resolve(t, last, on_entity, key_chain)` | 執行所有 resolver，將 prototype 轉為 instance |
| `makeMapObject(tiles, idx)` | 建立地圖視覺物件 (MapObject) |
| `addParticles(ps)` / `removeParticles(ps)` | 粒子系統管理 |
| `toScreen(tiles, x, y, w, h, a, ...)` | 渲染到螢幕 |
| `addTemporaryValue(prop, v)` / `removeTemporaryValue(prop, id)` | 可撤銷屬性加成 |
| `check(prop, ...)` | 屬性 getter（若值為函數則呼叫之） |
| `attr(prop, v, fix)` | 屬性 getter/setter，含 fallback |
| `loadList(file, no_default, res, mod)` | 從 Lua 檔載入實體定義列表 |

---

### Actor.lua — 角色/怪物基底

繼承自 Entity，增加角色行為：

| 欄位/方法 | 說明 |
|-----------|------|
| `x`, `y` | 位置（**勿直接設定**，使用 `move()`） |
| `energy` | `{value, mod}` 行動點累積池 |
| `faction` | 陣營識別符 |
| `sight` | 視野範圍 |
| `dead` | 死亡旗標 |
| `act()` | 每回合被呼叫，允許行動 |
| `move(x, y, force)` | 移動（含碰撞/攻擊判斷） |
| `moveDir(dir, force)` | 八方向移動 |
| `setupMinimapInfo(mo, map)` | 根據陣營關係設小地圖顏色 |
| `setEmote(e)` | 附加表情粒子 |
| `defineDisplayCallback()` | 設定粒子與戰術顯示 callback |

---

### Grid.lua — 地形格

- 極簡介面，主要用於地圖裝飾與移動阻擋
- `block_move(x, y, e, act, couldpass)` — 移動阻擋邏輯
- `setupMinimapInfo(mo, map)` — 依可通行性設小地圖顏色
- `_noalpha` — 停用 alpha 通道渲染

---

### Object.lua — 物品/裝備

| 功能 | 方法 |
|------|------|
| 堆疊管理 | `stackable()`, `canStack(o)`, `stack(o)`, `unstack(num)`, `forAllStack(fct)` |
| 裝備 | `wornInven()`, `slot`, `require` |
| 命名 | `getName(t)`, `getDesc()` |
| 需求描述 | `getRequirementDesc(who)` — 帶顏色標記（已滿足/未滿足） |
| 排序 | `getTypeOrder()`, `getSubtypeOrder()` |

`stacking`（預設為名稱）決定堆疊識別符；`stacked` table 追蹤堆疊內容。

---

### Trap.lua — 陷阱

| 欄位/方法 | 說明 |
|-----------|------|
| `triggered` | 觸發 callback（必填），回傳 `(known, delete)` |
| `disarmable` | 可否解除 |
| `detect_power`, `disarm_power` | 難度評等 |
| `known_by` | 弱引用 table，追蹤知道此陷阱的角色 |
| `setKnown(actor, v)` / `knownBy(actor)` | 知曉狀態管理 |
| `canDisarm(x, y, who)` / `disarm(x, y, who)` | 解除邏輯 |
| `trigger(x, y, who)` | 觸發陷阱 |
| `on_move(x, y, who, forced)` | 踩到時自動觸發 |

---

### Projectile.lua — 投射物

| 欄位/方法 | 說明 |
|-----------|------|
| `project` | `{def: {typ, x, y, tg, damtype, dam, particles}}` 投射定義 |
| `homing` | `{target, count, on_hit, on_move}` 追蹤飛彈資料 |
| `travel_particle`, `trail_particle` | 飛行/軌跡粒子 |
| `src` | 發射來源 Actor |
| `move(x, y, force)` | 移動（帶粒子/軌跡處理） |
| `makeProject(src, display, def, ...)` | 工廠方法 |
| `act()` | 每回合執行移動/行動 |

支援兩種模式：預計算路徑（projectile-type）與追蹤飛彈（homing）。

---

## 3. 世界結構

```
World
 └─ Zone（地區，如「迷宮 A」）
     └─ Level（樓層，如「B1F」）
         ├─ Map（地圖格資料 + 渲染）
         └─ [Actor, ...]（本層角色列表）
```

### World.lua

純基底類別；一個存檔一個實例，跨角色死亡持久存在。僅提供 `init()` 與 `run()` 生命週期掛點。

---

### Zone.lua — 地區生成協調器

**主要職責**
- 載入 zone.lua 定義（`short_name`, `max_level`, `level_range`, `generator`, `levels`）
- 協調地圖/Actor/Object/Trap 生成器
- 管理多層 Level（含持久化：`persistent = "zone" | "level" | false`）
- Ego 系統：`ego_rules` 定義前綴/後綴如何合併到實體

**關鍵方法**

| 方法 | 說明 |
|------|------|
| `getLevel(game, lev, old_lev)` | 取得/生成指定層，處理持久化策略 |
| `newLevel(level_data, lev, old_lev, game)` | 建立新層（含生成 + 連通性驗證） |
| `makeEntity(level, type, filter, force_level)` | 隨機生成並解析單一實體 |
| `makeEntityByName(level, type, name)` | 依 `define_as` 生成指定實體 |
| `addEntity(level, e, typ, x, y)` | 將實體放置到關卡地圖 |
| `computeRarities(type, list, level, filter)` | 建立基於稀有度/等級的機率表 |
| `checkFilter(e, filter, typ)` | 驗證實體是否符合過濾條件 |
| `finishEntity(level, type, e, ego_filter)` | 最終解析（含 ego 套用） |
| `applyEgo(e, ego, type)` | 合併 ego 屬性到實體 |
| `setup(t)` | 靜態方法：註冊 Actor/Grid/Object/Trap 類別 |

**設計細節**
- 稀有度計算：`10000 / ood_factor^distance`（越超出深度越少見）
- 連通性驗證：用 A* 確認關卡可達性，失敗最多重試 50 次
- LRU cache：`enableLastPersistZones(max)` 快取最近造訪的 zone

---

### Level.lua — 單一樓層容器

| 欄位 | 說明 |
|------|------|
| `level` | 深度層數 |
| `map` | Map 物件 |
| `e_array` | 回合順序的實體列表 |
| `entities` | `{uid→entity}` O(1) 查找 |
| `spots` | 生成器提供的生成點（出口、寶藏…） |
| `sublevels` | 子層列表 `{name→Level}` |
| `last_iteration` | `{i=index}` 迭代安全移除追蹤 |

**關鍵設計**
- 迭代安全：`removeEntity()` 在迭代中間時調整 `last_iteration.i`，避免跳過實體
- 子層堆疊：`selectSublevel(name)` 原子交換主層與子層

---

### Map.lua — 空間格子 + 渲染後端

**Z 層常數**

| 常數 | 值 | 說明 |
|------|----|------|
| `Map.TERRAIN` | 1 | 地形/牆壁 |
| `Map.TRAP` | 50 | 陷阱 |
| `Map.ACTOR` | 100 | 角色/怪物 |
| `Map.PROJECTILE` | 500 | 投射物 |
| `Map.OBJECT` | 1000 | 物品 |
| `Map.TRIGGER` | 10000 | 觸發器 |

**主要欄位**

| 欄位 | 說明 |
|------|------|
| `map` | 稀疏陣列 `[x+y*w]={pos→entity}` |
| `seens`, `remembers`, `has_seens` | FOV 可見性狀態 |
| `lites` | 光源/火炬狀態 |
| `effects` | 暫時效果（傷害/視覺範圍） |
| `_fovcache` | `{block_sight, block_esp, block_sense, path_caches}` |
| `_map` | C 引擎地圖物件（`core.map`） |
| `mx`, `my` | 視口捲動偏移 |

**主要方法**

| 方法 | 說明 |
|------|------|
| `setViewPort(x, y, w, h, tile_w, tile_h, ...)` | 設定顯示區域與圖磚大小 |
| `display(x, y, nb_keyframe, ...)` | 渲染地圖與特效 |
| `call(x, y, pos, e)` | metamethod：get/set 實體（帶自動更新） |
| `updateMap(x, y)` | 重建 MapObject、FOV 快取、實體檢查函數 |
| `checkAllEntities(x, y, what, ...)` | 遍歷 (x,y) 所有實體查詢方法 |
| `addEffect(src, x, y, duration, damtype, ...)` | 生成暫時視覺/傷害範圍 |
| `moveViewSurround(x, y, marginx, marginy)` | 追蹤玩家視口 |

**關鍵設計**
- **動態實體檢查函數**：每個 (x,y) 位置編譯一個專屬 Lua 函數，僅檢查該位置存在的實體，避免 `pairs()` 開銷
- **FOV 快取分離**：sight/ESP/sense 三套獨立快取
- **懶更新**：只有呼叫 `call()`/`remove()` 時才呼叫 `updateMap(x,y)`，不持續更新

---

### MapEffect.lua — 暫時地圖效果

繼承自 Entity，增加：
- `alpha`（0-100，預設 100）— 透明度
- `display_on_seen`（預設 true）— 僅在可見格子顯示
- 可掛載 `overlay_particle` 做複雜視覺效果

---

## 4. 遊戲迴圈

### Game.lua — 基底遊戲類別

**主要職責**：遊戲狀態、UI 對話框堆疊、渲染、輸入、設定、協程管理

| 方法 | 說明 |
|------|------|
| `tick()` | 核心 tick：處理錯誤、協程、shader、計時器 |
| `display(nb_keyframes)` | 渲染幀：對話框、飄字、tween、計時器 |
| `registerDialog(d)` / `unregisterDialog(d)` | 對話框堆疊管理 |
| `onTickEnd(f, name)` | 回合結束 callback（可回傳 `TICK_RESCHEDULE` 重排） |
| `registerCoroutine(id, co)` / `cancelCoroutine(id)` | 協程池管理 |
| `setResolution(res, force)` | 解析度切換 |
| `saveGame()` | 遊戲持久化 |

**重要資料結構**
- `dialogs`：堆疊式 UI 對話框（頂部接收輸入）
- `entities`：弱值 table，實體在無引用時自動 GC
- `on_tick_end`：`{fcts, names}` — 回合末 callback 佇列
- `__coroutines`：背景任務協程 pool

---

### GameEnergyBased.lua — Energy-based 行動系統

```lua
-- 每 tick 給所有實體加 energy
e.energy.value += energy_per_tick * e.energy.mod * e.global_speed
-- energy 足夠時行動
if e.energy.value >= energy_to_act then e:act() end
```

| 參數 | 預設值 |
|------|--------|
| `energy_to_act` | 1000 |
| `energy_per_tick` | 100 |

- `entities`：弱值 table 的行動實體登錄表
- `level.last_iteration`：暫停後恢復迭代位置（安全中途暫停）
- 支援主層 + sublevel 同時 tick

---

### GameTurnBased.lua — 回合制變體（54 行）

繼承 GameEnergyBased，加上暫停機制：

```lua
-- 玩家 act() → game.paused = true（等待輸入）
-- 玩家行動後消耗 energy → game.paused = false（NPC 輪流行動）
```

- `paused`：布林暫停旗標
- `can_pause = true`：啟用 GameEnergyBased 的暫停邏輯
- 若玩家 energy 不足時自動取消暫停（防止死鎖）

---

## 5. Resolver 延遲計算系統 (resolvers.lua)

Resolver 是「延遲計算」框架，讓實體定義包含亂數/條件邏輯，直到 `resolve()` 時才執行。

**結構**：`resolvers.foo(...)` 建立 `{__resolver="foo", ...data}`；`resolvers.calc.foo(t, e)` 執行計算。

| Resolver | 說明 |
|----------|------|
| `rngrange(x, y)` | 隨機整數 [x, y]（`__resolve_instant`）|
| `rngfloat(x, y)` | 隨機浮點數 |
| `rngavg(x, y)` | 平均隨機（集中於中間值）|
| `dice(x, y)` | xdy 擲骰 |
| `rngtable(t)` | 從 table 隨機取一值 |
| `rngcolor(t)` | 隨機顏色並設 color_r/g/b |
| `mbonus(max, add)` | 依當前層數縮放的加成 |
| `talents(list)` | 學習技能列表 |
| `rngtalent(list)` | 從列表隨機學一個技能 |
| `rngtalentsets(list)` | 從集合隨機選一組技能 |
| `tmasteries(list)` | 設定技能類型熟練度 |
| `levelup(base, every, inc, max)` | 升級屬性進程設定 |
| `generic(fct)` | 自訂函數 resolver |

- `__resolve_instant`：在其他 resolver 之前優先執行（適合即時亂數）
- `__resolve_last`：在其他 resolver 之後執行
- `resolvers.current_level`：全域變數，Zone 生成前設定，讓 `mbonus` 感知當前深度

---

## 6. Actor 介面混入 (interface/)

以下混入透過 `class.inherit(engine.Actor, interface.X, ...)` 組合到 Actor。

### ActorTalents — 技能系統

**靜態定義**（全局共用）：
```lua
self:newTalentType{type="spell/fire", name="Fire Spells"}
self:newTalent{
    name = "Fireball", type={"spell/fire",1}, mode="activated",
    cooldown=10, action=function(self, t) ... end,
}
-- 自動生成 T_FIREBALL 常數
```

**實例資料**

| 欄位 | 說明 |
|------|------|
| `talents` | `{T_FIREBALL=3}` 技能 ID → 等級 |
| `sustain_talents` | `{T_SHIELD=true}` 已開啟的持續技能 |
| `talents_cd` | `{T_FIREBALL=5}` 冷卻剩餘 |
| `talents_types` | 技能類型解鎖狀態 |
| `talents_types_mastery` | 熟練度修正 |

**技能模式**：`"activated"`（一次性）、`"sustained"`（開關）、`"passive"`（常駐，呼叫 `passives()` 套用臨時值）

**執行流程**：`useTalent()` → `preUseTalent()` 檢查 → 協程執行 `action()` → `postUseTalent()` 扣資源/設冷卻

---

### ActorStats — 屬性系統

```lua
ActorStats:defineStat("Strength", "str", 10, 1, 100, "Physical power")
-- 自動生成 getStr()、incStat("str", v) 等方法
```

| 方法 | 說明 |
|------|------|
| `getStat(stat, scale, raw)` | 取得最終值（含加成） |
| `incStat(stat, val)` | 增減基礎值 |
| `incIncStat(stat, val)` | 增減臨時加成（裝備/效果）|
| `onStatChange(stat, v)` | 屬性變更 hook（子類別覆寫） |

---

### ActorLife — 生命值與死亡

| 方法 | 說明 |
|------|------|
| `regenLife()` | 每回合生命回復（從 `act()` 呼叫） |
| `heal(value, src)` | 治療 |
| `takeHit(value, src, death_note)` | 受傷；HP ≤ 0 觸發死亡 |
| `die(src, death_note)` | 死亡流程：掉落、移除、成就判定 |
| `attack(target, x, y)` | 基礎攻擊（子類別覆寫） |

- `die_at`：死亡 HP 閾值（通常為 0，可自訂）
- `onHeal()` / `onTakeHit()` hook 可修改治療/傷害值

---

### ActorFOV — 視野計算

```lua
actor:computeFOV(range, "block_sight", function(x, y, dx, dy, sqdist)
    game.level.map:apply(x, y)
end)
```

| 方法 | 說明 |
|------|------|
| `computeFOV(radius, block, apply, ...)` | 計算圓形 FOV（呼叫 C 層 `core.fov.*`） |
| `computeFOVBeam(radius, dir, angle, ...)` | 方向性 FOV 扇形 |
| `hasLOS(x, y)` | 快速查詢兩點間直線視野 |
| `lineFOV(x, y)` | FOV 線迭代器（投射物路徑用）|
| `distanceMap(x, y, v)` | 取得/設定距離地圖值 |

- `fov.actors`：弱引用，目前 FOV 內的角色
- `fov.actors_dist`：依距離排序的角色列表
- FOV 快取：避免同回合重複計算

---

### ActorProject — 投射與傷害系統

```lua
self:project(
    {type="bolt", range=5, block_path=function(...)end},
    tx, ty, DamageType.FIRE, 100, particles
)
```

**目標形狀**：`bolt`、`beam`（貫穿）、`ball`（AOE）、`cone`（扇形）、`hit`（直接命中）、`triangle`、`wall`、`widebeam`

**執行流程**：
1. `Target:getType(t)` 解析形狀
2. `lineFOV` 迭代器逐格推進，判斷 `block_path`
3. 角落阻擋特例處理
4. 對每個命中格呼叫 `DamageType.project(src, x, y, type, dam)`
5. 若有 `create_projectile`，生成飛行實體再傷害

---

### ActorAI — AI 系統

| 方法 | 說明 |
|------|------|
| `doAI()` | 每回合 AI 入口 |
| `runAI(ai, ...)` | 執行指定 AI 行為 |
| `moveDirection(x, y, force)` | 向目標移動一步（含繞路） |
| `setTarget(target, last_seen)` | 設定目標（觸發 hook） |
| `getTarget(typ)` | 取得目標座標與 Actor |
| `aiCanPass(x, y)` | 檢查是否可通過（含敵意判斷） |
| `aiSeeTargetPos(target, add_spread)` | 取得目標位置（含誤差） |
| `aiGetAvailableTalents(...)` | 取得可用技能列表 |

**實例資料**
- `ai`：當前 AI 名稱
- `ai_state`：跨回合持久 AI 狀態
- `ai_target`：`{actor, last_seen}` 目標追蹤
- `ai_actors_seen`：弱引用，曾見過的所有角色
- `AI_LOCATION_GUESS_ERROR = 3`：目標位置猜測誤差半徑

**設計細節**：AI 對目標位置施加誤差（含慣性平滑），避免完美資訊；支援特殊移動（穿牆等）增加誤差擴散。

---

### ActorTemporaryEffects — Buff/Debuff 系統

```lua
self:newEffect{
    name = "BURNING", desc = "On fire", type = "magical",
    activation = function(self, eff) ... end,
    deactivation = function(self, eff) ... end,
    on_timeout = function(self, eff) self:takeDamage(eff.power) end,
}
-- 自動生成 EFF_BURNING 常數
```

| 方法 | 說明 |
|------|------|
| `setEffect(eff_id, dur, p, silent)` | 施加/刷新效果 |
| `removeEffect(eff, silent, force)` | 移除效果 |
| `hasEffect(eff_id)` | 是否有此效果 |
| `timedEffects(filter)` | 每回合倒數，到期呼叫 `deactivation`（從 `act()` 呼叫）|
| `effectTemporaryValue(eff, k, v)` | 效果結束時自動清除的臨時值 |
| `effectParticles(eff, ...)` | 效果結束時自動清除的粒子 |

- `tmp`：`{EFF_BURNING = {dur=5, power=10, ...}}` 活躍效果表
- 支援 `on_merge` callback：效果重疊時合併（如延長持續時間）

---

### ActorInventory — 揹包系統

| 方法 | 說明 |
|------|------|
| `addObject(inven_id, o)` / `removeObject(inven_id, item)` | 物品增刪 |
| `wearObject(o, replace, vocal)` | 裝備物品（觸發 `on_wear`）|
| `takeoffObject(inven_id, item)` | 卸下裝備（觸發 `on_takeoff`）|
| `canWearObject(o, try_slot)` | 檢查裝備需求（屬性/等級/技能）|
| `sortInven(inven)` | 排序 + 堆疊整理 |
| `pickupFloor(i, vocal)` | 撿起地板物品 |
| `dropFloor(inven, item, vocal)` | 丟棄物品 |

- `inven`：多個 slot table（`INVEN_MAINHAND`, `INVEN_BODY`, …）
- 裝備的 `carried`/`wielded` 屬性透過臨時值系統自動套用/撤銷
- 排序順序：type > subtype > name > quantity

---

### ActorLevel — 等級與經驗

| 方法 | 說明 |
|------|------|
| `gainExp(value)` | 獲得經驗（達到閾值觸發升級）|
| `levelup()` | 升級流程（使用 `_levelup_info` table）|
| `forceLevelup(lev)` | 強制升到指定等級 |
| `worthExp(target)` | 計算此角色的經驗值 |

- `exp_chart`：函數或 table，決定每級所需 XP
- `_levelup_info`：定義升級時的屬性/技能進程（kchain/k/inc/max/every）

---

### ActorResource — 資源系統

```lua
ActorResource:defineResource("Mana", "mana", nil, "mana_regen", "...")
-- 自動生成 getMana(), incMana(), getMaxMana() 等
```

- `regenResources()`：每回合回復（從 `act()` 呼叫）
- `recomputeRegenResources()`：動態編譯快速回復函數
- `useResources(costs, check)`：消耗資源（check=true 僅驗證不扣除）
- 支援反向值系統（如用盡才滿）、持續技能抑制回復

---

## 7. 玩家介面混入

### PlayerRest — 休息系統

```lua
player:restInit(turns, "resting", "rested", on_end_callback)
```

- 每回合呼叫 `restCheck()` 判斷是否停止（子類別覆寫）
- 停止條件：受傷、敵人出現、HP/MP 滿等

### PlayerRun — 自動奔跑

```lua
player:runInit(dir)    -- 方向奔跑
player:runFollow(path) -- 沿預計算路徑奔跑
```

- `runCheck()`：感知地形變化（岔路口、敵人、物品）
- `running` 狀態：`{dir, block_left/right, ignore_left/right, path, cnt}`
- 支援自動探索整合（`running.explore` 旗標）

### PlayerExplore — 自動探索

- Flood-fill BFS 找最近未探索格或物品
- 自動規避非對稱 LoS（防埋伏）
- 優先「孤立」未探索格（只有一個相鄰未見格的格子）

### PlayerHotkeys — 快捷鍵系統

- 7 頁 × 12 槽 = 84 個快捷鍵
- 支援技能與物品兩種類型
- `hotkey_page`：當前頁；`quickhotkeys`：全局模板

### PlayerMouse — 滑鼠控制

- `mouseMove(tmx, tmy, ...)` — A* 尋路 + 直線路徑 fallback
- `mouseScrollMap(map, xrel, yrel)` — Shift + 拖曳捲動地圖
- 偵測敵人限制移動路徑

### GameTargeting — 目標選擇系統

- 三種目標模式：`"lock"`（掃描）、`"free"`（滑鼠）、`"immediate"`（方向性）
- 使用協程暫停執行等待玩家選擇
- 戰術格子 overlay：紅=阻擋、藍=可用、綠=盟友、黃=敵人
- `tooltipDisplayAtMap(x, y, text)` — 地圖上方顯示提示

### WorldAchievements — 成就系統

- 三個作用域：世界（world）/ 遊戲（game）/ 玩家（player）
- `gainAchievement(id, src)` — 檢查 `can_gain` 條件後授予
- 廣播到聊天頻道；支援「巨型」成就特殊顯示

### BloodyDeath — 死亡視覺效果

- `bloodyDeath(tint)` — 對 3 個相鄰格套用血色染色
- `has_blood`：`true` 或 `{nb, color=[r,g,b]}`

---

## 8. 傷害類型系統 (DamageType.lua)

```lua
DamageType:newDamageType{
    name = "FIRE", type = "fire", text_color = "#r#",
    projector = function(src, x, y, type, dam)
        local target = game.level.map(x, y, Map.ACTOR)
        if target then target:takeHit(dam, src) end
    end,
}
-- 自動生成 DamageType.FIRE 常數
```

- 每種傷害類型有獨立 projector 函數，由 `ActorProject:project()` 呼叫
- `setDefaultProjector(fct)` — 未自訂 projector 的傷害類型使用預設
- `projectingFor(src, v)` / `getProjectingFor(src)` — 委派投射（一個角色代另一個投射）

---

## 9. 目標系統 (Target.lua)

**目標形狀描述**：
```lua
{type="bolt", range=10}              -- 直線單目標
{type="beam", range=10}              -- 直線貫穿
{type="ball", range=5, radius=3}     -- 球形 AOE
{type="cone", range=8, cone_angle=45} -- 扇形
{type="hit"}                          -- 直接命中
```

**目標樣式**
- `lock`（掃描模式）：鍵盤掃描目標
- `free`（自由模式）：滑鼠指定位置
- `immediate`（即時模式）：方向鍵選擇

**渲染**
- 彩色 overlay 即時顯示射程/形狀（紅/藍/綠/黃 tile 顏色）
- 可選 FBO 渲染做半透明 overlay 效果
- 箭頭指示器顯示來源→目標方向

---

## 10. 程序地圖生成系統 (generator/)

所有生成器繼承 `engine.Generator`，實作 `:generate(lev, old_lev)` 方法。

**Zone 中指定生成器**：
```lua
generator = {
    map   = {class="engine.generator.map.Roomer", floor="FLOOR", wall="WALL"},
    actor = {class="engine.generator.actor.Random", nb_npc={10,15}},
}
```

### 地圖生成器 (generator/map/)

| 生成器 | 演算法 | 特色 |
|--------|--------|------|
| `Rooms` | 遞迴 BSP 切割 | 最簡單；根據長寬比選切割軸 |
| `RoomsLoader` | 預設計房間 + MST 連通 | 支援 .tmx / .lua 房間；房間旋轉/翻轉 |
| `Cavern` | Perlin noise + flood-fill | 含連通性驗證；支援插入房間 |
| `CavernousTunnel` | 洞窟變體 | — |
| `Maze` | 深度優先遞迴回溯 | 可調整格子寬高（`widen_w/h`）|
| `Forest` | Perlin noise + A* 道路 | 多層植被；邊緣入口；路點連通 |
| `Heightmap` | 分形高度圖 | 依高度閾值分配地形類型 |
| `Building` | 兩層 BSP（街區→建築）| 牆壁門洞系統 |
| `Town` | 單層 BSP | L 形內部隔間；可選院落 |
| `Static` | 手工 .tmx / .lua 地圖 | 完整自訂環境 API |
| `GOL` | Game of Life 細胞自動機 | 3 代演化；自訂生死規則 |
| `MapScript` | Script 驅動 | — |
| `WaveFunctionCollapse` | 呼叫 C++ WFC 核心 | 樣本學習 + 非同步生成 |
| `Empty`, `Filled`, `Hexacle`, `Octopus`, `TileSet` | 特殊變體 | — |

### Actor 生成器 (generator/actor/)

**Random.lua**：
- `nb_npc`：每層生成數量範圍
- `filters`：Actor 類型過濾器
- `guardian`：Boss 定義（含生成地點偏好）
- 連通性檢查；Boss 失敗則重建關卡

### Object/Trap 生成器

- `generator/object/Random.lua`、`generator/object/OnSpots.lua`
- `generator/trap/Random.lua`

---

## 11. AI 系統 (ai/)

AI 是命名行為的組合，以字串 key 組合：

```lua
npc.ai = "dumb_talented"     -- 主 AI
npc.ai_state = {talent_in=3} -- AI 狀態參數
```

### simple.lua — 基礎 AI 行為

| AI 名稱 | 說明 |
|---------|------|
| `move_simple` | 直線朝目標移動 |
| `move_dmap` | 目標可見用距離地圖；否則往最後目擊點 |
| `move_astar` / `move_astar_advanced` | A* 尋路（含 Actor 阻擋可選）|
| `move_blocked_astar` | 被阻擋多回合後切換 A* |
| `move_wander` | 隨機相鄰移動 |
| `move_complex` | 整合多策略（A*/距離地圖/漫遊） |
| `flee_simple` / `flee_dmap` | 反向移動 + 障礙迴避 |
| `target_simple` / `target_player` | 目標選取（最近敵人或玩家）|
| `simple` / `dmap` | 合成 AI（目標選取 + 移動）|
| `none` | 空 AI 佔位符 |

### talented.lua — 技能使用 AI

| AI 名稱 | 說明 |
|---------|------|
| `dumb_talented` | 隨機挑可用技能；無戰術評估 |
| `improved_talented` | 嘗試最多 5 個技能 + fallback |
| `dumb_talented_simple` | 目標選取 + N 分之一機率用技能 + 移動 |

`ai_state.talent_in`：使用技能的頻率；`ai_state.no_talents`：技能抑制旗標

### special_movements.lua — 特殊移動

| AI 名稱 | 說明 |
|---------|------|
| `move_ghoul` | 交替移動/暫停（`pause_chance`）|
| `move_snake` | 側滑接近；只在近距離時直線衝鋒 |

---

## 12. 演算法 (algorithms/)

### BSP.lua — 二元空間分割

- `init(w, h, min_w, min_h, max_depth)` — 初始化樹
- `partition(store)` — 遞迴切割（50% 隨機選軸）
- `leafs`：僅葉節點；`splits`：切割座標（用於走廊生成）

### MST.lua — 最小生成樹（Kruskal 演算法）

- `edge(r1, r2, cost, data)` — 加入帶權邊
- `run()` — Union-Find 計算 MST，回傳最小邊集合
- `fattenRandom(nb_adds)` — 加入隨機非 MST 邊（增加環路）
- `fattenShorter(nb_adds)` — 加入最短非 MST 邊

---

## 13. Tilemap 中間表示 (tilemaps/)

部分生成器先產生抽象 tilemap（字元代號），再映射到實際 Entity。

### Tilemap.lua — 基底

- `setSize(w, h, fill_with)` / `makeData(w, h, fill_with)` — 建立 2D 陣列
- `point(x, y)` — 帶運算子重載的位置物件（+, -, *, /, distance, direction）
- `pointIterator(sx, sy, tx, ty)` — 矩形區域迭代器
- `clone()` — 深拷貝

### WaveFunctionCollapse.lua

- 整合 C++ WFC 核心（樣本學習模式）
- `run(t)` — 同步或非同步啟動 WFC
- `waitAll(...)` — 平行等待多個 WFC 實例（效能優化）
- `parseResult(data)` — 解析字元輸出為 2D 格子

### BSP.lua / Maze.lua / Heightmap.lua / Noise.lua / Rooms.lua / Static.lua / Proxy.lua

各種對應演算法的 Tilemap 變體。

---

## 14. 存檔系統 (Savefile.lua)

### 格式

每次存檔 = 一個 zip 檔，內含多個 Lua 序列化字串：

```
/save/<player_name>/
    save.lua          -- 頂層 game 物件
    description.lua   -- 元資料（模組、版本、Addon、可讀取旗標）
    <hash1>.lua       -- 某個子物件（Level、Actor…）
    <hash2>.lua
```

### 存檔流程

1. `game:save()` → `Savefile:init(name)` → 建立 zip
2. `core.serial.new()` 序列化根物件
3. 遞迴遇到子物件 → `addToProcess(t)` 排隊
4. 相同物件引用 → `loadObject(hash)` 取代（避免重複）
5. 完成後關閉 zip，可選 Steam Cloud 上傳

### 讀檔流程

1. `Savefile:load()` → 解壓到 `/tmp/loadsave/`
2. `class.load(str)` 反序列化，遇 `loadObject` 遞迴讀取
3. 根據 `__CLASSNAME` 重設 metatable
4. 延遲呼叫 `:loaded()`（確保相互引用建立後才初始化）

### 其他特性

- `SavefilePipe`：背景存檔（協程分批，避免卡頓）
- `setSaveMD5Type(type)`：啟用 MD5 校驗（偵測存檔修改）
- `saveQuickBirth(descriptor)` / `loadQuickBirth()` — 快速角色創建模板

---

## 15. 渲染支援系統

### Tiles.lua — 圖磚快取

- 三層巢狀 table 快取（char → fgidx → bgidx）
- `loadTileset(file)` — 載入大圖切片定義
- `loadImage(image)` — 含 addon 路徑支援
- `get(char, fr, fg, fb, br, bg, bb, image, ...)` — 取得快取/生成圖磚
- `clean()` — 清除快取並 GC

### Shader.lua — GLSL Shader 管理

- 懶載入：第一次存取 `shader.shad` 才實際編譯
- 參數化快取：相同名稱+參數的 shader 共用
- `setUniform(k, v)` — 設定數字/向量/材質 uniform
- `cleanup()` — 刪除超時的臨時 shader
- `core.shader.allow(kind)` — 依使用者設定決定 shader 功能等級

### Particles.lua — 粒子系統

```lua
local p = Particles.new("flame", radius=1, {size=2, density=50})
actor:addParticles(p)
```

- 粒子定義在 `/data/gfx/particles/*.lua`（行為、壽命、顏色曲線）
- C 層維護物理計算（`src/particles.c`）
- `__particles_gl` 弱引用 table 防止 GC 前仍被渲染
- 支援子粒子（sub-emitters）複合效果

### FlyingText.lua — 飄字效果

- `add(x, y, duration, xvel, yvel, str, color, bigfont)` — 建立飄字
- 弱引用 table 追蹤活躍飄字；到期自動清除
- 生命末尾放大縮放效果（pop-out）

---

## 16. UI 框架 (ui/)

### Base.lua — UI 基底

所有 UI 元件的基底：

- 靜態字型：`font`（DroidSans 12pt）、`font_mono`、`font_bold`
- 主題系統：`loadUIDefinitions(file)` — 可換皮（9-patch frame + 顏色）
- 材質快取：`cache` / `tcache`，避免重複載入
- `makeFrame(base, w, h, iw, ih)` — 9-patch 邊框建構
- `drawFrame(f, x, y, r, g, b, a, w, h)` — 含裁切的邊框渲染

### Dialog.lua — 視窗容器

```lua
local d = Dialog.new("Title", width, height)
d:loadUI{
    {left=3, top=3, ui=Button.new{...}},
    {right=3, bottom=3, ui=List.new{...}},
}
d:setupUI(auto_w, auto_h)
game:registerDialog(d)
```

- 錨點佈局：`{left, right, top, bottom, vcenter, hcenter}`
- Modal 堆疊：`game.dialogs` 頂部接收輸入
- 工廠方法：`simplePopup`、`simpleWaiter`、`listPopup`、`yesnoPopup` 等

### 主要 UI 元件

| 元件 | 特色 |
|------|------|
| `Button` | 點擊 callback；glow 動畫；失焦淡出 |
| `List` | 可捲動清單；鍵盤（↑↓, Home/End, PgUp/Dn）+ 滾輪操作 |
| `ListColumns` | 多欄清單，可調整欄寬 |
| `TreeList` | 可展開/收合的樹狀清單 |
| `Textzone` | 富文本（色彩 tag）；慣性捲動；可選 shadow shader |
| `TextzoneList` | 多段文字 + 條目選擇 |
| `Textbox` | 單行輸入框，支援 Unicode |
| `Numberbox` | 數字輸入框 |
| `Slider` / `NumberSlider` | 滑桿 |
| `Checkbox` | 勾選框 |
| `Dropdown` | 下拉選單 |
| `Tabs` | 標籤頁切換；滑鼠事件委派 |
| `ImageList` | 圖像格狀選擇（技能/物品圖示）|
| `EquipDoll` | 人形裝備圖（點擊對應部位）|
| `EntityDisplay` | 顯示實體圖像與描述 |
| `Waitbar` / `Waiter` | 進度條 |
| `WebView` | 嵌入網頁（CEF3/Awesomium）|
| `UIContainer` / `UIGroup` | 容器/群組佈局 |
| `SurfaceZone` | 自由繪製區域（GL surface）|

### 預建對話框 (dialogs/)

| 對話框 | 功能 |
|--------|------|
| `GameMenu` | 主選單/暫停選單 |
| `ShowInventory` / `ShowEquipment` / `ShowEquipInven` | 物品/裝備管理 |
| `ShowPickupFloor` | 地板撿取 |
| `ShowStore` | 商店界面 |
| `ShowQuests` | 任務列表 |
| `ShowLog` | 訊息記錄 |
| `ShowAchievements` | 成就清單 |
| `ViewHighScores` | 排行榜 |
| `UseTalents` | 技能使用 |
| `KeyBinder` | 按鍵設定 |
| `VideoOptions` / `AudioOptions` | 影音設定 |
| `DisplayResolution` | 解析度設定 |
| `LanguageSelect` | 語言選擇 |
| `Downloader` | 更新/下載器 |
| `Chat` / `ChatChannels` / `ChatFilter` | 在線聊天 |
| `GetText` / `GetQuantity` / `Talkbox` | 輸入對話 |
| `UserInfo` | 用戶資料 |

---

## 17. 輸入系統

### Key.lua — 底層按鍵處理

- 200+ 按鍵常數（`_a`, `_RETURN`, `_ESCAPE`, `_F1` …）
- `receiveKey(sym, ctrl, shift, alt, meta, unicode, isup, key)` — 處理按鍵事件
- `handleStatus(...)` — 維護 `key.status` 按鍵狀態 dict
- `setCurrent()` — 註冊為當前事件接收者
- 支援搖桿（`receiveJoyButton`）

### KeyBind.lua — 虛擬動作系統

```lua
-- 定義虛擬動作（/data/keybinds/*.lua）
defineAction{type="MOVE_LEFT", name="Move Left", default={{"left"},{"numpad4"}}}

-- 綁定動作到 callback
key:addBind("MOVE_LEFT", function() player:moveDir(4) end)
```

- `loadRemap(file)` / `saveRemap(file)` — 載入/儲存用戶重映射
- `bindKeys()` — 依當前重映射重新綁定所有虛擬動作
- `triggerVirtual(virtual)` — 程式化觸發動作
- 每動作支援最多 3 個實體按鍵
- 重映射存於 `/settings/keybinds2.cfg`

---

## 18. 支援系統

### Quest.lua — 任務系統

**狀態機**：`PENDING(0)` → `COMPLETED(1)` → `DONE(100)` 或 `FAILED(101)`

```lua
local quest = Quest.new({
    name = "Kill the Dragon",
    on_grant = function(self, who) ... end,
    on_status_change = function(self, who, status, sub) ... end,
}, player)
quest:setSubCompleted("find_lair")
quest:setCompleted()
```

### Faction.lua — 陣營系統

- `Faction:add(t)` — 定義陣營（含初始反應表）
- `Faction:factionReaction(f1, f2)` — 查詢當前反應（-100 到 100）
- `Faction:setFactionReaction(f1, f2, reaction, mutual)` — 動態修改
- 預定義：`"players"` 與 `"enemies"` 陣營

### Store.lua — 商店系統

繼承 Entity + ActorInventory，增加：
- `loadup(level, zone)` — 從 zone 實體生成商品
- `tryBuy(who, o, item, nb)` / `onBuy(...)` — 模板方法購買流程
- `trySell(who, o, item, nb)` / `onSell(...)` — 模板方法販售流程
- `canRestock()` — 檢查補貨延遲
- `interact(who, name)` — 開啟商店對話框

### Chat.lua — NPC 對話系統

- 支援兩種格式：傳統 Lua 腳本 + 新版 JSON（視覺化編輯器）
- `replace(text)` — 解析 `@placeholder@` 插值
- `switchNPC(npc, pan_camera)` — 對話中切換 NPC
- `chatFormatActions(nodes, answer, ...)` — 遞迴解析 JSON 動作/條件鏈
- 支援唯一條件追蹤（每玩家/NPC/遊戲狀態）

### Birther.lua — 角色創建嚮導

- 多步驟精靈（base → role → …）
- `loadDefinition(file, env)` — 載入描述定義
- `randomSelect()` — 隨機選擇；`quickBirth()` — 預設選擇
- `apply(self_contained)` — 將所有選擇的 `copy`/`stats`/`talents` 累加到角色
- 支援 a-z, A-Z 快捷鍵

### Autolevel.lua — NPC 自動升級

- `registerScheme(t)` — 註冊升級方案
- `autoLevel(actor)` — 執行 `actor.autolevel` 指定的方案

### HighScores.lua — 高分榜

- `registerScore(world, details)` — 儲存死亡角色分數
- `noteLivingScore(world, name, details)` — 追蹤存活角色
- `createHighScoreTable(world, formatters)` — 生成格式化分數字串
- 透過 `profile:saveModuleProfile()` 持久化

### NameGenerator.lua — 音節名稱生成

```
$s=起始音節, $m=中間, $e=結尾, $v=母音, $c=子音
$35m = 35% 機率加中間音節
```

使用 LPEG 模式替換；支援重複抑制

### NameGenerator2.lua — 文法名稱生成

- 預訓練音節組合文法（syllable transition 機率）
- `generate(no_repeat, min_syl, max_syl)` — 帶音節數限制的生成
- 累積機率分布做加權隨機；禁詞列表避免重複

### I18N.lua — 國際化系統

```lua
I18N:loadLocale("/data/locales/engine/zh.lua")
I18N:setLocale("zh")
_t"Hello World"           -- 取得翻譯字串
_t("Hello %s", name)      -- 帶參數
string.tformat(s, ...)    -- 格式化（支援參數重排序）
```

- 翻譯資料：`{["Hello World"] = "你好世界"}`
- tag 系統分類翻譯（"entity name"、"tformat" 等）
- `dumpUnknowns()` — 匯出未翻譯字串

### colors.lua — 顏色系統

- 60+ 命名顏色（BLACK, WHITE, RED, GOLD, DARK_KHAKI …）
- 雙向登錄：`colors`（全定義）+ `r_colors`（反向查找）
- `colors.simple(c)`、`colors.simple1(c, a)`、`colors.hex1(hex)` — 顏色工具
- `colors.lerp(a, b, x)` — 線性插值

### utils.lua — 全局工具庫

此檔案向全局命名空間注入大量輔助函數：

**math.*** （10+ 函數）：
- `math.decimals(v, nb)` — 四捨五入到 N 小數位
- `math.round(v, mult, num)` — 捨入到倍數
- `math.scale(i, imin, imax, dmin, dmax)` — 線性插值
- `math.boundscale(...)` — 有界插值

**string.*** （30+ 函數）：
- `string.limit_decimals(num, sig_figs)` — 精度格式化
- `string.trim(str)` — 去除空白
- `string.a_an(str)` — 加冠詞 "a"/"an"
- `string.he_she(actor)` — 依 `actor.female` 回傳代名詞
- `string.capitalize(str)` / `string.bookCapitalize(str)` — 大寫轉換
- `string.noun_sub(str, type, noun)` — 替換 `@type@` 佔位符
- `string.split(str, char)` — 字串分割
- `string.splitAtSize(bstr, size, font)` — 依像素寬自動換行
- `string.toTString(str)` — 轉換為 TString 富文本類型
- `string.removeColorCodes(str)` — 移除顏色標記
- `string.levenshtein_distance(str1, str2)` — 編輯距離

**table.*** （50+ 函數）：
- `table.clone(tbl, deep, k_skip)` — 深/淺拷貝
- `table.merge(dst, src, deep)` — 合併（覆寫）
- `table.mergeAdd(dst, src, deep)` — 合併（數字相加）
- `table.ruleMergeAppendAdd(dst, src, rules)` — 規則驅動合併（ego 系統使用）
- `table.keys(t)` / `table.values(t)` — 提取鍵/值
- `table.count(t)` — 計數（支援 pairs）
- `table.weak_keys(t)` / `table.weak_values(t)` — 弱引用 table 建立
- `table.has(t, ...)` / `table.get(t, ...)` / `table.set(t, ...)` — 巢狀存取
- `table.shuffle(t)` — 隨機排列
- `table.applyRules(dst, src, rules, state)` — 複雜規則合併
- `table.equivalence(t1, t2, recurse)` — 深度相等比較

**util.*** （40+ 函數）：
- `util.bound(i, min, max)` — 夾值；`util.boundWrap(i, min, max)` — 循環夾值
- `util.getval(val, ...)` — 取值（函數則呼叫，否則直接回傳）
- `util.lerp(a, b, x)` — 線性插值
- `util.dirToCoord(dir, sx, sy)` — 方向轉 dx/dy
- `util.coordToDir(dx, dy, sx, sy)` — 座標轉方向
- `util.getDir(x1, y1, x2, y2)` — 兩點間方向
- `util.adjacentCoords(x, y, no_diagonals)` — 取相鄰格
- `util.findFreeGrid(sx, sy, radius, block, what, checker)` — 找空格子
- `util.loadfilemods(file, env)` — 帶 addon 覆蓋載入
- `util.uuid()` — 生成 UUID
- `util.showMainMenu(no_reboot, ...)` — 顯示/重啟主選單
- `util.send_error_backtrace(msg)` — 帶 call stack 的錯誤記錄

**迭代器**：
- `ipairsclone(t)` / `pairsclone(t)` / `ripairsclone(t)` — 拷貝後迭代（迭代中修改安全）
- `ripairs(t)` — 反向 ipairs
- `ipairs_value(t)` / `ripairs_value(t)` — 先回傳值的迭代器

### version.lua — 版本管理

```lua
engine.version_check(v)          -- 比較 v 與引擎版本
engine.version_compare(v, ev)    -- 比較兩個版本 table
engine.version_nearly_same(v, ev) -- 檢查 major/minor 相容性
engine.version_from_string(s)    -- 解析 "x.y.z" 或 "name-x.y.z"
```

回傳值：`"newer"`, `"lower"`, `"same"`, `"different engine"`, `"bad C core"`

---

## 19. 關鍵設計模式總結

| 模式 | 應用 |
|------|------|
| **Mixin 繼承** | `engine/interface/` 所有介面，Actor 按需組合 |
| **Data-driven 定義** | `newTalent`, `newEffect`, `newDamageType` — 資料與邏輯同在定義 table |
| **兩階段初始化** | Entity define（原型）→ resolve（實例），支援延遲亂數計算 |
| **命名行為** | AI 系統以字串 key 組合行為，可在運行時動態切換 |
| **弱引用追蹤** | `__uids`, `entities`, `ai_target`, FOV actors，讓 GC 自然清理死亡實體 |
| **每物件存一檔** | 存檔用 zip 內多 Lua 檔，跨物件引用用 hash 連結，天然支援 graph 結構 |
| **Hook 系統** | 模組可在不修改引擎的情況下，在任何 hook 點注入邏輯 |
| **延遲載入** | Shader、存檔物件首次使用時才真正初始化 |
| **動態函數編譯** | Map 的實體檢查函數、ActorResource 的回復函數，按需編譯提升效能 |
| **臨時值 ID 追蹤** | 所有加成透過 ID 可逆撤銷（裝備、技能、效果），不需手動管理 |
| **協程目標選擇** | GameTargeting / ActorTalents 用協程暫停等待玩家輸入，避免回呼地獄 |
| **模板方法** | Store 的 tryBuy/onBuy、PlayerRest 的 restCheck()，預留覆寫點 |
| **Registry Pattern** | DamageType, Faction, WorldAchievements 維護全域定義登錄表 |
| **LRU Cache** | Zone 最近造訪層快取（`enableLastPersistZones`），減少磁碟讀寫 |
| **概率生成系統** | Zone 的 `computeRarities()`，稀有度 × 深度差的加權生成 |
