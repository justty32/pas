# AI Core — ai-core-author 與 Small Function Center 設計

## §8. ai-core-author 設計（讓 AI / 人類製作新函式）

> 一站式工具：從「我想要一個能做 X 的 function」到「funcs/foo.sh 已註冊並通過驗證」。

**Calling Pack 說明**：Calling pack 是一種常見的 function 模式，把固定的 system prompt / context 與 LLM 呼叫封裝成一個具名 function（例如 `llm_call_coding_question.sh`）。實作上就是普通獨立 function，放在 `funcs/`，通常由 `ai-core-author` 產生後再手調 prompt。**不需要新的架構概念**。

### 8.1 流程

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
[3] 寫入 funcs/<name>.<ext> 或 SFC registry（見 §8.3）
[4] 自動跑 --metadata 確認協議遵守
[5] 在 ledger 留下 authoring record（含使用的 prompt、迭代次數）
```

### 8.2 為什麼 dry-run 是強制的

- 防止 AI 寫出「看起來對、實際亂跑」的 function 進入 registry
- 提供人類看記錄時的信心：「這個 function 已通過 N 個範例驗證」
- 沒有 examples 的 author 請求會被拒絕（或退化為「人類事後手動驗證」模式）

### 8.3 CLI

```bash
ai-core-author --spec spec.json                    # 寫成獨立 function（預設）
ai-core-author --spec spec.json --language python  # 指定語言
ai-core-author --spec spec.json --dry-run-only     # 不註冊只驗證
ai-core-author --spec spec.json --target ./funcs/  # 指定輸出目錄
ai-core-author --spec spec.json --target sfc --sfc <sfc-name>  # 塞進指定 SFC
```

**獨立 function 還是 SFC 子函式？**
預設寫成獨立 function（`funcs/<name>.<ext>`）。需要塞進 SFC 時，spec 裡加 `"target": "sfc"` 並帶 `--sfc <sfc-name>`；author 會呼叫該 SFC 的 registry 介面而非直接寫檔。一般函式邏輯簡單且獨立時選獨立 function；屬於同一工具域的微小 one-liner 集合時才考慮 SFC。

**`funcs/` 預設路徑與跨專案使用**：
預設輸出至 `user_data_dir/ai_core/funcs/`（與 `ai-core-hub` 預設掃描路徑一致）。跨專案使用時有兩種方式：以 `--target <path>` 明確指定，或設定 `AI_CORE_FUNCS_DIR` 環境變數讓兩個工具共用同一路徑。

`ai-core-author` 自身遵守 `--metadata` 協議（讓 AI 也能透過 hub 發現它，從而要求另一個 AI 寫新 function — 函式自我增殖）。

---

## §9. Small Function Center (SFC) 設計

**定位**：SFC 是一種 dispatcher pattern，把大量邏輯相關的微小函式集中到一個 entrypoint，避免 hub 清單因每個 one-liner 都變成獨立檔案而膨脹。

**這不是一個固定實作，而是一個慣例**：任何提供「透過某個 CLI 參數選項呼叫子函式」能力的工具都可算作 SFC；旗標名稱不強制為 `--call`，由實作者自行決定。

### 9.1 最小合約（唯一強制）

```bash
<sfc-name> <dispatch-flag> <func_name> [--input X] [--output Y]   # 呼叫子函式
<sfc-name> --metadata                                               # 描述 SFC 自身
```

`dispatch-flag` 的名稱（`--call`、`--run`、`--invoke`…）由實作者自訂；metadata 的 `usage` 欄位說明實際用法。I/O 慣例、stderr 錯誤、exit code 同全系統標準（§5）。

### 9.2 建議額外介面（強烈建議，不強制）

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

### 9.3 可擴充性建議

SFC 應讓新增子函式**不需修改核心程式碼**：

| 語言 | 建議方式 |
|---|---|
| Python | 子函式各自是獨立 `.py` module，放到指定目錄，SFC 啟動時自動 import / 動態掛載 |
| Bash | 子函式各自是獨立 `.sh`，SFC 做 `case` 分派或 source |
| 其他 | 只要新增子函式不改動 SFC 核心即可，實作自由 |

**內部管理**（registry file、動態掃描目錄、hardcode dict…）完全自由，取決於使用情境。

### 9.4 與 hub 的整合

hub scanner（§7.5）遇到 SFC 時：
- 若 SFC 支援 `--list` → 展開子函式，各自作為獨立 function 列出
- 若不支援 → 只列出 SFC 本身，標 `"type": "sfc"`
