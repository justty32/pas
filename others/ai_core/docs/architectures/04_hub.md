# AI Core — Function Hub 設計

## §7. Function Hub 設計

兩種形態並存（共用同一份函式掃描邏輯）：

### 7.1 One-shot 版（`ai-core-hub`）

KISS、無狀態、適合 CI / build pipeline / 離線生成 skill bundle：

```bash
ai-core-hub --build-list ./funcs/* > list.txt
ai-core-hub --export mcp ./funcs/* > skills.mcp.json
ai-core-hub --export openai-tools ./funcs/* > tools.json
ai-core-hub --export anthropic-tools ./funcs/* > tools.json
```

### 7.2 Server 版（`ai-core-hub-server`）

常駐，提供 runtime discovery：

| 端點 | 用途 |
|---|---|
| `GET /funcs?detail=summary` | 列所有函式（短資訊，給 AI scan） |
| `GET /funcs?detail=full` | 列所有函式（完整 metadata） |
| `GET /funcs/<name>` | 單一函式完整 metadata |
| `GET /search?q=...` | 對 description 做關鍵字 / LLM 語意搜尋（後者透過 ai-core-call 自舉） |
| `POST /funcs/<name>/call` | 代理執行 |
| `GET /graph` | 函式依賴圖（從 metadata 的 `dependencies` 累積） |
| `GET /export?format=mcp\|openai-tools\|anthropic-tools` | runtime export |

### 7.3 對 metadata 缺漏的處理

完全遵守 §4.6 的容錯規則。Hub 在 list / API 中對缺漏項標警告但仍列出函式。

### 7.4 list.txt 的 LLM 摘要（對抗 context 爆炸）

當函式集大到 list.txt 自己會撐爆 context 時，Hub 透過 `ai-core-call` 對每個函式的 description 自動產出更短的 summary（覆蓋或補上 `summary` 欄）— **真正的自舉**。

### 7.5 Scanner 掃描策略

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
