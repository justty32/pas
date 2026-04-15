# 開發教學 1：如何新增一個自定義方塊 (Node)

## 目標
本教學將引導你如何在 Luanti 中新增一個自定義方塊。我們將創建一個具有發光特性、特定碰撞箱且能被手挖掘的「魔法石」。

## 1. 前置知識
- 了解 Luanti 的 Mod 加載機制（每個 Mod 都有一個 `init.lua` 與 `mod.conf`）。
- 了解 `core` 命名空間是 Luanti API 的核心進入點。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (詳細參數說明)。
- **實作範例**：`games/devtest/mods/basenodes/init.lua` (行號 15, `core.register_node`)。
- **底層轉換**：`src/script/lua_api/l_item.cpp` (行號 566, `ModApiItem::l_register_item_raw`)。

## 3. 實作步驟

### A. 建立 Mod 目錄
在 `mods/` 資料夾下建立 `magic_stuff` 目錄。

### B. 撰寫 `mod.conf`
建立 `mods/magic_stuff/mod.conf`：
```ini
name = magic_stuff
description = Adds magical nodes and items.
author = dev
```

### C. 撰寫 `init.lua` 並註冊方塊
建立 `mods/magic_stuff/init.lua`：
```lua
-- 註冊方塊
core.register_node("magic_stuff:glowing_stone", {
    description = "Magic Glowing Stone", -- 顯示名稱
    tiles = {"magic_stone.png"},         -- 六面貼圖 (需放於 mods/magic_stuff/textures/)
    light_source = 14,                  -- 發光強度 (0-14)
    groups = {cracky = 3, oddly_breakable_by_hand = 1}, -- 挖掘屬性與類別
    sounds = core.node_sound_stone_defaults(),        -- 音效設定
    
    -- 進階屬性：當方塊被挖掘後掉落的物品
    drop = "magic_stuff:glowing_stone",
    
    -- 事件回呼 (Callback)
    on_place = function(itemstack, placer, pointed_thing)
        core.log("action", placer:get_player_name() .. " placed a magic stone!")
        return core.item_place(itemstack, placer, pointed_thing)
    end,
})
```

## 4. 驗證方式
1. **啟動遊戲**：執行 `bin/luanti`。
2. **啟用 Mod**：在世界設定中啟用 `magic_stuff` 模組。
3. **進入遊戲**：
    - 開啟創造模式 (Creative Mode) 或使用指令 `/giveme magic_stuff:glowing_stone`。
    - 放置方塊：觀察其是否發光且具備正確的貼圖。
    - 挖掘方塊：確認挖掘聲音正確，且掉落物正確。
4. **檢查日誌**：查看 `debug.txt` 或終端機，確認 `on_place` 的日誌是否有輸出。
