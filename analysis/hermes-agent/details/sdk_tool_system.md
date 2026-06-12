# hermes-agent 工具系統深度剖析：SDK 建造者視角

> 核對於 2026-06-12。所有引用均對應實際源碼行號。

本文以「你要從零打造一個 AI agent SDK」的視角，解構 hermes-agent 工具系統的設計決策。目標是讓讀者能提取可複用的模式，而非只是描述 hermes-agent 本身。

---

## 1. Registry 設計模式

### Singleton + 自註冊

hermes-agent 採用**模組層級 Singleton + 自註冊**的組合：

```python
# tools/registry.py:151-168  — Singleton 物件
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        ...

# tools/registry.py:543  — 模組層級單例
registry = ToolRegistry()
```

各工具檔案在**模組匯入時**（import time）於頂層呼叫 `registry.register()`：

```python
# tools/terminal_tool.py:2675-2683
registry.register(
    name="terminal",
    toolset="terminal",
    schema=TERMINAL_SCHEMA,
    handler=_handle_terminal,
    check_fn=check_terminal_requirements,
    emoji="💻",
    max_result_size_chars=100_000,
)
```

這個模式的觸發機制不是人工呼叫，而是透過 `discover_builtin_tools()` 掃描目錄後 `importlib.import_module()`（`tools/registry.py:57-74`）。發現函數用 AST 靜態分析篩選哪些模組頂層有 `registry.register(...)` 呼叫（`tools/registry.py:29-54`），避免引入不必要的模組。

**優點**

- 工具作者只需關心自己的檔案，不需修改任何「工具清單」。
- 新增工具 = 新增一個 `.py` 檔，放進 `tools/` 目錄即自動生效。
- 避免了 "工具清單 + 實作" 兩份資料的同步問題。

**缺點**

- 隱式耦合：工具「存在」取決於模組被匯入，import 錯誤會靜默跳過（`tools/registry.py:72-73` 只記 warning）。
- 測試隔離困難：Singleton 跨測試汙染，需要額外的 setup/teardown 清理。
- 執行緒安全需要 `RLock`（`tools/registry.py:161-162`），增加了 Singleton 的複雜度。

### ToolEntry 欄位剖析

`ToolEntry` 以 `__slots__` 宣告欄位（`tools/registry.py:80-84`），共 11 個：

| 欄位 | 型別 | SDK 必要性 | 說明 |
|---|---|---|---|
| `name` | `str` | **必要** | 工具唯一識別名，LLM 會用此名呼叫 |
| `schema` | `dict` | **必要** | OpenAI function calling 格式的 JSON Schema |
| `handler` | `Callable` | **必要** | 實際執行工具的函式 |
| `toolset` | `str` | 建議保留 | 工具分組，用於啟用/停用整組工具 |
| `check_fn` | `Callable` | 建議保留 | 零引數函式，回傳 bool，表示工具是否可用（探測環境） |
| `is_async` | `bool` | 建議保留 | 標記 handler 是否為 coroutine，觸發 async 橋接邏輯 |
| `requires_env` | `list` | 可省略 | 文件化需要哪些環境變數，供 UI 顯示 |
| `description` | `str` | 可省略 | 冗餘於 schema，僅供內部查詢用 |
| `emoji` | `str` | **可省略** | 完全是 UI 裝飾，hermes-agent 特有 |
| `max_result_size_chars` | `int\|float` | 建議保留 | 截斷過大結果，保護 context window |
| `dynamic_schema_overrides` | `Callable` | 可省略 | 執行時動態覆蓋 schema 欄位（hermes-agent 特有，應對 delegation 限制等） |

**SDK 最小核心**：`name` + `schema` + `handler`，加上 `check_fn` 和 `is_async` 就已覆蓋 90% 使用情境。

---

## 2. Schema 設計與 LLM 整合

### register() 的 schema 格式

schema 是一個**不含 `type: "function"` 外殼**的裸 dict，對應 OpenAI function calling 的 `function` 物件：

```python
# tools/terminal_tool.py:2617-2659
TERMINAL_SCHEMA = {
    "name": "terminal",
    "description": TERMINAL_TOOL_DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "..."},
            "background": {"type": "boolean", "default": False},
            "timeout": {"type": "integer", "minimum": 1},
            ...
        },
        "required": ["command"]
    }
}
```

`name` 欄位在 schema 內是**選填**的；`get_definitions()` 會強制補上 `entry.name`（`tools/registry.py:366-367`）。這讓工具作者可以在 schema dict 裡省略 name，或是讓 name 與 toolset 不同。

### get_definitions() 組裝流程

`get_definitions(tool_names: Set[str])` 回傳 LLM API 可直接使用的格式（`tools/registry.py:337-384`）：

```python
result.append({"type": "function", "function": schema_with_name})
```

組裝時依序做三件事：

1. **check_fn 過濾**：呼叫 `_check_fn_cached(entry.check_fn)`（30 秒 TTL）——若工具不可用，直接跳過，不納入最終清單（`tools/registry.py:358-364`）。
2. **dynamic_schema_overrides 套用**：呼叫工具的 `dynamic_schema_overrides()` callback，將回傳的 dict 淺合併進 schema（`tools/registry.py:372-382`）。
3. **包裝成 OpenAI 格式**：加上 `{"type": "function", ...}` 外殼（`tools/registry.py:383`）。

### Schema 驗證：hermes-agent 不做，由呼叫端自行消化

hermes-agent **沒有**在 `dispatch()` 或執行器層對 LLM 回傳的引數做 JSON Schema 驗證。執行流程是：

1. `json.loads(tool_call.function.arguments)`：純 JSON 解析，失敗就給空 dict（`agent/tool_executor.py:275-279`）。
2. 直接呼叫 handler，handler 自己用 `args.get("command")` 取值。

若 LLM 回傳不符 schema 的引數（例如 `command` 型別錯誤、缺少必填欄位），會在 handler 內部以 Python 例外的形式冒泡出來，被 `registry.dispatch()` 的頂層 try/except 攔截並回傳 `{"error": "..."}` JSON（`tools/registry.py:405-416`）。

**SDK 啟示**：Schema 驗證可以做，也可以不做。不做的好處是 handler 可以針對個別欄位提供有意義的錯誤訊息，而非一律「validation failed」。若要做驗證，最合適的位置是 `dispatch()` 內、呼叫 handler 之前。

---

## 3. 並行執行模型

### 判斷邏輯：誰決定要並行？

呼叫點在 agent 主迴圈（`run_agent.py` 或 `agent/conversation_loop.py`）。hermes-agent 的判斷邏輯是：若 LLM 在同一輪回傳**複數個** tool_calls，就走並行路徑；單個 tool call 走序列路徑。`tool_executor.py` 本身只提供兩個函式，判斷由呼叫方負責。

### 執行架構：ThreadPoolExecutor

並行路徑使用 `concurrent.futures.ThreadPoolExecutor`，上限 8 個 worker：

```python
# agent/tool_executor.py:51
_MAX_TOOL_WORKERS = 8

# agent/tool_executor.py:561-563
max_workers = min(len(runnable_calls), _MAX_TOOL_WORKERS)
with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    ...
```

實際上 `max_workers = min(本輪工具數, 8)`，所以若只有 3 個工具就只開 3 個 thread。

**Worker 上限取捨**：8 是一個實驗性常數，平衡了以下矛盾：
- 太少（1-2）：並行效益小，長尾工具（如多個 web_search）仍需排隊。
- 太多（32+）：LLM 極少同時呼叫超過 8 個工具；開大量 thread 造成 context switch 開銷，並讓 `propagate_context_to_thread()` 的 ContextVar 複製成本累積。

### 結果合併回對話

並行完成後，結果以**原始 tool_call 的順序**插入 messages（`agent/tool_executor.py:453`）：

```python
results = [None] * num_tools  # 預先分配，index 對應 tool_call 順序
# 每個 worker 寫入 results[index]，不是 append
```

最後迴圈按 `parsed_calls` 的順序，把每個 `results[i]` 轉成 tool result message 並 `messages.append()`（`agent/tool_executor.py:626-748`）。

這個設計確保：即使 `read_file` 在 200ms 完成、`terminal` 在 5s 才完成，模型看到的 tool results 仍然與它提出 tool_calls 的順序一致——符合 OpenAI API 的語意要求（每個 tool_call_id 必須對應到一個 tool result）。

### 中斷與 heartbeat

並行等待時以 5 秒為一個 poll 周期（`agent/tool_executor.py:578-617`）：

```python
while True:
    done, not_done = concurrent.futures.wait(futures, timeout=5.0)
    if not not_done:
        break
    if agent._interrupt_requested:
        for f in not_done: f.cancel()
        concurrent.futures.wait(not_done, timeout=3.0)
        break
    # 每 30s 發一次 heartbeat（6 × 5s）
    if _conc_elapsed % 30 < 6:
        agent._touch_activity(...)
```

這個設計讓使用者的「stop」指令能在 5 秒內生效，同時對 gateway 的 inactivity monitor 維持心跳。

---

## 4. Guardrails 模式

### 架構：純函數式觀察者，不侵入核心迴圈

`ToolCallGuardrailController`（`agent/tool_guardrails.py:224-381`）是一個**無副作用的觀察器**：它只追蹤呼叫歷史並回傳 `ToolGuardrailDecision`，本身不執行任何阻擋動作。

```python
# agent/tool_guardrails.py:144-157
@dataclass(frozen=True)
class ToolGuardrailDecision:
    action: str = "allow"  # allow | warn | block | halt
    code: str = "allow"
    message: str = ""
    ...
    @property
    def allows_execution(self) -> bool:
        return self.action in {"allow", "warn"}
```

### 介入時機

在執行器的**兩個位置**各有一次 guardrail 呼叫：

**before_call**（在工具執行前）：

```python
# agent/tool_executor.py:375-390（並行路徑，序列路徑類似）
guardrail_decision = agent._tool_guardrails.before_call(function_name, function_args)
if not guardrail_decision.allows_execution:
    block_result = agent._guardrail_block_result(guardrail_decision)
    blocked_by_guardrail = True
```

`before_call` 只在 `hard_stop_enabled=True` 時才有機會回傳 `block`；預設設定下它永遠回傳 `allow`（`agent/tool_guardrails.py:243-244`）。

**after_call**（工具執行後，透過 `_append_guardrail_observation`）：負責更新失敗計數，並決定是否在工具結果後面附加 warning 訊息給 LLM 看。

### 三種行為：warn / block / halt

| action | 說明 | 是否阻止執行 |
|---|---|---|
| `allow` | 正常，不做任何事 | 否 |
| `warn` | 在工具結果末尾附加警告文字（`append_toolguard_guidance`），LLM 會看到 | 否 |
| `block` | 合成一個假的 tool result 回傳給 LLM，內含錯誤訊息 | 是 |
| `halt` | 與 block 相同，但額外設定 `_halt_decision` 供主迴圈決定是否終止當輪 | 是 |

偵測邏輯分三類（`agent/tool_guardrails.py:241-375`）：

1. **完全相同的失敗**（exact_failure）：`ToolCallSignature` = sha256(tool_name + sorted_canonical_args)。同一 signature 失敗 2 次 → warn；5 次 → block。
2. **同工具不同引數的失敗**（same_tool_failure）：同工具名失敗 3 次 → warn；8 次 → halt。
3. **冪等工具無進展**（idempotent_no_progress）：`read_file`, `web_search` 等工具回傳相同結果 2 次 → warn；5 次 → block。

### SDK 啟示

**關鍵設計原則**：guardrail controller 是純資料結構，不持有任何對 agent 的引用。這讓它：

- 易於單元測試（只需建立 controller、呼叫 `before_call`/`after_call`，驗證 decision）。
- 易於替換（換一套 policy 只需換 `ToolCallGuardrailConfig`）。
- 不需要修改核心執行器（執行器負責「如何回應 decision」，guardrail 只負責「要回傳什麼 decision」）。

「需要使用者確認」的模式在 hermes-agent 是透過 plugin hook（`get_pre_tool_call_block_message`，`agent/tool_executor.py:346-373`）實現的，而非 guardrail controller。Guardrail 只處理**自動偵測的 loop/failure 模式**；人工審批屬於 plugin 層。

---

## 5. SDK 最小工具系統建議

若你要從零複製最關鍵的模式，以下是分層建議：

### 必要抽象（不可省略）

```python
# Layer 1: 工具元數據
@dataclass
class ToolEntry:
    name: str
    schema: dict          # OpenAI function schema（不含外殼）
    handler: Callable     # (args: dict, **kw) -> str（JSON 字串）
    is_async: bool = False
    check_fn: Optional[Callable] = None

# Layer 2: Registry
class ToolRegistry:
    _tools: Dict[str, ToolEntry]
    
    def register(self, ...) -> None: ...
    def get_definitions(self, names: Set[str]) -> List[dict]: ...
    def dispatch(self, name: str, args: dict) -> str: ...

# Layer 3: 回傳格式標準化
def tool_error(message: str, **extra) -> str:
    return json.dumps({"error": message, **extra})

def tool_result(data=None, **kwargs) -> str:
    return json.dumps(data or kwargs)
```

### 建議保留（值得複製）

- **`check_fn` + TTL cache**：30 秒快取 `check_fn` 結果，避免每次 `get_definitions()` 都探測外部環境（`tools/registry.py:121-141`）。
- **generation counter**：`_generation` 整數，每次 `register`/`deregister` 遞增（`tools/registry.py:168`）。外部 cache 可以拿它做 cache key，不需要每次都重建 tool definitions。
- **`max_result_size_chars`**：每個工具可宣告自己回傳結果的最大字元數，執行後截斷，保護 context window。
- **snapshot 模式**：`_snapshot_entries()` 回傳 list copy，讓讀取和寫入不互相阻塞（`tools/registry.py:169-176`）。

### 可省略（hermes-agent 特有，不必複製）

- `toolset`：工具分組概念，對 hermes-agent 的 enable/disable CLI（`hermes tools enable`）有用，小型 SDK 不需要。
- `emoji`：純 UI 裝飾，與功能無關。
- `dynamic_schema_overrides`：只有當你有執行時才確定的 schema 欄位（如「最多幾個子 agent」）才需要，一般工具不需要。
- `toolset_aliases`：`toolset` 的別名機制，為 MCP 相容性而設計。
- `discover_builtin_tools()` 的 AST 掃描機制：若工具數量少，直接手動 register 即可；若要自動發現，直接全部 import 更簡單。

---

## 6. 坑點與非顯而易見的設計決策

### 坑點一：序列路徑有大量特殊 case，是「硬編碼 dispatch table」

`execute_tool_calls_sequential()` 有一段非常長的 if/elif 鏈（`agent/tool_executor.py:964-1239`），對 `todo`, `session_search`, `memory`, `clarify`, `read_terminal`, `delegate_task`, context engine 工具、memory manager 工具等一一特殊處理——這些工具不走 `registry.dispatch()`，而是直接在這裡 inline 呼叫。

這個設計的原因是這些工具需要注入 agent 實例的私有狀態（`agent._todo_store`, `agent._memory_store`, `agent.session_id` 等），而 registry 的 `dispatch()` 介面只接受 `(name, args, **kwargs)`，傳遞 agent 引用很彆扭。

**SDK 啟示**：若你的工具需要存取 agent 狀態，有兩種更乾淨的解法：
1. 在 register 時傳入部分 state 的閉包（handler 捕獲 agent 弱引用）。
2. 允許 `dispatch(name, args, context=...)` 傳遞一個上下文物件，讓 handler 從 context 取值。

hermes-agent 選擇在執行器裡 inline 是歷史演化的結果，不是最初設計的選擇。

### 坑點二：check_fn 只和 toolset 的「第一個工具」綁定

```python
# tools/registry.py:303-304
if check_fn and toolset not in self._toolset_checks:
    self._toolset_checks[toolset] = check_fn
```

同一 toolset 的第二個工具若提供不同的 `check_fn`，會被靜默忽略。這是刻意的——假設同 toolset 的所有工具共用同一個可用性條件。

### 坑點三：tool_error / tool_result 看似小工具，實際是 protocol boundary

handler 的回傳型別是 `str`（JSON 字串），不是 `dict`。這是因為：

1. MCP 工具、registry 工具、agent 內建工具的結果最後都需要插入 message list，統一型別讓 `make_tool_result_message()` 不需要判斷型別。
2. `maybe_persist_tool_result()` 可以對字串做字元長度截斷，若回傳 dict 就需要額外序列化步驟。

hermes-agent 還有一個額外的 `_sanitize_tool_error()`（由 `registry.dispatch()` 呼叫，`tools/registry.py:410-415`），專門清除例外訊息裡可能讓 LLM 誤解結構的 token（如 `<|endoftext|>`、XML CDATA、code fence 等）。這是一個不明顯但重要的防禦措施。

### 坑點四：並行路徑的結果陣列必須按順序填入，不能 append

`results = [None] * num_tools`，worker 寫入 `results[index]`（`agent/tool_executor.py:453, 531`）。若改成每個 worker 都 `results.append()`，最終順序就會是完成時間順序，而非 tool_call 發出時的順序——這會導致 OpenAI API 抱怨 tool result 順序與 assistant message 的 tool_calls 不對應。

### 坑點五：deregister 的 toolset 清理邏輯是 O(N)

```python
# tools/registry.py:317-329
toolset_still_exists = any(
    e.toolset == entry.toolset for e in self._tools.values()
)
```

每次 deregister 都線性掃描所有工具，找出 toolset 是否還有其他工具。對靜態工具集無影響，但若有頻繁 MCP 工具動態刷新（`notifications/tools/list_changed`），高頻 deregister 在工具數量多時會有效能問題。

### 坑點六：`dispatch()` 的 async 橋接需要 import model_tools

```python
# tools/registry.py:403
from model_tools import _run_async
```

這個 import 在 `dispatch()` 被呼叫時才發生（lazy），是為了避免循環 import（`registry.py` → `model_tools.py` → `tools/*.py` → `registry.py`）。但這也意味著若 `model_tools` 不存在或載入失敗，async 工具會在第一次呼叫時才爆炸，而非在 import 時。
