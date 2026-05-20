# 教學：如何在 Gemini CLI 中新增一個工具 (Target-oriented Tutorial)

本教學將引導你如何在 Gemini CLI 的 `core` 套件中新增一個自訂工具。

## 1. 步驟一：定義工具參數與聲明
在 `packages/core/src/tools/definitions/` 下尋找適合的類別（例如 `coreTools.ts`），或建立新的定義檔。

```typescript
// 定義參數介面
export interface MyToolParams {
  name: string;
  count?: number;
}

// 在工具聲明清單中加入新工具
export const MY_TOOL_DEFINITION = {
  name: 'my_tool',
  description: '這是一個示範工具，會做一些有趣的事情。',
  parameters: {
    type: 'object',
    properties: {
      name: { type: 'string', description: '對象名稱' },
      count: { type: 'number', description: '執行次數' },
    },
    required: ['name'],
  },
};
```

## 2. 步驟二：建立工具實作
在 `packages/core/src/tools/` 目錄下建立 `my-tool.ts`。

```typescript
import { BaseToolInvocation, type ToolResult } from './tools.js';
import { MY_TOOL_NAME } from './tool-names.js';

export class MyToolInvocation extends BaseToolInvocation<MyToolParams, ToolResult> {
  getDescription(): string {
    return `執行 MyTool，對象為 ${this.params.name}`;
  }

  async execute(): Promise<ToolResult> {
    try {
      // 實作你的工具邏輯
      const result = `Hello, ${this.params.name}!`;
      return { output: result };
    } catch (error) {
      return { output: `執行失敗: ${error.message}`, isError: true };
    }
  }
}
```

## 3. 步驟三：註冊工具
在 `packages/core/src/tools/tool-registry.ts` 中註冊你的工具類別。

```typescript
// 在 ToolRegistry 中對應的地方加入
case MY_TOOL_NAME:
  return new MyToolInvocation(context, params, messageBus);
```

## 4. 步驟四：更新提示詞
確保工具在系統提示詞中被提及。通常 `core` 工具會自動包含在 `snippets.ts` 的工具清單中。

## 5. 步驟五：編寫測試
為你的工具編寫 Vitest 測試，確保邏輯正確。

```typescript
// packages/core/src/tools/my-tool.test.ts
import { describe, it, expect } from 'vitest';
import { MyToolInvocation } from './my-tool.js';

describe('MyTool', () => {
  it('應該正確回傳問候語', async () => {
    const invocation = new MyToolInvocation({...}, { name: 'Gemini' }, {...});
    const result = await invocation.execute();
    expect(result.output).toContain('Hello, Gemini');
  });
});
```

## 6. 驗證
執行 `npm test -w @google/gemini-cli-core -- src/tools/my-tool.test.ts` 來驗證。
