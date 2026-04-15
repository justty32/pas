# 事件與任務系統：動態敘事的雙軌制 (Incidents & Quests)

RimWorld 使用兩套互補的系統來創造隨機故事。

## 1. 事件系統 (Incidents) - 隨機與單次
事件是敘事者直接拋出的單元動作。
*   **數據與邏輯分離**: `IncidentDef` 定義頻率，`IncidentWorker` 執行代碼。
*   **點數驅動**: 許多事件（如襲擊）會讀取當前地圖的 `points` 來決定規模。
*   **調度器**: `Storyteller` 與其組件 `StorytellerComp` 決定「何時」發生事件。

## 2. 任務系統 (Quests) - 腳本與持久化
任務是比事件更複雜的長期目標。
*   **腳本化**: 使用 `QuestDef` 定義。它由多個 `QuestNode` 組成的樹狀邏輯驅動。
*   **信號通訊 (Signals)**: 任務內部的節點透過「信號」進行非同步通信（例如：「當目標抵達時」發出信號 -> 「啟動計時器」）。
*   **數據容器 (Slate)**: 存儲任務生成的具體參數，供後續節點引用。

## 3. 核心類別
*   **`IncidentWorker`**: 重寫 `TryExecuteWorker` 來實作你的事件邏輯。
*   **`QuestGen`**: 生成任務的靜態入口。
*   **`QuestManager`**: 管理所有進行中與已結束的任務。

## 4. Mod 開發建議
*   **新增簡單事件**: 寫一個繼承自 `IncidentWorker` 的 C# 並在 XML 中定義 `IncidentDef`。
*   **製作複雜任務**: 推薦先研究原版的 `QuestScriptDef` (XML)，理解各個 `QuestNode` 的組合方式。
*   **動態攔截**: 透過 Harmony Patch 修改 `IncidentWorker.CanFireNow` 來在特定條件下禁用或強制觸發事件。

---
*由 Gemini CLI 分析 RimWorld.Incident 與 RimWorld.QuestGen 生成。*
