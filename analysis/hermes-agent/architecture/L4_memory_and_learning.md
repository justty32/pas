# hermes-agent 架構分析 - Level 4: 記憶與學習機制

## 1. 記憶管理系統 (Memory Management)
`hermes-agent` 的記憶系統不僅是簡單的資料儲存，而是一個與對話流深度整合的架構，由 `agent/memory_manager.py` 統一管理。

### 核心機制：
- **記憶提供者 (Memory Providers)**: 支援多種後端，但同一時間僅允許一個外部外掛提供者，以避免 Schema 膨脹或記憶衝突。
- **預取與同步 (Prefetch & Sync)**: 
    - **對話前**: 根據使用者目前的訊息「預取」相關記憶片段。
    - **對話後**: 將整段對話（包含模型的回應）「同步」回記憶庫。
- **上下文隔離 (Context Fencing)**: 使用 `<memory-context>` 標籤將記憶片段包裹起來。這能讓 LLM 明確區分哪些是「回憶」內容，而非使用者的「新指令」。
- **流式清洗 (Streaming Scrubber)**: `StreamingContextScrubber` 會在模型回應流式輸出時，即時過濾掉標籤內的內容，確保終端使用者不會看到冗長的記憶注入過程。

## 2. 會話壓縮 (Conversation Compression)
當對話長度接近模型的上下文極限（Context Window）時，`agent/conversation_compression.py` 會介入。

### 壓縮流程：
1. **觸發**: 當 Token 數超過設定閾值（如 Window 的 80%）。
2. **總結**: 呼叫輔助模型（Auxiliary Model）對目前對話進行精煉總結。
3. **會話輪轉**: 存檔目前的 SQLite 會話，更新 `session_id`，並將總結作為新會話的起點。
4. **通知系統**: 通知所有記憶提供者與外掛，會話已發生壓縮，同步更新其內部狀態。

## 3. 自我學習與維護 (Curator & Learning Loop)
`agent/curator.py` 是實現「自我改進」的核心。它扮演一個後台管家的角色，負責維護 Agent 產出的資產。

### Curator 運作方式：
- **閒置觸發**: 為了不干擾使用者，Curator 僅在系統閒置且距離上次執行超過一定時間（如 7 天）時啟動。
- **輔助 Agent 代理**: Curator 會分支出一個獨立的 AIAgent（Forked Agent），專門執行審查任務。
- **技能維護 (Skill Maintenance)**: 
    - **自動遷移**: 根據技能的活動時間點，自動將其標記為「活躍」、「陳舊」或「封存」。
    - **優化與合併**: 它可以建議將多個細碎的技能合併，或針對常出錯的技能產出 Patch（修補程式）。
- **非侵入性**: 它使用輔助模型 API，不影響主會話的提示詞快取或 Token 消耗。
