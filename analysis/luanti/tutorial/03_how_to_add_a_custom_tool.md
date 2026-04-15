# 開發教學 3：如何新增自定義工具 (Tools)

## 目標
本教學將引導你新增一個自定義工具（如「魔法稿子」），並設定其針對不同材質的挖掘效率。

## 1. 前置知識
- 了解 `tool_capabilities`：這是定義工具性能的核心屬性。
- 了解 `cracky`, `choppy`, `snappy` 等常見的方塊群組。

## 2. 原始碼導航 (核心參考)
- **實體定義**：`games/devtest/mods/basetools/init.lua` (行號 36, `tool_capabilities`)。
- **C++ 底層邏輯**：`src/tool.cpp` (處理挖掘速度計算)。

## 3. 實作步驟

### A. 註冊工具
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_tool("magic_stuff:magic_pickaxe", {
    description = "Magic Pickaxe",
    inventory_image = "magic_pickaxe.png",
    tool_capabilities = {
        full_punch_interval = 1.0, -- 攻擊冷卻時間（秒）
        max_drop_level = 3,       -- 能挖掘的最高方塊等級
        groupcaps = {
            -- 定義對 "cracky" (石質) 群組的挖掘能力
            cracky = {
                times = {[1]=2.0, [2]=1.0, [3]=0.5}, -- 等級 1,2,3 的挖掘耗時
                uses = 20,                          -- 總耐久度 (可挖掘次數)
                maxlevel = 3,                       -- 可挖掘的最高方塊等級
            },
        },
        damage_groups = {fleshy = 5}, -- 對生物造成的傷害
    },
})
```

## 4. 驗證方式
1. 使用 `/giveme magic_stuff:magic_pickaxe` 獲取工具。
2. 挖掘石質方塊：確認挖掘速度是否符合 `times` 的設定。
3. 檢查耐久度：挖掘 20 次後確認工具是否損壞。
