# 開發教學 10：實作火球術與地雷陷阱

## 目標
本教學將引導你實作一套基礎的戰鬥組件：
1. **火球術**：一個具備發光特效、飛行軌跡且命中會爆炸的投射物。
2. **地雷陷阱**：一個隱藏在地面下，玩家踏上後會觸發特效並造成傷害的方塊。

## 1. 前置知識
- 了解 Lua 實體 (`register_entity`) 的基本操作。
- 了解粒子系統 (`add_particlespawner`)。
- 了解向量運算 (`vector.add`, `vector.multiply`)。

## 2. 實作步驟

### A. 實作火球投射物
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_entity("magic_stuff:fireball", {
    initial_properties = {
        visual = "sprite",
        textures = {"fireball.png"},
        visual_size = {x=0.5, y=0.5},
        physical = false, -- 我們手動處理碰撞以獲得更好的控制
        glow = 14,
    },

    timer = 0,

    on_step = function(self, dtime)
        self.timer = self.timer + dtime
        local pos = self.object:get_pos()
        
        -- 1. 產行飛行尾跡特效
        core.add_particlespawner({
            amount = 5,
            time = 0.1,
            minpos = pos, maxpos = pos,
            minvel = {x=-0.2, y=-0.2, z=-0.2}, maxvel = {x=0.2, y=0.2, z=0.2},
            texture = "magic_dust.png",
        })

        -- 2. 命中檢測 (方塊)
        local node = core.get_node(pos)
        if core.registered_nodes[node.name].walkable or self.timer > 5 then
            self:explode(pos)
            return
        end

        -- 3. 命中檢測 (實體/玩家)
        local objs = core.get_objects_inside_radius(pos, 1.0)
        for _, obj in ipairs(objs) do
            if obj ~= self.object then
                obj:punch(self.object, 1.0, {
                    full_punch_interval = 1.0,
                    damage_groups = {fleshy = 5},
                })
                self:explode(pos)
                break
            end
        end
    end,

    explode = function(self, pos)
        -- 產生爆炸特效
        core.add_particlespawner({
            amount = 50,
            time = 0.5,
            minpos = pos, maxpos = pos,
            minvel = {x=-5, y=-5, z=-5}, maxvel = {x=5, y=5, z=5},
            texture = "fire_particle.png",
        })
        -- 播放爆炸聲
        core.sound_play("explosion", {pos = pos, gain = 1.0})
        self.object:remove()
    end,
})
```

### B. 實作地雷陷阱 (區域觸發)
```lua
core.register_node("magic_stuff:landmine", {
    description = "Magic Landmine",
    tiles = {"landmine.png"},
    groups = {cracky = 3},
    
    -- 使用 ABM 進行偵測（或更即時的方法：在玩家 step 中偵測）
})

-- 實作陷阱觸發邏輯
core.register_abm({
    label = "Landmine Trigger",
    nodenames = {"magic_stuff:landmine"},
    interval = 1.0,
    chance = 1,
    action = function(pos)
        local objs = core.get_objects_inside_radius(pos, 1.5)
        for _, obj in ipairs(objs) do
            if obj:is_player() then
                -- 觸發效果
                core.set_node(pos, {name = "air"})
                core.add_particlespawner({
                    amount = 100,
                    time = 0.5,
                    minpos = pos, maxpos = pos,
                    texture = "fire_particle.png",
                })
                obj:set_hp(obj:get_hp() - 10)
                core.chat_send_player(obj:get_player_name(), "BOOM! You stepped on a mine!")
            end
        end
    end,
})
```

## 3. 驗證方式
1. **火球術**：使用指令 `/spawnentity magic_stuff:fireball` (或建立一個發射它的工具)。確認火球是否有尾跡，且撞牆或撞人會爆炸。
2. **地雷**：放置地雷，然後走過去。確認是否在 1 秒內觸發爆炸、消失並扣除生命值。
