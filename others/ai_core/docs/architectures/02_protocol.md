# AI Core — metadata 協議與錯誤處理慣例

## §4. metadata 協議（極簡版）

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

**各 `io` 型態補充範例：**

`io.input = "args"`（引數直接傳入）：

```json
{
  "name": "greet",
  "summary": "對指定名字輸出問候語",
  "io": {"input": "args", "output": "stdout"},
  "usage": "greet.sh --name Alice"
}
```

`io.input = "none"`（無需輸入）：

```json
{
  "name": "list-models",
  "summary": "列出 ai-core-server 目前已設定的 model 清單",
  "io": {"input": "none", "output": "stdout", "format": {"output": "json"}}
}
```

`io.output = "none"`（純副作用，無正常輸出）：

```json
{
  "name": "cleanup-cache",
  "summary": "清除本地快取檔案",
  "io": {"input": "args", "output": "none"},
  "usage": "cleanup-cache.sh --older-than 30d"
}
```

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
    "entry_http_endpoint": "GET /entries/<name>",
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

## §5. 錯誤處理慣例（全系統統一）

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
