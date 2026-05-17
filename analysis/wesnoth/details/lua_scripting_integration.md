# Wesnoth 技術專題 - Lua 腳本整合與擴展機制剖析

## 1. Lua 核心架構 (Lua Kernels)
Wesnoth 並非只有一個單一的 Lua 環境，而是根據用途劃分為多個「內核 (Kernels)」：
- **`game_lua_kernel`**: 處理遊戲過程中的邏輯（事件、AI、場景腳本）。
- **`mapgen_lua_kernel`**: 用於地圖生成算法。
- **`application_lua_kernel`**: 用於非遊戲過程的應用程序邏輯。

## 2. C++/Lua 橋接技術
為了讓 Lua 能夠操作 C++ 定義的複雜對象，Wesnoth 採用了以下技術：

### Userdata 與 Metatables
- **WML 映射 (`vconfig`)**: 通過 `register_vconfig_metatable`，將 C++ 的 `config` 對象映射為 Lua 表格。Lua 腳本可以像操作普通表格一樣讀寫 WML 數據。
- **單位與團隊映射**: `lua_unit.cpp` 與 `lua_team.cpp` 將遊戲實體暴露給 Lua，並提供了一系列 C++ 實作的方法（如 `unit:advance`, `team:add_village`）。

### 安全性與資源管理
- **`scoped_lua_argument`**: 使用 RAII 模式管理 Lua 棧 (Stack)，自動處理 `lua_pop`，防止在複雜的 C++ 調用流程中發生棧溢出。
- **異常處理**: 將 Lua 錯誤轉換為 C++ 異常，確保遊戲在腳本錯誤時不會直接崩潰，而是能優雅地報告錯誤。

## 3. Lua 在遊戲中的角色
- **自定義事件 (WML Events)**: 可以在 WML 中使用 `[lua]` 標籤執行一段 Lua 程式碼。
- **AI 擴展**: 開發者可以編寫全 Lua 的 Candidate Actions，並整合進 RCA 框架。
- **UI (GUI2)**: 新一代的 UI 系統大量依賴 Lua 進行數據綁定與動態更新。

## 4. 關鍵類別參考
- `src/scripting/lua_kernel_base.cpp`: 基礎 Lua 環境管理。
- `src/scripting/game_lua_kernel.cpp`: 遊戲邏輯核心。
- `src/scripting/lua_wml.cpp`: WML 與 Lua 的數據轉換橋樑。
- `src/scripting/lua_common.hpp`: 包含常用的 Lua API 封裝。

---
*最後更新: 2026-05-17*
