# 開發教學 5：如何使用環境自動更新 (ABM)

## 目標
本教學將實作一個「魔法腐蝕」機制：讓附近的石頭 (Stone) 隨機轉化為你自定義的「魔法石」。

## 1. 前置知識
- **ABM (Active Block Modifier)**：這是一種週期性掃描全域區塊並對特定方塊執行操作的機制。
- **效能考量**：ABM 的 `interval` 與 `chance` 應謹慎設定，避免伺服器負擔過重。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (搜尋 `minetest.register_abm`)。
- **C++ 實作**：`src/serverenvironment.cpp` (ABM 的執行調度邏輯)。

## 3. 實作步驟

### A. 註冊 ABM
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_abm({
    label = "Magic Corruption",         -- 用於偵錯的標籤
    nodenames = {"basenodes:stone"},    -- 目標方塊
    neighbors = {"magic_stuff:glowing_stone"}, -- 必須鄰近此方塊才會觸發
    interval = 5.0,                    -- 每 5 秒執行一次檢查
    chance = 10,                       -- 1/10 的機率觸發
    
    action = function(pos, node, active_object_count, active_object_count_wider)
        -- 執行轉化
        core.set_node(pos, {name = "magic_stuff:glowing_stone"})
        -- 產生粒子特效
        core.add_particlespawner({
            amount = 10,
            time = 1,
            minpos = pos, maxpos = pos,
            minvel = {x=-1, y=1, z=-1}, maxvel = {x=1, y=2, z=1},
            texture = "magic_dust.png",
        })
    end,
})
```

## 4. 驗證方式
1. 放置一個「魔法石」在普通石頭旁邊。
2. 等待一段時間：確認周圍的石頭是否隨機轉化為魔法石。
3. 觀察粒子：轉化發生時是否伴隨正確的粒子效果。
