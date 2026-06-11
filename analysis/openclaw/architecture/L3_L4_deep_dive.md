# Level 3: OpenClaw 執行管線與 Agent 驅動深度剖析

## 1. 訊息處理生命週期 (Message Lifecycle)

訊息從進入系統到產生回覆，經過以下關鍵路徑：

1.  **Gateway RPC (`chat.ts`)**:
    - 接收來自 Web/API 的 `chat.send` 請求。
    - 驗證參數、解析身分、鎖定 Agent 範圍。
2.  **Auto-reply Dispatcher (`dispatch.ts`)**:
    - **Foreground Reply Fence**: 建立「世代圍欄」，確保回覆按順序交付，並自動取消過時的生成任務。
    - **Hook Composition**: 執行全域鉤子，允許插件介入預處理。
3.  **Reply Pipeline (`get-reply.ts`)**:
    - **Context Augmentation**: 自動抓取網頁連結、執行 OCR/音訊轉錄。
    - **Model Selection**: 根據策略選擇最佳 LLM 供應商。
4.  **Agent Runner (`agent-runner.ts`)**:
    - **Preflight Compaction**: 在執行前檢查 Token 預算，必要時觸發 Checkpoint 壓縮。
    - **Execution Loop**: 呼叫嵌入式 Agent 或沙盒環境執行任務。
    - **Fallback Handler**: 當主模型失敗時，自動降級至備用模型。
5.  **Outbound Delivery**:
    - 將生成的 Chunk 透過 WebSocket 串流回客戶端。
    - **Commitment Extraction**: 自動提取 Agent 的承諾（如排程提醒）。

## 2. 核心技術深挖：前台回覆圍欄 (Generation Fencing)

為了在不穩定的網路環境中提供流暢體驗，OpenClaw 實作了 `ForegroundReplyFence`：
- **世代追蹤 (Generation Tracking)**：為每個 Request 分配遞增的 Generation ID。
- **競爭抑制**：如果系統正在處理一個更晚（較新）的 Request，則會主動中止當前正在進行的舊生成。
- **交付保證**：確保使用者看到的始終是針對其「最新意圖」的回覆，避免上下文錯亂。

## 3. 嵌入式執行與 Fallback 策略
- **`runAgentTurnWithFallback`**: 這是系統強韌性的關鍵。它定義了詳細的錯誤重試矩陣（Billing, Rate Limit, Context Overflow）。
- **沙盒隔離**: Agent 運行在受限的 `workspace` 中，透過 `EmbeddedAgentRunner` 管理文件訪問與工具執行安全。

---

# Level 4: 記憶系統與會話壓縮 (Compaction)

## 1. 檢查點機制 (Checkpointing)
不同於傳統的資料庫刪除，OpenClaw 採用實體文件快照：
- **Pre-compaction Snapshot**: 在壓縮前為轉錄文件 (`transcript.jsonl`) 建立副本。
- **無損回滾**: 若 LLM 總結失敗或導致邏輯損毀，系統可立即恢復至最後一個 Checkpoint。
- **容量治理**: 內建 `trimSessionCheckpoints` 邏輯，嚴格控制磁碟佔用（預設 128MB/會話）。

## 2. 記憶檢索 (Memory)
- **FTS5 整合**: 雖然是 Node.js 專案，但底層透過 SQLite 的 FTS5 進行高效的歷史訊息檢索。
- **Context Pruning**: 根據模型能力，動態移除過舊的工具執行細節，僅保留核心意圖摘要。
