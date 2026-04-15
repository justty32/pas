# 開發教學 6：如何創建與修改生物 AI (Creature AI)

## 目標
本教學將引導你實作一個會主動追擊玩家的「魔法小怪」。它具備三種狀態：`idle` (閒置)、`chase` (追逐) 與 `attack` (攻擊)。

## 1. 前置知識
- 了解 `on_step` 的運行機制。
- 熟悉 `vector` 向量運算（Luanti 內建）。
- 了解 `minetest.find_path` 尋路 API。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`src/script/lua_api/l_env.cpp` (行號 1261, `l_find_path`)。
- **向量運算**：`builtin/common/vector.lua` (提供方向與距離運算)。
- **實作範例**：`games/devtest/mods/testentities/visuals.lua`。

## 3. 實作步驟

### A. 註冊 AI 實體
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_entity("magic_stuff:magic_mob", {
    initial_properties = {
        visual = "mesh",
        mesh = "magic_mob.obj",
        textures = {"magic_mob_texture.png"},
        physical = true,
        collisionbox = {-0.4, -0.01, -0.4, 0.4, 1.8, 0.4},
        visual_size = {x=10, y=10},
    },

    state = "idle",
    timer = 0,
    path = nil,

    on_step = function(self, dtime)
        self.timer = self.timer + dtime
        local pos = self.object:get_pos()
        local players = core.get_connected_players()
        local target = nil
        
        -- 1. 目標搜索：尋找最近的玩家
        for _, player in ipairs(players) do
            local ppos = player:get_pos()
            if vector.distance(pos, ppos) < 15 then -- 警戒範圍 15 格
                target = player
                break
            end
        end

        -- 2. 狀態機邏輯
        if target then
            self.state = "chase"
            local tpos = target:get_pos()
            local dist = vector.distance(pos, tpos)

            if dist < 2 then
                self.state = "attack"
                self:handle_attack(target, dtime)
            else
                self:handle_chase(pos, tpos)
            end
        else
            self.state = "idle"
            self.object:set_velocity({x=0, y=0, z=0})
        end
    end,

    -- 追逐邏輯：使用向量直衝或尋路
    handle_chase = function(self, pos, tpos)
        local dir = vector.direction(pos, tpos)
        local speed = 3
        -- 讓 AI 朝向玩家並移動
        self.object:set_yaw(core.dir_to_yaw(dir))
        self.object:set_velocity({x=dir.x * speed, y=0, z=dir.z * speed})
    end,

    -- 攻擊邏輯
    handle_attack = function(self, target, dtime)
        if self.timer > 1.5 then -- 攻擊冷卻 1.5 秒
            target:punch(self.object, 1.0, {
                full_punch_interval = 1.0,
                damage_groups = {fleshy = 2},
            })
            self.timer = 0
            core.log("action", "Mob attacked player!")
        end
    end,
})
```

### B. 如何修改現有 AI
若要修改現有 Mod 的 AI，應重點尋找 `on_step` 內的以下邏輯：
- **速度控制**：修改 `set_velocity` 的數值。
- **偵測距離**：修改 `vector.distance` 的判斷門檻。
- **尋路優化**：若 AI 常卡住，加入 `core.find_path` 以繞過障礙：
```lua
-- 進階尋路範例
local path = core.find_path(pos, tpos, 10, 1, 2, "A*")
if path and #path > 1 then
    local next_node = path[2] -- 前往路徑的下一個點
    local dir = vector.direction(pos, next_node)
    -- ... 移動邏輯
end
```

## 4. 驗證方式
1. 生成生物：`/spawnentity magic_stuff:magic_mob`。
2. 測試追蹤：玩家走動，確認生物是否轉向並跟隨。
3. 測試攻擊：靠近生物，確認玩家是否會受傷且有攻擊冷卻效果。
4. 測試障礙物：在中間放牆，確認 AI 行為（若未加尋路則會頂牆，加了則會繞道）。
