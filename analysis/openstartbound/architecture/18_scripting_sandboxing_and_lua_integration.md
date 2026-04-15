# 模塊分析：18_scripting_sandboxing_and_lua_integration (腳本沙箱化與 Lua 集成)

OpenStarbound 使用 Lua 5.2 作為其主要的邏輯擴展語言。為了確保數百個 Mod 腳本能並行運行且互不干擾，引擎實現了一套嚴密的沙箱化機制。

## 1. 環境隔離：LuaContext 與 _ENV
在 Lua 5.2 中，全局變量存放在 `_ENV` 表中。OpenStarbound 利用這一特性實現了實體級別的隔離：
- **獨立全局表：** 每個實體（如 `Monster`, `Npc`）都有自己獨立的 `LuaContext`。這意味著一個腳本中定義的全局變量不會出現在另一個腳本中。
- **共享只讀庫：** 所有 Context 共享一組基礎的、經過挑選的標準庫（如 `math`, `table`, `string`），但這些庫在 Context 內是不可修改的。

## 2. 標準庫限制 (Standard Library Sandboxing)
為了安全性，引擎禁用了可能威脅系統安全的標準功能：
- **禁用功能：** `os.execute`, `os.remove`, `io.*`, `debug.*`, `package.loadlib` 等。
- **自定義加載器 (RequireFunction)：** `setRequireFunction` 允許 C++ 接管 Lua 的 `require` 調用。腳本只能加載來自 `Assets` 系統（即虛擬檔案系統）中的 `.lua` 文件，無法訪問宿主機的真實硬碟。

## 3. 強類型 C++ 綁定 (Template-Based Bindings)
引擎在 `StarLua.hpp` 中實現了一套極其強大的 C++ 綁定層：
- **自動轉換 (LuaConverter)：** 通過模板特化，系統能自動處理 `Json`, `String`, `EntityId`, `Vec2F` 等類型在 C++ 與 Lua 之間的轉換。
- **異常捕獲：** 當 Lua 腳本調用 C++ 函數出錯時，C++ 會捕獲 `LuaException` 並將錯誤信息（包含 Lua 調用棧）導出至日誌，而不會導致整個遊戲進程崩潰。
- **回調註冊 (LuaCallbacks)：** C++ 物件通過註冊一組具名的回調函數（如 `monster.setAggressive`）來暴露接口。這些回調在 Lua 端表現為普通的函數對象。

## 4. 執行控制與資源限制
為了防止惡意或低效腳本導致遊戲卡死，引擎提供了執行監視機制：
- **指令限制 (Instruction Limit)：** `LuaInstructionLimitReached` 異常會在腳本執行超過預設的字節碼指令數時觸發，強制中斷腳本執行。
- **遞歸限制 (Recursion Limit)：** 防止腳本因無限遞歸導致 C++ 棧溢出。
- **內存監控：** 通過自定義的 Lua 內存分配器，引擎可以監控並限制單個腳本上下文佔用的內存總量。

## 5. 數據橋接：JSON 與 Lua Table
由於遊戲大量使用 JSON 存儲配置，`StarLua.cpp` 提供了高效的 JSON 與 Lua Table 互轉功能：
- **深度序列化：** `LuaConverter<Json>::from` 支持將複雜的嵌套 JSON 對象直接轉化為 Lua Table，反之亦然。
- **輕量級引用：** 通過 `LuaReference` 管理 Lua 對象的生命週期，防止在 C++ 層發生內存洩漏。

## 6. 腳本熱重載支持
得益於 `Root` 對 `Assets` 的監聽，當腳本文件發生變化時，對應的 `LuaContext` 可以被銷毀並重新創建，實現邏輯的實時更新而不需重新啟動遊戲。
