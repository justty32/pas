# 02 - Lua 整合：引擎接管與 Hook 系統

VCMI 整合了 LuaJIT，並通過 `scripting/lua/` 模組將 C++ 物件安全地暴露給腳本環境。

## 1. 腳本的啟動與環境 (`LuaScriptingContext`)

腳本通常放在 Mod 的 `scripts/` 資料夾中。
- **作用域**: 腳本可以運行在伺服器端（邏輯）或客戶端（UI/渲染）。
- **權限**: 伺服器端腳本對 `CGameState` 有廣泛的讀取權限。

## 2. 核心 Hook 機制

VCMI 使用事件回調系統。主要的 API 位於 `scripting/lua/api/`：

```lua
-- 範例：監聽英雄進入特定區域
function onHeroVisit(hero, object)
    if object.type == "treasure_chest" then
        print("Hero " .. hero.name .. " found a chest!")
        -- 直接修改狀態
        hero.experience = hero.experience + 1000
    end
end

-- 註冊事件
VCMI.registerEvent("onHeroVisit", onHeroVisit)
```

## 3. C++ 與 Lua 的封裝器 (`LuaWrapper.h`)

作為資深開發者，你會對 `LuaCallWrapper.h` 感興趣。它使用了模板元編程來自動處理 C++ 類型與 Lua 堆疊之間的轉換，支持：
- 基本類型 (int, double, string)
- VCMI 特有的物件指標 (`CGObjectInstance*`)
- 容器類型 (`std::vector`, `std::map`)

## 4. 序列化與狀態持久化

這是 VCMI 腳本系統最精妙的部分：
- 當玩家存檔時，Lua 虛擬機中的 **全域變數**（只要它們是可序列化類型）會被一併存入 `.vcmi` 存檔。
- `LuaReference.cpp` 負責管理這些跨 C++/Lua 的參考計數，防止記憶體洩漏。

## 5. 高效開發建議

- **使用 `VCMI.log`**: 腳本內日誌會直接輸出到引擎的 `VCMI_Log.txt`，並根據 `logging/` 設定進行分級。
- **避免密集計算**: 雖然 LuaJIT 很快，但涉及全圖掃描等操作時，建議在 C++ 中實現核心邏輯，僅將策略交給 Lua。
- **閱讀 `scripting/lua/api/Registry.cpp`**: 這是理解 Lua 可調用哪些 C++ 功能的最佳地圖。

---
**下一章**: [`03-cpp-core-modification.md`](03-cpp-core-modification.md) - 深入 Bonus 系統與核心修改。
