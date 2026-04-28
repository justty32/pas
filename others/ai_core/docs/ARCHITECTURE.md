# AI Core 架構規劃

> 此文件為實作前的設計定稿。後續若有變動以本檔最新版本為準，並在 `## 變更紀錄` 區段附註。

## 定位（Positioning）

ai_core 同時服務 **AI agent** 與 **人類使用者**。預期使用比例約 **AI 80% / 人類 20%**，但**人類保持完全掌控**：

- AI agent 透過 ai_core 呼叫 LLM、組合既有函式、甚至**產出新的函式**
- 函式會自我增殖：人類或 AI 在「足夠明確的 context」下，呼叫某 authoring function 讓 LLM 寫出新 function；這個新 function 進入 hub 被後續 caller 使用，形成生長的工具樹
- 人類看到 AI 寫出的好用 function 可以直接拿來用 — 所有函式都是普通 shell command，沒有 AI-only 的格式

設計後果：

1. CLI 與 metadata 同時對人類友善與 AI 友善 — 不為了討好任一方而犧牲另一方
2. 系統不假設 caller 是 AI；任何 function 都能在純 shell 環境下被人手動呼叫
3. 任何 AI 寫出來的 function 都得通過 dry-run + 範例驗證才能進入 registry，避免「AI 生 AI 用」的內部黑箱

---

## 1. 設計原則

承襲 `thinking.md`：

- **KISS、輕量、不重造輪子、相依最少**
- **shell 為一等公民**：所有元件以 CLI 為主介面，人類與 AI 都用同一個介面
- **每個函式預設 stateless one-shot**；需要狀態者自己管狀態，重量級者升格為常駐 server
- **錯誤訊息走 stderr、正常輸出走 stdout 或 `--output` 指定路徑**（Unix 慣例）
- **metadata 是極簡協議**：只強制「合法 JSON」，不規定具體 schema
- **metadata 容錯**：所有 caller / hub / author 等元件都必須**預期某些函式根本沒寫 `--metadata`、或寫得不合法、或缺慣例 key**。這時應 graceful 降級（使用合理預設、提示使用者讀文件），而不是 crash 或拒絕呼叫該函式

### Singleton Resource Manager Pattern

對「一次只能服務一個請求、建立成本高」的單例資源（LLM 模型、heavy GPU 計算、配額受限的外部 API、長連線的本地服務等），統一採用此 pattern：

1. **常駐 server** 包住該資源，HTTP / IPC 對外
2. **per-resource FIFO queue + worker**
3. **配套一支 shell wrapper CLI**（因為 shell 不該被迫去 curl）— wrapper 把 args 翻成 HTTP 呼叫；server + wrapper 是**共生雙元件**，一起發布
4. wrapper CLI 必須提供 `--metadata`（描述這支 wrapper 工具自身）與 `--entry-metadata`（描述 server 底下個別 entry，如某個 model）
5. 配額不足 / 不合法輸入 / 不存在的 entry → wrapper 直接 stderr + 非 0 exit code

**此 pattern 有兩種亞型：**

| 亞型 | 說明 | 介面 |
|---|---|---|
| **Entry-managing singleton** | 管理多個具名資源（entries），每個 entry 有自己的配額 / 狀態。例：LLM Entry Manager（多個 model） | `--metadata`（工具自身）+ `--entry-metadata`（個別 entry） |
| **Simple singleton server** | 包住單一資源，不需要 entry 概念。功能上更像常駐的 MCP 工具伺服器，只是變成 singleton 以保護底層資源。 | 只有 `--metadata` |

只有 **entry-managing** 亞型需要在 metadata 中宣告 `has_entries: true`，讓 caller 知道還有 `--entry-metadata` 可用（詳見 §4.7）。

**LLM Entry Manager 是 entry-managing 亞型的首個實例**：`ai-core-server`（server）+ `ai-core-call`（wrapper CLI）。未來新增同類 manager 時應沿用同一套介面慣例（同名旗標、同樣的錯誤碼語意），讓 caller 對所有 manager 的行為一致。

---

## 2. 整體架構

```
caller（人類 shell / AI agent / 其他 function）
   │
   ├── 直接 shell call ────────────────────────────┐
   │                                                ▼
   │                               任意語言寫的 function
   │                               （唯一硬規則：--metadata 印合法 JSON）
   │                                       │
   │                                       ├── 單純函式：直接執行
   │                                       └── 重資源：透過 wrapper CLI ──▶ singleton server
   │
   ├── 想知道有哪些 function ──▶ Function Hub（server / one-shot 雙形態）
   │
   └── 想新增 function ─────────▶ ai-core-author（一站式產生 + dry-run + 註冊）
```

具體 singleton manager 的首例：

```
ai-core-server（HTTP）          ←── ai-core-call（shell wrapper CLI）
   ├─ per-model asyncio queue
   ├─ rate limit (rpm / tokens / cost)
   └─ litellm router → ollama / lm-studio / gemini
```

---

## 3. 技術選型

| 項目 | 選擇 | 理由 |
|---|---|---|
| 主語言 | Python 3.11+ | LLM 生態最完整；asyncio 跨平台行為穩定 |
| 套件管理 | `uv` | 快、跨平台、有 lockfile |
| LLM 抽象 | `litellm` | 已支援 ollama、lm studio (OpenAI 相容)、gemini |
| HTTP server | `fastapi` + `uvicorn` | Entry Manager / Hub server 都用 |
| 跨平台路徑 | `platformdirs` | 自動找對 config / data dir |
| CLI 註冊 | `pyproject.toml [project.scripts]` | 不靠 shebang，Win/Linux 都能跑 |
| 配置 / metadata | JSON | 已拍板 |

---

## 4. metadata 協議（極簡版）

唯一強制：

1. 函式接受 `--metadata` 旗標
2. 觸發時 stdout 輸出**合法 JSON**（任意 key-value）
3. exit code 0

下列為**慣例 key**（自願遵守、有就用、沒就略），但**強烈建議寫入** — 否則 caller / Hub 無法智慧化呼叫，且 AI 學習成本大增。

### 4.1 描述類

- `name`：函式識別名（不寫的話 Hub 用檔名 fallback）
- `summary`：一行短摘要（list.txt 過大時 Hub 優先用此欄）
- `description`：給 AI / 人類讀的長描述
- `usage`：人類可讀的呼叫範例字串
- `tags` / `category`：分類（陣列），方便過濾、搜尋

### 4.2 I/O 慣例（`io`）

宣告函式的標準使用方式 — 輸入從哪來、輸出去哪。

```json
{
  "io": {
    "input":  "stdin" | "file" | "args" | "none",
    "input_flag":  "--input",
    "output": "stdout" | "file" | "none",
    "output_flag": "--output",
    "format": {
      "input":  "text" | "json" | "binary",
      "output": "text" | "json" | "binary"
    }
  }
}
```

| 欄位 | 含義 |
|---|---|
| `io.input = "stdin"` | 函式從 stdin 讀資料 |
| `io.input = "file"` | 函式透過 `io.input_flag`（預設 `--input`）指定的旗標接收檔案路徑 |
| `io.input = "args"` | 資料直接以命令列引數傳入 |
| `io.input = "none"` | 函式不需輸入 |
| `io.output = "stdout"` | 結果寫到 stdout |
| `io.output = "file"` | 結果寫到 `io.output_flag`（預設 `--output`）指定的檔案路徑 |
| `io.output = "none"` | 函式無正常輸出（純副作用） |
| `io.format` | 描述輸入 / 輸出資料格式，`text` 為預設 |

**錯誤輸出永遠是 stderr**，不必在 metadata 中宣告。

### 4.3 範例與錯誤類型（`examples`、`errors`）

`examples`（**強烈建議**，給 AI 學習用、給 author 工具的 dry-run 比對用）：

```json
{
  "examples": [
    {
      "input": "hello world",
      "output": "hello world",
      "note": "原樣輸出"
    },
    {
      "input": "",
      "output": "",
      "note": "空輸入也回空"
    }
  ]
}
```

`errors`（可能拋出的錯誤類型清單，給 AI 撰寫 retry / fallback 邏輯）：

```json
{
  "errors": [
    {"type": "QuotaExceeded", "when": "當日 token 用完", "retriable": false},
    {"type": "BackendDown",   "when": "ollama 服務未啟動", "retriable": true}
  ]
}
```

### 4.4 依賴（`dependencies`）

宣告本函式呼叫了哪些其他函式（讓 hub 建構依賴圖 / 給 AI 預先了解副作用範圍）：

```json
{
  "dependencies": ["ai-core-call", "echo"]
}
```

### 4.5 完整範例

`echo.sh --metadata`：

```json
{
  "name": "echo",
  "summary": "把輸入原樣輸出，用來測試管線",
  "description": "從 --input 指定的檔讀取內容，原樣寫入 --output 指定的檔。",
  "usage": "echo.sh --input src.txt --output dst.txt",
  "tags": ["util", "test"],
  "io": {
    "input":  "file",
    "input_flag":  "--input",
    "output": "file",
    "output_flag": "--output",
    "format": {"input": "text", "output": "text"}
  },
  "examples": [
    {"input": "abc", "output": "abc"}
  ],
  "errors": [
    {"type": "InputNotFound", "when": "--input 路徑不存在", "retriable": false}
  ],
  "dependencies": []
}
```

### 4.6 容錯與降級（caller / Hub / author 的義務）

各元件遇到下列情境時必須 graceful，不能 crash：

| 情境 | 處理 |
|---|---|
| 函式不支援 `--metadata`（旗標不認得 / 拋例外） | 視為「無 metadata」；Hub 仍列出函式，標 `"metadata": "absent"`，提示使用者 `--help` 或讀 source |
| `--metadata` exit code 非 0 | 同上 |
| `--metadata` 輸出非合法 JSON | 同上，外加 stderr 警告 |
| metadata JSON 合法但缺 `io` | 預設 `{"input": "stdin", "output": "stdout", "format": "text"}`；提示「io contract unknown」 |
| 缺 `description` / `summary` | 用檔名 / `(no description)` 替代，Hub list 標記 |
| 缺 `examples` | author 的 dry-run 退化為「只驗證執行不 crash」，不比對輸出 |

`protocol/metadata.py` 提供 Python helper（`fetch_metadata(path) -> MetadataView`）統一處理這些 case，讓各元件不重寫樣板。

### 4.7 entrydata 介面宣告

**metadata 是了解一個工具的唯一入口**。但對於 entry-managing singleton（§1），工具底下管理多個 entry；每個 entry 也有自己的資料介面，稱為 **entrydata**。

caller 如何知道某工具有 entrydata 介面？**從 metadata 宣告中得知**：

```json
{
  "name": "ai-core-call",
  "has_entries": true,
  "entry_interface": {
    "flag": "--entry-metadata",
    "http_endpoint": "GET /entries",
    "entry_http_endpoint": "GET /entries/<name>/metadata",
    "note": "每個 entry 代表一個 LLM 後端，entrydata 描述其特性、限制與目前用量"
  }
}
```

| 欄位 | 含義 |
|---|---|
| `has_entries` | 布林值；存在且為 true 代表此工具管理多個具名 entry |
| `entry_interface.flag` | 用來列出 / 查詢 entry 的 CLI 旗標 |
| `entry_interface.http_endpoint` | 查詢全部 entry 的 HTTP 端點 |
| `entry_interface.entry_http_endpoint` | 查詢單一 entry 的 HTTP 端點 |

**無 `has_entries`（或值為 false）的工具視為 simple singleton**，只有 `--metadata`，無 entrydata 介面。

entrydata 的 schema 完全自由（僅強制合法 JSON）；慣例 key 同 §4 其他小節——寫了就好用，缺了 graceful 降級。

### 4.8 Server 啟用提示（server-backed wrapper 的可選 metadata key）

對需要常駐 server 才能運作的 wrapper（§1 兩種亞型都適用），metadata 可宣告該 server 的典型啟用狀態與啟動方式，讓 hub 在清單中對 caller 顯示提示：

```json
{
  "name": "ai-core-call",
  "has_entries": true,
  "server": {
    "activation": "usually-on",
    "activation_hint": "ai-core-server"
  }
}
```

| 欄位 | 含義 |
|---|---|
| `server.activation` | `"usually-on"` / `"rarely-on"` / `"default-off"` 三選一；提示此 server 在系統中的典型啟用狀態 |
| `server.activation_hint` | 一行字串，告訴使用者怎麼啟動該 server（命令、文件路徑等任何提示） |

**這是純註解，不影響 wrapper 行為**：server 沒啟動時 wrapper 仍照 §5.2 規則直接 stderr + exit 1。`activation` 與 `activation_hint` 只供 hub 顯示，幫助 caller 評估「呼叫這個 function 前要不要先啟動什麼」。

**設計取捨**：本架構**不**規範 server 的啟動方式（daemon、systemd unit、`nohup` 等都是使用者選擇），因為跨平台 daemon 化坑多、KISS 原則下不值得在第一版做。`ai-core-server` 就是一個前景執行的程式，需要常駐請用系統提供的工具（`tmux`、systemd、Windows Service 等）。

---

## 5. 錯誤處理慣例（全系統統一）

| 通道 | 用途 |
|---|---|
| stdout | 正常結果（或寫入 `--output` 指定路徑） |
| stderr | 錯誤訊息、警告、診斷 |
| exit code | 成功 `0`；失敗非 `0` |

**失敗時不污染 `--output` 檔**：保留前次內容或不建立檔案。

### 5.1 `--json-errors` 旗標（給 AI / 程式 caller）

預設 stderr 是人類可讀的純文字。caller 加 `--json-errors` 旗標後，stderr 改輸出單行 JSON：

```json
{"type": "QuotaExceeded", "message": "gemini-flash 今日 token 已用完", "hint": "改用 ollama-llama3 或等明天", "retriable": false}
```

所有元件（entry manager wrapper、hub、author、自訂 function 透過 `protocol/metadata.py` helper）都應支援此旗標。預設關閉以保持人類友善。

### 5.2 Entry Manager 在下列情況直接 stderr 噴錯誤、exit code 非 0

- **server 未啟動**（`ai-core-call` 無法連線）→ 提示「請先執行 ai-core-server」，exit 1；wrapper 不做 auto-start，保持無副作用
- token / cost / rpm 配額不足
- 輸入不合法（例如 messages 格式錯誤）
- 未指定 entry / 指定的 entry 不存在
- 後端連線失敗且無 fallback

超限請求**不入 queue**（避免堆積無望的工作）。

---

## 6. LLM Entry Manager 設計

> §1「Singleton Resource Manager Pattern」的首個實例 — server (`ai-core-server`) + wrapper CLI (`ai-core-call`) 雙元件。

### 6.1 為什麼必須常駐 server

- 本地模型（ollama / lm studio）連線昂貴，不該每次 fork 重連
- queue 與 rate limit 是有狀態的
- 多個並行 caller 共享 quota

### 6.2 Queue 與呼叫流程

```
caller shell:
    ai-core-call --entry gemini-flash --input prompt.txt --output result.txt
        │
        ▼ POST /call（wrapper 翻成 HTTP）
    ai-core-server:
        ├─ 檢查 entry 是否存在  ──失敗→ 422 + error JSON ──→ wrapper stderr
        ├─ 檢查 quota / rpm    ──失敗→ 429 + error JSON ──→ wrapper stderr
        ├─ 檢查輸入合法性      ──失敗→ 400 + error JSON ──→ wrapper stderr
        └─ 進入該 model 的 queue（附帶 enqueue_ts + time_to_wait_ms）
                │
                ├─ worker 取出前若 now − enqueue_ts > time_to_wait_ms
                │       → 408 + error JSON → wrapper stderr + 非 0 exit
                ▼ worker 取出（FIFO 串行，未超時）
            litellm 呼叫對應 backend
                │
                ▼ 完成
            結果回傳 wrapper，wrapper 寫入 --output 指定路徑
            wrapper exit 0
```

**`--output` 必填**。檔案 I/O 由 wrapper 端負責，server 不直接觸碰 caller 的檔案系統（跨機器或容器化時更乾淨）。

### 6.3 同步 vs 非同步

| 模式 | 行為 | 適用情境 |
|---|---|---|
| 預設（同步） | wrapper 阻塞等到 server 處理完，寫檔後 exit | shell 管道、自然語意 |
| `--async` | wrapper POST 後立刻返回 task_id 到 stdout | 高併發、批次發 N 個工作 |

`--async` 模式下後續可用 `ai-core-call --task <id> --output result.txt` 收結果。

### 6.4 通訊端點

- HTTP on `127.0.0.1:5577`（預設可配置）
- `POST /call` → 建立 task；`{model, messages, options, async, time_to_wait_ms?, parent_call_id?}`
- `GET /tasks/<id>` → 查詢狀態
- `GET /tasks/<id>/result` → 取結果
- `GET /status` → 所有 queue 與 quota 狀態
- `GET /entries` → 列出所有 entry
- `GET /entries/<name>/metadata` → 單一 entry 的 metadata（給 `--entry-metadata` 用）
- 本機 token 認證（產生在 `~/.config/ai_core/token`）

### 6.5 `--metadata` vs `--entry-metadata`

`ai-core-call` 同時提供兩個 metadata 介面：

| 旗標 | 描述對象 | 內容 |
|---|---|---|
| `--metadata` | wrapper CLI 自身 | summary、usage、I/O 慣例（§4） |
| `--entry-metadata` | server 底下的個別 entry（model） | 每個 model 的特性、限制、目前用量 |

```bash
ai-core-call --entry-metadata                       # 所有 entry 的陣列
ai-core-call --entry-metadata --entry gemini-flash  # 單一 entry
```

`--entry-metadata` 輸出範例：

```json
{
  "name": "gemini-flash",
  "backend": "gemini",
  "model": "gemini-2.0-flash",
  "summary": "輕量快速、適合短答與分類",
  "is_local": false,
  "context_window": 1000000,
  "expected_latency_ms": 800,
  "cost": {
    "input_per_1k_tokens_usd": 0.000075,
    "output_per_1k_tokens_usd": 0.0003
  },
  "limits": {"rpm": 15, "tokens_per_day": 1000000, "cost_per_day": 5.0},
  "concurrency": 5,
  "current_usage": {"tokens_today": 12345, "cost_today": 0.42, "queue_length": 0, "active_workers": 2, "rpm_remaining": 13}
}
```

**`--entry-metadata` 內部 schema 也是自由的**（僅強制合法 JSON）。此介面屬 §1 pattern 的一部分，未來其他 manager 也應提供同名旗標。

### 6.6 Queue 實作

- 每個 model 一條 `asyncio.Queue`
- 每條 queue 配 **N 個 worker**（N = entry config 的 `concurrency`，預設 1）共享消費
- `concurrency: 1` 退化為 FIFO 串行（本地模型 / GPU 受限資源的標準場景）
- `concurrency > 1` 適合雲端 stateless API（gemini-flash 等），讓多個請求並行送出，受 §6.7 rate limit 約束
- rate limit 檢查在**入 queue 之前**（§6.7），與 worker 數無關
- worker 例外不終止 worker 本身；錯誤寫進 task 結果，sync 模式 wrapper 收到後噴 stderr
- `concurrency` 為靜態配置：改值需編輯 config + 重啟 server，不支援 runtime 動態調整（KISS）

### 6.7 Rate Limit

第一版欄位：`rpm`、`tokens_per_day`、`cost_per_day`。GPU / 電力先在 schema 預留、不實作追蹤。

超限：請求**不入 queue**，立刻 429 + stderr。

### 6.8 佇列等待逾時（time_to_wait）

rate limit 擋在入 queue 之前；**time_to_wait 擋在 queue 內等待期間**，兩者互補。

```
caller 呼叫時帶 --wait 3000（ms）
    → POST /call body: {... "time_to_wait_ms": 3000}
    → server 記錄 enqueue_ts

worker 準備取出時：
    if now() - enqueue_ts > time_to_wait_ms:
        task.status = "timeout"
        回傳 408 {"type": "QueueTimeout", "message": "等待超過 3000ms", "retriable": true}
    else:
        正常呼叫 LLM
```

**CLI 旗標**：`ai-core-call --wait <ms>`，預設不設逾時（等到 server 處理完為止）。

**適用場景**：
- interactive 呼叫：不想等超過 N 秒，寧可讓使用者知道系統忙
- batch 工作：不重要的項目可設短 timeout 讓位給重要任務
- retry 邏輯：timeout 的 `retriable: true` 讓 caller 知道重試有意義

### 6.9 Streaming Output

LLM 普遍支援 token streaming；互動式情境下，逐 token 看到輸出比等完整回應自然得多。

**CLI 行為**：

| 旗標組合 | 行為 |
|---|---|
| `--stream` | token 即時吐到 stdout；`--output` 變為可選 |
| `--stream` + `--output` | stdout 即時 stream + 全文寫到 `--output`（atomic，完成後一次寫入） |
| 純 `--output`（無 `--stream`） | 維持預設：等完成才寫檔，stdout 不輸出 |
| `--stream --async` | **不允許**，wrapper 在送 HTTP 之前就 stderr 報錯（兩者語意衝突） |

**HTTP 傳輸**：server 對 streaming task 用 **chunked transfer encoding**（單一 HTTP response，逐塊送 delta token）。SSE 過度，chunked 已足夠且 Python 標準庫好處理。

**與 time_to_wait 的互動**：`time_to_wait_ms` 只計算 **queue 等待時間**；一旦 worker 取出 task、第一個 token 開始流出，計時就解除。streaming 過程多長都不被 `time_to_wait` 中斷。

**錯誤處理**：若 streaming 中途失敗（backend 斷線等），stdout 已輸出的部分留著（unix 沒有 unwrite），錯誤訊息進 stderr，exit code 非 0。

**Ledger**：與非 stream 同樣寫一筆 record。`duration_ms` 為總耗時，`tokens.output` 為最終 token 總數，`output_summary` 取最終結果的前若干字元。

**`--output` 不污染原則**：`--output` 是 atomic 一次寫入（streaming 過程內容只在記憶體 buffer），失敗時直接不寫檔，與 §5 規則一致。

### 6.10 Wrapper 輸入介面（input contract）

底層 `POST /call` 的核心是 OpenAI 風格的 `messages` 陣列；但對 wrapper CLI 來說，**`--input <file>` 是唯一強制的輸入介面**。

**核心語意**：`--input` 檔案內容被 wrapper 自動包成單一 user message：

```
messages = [{"role": "user", "content": <檔案內容>}]
```

「送一個 prompt 取一個回應」這個最常見場景靠這一個旗標就夠用。

**狀態管理由 caller 負責**（呼應 §1 stateless 原則）：多輪對話、history、session 等概念**完全不存在於 wrapper 內**。caller 想做多輪對話 → 自己維護 `chat.json`、自己拼接訊息、自己更新檔案。wrapper 不記任何 session。

**Wrapper 可選提供「語法糖」旗標**——這是 wrapper 實作層的選擇，**不在協議層強制**。常見參考設計：

| 範例旗標 | 用途 |
|---|---|
| `--system <text\|@file>` | 自動 prepend system message |
| `--messages <file>` | 直接送完整 JSON `messages` 陣列，跳過 wrapper 的單訊息包裝 |
| `--append <file>` | 把 input 接到既有 messages 之後 |

這些 sugar 是 wrapper 作者的決定，可全有、全無、或只挑幾個。`ai-core-call` 第一版實作哪些 sugar，留待 M1 實作階段視真實使用情境決定。

**caller 需要超出 sugar 能力時**：直接 `POST /call` 送完整 `messages` 陣列，繞過 CLI 走 HTTP 層即可。

---

## 7. Calling Chain Observability

人類掌控 80/20 系統的關鍵。每次函式呼叫都產生一筆**call record**，所有 record 寫進同一個 append-only ledger。

### 7.1 Ledger 格式

位置：`platformdirs.user_data_dir("ai_core")/calls.jsonl`

每行一個 JSON record：

```json
{
  "id": "01J...ulid",
  "parent_id": "01J...ulid",
  "ts": "2026-04-28T15:42:01.123Z",
  "duration_ms": 842,
  "caller": {"type": "user|function|agent", "name": "ai-core-author"},
  "callee": {"name": "ai-core-call", "args_summary": "--entry gemini-flash --input /tmp/x.txt --output /tmp/y.txt"},
  "status": "ok|error",
  "output_summary": "23 chars: 'hello, this is gemini speaking...'",
  "tokens": {"input": 42, "output": 17, "cost_usd": 0.0001},
  "error": null
}
```

`args_summary` 與 `output_summary` 是**摘要**（避免 ledger 爆炸；長內容用 path 引用）；完整內容需要時可從 `--output` 指定的檔取。

### 7.2 Parent / child 關係如何傳遞

關鍵機制：**環境變數 `AI_CORE_PARENT_CALL_ID`**

- 任何函式啟動時，會檢查環境變數 `AI_CORE_PARENT_CALL_ID`，作為自身 record 的 `parent_id`
- 函式 spawn 子 process 呼叫其他函式時，把自己的 `call_id` 設給子 process 的同名環境變數
- `protocol/metadata.py` 提供 `wrap_call(...)` helper，自動處理 record 寫入與環境變數傳遞，避免每個 function 重寫樣板

這樣 ledger 自然形成樹狀，不需要 caller 顯式傳 ID。

### 7.3 查詢工具：`ai-core-trace`

```bash
ai-core-trace --recent 20                      # 最近 20 筆
ai-core-trace --tree <call_id>                 # 該 call 的完整子樹
ai-core-trace --func ai-core-call --since 1h   # 某 func 過去 1 小時的呼叫
ai-core-trace --errors --since 1d              # 過去 24h 的失敗
ai-core-trace --tree <id> --format dot         # 輸出 graphviz dot
```

第一版輸出純文字 tree（縮排顯示）。HTML / web UI 之後再說。

---

## 8. Function Hub 設計

兩種形態並存（共用同一份函式掃描邏輯）：

### 8.1 One-shot 版（`ai-core-hub`）

KISS、無狀態、適合 CI / build pipeline / 離線生成 skill bundle：

```bash
ai-core-hub --build-list ./funcs/* > list.txt
ai-core-hub --export mcp ./funcs/* > skills.mcp.json
ai-core-hub --export openai-tools ./funcs/* > tools.json
ai-core-hub --export anthropic-tools ./funcs/* > tools.json
```

### 8.2 Server 版（`ai-core-hub-server`）

常駐，提供 runtime discovery：

| 端點 | 用途 |
|---|---|
| `GET /funcs?detail=summary` | 列所有函式（短資訊，給 AI scan） |
| `GET /funcs?detail=full` | 列所有函式（完整 metadata） |
| `GET /funcs/<name>` | 單一函式完整 metadata |
| `GET /search?q=...` | 對 description 做關鍵字 / LLM 語意搜尋（後者透過 ai-core-call 自舉） |
| `POST /funcs/<name>/call` | 代理執行（自動寫 ledger） |
| `GET /graph` | 函式依賴圖（從 metadata 的 `dependencies` 累積） |
| `GET /export?format=mcp\|openai-tools\|anthropic-tools` | runtime export |

### 8.3 對 metadata 缺漏的處理

完全遵守 §4.6 的容錯規則。Hub 在 list / API 中對缺漏項標警告但仍列出函式。

### 8.4 list.txt 的 LLM 摘要（對抗 context 爆炸）

當函式集大到 list.txt 自己會撐爆 context 時，Hub 透過 `ai-core-call` 對每個函式的 description 自動產出更短的 summary（覆蓋或補上 `summary` 欄）— **真正的自舉**。

### 8.5 Scanner 掃描策略

```bash
ai-core-hub --build-list ./funcs/               # 掃指定目錄下所有可執行檔
ai-core-hub --build-list ./funcs/ --ext .sh,.py # 改為副檔名過濾
ai-core-hub --build-list ./funcs/ --recursive   # 遞迴子目錄（預設只掃頂層）
```

**掃描邏輯**：

1. 列出指定路徑下的檔案
2. 過濾（擇一）：
   - 預設：有可執行位元（`os.access(path, os.X_OK)`）
   - `--ext`：符合指定副檔名（不再要求可執行位元）
3. 對每個候選呼叫 `<file> --metadata`，以 §4.6 容錯規則處理回應
4. 彙總成 function 清單

**Server 類工具的處理原則**：
Scanner 掃的是 **wrapper CLI**（如 `ai-core-call`），而非 server 程序本身。wrapper 的 `--metadata` 已代表整個工具的能力；hub 不需要知道底層是否有常駐 server，統一透過 wrapper 介面取 metadata。

---

## 9. ai-core-author 設計（讓 AI / 人類製作新函式）

> 一站式工具：從「我想要一個能做 X 的 function」到「funcs/foo.sh 已註冊並通過驗證」。

### 9.1 流程

```
caller (人 or AI) 提供：
    {name, description, examples: [{input, output}], language?: "bash|python|..."}
        │
        ▼
[1] 呼叫 ai-core-call 產出 function 骨架 + metadata（含 examples 抄回 metadata）
        │
        ▼
[2] dry-run：把 examples 一筆筆當輸入跑，比對輸出
        │
        ├─ 通過 ──▶ [3] 註冊
        │
        └─ 失敗 ──▶ 把錯誤回給 LLM，最多重試 N 輪
        │
        ▼
[3] 寫入 funcs/<name>.<ext> 或 small_funcs registry
[4] 自動跑 --metadata 確認協議遵守
[5] 在 ledger 留下 authoring record（含使用的 prompt、迭代次數）
```

### 9.2 為什麼 dry-run 是強制的

- 防止 AI 寫出「看起來對、實際亂跑」的 function 進入 registry
- 提供人類看 ledger 時的信心：「這個 function 已通過 N 個範例驗證」
- 沒有 examples 的 author 請求會被拒絕（或退化為「人類事後手動驗證」模式）

### 9.3 CLI

```bash
ai-core-author --spec spec.json                    # spec 含 name/description/examples
ai-core-author --spec spec.json --language python  # 指定語言
ai-core-author --spec spec.json --dry-run-only     # 不註冊只驗證
ai-core-author --spec spec.json --target funcs/    # 指定註冊位置
```

`ai-core-author` 自身遵守 `--metadata` 協議（讓 AI 也能透過 hub 發現它，從而要求另一個 AI 寫新 function — 函式自我增殖）。

---

## 10. Small Function Center (SFC) 設計

**定位**：SFC 是一種 dispatcher pattern，把大量邏輯相關的微小函式集中到一個 entrypoint，避免 hub 清單因每個 one-liner 都變成獨立檔案而膨脹。

**這不是一個固定實作，而是一個慣例**：任何提供「透過某個 CLI 參數選項呼叫子函式」能力的工具都可算作 SFC；旗標名稱不強制為 `--call`，由實作者自行決定。

### 10.1 最小合約（唯一強制）

```bash
<sfc-name> <dispatch-flag> <func_name> [--input X] [--output Y]   # 呼叫子函式
<sfc-name> --metadata                                               # 描述 SFC 自身
```

`dispatch-flag` 的名稱（`--call`、`--run`、`--invoke`…）由實作者自訂；metadata 的 `usage` 欄位說明實際用法。I/O 慣例、stderr 錯誤、exit code 同全系統標準（§5）。

### 10.2 建議額外介面（強烈建議，不強制）

```bash
<sfc-name> --list                                      # 列出所有子函式名稱
<sfc-name> <dispatch-flag> <func_name> --metadata      # 查詢某子函式的 metadata
```

**子函式 metadata 查詢**（`<dispatch-flag> <func_name> --metadata`）強烈建議實作，原因：
- hub scanner 呼叫 `--list` 展開子函式後，還需要各子函式的 metadata 才能讓 AI 理解用法
- 缺少此介面，hub 只能列出子函式名稱，無法提供 summary / io / examples 等慣例欄位

**實作方式（二擇一）**：

| 方式 | 說明 | 適用 |
|---|---|---|
| **Pass-through** | SFC 把 `--metadata` 直接轉給底層子函式執行（子函式本身輸出 JSON） | 子函式是獨立可執行檔，自身遵守 `--metadata` 協議 |
| **SFC 自管** | SFC 內部維護各子函式的 metadata，收到查詢時自行輸出 | 子函式是 SFC 內的 Python function 或 bash snippet，無法獨立執行 |

`--list` 的存在讓 hub scanner 能把子函式分別展開列入清單；若 `--list` 與 metadata 查詢都不支援，hub 只收錄 SFC 本身。

### 10.3 可擴充性建議

SFC 應讓新增子函式**不需修改核心程式碼**：

| 語言 | 建議方式 |
|---|---|
| Python | 子函式各自是獨立 `.py` module，放到指定目錄，SFC 啟動時自動 import / 動態掛載 |
| Bash | 子函式各自是獨立 `.sh`，SFC 做 `case` 分派或 source |
| 其他 | 只要新增子函式不改動 SFC 核心即可，實作自由 |

**內部管理**（registry file、動態掃描目錄、hardcode dict…）完全自由，取決於使用情境。

### 10.4 與 hub 的整合

hub scanner（§8.5）遇到 SFC 時：
- 若 SFC 支援 `--list` → 展開子函式，各自作為獨立 function 列出
- 若不支援 → 只列出 SFC 本身，標 `"type": "sfc"`

---

## 11. 目錄結構

```
ai_core/
├── pyproject.toml
├── README.md
├── CLAUDE.md / thinking.md（已存在）
├── docs/
│   └── ARCHITECTURE.md（本檔）
├── src/ai_core/
│   ├── entry_manager/      # ai-core-server
│   │   ├── server.py
│   │   ├── queue.py
│   │   ├── ratelimit.py
│   │   ├── backends.py
│   │   └── cli.py
│   ├── client/             # ai-core-call (entry manager wrapper)
│   │   └── cli.py
│   ├── hub/
│   │   ├── scanner.py      # 共用函式掃描 / metadata fetch 邏輯
│   │   ├── exports.py      # mcp / openai-tools / anthropic-tools 格式轉換
│   │   ├── server.py       # ai-core-hub-server
│   │   └── cli.py          # ai-core-hub (one-shot)
│   ├── small_funcs/
│   │   ├── registry.py
│   │   ├── funcs/
│   │   └── cli.py          # ai-core-sfc
│   ├── author/             # ai-core-author
│   │   ├── generator.py    # 透過 ai-core-call 產 function 骨架
│   │   ├── dryrun.py
│   │   └── cli.py
│   ├── trace/              # ai-core-trace
│   │   ├── ledger.py       # 寫 / 讀 jsonl
│   │   └── cli.py
│   └── protocol/
│       ├── metadata.py     # fetch_metadata、wrap_call、--json-errors helper
│       └── env.py          # AI_CORE_PARENT_CALL_ID 等環境變數
├── funcs/                  # 範例外部函式
│   └── echo.sh
└── tests/
```

---

## 12. CLI 入口（`pyproject.toml`）

```toml
[project.scripts]
ai-core-server      = "ai_core.entry_manager.cli:main"
ai-core-call        = "ai_core.client.cli:main"
ai-core-hub         = "ai_core.hub.cli:main"             # one-shot
ai-core-hub-server  = "ai_core.hub.server:main"          # 常駐
ai-core-sfc         = "ai_core.small_funcs.cli:main"
ai-core-author      = "ai_core.author.cli:main"
ai-core-trace       = "ai_core.trace.cli:main"
```

跨平台都能用，不依賴 shebang。

---

## 13. 配置範例

位置：`platformdirs.user_config_dir("ai_core")/config.json`

- Linux：`~/.config/ai_core/config.json`
- Windows：`%APPDATA%\ai_core\config.json`

```json
{
  "server": {"host": "127.0.0.1", "port": 5577},
  "hub_server": {"host": "127.0.0.1", "port": 5578},
  "ledger_path": null,
  "models": {
    "ollama-llama3": {
      "backend": "ollama",
      "model": "llama3",
      "base_url": "http://localhost:11434"
    },
    "lmstudio-local": {
      "backend": "openai",
      "model": "local-model",
      "base_url": "http://localhost:1234/v1",
      "api_key": "not-needed"
    },
    "gemini-flash": {
      "backend": "gemini",
      "model": "gemini-2.0-flash",
      "api_key_env": "GEMINI_API_KEY",
      "limits": {"rpm": 15, "tokens_per_day": 1000000, "cost_per_day": 5.0},
      "concurrency": 5
    }
  }
}
```

`ledger_path = null` 表示走預設 `user_data_dir("ai_core")/calls.jsonl`。

---

## 14. 開發里程碑

### M0 — 骨架與協議（半天 ~ 一天）
- [ ] `pyproject.toml` + `uv` lockfile
- [ ] 7 個 CLI entrypoint 空殼
- [ ] `protocol/metadata.py`：`fetch_metadata`（含容錯）、`wrap_call`、`--json-errors` helper
- [ ] 範例 `funcs/echo.sh` 支援 `--input/--output/--metadata`
- [ ] 測試：`--metadata` 容錯（缺欄位 / 不合法 JSON / 函式根本不支援，都 graceful）

### M1 — Entry Manager MVP
- [ ] FastAPI server + `/call`、`/tasks/<id>`、`/status`、`/entries`、`/entries/<name>/metadata`
- [ ] litellm 接通三個 backend（ollama / lm studio / gemini）
- [ ] per-model asyncio queue + worker
- [ ] `ai-core-call` wrapper（同步 + `--async` 模式）
- [ ] **Dogfood**：`ai-core-call` 自身實作 `--metadata` 與 `--entry-metadata`

### M2 — Calling Chain Ledger
- [ ] `trace/ledger.py`：append-only JSONL 寫入、ULID id、parent 關係
- [ ] `protocol/metadata.py:wrap_call` 串進 entry manager wrapper
- [ ] `ai-core-trace` CLI：`--recent`、`--tree`、`--func`、`--errors`
- [ ] 環境變數 `AI_CORE_PARENT_CALL_ID` 跨 process 傳遞測試

### M3 — Rate limit + 真實 backend 測試
- [ ] rpm / tokens / cost 限制與超限 stderr
- [ ] `--json-errors` 旗標
- [ ] 對 ollama / lm studio / gemini 各跑通一次
- [ ] 失敗重試與排隊降級

### M4 — Function Hub（雙形態）
- [ ] `hub/scanner.py`：掃描 + 容錯抓 metadata
- [ ] `ai-core-hub`（one-shot）：`--build-list`
- [ ] `hub/exports.py`：mcp / openai-tools / anthropic-tools 三種 export
- [ ] `ai-core-hub-server`：runtime discovery API（含 `/funcs`、`/search`、`/graph`、`/export`）
- [ ] 用 `ai-core-call` 自己對 list.txt 做摘要 — 自舉

### M4.5 — Agent Docs 自動化
- [ ] `ai-core-hub --gen-agent-md > AGENTS.md`（產生通用 agent 入口文件）
- [ ] `ai-core-hub --gen-functions-md > auto/FUNCTIONS.md`（產生函式清單）
- [ ] `ai-core-hub --export claude-skill` 產生 `auto/skills/<name>/SKILL.md`
- [ ] `ai-core-author` 成功註冊後自動觸發 `--gen-functions-md` + `--gen-agent-md`，讓 `auto/` 永遠最新
- [ ] `auto/` 目錄內容納入 CI / pre-commit 驗證（與 `funcs/` 一致性）

### M5 — Small Function Center（參考實作 `ai-core-sfc`）
- [ ] 子函式機制（Python 模組動態 import / 掛載；新增子函式不需改核心）
- [ ] dispatch CLI：`ai-core-sfc <dispatch-flag> <name> --input X --output Y`（旗標名稱由實作者決定）
- [ ] SFC 自身的 `--metadata`
- [ ] `--list` 列出子函式名稱
- [ ] 子函式 metadata 查詢（pass-through 或 SFC 自管，二擇一）
- [ ] hub scanner 整合測試：能正確展開 SFC 內所有子函式

### M6 — ai-core-author（自舉）
- [ ] `--spec` 介面 + dry-run + 註冊流程
- [ ] 多語言骨架產出（先支援 bash / python）
- [ ] 失敗回饋 LLM 重試機制
- [ ] author 自身遵守 `--metadata`，可被其他 AI 透過 hub 發現

### M7 — calling pack 範例集 + README
- [ ] `llm_call_coding_question` 等典型 calling pack 範例
- [ ] README 教學（人類視角 + AI agent 視角）

---

## 15. 跨平台注意事項

1. 路徑全用 `pathlib.Path`，不寫死 `/` 或 `\`
2. Subprocess 一律 `shell=False` + list args（避開 Windows quote 地獄）
3. 檔案 I/O 強制 `encoding="utf-8"`
4. CLI 透過 `[project.scripts]`，不依賴 shebang
5. Server port 衝突：第一版只做 TCP（unix socket / named pipe 留待未來）
6. config / data dir 一律走 `platformdirs`
7. ledger 寫入 lock：用 `fcntl`（Linux）+ `msvcrt`（Windows）寫薄 wrapper，或乾脆用單行原子 append（POSIX `O_APPEND` + Windows 對應）

---

## 16. Agent 整合與文檔策略

ai_core 初期使用方式是「人類 + 現成 AI agent（Claude Code / Cline / Cursor / Aider / ...）+ ai_core function」三方協作。**長期目標是 function 集合成熟到能替代 agent 的部分功能** — 這條演進路徑要求文檔系統從一開始就把 agent 當一級讀者。

### 16.1 文檔分層

```
ai_core/
├── README.md              # 人類入口；快速上手 + 用例
├── CLAUDE.md              # Claude Code 專用入口（已存在）
├── AGENTS.md              # 通用 agent 入口；任何 agent 進專案先讀這個
├── docs/
│   ├── ARCHITECTURE.md    # 設計（本檔）；給開發者 / 想深入的 agent
│   ├── OPEN_QUESTIONS.md  # 已識別、尚未進入主架構的設計缺口
│   └── EVOLUTION.md       # （待建）從 agent-assisted 到 self-sufficient 的演進路徑
└── auto/                  # 由 ai-core-hub 產生 / 更新，不手寫
    ├── FUNCTIONS.md       # 所有 function 清單與用法（人類 + agent 兩用）
    ├── CHAINS.md          # 常見 calling chain pattern（從 ledger 自動萃取）
    ├── tools.openai.json  # OpenAI tools schema export
    ├── tools.anthropic.json
    ├── server.mcp.json    # MCP server descriptor
    └── skills/            # Claude Code skills 格式
        └── <func_name>/
            └── SKILL.md
```

**手寫 vs 自動產生**：手寫文件描述「設計與哲學」（少變動）；自動產生文件描述「目前能力」（隨 function 集合變動）— 兩者分開避免手動同步。

### 16.2 AGENTS.md 結構

新增專案根目錄的 `AGENTS.md` 作為通用 agent 入口（不只給 Claude Code，所有 agent 都看這個）。建議模板：

```markdown
# AI Core — Agent Guide

## 你能用 ai_core 做什麼
- 呼叫 LLM             → ai-core-call --entry <model> --input X --output Y
- 列出可用 function    → ai-core-hub --build-list   或   GET hub-server /funcs
- 製作新 function      → ai-core-author --spec spec.json
- 追溯 calling chain   → ai-core-trace --tree <call_id>

## 進入專案後的建議流程
1. 跑 `ai-core-hub --build-list` 拿到當前 function 清單
2. 對任一 function 不確定用法時：`<func> --metadata`
3. 需要 LLM 推理：呼 `ai-core-call`
4. 需要新能力且確定要寫 function：呼 `ai-core-author`，**不要直接手寫到 funcs/**
5. 想追溯某次呼叫的 chain：`ai-core-trace --tree <call_id>`

## 行為規範
- 每個 function 都應遵守 --metadata 協議；不確定先看 metadata
- 錯誤訊息走 stderr；機器可解析錯誤加 `--json-errors` 旗標
- 任何 function 呼叫都會被自動記入 ledger；人類可隨時審計
- 環境變數 AI_CORE_PARENT_CALL_ID 由系統自動傳遞，agent 不需手動處理

## Tool calling schema（給支援 native tool calling 的 agent）
- OpenAI format    → auto/tools.openai.json
- Anthropic format → auto/tools.anthropic.json
- MCP server       → auto/server.mcp.json
```

`AGENTS.md` 由 `ai-core-hub --gen-agent-md > AGENTS.md` 產生，並在 function 集合變動時可重新跑。

### 16.3 Hub `--export` 支援的 agent 格式

| 格式 | 用途 | 對應 agent |
|---|---|---|
| `openai-tools` | OpenAI tools schema | GPT、Cursor、Aider 等 |
| `anthropic-tools` | Anthropic tools schema | Claude API |
| `mcp` | MCP server descriptor | Claude Desktop、MCP-aware client |
| `claude-skill` | Claude Code skills（`SKILL.md` + frontmatter） | Claude Code |
| `agent-md` | 通用 markdown agent guide（產生 AGENTS.md） | 任何 agent |
| `functions-md` | 函式清單 markdown（產生 auto/FUNCTIONS.md） | 任何 agent / 人類 |

```bash
ai-core-hub --export openai-tools ./funcs/* > auto/tools.openai.json
ai-core-hub --export claude-skill ./funcs/* --out auto/skills/
ai-core-hub --gen-agent-md > AGENTS.md
ai-core-hub --gen-functions-md > auto/FUNCTIONS.md
```

Server 版（`ai-core-hub-server`）對應端點：`GET /export?format=...`、`GET /agents-md`、`GET /functions-md`。

### 16.4 自動文檔更新時機

設計三個觸發點：

1. **手動**：使用者 / agent 跑 `ai-core-hub --gen-*`
2. **註冊時觸發**：`ai-core-author` 註冊新 function 後自動跑 `--gen-functions-md` 與 `--gen-agent-md`，讓 auto/ 永遠最新
3. **CI / pre-commit**（可選）：把 `auto/` 視為產出物，`pre-commit` hook 驗證它與當前 funcs/ 一致

### 16.5 Self-Sufficiency 演進路徑

詳細路線圖待後續展開（規劃寫成 `docs/EVOLUTION.md`，目前尚未建立）。本節先給概念輪廓：

| 階段 | 狀態 | agent 角色 | ai_core 重點 |
|---|---|---|---|
| 1. Agent-assisted | function 集合稀少 | 主導；人類提需求、agent 直接做 | 提供 LLM 入口、author 工具、ledger |
| 2. Function-rich | function 豐富、多數任務有對應 function | orchestrator；決定組哪些 function | calling chain template、語意搜尋 |
| 3. Self-sufficient | 常用任務有 chain template | 輕薄 router 或不需要 | chain 自動萃取、ai-core-author 自動發現重複模式 |

第一版（M0–M7）專注階段 1。階段 2 / 3 等真實使用模式累積後再設計，不預先過度工程。

### 16.6 與現成 agent 的整合 hint

ai_core 不深度耦合任何特定 agent，但提供慣例配置降低接入摩擦：

| Agent | 整合方式 |
|---|---|
| Claude Code | 已有 `CLAUDE.md`；可選 `auto/skills/` 載入為 skills |
| Cursor | `.cursorrules` 指向 `AGENTS.md` |
| Aider | `.aider.conf.yml` 把 `AGENTS.md` 加進 context |
| Cline | 同 Cursor，讀 `AGENTS.md` |
| MCP client | 啟動 `ai-core-hub-server` 並用 `auto/server.mcp.json` |

這些是文件層的接入；底層 function 不變。

---

## 17. 變更紀錄

- 2026-04-28：初版定稿。涵蓋四個元件、queue 流程、stderr 錯誤慣例、跨平台選型。
- 2026-04-28：新增 `io` 慣例 key 描述函式 I/O 風格。
- 2026-04-28：將「常駐 server + queue」抽象為 **Singleton Resource Manager Pattern**（§1）；Entry Manager 補上 `--entry-metadata` 與 `/entries/*` HTTP 端點。
- 2026-04-28：明確定位為 **AI 80% / 人類 20%**，新增 §7 **Calling Chain Observability**（ledger + ai-core-trace）；Function Hub 拆為 **server + one-shot 雙形態**（§8）；新增 §9 **ai-core-author**（讓 AI / 人類產生新 function，含 dry-run）；§4.6 補 metadata **容錯與降級**規則；§5.1 補 `--json-errors` 旗標；§1 補 Singleton Resource Manager 必須**配套 shell wrapper CLI**。里程碑重排為 M0–M7。
- 2026-04-28：新增 §15 **Agent 整合與文檔策略**（AGENTS.md / auto-generated docs / claude-skill 與 agent-md export 格式 / Self-Sufficiency 演進階段）。里程碑加 M4.5（agent docs 自動化）。
- 2026-04-28：依 `thinking.md` 補完四個缺口：①§1 補 Singleton Pattern 兩種亞型（entry-managing vs. simple singleton）；②§4.7 新增 **entrydata 介面宣告**（metadata 是唯一入口，`has_entries` + `entry_interface` 告知 caller 還有 entrydata 可用）；③§6.2 / §6.4 / §6.8 補 **佇列等待逾時**機制（`time_to_wait_ms`、`--wait` 旗標、408 回應）；④§13 補 M4.5 milestone 完整內容。
- 2026-04-28：釐清三個設計決策並更新文件：①§5.2 補 server 未啟動的錯誤行為（wrapper 直接 stderr + exit 1，不做 auto-start）；②移除 §7.4 `--preview-chain`（不在計劃內）；③§8.5 新增 **Hub Scanner 掃描策略**（可執行檔 / 副檔名過濾、遞迴選項、server 類工具掃 wrapper 而非 server 本身）。
- 2026-04-28：新增 §10 **Small Function Center (SFC) 設計**。SFC 是 dispatcher pattern 而非固定實作：分派子函式的 CLI 參數旗標由實作者自訂（不強制為 `--call`）；最小合約只要求能呼叫子函式 + `--metadata`；建議支援 `--list` 以利 hub 展開子函式；可擴充性優先（Python 動態 import / Bash case 分派等），內部管理完全自由。章節號碼因插入 §10 整體遞增（原 §10–§16 → §11–§17）。
- 2026-04-28：A 類修正（內部一致性）：①§16 內部子節編號從 §15.X 補正為 §16.X；②§16.2 AGENTS.md 模板移除已廢除的 `--preview-chain`，改為 `ai-core-trace --tree`；③§14 M5 里程碑反映 §10 設計（dispatch flag 名稱不強制、補上 `--list` 與子函式 metadata 查詢）；④§16.1 / §16.5 將不存在的 `EVOLUTION.md` 標為待建。新增 `docs/OPEN_QUESTIONS.md` 追蹤已識別但尚未處理的 B / C 類設計缺口。
- 2026-04-28：處理 B1（Streaming output）→ §6.9。`ai-core-call --stream` 即時把 token 吐到 stdout；`--stream` 模式下 `--output` 變可選，若給則完成後 atomic 寫入；`--stream --async` 不允許；HTTP 採 chunked transfer encoding；`time_to_wait_ms` 只算 queue 等待時間。
- 2026-04-28：處理 B2（Messages / chat history 介面）→ §6.10。協議層只強制 `--input <file>`，內容自動包成單一 user message；多輪對話、system prompt 等狀態由 caller 自己管理（不在 wrapper 內）；`--system` / `--messages` / `--append` 等都是 wrapper 實作層的可選 sugar，不在協議強制範圍。需要超出 sugar 的能力可直接走 HTTP。
- 2026-04-28：處理 B3（Server 生命週期）→ §4.8 + §5.2。架構不規範 server 啟動方式（前景執行、daemon 化交給使用者用系統工具）。新增 §4.8 server-backed wrapper 的可選 metadata 註解：`server.activation`（`usually-on` / `rarely-on` / `default-off`）+ `server.activation_hint`，讓 hub 顯示給 caller。註解不影響 wrapper 行為，server 沒啟動仍照 §5.2 直接報錯。
- 2026-04-28：處理 B4（雲端 model 並行呼叫）→ §6.6 / §6.5 / §13。entry config 新增 `concurrency` 欄位（預設 1，向後相容）；§6.6 queue 實作改為每條 queue 配 N 個 worker；本地 GPU 受限模型維持 1，雲端 stateless API 可設 N 並行；rate limit 仍在入 queue 前檢查；`--entry-metadata` 暴露 `concurrency` 與 `active_workers`。靜態配置，改值需重啟 server。
