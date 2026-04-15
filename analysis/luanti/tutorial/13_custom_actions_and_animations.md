# 開發教學 13：如何自定義動作與同步動畫

## 目標
本教學將引導你實作一個「施法動作」。當玩家使用特定物品時，會執行以下動作：
1. 玩家播放「舉手」動畫。
2. 所有人都能看到這個施法動作。
3. 在動作結束後觸發魔法效果。

## 1. 前置知識
- 了解模型動畫幀區段 (Frames)。
- 了解 `set_animation` 函數。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (搜尋 `set_animation`)。
- **C++ 同步邏輯**：`src/network/serverpackethandler.cpp` (搜尋 `TOSERVER_INTERACT`)。

## 3. 實作步驟

### A. 準備帶有動畫的模型
確保你的 `character.b3d` 包含一個施法動畫區段，例如：
- 幀 1-40: Idle
- 幀 41-80: Walking
- 幀 81-120: Casting (我們要用的區段)

### B. 定義施法物品與動作
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_tool("magic_stuff:magic_wand", {
    description = "Magic Wand",
    inventory_image = "magic_wand.png",
    
    on_use = function(itemstack, user, pointed_thing)
        local player_name = user:get_player_name()
        
        -- 1. 同步播放施法動畫 (幀 81-120，速度 30FPS，不循環)
        user:set_animation({x=81, y=120}, 30, 0, false)
        
        -- 2. 為了防止動作被立即打斷，我們可以在 Lua 層加一個延遲鎖定
        -- 這裡示範 1.3 秒後執行魔法邏輯 (40幀 / 30FPS ≈ 1.33s)
        core.after(1.3, function()
            -- 魔法邏輯：例如在指到的地方產生火球
            if pointed_thing.type == "node" then
                local p = pointed_thing.above
                core.add_entity(p, "magic_stuff:fireball")
            end
            
            -- 3. 恢復 Idle 動畫
            user:set_animation({x=1, y=40}, 30, 0, true)
        end)
        
        return itemstack
    end,
})
```

### C. 處理動作衝突
預設情況下，玩家移動時會自動播放 Walking 動畫，這會打斷我們的 Casting 動畫。若要解決此問題：
- 檢查 `set_animation_frame_speed` 或是使用較複雜的 Mod 如 `player_api` (Minetest Game 內建)。
- 簡單做法：在施法期間短暫降低玩家移動速度：
```lua
user:set_physics_override({speed = 0.5})
core.after(1.3, function() user:set_physics_override({speed = 1.0}) end)
```

## 4. 驗證方式
1. 進入遊戲，拿取 `magic_stuff:magic_wand`。
2. 切換至第三人稱視角 (`F7`)。
3. 點擊左鍵使用法杖。
4. **觀察**：確認角色是否正確執行舉手施法動作，動作結束後才產生火球，且動作結束後正確恢復為 Idle 狀態。
5. **多人測試**：讓另一位玩家看著你施法，確認他看到的動畫與你同步。
