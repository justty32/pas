# Gemini CLI 指令佇列機制深化分析 (Command Queuing)

## 1. 現狀分析
在目前的實作中，`useMessageQueue` 鉤子負責管理當 Agent 正在處理 (Responding) 時，使用者額外輸入的指令。

- **檔案路徑**: `packages/cli/src/ui/hooks/useMessageQueue.ts`
- **當前行為**: 當狀態回到 `Idle` 時，系統會使用 `messageQueue.join('\n\n')` 將所有排隊指令合併為一個字串，並呼叫一次 `submitQuery`。
- **影響**: Gemini 會收到一個包含多個指令的大段文字。雖然節省了 Token 開銷，但對於需要精確步驟執行的任務，可能會導致 Agent 忽略部分指令或邏輯混亂。

## 2. 深化方案：序列化執行 (Sequential Execution)
為了實現「一條接一條」執行，需將 `useMessageQueue` 的合併邏輯改為彈出 (Pop) 邏輯。

### 核心修改建議
修改 `packages/cli/src/ui/hooks/useMessageQueue.ts` 中的 `useEffect`：

```typescript
  // 序列化處理排隊訊息
  useEffect(() => {
    if (
      isConfigInitialized &&
      streamingState === StreamingState.Idle &&
      !isCompressing &&
      isMcpReady &&
      messageQueue.length > 0
    ) {
      // 1. 僅取出佇列中的第一條訊息
      const nextMessage = messageQueue[0];
      
      // 2. 更新狀態以移除該訊息
      setMessageQueue((prev) => prev.slice(1));
      
      // 3. 提交單一指令
      // 這會觸發新的 Responding 狀態，阻塞後續 useEffect 執行
      submitQuery(nextMessage);
    }
  }, [
    isConfigInitialized,
    streamingState,
    isMcpReady,
    messageQueue,
    submitQuery,
    isCompressing,
  ]);
```

## 3. 實作細節與考量

### A. 狀態同步
由於 `submitQuery` 是異步的且會立即修改 `streamingState`，序列化執行能確保在前一個指令的 `agent_end` 事件觸發後，下一個指令才被送出。這保證了 Gemini 的上下文 (History) 是按順序增長的。

### B. 視覺回饋
目前的 `QueuedMessageDisplay.tsx` 會顯示剩餘排隊的數量。改為序列化後，使用者會看到排隊數量逐一遞減，每一條指令都會產生獨立的「User Message」氣泡，視覺上更清晰。

### C. 設定項擴展 (可選)
為了兼顧效能與精確度，可以在 `settings.json` 中加入開關：

```json
{
  "ui": {
    "commandQueueMode": "sequential" // 或 "combined"
  }
}
```

在 `useMessageQueue` 中讀取此設定：
```typescript
const combinedMessage = queueMode === 'combined' 
  ? messageQueue.join('\n\n') 
  : messageQueue[0];
```

## 4. 預期效果
- **指令隔離**: 每個指令都有獨立的思考鏈與工具執行區塊。
- **錯誤中斷**: 如果排在前面的指令導致嚴重錯誤，使用者可以在後續指令被自動送出前手動中斷。
- **使用者體驗**: 更符合人類「對話」的直覺，即一次說一件事。
