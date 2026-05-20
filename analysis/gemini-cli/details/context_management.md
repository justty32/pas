# Gemini CLI 上下文管理與壓縮機制 (Level 5 分析)

## 1. 挑戰：長上下文管理
隨著對話進行，Token 數量會迅速增加。Gemini CLI 必須在保持核心上下文的同時，避免超出模型限制並降低成本。

## 2. 聊天壓縮服務 (`ChatCompressionService`)
當 Token 數量超過閾值（預設為模型限制的 50%）時，會觸發壓縮流程：
- **分割點尋找 (`findCompressSplitPoint`)**: 尋找安全的分割位置，通常會保留最後 30% 的訊息作為即時上下文。
- **反向 Token 預算策略**: 
  - 優先保留最新的訊息。
  - 對於較舊的工具輸出（如大型 grep 或檔案內容），若超出預算（50,000 tokens），會將其內容截斷並儲存到暫存檔。
  - 被截斷的內容在對話中會被替換為指向暫存檔的說明，AI 仍知道資訊存在，但不再佔用上下文空間。

## 3. 工具輸出Distillation (`ToolDistillationService`)
針對某些產生大量重複資訊的工具，CLI 會進行「蒸餾」處理，提煉關鍵資訊，捨棄冗餘細節，從而極大化 Token 使用效率。

## 4. 階層式記憶 (Hierarchical Memory)
記憶不只是字串，而是結構化的：
- **Inbox**: 新發現的事實首先進入收件匣。
- **Consolidation**: 定期將 Inbox 中的事實整理進 `MEMORY.md` 或全域配置中。
- **Scoped Access**: 子代理僅能存取與其任務相關的記憶片段。
