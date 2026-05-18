# AI Core — LLM Entry Manager 設計

> §1「Singleton Resource Manager Pattern」的首個實例 — server (`ai-core-server`) + wrapper CLI (`ai-core-call`) 雙元件。

## §6. LLM Entry Manager 設計

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
- `POST /call` → 建立 task；`{model, messages, options, async, time_to_wait_ms?}`
- `GET /tasks/<id>` → 查詢狀態
- `GET /tasks/<id>/result` → 取結果
- `GET /status` → 所有 queue 與 quota 狀態
- `GET /entries` → 列出所有 entry
- `GET /entries/<name>` → 單一 entry 的 metadata（給 `--entry-metadata` 用）
- 本機 token 認證（詳見 §6.13）

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

### 6.11 Server 自身 Log

server 的啟動訊息、worker 例外、queue 狀態等運作日誌（**非** ledger），走以下規則：

| 旗標 | 行為 |
|---|---|
| 預設 | 寫到 stderr（前景執行時最直覺，daemon 化由使用者自行重導） |
| `--log-file <path>` | 同時寫到指定檔案（適合 tmux / nohup 常駐） |
| `--log-level <level>` | `debug` / `info` / `warning` / `error`，預設 `info` |

Log rotation 不由 server 管理：使用者若需要可搭配 `logrotate`（Linux）或系統工具；第一版不內建 rotation 機制（KISS）。

### 6.12 Server 重啟行為

第一版**不 persist 任何 task 到磁碟**，所有 queue 狀態純 in-memory：

| 情境 | 行為 |
|---|---|
| sync wrapper 等待中、server 被 kill | wrapper 偵測到 `ConnectionError` → stderr 報錯 + exit 1；caller 自行決定是否重試 |
| async task id 在 server 重啟後查詢 | server 回 404；caller 視為任務遺失，需重新提交 |
| 正在執行的 LLM 呼叫（worker 已取出）| 中斷，結果丟失；無自動恢復 |

**設計取捨**：Task persistence 增加複雜度（序列化、crash recovery、ID 衝突），與 KISS 原則相悖。第一版讓 caller 負責重試邏輯；若未來使用場景顯示這是主要痛點，再評估加入。

### 6.13 本機 Token 認證

token 只在本機環境（127.0.0.1）使用，安全暴露面低，設計從簡：

- **生成時機**：server 首次啟動時自動產生隨機 token（`secrets.token_hex(32)`），寫入 `user_config_dir("ai_core")/token`，權限設為 `0600`（Unix）或 ACL 限制當前使用者（Windows）
- **Wrapper 讀取方式**：優先讀 `AI_CORE_TOKEN` 環境變數；未設定則從預設路徑讀檔
- **傳遞方式**：`Authorization: Bearer <token>` HTTP header
- **Rotation**：第一版不內建 rotation；需要時手動刪除 token 檔再重啟 server 即可
