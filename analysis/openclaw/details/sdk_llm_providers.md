# OpenClaw Multi-provider LLM 抽象層深度剖析
## 從 SDK 建造者視角

> 核對於 2026-06-12，基於 `packages/llm-core/`、`packages/llm-runtime/`、`src/llm/` 實際原始碼。

---

## 1. Provider 抽象介面

### 1.1 核心型別體系

OpenClaw 的 LLM 抽象層以兩個 package 為中心：

- `packages/llm-core/` — 純型別契約，不依賴任何 provider SDK
- `packages/llm-runtime/` — 運行時 API 登錄表（registry）與轉發邏輯

**最頂層的 API 家族型別：**

```typescript
// packages/llm-core/src/types.ts:6-18
export type KnownApi =
  | "openai-completions"
  | "mistral-conversations"
  | "openai-responses"
  | "azure-openai-responses"
  | "openai-chatgpt-responses"
  | "anthropic-messages"
  | "bedrock-converse-stream"
  | "google-generative-ai"
  | "google-vertex";

export type Api = KnownApi | (string & {}); // 允許自訂 provider
```

**Model 描述符（provider 配置的核心）：**

```typescript
// packages/llm-core/src/types.ts:579-629
export interface Model<TApi extends Api = Api> {
  id: string;                     // provider 側的模型 id（如 "claude-opus-4-5"）
  name: string;                   // 人類可讀名稱
  api: TApi;                      // 決定使用哪個 provider adapter
  provider: Provider;             // 路由/診斷/設定查詢用 id（如 "anthropic"）
  baseUrl: string;                // API 基礎 URL
  reasoning: boolean;             // 是否支援 thinking 控制
  thinkingLevelMap?: ThinkingLevelMap; // 各 level 對應 provider 原生值
  input: ("text" | "image")[];    // 支援的輸入模態
  cost: {
    input: number;   // USD/百萬 token
    output: number;
    cacheRead: number;
    cacheWrite: number;
  };
  contextWindow: number;
  contextTokens?: number;         // 可選：運行時有效上限（不修改原始 contextWindow）
  maxTokens: number;
  params?: Record<string, unknown>; // provider plugin 專屬參數
  headers?: Record<string, string>;
  authHeader?: boolean;           // 用 Authorization: Bearer 而非 provider 專屬 header
  compat?: TApi extends "openai-completions"
    ? OpenAICompletionsCompat
    : TApi extends "openai-responses"
      ? OpenAIResponsesCompat
      : TApi extends "anthropic-messages"
        ? AnthropicMessagesCompat
        : never;
  mediaInput?: { image?: { maxBytes?; maxPixels?; maxSidePx?; preferredSidePx?; tokenMode? } };
}
```

**一個 provider 需要實作的最小介面：**

```typescript
// packages/llm-runtime/src/api-registry.ts:27-37
export interface ApiProvider<
  TApi extends Api = Api,
  TOptions extends StreamOptions = StreamOptions,
> {
  api: TApi;                                    // 對應的 API 家族 id
  stream: StreamFunction<TApi, TOptions>;       // 完整 options 的串流入口
  streamSimple: StreamFunction<TApi, SimpleStreamOptions>; // 簡化版串流入口
}
```

**StreamFunction 簽章：**

```typescript
// packages/llm-core/src/types.ts:201-208
export type StreamFunction<
  TApi extends Api = Api,
  TOptions extends StreamOptions = StreamOptions,
> = (
  model: Model<TApi>,
  context: Context,
  options?: TOptions,
) => AssistantMessageEventStreamContract;
// 契約：一定回傳串流，不能 throw；錯誤必須編碼進 stream 的 error 事件
```

**Context（對話上下文）：**

```typescript
// packages/llm-core/src/types.ts:352-356
export interface Context {
  systemPrompt?: string;
  messages: Message[];
  tools?: Tool[];
}
```

---

## 2. Streaming 統一處理

### 2.1 事件協定

所有 provider 最終輸出同一套 `AssistantMessageEvent` 聯集型別，消費方不需要感知底層 provider 差異：

```typescript
// packages/llm-core/src/types.ts:366-387
export type AssistantMessageEvent =
  | { type: "start"; partial: AssistantMessage }
  | { type: "text_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "text_delta"; contentIndex: number; delta: string; partial?: AssistantMessage }
  | { type: "text_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "thinking_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "thinking_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "thinking_end"; contentIndex: number; content: string; partial: AssistantMessage }
  | { type: "toolcall_start"; contentIndex: number; partial: AssistantMessage }
  | { type: "toolcall_delta"; contentIndex: number; delta: string; partial: AssistantMessage }
  | { type: "toolcall_end"; contentIndex: number; toolCall: ToolCall; partial: AssistantMessage }
  | { type: "done"; reason: "stop"|"length"|"toolUse"; message: AssistantMessage }
  | { type: "error"; reason: "aborted"|"error"; error: AssistantMessage };
```

### 2.2 EventStream 基礎建設

OpenClaw 自行實作非同步佇列，不用 Node.js 原生 Readable/Transform Stream，讓 provider 可以 `push()` 事件而消費方 `for await ... of` 迭代：

```typescript
// packages/llm-core/src/utils/event-stream.ts:9-96
export class EventStream<T, R = T> implements AsyncIterable<T> {
  push(event: T): void     // provider 呼叫
  end(result?: R): void    // provider 完成時呼叫
  result(): Promise<R>     // 等待最終 AssistantMessage
  [Symbol.asyncIterator]() // 消費方迭代
}

export class AssistantMessageEventStream
  extends EventStream<AssistantMessageEvent, AssistantMessage>
  implements AssistantMessageEventStreamContract
```

### 2.3 各家 SSE 差異的處理

**Anthropic SSE 解析器**（`src/agents/anthropic-transport-stream.ts:697-745`）：

- 自行解析 HTTP response body（`ReadableStream<Uint8Array>`）
- 逐行提取 `data:` 欄位，處理 `[DONE]` sentinel
- Anthropic 事件型別：`message_start` → `content_block_start` → `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`
- `content_block_delta` 有三種 `delta.type`：`text_delta`、`thinking_delta`、`input_json_delta`（tool call 參數）、`signature_delta`（thinking 簽名）

**stop_reason 映射範例（Anthropic）：**

```typescript
// src/agents/anthropic-transport-stream.ts:588-606
function mapStopReason(reason: string | undefined): string {
  switch (reason) {
    case "end_turn":   return "stop";
    case "max_tokens": return "length";
    case "tool_use":   return "toolUse";
    case "pause_turn": return "stop";
    case "refusal":
    case "sensitive":  return "error";
    case "stop_sequence": return "stop";
    default: throw new Error(`Unhandled stop reason: ${String(reason)}`);
  }
}
```

**Lazy loading 機制**（`src/llm/providers/register-builtins.ts:157-180`）：

provider 模組在第一次呼叫時才 `import()`，呼叫方仍同步獲得 `AssistantMessageEventStream`，載入完成後透過 `forwardStream()` 把內部串流的事件轉送進去。載入失敗時則推入 `error` 事件：

```typescript
// src/llm/providers/register-builtins.ts:157-180
function createLazyStream<TApi, TOptions, TSimpleOptions>(
  loadModule: () => Promise<LazyProviderModule<...>>,
): StreamFunction<TApi, TOptions> {
  return (model, context, options) => {
    const outer = new AssistantMessageEventStream();
    loadModule()
      .then((module) => forwardStream(outer, module.stream(model, context, options)))
      .catch((error) => {
        outer.push({ type: "error", reason: "error", error: createLazyLoadErrorMessage(model, error) });
        outer.end(message);
      });
    return outer; // 同步回傳，不等載入
  };
}
```

---

## 3. Thinking / Reasoning 跨供應商適配

### 3.1 統一的 ThinkingLevel 枚舉

```typescript
// packages/llm-core/src/types.ts:36-49
export type ThinkingLevel = "minimal" | "low" | "medium" | "high" | "xhigh" | "max";
export type ModelThinkingLevel = "off" | ThinkingLevel;
export type ThinkingLevelMap = Partial<Record<ModelThinkingLevel, string | null>>;
// null = 明確不支援（硬上限）；undefined = 使用 provider 預設

export interface ThinkingBudgets {
  minimal?: number;  // token 預算
  low?: number;
  medium?: number;
  high?: number;
  max?: number;
}
```

### 3.2 Anthropic 適配

Anthropic API 目前以「effort 字串」或「budget_tokens」兩種方式控制 thinking：

**新型 Adaptive Thinking（claude-fable-5、opus-4-6/7/8、sonnet-4-6）：**

```typescript
// src/agents/anthropic-transport-stream.ts:161-190
function mapThinkingLevelToEffort(
  level: ThinkingLevel | "off",
  model: AnthropicTransportModel,
): AnthropicAdaptiveEffort {
  switch (resolvedLevel) {
    case "off":
    case "minimal":
    case "low":  return "low";
    case "medium": return "medium";
    case "xhigh":  return supportsNativeXhighEffort(model) ? "xhigh" : "high";
    case "max":    return supportsClaudeNativeMaxEffort(model) ? "max" : "high";
    default:       return "high";
  }
}
// payload: params.thinking = { type: "adaptive" }; params.output_config = { effort }
```

**舊型 budget_tokens Thinking（其他 Claude 模型）：**

```typescript
// src/agents/anthropic-transport-stream.ts:216-237
function adjustMaxTokensForThinking(params) {
  const budgets = { minimal: 1024, low: 2048, medium: 8192, high: 16384 };
  // payload: params.thinking = { type: "enabled", budget_tokens: thinkingBudget }
  // 同時調高 max_tokens = min(baseMaxTokens + thinkingBudget, modelMaxTokens)
}
```

**自定義 thinkingLevelMap**（`packages/llm-core/src/model-contracts/anthropic.ts:78-91`）：
若 model 沒有設定 `thinkingLevelMap`，則根據模型 id 的正則匹配自動填入 `{ xhigh: null|"xhigh", max: "max" }`。

### 3.3 OpenAI/OpenAI-compatible 適配

OpenAI 用 `reasoning_effort` 字串參數（`"low" | "medium" | "high"`）。OpenClaw 透過 `thinkingFormat` 欄位支援多種方言：

```typescript
// packages/llm-core/src/types.ts:426-434
thinkingFormat?:
  | "openai"          // reasoning_effort: "low"/"medium"/"high"
  | "openrouter"      // reasoning: { effort: "low"/"medium"/"high" }
  | "deepseek"        // thinking: { type: "enabled" } + reasoning_effort
  | "together"        // reasoning: { enabled: true } + reasoning_effort
  | "zai"             // enable_thinking: boolean
  | "qwen"            // enable_thinking: boolean
  | "qwen-chat-template"; // chat_template_kwargs.enable_thinking
```

映射函式（`src/llm/providers/stream-wrappers/reasoning-effort-utils.ts:8-19`）：

```typescript
export function mapThinkingLevelToReasoningEffort(thinkingLevel: ThinkLevel): ReasoningEffort {
  if (thinkingLevel === "off")      return "none";
  if (thinkingLevel === "adaptive") return "medium";
  if (thinkingLevel === "max")      return "xhigh";
  return thinkingLevel; // minimal/low/medium/high/xhigh 直接對應
}
```

注意：`clampReasoning()` 在 `src/llm/providers/simple-options.ts:36-38` 中將 `xhigh` 靜默降為 `high`，因為舊版 OpenAI API 不支援 `xhigh`。

### 3.4 Google Gemini 適配

Google API 用 `ThinkingConfig` 物件，有自己的枚舉值：

```typescript
// src/llm/providers/google-shared.ts:42-47
export type GoogleThinkingLevel =
  | "THINKING_LEVEL_UNSPECIFIED"
  | "MINIMAL" | "LOW" | "MEDIUM" | "HIGH";

export type GoogleThinkingOptions = {
  enabled: boolean;
  budgetTokens?: number;
  level?: GoogleThinkingLevel;
};
```

### 3.5 clampThinkingLevel — 安全邊界

當請求的 level 超出模型支援範圍時，`clampThinkingLevel()` 向下退化，不會靜默升級：

```typescript
// src/llm/model-utils.ts:59-80
export function clampThinkingLevel<TApi extends Api>(
  model: Model<TApi>,
  level: ModelThinkingLevel,
): ModelThinkingLevel {
  // thinkingLevelMap[level] === null → 硬上限，向下找最近可用 level
  // 沒有 xhigh/max 條目 → 不允許這些 level
}
```

---

## 4. Token 統計與計費

### 4.1 統一的 Usage 型別

```typescript
// packages/llm-core/src/types.ts:261-274
export interface Usage {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  totalTokens: number;
  cost: {
    input: number;
    output: number;
    cacheRead: number;
    cacheWrite: number;
    total: number;
  };
}
```

`cacheRead` / `cacheWrite` 對應各家 prompt cache 的計費欄位。不支援 cache 的 provider 這兩欄為 0。

### 4.2 費用計算

費用統一在 `calculateCost()` 集中計算，model 描述符攜帶單價資訊：

```typescript
// src/llm/model-utils.ts:9-17
export function calculateCost<TApi extends Api>(model: Model<TApi>, usage: Usage): Usage["cost"] {
  usage.cost.input   = (model.cost.input   / 1_000_000) * usage.input;
  usage.cost.output  = (model.cost.output  / 1_000_000) * usage.output;
  usage.cost.cacheRead  = (model.cost.cacheRead  / 1_000_000) * usage.cacheRead;
  usage.cost.cacheWrite = (model.cost.cacheWrite / 1_000_000) * usage.cacheWrite;
  usage.cost.total = usage.cost.input + usage.cost.output + usage.cost.cacheRead + usage.cost.cacheWrite;
  return usage.cost;
}
```

### 4.3 各家 token 欄位對應

**Anthropic**（`src/agents/anthropic-transport-stream.ts:1225-1237`）：

| Usage 欄位 | Anthropic 原始欄位 |
|---|---|
| `input` | `message.usage.input_tokens` |
| `output` | `message.usage.output_tokens` |
| `cacheRead` | `usage.cache_read_input_tokens` |
| `cacheWrite` | `usage.cache_creation_input_tokens` |

usage 在 `message_start` 事件中初始化，在 `message_delta` 事件中更新（streaming 期間的增量）。

### 4.4 分層定價（Tiered Pricing）

`ModelDefinitionConfig.cost` 支援 `tieredPricing` 陣列（`src/config/types.models.ts:175-189`），允許「前 N tokens 用 rate A，超過後用 rate B」的階梯計費模型，例如某些 Google Gemini 模型的 token 計費會隨 context 長度改變。

---

## 5. Fallback / Model Selection

### 5.1 設定層 Fallback

當預設 provider/model 在使用者設定中找不到時，`resolveConfiguredProviderFallback()` 從 `models.providers` 中依插入順序選第一個可用 provider：

```typescript
// src/agents/configured-provider-fallback.ts:13-49
export function resolveConfiguredProviderFallback(params: {
  cfg: Pick<OpenClawConfig, "models">;
  defaultProvider: string;
  defaultModel?: string;
}): ProviderModelRef | null {
  // 若 defaultProvider 已有對應設定且 defaultModel 存在 → 不 fallback
  // 否則 → 取 providers 物件中第一個有 model 的 provider
}
```

### 5.2 模型不存在的錯誤識別

`isModelNotFoundErrorMessage()` 使用大量正則匹配各家不同的錯誤措辭，讓 probe/fallback 邏輯能區分「模型不存在」與「一般網路/鑑權錯誤」：

```typescript
// src/agents/live-model-errors.ts:8-53
export function isModelNotFoundErrorMessage(raw: string): boolean {
  // 涵蓋：
  // "no endpoints found for", "router not found", "unknown model",
  // "model_not_found", "404 not found", "not_found_error",
  // "models/xxx is not found", "model does not exist",
  // "model deprecated, upgrade to", "is not a valid model id",
  // "invalid model" 等等
}
```

MiniMax 有特殊的 HTML 404 格式，獨立處理（`src/agents/live-model-errors.ts:55-62`）。

### 5.3 Auth 層的 Fallback 邏輯

`resolveApiKeyForProvider()` 的憑證解析順序（`src/agents/model-auth.ts:939+`）：

1. 明確指定 `profileId` → 直接解析，失敗即 throw
2. 設定檔 `auth.profiles`/`auth.order` → 依序嘗試
3. `authOverride === "aws-sdk"` → 直接 AWS SDK auth
4. `credentialPrecedence === "env-first"` → 先讀環境變數
5. Provider entry 的 `apiKey` 欄位（可能是 literal / profile id / env marker）
6. 環境變數（`ANTHROPIC_API_KEY`、`OPENAI_API_KEY` 等）
7. `resolveUsableCustomProviderApiKey`（models.json 設定的 key）
8. 合成本機 auth（local server 不需要 key，合成 placeholder）
9. Plugin synthetic auth
10. 全部失敗 → throw `ProviderAuthError`

---

## 6. Provider 發現與設定

### 6.1 設定檔結構（models.json）

```typescript
// src/config/types.models.ts:279-292
export type ModelsConfig = {
  mode?: "merge" | "replace";  // 與內建 catalog 合併或完全取代
  providers?: Record<string, ModelProviderConfig>;
};

export type ModelProviderConfig = {
  baseUrl: string;
  apiKey?: SecretInput;       // 字串、env 變數名、或 secret ref
  auth?: ModelProviderAuthMode; // "api-key"|"aws-sdk"|"oauth"|"token"
  api?: ModelApi;             // 預設 API adapter
  contextWindow?: number;
  maxTokens?: number;
  timeoutSeconds?: number;
  region?: string;
  params?: Record<string, unknown>;
  headers?: Record<string, SecretInput>;
  authHeader?: boolean;
  models: ModelDefinitionConfig[];
};
```

實際 JSON 範例（自訂本機 vLLM）：

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "my-vllm": {
        "baseUrl": "http://localhost:8000",
        "api": "openai-completions",
        "models": [
          {
            "id": "mistral-7b-instruct",
            "name": "Mistral 7B",
            "reasoning": false,
            "input": ["text"],
            "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
            "contextWindow": 32768,
            "maxTokens": 4096
          }
        ]
      }
    }
  }
}
```

### 6.2 API Registry（運行時）

provider 模組呼叫 `registerApiProvider()` 把自己的 `stream`/`streamSimple` 函式掛入全域 `Map<string, ApiProvider>`：

```typescript
// packages/llm-runtime/src/api-registry.ts:77-90
export function registerApiProvider<TApi extends Api, TOptions extends StreamOptions>(
  provider: ApiProvider<TApi, TOptions>,
  sourceId?: string,  // 用於批次卸載（plugin 卸載時用）
): void {
  apiProviderRegistry.set(provider.api, { provider: ..., sourceId });
}
```

`getApiProvider(api)` 在 `stream(model, context)` 呼叫時查表，找不到直接 throw（`packages/llm-runtime/src/stream.ts:14-19`）。

### 6.3 Plugin 擴充點

Plugin 可用相同的 `registerApiProvider()` 覆蓋內建 provider 或新增自訂 API 家族。卸載 plugin 時呼叫 `unregisterApiProviders(sourceId)` 清除（`packages/llm-runtime/src/api-registry.ts:103-108`）。

---

## 7. SDK 最小 Provider 抽象建議

根據 OpenClaw 的實際設計，自行建造 multi-provider LLM SDK 的最小介面草圖如下：

```typescript
/** Step 1: 定義 API 家族 id（可 string & {} 允許自訂） */
type KnownApi =
  | "openai-completions"
  | "anthropic-messages"
  | "google-generative-ai";
type Api = KnownApi | (string & {});

/** Step 2: 模型描述符（攜帶路由/費用/能力資訊） */
interface Model<TApi extends Api = Api> {
  id: string;
  api: TApi;
  provider: string;
  baseUrl: string;
  reasoning: boolean;
  cost: { input: number; output: number; cacheRead: number; cacheWrite: number };
  contextWindow: number;
  maxTokens: number;
  thinkingLevelMap?: Partial<Record<"off"|"low"|"medium"|"high"|"xhigh"|"max", string|null>>;
  compat?: Record<string, unknown>; // per-API 相容開關
}

/** Step 3: 對話上下文 */
interface Context {
  systemPrompt?: string;
  messages: Message[];
  tools?: Tool[];
}

/** Step 4: 統一事件協定 */
type StreamEvent =
  | { type: "start" }
  | { type: "text_delta"; delta: string }
  | { type: "thinking_delta"; delta: string }
  | { type: "toolcall_end"; toolCall: { id: string; name: string; arguments: unknown } }
  | { type: "done"; message: AssistantMessage }
  | { type: "error"; error: AssistantMessage };

/** Step 5: Stream 容器 */
interface EventStreamContract extends AsyncIterable<StreamEvent> {
  push(event: StreamEvent): void;
  end(): void;
  result(): Promise<AssistantMessage>;
}

/** Step 6: Provider 實作介面 */
type StreamFunction<TApi extends Api> =
  (model: Model<TApi>, context: Context, options?: StreamOptions) => EventStreamContract;

interface ApiProvider<TApi extends Api = Api> {
  api: TApi;
  stream: StreamFunction<TApi>;
}

/** Step 7: Registry（全域 Map，支援 plugin 熱插拔） */
const registry = new Map<string, ApiProvider>();
function register(provider: ApiProvider, sourceId?: string): void { ... }
function get(api: Api): ApiProvider | undefined { return registry.get(api); }
function unregisterBySource(sourceId: string): void { ... }
```

**關鍵設計決策**：

- `stream()` 永不 throw，所有錯誤透過 `error` 事件傳遞
- `Model.api` 決定使用哪個 adapter，`Model.provider` 只用於認證和診斷
- `compat` 欄位讓同一個 API 家族（如 `openai-completions`）支援 20+ 個不同 provider 的微小差異，無需為每個 provider 開一個 api 類型

---

## 8. 坑點：各家 API 的不一致之處

### 8.1 Thinking/Reasoning 格式高度分散

如 §3 所示，目前有 7 種不同的 thinking 格式（`openai`/`openrouter`/`deepseek`/`together`/`zai`/`qwen`/`qwen-chat-template`），且各家還不斷演進。更麻煩的是：

- OpenAI `reasoning_effort` 只接受 `"low"|"medium"|"high"`，沒有 `xhigh` — 需要靜默降級（`src/llm/providers/simple-options.ts:36-38`）
- Anthropic 舊模型用 `budget_tokens`，新模型用 `effort` 字串，兩套 payload 格式完全不同，要靠模型 id 正則判斷走哪條路
- Google Gemini 用 Google 自己的 `ThinkingLevel` 枚舉（全大寫），且 `xhigh`/`max` 直接不存在，需映射為 `"HIGH"`
- `thinkingSignature` 在 Anthropic 是加密簽名字串（必須原封不動回傳），在 OpenAI Responses 是 item id（`src/llm/types.ts:229`）

### 8.2 Stop Reason 命名各異

| Provider | 原始值 | OpenClaw 統一值 |
|---|---|---|
| Anthropic | `end_turn` | `stop` |
| Anthropic | `max_tokens` | `length` |
| Anthropic | `tool_use` | `toolUse` |
| Anthropic | `refusal`/`sensitive` | `error` |
| OpenAI | `stop` | `stop` |
| OpenAI | `length` | `length` |
| OpenAI | `tool_calls` | `toolUse` |
| Google | `STOP` | `stop` |
| Google | `MAX_TOKENS` | `length` |

Anthropic 的 `refusal` 和 `sensitive` 是 Fable 5 特有的分類器輸出，會觸發 refusal buffer flush/discard 邏輯（`src/agents/anthropic-transport-stream.ts:1073-1077`）。

### 8.3 Tool Call 格式差異

- Anthropic 的 `tool_use` block 中，`input` 欄位是 JSON object（有時在 streaming 中是不完整的 JSON 字串，需 `parseStreamingJson()` 處理）
- OpenAI completions 的 `function.arguments` 是 JSON 字串
- Google Gemini 的 `functionCall.args` 是 object，且 `thoughtSignature` 可能掛在 function call part 上（`src/llm/providers/google-shared.ts:74-80`），不代表是 thinking 內容
- 部分 provider（如 MiniMax）不支援 tool call streaming，需 wrapper 層模擬（`src/llm/providers/stream-wrappers/minimax.ts`）

### 8.4 Tool Result 訊息結構

- Anthropic 要求 tool result 緊跟在 `user` role 訊息中，複數 tool result 打包成 `content: [{ type: "tool_result" }, ...]`
- OpenAI 每個 tool result 是獨立的 `{ role: "tool", ... }` 訊息
- 部分 OpenAI-compatible provider（`requiresAssistantAfterToolResult: true`）在 tool result 後需要插一條空 assistant 訊息

### 8.5 Cache Control 實作差異

`CacheRetention = "none" | "short" | "long"`，但實際對應：

- Anthropic 直接：`cache_control: { type: "ephemeral", ttl: "1h" }`（long）或 `{ type: "ephemeral" }`（short，預設 5 分鐘）
- OpenAI 的 prompt cache 是自動的，SDK 不需要明確標記
- 部分第三方（如 Fireworks）使用 Anthropic 格式但不支援 `cache_control` on tools（`AnthropicMessagesCompat.supportsCacheControlOnTools: false`）

### 8.6 Max Tokens 欄位名稱分裂

OpenAI 新版模型用 `max_completion_tokens`，舊版用 `max_tokens`。OpenClaw 透過 `OpenAICompletionsCompat.maxTokensField` 設定（`packages/llm-core/src/types.ts:416-417`），並根據 baseUrl 自動偵測（例如 api.openai.com 的新模型預設用 `max_completion_tokens`）。

### 8.7 Thinking Block 的多輪重播

Anthropic 要求 thinking block 必須攜帶 `thinkingSignature`（加密 token），且 `redacted_thinking` block 必須原封不動回傳（`src/agents/anthropic-transport-stream.ts:448-480`）。某些 Anthropic-compatible provider（如 Xiaomi Native）使用不同的 `reasoning_content` 欄位格式，需要特殊路徑處理（`supportsReasoningContentReplay()`，`src/agents/anthropic-transport-stream.ts:287-292`）。

### 8.8 OAuth vs API Key 混合場景

直接 Anthropic 平台支援 OAuth token（`sk-ant-oat...`），OAuth token 使用時 system prompt 會被強制插入 "You are Claude Code..." 前置語（`src/agents/anthropic-transport-stream.ts:929-949`），且工具名稱會正規化為 Claude Code 的官方工具名（`toClaudeCodeName()`）。這是很容易在 fork/整合時踩到的坑。

---

*文件基於 OpenClaw 原始碼，核對於 2026-06-12。*
