# 開發教學 9：如何使用 Formspecs 建立自定義 UI

## 目標
本教學將引導你建立一個簡單的「魔法商店」介面。玩家可以輸入數量，點擊按鈕後由 Mod 接收並處理邏輯。

## 1. 前置知識
- 了解 Formspec 的字串語法 (DSL)。
- 了解 `minetest.show_formspec` 函數。
- 了解回呼函數 `minetest.register_on_player_receive_fields`。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (搜尋 `Formspec`)。
- **解析邏輯**：`src/gui/guiFormSpecMenu.cpp` (行號 974, `parseButton`)。
- **實作範例**：`builtin/mainmenu/init.lua` (雖然是主選單，但邏輯雷同)。

## 3. 實作步驟

### A. 定義 Formspec 字串
我們將建立一個 5x4 大小的視窗：
```lua
local function show_magic_shop(player_name)
    local formspec = 
        "size[5,4]" ..
        "label[1,0.5;--- Magic Dust Shop ---]" ..
        "field[1,1.5;3,1;amount_field;Enter Amount;1]" .. -- 輸入框
        "button[1,2.5;3,1;buy_button;Purchase]" ..        -- 購買按鈕
        "button_exit[4,0.5;1,0.5;close;X]"               -- 關閉按鈕
        
    core.show_formspec(player_name, "magic_stuff:shop", formspec)
end
```

### B. 處理玩家互動 (Callbacks)
當玩家點擊按鈕或按下 Enter 時，Lua 會接收到數據。
```lua
core.register_on_player_receive_fields(function(player, formname, fields)
    -- 1. 確認是來自我們的商店介面
    if formname ~= "magic_stuff:shop" then
        return false -- 傳遞給其他 Mod 處理
    end

    -- 2. 處理點擊事件
    if fields.buy_button then
        local amount = tonumber(fields.amount_field) or 0
        local player_name = player:get_player_name()
        
        if amount > 0 then
            core.chat_send_player(player_name, "You purchased " .. amount .. " Magic Dust!")
            -- 這裡可以加入扣除金幣或給予物品的邏輯
        else
            core.chat_send_player(player_name, "Invalid amount!")
        end
    end

    -- 3. 處理關閉 (若按鈕是 button_exit 則 fields.quit 會為 true)
    if fields.quit then
        core.log("action", player:get_player_name() .. " closed the shop.")
    end

    return true -- 攔截事件，不再傳遞
end)
```

### C. 觸發介面顯示
你可以透過指令或點擊某個方塊來顯示此介面：
```lua
core.register_chatcommand("shop", {
    func = function(name)
        show_magic_shop(name)
    end,
})
```

## 4. 驗證方式
1. 進入遊戲後輸入 `/shop`。
2. 檢查：確認是否出現標題為 "Magic Dust Shop" 的視窗。
3. 互動：在輸入框輸入 "10"，點擊 "Purchase"。
4. 確認：聊天室是否顯示 "You purchased 10 Magic Dust!"。
5. 關閉：點擊 "X" 或按 Esc，確認視窗是否正常關閉。
