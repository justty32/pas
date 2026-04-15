# 教學 07：為 ToME 新增職業與技能樹（進階 Addon）

> **目標**：深入 ToME 的職業系統，製作一個完整的新職業「血術師（Sanguinist）」：自訂技能類型（TalentType）、五個技能（含被動、施放、持續）、依賴鏈、熟練度系統、Birther 整合、起始裝備，以及種族相容性設定。
>
> **前置條件**：閱讀並理解教學 06（Addon 基礎）。本教學是教學 06「暗影刺客」的直接延伸，聚焦在教學 06 沒有詳細說明的進階細節。

---

## 目錄

1. [TalentType 深度解析](#1-talenttype-深度解析)
2. [newTalent 所有選項](#2-newtalent-所有選項)
3. [require：前置條件完整規格](#3-require前置條件完整規格)
4. [技能依賴鏈範例（五個技能）](#4-技能依賴鏈範例)
5. [Birther subclass 深度解析](#5-birther-subclass-深度解析)
6. [descriptor_choices：種族與職業相容性](#6-descriptor_choices-種族與職業相容性)
7. [resolvers.equipbirth 與 resolvers.inventorybirth](#7-resolversequipbirth-與-resolversinventorybirth)
8. [熟練度系統（Mastery）](#8-熟練度系統mastery)
9. [完整 Addon 實作](#9-完整-addon-實作)
10. [測試與除錯技巧](#10-測試與除錯技巧)
11. [常見錯誤排查](#11-常見錯誤排查)

---

## 1. TalentType 深度解析

`newTalentType{}` 宣告一個技能分類（技能樹）。ToME 的技能以 `"category/subcategory"` 格式組織。

### 1.1 完整欄位說明

```lua
newTalentType{
    -- ── 必填 ──────────────────────────────────────────────────
    type        = "blood/sanguination",   -- 識別符：category/sub
    name        = "血術精通",             -- 顯示名稱（技能樹標題）

    -- ── 常用選項 ───────────────────────────────────────────────
    description = "操控血液的古老力量。", -- 描述（滑鼠懸停時顯示）

    -- generic = true：「通用」技能樹
    --   → 在 Birther 的 talents_types 表格中，false/true 第一個元素用 false 表示未解鎖
    --   → 通用技能點數（unused_generics）消費，而非職業點數（unused_talents）
    --   → 不同的成長曲線（通常較通用技能較弱）
    -- generic = false 或不設（預設）：職業技能樹，消費 unused_talents
    generic     = false,

    -- allow_random = true：允許此技能樹的技能被隨機 Boss 隨機習得
    -- allow_random = false（預設）：此技能樹不會隨機出現在 Boss 身上
    allow_random = true,

    -- not_on_random_boss = true：即使 allow_random=true，也不讓技能樹本身
    --   出現在隨機 Boss 的技能類型列表中（個別技能仍可能被選中）
    not_on_random_boss = true,

    -- min_require：此技能樹的技能要求最少的屬性值才能加點
    -- 實際上這個欄位控制的是 Birther 展示時是否顯示屬性需求
    -- 技能的實際需求在 newTalent 的 require 中定義
    min_require = { stat = { mag=20 } },

    -- on_mastery_change：當玩家改變此技能樹熟練度時呼叫
    on_mastery_change = function(self, mastery, tt)
        -- self = Actor, mastery = 新熟練度值, tt = 技能樹 type 字串
        -- 可以在這裡更新相依屬性
    end,
}
```

### 1.2 category 與 subcategory 的關係

```
type = "blood/sanguination"
         ↑         ↑
    category    subcategory

category = "blood"          ← 大類別（如 technique, cunning, spell, gift）
subcategory = "sanguination" ← 小類別（技能樹名稱）
```

引擎自動從 type 提取 `category`（第一個 `/` 前）。同一個 category 下的技能樹，在技能 UI 中會分組顯示。

---

## 2. newTalent 所有選項

```lua
newTalent{
    -- ── 必填 ──────────────────────────────────────────────────
    name    = "血液汲取",
    type    = {"blood/sanguination", 1},  -- {type, 在此樹中的位置（1~4）}
    -- 位置 1：樹中第一個技能，無前置需求
    -- 位置 2：需要先習得 1 個該樹技能才能學習
    -- 位置 3：需要 2 個，以此類推

    -- ── 模式（三選一）───────────────────────────────────────────
    mode    = "activated",    -- 主動技能：按鍵後觸發，消耗能量
    -- mode = "sustained",   -- 持續技能：開/關切換，啟動消耗資源，每回合持續消耗
    -- mode = "passive",     -- 被動技能：習得後永久生效，沒有使用動作

    -- ── 技能點需求 ────────────────────────────────────────────
    points  = 5,              -- 最大加點數（1~5，ToME 標準是 5）
    -- 不設預設為 1（只能加到 1 點，通常用於特殊技能）

    -- ── 冷卻與消耗 ────────────────────────────────────────────
    cooldown = 8,             -- 冷卻回合數（mode="activated" 才有意義）
    mana     = 20,            -- 施展時消耗的魔力（需要 ActorResource 定義 mana）
    -- 其他資源：vim、psi、positive、negative、hate、stamina...

    -- 持續技能的資源定義
    sustain_mana = 10,        -- 啟動時消耗（mode="sustained"）
    -- sustain_slots = 1,     -- 此技能最多同時持續幾個

    -- ── 前置需求（見第 3 節詳細說明）─────────────────────────
    require = { stat={mag=function(level) return 20 + level * 8 end} },

    -- ── 技能資訊（滑鼠懸停顯示）────────────────────────────────
    -- info 是函數，self=Actor、t=talent 定義表格
    -- 回傳字串（顯示在技能描述框）
    info    = function(self, t)
        local damage = self:getTalentLevel(t) * 15
        return ("汲取目標的血液，造成 %d 點傷害並回復等量生命。"):format(damage)
    end,

    -- ── 使用效果（activated 模式）────────────────────────────
    action  = function(self, t)
        -- 選擇目標
        local tg = {type="bolt", range=self:getTalentRange(t)}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return nil end

        -- 計算傷害
        local dam = self:getTalentLevel(t) * 15

        -- 造成傷害（DamageType.project）
        self:project(tg, x, y, engine.DamageType.NATURE, dam)

        -- 回復玩家生命
        self:heal(dam * 0.5, target)

        game.logSeen(self, "%s 汲取了 %s 的生命力！",
            self:getName():capitalize(), target:getName():capitalize())

        return true  -- true = 使用成功，消耗能量和冷卻
    end,

    -- 持續技能的回調
    activate   = function(self, t)  -- 啟動時呼叫（mode="sustained"）
        -- 回傳一個 ret 表格，存在 self.sustain_talents[t.id] 中
        return { id = self:addTemporaryValue("combat_dam", 10) }
    end,
    deactivate = function(self, t, ret)  -- 關閉時呼叫
        self:removeTemporaryValue("combat_dam", ret.id)
        return true
    end,

    -- 被動技能的回調
    passives   = function(self, t, p)  -- mode="passive"，每次學習/升級時呼叫
        self:talentTemporaryValue(p, "combat_physcrit", self:getTalentLevel(t) * 2)
    end,

    -- ── 其他選項 ───────────────────────────────────────────────
    range   = function(self, t) return math.floor(self:getTalentLevel(t) * 1.5 + 3) end,
    radius  = function(self, t) return 2 end,   -- 法術範圍（球形/錐形）
    target  = function(self, t) return {type="bolt", range=self:getTalentRange(t)} end,

    -- no_energy = true：使用不消耗回合行動（瞬發）
    no_energy = true,

    -- on_pre_use：使用前的條件檢查（return false 阻止使用）
    on_pre_use = function(self, t, silent)
        if not self:hasEffect(self.EFF_BLEEDING) then
            if not silent then game.logPlayer(self, "你必須處於流血狀態才能使用此技能！") end
            return false
        end
        return true
    end,
}
```

---

## 3. require：前置條件完整規格

`require` 控制玩家何時能加點到這個技能。支援靜態值和動態函數：

```lua
require = {
    -- 屬性要求：每個等級都可以有不同要求
    stat = {
        mag = function(level) return 12 + level * 5 end,
        -- level 1：需要 mag 17
        -- level 2：需要 mag 22，以此類推
        -- 也可以是靜態數字：mag = 20
    },

    -- 等級要求
    level = function(level) return -5 + level * 4 end,
    -- level 1：-5 + 4 = 角色 -1 級才能加（實際上無限制）
    -- level 3：-5 + 12 = 角色 7 級以上

    -- 前置技能要求（最常用的依賴鏈機制）
    talent = {
        -- 格式1：{技能ID, 需要的等級}
        {self.T_BLOOD_DRAIN, 2},   -- 需要「血液汲取」學到第 2 級

        -- 格式2：只要學過（任意等級）
        self.T_BLOOD_MASTERY,

        -- 格式3：{技能ID, false} 表示「不能學過這個技能」（互斥）
        -- {self.T_HOLY_LIGHT, false},
    },

    -- 出身需求（此職業才能學）
    birth_descriptors = {
        {"subclass", "Sanguinist"},  -- 只有血術師才能學此技能
    },

    -- 特殊條件（自訂邏輯）
    special = {
        desc = "必須吸收過至少一個敵人的生命",
        fct  = function(self, t, offset)
            return (self.blood_absorbed or 0) >= 1
        end,
    },
}
```

**技能依賴鏈示意圖**：

```
血術精通（被動）  ← 位置 1，無前置
    ↓ 需要 1 點
血液汲取（主動）  ← 位置 2，require.talent = {T_BLOOD_MASTERY}
    ↓ 需要 2 點
血盾屏護（持續）  ← 位置 3，require.talent = {T_BLOOD_DRAIN, 2}
    ↓ 需要 2 點
血液爆發（主動）  ← 位置 4（最強技能），require.talent = {T_BLOOD_SHIELD, 2}
```

---

## 4. 技能依賴鏈範例

這裡展示完整的「血術」技能樹（五個技能，一條清晰的依賴鏈）：

```lua
-- game/addons/sanguinist/data/talents/blood.lua

-- ═══════════════════════════════════════════════════
-- 技能樹定義
-- ═══════════════════════════════════════════════════
newTalentType{
    type        = "blood/sanguination",
    name        = "血術精通",
    description = "透過操控血液的力量汲取敵人的生命，或以血為盾、以血為刃。",
    allow_random = false,   -- 不讓隨機 Boss 用這些技能（保持職業特色）
}

-- ── 技能 1：血術精通（被動） ─────────────────────────────
newTalent{
    name   = "血術精通",
    type   = {"blood/sanguination", 1},  -- 樹中第一個
    mode   = "passive",
    points = 5,
    -- 無前置需求（樹的第一個技能）
    passives = function(self, t, p)
        -- 每點增加 3% 生命汲取效率
        self:talentTemporaryValue(p, "blood_drain_bonus",
            self:getTalentLevel(t) * 0.03)
    end,
    info = function(self, t)
        return ("深化你對血術的理解。\n"..
               "每點提升 3%% 生命汲取效果（當前：%.0f%%）。"):format(
               (self:getTalentLevel(t) * 3))
    end,
}

-- ── 技能 2：血液汲取（主動） ─────────────────────────────
newTalent{
    name     = "血液汲取",
    type     = {"blood/sanguination", 2},  -- 需要先學 1 個技能
    mode     = "activated",
    points   = 5,
    cooldown = function(self, t)
        return math.max(3, 8 - self:getTalentLevel(t))
    end,
    mana     = 15,
    range    = function(self, t)
        return math.floor(3 + self:getTalentLevel(t) * 0.8)
    end,
    require  = {
        stat  = { mag = function(level) return 10 + level * 4 end },
        -- 依賴技能1
        talent = { {ActorTalents.T_BLOOD_MASTERY, 1} },
    },
    action = function(self, t)
        local tg = {type="bolt", range=self:getTalentRange(t)}
        local x, y, target = self:getTarget(tg)
        if not x or not target then return nil end

        local dam = self:combatSpellpower() * (0.5 + self:getTalentLevel(t) * 0.3)
        -- 汲取加成來自血術精通被動
        local bonus = 1 + (self.blood_drain_bonus or 0)
        dam = dam * bonus

        self:project(tg, x, y, DamageType.MIND, dam)

        -- 回復自身生命（50% 傷害轉化）
        if not target.dead then
            self:heal(dam * 0.5, target)
        end
        return true
    end,
    info = function(self, t)
        local dam = self:combatSpellpower() * (0.5 + self:getTalentLevel(t) * 0.3)
        return ("向目標射出血液汲取射線，造成 %.0f 精神傷害並回復 50%% 作為生命值。\n"..
               "冷卻：%d 回合 | 射程：%d格"):format(
               dam, self:getTalentCooldown(t), self:getTalentRange(t))
    end,
}

-- ── 技能 3：血盾屏護（持續） ─────────────────────────────
newTalent{
    name           = "血盾屏護",
    type           = {"blood/sanguination", 3},
    mode           = "sustained",
    points         = 5,
    sustain_mana   = 20,
    -- 每回合持續消耗（若使用 ActorResource）
    -- sustain_drain = {mana = 2},
    require = {
        stat  = { mag = function(level) return 18 + level * 5 end },
        talent = { {ActorTalents.T_BLOOD_DRAIN, 2} },  -- 需要血液汲取 2 點
    },
    activate = function(self, t)
        -- 啟動時給予護甲和生命回復
        local armor = math.floor(self:getTalentLevel(t) * 4)
        local regen = self:getTalentLevel(t) * 0.5
        local ret = {}
        ret.armor = self:addTemporaryValue("combat_armor", armor)
        ret.regen = self:addTemporaryValue("life_regen", regen)
        return ret
    end,
    deactivate = function(self, t, ret)
        self:removeTemporaryValue("combat_armor", ret.armor)
        self:removeTemporaryValue("life_regen", ret.regen)
        return true
    end,
    info = function(self, t)
        local armor = math.floor(self:getTalentLevel(t) * 4)
        local regen = self:getTalentLevel(t) * 0.5
        return ("以血液薄膜包裹自身，提供 %d 點護甲值和每回合 %.1f 點生命回復。"):format(
               armor, regen)
    end,
}

-- ── 技能 4：血液爆發（主動） ─────────────────────────────
newTalent{
    name     = "血液爆發",
    type     = {"blood/sanguination", 4},  -- 需要 3 個前置
    mode     = "activated",
    points   = 5,
    cooldown = 14,
    mana     = 40,
    radius   = function(self, t) return 2 + math.floor(self:getTalentLevel(t) / 2) end,
    require = {
        stat  = { mag = function(level) return 28 + level * 6 end },
        talent = { {ActorTalents.T_BLOOD_SHIELD, 2} },  -- 需要血盾 2 點
    },
    action = function(self, t)
        -- 以自身為中心的血液爆炸（消耗自己的生命）
        local cost = self.max_life * 0.1  -- 消耗 10% 最大生命值
        if self.life <= cost then
            game.logPlayer(self, "你的生命值不足以釋放血液爆發！")
            return nil
        end
        self:takeHit(cost, self)  -- 自我傷害

        local dam = self:combatSpellpower() * (1 + self:getTalentLevel(t) * 0.5)
        local tg = {type="ball", radius=self:getTalentRadius(t), selffire=false}
        self:project(tg, self.x, self.y, DamageType.MIND, dam)

        game.logSeen(self, "%s 引爆自身血液，對周圍造成 %.0f 傷害！",
            self:getName():capitalize(), dam)
        return true
    end,
    info = function(self, t)
        local dam = self:combatSpellpower() * (1 + self:getTalentLevel(t) * 0.5)
        return ("引爆自身血液，消耗 10%% 最大生命值，\n"..
               "對 %d 格範圍內的敵人造成 %.0f 精神傷害。"):format(
               self:getTalentRadius(t), dam)
    end,
}
```

---

## 5. Birther subclass 深度解析

`newBirthDescriptor` 的 `subclass` 類型定義職業在角色創建時的所有屬性：

```lua
-- game/addons/sanguinist/data/birth/classes/sanguinist.lua

-- 大類別（class）：讓血術師在職業選單中有自己的分類
-- 這個定義控制「選職業大類時看到什麼」
newBirthDescriptor{
    type = "class",
    name = "血術師",   -- 大類別名稱
    desc = {
        "血術師以血液為媒介施展古老的禁忌魔法，",
        "能汲取敵人的生命力，以鮮血鑄造護盾。",
    },
    -- descriptor_choices：限制這個大類別下可選的小類別
    descriptor_choices = {
        subclass = {
            __ALL__ = "disallow",
            ["Sanguinist"] = "allow",
        },
    },
    copy = {
        -- 大類別共用屬性（所有血術師子職業都繼承）
        max_life = 90,
    },
}

-- ════════════════════════════════════════════════════
-- 子職業（subclass）：核心定義
-- ════════════════════════════════════════════════════
newBirthDescriptor{
    type = "subclass",
    name = "Sanguinist",    -- 職業名稱（英文，也是 ActorTalents.T_XXX 的查找鍵）
    desc = {
        "血術師是掌握禁忌血液魔法的法師，",
        "他們以血液為燃料，汲取敵人的生命以延續自身。",
        "血術師的防禦能力極強，但需要謹慎管理生命值。",
        "",
        "#GOLD#重要屬性：",
        "#LIGHT_BLUE# * 魔力（Magic）：影響血術技能的傷害和效果",
        "#LIGHT_BLUE# * 體質（Constitution）：影響最大生命值",
        "#GOLD#每級生命：#LIGHT_BLUE# +2",
    },

    -- 加點的力量來源（用於與物品的相容性判斷）
    -- technique = 肉體技能, arcane = 奧術, nature = 自然, psionic = 靈能
    power_source = {arcane=true},

    -- 起始屬性加點
    stats = {
        mag = 5,    -- 魔力 +5
        con = 2,    -- 體質 +2
        str = -1,   -- 力量 -1（血術師不擅長近戰）
    },

    -- 技能樹訪問權（talents_types）
    -- 格式：["type/subtype"] = {已解鎖, 初始熟練度}
    -- true = 角色創建時就能見到此技能樹
    -- false = 未解鎖（需要特殊條件才能訪問）
    -- 熟練度：0.3 = 起始技能消耗效率 1.3 倍（基礎是 1.0）
    talents_types = {
        -- 血術師專屬技能樹
        ["blood/sanguination"]   = {true,  0.3},  -- 主技能樹，已解鎖

        -- 通用技能樹（大多數職業都有）
        ["spell/arcane"]         = {false, 0.2},  -- 奧術（未解鎖，可花點解鎖）
        ["cunning/survival"]     = {true,  0.2},  -- 求生技巧
        ["technique/combat-training"] = {false, 0.0},  -- 戰鬥訓練（弱）
    },

    -- 起始技能（從技能定義中直接習得）
    -- 使用 ActorTalents 上的常數（在 data/talents/blood.lua 載入後自動定義）
    talents = {
        [ActorTalents.T_BLOOD_MASTERY] = 1,  -- 血術精通第 1 點
        [ActorTalents.T_BLOOD_DRAIN]   = 1,  -- 血液汲取第 1 點
    },

    -- 技能樹熟練度（額外加成，在 talents_types 的基礎熟練度之上）
    -- 通常在 copy 中用 resolvers 設定
    -- （見第 8 節）

    -- copy：會被「複製貼上」到角色上的屬性
    -- 這裡放的是複雜的 resolver 和特殊屬性
    copy = {
        -- 每級生命加成
        life_rating = 12,    -- 比 warrior（14）少，比 mage（8）多

        -- 每級魔力回復
        mana_regen = 0.5,

        -- 起始魔力
        max_mana = 100,

        -- 不受鎧甲施法懲罰（血術師用布甲）
        -- combat_spellpower 的計算（由 ToME 的 Armor 系統管理）

        -- 起始裝備（見第 7 節詳細說明）
        equipment = resolvers.equipbirth{ id=true,
            -- 一件布甲（輕型防護）
            {type="armor", subtype="cloth", name="linen robe",
             autoreq=true, ego_chance=-1000},
            -- 一根木杖
            {type="weapon", subtype="staff", name="elm staff",
             autoreq=true, ego_chance=-1000},
        },

        -- 起始揹包物品（不裝備，直接放入揹包）
        inventory = resolvers.inventorybirth{ id=true,
            -- 3 瓶治癒藥水（使用 define_as 精確指定）
            {type="potion", subtype="potion", defined="POTION_REGENERATION",
             ego_chance=-1000},
            {type="potion", subtype="potion", defined="POTION_REGENERATION",
             ego_chance=-1000},
        },

        -- 角色外觀（裝備模型貼圖）
        moddable_attachement_spots = "mage",
    },
}
```

---

## 6. descriptor_choices：種族與職業相容性

`descriptor_choices` 控制「選擇 A 後，B 的選項如何被過濾」。最常見的是種族-職業相容性：

```lua
-- 在 subclass 定義中設定哪些種族可以選擇此職業：
descriptor_choices = {
    -- 過濾 "race" 類型的描述符
    race = {
        -- 允許所有種族（不設限制）
        __ALL__ = "allow",
    },
    -- 或者只允許特定種族：
    -- race = {
    --     __ALL__  = "disallow",
    --     ["Human"] = "allow",
    --     ["Elf"]   = "allow",
    -- },
}

-- 在 race 定義中也可以設定哪些職業兼容：
-- （位於 data/birth/races/xxx.lua）
newBirthDescriptor{
    type = "race",
    name = "Human",
    descriptor_choices = {
        subclass = {
            -- 允許玩家選擇血術師
            ["Sanguinist"] = "allow",
            -- 其他職業的 allow/disallow 由各職業的 subclass 定義控制
        },
    },
    -- ...
}
```

**相容性邏輯**：種族和職業的 `descriptor_choices` 取**交集**。只有兩邊都 `"allow"` 的組合才能被玩家選擇。

---

## 7. resolvers.equipbirth 與 resolvers.inventorybirth

這兩個 resolver 是 ToME 特有的，**專門用於角色創建時**的裝備初始化：

```lua
-- equipbirth：嘗試自動裝備到適當槽位
equipment = resolvers.equipbirth{ id=true,   -- id=true：物品自動鑑定
    -- 每個表格是一個物品篩選條件
    {
        type = "weapon", subtype="staff",
        name = "elm staff",      -- 精確名稱匹配
        autoreq = true,          -- 自動提升屬性/等級以滿足需求（角色創建常用）
        ego_chance = -1000,      -- 不生成附魔（確保是基礎版）
        ignore_material_restriction = true,  -- 忽略材料等級限制（equipbirth 默認啟用）
    },
    -- 也可以用更寬鬆的條件（讓系統隨機選）
    {
        type = "armor",
        subtype = "cloth",
        autoreq = true,
        ego_chance = -1000,
    },
},

-- inventorybirth：放入揹包（不裝備）
inventory = resolvers.inventorybirth{ id=true,
    {type="potion", subtype="potion"},  -- 任意藥水
    {type="potion", defined="POTION_REGENERATION"},  -- 精確指定物品 define_as
},
```

**`resolvers.equip` vs `resolvers.equipbirth` 的差異**：

| 欄位 | equip（NPC 用） | equipbirth（出生用） |
|------|----------------|---------------------|
| 材料限制 | 遵守 zone 的 material_level | 忽略（可以在任何材料等級） |
| 使用場景 | NPC 的 resolvers.equip{} | 角色創建的 copy.equipment |
| autoreq | 不常用 | 推薦使用，確保能穿上 |

---

## 8. 熟練度系統（Mastery）

熟練度影響技能的效果上限。`getTalentMastery()` 在技能公式中常見：

```lua
-- 技能內部用 getTalentMastery 來縮放效果：
local mastery = self:getTalentTypeMastery("blood/sanguination")
-- 返回值：0.3（初始值）到 1.0+（用點解鎖後）

-- 實際應用範例：
local dam = base_dam * mastery
```

**設定初始熟練度的方式**：

```lua
-- 方式 1：在 talents_types 中設定（推薦）
talents_types = {
    ["blood/sanguination"] = {true, 0.3},  -- 0.3 = 基礎熟練度加成
    -- 實際熟練度 = 1.0 + 0.3 = 1.3（因為引擎以 1.0 為基礎）
},

-- 方式 2：在 copy 中用 resolvers 設定（用於更精細控制）
copy = {
    resolvers.talents_types_mastery{
        ["blood/sanguination"] = 0.4,  -- 覆蓋 talents_types 中的值
    },
},
```

**讓玩家提升熟練度**：在技能 UI 中按 `+` 鍵投入「熟練度點數」（mastery point），需要在 Birther 中設定玩家有多少點可以分配。ToME 標準是每 10 級一個熟練度點。

---

## 9. 完整 Addon 實作

### 9.1 目錄結構

```
game/addons/sanguinist/
├── init.lua
├── hooks/
│   └── load.lua              ← 載入技能定義和職業
└── data/
    ├── birth/
    │   └── classes/
    │       └── sanguinist.lua ← newBirthDescriptor（見第 5 節）
    └── talents/
        └── blood.lua          ← newTalentType + newTalent（見第 4 節）
```

### 9.2 init.lua

```lua
-- game/addons/sanguinist/init.lua

long_name   = "Sanguinist Class"
short_name  = "sanguinist"
for_module  = "tome"
version     = {1, 0, 0}
author      = {"你的名字", "your@email.com"}
description = [[
血術師職業 Addon：以血為代價，以血換力。
]]

hooks     = true   -- 使用 hooks/load.lua
data      = true   -- 有 data/ 目錄
```

### 9.3 hooks/load.lua

```lua
-- game/addons/sanguinist/hooks/load.lua

local ActorTalents = require "engine.interface.ActorTalents"

-- 在 ToME 的 load.lua 末尾執行後，載入我們的技能定義
hook{"ToME:load", function(info)
    -- 載入技能類型和技能定義
    ActorTalents:loadDefinition("/data/talents/blood.lua")

    -- 載入職業出生描述符
    local Birther = require "engine.Birther"
    Birther:loadDefinition("/data/birth/classes/sanguinist.lua")
end}
```

### 9.4 data/talents/blood.lua

（已在第 4 節展示完整程式碼）

### 9.5 data/birth/classes/sanguinist.lua

（已在第 5 節展示完整程式碼）

---

## 10. 測試與除錯技巧

### 10.1 在角色創建中快速測試

啟動遊戲進入角色創建，如果職業不出現：

1. 確認 `init.lua` 有 `hooks = true`
2. 確認 `hooks/load.lua` 的 hook 名稱是 `"ToME:load"`（不是 `"ToME:run"`）
3. 確認 `Birther:loadDefinition` 的路徑正確（`/data/birth/classes/sanguinist.lua`，使用虛擬路徑）

### 10.2 技能不出現在技能 UI

```lua
-- 在遊戲中進入 debug 模式，呼叫以下查詢：
-- （在 Lua console 中，按 F12 或使用 ~ 鍵）
print(ActorTalents.talents_types_def["blood/sanguination"])
-- 應該顯示技能類型的定義表格
-- 如果是 nil，表示 loadDefinition 沒有成功執行
```

### 10.3 技能效果驗證

建立一個測試角色，在 debug 模式下手動設定技能等級：

```lua
-- 在 Lua console：
game.player:learnTalent(game.player.T_BLOOD_DRAIN, true, 5)
game.player:setTalentTypeMastery("blood/sanguination", 1.5)
```

### 10.4 require 問題

如果玩家無法加點（技能顯示「需求不足」），在技能的 `require` 中加入 print：

```lua
require = {
    stat = { mag = function(level)
        local v = 10 + level * 4
        print("[DEBUG] mag require for level", level, ":", v, "current:", game and game.player and game.player:getStat("mag"))
        return v
    end },
},
```

---

## 11. 常見錯誤排查

### 錯誤：`talent already exists with id T_BLOOD_MASTERY`

**原因**：`loadDefinition` 被呼叫了兩次（重複載入）。

**解法**：在 `hooks/load.lua` 中只呼叫一次。如果你有多個 hook 可能重複觸發，用 guard：

```lua
hook{"ToME:load", function(info)
    if _G.__sanguinist_loaded then return end
    _G.__sanguinist_loaded = true
    ActorTalents:loadDefinition("/data/talents/blood.lua")
end}
```

---

### 錯誤：`blood/sanguination` 職業技能樹顯示為通用（generic）

**原因**：`newTalentType` 沒有設 `generic = false`（或省略），但 `talents_types` 中的設定與之矛盾。

**解法**：確認 `newTalentType` 中沒有 `generic = true`，且 `talents_types` 的第一個元素（`true`/`false`）是已解鎖狀態，不是 generic 標誌。

---

### 錯誤：`resolvers.equipbirth` 找不到物品

**原因**：指定的物品名稱（`name = "elm staff"`）在當前 Zone 的材料等級下找不到，或拼寫不符。

**解法**：
- 加入 `ignore_material_restriction = true`（equipbirth 預設已加入）
- 用 `defined = "ELM_STAFF"`（對應 `define_as`）精確指定，比名稱更可靠
- 在 Lua console 確認物品存在：`print(game.zone.object_list)` 或搜尋物品清單

---

### 錯誤：職業不顯示在特定種族的選項中

**原因**：種族的 `descriptor_choices.subclass` 沒有 allow 這個職業，或職業的 `descriptor_choices.race` 屏蔽了這個種族。

**解法**：
- 在 `sanguinist.lua` 的 `descriptor_choices.race` 中設 `__ALL__ = "allow"` 允許所有種族
- 確認目標種族（如 Human）的 `descriptor_choices.subclass` 沒有設 `__ALL__ = "disallow"` 且沒有特別排除 Sanguinist

---

### 錯誤：技能依賴鏈無法正常工作（`T_BLOOD_DRAIN` 為 nil）

**原因**：`ActorTalents.T_BLOOD_DRAIN` 在技能定義載入之前被引用。

**解法**：確認 `data/birth/classes/sanguinist.lua` 中的 `talents` 表格在 `data/talents/blood.lua` 載入**後**才執行。因為 `hooks/load.lua` 先載入技能再載入描述符，這通常不成問題。若仍報錯，把技能 ID 改為字串：

```lua
-- 用字串而不是常數（不依賴執行順序）
talents = {
    ["T_BLOOD_MASTERY"] = 1,
    ["T_BLOOD_DRAIN"]   = 1,
},
```

---

## 小結：製作新職業的完整檢查清單

- [ ] `init.lua`：設定 `hooks=true, data=true`
- [ ] `hooks/load.lua`：`ActorTalents:loadDefinition` + `Birther:loadDefinition`
- [ ] `data/talents/xxx.lua`：`newTalentType` + `newTalent`（全部技能）
- [ ] `data/birth/classes/xxx.lua`：`class` 大類別 + `subclass` 子職業
- [ ] subclass 的 `talents_types` 包含所有要解鎖的技能樹
- [ ] subclass 的 `talents` 包含起始技能
- [ ] subclass 的 `copy.equipment` 用 `resolvers.equipbirth`
- [ ] `descriptor_choices` 設定種族相容性（允許所有種族或限制特定種族）
- [ ] 在遊戲中測試角色創建 → 技能 UI → 每個技能效果
