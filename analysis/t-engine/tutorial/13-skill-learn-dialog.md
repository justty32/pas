# 教學 13：自訂技能學習界面

## 本章目標

製作一個全新的**技能學習 Dialog**，並在遊戲 HUD 中加入一個可點擊的按鈕開啟它：

- 左側：TreeList 顯示所有天賦分類（可展開）及各天賦的等級狀態
- 右側：選中天賦的完整說明 + 「學習」按鈕
- 底部：「關閉」按鈕
- **舊的 `UseTalents` Dialog 完全保留**，按原有快捷鍵仍可開啟
- HUD 下方加入一個「技能書」圖示，點擊後開啟新 Dialog

---

## 系統核心概念

### TE4 Dialog 的生命週期

```lua
-- 開啟 Dialog
game:registerDialog(MyDialog.new(args))
-- → 加入 game.dialogs 列表
-- → 下一幀開始渲染
-- → Dialog 的 key/mouse 接管輸入

-- 關閉 Dialog
game:unregisterDialog(self)
-- → 從 game.dialogs 移除
-- → 輸入控制返還給前一個 Dialog 或遊戲本身
```

### `loadUI` 佈局系統

Dialog 的 `loadUI` 接受一個表格，每個元素描述一個 UI 元件的位置：

```lua
self:loadUI{
    {left=0,   top=0,    ui=left_widget},   -- 距左邊 0，距頂部 0
    {right=0,  top=0,    ui=right_widget},  -- 距右邊 0，距頂部 0
    {left=0,   bottom=0, ui=bottom_btn},    -- 距左邊 0，距底部 0
    {hcenter=0, vcenter=0, ui=center_widget}, -- 水平+垂直置中
}
-- left/right/top/bottom 是相對於 Dialog 內容區域（iw × ih）的偏移
```

### 天賦資料結構

```lua
-- actor.talents_types_def → {tt1, tt2, ...}（天賦分類列表）
-- 每個分類：
tt = {
    type    = "generic/speed",   -- 分類 ID
    name    = "速度技巧",         -- 顯示名稱
    talents = {t1, t2, ...},     -- 此分類中的天賦列表
    known   = true,              -- 玩家是否解鎖此分類
    mastery = 1.0,               -- 熟練度
}

-- actor.talents_def[T_FIREBALL] → 天賦定義
t = {
    id      = T_FIREBALL,
    name    = "火球術",
    type    = {"spell/fire", 1},  -- {分類ID, 分類中的排序位置}
    require = {level={2}},        -- 等級需求
    points  = 5,                  -- 最大等級
    mode    = "activated",        -- "activated" / "sustained" / "passive"
}

-- 玩家天賦狀態
actor:getTalentLevelRaw(t.id)  -- 當前等級（0 = 未學習）
actor:canLearnTalent(t)        -- 返回 true 或 false, "錯誤訊息"
actor:learnTalent(t.id)        -- 學習 / 升級（消耗 unused_talents 點數）
actor.unused_talents           -- 可用天賦點數
actor:getTalentFullDescription(t)  -- 完整說明文字
```

---

## 完整檔案結構

```
mygame/
  mod/
    dialogs/
      SkillLearnDialog.lua    ← 新 Dialog（主體）
    class/
      uiset/
        GameUI.lua            ← 自訂 UISet，加入技能書按鈕
      Game.lua                ← 加入 SHOW_SKILL_TREE 鍵綁定
```

---

## 步驟一：技能學習 Dialog

### 完整實作：`mod/dialogs/SkillLearnDialog.lua`

```lua
-- mod/dialogs/SkillLearnDialog.lua
-- 自訂技能學習界面
-- 保留舊版 UseTalents Dialog，此為獨立新界面

require "engine.class"
local Dialog    = require "engine.ui.Dialog"
local TreeList  = require "engine.ui.TreeList"
local Textzone  = require "engine.ui.Textzone"
local Button    = require "engine.ui.Button"
local Separator = require "engine.ui.Separator"

module(..., package.seeall, class.inherit(Dialog))

-- ── 建構函式 ─────────────────────────────────────────────────
function _M:init(actor)
    self.actor = actor

    Dialog.init(self, "技能學習", game.w * 0.75, game.h * 0.8)

    -- 右側區域的寬度
    local right_w = math.floor(self.iw * 0.45)
    -- 左側 TreeList 的寬度
    local left_w  = self.iw - right_w - 20  -- 20 是中間 Separator 的空間

    -- 右側：天賦說明區域（可捲動）
    self.c_desc = Textzone.new{
        width       = right_w,
        height      = self.ih - 60,
        auto_height = false,
        scrollbar   = true,
        text        = "#GREY#選擇一個天賦以查看說明。",
    }

    -- 右側底部：學習按鈕 + 點數顯示
    self.c_learn_btn = Button.new{
        text = "學習（消耗 1 點）",
        fct  = function() self:doLearn() end,
    }
    self.c_points_label = Textzone.new{
        width       = right_w,
        height      = 30,
        auto_height = false,
        text        = self:getPointsText(),
    }

    -- 建立左側 TreeList 資料
    self:buildTree()

    self.c_tree = TreeList.new{
        width    = left_w,
        height   = self.ih - 10,
        scrollbar = true,
        -- 欄位定義
        columns  = {
            {name = "天賦名稱", width = 65, display_prop = "name"},
            {name = "等級",     width = 17, display_prop = "level_str"},
            {name = "狀態",     width = 18, display_prop = "status_str"},
        },
        tree     = self.tree,
        -- 點擊展開/收合
        fct      = function(item) if not item.sub then self:onSelect(item) end end,
        select   = function(item, sel) if sel and not item.sub then self:onSelect(item) end end,
    }

    -- 佈局
    self:loadUI{
        -- 左側：TreeList（0 偏移，頂對齊）
        {left = 0, top = 0, ui = self.c_tree},
        -- 中間：垂直分隔線
        {left = left_w + 5, top = 5,
         ui = Separator.new{dir = "vertical", size = self.ih - 10}},
        -- 右側頂：天賦說明
        {right = 0, top = 0, ui = self.c_desc},
        -- 右側底：可用點數
        {right = 0, bottom = self.c_learn_btn.h + 5, ui = self.c_points_label},
        -- 右側最底：學習按鈕
        {right = 0, bottom = 0, ui = self.c_learn_btn},
    }

    self:setupUI()
    self:setFocus(self.c_tree)

    -- 鍵盤綁定
    self.key:addBinds{
        EXIT = function() game:unregisterDialog(self) end,
    }
end

-- ── 可用點數文字 ──────────────────────────────────────────────
function _M:getPointsText()
    local pts = self.actor.unused_talents or 0
    if pts == 0 then
        return "#RED#可用天賦點數：0（無法學習）"
    else
        return ("#LIGHT_GREEN#可用天賦點數：%d"):format(pts)
    end
end

-- ── 建立 TreeList 資料 ────────────────────────────────────────
-- TreeList 期望的資料結構：
--   {
--     { name="分類名稱", sub={...子項目...} },  ← 分類節點（可展開）
--     { name="天賦名稱", talent_id=..., ... },  ← 葉節點（可選中）
--   }
function _M:buildTree()
    self.tree = {}
    self.talent_items = {}  -- 用於 doLearn 查找當前選中的天賦

    local actor = self.actor

    for i, tt in ipairs(actor.talents_types_def or {}) do
        -- 只顯示玩家已解鎖的分類（known = true）
        if tt.known then
            local sub_items = {}
            local cat_display = tt.type:gsub(".*/", ""):capitalize()

            for j, t in ipairs(tt.talents or {}) do
                local cur_lv  = actor:getTalentLevelRaw(t.id) or 0
                local max_lv  = t.points or 1
                local can, why = actor:canLearnTalent(t)

                -- 狀態文字
                local status
                if cur_lv >= max_lv then
                    status = "#GREY#已滿"
                elseif can then
                    status = "#LIGHT_GREEN#可學"
                elseif (actor.unused_talents or 0) == 0 then
                    status = "#RED#無點數"
                else
                    status = "#YELLOW#未達需求"
                end

                local item = {
                    name       = t.name,
                    level_str  = ("%d/%d"):format(cur_lv, max_lv),
                    status_str = status,
                    talent     = t,
                    talent_id  = t.id,
                    _can_learn = can,
                    _why       = why,
                }
                sub_items[#sub_items+1] = item
                self.talent_items[t.id] = item
            end

            if #sub_items > 0 then
                self.tree[#self.tree+1] = {
                    name      = ("#GOLD#%s"):format(tt.name:capitalize()),
                    -- TreeList 用 sub 欄位識別分類節點
                    sub       = sub_items,
                    -- 預設展開
                    shown     = true,
                }
            end
        end
    end
end

-- ── 選中天賦時更新說明 ────────────────────────────────────────
function _M:onSelect(item)
    if not item or not item.talent then return end

    self.selected_talent = item.talent

    -- 更新說明文字
    local desc = self.actor:getTalentFullDescription(item.talent)
    local cur_lv = self.actor:getTalentLevelRaw(item.talent_id) or 0
    local max_lv = item.talent.points or 1

    local header = ("#GOLD#%s#LAST#\n#GREY#等級：%d / %d  |  類型：%s\n\n"):format(
        item.talent.name,
        cur_lv, max_lv,
        item.talent.type and item.talent.type[1] or "?"
    )

    -- 若有前置需求，顯示
    local req_text = ""
    if item.talent.require then
        req_text = "#YELLOW#前置需求：\n"
        local req = item.talent.require
        if req.level then
            req_text = req_text .. ("  等級 %d 以上\n"):format(req.level[1] or 0)
        end
        if req.talent then
            for _, rv in ipairs(req.talent) do
                local req_t = self.actor:getTalentFromId(rv[1])
                req_text = req_text .. ("  需要：%s Lv.%d\n"):format(
                    req_t and req_t.name or tostring(rv[1]), rv[2] or 1)
            end
        end
        req_text = req_text .. "\n"
    end

    self.c_desc:setText(header .. req_text .. (desc or "（無說明）"))

    -- 更新可用點數文字
    self.c_points_label:setText(self:getPointsText())
end

-- ── 學習按鈕邏輯 ─────────────────────────────────────────────
function _M:doLearn()
    local t = self.selected_talent
    if not t then
        self:simplePopup("提示", "請先選擇一個天賦。")
        return
    end

    local actor = self.actor
    local cur_lv = actor:getTalentLevelRaw(t.id) or 0
    local max_lv = t.points or 1

    -- 1. 已達上限
    if cur_lv >= max_lv then
        self:simplePopup("無法學習", ("「%s」已達最高等級（%d/%d）。"):format(
            t.name, cur_lv, max_lv))
        return
    end

    -- 2. 沒有可用點數
    if (actor.unused_talents or 0) <= 0 then
        self:simplePopup("無法學習", "沒有可用的天賦點數。\n升級後可獲得天賦點數。")
        return
    end

    -- 3. 不符合前置需求
    local can, why = actor:canLearnTalent(t)
    if not can then
        self:simplePopup("無法學習",
            ("「%s」不符合學習條件：\n%s"):format(t.name, why or "未知原因"))
        return
    end

    -- 4. 學習
    actor:learnTalent(t.id)
    actor.unused_talents = (actor.unused_talents or 1) - 1
    actor.changed = true

    game.logPlayer(actor, "#LIGHT_GREEN#學會了 %s（等級 %d）！",
        t.name, actor:getTalentLevelRaw(t.id))

    -- 5. 刷新列表（等級和狀態可能改變）
    self:buildTree()
    self.c_tree:setList(self.tree)

    -- 6. 更新右側說明和點數
    local updated_item = self.talent_items[t.id]
    if updated_item then
        self:onSelect(updated_item)
    end

    self.c_points_label:setText(self:getPointsText())
end
```

---

## 步驟二：在 HUD 加入「技能書」圖示按鈕

### 設計方法

TE4 的 UISet 管理 HUD 的繪製和滑鼠事件。加入新按鈕的標準流程：

1. 在 `displayUI()` 中把按鈕圖示繪製到螢幕
2. 在 `createSeparators()` 中記錄按鈕的位置和尺寸
3. 在 `clickIcon()` 中根據點擊座標開啟 Dialog

對於**自訂模組**（不繼承 ToME UISet），最乾淨的方法是讓模組有自己的 UISet 類別。以下示範在簡化的自訂 UISet 中加入按鈕。

### 自訂 UISet：`mod/class/uiset/GameUI.lua`

```lua
-- mod/class/uiset/GameUI.lua
-- 自訂 UISet，在 HUD 下方加入技能書按鈕

require "engine.class"
local UISet     = require "engine.game.GameUI"   -- 引擎基礎 UISet
local LogDisplay = require "engine.LogDisplay"
local FontPackage = require "engine.FontPackage"

module(..., package.seeall, class.inherit(UISet))

-- 預載入按鈕圖示（module 層級，只載入一次）
local _skill_icon, _skill_icon_w, _skill_icon_h
local _skill_icon_sel, _, _  -- hover 高亮版（可選）

function _M:init()
    UISet.init(self)
end

function _M:activate()
    UISet.activate(self)

    -- 載入技能書圖示
    -- 你可以替換為自己的圖片路徑；這裡借用引擎現有圖示做示範
    _skill_icon, _skill_icon_w, _skill_icon_h =
        core.display.loadImage("/data/gfx/ui/talents-icon.png"):glTexture()

    -- 字型
    local font, size = FontPackage:getFont("default")
    local f = core.display.newFont(font, size)
    self.hud_font   = f
    self.hud_font_h = f:lineSkip()

    -- 訊息日誌
    self.logdisplay = LogDisplay.new(
        0, game.h - self.hud_font_h * 5,
        game.w, self.hud_font_h * 5,
        nil, font, size)

    game.log = function(style, ...)
        if type(style) == "number" then
            self.logdisplay(...)
        else
            self.logdisplay(style, ...)
        end
    end
    game.logPlayer = function(e, style, ...)
        if e == game.player or e == game.party then
            game.log(style, ...)
        end
    end

    -- 記錄技能書按鈕的位置（供 clickIcon 使用）
    self:_setupSkillButton()
end

-- ── 設定技能書按鈕的螢幕位置 ─────────────────────────────────
function _M:_setupSkillButton()
    -- 把按鈕放在螢幕右下角
    local btn_w = _skill_icon_w or 32
    local btn_h = _skill_icon_h or 32
    self.skill_btn = {
        x = game.w - btn_w - 8,
        y = game.h - btn_h - 8,
        w = btn_w,
        h = btn_h,
    }

    -- 向 game 的全域滑鼠系統註冊這個區域
    -- （UISet 的 mouse 物件由引擎在 setupMouse 時掛載）
    if game.mouse then
        game.mouse:registerZone(
            self.skill_btn.x, self.skill_btn.y,
            self.skill_btn.w, self.skill_btn.h,
            function(button, mx, my, xrel, yrel, bx, by, event)
                if event == "button" and button == "left" then
                    self:openSkillDialog()
                elseif event == "motion" then
                    -- hover：顯示 tooltip
                    game:tooltipDisplayAtMap(game.w, game.h,
                        "#GOLD#技能學習\n#LAST#點擊開啟技能學習界面。")
                end
            end
        )
    end
end

-- ── displayUI：每幀繪製 HUD ───────────────────────────────────
function _M:displayUI()
    -- 繪製訊息日誌背景（半透明黑色）
    core.display.drawQuad(
        0, game.h - self.hud_font_h * 5 - 2,
        game.w, self.hud_font_h * 5 + 2,
        0, 0, 0, 180)

    -- 繪製技能書圖示按鈕
    if _skill_icon and self.skill_btn then
        local b = self.skill_btn

        -- hover 效果：滑鼠移到按鈕上時略微增亮
        local mx, my = core.mouse.get()
        local hover = mx >= b.x and mx <= b.x + b.w
                  and my >= b.y and my <= b.y + b.h

        -- 繪製按鈕背景框（半透明圓角矩形）
        core.display.drawQuad(b.x - 2, b.y - 2, b.w + 4, b.h + 4,
            20, 20, 20, hover and 200 or 150)

        -- 繪製圖示
        local alpha = hover and 1.0 or 0.8
        _skill_icon:toScreenFull(b.x, b.y, b.w, b.h,
            _skill_icon_w, _skill_icon_h,
            alpha, alpha, alpha, alpha)  -- r g b a

        -- 繪製標籤文字（圖示下方）
        local label = "技能"
        local lw    = self.hud_font:size(label)
        self.hud_font:drawColorString(
            core.display.glMatrix(),
            label,
            b.x + (b.w - lw) / 2, b.y + b.h + 2,
            hover and 1 or 0.7,   -- r
            hover and 1 or 0.9,   -- g
            hover and 0 or 0.7,   -- b
            true)
    end
end

-- ── 開啟技能學習 Dialog ───────────────────────────────────────
function _M:openSkillDialog()
    if not game.player then return end
    game:registerDialog(
        require("mod.dialogs.SkillLearnDialog").new(game.player)
    )
end
```

> **`toScreenFull(x, y, w, h, tex_w, tex_h, r, g, b, a)`**：把 glTexture 繪製到指定矩形區域，`r g b a` 是顏色乘數（1.0 = 原色，< 1.0 = 變暗）。

---

## 步驟三：鍵盤快捷鍵（備用方式）

即使已有 HUD 按鈕，加入鍵盤快捷鍵讓操作更方便：

### 修改 `mod/class/Game.lua → setupCommands()`

```lua
-- mod/class/Game.lua

function _M:setupCommands()
    -- 原有指令...

    self.key:addBinds{
        -- ★ 新增：開啟技能學習界面（預設綁定 K 鍵，可在設定中更改）
        SHOW_SKILL_TREE = function()
            game:registerDialog(
                require("mod.dialogs.SkillLearnDialog").new(self.player)
            )
        end,

        -- 保留舊版 UseTalents（預設 T 鍵）
        USE_TALENTS = function()
            game:registerDialog(
                require("engine.dialogs.UseTalents").new(self.player)
            )
        end,
    }
end
```

### 在 `data/keybinds/` 中宣告新鍵位

```lua
-- mod/data/keybinds/interface.lua（或建立新檔）
-- 讓玩家可以在設定界面中重新綁定此鍵

defineKeyBind{
    default = {{key="_k"}},   -- 預設 K 鍵
    id      = "SHOW_SKILL_TREE",
    name    = "開啟技能學習界面",
    type    = "interface",
}
```

---

## 步驟四：在 `mod/load.lua` 中載入 UISet

確保遊戲使用自訂的 UISet：

```lua
-- mod/load.lua（摘錄）

-- 載入自訂 UISet
local GameUI = require "mod.class.uiset.GameUI"

-- 在 Game.init 後設定 UISet（通常在 mod/class/Game.lua 的 init 中）
```

### 在 `mod/class/Game.lua → init()` 中設定 UISet

```lua
-- mod/class/Game.lua

function _M:init(zone, level, player)
    -- ... 原有初始化 ...

    -- ★ 設定自訂 UISet
    self.uiset = require("mod.class.uiset.GameUI").new()
    self.uiset:activate()
end
```

---

## 完整 UI 佈局示意圖

```
┌────────────────────────────────────────────────────────────────┐
│                          技能學習                               │  ← Dialog 標題
├──────────────────────────┬─────────────────────────────────────┤
│  天賦名稱      等級  狀態 │                                     │
│ ▼ 戰鬥技巧              │  ── 選中天賦的說明 ──               │
│    近戰攻擊   2/5  可學  │                                     │
│    防禦姿態   0/5  可學  │  [天賦名稱]                         │
│    連擊       0/5  未達  │  等級：0 / 5  |  類型：combat/…    │
│ ▼ 魔法        ───────── │                                     │
│    火球術     0/5  可學  │  前置需求：                         │
│    冰錐術     3/5  已滿  │    等級 5 以上                      │
│    閃電鏈     0/5  無點  │                                     │
│                          │  [天賦說明文字…]                    │
│                          │                                     │
│                          │─────────────────────────────────────│
│                          │  可用天賦點數：2                    │
│                          │  [學習（消耗 1 點）]               │
└──────────────────────────┴─────────────────────────────────────┘
                                  [關閉]  ← Dialog 底部按鈕（由 setupUI 自動加入）
```

---

## 步驟五：處理 `simplePopup`

`Dialog:simplePopup(title, text)` 是引擎 Dialog 基礎類別提供的方法，用於顯示簡單的確認彈窗。它的實作是在 Dialog 內部再開啟一個子 Dialog，不需要額外實作。

但如果你的模組沒有繼承完整的 Dialog 類別（例如使用極簡 UI），可以自行實作：

```lua
-- 替代版本：直接用 game.log 輸出錯誤，不開彈窗
function _M:doLearn()
    -- ...（省略前半段，直接換掉 simplePopup）

    local can, why = actor:canLearnTalent(t)
    if not can then
        game.logPlayer(actor,
            "#RED#無法學習「%s」：%s", t.name, why or "未知原因")
        return
    end
    -- ...
end
```

---

## 常見錯誤排查

| 錯誤現象 | 原因 | 解法 |
|---------|------|------|
| TreeList 顯示空白 | `buildTree()` 沒有任何 known 分類 | 確認 actor 的 `talents_types_def` 已填充；確認有分類設定了 `known = true` |
| 學習後等級沒有更新 | `buildTree()` + `setList()` 沒有重建 | 確認 `doLearn()` 末尾有呼叫 `self.c_tree:setList(self.tree)` |
| `canLearnTalent` 始終返回 false | 玩家沒有 `unused_talents` 點數 | 在 `newGame()` 中給玩家初始點數：`player.unused_talents = 3` |
| 按鈕點擊沒有反應 | `game.mouse` 尚未初始化時呼叫 `_setupSkillButton` | 把 `_setupSkillButton` 移到 `Game:setupMouse()` 完成後，或在 UISet `activate()` 中延遲呼叫 |
| `toScreenFull` 參數數量錯誤 | TE4 glTexture 的 `toScreenFull` 參數需精確 | 呼叫格式：`tex:toScreenFull(x, y, w, h, tex_w, tex_h)` （基礎版，不帶顏色） |
| Dialog 的 `loadUI` 佈局錯亂 | `right=0` / `bottom=0` 相對的是 `iw`/`ih`（內容區），不是 `w`/`h` | 確認 `Dialog.init` 已呼叫；確認 `iw`/`ih` 在 `loadUI` 時已正確設定 |
| 舊 `UseTalents` 被覆蓋消失 | 誤刪了 `USE_TALENTS` 鍵綁定 | 在 `setupCommands` 中同時保留 `USE_TALENTS` 和 `SHOW_SKILL_TREE` 兩個綁定 |

---

## 進階擴展方向

### 1. 天賦分頁（Tabs）

把天賦分類改用 `Tabs` 元件顯示，每個 Tab 是一個獨立的 TreeList：

```lua
local Tabs = require "engine.ui.Tabs"
self.c_tabs = Tabs.new{
    width = left_w,
    height = self.ih - 10,
    tabs = {
        {title = "戰鬥",   ui = self:buildTabList("combat")},
        {title = "魔法",   ui = self:buildTabList("spell")},
        {title = "通用",   ui = self:buildTabList("generic")},
    },
}
```

### 2. 即時預覽（學習前預覽效果）

點擊「學習」前，右側額外顯示學習後的下一等級說明：

```lua
-- 在 onSelect 中額外顯示下一級說明
local next_lv = cur_lv + 1
if next_lv <= max_lv then
    local next_desc = self.actor:getTalentFullDescription(t, next_lv)
    self.c_desc:setText(... "\n#YELLOW#──下一級說明──\n" .. next_desc)
end
```

### 3. 支援天賦書 / 捲軸學習

若天賦可以透過道具（天賦書）學習，在 `doLearn()` 中加入判斷，消耗道具而非點數：

```lua
-- 學習天賦書：消耗背包中對應的書
local book = self:findBook(t.id)
if book then
    self.actor:removeObject(self.actor:getInven("INVEN"), book_idx)
    self.actor:learnTalent(t.id)
else
    -- 沒有書，走普通消耗點數流程
end
```

---

## 本章小結

| 概念 | 實作位置 | 關鍵 API |
|------|---------|---------|
| 自訂 Dialog | `dialogs/SkillLearnDialog.lua` | `Dialog.init` + `loadUI` + `setupUI` |
| TreeList 天賦樹 | `SkillLearnDialog:buildTree()` | `TreeList.new{tree=..., columns=...}` |
| 天賦資料讀取 | `actor.talents_types_def` | `getTalentLevelRaw`, `canLearnTalent`, `learnTalent` |
| 學習邏輯 | `SkillLearnDialog:doLearn()` | `actor:learnTalent(t.id)`, `actor.unused_talents` |
| HUD 圖示按鈕 | `uiset/GameUI.lua → displayUI()` | `glTexture:toScreenFull`, `game.mouse:registerZone` |
| 鍵盤快捷鍵 | `class/Game.lua → setupCommands()` | `self.key:addBinds{SHOW_SKILL_TREE=...}` |
| 舊界面保留 | `setupCommands()` 的 `USE_TALENTS` | 不刪除原有綁定，新舊同時存在 |
