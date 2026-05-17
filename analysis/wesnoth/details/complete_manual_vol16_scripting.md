# Wesnoth 技術全典：Lua 腳本核心直譯器 (第十六卷)

本卷解構 `src/scripting/` 目錄。這是連結底層 C++ 引擎與頂層 Lua 腳本的橋樑，也是 Wesnoth 高度 Mod 化的技術基石。

---

## 1. 核心內核：`game_lua_kernel.cpp` 與 `application_lua_kernel.cpp`

Wesnoth 採用了多核心 (Multi-kernel) 的 Lua 設計模式。這意味著不同的遊戲狀態擁有完全獨立的 Lua 虛擬機 (lua_State)，彼此之間的變數互不干擾。

### 1.1 `application_lua_kernel` (全域核心)
- **工程語義**：負責遊戲主選單、戰役選擇等非地圖狀態下的 Lua 執行。
- **執行緒管理 (`thread` class)**：
  - 封裝了 Lua 協程 (Coroutines)，支援非同步的腳本執行。
  - 透過 `load_script_from_file` 安全地載入 `.lua` 檔案並進行語法編譯檢查。

### 1.2 `game_lua_kernel` (遊戲邏輯核心)
這是最龐大、功能最完整的直譯器，專門處理地圖與戰鬥。
- **沙盒與安全性 (Sandboxing)**：
  - `game_lua_kernel` 會過濾掉危險的標準 Lua C API（如 `os.execute` 或底層檔案 I/O），確保下載的 Mod 不會執行惡意程式碼破壞玩家電腦。
- **介面註冊 (Interface Binding)**：
  - 此檔案中充滿了 `intf_get_unit`, `intf_set_variable`, `intf_fire_event` 等函數。
  - 這些函數是 C++ 提供給 Lua 的 **API Hooks**。當 Lua 呼叫 `wesnoth.get_units()` 時，實際上是穿越了虛擬機邊界，執行了 C++ 中的 `intf_get_units` 演算法，將 `unit_map` 中的 C++ 物件轉換為 Lua Table 並壓入棧 (Stack) 中。

---

## 2. 雙向綁定機制 (Two-way Binding)

### 2.1 C++ 呼叫 Lua
當 WML 解析到 `[lua]` 標籤時，`game_lua_kernel` 會透過 `luaL_loadstring` 將 WML 內的字串推入 Lua 虛擬機執行。

### 2.2 Lua 呼叫 WML 事件
- **`intf_fire_event(lua_State *L)`**: 
  - **工程解析**：允許 Lua 直接觸發一個 WML 事件。這打通了兩者的壁壘：一個純 Lua 寫成的 AI，可以透過呼叫此函數，觸發由 WML 寫成的劇情對話，實現跨語言的事件驅動。

### 2.3 狀態同步與序列化
- **持久化變數 (`intf_set_variable`)**: 
  - Lua 的局部變數無法存檔。因此 Wesnoth 提供了一套機制，允許 Lua 將資料寫入 WML 的 `$variables` 中。這些變數在 `game_state::write_config` 觸發時會被序列化到磁碟，保證了 Lua 腳本的狀態在讀檔後能完美復原。

---
*第十六卷解析完畢。腳本內核展示了如何安全、高效地在靜態編譯語言 (C++) 與動態腳本語言 (Lua) 之間建立數據與指令的高速公路。*
*最後更新: 2026-05-17*
