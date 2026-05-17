# Wesnoth 技術全典：WML 事件驅動引擎 (第十五卷)

本卷解構 `src/game_events/` 目錄下的所有檔案。The Battle for Wesnoth 是一個高度事件驅動 (Event-driven) 的遊戲，而這個目錄就是處理所有 `[event]` 腳本的核心引擎。

---

## 1. 檔案解析：事件泵與排程器 (`pump.cpp`, `manager.cpp`)

WML 事件不是透過輪詢 (Polling) 來執行的，而是透過嚴格的佇列與泵送機制。

### 1.1 `manager::pump()` (事件泵)
- **工程語義**：觸發並清空事件佇列的核心迴圈。
- **演算法細節**：
  - 遊戲中的其他系統（例如 `attack.cpp`）會將事件（如 `name=die`）推入佇列。
  - `pump()` 會從佇列中彈出事件，然後掃描所有已註冊的事件處理器 (`handlers`)。
  - **遞歸安全性**：一個事件的執行可能會觸發另一個事件（例如：單位死亡事件的腳本中又殺死了另一個單位）。`pump()` 實作了深度限制與堆疊管理，防止無限迴圈導致引擎堆疊溢位 (Stack Overflow)。

### 1.2 `game_events::manager` (全域事件註冊表)
- **事件匹配 (Event Matching)**：
  - 給定一個事件名稱（如 `moveto`），`manager` 會利用雜湊表快速檢索所有監聽該事件的 `handler`。
  - **空間過濾**：它不僅匹配名稱，還支援 `[filter]`（只在特定單位於特定地點觸發）。這種精確的條件判斷被延遲到事件觸發的瞬間才計算，極大地節省了 CPU 開銷。

---

## 2. 檔案解析：WML 行動與條件 (`action_wml.cpp`, `conditional_wml.cpp`)

當一個事件被觸發後，它內部包含的 WML 腳本需要被直譯與執行。

### 2.1 `action_wml.cpp`
- **工程語義**：定義所有 WML 動作指令（如 `[kill]`, `[message]`, `[gold]`）的 C++ 處理常式。
- **原子操作**：每一個指令都被封裝為獨立的函數。這些函數會直接對 `game_board` 或 `display` 下達修改指令。
- **撤銷相容性 (Undo Compatibility)**：若執行了包含 RNG（隨機數）或改變視野的動作，這些 `action_wml` 會自動呼叫 Undo 系統鎖定歷史紀錄。

### 2.2 `conditional_wml.cpp`
- **工程語義**：實作 WML 的布林邏輯 (Boolean Logic) 虛擬機。
- **演算法細節**：
  - 解析 `[if]`, `[then]`, `[else]`, `[while]` 等控制流結構。
  - 實作了 `[and]`, `[or]`, `[not]` 等邏輯閘。透過遞歸的 `evaluate_condition` 函數，能夠處理極度深層嵌套的邏輯樹。
  - **短路求值 (Short-circuit Evaluation)**：與現代編譯器一樣，如果在 `[or]` 的第一個條件為真，後續的複雜 `[filter]` 判斷將被跳過，優化執行效能。

---

## 3. 動態右鍵選單 (`menu_item.cpp`, `wmi_manager.cpp`)

- **工程語義**：處理 WML 中透過 `[set_menu_item]` 自定義的右鍵選單。
- **上下文感知 (Context-aware)**：選單項會根據滑鼠當前懸停的坐標 `loc`，實時計算 `[show_if]` 的條件，決定是否顯示在 UI 上。
