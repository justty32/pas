# 教學 04：任務系統與 NPC 對話

> **目標**：為 `hellodungeon` 加入完整的任務流程：村長 NPC 開口委託、玩家接受任務、擊殺地城頭目觸發完成、回到城鎮報告領取獎勵。
>
> **前置條件**：完成教學 01–03（已有城鎮與地城兩個地區）。

---

## 目錄

1. [系統架構總覽](#1-系統架構總覽)
2. [第一步：Quest 定義檔](#2-第一步quest-定義檔)
3. [第二步：ActorQuest 混入](#3-第二步actorquest-混入)
4. [第三步：Chat 對話腳本格式](#4-第三步chat-對話腳本格式)
5. [第四步：建立村長 NPC](#5-第四步建立村長-npc)
6. [第五步：建立對話腳本](#6-第五步建立對話腳本)
7. [第六步：建立地城頭目](#7-第六步建立地城頭目)
8. [第七步：回報完成對話](#8-第七步回報完成對話)
9. [第八步：連接 NPC 與對話觸發](#9-第八步連接-npc-與對話觸發)
10. [第九步：顯示任務日誌](#10-第九步顯示任務日誌)
11. [完整檔案結構](#11-完整檔案結構)
12. [常見錯誤排查](#12-常見錯誤排查)

---

## 1. 系統架構總覽

```
Quest 定義（.lua 檔）
  ├── name, desc, id
  ├── on_grant(self, who)          ← 任務給予時
  └── on_status_change(self, who, status, sub)  ← 狀態改變時

ActorQuest（混入）
  ├── grantQuest("quest-id")       ← 給予任務
  ├── hasQuest("quest-id")         ← 檢查是否有任務（回傳 Quest 物件或 false）
  ├── setQuestStatus("id", COMPLETED, "sub-obj")  ← 設定任務/子目標狀態
  └── isQuestStatus("id", DONE)    ← 查詢狀態

Chat 腳本（data/chats/xxx.lua）
  ├── newChat{ id="xxx", text="...", answers={...} }
  ├── answers.cond(npc, player)    ← 顯示選項的條件
  ├── answers.action(npc, player)  ← 選擇後執行的動作
  └── return "welcome"             ← 指定第一個對話節點

Chat 引擎
  ├── Chat.new("chat-name", npc, player)
  └── game:registerDialog(chat_dlg)  ← 顯示對話視窗
```

**任務狀態常數**（定義在 `engine/Quest.lua`）：

| 常數 | 值 | 意義 |
|------|----|------|
| `Quest.PENDING` | 0 | 進行中（預設） |
| `Quest.COMPLETED` | 1 | 達成目標，可回報 |
| `Quest.DONE` | 100 | 已完成（領取獎勵後） |
| `Quest.FAILED` | 101 | 已失敗 |

---

## 2. 第一步：Quest 定義檔

Quest 定義是一個 Lua 檔案，由 `grantQuest("id")` 動態載入。引擎會從 `/data/quests/<id>.lua` 讀取：

```lua
-- game/modules/hellodungeon/data/quests/slay-boss.lua

-- 任務 ID（與檔案名稱相同）
id = "slay-boss"

-- 顯示在任務日誌的標題
name = "消滅科博德首領"

-- 任務描述函數（動態生成，可依狀態顯示不同文字）
desc = function(self, who)
    local d = {}
    d[#d+1] = "村長請你消滅地城深處的科博德首領，以保護城鎮的安全。"

    -- 依子目標狀態顯示進度
    if self:isCompleted("killed_boss") then
        d[#d+1] = "\n#LIGHT_GREEN#✔ 已擊殺科博德首領。#LAST#"
    else
        d[#d+1] = "\n#YELLOW#○ 目標：擊殺地城第三層的科博德首領。#LAST#"
    end

    if self:isStatus(self.DONE) then
        d[#d+1] = "\n#LIGHT_GREEN#✔ 已向村長回報，任務完成。#LAST#"
    elseif self:isCompleted("killed_boss") then
        d[#d+1] = "\n#YELLOW#○ 回到城鎮向村長回報。#LAST#"
    end

    return table.concat(d, "\n")
end

-- 任務給予時呼叫（可在這裡初始化任務狀態、顯示歡迎訊息等）
on_grant = function(self, who)
    game.logPlayer(who, "#YELLOW#新任務：%s", self.name)
end

-- 任務/子目標狀態改變時呼叫
on_status_change = function(self, who, status, sub)
    if sub == "killed_boss" and status == self.COMPLETED then
        game.logPlayer(who, "#LIGHT_GREEN#任務進度：科博德首領已被消滅！返回城鎮回報。")
    end
    -- 所有子目標完成 → 標記整個任務完成
    if self:isCompleted("killed_boss") and self:isCompleted("reported") then
        who:setQuestStatus(self.id, engine.Quest.DONE)
    end
end
```

**設計要點**：

- `id` 必須與傳入 `grantQuest()` 的字串一致，也等於檔案名稱（不含 .lua）
- `desc` 可以是字串或函數；函數可在不同狀態下顯示不同內容
- 子目標（sub-objective）是任意字串，用 `setQuestStatus(id, status, sub)` 設定

---

## 3. 第二步：ActorQuest 混入

在 `Actor.lua` 中加入 `ActorQuest`：

```lua
-- game/modules/hellodungeon/class/Actor.lua

require "engine.class"
local Actor = require "engine.Actor"
-- ... 其他 require ...
local ActorQuest = require "engine.interface.ActorQuest"   -- ← 新增

module(..., package.seeall, class.inherit(
    Actor,
    -- ... 其他混入 ...
    ActorQuest      -- ← 新增（不需要單獨 init，它是純方法集合）
))

function _M:init(t, no_default)
    -- ActorQuest 不需要 init：self.quests 是在 grantQuest 時惰性建立的
    Actor.init(self, t, no_default)
    -- ... 其他 init ...
end
```

`ActorQuest` 提供的方法（不需要手動 init）：

| 方法 | 說明 |
|------|------|
| `grantQuest("id")` | 從 `/data/quests/id.lua` 載入並給予任務 |
| `hasQuest("id")` | 回傳 Quest 物件或 `false` |
| `setQuestStatus("id", status, sub)` | 設定任務/子目標狀態 |
| `isQuestStatus("id", status, sub)` | 查詢是否為指定狀態 |
| `removeQuest("id")` | 移除任務（謹慎使用）|

---

## 4. 第三步：Chat 對話腳本格式

對話腳本是一個普通 Lua 檔案，放在 `data/chats/`，用 `newChat{}` 宣告每個對話節點：

```lua
-- data/chats/elder.lua（範例結構）

-- 第一個對話節點
newChat{ id="welcome",
    -- @playername@ 會被替換為玩家角色名稱
    text = "你好，@playername@！我是村長。科博德首領盤踞地城，威脅我們的城鎮...",
    answers = {
        -- 每個答案是一個表格
        -- [1]      = 顯示文字
        -- cond     = 顯示此選項的條件（function(npc, player) return bool）
        -- action   = 選擇後執行的動作（function(npc, player)）
        -- jump     = 跳到哪個 id 繼續（nil = 結束對話）

        -- 條件1：玩家還沒有任務 → 提供接受任務選項
        {
            "我願意替你消滅牠！",
            cond = function(npc, player)
                return not player:hasQuest("slay-boss")
            end,
            action = function(npc, player)
                player:grantQuest("slay-boss")
                game.logPlayer(player, "你接受了任務：消滅科博德首領。")
            end,
            jump = "accepted",
        },

        -- 條件2：任務已完成頭目但還沒回報 → 顯示回報選項
        {
            "首領已被我消滅了！",
            cond = function(npc, player)
                return player:hasQuest("slay-boss")
                    and player:isQuestStatus("slay-boss", engine.Quest.COMPLETED, "killed_boss")
                    and not player:isQuestStatus("slay-boss", engine.Quest.COMPLETED, "reported")
            end,
            action = function(npc, player)
                player:setQuestStatus("slay-boss", engine.Quest.COMPLETED, "reported")
                -- 給予獎勵
                player.life = math.min(player.life + 50, player.max_life)
                game.logPlayer(player, "#LIGHT_GREEN#村長感謝你的英勇！你的生命值回復了 50 點。")
            end,
            jump = "reward",
        },

        -- 條件3：任務已全部完成 → 感謝對話
        {
            "城鎮現在安全多了。",
            cond = function(npc, player)
                return player:hasQuest("slay-boss")
                    and player:isQuestStatus("slay-boss", engine.Quest.DONE)
            end,
            jump = "done",
        },

        -- 沒有條件的選項：隨時可見
        {
            "我只是路過。",
            -- 沒有 action，沒有 jump → 結束對話
        },
    }
}

-- 接受任務後的節點
newChat{ id="accepted",
    text = "太好了！地城的第三層深處有牠的巢穴。祝你好運，勇者！",
    answers = {
        { "我會的，再見！" },
    }
}

-- 回報完成後的節點
newChat{ id="reward",
    text = "你真是太厲害了！城鎮因你而得救。請收下這點薄禮。",
    answers = {
        { "謝謝你，村長。" },
    }
}

-- 任務已完成的節點
newChat{ id="done",
    text = "再次感謝你的幫助，英雄！城鎮的大門永遠為你敞開。",
    answers = {
        { "保重。" },
    }
}

-- 必須 return 第一個節點的 id
return "welcome"
```

**`text` 中的特殊標記**：

| 標記 | 替換內容 |
|------|----------|
| `@playername@` | 玩家名稱 |
| `@npcname@` | NPC 名稱 |
| `#RED#`...`#LAST#` | 顏色標記（`#LAST#` = 恢復前一個顏色） |

---

## 5. 第四步：建立村長 NPC

```lua
-- game/modules/hellodungeon/data/zones/town/npcs.lua

newEntity{
    define_as = "ELDER",
    type = "humanoid", subtype = "human",
    name = "村長 Aldric",
    display = "@", color = colors.YELLOW,
    -- 村長不移動、不攻擊
    ai = "simple",
    ai_state = { talent_in=9999 },
    body = { INVEN=10 },
    energy = { mod=1 },
    stats = { str=10, dex=10, con=10 },
    max_life = 100, life_rating = 10,
    rank = 1,
    exp_worth = 0,      -- 殺掉不給經驗（村長不應該被殺...）
    never_move = 1,     -- 不移動

    -- 對話腳本名稱（對應 data/chats/elder.lua）
    chat = "elder",

    -- 村長是固定生成的，不要被隨機生成器取走
    -- 通過在 zone.lua 的 post_process 中手動放置
    rarity = false,     -- 不參與隨機生成
}
```

村長不應該被 `generator.actor.Random` 隨機放置，而是在地圖生成完成後手動放在固定位置。在 `data/zones/town/zone.lua` 的 `post_process` 中：

```lua
-- data/zones/town/zone.lua 中的 post_process

post_process = function(level, zone)
    -- 在地圖中間位置放置村長
    local cx, cy = math.floor(level.map.w / 2), math.floor(level.map.h / 2)

    -- 找一個空的地板格
    for tries = 0, 50 do
        local x = cx + rng.range(-5, 5)
        local y = cy + rng.range(-5, 5)
        if not level.map:checkEntity(x, y, engine.Map.TERRAIN, "block_move")
            and not level.map(x, y, engine.Map.ACTOR) then
            -- 建立並放置村長
            local npc = zone.npc_class:loadList("/data/zones/town/npcs.lua")
            local elder = zone:makeEntityByName(level, npc, "ELDER")
            if elder then
                zone:addEntity(level, elder, "actor", x, y)
            end
            break
        end
    end
end,
```

---

## 6. 第五步：建立對話腳本

建立對話腳本檔案（在第三步中已完整展示格式）：

```lua
-- game/modules/hellodungeon/data/chats/elder.lua
-- （完整程式碼見第三步）
```

確保 `data/chats/` 目錄存在。`engine.Chat` 會自動尋找 `/data/chats/<name>.lua` 路徑（虛擬路徑）。

---

## 7. 第六步：建立地城頭目

在地城的 NPC 定義中加入首領，並在死亡時觸發任務進度：

```lua
-- game/modules/hellodungeon/data/general/npcs/kobold.lua
-- （在現有定義後加入首領）

newEntity{ base = "BASE_KOBOLD",
    define_as = "KOBOLD_BOSS",
    name = "科博德首領「鐵爪葛爾」",
    display = "K", color = colors.CRIMSON,
    level_range = {3, 3},   -- 只出現在第三層
    rarity = false,         -- 不隨機生成，由地圖手動放置
    exp_worth = 5,
    rank = 3,               -- 精英怪（Boss 等級）
    max_life = resolvers.rngrange(60, 80),
    life_rating = 14,
    combat = { dam=resolvers.rngrange(10, 18), atk=12, apr=5 },
    body = { INVEN=10, WEAPON=1 },
    -- 死亡時觸發任務更新
    on_die = function(self, who)
        -- who = 殺死此 NPC 的 Actor（通常是玩家）
        if who == game.player then
            game.player:setQuestStatus(
                "slay-boss",
                engine.Quest.COMPLETED,
                "killed_boss"       -- 子目標 ID
            )
        end
        -- 掉落豐厚戰利品
        for i = 1, 3 do
            local o = game.zone:makeEntity(game.level, "object", nil, nil, true)
            if o then
                game.level.map:addObject(self.x, self.y, o)
            end
        end
    end,
}
```

在地城 zone.lua 的 `post_process` 中，當生成第三層時放置首領：

```lua
-- data/zones/dungeon/zone.lua

post_process = function(level, zone)
    -- 只在第三層放置首領
    if level.level ~= 3 then return end

    -- 找一個空的地板格放置首領
    for tries = 0, 100 do
        local x = rng.range(5, level.map.w - 5)
        local y = rng.range(5, level.map.h - 5)
        if not level.map:checkEntity(x, y, engine.Map.TERRAIN, "block_move")
            and not level.map(x, y, engine.Map.ACTOR) then
            local boss = zone:makeEntityByName(level, "actor", "KOBOLD_BOSS")
            if boss then
                zone:addEntity(level, boss, "actor", x, y)
                game.log("#RED#你感覺到深處有股邪惡的氣息…")
            end
            break
        end
    end
end,
```

---

## 8. 第七步：回報完成對話

回報對話已在第三步的 `elder.lua` 中整合（條件2：`killed_boss` 完成但 `reported` 未完成）。要讓整個任務標記為 `DONE`，需在 Quest 定義的 `on_status_change` 中處理：

```lua
-- data/quests/slay-boss.lua（相關段落）

on_status_change = function(self, who, status, sub)
    -- 子目標進度提示
    if sub == "killed_boss" and status == self.COMPLETED then
        game.logPlayer(who, "#LIGHT_GREEN#首領已倒下！返回城鎮向村長回報。")
    end

    -- 回報完成 → 標記整個任務為 DONE
    if sub == "reported" and status == self.COMPLETED then
        who:setQuestStatus(self.id, engine.Quest.DONE)
    end
end
```

---

## 9. 第八步：連接 NPC 與對話觸發

玩家需要按下「互動鍵」（或碰觸 NPC）才能開始對話。最常見的做法：

**方法 A：碰觸 NPC 觸發（修改 Actor.lua 的移動函數）**

在 `Player.lua` 的移動邏輯中，如果目標格有 NPC，先嘗試對話而不是攻擊：

```lua
-- game/modules/hellodungeon/class/Player.lua

-- 修改或加入 bump 函數（碰觸非敵對 NPC 時觸發對話）
function _M:bump(x, y)
    local target = game.level.map(x, y, engine.Map.ACTOR)
    -- 如果目標有 chat 欄位，且不是敵對的 → 觸發對話
    if target and target.chat and target.faction ~= "enemies" then
        self:talkTo(target)
        self:useEnergy()
        return true
    end
    -- 否則走正常攻擊流程
    return false
end

-- 對話入口函數
function _M:talkTo(npc)
    local chat = require "engine.Chat"
    local d = chat.new(npc.chat, npc, self)
    game:registerDialog(d)
end
```

**方法 B：按 `t` 鍵對話（在 Game.lua 的 setupCommands 加入）**

```lua
-- game/modules/hellodungeon/class/Game.lua
-- 在 setupCommands 中加入：

[{"_t"}] = function()
    if not self.player then return end
    -- 查詢玩家四周一格內有沒有可對話的 NPC
    for _, dir in ipairs({"n","s","e","w","ne","nw","se","sw"}) do
        local dx, dy = util.dirToCoord(util.dirToPath(dir))
        local x, y = self.player.x + dx, self.player.y + dy
        local target = self.level.map(x, y, engine.Map.ACTOR)
        if target and target.chat then
            self.player:talkTo(target)
            self.player:useEnergy()
            return
        end
    end
    self.log("附近沒有可以對話的人。")
end,
```

---

## 10. 第九步：顯示任務日誌

加入 `j` 鍵顯示任務日誌（用 TE4 內建 UI）：

```lua
-- game/modules/hellodungeon/class/Game.lua
-- 在 setupCommands 加入：

[{"_j"}] = function()
    if not self.player then return end
    -- 如果沒有任何任務
    if not self.player.quests or not next(self.player.quests) then
        game.log("你目前沒有任何進行中的任務。")
        return
    end

    -- 建立簡單的任務清單對話框
    local d = require("engine.ui.Dialog").new("任務日誌", 500, 400)
    local text = ""
    for id, q in pairs(self.player.quests) do
        local status = engine.Quest.status_text[q.status] or "未知"
        text = text..string.format("#YELLOW#%s#LAST# [%s]\n", q.name, status)
        if type(q.desc) == "function" then
            text = text..q:desc(self.player).."\n\n"
        elseif q.desc then
            text = text..q.desc.."\n\n"
        end
    end

    local Textzone = require "engine.ui.Textzone"
    local tz = Textzone.new{
        width = d.iw,
        height = d.ih,
        scrollbar = true,
        text = text,
    }
    d:loadUI{{left=0, top=0, ui=tz}}
    d:setupUI()
    game:registerDialog(d)
end,
```

---

## 11. 完整檔案結構

```
game/modules/hellodungeon/
├── class/
│   ├── Actor.lua                 ← 修改：繼承 ActorQuest
│   ├── Player.lua                ← 修改：加入 bump、talkTo 函數
│   └── Game.lua                  ← 修改：加入 t 鍵對話、j 鍵任務日誌

├── data/
│   ├── quests/                   ← 新增目錄
│   │   └── slay-boss.lua         ← 新增：討伐首領任務定義
│   │
│   ├── chats/                    ← 新增目錄
│   │   └── elder.lua             ← 新增：村長對話腳本
│   │
│   ├── general/
│   │   └── npcs/
│   │       └── kobold.lua        ← 修改：加入 KOBOLD_BOSS（含 on_die）
│   │
│   └── zones/
│       ├── town/
│       │   ├── zone.lua          ← 修改：加入 post_process 放置村長
│       │   └── npcs.lua          ← 修改：加入 ELDER 定義
│       └── dungeon/
│           └── zone.lua          ← 修改：加入 post_process 放置首領
```

**共新增 3 個檔案（目錄），修改 5 個檔案**。

---

## 12. 常見錯誤排查

### 錯誤：`grantQuest: no such quest 'slay-boss'`（找不到任務檔案）

**原因**：`grantQuest` 從 `/data/quests/slay-boss.lua` 載入，路徑基於虛擬檔案系統。

**解法**：確認檔案在 `data/quests/slay-boss.lua`（相對於你的模組根目錄）。虛擬路徑 `/data/` 對應到模組的 `data/` 目錄。

---

### 錯誤：對話框顯示後沒有文字

**原因**：`engine.Chat.new()` 找不到聊天腳本，或腳本中沒有 `return "welcome"`。

**解法**：
1. 確認 `data/chats/elder.lua` 存在
2. 確認腳本最後一行是 `return "welcome"`（第一個節點的 id）
3. 確認 `npc.chat = "elder"` 的字串與檔案名稱一致（不含 .lua）

---

### 錯誤：對話選項不出現（cond 返回 false）

**原因**：`cond` 函數的邏輯錯誤，或引用了不存在的 Quest。

**診斷**：在 cond 中加入 print 暫時除錯：

```lua
cond = function(npc, player)
    local q = player:hasQuest("slay-boss")
    print("[CHAT DEBUG] hasQuest:", q, "killed_boss:", q and player:isQuestStatus("slay-boss", engine.Quest.COMPLETED, "killed_boss"))
    return not q
end,
```

---

### 錯誤：`setQuestStatus` 沒有效果

**原因**：玩家還沒有這個任務（`hasQuest` 返回 false），`setQuestStatus` 會靜默忽略。

**解法**：確認在呼叫 `setQuestStatus` 之前已呼叫 `grantQuest`。在 `on_die` 中直接呼叫前可加個保護：

```lua
on_die = function(self, who)
    if who == game.player and game.player:hasQuest("slay-boss") then
        game.player:setQuestStatus("slay-boss", engine.Quest.COMPLETED, "killed_boss")
    end
end,
```

---

### 錯誤：村長不出現在地圖上

**原因**：`post_process` 中的 `makeEntityByName` 無法找到 `ELDER`，可能是 NPC 清單沒有正確載入。

**解法**：`makeEntityByName` 的第二個參數要是已載入的清單或類型字串 `"actor"`。使用字串 `"actor"` 時，引擎會從 `zone.npc_list` 中尋找：

```lua
-- 確保 zone.lua 中沒有限制 npc 清單，或手動傳入清單
local elder = zone:makeEntityByName(level, zone.npc_list, "ELDER")
```

如果 `npc_list` 中沒有 ELDER（因為設了 `rarity=false`），需要用：

```lua
local npc_class = require "mod.class.NPC"
local list = npc_class:loadList("/data/zones/town/npcs.lua")
local elder = zone:makeEntityByName(level, list, "ELDER")
```
