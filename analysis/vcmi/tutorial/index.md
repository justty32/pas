# VCMI 引擎開發教程：給資深工程師

歡迎，同行。既然你已經在 C++/Lua 和遊戲開發領域深耕多年，這份教程將略過瑣碎的語法說明，直接從 **系統架構、擴展機制與效能併發** 出發，幫助你快速掌握 VCMI 1.7.3 的靈魂。

## 擴展 VCMI 的三支柱 (The Three Pillars)

要利用 VCMI 製作自己的遊戲或大幅修改原版邏輯，你主要會從以下三個層面介入：

1.  **數據驅動 (JSON Modding)**: 通過 JSON Schema 定義所有靜態資料（兵種、寶物、種族）。VCMI 具備強大的繼承與覆蓋機制。
2.  **腳本驅動 (Lua Hooking)**: 使用 LuaJIT 深度介入遊戲流程。VCMI 的 Lua API 不僅能處理 UI 事件，還能直接操控紅利系統 (`BonusSystem`) 與戰鬥邏輯。
3.  **核心驅動 (C++ Core)**: 若需新增底層網路協議 (`NetPack`)、重寫 AI 框架或擴展紅利類型，則需直接修改 `VCMI_lib` 並重新編譯。

## 教程導覽

1.  [`01-mod-architecture.md`](01-mod-architecture.md): **Mod 生命週期與數據繼承**。理解 `mod.json` 與 JSON Schema 驗證。
2.  [`02-lua-integration.md`](02-lua-integration.md): **高效 Lua 腳本開發**。探討 VCMI 的 Hook 系統、序列化支持與 C++ 封裝器。
3.  [`03-cpp-core-modification.md`](03-cpp-core-modification.md): **深入核心與 Bonus 系統**。解析引擎中最核心的加成圖（Bonus Tree）設計模式。
4.  [`04-workflow-and-debugging.md`](04-workflow-and-debugging.md): **開發工作流與效能優化**。解析併發策略、網路同步與調試指南。

## 快速啟動建議

- **查看現有 Mod**: VCMI 的 Mod 資料夾結構與引擎 `config/` 是一一對應的。
- **關注 `CGameState`**: 這是唯一的真理來源 (Source of Truth)，所有修改最終必須體現在這裡。
