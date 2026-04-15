# T-Engine 4 — ToME 1.7.6 內容層詳細分析

> 本文件是 `game_detail.md` 的補充，專注分析 `game/modules/tome-1.7.6/` 中尚未深入記錄的子系統：內容資料層、對話框系統、任務系統、史料系統、自訂生成器、UI 主題。

---

## 目錄

1. [data/general/ — 核心內容資料](#1-datageneral--核心內容資料)
   - 1.1 [NPC 定義（npcs/）](#11-npc-定義-npcs)
   - 1.2 [物品定義（objects/）](#12-物品定義-objects)
   - 1.3 [地形定義（grids/）](#13-地形定義-grids)
   - 1.4 [商店定義（stores/）](#14-商店定義-stores)
   - 1.5 [陷阱定義（traps/）](#15-陷阱定義-traps)
   - 1.6 [事件系統（events/）](#16-事件系統-events)
   - 1.7 [遭遇系統（encounters/）](#17-遭遇系統-encounters)
2. [mod/dialogs/ — 對話框系統](#2-moddialogs--對話框系統)
3. [data/quests/ — 任務系統](#3-dataquests--任務系統)
4. [data/lore/ — 史料系統](#4-datalore--史料系統)
5. [mod/class/generator/ — 自訂生成器](#5-modclassgenerator--自訂生成器)
6. [mod/class/uiset/ — UI 主題系統](#6-modclassuiset--ui-主題系統)
7. [系統間關係總覽](#7-系統間關係總覽)

---

## 1. data/general/ — 核心內容資料

### 1.1 NPC 定義 (npcs/)

共 **72 個 NPC 定義檔案**，以生物種類組織。

#### 檔案分類

**普通生物（野生動物）**

| 檔案 | 生物類型 |
|------|---------|
| `bear.lua` | 熊類（黑熊、灰熊、大黑熊等）|
| `canine.lua` | 犬科（狼、蜘蛛犬、渡鴉等）|
| `bird.lua` | 鳥類（蝙蝠、老鷹等）|
| `feline.lua` | 貓科（山貓、豹等）|
| `rodent.lua` | 齧齒類（大鼠、松鼠等）|
| `snake.lua` | 蛇類（蛇蝎、巨蟒等）|
| `ant.lua` | 螞蟻類（兵蟻、蟻后等）|
| `aquatic_critter.lua` | 水生生物 |

**不死生物**

| 檔案 | 說明 |
|------|------|
| `skeleton.lua` | 骷髏（戰士/弓手/法師/精英）|
| `mummy.lua` | 木乃伊 |
| `ghost.lua` | 幽靈（含相位穿牆能力）|
| `ghoul.lua` | 食屍鬼 |
| `wight.lua` | 惡靈 |
| `vampire.lua` | 吸血鬼（含魅惑技能）|
| `lich.lua` | 巫妖（高等不死法師）|
| `undead-rat.lua` | 不死鼠（特殊任務相關）|

**惡魔類**

| 檔案 | 說明 |
|------|------|
| `minor-demon.lua` | 小惡魔（Imp、Quasit 等）|
| `major-demon.lua` | 大惡魔（Balrog 類等）|
| `aquatic_demon.lua` | 水生惡魔 |

**龍類**

| 檔案 | 說明 |
|------|------|
| `cold-drake.lua` | 冰龍（含冰霜吐息）|
| `fire-drake.lua` | 火龍（含火焰吐息）|
| `storm-drake.lua` | 風暴龍（含閃電吐息）|
| `venom-drake.lua` | 毒龍（含毒液吐息）|
| `wild-drake.lua` | 野性龍 |
| `multihued-drake.lua` | 多彩龍（多種吐息）|

**人形生物**

| 檔案 | 說明 |
|------|------|
| `elven-caster.lua` | 精靈法師 |
| `elven-warrior.lua` | 精靈戰士 |
| `orc.lua` | 獸人（4 個地區變體：gorbat/grushnak/rak-shor/vor）|
| `thieve.lua` | 盜賊 |
| `minotaur.lua` | 牛頭人 |
| `humanoid_random_boss.lua` | 動態隨機菁英人形生物 |

**特殊/BOSS**

| 檔案 | 大小 | 說明 |
|------|------|------|
| `horror.lua` | 43KB（最大）| 各類恐怖生物（含大量 Goroth 系列）|
| `horror_aquatic.lua` | — | 水生恐怖 |
| `horror-corrupted.lua` | — | 腐化恐怖 |
| `horror-undead.lua` | — | 不死恐怖 |
| `horror_temporal.lua` | — | 時空恐怖 |
| `gwelgoroth.lua` | — | 特殊 boss |
| `losgoroth.lua` | — | 特殊 boss |
| `shivgoroth.lua` | — | 特殊 boss |
| `telugoroth.lua` | — | 特殊 boss |
| `ziguranth.lua` | — | 反魔法派系成員 |
| `sandworm.lua` | — | 沙蟲（含 sandworm_tunneler AI）|

**特殊生物**

| 檔案 | 說明 |
|------|------|
| `crystal.lua` | 水晶生物（無AI，靜止掉落）|
| `ooze.lua` / `jelly.lua` | 軟體生物（分裂、吸收等特性）|
| `swarm.lua` | 群集生物 |
| `plant.lua` / `molds.lua` | 植物/黴菌 |
| `shade.lua` | 影子生物 |
| `construct.lua` | 魔法構裝體 |
| `ritch.lua` | Ritch（巨蟲）|
| `xorn.lua` | Xorn（石化生物）|
| `yaech.lua` | Yaech（奈迦族）|
| `naga.lua` | 奈迦 |
| `shertul.lua` | Sher'Tul（古老智慧種族）|
| `spider.lua` | 蜘蛛 |

#### NPC 實體定義結構

```lua
newEntity{
    define_as = "BASE_NPC_SKELETON",
    type = "undead", subtype = "skeleton",
    name = _t"skeleton", color = colors.WHITE,
    display = 's', image = "npc/undead_skeleton_warrior.png",
    -- 等級與屬性
    level_range = {1, 20}, exp_worth = 1,
    max_life = resolvers.rngrange(20, 30),
    stats = {str=14, dex=12, con=10, mag=10, wil=10, cun=10},
    -- 戰鬥屬性
    combat = {dam=resolvers.rngrange(5,8), atk=5, apr=3},
    resists = {[DamageType.COLD]=100, [DamageType.POISON]="immune"},
    -- AI 與行為
    rank = 2,  -- 2=普通, 3=稀有, 3.5+=Boss
    ai = "dumb_talented", ai_state = {talent_in=3},
    autolevel = "warrior",  -- 自動升級方案
    -- 技能
    talents = {[T_BONE_SHIELD]=1},
    -- 掉落
    drops = resolvers.drops{chance=100, nb=2, {type="money"}},
    -- 材料
    ingredient_on_death = {id="BONE", nb=1},
}
```

#### 唯一怪（Unique）系統

- `define_as` 以大寫命名（如 `"RHALOREN_QUEST_BOSS"`）
- `unique = true` 標記唯一，每個存檔只出現一次
- 通常有自訂名稱、台詞、裝備和特殊掉落
- `flavor_on_death` 設定死亡時顯示的特殊訊息

---

### 1.2 物品定義 (objects/)

共 **60+ 個物品定義檔案**，按類型組織。

#### 武器類

| 檔案 | 武器類型 |
|------|---------|
| `swords.lua` | 單手劍 |
| `axes.lua` | 單手斧 |
| `maces.lua` | 單手棒錘 |
| `knifes.lua` | 匕首/短刀 |
| `whips.lua` | 鞭子 |
| `polearms.lua` | 長柄武器 |
| `2hswords.lua` / `2haxes.lua` / `2hmaces.lua` / `2htridents.lua` | 雙手武器 |
| `bows.lua` | 弓 |
| `slings.lua` | 投石器 |
| `digger.lua` | 挖掘工具 |
| `staves.lua` | 魔杖（法師專用）|
| `mindstars.lua` | 心靈星（心靈師專用）|
| `totems.lua` | 圖騰（召喚師專用）|

#### 防具類

| 檔案 | 防具位置 |
|------|---------|
| `cloth-armors.lua` | 布甲（法袍）|
| `light-armors.lua` | 輕甲（皮革）|
| `heavy-armors.lua` | 重甲（鎖甲）|
| `massive-armors.lua` | 板甲（全身甲）|
| `helms.lua` | 頭盔 |
| `leather-caps.lua` | 皮革帽 |
| `leather-boots.lua` | 皮革靴 |
| `heavy-boots.lua` | 重型靴 |
| `gauntlets.lua` | 板甲手套 |
| `gloves.lua` | 皮革手套 |
| `shields.lua` | 盾牌 |
| `leather-belt.lua` | 腰帶 |
| `jewelry.lua` | 珠寶（戒指/項鍊）|
| `lites.lua` | 光源（火把/燈籠/符文石）|

#### 消耗品

| 檔案 | 說明 |
|------|------|
| `potions.lua` | 藥水（治療/屬性/特效）|
| `scrolls.lua` | 卷軸（傳送/辨識/地圖）|
| `rods.lua` | 法杖（可充能的魔法道具）|
| `wands.lua` | 魔棒（可消耗的魔法道具）|

#### 神器（Artifacts）

| 檔案 | 大小 | 說明 |
|------|------|------|
| `world-artifacts.lua` | 313KB（最大）| 主要世界傳奇神器（數百件）|
| `world-artifacts-maj-eyal.lua` | 47KB | Maj'Eyal 地區神器 |
| `world-artifacts-far-east.lua` | 21KB | 遠東地區神器 |
| `boss-artifacts.lua` | 8KB | 通用 Boss 掉落神器 |
| `boss-artifacts-maj-eyal.lua` | 67KB | Maj'Eyal Boss 神器 |
| `boss-artifacts-far-east.lua` | 21KB | 遠東 Boss 神器 |
| `brotherhood-artifacts.lua` | 13KB | 煉金士兄弟會神器 |
| `quest-artifacts.lua` | 17KB | 任務關鍵神器 |
| `special-artifacts.lua` | 4KB | 特殊機制神器 |

#### Ego 系統（物品詞綴）

`egos/` 目錄包含物品詞綴定義：
- **前綴 ego**（如 「燃燒的」、「冰冷的」）：修改物品基礎屬性
- **後綴 ego**（如 「敏捷之」、「力量之」）：添加屬性加成
- **特殊 ego**：`special_on_hit`、`talent_on_hit`、`on_block` 等特殊效果

```lua
-- ego 定義範例
newEntity{
    power_source = {arcane=true},
    name = _t"of striking",
    keywords = {striking=true},
    level_range = {1, 50},
    rarity = 10,
    wielder = {
        combat_atk = resolvers.mbonus(12, 5),
    },
}
```

#### 物品辨識系統

- `unided_name`：未辨識時的名稱（如 "red potion"）
- `desc`：辨識後顯示的說明
- `identified`：是否已辨識（武器/防具預設為 true，藥水/卷軸預設為 false）

#### 區域性物品

- `tome_drops`：控制物品在哪些情境出現（`"Maj'Eyal"`, `"Far East"` 等）
- `level_range`：物品出現的等級範圍
- `rarity`：越高越少見

#### 隨機神器（Randart）

`random-artifacts.lua` 定義隨機神器的生成規則：
- 基於基礎物品加上隨機 ego 與屬性
- `GameState:generateRandart(data)` 呼叫
- 強大神器系統（Randart Power Budget）控制平衡

---

### 1.3 地形定義 (grids/)

共 **30 個地形定義檔案**，依環境主題組織。

#### 檔案分類

**自然環境**

| 檔案 | 環境 |
|------|------|
| `forest.lua` | 森林（樹木、草地、荊棘）|
| `jungle.lua` | 叢林（熱帶植被）|
| `ice.lua` | 冰雪（冰原、凍土）|
| `underground.lua` | 地下（岩石、洞窟）|
| `cave.lua` | 山洞 |
| `lava.lua` | 熔岩（岩漿地形、傷害地板）|
| `sand.lua` / `sanddunes.lua` | 沙漠（沙地、沙丘）|
| `mountain.lua` | 山地 |
| `water.lua` | 水域（淺水、深水、沼澤）|
| `autumn_forest.lua` | 秋天森林 |
| `snowy_forest.lua` | 積雪森林 |
| `elven_forest.lua` | 精靈森林 |

**地城主題**

| 檔案 | 主題 |
|------|------|
| `gothic.lua` | 哥特式（石磚牆、拱頂）|
| `fortress.lua` | 要塞（城堡磚牆）|
| `bone.lua` | 骨頭（獸人城市美術風格）|
| `malrok_walls.lua` | Malrok 牆壁（特殊地城）|
| `slimy_walls.lua` | 黏液牆壁 |
| `crystal.lua` | 水晶地形 |
| `void.lua` | 虛空（宇宙背景）|
| `psicave.lua` | 心靈山洞 |
| `slime.lua` | 黏液地形 |
| `burntland.lua` | 燒焦大地 |

**特殊環境**

| 檔案 | 說明 |
|------|------|
| `icecave.lua` | 冰窟 |
| `underground_dreamy.lua` | 夢境地下 |
| `underground_gloomy.lua` | 陰鬱地下 |
| `underground_slimy.lua` | 黏液地下 |
| `jungle_hut.lua` | 叢林小屋 |

**核心定義**

`basic.lua`（25KB）：最主要的地形定義，包含：
- FLOOR（地板）/ WALL（牆壁）基礎類型
- DOOR / DOOR_LOCKED / DOOR_BLOCKED（各類門）
- STAIRS_UP / STAIRS_DOWN（樓梯）
- 特殊互動地形

#### 地形屬性

```lua
newEntity{
    define_as = "FLOOR",
    type = "floor",
    name = _t"floor",
    display = '.', color = colors.GREY,
    -- 通行性
    block_move = false,
    block_sight = false,
    -- 地圖顯示
    special_minimap = colors.WHITE,
    -- 互動回呼
    on_stand = function(self, x, y, who) ... end,
    on_dig = function(self, x, y, who) ... end,
}
```

**特殊 Grid 屬性**（`mod/class/Grid.lua` 擴展）：

| 屬性 | 說明 |
|------|------|
| `door_opened` | 開門後替換的 Grid |
| `door_player_check` | 開門前顯示的確認對話框 |
| `change_zone` | 傳送目標（樓梯用）|
| `air_level` / `air_condition` | 空氣供應量/類型（水下地形）|
| `translate_into_region` | 傳送至地區內部坐標 |

---

### 1.4 商店定義 (stores/)

**`basic.lua`**（22KB）：完整商店/供應商系統。

#### 商店類型

| 商店名稱 | 商品類型 |
|---------|---------|
| Heavy Armor Smith | 重甲、板甲 |
| Light Armor Tanner | 輕甲、布甲 |
| Weapon Smith | 各類武器 |
| Potion Alchemist | 藥水、消耗品 |
| Scroll Vendor | 卷軸、魔棒 |
| Jewelry Vendor | 戒指、項鍊 |
| Gem Vendor | 寶石（材料）|
| General Loot | 混合物品 |
| Faction Merchant | 陣營限定物品 |

#### 商店配置

```lua
newEntity{
    name = _t"heavy armor store",
    store_filter = "tome_store",
    purse = 200,          -- 商人金幣（影響最大收購價）
    nb_fill = 10,          -- 庫存格數
    filters = {            -- 允許的物品類型篩選
        {type="armor", subtype="massive"},
        {type="armor", subtype="heavy"},
        {type="armor", subtype="shield"},
    },
    empty_before_restock = true,   -- 補貨前清空
    restock_on_zone_change = true, -- 換地區時補貨
}
```

**定價規則**：
- 基礎買入價 = 物品原價 × 1.0
- 賣出價：寶石為 40%，其他物品為 5%
- 陣營友好度加成（Angolwen 等特殊商人有折扣）

---

### 1.5 陷阱定義 (traps/)

共 **9 個陷阱類型檔案**。

#### 陷阱類型

| 檔案 | 陷阱類別 |
|------|---------|
| `alarm.lua` | 警報陷阱（召喚敵人）|
| `annoy.lua` | 騷擾陷阱（弱效果）|
| `complex.lua` | 複雜陷阱（多效果組合）|
| `elemental.lua` | 元素陷阱（火/冰/閃電/酸）|
| `natural_forest.lua` | 自然森林陷阱（荊棘/植物）|
| `teleport.lua` | 傳送陷阱（隨機/陷阱房間）|
| `temporal.lua` | 時間陷阱（減速/時間歸零）|
| `water.lua` | 水中陷阱 |
| `store.lua` | 商店陷阱（有代價的獎勵）|

#### 陷阱定義結構

```lua
newEntity{
    type = "trap", subtype = "elemental",
    name = _t"fire trap",
    display = '^', color = colors.RED,
    -- 偵測與拆除
    detect_power = 10,   -- 偵測難度
    disarm_power = 12,   -- 拆除難度
    -- 觸發效果
    triggered = function(self, x, y, who)
        game.level.map:particleEmitter(x, y, 1, "fire")
        who:takeHit(rng.avg(10, 25), self, {type="fire"})
        game.logSeen(who, "A fire trap activates!")
    end,
    -- 出現條件
    rarity = 10, level_range = {1, 30},
    -- 外觀
    disarmed = {define_as = "DISARMED_FIRE_TRAP"},
}
```

---

### 1.6 事件系統 (events/)

共 **34 個程序性世界事件**，隨機修改已生成的地圖。

#### 事件類型

**環境修改類**

| 事件檔 | 說明 |
|--------|------|
| `antimagic-bush.lua` | 反魔法荊棘（傷害魔法使用者）|
| `blighted-soil.lua` | 枯萎土地（腐化效果）|
| `pyroclast.lua` | 火山噴發（熔岩地形）|
| `meteor.lua` | 隕石（坑洞地形）|
| `thunderstorm.lua` | 雷暴（閃電環境效果）|
| `snowstorm.lua` | 雪暴（寒冷環境效果）|
| `drake-cave.lua` | 龍巢穴（特殊地形）|
| `damp-cave.lua` | 潮濕山洞 |

**稀有特殊事件**

| 事件檔 | 大小 | 說明 |
|--------|------|------|
| `cultists.lua` | 11KB | 邪教徒 NPC 群出現 |
| `fearscape-portal.lua` | 9.4KB | 恐懼界入口傳送門 |
| `naga-portal.lua` | 7.6KB | 奈迦界傳送門 |
| `rat-lich.lua` | 7KB | 鼠妖（特殊 Boss 遭遇）|
| `sub-vault.lua` | 6.2KB | 程序性寶庫變體 |
| `old-battle-field.lua` | 7.7KB | 古戰場殘跡（戰利品/危機）|
| `glowing-chest.lua` | 4KB | 發光寶箱（特殊獎勵）|
| `weird-pedestals.lua` | 5.7KB | 古代台座（謎題）|

#### 事件執行流程

```lua
-- 事件定義範例
newEvent{
    name = "meteor",
    rarity = 10,     -- 出現機率（越高越少見）
    -- 觸發條件
    filter = function(self, zone, level, spot)
        return zone.short_name ~= "underwater"
    end,
    -- 生成邏輯
    generate = function(self, zone, level, spot)
        local x, y = spot.x, spot.y
        -- 1. 找到地圖上的合適位置
        local gx, gy = game.state:findEventGrid(level, x, y, 8)
        if not gx then return end
        -- 2. 修改地形
        level.map(gx, gy, Map.TERRAIN, terrains.CRATER)
        -- 3. 添加視覺效果
        level.map:particleEmitter(gx, gy, 2, "smoke_cloud")
        -- 4. 設置互動回呼
        level.map(gx, gy, Map.TERRAIN).on_stand = function(self, x, y, who)
            who:takeHit(rng.avg(5, 10), nil, {type="physical"})
        end
    end,
}
```

#### 事件分組 (events/groups/)

每個地區類型使用一個事件組定義可能出現的事件：

| 分組檔 | 用途 |
|--------|------|
| `majeyal-generic.lua` | Maj'Eyal 地下城通用事件 |
| `fareast-generic.lua` | 遠東地下城通用事件 |
| `outdoor-majeyal-generic.lua` | Maj'Eyal 戶外通用事件 |
| `outdoor-majeyal-gloomy.lua` | Maj'Eyal 陰鬱戶外事件 |
| `outdoor-fareast-generic.lua` | 遠東戶外事件 |

分組中的事件有個別出現機率（如：weird-pedestals 10%出現率）。

---

### 1.7 遭遇系統 (encounters/)

共 **4 個遭遇定義檔案**，用於世界地圖上的特殊 NPC 遭遇。

#### 遭遇檔案

| 檔案 | 大小 | 說明 |
|------|------|------|
| `maj-eyal.lua` | 10KB | 主大陸遭遇事件 |
| `fareast.lua` | 3.5KB | 遠東地區遭遇事件 |
| `maj-eyal-npcs.lua` | 4.2KB | 遭遇中使用的 NPC 定義 |
| `fareast-npcs.lua` | 2.5KB | 遠東遭遇 NPC |

#### 遭遇機制

```lua
-- 遭遇定義結構
newEntity{
    define_as = "ENCOUNTER_MERCHANT",
    type = "encounter",
    name = _t"lost merchant",
    -- 生成條件
    level_range = {5, 25}, rarity = 15,
    min_lore = 0,
    -- 是否立即觸發（或需要玩家踩上去）
    immediate = true,
    -- 觸發邏輯
    on_encounter = function(self, who, x, y)
        -- 生成 WorldNPC 並設置對話
        local npc = game.zone:makeEntityByName(game.level, "worldnpc", "LOST_MERCHANT")
        game.zone:addEntity(game.level, npc, "worldnpc", x, y)
        npc:talkTo(who)
    end,
    -- 特殊條件過濾
    special_filter = function(self, who)
        return not who:hasQuest("lost-merchant")
    end,
}
```

**遭遇觸發鏈**：世界地圖行走 → 觸發遭遇 → 生成 WorldNPC → 啟動對話/任務 → 更新任務狀態

---

## 2. mod/dialogs/ — 對話框系統

共 **44+ 對話框檔案**，實現所有玩家互動介面。

### 2.1 核心遊戲對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `Birther.lua` | 72KB | 角色創建畫面（出生選擇流程）|
| `CharacterSheet.lua` | 97KB | 角色資訊/裝備全覽頁面 |
| `LevelupDialog.lua` | 48KB | 升級技能選擇 |
| `GameOptions.lua` | 48KB | 遊戲設定選單 |
| `DeathDialog.lua` | 14KB | 死亡畫面與重生選項 |

### 2.2 物品管理對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `ShowEquipInven.lua` | 13KB | 裝備 + 背包合併檢視 |
| `ShowEquipment.lua` | 3.4KB | 純裝備欄位 |
| `ShowInventory.lua` | 4.4KB | 純背包內容 |
| `ShowPickupFloor.lua` | 2.4KB | 地板物品拾取 |
| `ShowStore.lua` | 10KB | 商店買賣介面 |
| `UseItemDialog.lua` | 9.5KB | 使用物品確認 |
| `SwiftHands.lua` | 5.6KB | 快速換裝介面 |
| `SwiftHandsUse.lua` | 4.3KB | 快速使用消耗品 |
| `SentientWeapon.lua` | 9.4KB | 有靈性武器互動 |

### 2.3 技能相關對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `UseTalents.lua` | 18KB | 技能使用選單 |
| `UberTalent.lua` | 11KB | 偉業技能特殊互動 |

**talents/ 子目錄**（具時間魔法技能的特殊 UI）：
- `Contingency.lua`、`Empower.lua`、`Extension.lua`、`Matrix.lua`、`Quicken.lua`
- `MagicalCombatArcaneCombat.lua`

### 2.4 資訊顯示對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `ShowMap.lua` | 3.9KB | 世界地圖 |
| `ShowLore.lua` | 4.3KB | 史料書/圖鑑 |
| `ShowIngredients.lua` | 2.9KB | 工藝材料庫存 |
| `ShowChatLog.lua` | 11KB | 訊息歷史記錄 |
| `ShowAchievements.lua` | 3.4KB | 成就列表 |
| `LorePopup.lua` | 4KB | 新史料彈出提示 |
| `QuestPopup.lua` | 4.5KB | 任務通知 |

### 2.5 隊伍管理對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `PartyOrder.lua` | 3.3KB | 隊伍命令（攻擊/防守等）|
| `PartySelect.lua` | 2.1KB | 選擇隊伍成員 |
| `PartySendItem.lua` | 3.1KB | 物品傳給隊友 |
| `PartyRewardSelector.lua` | 1.9KB | 戰利品分配選擇 |

### 2.6 特殊系統對話框

| 檔案 | 大小 | 功能 |
|------|------|------|
| `Chat.lua` | 7.7KB | NPC 對話系統（選項樹狀）|
| `MapMenu.lua` | 11KB | 地圖互動選單（右鍵）|
| `GraphicMode.lua` | 5.7KB | 圖形設定頁 |
| `OptionTree.lua` | 6.4KB | 階層式選項選單 |
| `ArenaFinish.lua` | 2.2KB | 競技場結算 |
| `Donation.lua` | 5.2KB | 永久死亡角色捐贈 |
| `UnlockDialog.lua` | 1.7KB | 解鎖成就通知 |
| `WandererSeed.lua` | 6.9KB | 流浪者模式種子設定 |

### 2.7 外觀系統（shimmer/ 子目錄）

Shimmer 是 ToME 的外觀自訂系統（贊助功能）：

| 檔案 | 說明 |
|------|------|
| `Shimmer.lua` | 外觀系統基礎 |
| `ShimmerOutfits.lua` | 服裝/外觀配色選擇 |
| `ShimmerOther.lua` | 其他外觀選項 |
| `ShimmerRemoveSustains.lua` | 移除持續效果（外觀相關）|
| `ShimmerDemo.lua` | 外觀預覽功能 |
| `CommonData.lua` | 共用外觀資料 |

### 2.8 隨從命令（orders/ 子目錄）

| 檔案 | 說明 |
|------|------|
| `Behavior.lua` | 設定隨從 AI 行為策略 |
| `Talents.lua` | 設定隨從使用哪些技能 |

### 2.9 UI 元件（elements/ 子目錄）

| 檔案 | 說明 |
|------|------|
| `ChatPortrait.lua` | NPC 對話肖像顯示 |
| `StatusBox.lua` | 狀態指示器小部件 |
| `TalentGrid.lua` | 技能格子顯示（升級/選擇）|
| `TalentTrees.lua` | 技能樹排版系統 |

### 2.10 除錯工具（dialogs/debug/ 子目錄）

共 **14 個除錯工具**，`cheat_only=true` 限制：

| 檔案 | 大小 | 功能 |
|------|------|------|
| `AdvanceActor.lua` | 15KB | 測試 Actor 升級 |
| `AdvanceZones.lua` | 11KB | 跳過地區進度 |
| `RandomActor.lua` | 14KB | 生成隨機 NPC |
| `RandomObject.lua` | 29KB | 生成隨機物品（最大）|
| `CreateItem.lua` | 14KB | 指定生成物品 |
| `Endgamify.lua` | 10KB | 模擬終局內容 |
| `DebugMain.lua` | 7.5KB | 除錯主選單 |
| `PlotTalent.lua` | 5.6KB | 技能測試 |
| `SummonCreature.lua` | 6KB | 召喚生物 |
| `AlterFaction.lua` | 3KB | 調整陣營關係 |
| `ChangeZone.lua` | 3KB | 傳送至指定地區 |
| `CreateTrap.lua` | 3.4KB | 放置陷阱 |
| `GrantQuest.lua` | 3KB | 啟動任務 |
| `SpawnEvent.lua` | 3KB | 觸發世界事件 |
| `ReloadZone.lua` | 1.4KB | 重新載入地區 |

---

## 3. data/quests/ — 任務系統

共 **49 個任務定義檔案**，實現完整的任務追蹤與進度管理。

### 3.1 起始任務（職業/種族專屬）

| 檔案 | 說明 |
|------|------|
| `start-allied.lua` | Allied Kingdoms 開始任務 |
| `start-archmage.lua` | 大法師職業特殊開場 |
| `start-dwarf.lua` | 矮人種族開場 |
| `start-shaloren.lua` | Shaloren 精靈開場 |
| `start-sunwall.lua` | 太陽之牆開場 |
| `start-thaloren.lua` | Thaloren 精靈開場 |
| `start-undead.lua` | 不死種族特殊開場 |
| `start-yeek.lua` | Yeek 種族開場 |
| `start-point-zero.lua` | Point Zero（時空裂縫）開場 |
| `starter-zones.lua` | 新手地區進度追蹤 |

### 3.2 主線任務鏈

| 任務 | 大小 | 說明 |
|------|------|------|
| `high-peak.lua` | 13KB | 主線終章：攻克 High Peak |
| `shertul-fortress.lua` | 10KB | 中線：解鎖 Sher'Tul 要塞 |
| `west-portal.lua` | 4.8KB | 主線：開啟西方傳送門 |
| `east-portal.lua` | 7.8KB | 主線：前往遠東 |
| `keepsake.lua` | 12KB | 神器保護任務 |
| `pre-charred-scar.lua` | — | 焦土峽谷前置 |

### 3.3 Tier 1 新手任務組

控制新手階段可訪問的地區序列（via `starter-zones.lua`）：
- 選擇其中 **2 個** Tier 1 地區（共 7 個可選）
- 完成後解鎖 High Peak 主線

### 3.4 側線任務

**職業相關**

| 任務 | 說明 |
|------|------|
| `antimagic.lua` | 加入 Ziguranth（反魔法路線）|
| `anti-antimagic.lua` | 加入 Angolwen（魔法路線）|
| `brotherhood-of-alchemists.lua` | 煉金士兄弟會配方任務（17KB）|
| `lichform.lua` | 巫妖轉化任務 |
| `lightning-overload.lua` | 法師閃電過載技能解鎖 |
| `paradoxology.lua` | 時空術師悖論研究 |
| `staff-absorption.lua` | 法杖吸收技能 |

**劇情側線**

| 任務 | 說明 |
|------|------|
| `love-melinda.lua` | Melinda 人質救援（情感線）|
| `mage-apprentice.lua` | 法師學徒指導 |
| `master-jeweler.lua` | 珠寶師工藝任務 |
| `ring-of-blood.lua` | 血戒契約 |
| `kryl-feijan-escape.lua` | Kryl-Feijan 越獄 |

**BOSS 觸發任務**

| 任務 | 說明 |
|------|------|
| `orc-pride.lua` | 消滅四個獸人部落 |
| `orc-breeding-pits.lua` | 清除獸人繁殖穴 |
| `orc-hunt.lua` | 特定獸人獵殺 |
| `dreadfell.lua` | Dreadfell 地城任務 |
| `deep-bellow.lua` | Deep Bellow 地城 |
| `grave-necromancer.lua` | 巫妖獵殺 |

**世界事件任務**

| 任務 | 說明 |
|------|------|
| `escort-duty.lua` | 護送任務（隨機生成護送 NPC）|
| `lost-merchant.lua` | 失蹤商人救援 |
| `lumberjack-cursed.lua` | 受詛咒的伐木工 |
| `spydric-infestation.lua` | 蜘蛛侵擾 |
| `temple-of-creation.lua` | 創造神殿探索 |
| `temporal-rift.lua` | 時空裂縫消除 |
| `trollmire-treasure.lua` | 巨魔之沼寶藏 |
| `void-gerlyk.lua` | Void 實體 Gerlyk |

**特殊模式任務**

| 任務 | 說明 |
|------|------|
| `arena.lua` | 競技場波次 |
| `arena-unlock.lua` | 競技場解鎖條件 |
| `infinite-dungeon.lua` | 無限地城記錄 |

### 3.5 任務定義結構

```lua
-- data/quests/example-quest.lua
name = _t"Main Quest: End the Threat"
desc = function(self, who)
    -- 根據任務狀態動態生成描述
    local desc = {}
    desc[#desc+1] = _t"You must defeat the great evil."
    if self:isCompleted("boss_killed") then
        desc[#desc+1] = "#LIGHT_GREEN#"..
            _t"* You have killed the boss!"
    else
        desc[#desc+1] = "#YELLOW#"..
            _t"* Find and kill the boss."
    end
    return table.concat(desc, "\n")
end
on_grant = function(self, who)
    -- 接受任務時執行
    game.logCenter(_t"A new quest begins!", ...)
end
on_status_change = function(self, who, status, sub)
    -- sub = 子狀態名稱
    if status == self.COMPLETED then
        who:grantReward(...)
    end
end
```

**任務狀態流**：未開始 → 進行中（`STARTED`）→ 完成（`COMPLETED`）/ 失敗（`FAILED`）

**子任務（substatus）**：`self:setSubStatus("boss_killed", true)` 追蹤各個子目標

---

## 4. data/lore/ — 史料系統

共 **36 個史料定義檔案**，構建世界觀知識體系。

### 4.1 史料分類

**地點史料**

| 檔案 | 記錄地點 |
|------|---------|
| `angolwen.lua` | 法師城市 Angolwen |
| `ardhungol.lua` | 蜘蛛巢穴 Ardhungol |
| `daikara.lua` | 火山 Daikara |
| `derth.lua` | 城鎮 Derth |
| `dreadfell.lua` | 恐懼要塞 |
| `kor-pul.lua` | Kor'Pul 地下城 |
| `last-hope.lua` | 最後希望城市 |
| `maze.lua` | 大迷宮 |
| `scintillating-caves.lua` | 閃耀洞窟 |
| `sandworm.lua` | 沙蟲領域 |
| `trollmire.lua` | 巨魔之沼 |

**派系/勢力史料**

| 檔案 | 說明 |
|------|------|
| `rhaloren.lua` | Rhaloren 精靈 |
| `shertul.lua` | Sher'Tul 古族 |
| `slazish.lua` | Slazish 族 |
| `spellhunt.lua` | 反魔法獵巫 |
| `sunwall.lua` | 太陽之牆 |
| `tannen.lua` | 法師 Tannen |
| `zigur.lua` | Zigur 城市（反魔法）|
| `iron-throne.lua` | 鐵王座帝國 |
| `orc-prides.lua` | 獸人部落 |
| `elvala.lua` | Elvala 精靈地 |

**劇情史料**

| 檔案 | 說明 |
|------|------|
| `fearscape.lua` | 恐懼界 |
| `spellblaze.lua` | 魔法大爆炸歷史 |
| `high-peak.lua` | High Peak 故事 |

**特殊史料**

| 檔案 | 大小 | 說明 |
|------|------|------|
| `misc.lua` | 85KB（最大）| 綜合世界史料（大量內容）|
| `fun.lua` | — | 幽默彩蛋條目 |
| `arena.lua` | — | 競技場相關史料 |
| `lore.lua` | — | 載入器（載入所有史料檔）|

### 4.2 史料條目結構

```lua
newLore{
    id = "temple-creation-note-1",  -- 唯一識別符
    category = "temple of creation",  -- 分類（ShowLore 中分組）
    name = _t"tract of destruction",  -- 顯示名稱
    lore = _t[[
#{bold}#On the Nature of the Spellblaze#{normal}#

In the age before the Spellblaze, the great mages...
    ]],
}
```

**文字格式化標記**：

| 標記 | 效果 |
|------|------|
| `#{bold}#...#{normal}#` | 粗體文字 |
| `#{italic}#...#{normal}#` | 斜體文字 |
| `#GOLD#...#LAST#` | 金色文字 |
| `#LIGHT_GREEN#...#LAST#` | 亮綠色 |
| `#RED#...#LAST#` | 紅色警告 |

### 4.3 史料發現機制

1. **地圖物品**：特殊「史料書」物品被拾取時觸發
2. **NPC 對話**：對話中選擇特定選項解鎖
3. **地形互動**：踩到特殊地板/物件
4. **事件觸發**：完成特定事件後自動解鎖

**發現時行為**（`PartyLore` 混入）：
- 打斷玩家的休息/奔跑
- 彈出 `LorePopup` 通知
- 記錄到 `PartyLore.lore` 表

---

## 5. mod/class/generator/ — 自訂生成器

ToME 在引擎標準生成器之上，實作了許多特化生成器。

### 5.1 Actor 生成器 (generator/actor/)

| 檔案 | 大小 | 說明 |
|------|------|------|
| `Arena.lua` | 25KB | 競技場 NPC 生成（波次系統）|
| `Random.lua` | 2.6KB | 隨機 Actor 覆蓋（ToME 特定規則）|
| `OnSpots.lua` | 2.6KB | 在指定位置生成 NPC |
| `RandomStairGuard.lua` | 1.9KB | 在樓梯旁生成守衛 |
| `CharredScar.lua` | 1.8KB | 焦土峽谷特有 NPC |
| `Sandworm.lua` | 2KB | 沙蟲遭遇生成 |
| `ValleyMoon.lua` | 3.5KB | 月之谷遭遇 |
| `HighPeakFinal.lua` | 1.9KB | High Peak 最終 Boss 生成 |

**Arena.lua — 波次系統核心**：
- 按波次（Wave）定義不同難度的 NPC 組合
- 支援隨機選擇池（weighted random）
- 每波清除後自動生成下一波
- 記錄最高波次到排行榜

### 5.2 Map 生成器 (generator/map/)

| 檔案 | 大小 | 說明 |
|------|------|------|
| `StaticPredrawn.lua` | 25KB | 預繪製地圖載入器（最大）|
| `VaultLevel.lua` | 5KB | 寶庫關卡生成 |
| `GenericTunnel.lua` | 2.4KB | 通用隧道生成 |
| `SlimeTunnels.lua` | 2.6KB | 黏液隧道（視覺特化）|
| `CharredScar.lua` | 2KB | 焦土峽谷地圖 |
| `Caldera.lua` | 3.7KB | 火山口地圖生成 |

**StaticPredrawn.lua — 預繪製地圖系統**：

```lua
-- zone 定義中使用
generator = {
    map = {
        class = "mod.class.generator.map.StaticPredrawn",
        -- 指定多個替代佈局（隨機選一）
        maps = {
            "city/last-hope-1",
            "city/last-hope-2",
        },
    },
}
```

功能：
- 載入 `.lua` 靜態地圖文件（字元碼 → 實體）
- 支援 `subgen` 子生成器（在靜態地圖特定位置嵌入程序生成內容）
- 解析地圖標記（`@` = 玩家起始、`<` = 向上樓梯等）
- 支援多地圖替代版本（replayability）

---

## 6. mod/class/uiset/ — UI 主題系統

ToME 支援可切換的 UI 佈局主題（UISet）。

### 6.1 檔案結構

| 檔案 | 大小 | 說明 |
|------|------|------|
| `UISet.lua` | 1.7KB | UISet 基礎類別 |
| `Classic.lua` | 22KB | 傳統 UI 佈局 |
| `ClassicPlayerDisplay.lua` | 22KB | 傳統玩家資訊面板 |
| `Minimalist.lua` | 105KB（最大）| 極簡 UI 主題 |

### 6.2 UISet 架構

**UISet.lua** — 基礎介面：
- `UISet:init()` — 初始化 UI 元素
- `UISet:display()` — 每幀繪製回呼
- `UISet:resize(w, h)` — 視窗大小改變時重排
- `UISet:getTargetDisplay(actor)` — 取得目標資訊顯示格式

### 6.3 Classic UI（傳統佈局）

**Classic.lua** — 主佈局：
- 底部：訊息 log（1-5 行，可設定）
- 右側：玩家屬性面板
- 右上：小地圖
- 整合快捷鍵列（3 頁 × 12 格）

**ClassicPlayerDisplay.lua** — 玩家資訊面板：
- 生命/魔力/體力等資源條（顏色編碼）
- 當前效果圖示
- 裝備欄縮略圖
- 屬性數值（根據是否有效果而閃爍）

### 6.4 Minimalist UI（極簡佈局）

**Minimalist.lua**（105KB）— 最複雜的 UI 主題：

主要設計理念：
- **地圖最大化**：移除固定面板，只在需要時顯示 HUD
- **條件式顯示**：資源條只在資源不滿或最近變化時顯示
- **通知氣泡**：事件用飄動文字取代靜態 log
- **智慧縮放**：根據視窗大小自動調整所有元素

顯著功能：
- 自訂圖示庫（技能/效果圖示）
- 動畫資源條（血量下降時紅色脈衝）
- 拖曳式快捷鍵列
- 可收合的多個資訊浮動面板

---

## 7. 系統間關係總覽

```
角色創建流程：
  Birther.lua
    ├── data/birth/ (職業/種族描述符)
    ├── data/quests/start-*.lua (起始任務)
    └── Player:registerOnBirth() (後置 callback)

世界遭遇流程：
  世界地圖移動
    ├── data/general/encounters/ (遭遇定義)
    │   └── on_encounter() → WorldNPC + Chat.lua
    └── data/quests/lost-merchant.lua 等 (任務更新)

地城生成流程：
  Zone:generate()
    ├── mod/class/generator/map/ (地圖生成)
    │   └── StaticPredrawn / VaultLevel / etc
    ├── data/general/events/ (隨機事件疊加)
    ├── mod/class/generator/actor/ (NPC 生成)
    │   └── data/general/npcs/ (NPC 定義庫)
    └── data/general/objects/ (物品生成)

物品生成流程：
  Zone:makeEntityByName("object", id)
    ├── data/general/objects/*.lua (物品定義)
    ├── egos/ (詞綴疊加)
    └── random-artifacts.lua (隨機神器)

任務完成流程：
  NPC 對話 / 地形互動 / 擊殺事件
    ├── who:setQuestStatus(quest, status)
    ├── on_status_change() (獎勵/下一步)
    ├── data/lore/ (解鎖史料)
    └── mod/class/interface/WorldAchievements.lua (成就)

UI 渲染流程：
  Game:display()
    ├── mod/class/uiset/Classic.lua 或 Minimalist.lua
    │   └── ClassicPlayerDisplay.lua (玩家資訊)
    └── mod/dialogs/ (開啟時疊加)
```

---

> **相關文件**：
> - `game_detail.md` — 引擎啟動、profile thread、引擎核心 Lua、ToME 核心類別、AI 系統
> - `engine_detail.md` — 引擎 Lua 層詳細分析（`engine/` 目錄）
> - `lua_engine_detail.md` — Lua 引擎核心設計（OOP/Entity/Game Loop 等）
> - `overview.md` — 整體架構概覽
