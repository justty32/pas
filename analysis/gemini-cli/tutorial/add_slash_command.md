# 教學：如何在 Gemini CLI 中新增斜線指令 (Slash Command)

本教學將引導你如何新增一個自訂的斜線指令（例如 `/loop`）。

## 1. 步驟一：建立指令實作檔
在 `packages/cli/src/ui/commands/` 目錄下建立新的指令檔案，例如 `loopCommand.ts`。

```typescript
import { CommandKind, type SlashCommand } from './types.js';
import { MessageType } from '../types.js';

export const loopCommand: SlashCommand = {
  name: 'loop',
  description: '進入或切換循環模式',
  kind: CommandKind.BUILT_IN,
  autoExecute: true, // 如果設為 true，輸入 /loop 後會立即執行 action
  action: async (context, args) => {
    // 取得目前的配置或服務
    const config = context.services.agentContext?.config;
    
    // 範例邏輯：切換 YOLO (Autonomous) 模式
    if (config) {
      const isYolo = config.getApprovalMode() === 'yolo';
      // 注意：這裡需要呼叫實際的配置修改 API，以下為虛擬碼
      // config.setApprovalMode(isYolo ? 'default' : 'yolo');
      
      return {
        type: 'message',
        messageType: 'info',
        content: `循環模式已${isYolo ? '關閉' : '開啟'}。`,
      };
    }

    return {
      type: 'message',
      messageType: 'error',
      content: '無法取得系統配置。',
    };
  },
};
```

## 2. 步驟二：在 BuiltinCommandLoader 中註冊
編輯 `packages/cli/src/services/BuiltinCommandLoader.ts`，將新指令加入載入清單。

1. **匯入指令**：
   ```typescript
   import { loopCommand } from '../ui/commands/loopCommand.js';
   ```

2. **加入 `allDefinitions` 陣列**：
   ```typescript
   const allDefinitions: Array<SlashCommand | null> = [
     aboutCommand,
     // ...
     loopCommand, // 加入這裡
     // ...
   ];
   ```

## 3. 步驟三：(選配) 定義 UI 回饋
如果指令需要特殊的 UI 渲染（而不僅僅是訊息），你可以在 `packages/cli/src/ui/types.ts` 中定義新的 `MessageType` 或 `HistoryItem` 類型，並在 `AppContainer.tsx` 中處理它。

## 4. 指令屬性說明
- **`name`**: 指令名稱（不含斜線）。
- **`altNames`**: 別名清單（例如 `['l', 'repeat']`）。
- **`description`**: 在 `/help` 中顯示的說明。
- **`autoExecute`**: 
    - `true`: 使用者輸入 `/loop` 按下 Enter 後直接執行。
    - `false`: 使用者輸入 `/loop` 按下 Enter 後，指令會保留在輸入框中供進一步編輯（適用於需要複雜參數的指令）。
- **`takesArgs`**: 是否接受參數。如果設為 `false` 且使用者提供了參數，系統可能會嘗試回退到父指令。

## 5. 測試
1. 執行 `npm run build` 重新編譯。
2. 啟動 CLI 並輸入 `/loop` 驗證。
