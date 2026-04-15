# 開發教學 2：如何新增自定義物品與合成配方

## 目標
本教學將引導你如何在 Luanti 中新增一個基礎物品（如「魔法粉末」），並定義其合成配方。

## 1. 前置知識
- 了解 `ItemStack` 的基本結構。
- 了解 Luanti 的三種主要合成方式：`normal` (網格), `cooking` (烹飪), `fuel` (燃料)。

## 2. 原始碼導航 (核心參考)
- **API 定義**：`doc/lua_api.md` (搜尋 `minetest.register_craft`)。
- **合成系統底層**：`src/craftdef.h` (行號 22, `enum CraftMethod`)。
- **實作範例**：`games/devtest/mods/basenodes/init.lua`。

## 3. 實作步驟

### A. 註冊基礎物品 (CraftItem)
在 `mods/magic_stuff/init.lua` 中加入：
```lua
-- 註冊物品（魔法粉末）
core.register_craftitem("magic_stuff:magic_dust", {
    description = "Magic Dust",
    inventory_image = "magic_dust.png", -- 貼圖檔案
    groups = {magic = 1},              -- 物品群組
})
```

### B. 定義合成配方 (Crafting)
在同一個檔案中定義如何合成這個物品：

#### 1. 普通網格合成 (3x3)
```lua
core.register_craft({
    output = "magic_stuff:magic_dust 4", -- 產出數量
    recipe = {
        {"magic_stuff:glowing_stone", "magic_stuff:glowing_stone", ""},
        {"magic_stuff:glowing_stone", "magic_stuff:glowing_stone", ""},
        {"", "", ""},
    }
})
```

#### 2. 熔爐烹飪 (Cooking)
```lua
core.register_craft({
    type = "cooking",
    output = "magic_stuff:magic_dust",
    recipe = "magic_stuff:glowing_stone",
    cooktime = 5, -- 烹飪所需時間（秒）
})
```

#### 3. 燃料定義 (Fuel)
```lua
core.register_craft({
    type = "fuel",
    recipe = "magic_stuff:magic_dust",
    burntime = 10, -- 燃燒時間（秒）
})
```

## 4. 驗證方式
1. **重啟遊戲**：確保 Mod 已重新載入。
2. **合成測試**：
    - 開啟背包中的合成網格。
    - 依照配方擺放「魔法石」，確認產出為「魔法粉末」。
3. **烹飪測試**：
    - 放置一個熔爐 (Furnace)。
    - 將「魔法石」放入上方格位，確認其能被燒成「魔法粉末」。
4. **燃料測試**：
    - 將「魔法粉末」放入熔爐下方格位，確認其能作為燃料燃燒 10 秒。
