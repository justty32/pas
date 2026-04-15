# 教學 15：自訂武器、裝備與種族貼圖

## 概述

TE4 的圖形渲染分兩個獨立系統：

1. **`image` 欄位** — 物品的庫存圖示及簡單 NPC 顯示
2. **`moddable_tile` 合成系統** — 玩家角色的多層圖像疊加（武器顯示在身上、護甲、頭盔等）

本教學說明這兩個系統的運作方式，以及如何建立自訂貼圖資源。

---

## 一、`image` 欄位（簡單圖示）

任何實體（Entity）都可以設定 `image` 欄位，這是它在地圖上和庫存畫面的圖示：

```lua
newEntity{
    name    = "Iron Sword",
    type    = "weapon", subtype = "sword",
    slot    = "MAINHAND",
    image   = "object/sword/iron_sword.png",  -- 相對於 /data/gfx/
}
```

若設定 `auto_image = true`，引擎會根據名稱自動產生路徑：
```lua
auto_image = true  -- 名稱 "Iron Sword" → image = "object/ironsword.png"
```
對獨特文物（unique）則會查找 `"object/artifact/ironsword.png"`。

**NPC 和非玩家 Actor** 的地圖圖示也用 `image` 欄位，不需要 `moddable_tile` 系統。

---

## 二、`moddable_tile` 合成系統

**玩家角色**在地圖上的外觀是多張 PNG 疊加而成的，每層代表身體部位或裝備槽位。這套系統由兩端共同驅動：

- **Actor 端**：`actor.moddable_tile` → 指向種族圖片資料夾
- **Object 端**：`object.moddable_tile` → 指向資料夾內的特定圖層

### 2.1 基本路徑邏輯

Actor 的 `moddable_tile` 欄位是種族/性別子資料夾名稱：

```lua
-- 在種族 birth descriptor 中設定
moddable_tile = "human_#sex#"   -- #sex# 在執行時替換為 "male" 或 "female"
moddable_tile = "dwarf_#sex#"
moddable_tile = "myrace_#sex#"
```

執行時 `updateModdableTile()` 計算出基底路徑：
```
base = "player/" .. moddable_tile:gsub("#sex#", sex) .. "/"
      → "player/human_female/"
```

所有裝備圖層的 PNG 都在這個資料夾下：
```
data/gfx/shockbolt/player/human_female/base_01.png
data/gfx/shockbolt/player/human_female/right_hand_04_01.png
data/gfx/shockbolt/player/human_female/upper_body_25.png
...
```

---

## 三、裝備的 `moddable_tile` 欄位

裝備物品有幾個 `moddable_tile` 相關欄位，控制它顯示在角色上的方式。

### 3.1 `moddable_tile`（主要圖層）

每種裝備類型的路徑格式不同：

| 裝備類型 | `moddable_tile` 格式 | `%s` 的值 |
|---------|---------------------|-----------|
| 武器（主手） | `"%s_hand_04_01"` | `"right"` |
| 武器（副手） | `"%s_hand_04_01"` | `"left"` |
| 盾牌 | `"%s_hand_10_01"` | `"right"` / `"left"` |
| 上身護甲 | `"upper_body_25"` | 無 %s |
| 下身護甲 | 透過 `moddable_tile2` | — |
| 披風 | `"cloak_%s_07"` | `"behind"` / `"shoulder"` / `"hood"` |
| 頭盔 | `"head_05"` | 無 %s |
| 手套 | `"hands_03"` | 無 %s |
| 靴子 | `"feet_04"` | 無 %s |

> **重點**：武器的 `%s` 代表「左手」或「右手」，因為同一物品可以裝備在主手（右）或副手（左）。

### 3.2 `moddable_tile2`（下身護甲圖層）

身體護甲（BODY slot）的第二圖層，用於渲染下半身：

```lua
-- 重型護甲同時設定上半身和下半身圖層
moddable_tile  = "upper_body_25"   -- 上半身
moddable_tile2 = "lower_body_16"   -- 下半身
```

### 3.3 `moddable_tile_back`（武器後層）

武器在「手背後」的圖層，渲染在手部圖層之前，用於讓武器柄看起來被握住：

```lua
moddable_tile_back = "special/%s_my_sword_back"
-- 檔案：player/human_female/special/right_my_sword_back.png
```

### 3.4 `moddable_tile_ornament`（裝飾圖層）

顯示在武器正面圖層之上的額外裝飾：

```lua
moddable_tile_ornament = "special/%s_my_sword_glow"
```

### 3.5 `moddable_tile_particle`（圖層粒子效果）

掛在武器圖層上的粒子效果：

```lua
moddable_tile_particle = {"fire_sword", {power=10}}
-- 等同於呼叫 Particles.new("fire_sword", 1, {power=10})
```

---

## 四、`resolvers.moddable_tile`（批量裝備快捷方式）

普通（非獨特）裝備通常用 `resolvers.moddable_tile` 隨機選取圖層，根據物品品質等級（`material_level` 1–5）：

```lua
-- 在物品定義中
newEntity{
    name        = "Short Sword",
    type        = "weapon", subtype = "sword",
    slot        = "MAINHAND",
    moddable_tile = resolvers.moddable_tile("sword"),
    -- material_level 1 → "%s_hand_04_01"
    -- material_level 3 → "%s_hand_04_03"
    -- material_level 5 → "%s_hand_04_05"
}
```

`resolvers.moddable_tile` 支援的 slot 名稱列表（在 `mod/resolvers.lua` 中定義）：

```
"sword", "2hsword", "dagger", "axe", "2haxe", "mace", "2hmace",
"bow", "sling", "staff", "trident", "whip", "shield", "mindstar",
"massive", "heavy", "light", "robe",
"helm", "wizard_hat", "leather_cap",
"gauntlets", "gloves",
"leather_boots", "heavy_boots",
"cloak",
"quiver", "shotbag", "gembag"
```

---

## 五、獨特裝備的自訂貼圖

獨特文物可以直接指定 `moddable_tile` 路徑：

```lua
newEntity{
    define_as = "DRAGON_SWORD",
    unique    = true,
    name      = "Dragon Sword",
    type      = "weapon", subtype = "sword",
    slot      = "MAINHAND",

    -- 庫存圖示（只需一張）
    image = "object/artifact/dragon_sword.png",

    -- 角色身上的圖層（每個種族性別組合都要有對應檔案！）
    moddable_tile = "special/%s_dragon_sword",
    --   主手：player/human_female/special/right_dragon_sword.png
    --   副手：player/human_female/special/left_dragon_sword.png
    --         player/human_male/special/right_dragon_sword.png
    --         player/dwarf_female/special/right_dragon_sword.png
    --         ...（每個種族）
}
```

> **注意**：`special/` 資料夾位於每個種族資料夾內，每個種族都要提供對應檔案，否則裝備在其他種族身上時圖層會消失。

引擎在物品初始化（`Object:init`）時會自動偵測是否存在 special 圖層：
```lua
-- 若 /data/gfx/shockbolt/player/human_female/special/right_dragon_sword.png 存在
-- 則自動設定 self.moddable_tile = "special/%s_dragon_sword"
```
因此，對於獨特文物，只要把 PNG 放到對的位置，引擎就會自動啟用。

---

## 六、完整圖層疊加順序

`updateModdableTile()` 依序建立 `add_mos` 列表，圖層由下而上：

```
[self.image]  ← 陰影底圖（base_shadow_01.png），作為主 image 欄位，不在 add_mos 中

add_mos[1]  ← 尾巴（moddable_tile_tail）
add_mos[2]  ← 背後飾物（moddable_tile_behinds，列表）
add_mos[3]  ← 披風後擺（CLOAK.moddable_tile:format("behind")）
add_mos[4]  ← Shader 光環（shader_auras）
add_mos[5]  ← 身體基底（moddable_tile_base 或 base_01.png）
             ← Hook: Actor:updateModdableTile:skin
add_mos[6]  ← 刺青（moddable_tile_tatoo）
add_mos[7]  ← 主手武器後層（MAINHAND.moddable_tile_back:format("right")）
add_mos[8]  ← 副手武器後層（OFFHAND.moddable_tile_back:format("left")）
add_mos[9]  ← 靴子（FEET.moddable_tile）
add_mos[10] ← 下身護甲/內衣（BODY.moddable_tile2 或 lower_body_01.png）
add_mos[11] ← 上身護甲/內衣（BODY.moddable_tile 或 upper_body_01.png）
add_mos[12] ← 披風肩部（CLOAK.moddable_tile:format("shoulder")）
add_mos[13] ← 披風兜帽（CLOAK.moddable_tile:format("hood")，需開啟設定）
add_mos[14] ← 頭髮（moddable_tile_hair）
add_mos[15] ← 面部特徵（moddable_tile_facial_features，列表）
add_mos[16] ← 頭盔（HEAD.moddable_tile）
             ← Hook: Actor:updateModdableTile:middle
add_mos[17] ← 角/冠（moddable_tile_horn）
add_mos[18] ← 手套（HANDS.moddable_tile）
add_mos[19] ← 箭袋（QUIVER.moddable_tile）
add_mos[20] ← 主手武器正面（MAINHAND.moddable_tile:format("right") + ornament）
add_mos[21] ← 副手武器正面（OFFHAND.moddable_tile:format("left") + ornament）
             ← Hook: Actor:updateModdableTile:front
```

---

## 七、建立自訂種族貼圖

### 7.1 資料夾結構

```
mod/data/gfx/shockbolt/player/
    lizardman_male/
        base_shadow_01.png   ← 必要：角色陰影剪影
        base_01.png          ← 必要：皮膚 01
        base_02.png          ← 選用：皮膚 02
        lower_body_01.png    ← 必要：預設下身內衣
        upper_body_01.png    ← 必要：預設上身內衣
        hair_01.png          ← 選用：頭髮
        head_01.png          ← 選用：支援頭盔 01
        hands_01.png         ← 選用：支援手套 01
        feet_01.png          ← 選用：支援靴子 01
        left_hand_04_01.png  ← 選用：支援單手劍（副手）
        right_hand_04_01.png ← 選用：支援單手劍（主手）
        cloak_behind_01.png  ← 選用：支援披風
        cloak_shoulder_01.png
        ...
    lizardman_female/
        [同上，但女性版本]
```

> **PNG 規格**：
> - 尺寸：64×64 像素（現代標準）
> - 格式：RGBA（需有透明通道）
> - 背景：完全透明（alpha = 0）
> - 所有圖層需使用相同畫布尺寸，像素對齊

### 7.2 最小可用貼圖集

只需 4 張 PNG，角色就能在地圖上顯示（無法顯示任何裝備）：

```
base_shadow_01.png  — 陰影（通常是橢圓形深色半透明底）
base_01.png         — 裸體身形 01
lower_body_01.png   — 預設下身內衣（防止裸體）
upper_body_01.png   — 預設上身內衣（防止裸體）
```

若要支援標準武器/護甲圖層，需新增對應的武器/護甲 PNG（以 `resolvers.moddable_tile` 所使用的檔案名稱為準）。

### 7.3 在 Birth Descriptor 中宣告種族

```lua
-- mod/data/birth/races/lizardman.lua
newBirthDescriptor{
    type = "race",
    name = "Lizardman",
    desc = { "蜥蜴人，爬蟲族裔，擅長潛行與毒術。" },
    descriptor_choices = {
        subrace = { Lizardman = "allow", __ALL__ = "disallow" },
    },
    moddable_attachement_spots = "race_lizardman",  -- 可選：自訂附著點
    copy = {
        type = "humanoid", subtype = "lizardman",
    },
}

newBirthDescriptor{
    type = "subrace",
    name = "Lizardman",
    desc = { "標準蜥蜴人。" },
    inc_stats = { str=2, con=2, dex=1, mag=-2 },
    copy = {
        moddable_tile      = "lizardman_#sex#",   -- 對應資料夾名稱
        moddable_tile_base = "base_01.png",       -- 預設皮膚
        -- 種族固有外觀（不受玩家更改）
        moddable_tile_horn = "horn_01",            -- 每個角色都有角
        life_rating        = 12,
    },
    cosmetic_options = {
        skin = {
            {name="綠色鱗片",  file="base_01"},
            {name="藍色鱗片",  file="base_02"},
            {name="黑色鱗片",  file="base_03"},
        },
        hairs = {   -- 蜥蜴人可以有羽冠，用 hair 槽位
            {name="無", file="hair_none"},
            {name="紅羽冠", file="hair_crest_red_01"},
        },
    },
}
```

### 7.4 角色建立時的流程

Birth 結束後，`newBirthDescriptor.copy` 中的欄位會複製到 Actor，然後：

1. 玩家在 birth 畫面選擇外觀（skin、hair 等）
2. 所選值存入 `actor.moddable_tile_base`、`actor.moddable_tile_hair` 等
3. 每次裝備/卸下裝備時呼叫 `actor:updateModdableTile()` 重建 `add_mos`

---

## 八、`add_mos` 直接使用（非玩家角色）

不使用 `moddable_tile` 系統的 NPC，可以直接在定義中設定 `add_mos` 做多層疊加：

```lua
newEntity{
    define_as = "BOSS_DRAGON",
    name      = "Dragon Boss",
    image     = "npc/dragon/dragon_base.png",
    add_mos   = {
        {image = "npc/dragon/dragon_wings.png",  auto_tall=1},
        {image = "npc/dragon/dragon_crown.png",  auto_tall=1},
    },
}
```

`auto_tall=1` 表示這個圖層使用 2 格高度的渲染（佔據上方格子），用於顯示高大的生物。

也可以在 `add_mos` 項目中加粒子：
```lua
add_mos = {
    {
        image         = "npc/demon/demon_body.png",
        particle      = "fire_aura",
        particle_args = {power=5},
        auto_tall     = 1,
    },
}
```

---

## 九、完整範例：自訂獨特劍 + 新種族

### 9.1 目錄結構

```
mod/
├── data/
│   ├── birth/
│   │   └── races/
│   │       └── lizardman.lua           ← 種族 birth descriptor
│   ├── gfx/
│   │   └── shockbolt/
│   │       └── player/
│   │           ├── lizardman_male/
│   │           │   ├── base_shadow_01.png
│   │           │   ├── base_01.png
│   │           │   ├── base_02.png
│   │           │   ├── lower_body_01.png
│   │           │   ├── upper_body_01.png
│   │           │   ├── horn_01.png
│   │           │   └── special/
│   │           │       ├── right_venom_fang.png   ← 獨特劍主手
│   │           │       └── left_venom_fang.png    ← 獨特劍副手
│   │           └── human_female/
│   │               └── special/
│   │                   ├── right_venom_fang.png   ← 人類也要有
│   │                   └── left_venom_fang.png
│   └── general/
│       └── objects/
│           └── venom_fang.lua           ← 武器定義
```

### 9.2 武器定義

```lua
-- mod/data/general/objects/venom_fang.lua
newEntity{
    define_as = "VENOM_FANG",
    unique    = true,
    name      = "Venom Fang",
    type      = "weapon", subtype = "sword",
    slot      = "MAINHAND",
    material_level = 3,

    -- 庫存圖示（自動 auto_image = true 也可用）
    image = "object/artifact/venom_fang.png",

    -- 角色上的圖層
    -- 引擎初始化時會自動偵測 special/ 資料夾並設定此欄位
    -- 也可以手動明確設定：
    moddable_tile = "special/%s_venom_fang",

    combat = {
        dam = 30, range = 1.4,
        damtype = DamageType.NATURE,
    },
    -- 加上武器粒子效果（見教學 14）
    moddable_tile_particle = {"poison_weapon", {power=3}},
}
```

### 9.3 種族定義

```lua
-- mod/data/birth/races/lizardman.lua
newBirthDescriptor{
    type = "race",
    name = "Lizardman",
    desc = { "古老的蜥蜴人族裔，居於沼澤深處。" },
    descriptor_choices = {
        subrace = { Lizardman = "allow", __ALL__ = "disallow" },
    },
    copy = {
        type = "humanoid", subtype = "lizardman",
        faction = "enemies",
    },
}

newBirthDescriptor{
    type = "subrace",
    name = "Lizardman",
    desc = { "天生具有毒性與快速再生能力的爬蟲種族。" },
    inc_stats = { str=2, con=2, dex=1, mag=-2, wil=-1 },
    talents_types = { ["race/lizardman"]={true, 0} },
    copy = {
        moddable_tile      = "lizardman_#sex#",
        moddable_tile_base = "base_01.png",
        moddable_tile_horn = "horn_01",   -- 所有蜥蜴人都有角，固定圖層
        life_rating = 12,
        random_name_def = "lizardman_#sex#",
    },
    cosmetic_options = {
        skin = {
            {name="綠色鱗片", file="base_01"},
            {name="藍色鱗片", file="base_02"},
        },
    },
}
```

---

## 十、常見問題排查

| 現象 | 原因 | 解法 |
|------|------|------|
| 裝備在角色身上不顯示 | 對應種族資料夾缺少 PNG | 為每個 `moddable_tile` 種族都新增相同命名的 PNG |
| 角色完全不顯示 | 缺少 `base_shadow_01.png` 或 `base_01.png` | 確認最小必要圖層都存在 |
| 武器方向顛倒 | `%s` 格式化寫錯 | 主手用 `right`，副手用 `left` |
| 護甲只顯示上半身 | 缺少 `moddable_tile2` | 身體護甲需設定 `moddable_tile2` 或提供 `lower_body_01.png` 預設圖 |
| 獨特武器不顯示 | `special/` 路徑不存在 | 檢查 `fs.exists("/data/gfx/shockbolt/player/human_female/special/right_XXXX.png")` |

---

## 重點總結

- **`image`** — 只控制庫存圖示和簡單實體顯示
- **`moddable_tile`（Actor）** → 指向種族圖片資料夾，如 `"lizardman_#sex#"`
- **`moddable_tile`（Object）** → 指定裝備在角色身上的圖層名稱，武器用 `%s` 代表左/右手
- **`resolvers.moddable_tile("sword")`** → 按品質等級選一個預設劍圖層
- **圖層順序**：陰影 → 尾巴 → 披風後擺 → 光環 → 身體 → 刺青 → 武器後層 → 靴子 → 下身 → 上身 → 披風肩 → 頭髮 → 臉部 → 頭盔 → 角 → 手套 → 箭袋 → 武器前層
- **最小種族貼圖集**：`base_shadow_01.png`、`base_01.png`、`lower_body_01.png`、`upper_body_01.png`
- **獨特裝備**：每個種族資料夾的 `special/` 子目錄都需要有對應 PNG
