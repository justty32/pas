# 開發教學 4：如何新增 Lua 實體 (Entities)

## 目標
本教學將引導你新增一個簡單的 Lua 實體（一個會上下浮動的魔法球）。

## 1. 前置知識
- 實體 (Entity) 與方塊 (Node) 不同，它不佔據固定的地圖格點，可以自由移動。
- 實體由 `LuaEntitySAO` (伺服器端) 與 `GenericCAO` (客戶端) 組成。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (搜尋 `core.register_entity`)。
- **實作範例**：`games/devtest/mods/testentities/visuals.lua` (行號 3, `core.register_entity`)。

## 3. 實作步驟

### A. 註冊實體
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_entity("magic_stuff:floating_orb", {
    initial_properties = {
        visual = "sprite",         -- 視覺類型：二維貼圖
        textures = {"magic_orb.png"}, -- 貼圖檔案
        visual_size = {x=1, y=1},
        collisionbox = {-0.2, -0.2, -0.2, 0.2, 0.2, 0.2},
        physical = false,          -- 是否受物理碰撞影響
    },
    
    -- 初始化變數
    timer = 0,

    -- 每幀更新 (Server Side)
    on_step = function(self, dtime)
        self.timer = self.timer + dtime
        local pos = self.object:get_pos()
        -- 讓實體上下浮動 (Sin 波)
        local new_y = pos.y + math.sin(self.timer * 2) * 0.02
        self.object:set_pos({x=pos.x, y=new_y, z=pos.z})
    end,

    -- 被攻擊時的回呼
    on_punch = function(self, puncher)
        core.log("action", "Magic orb was punched!")
        self.object:remove() -- 被打一下就消失
    end,
})
```

## 4. 驗證方式
1. 使用指令 `/spawnentity magic_stuff:floating_orb` 生成實體。
2. 觀察：確認球體是否在空中緩慢浮動。
3. 互動：左鍵敲擊球體，確認其是否消失。
