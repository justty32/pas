# thinking_layers.md

新想法紀錄（2026-05-20）

---

## 核心框架：用「用途」而非「層」定義結構

系統的結構由**執行模型（execution model）**決定，不是由技術層次決定。
沿著兩個軸展開：

|  | one-shot（請求完就結束） | persistent（持續存在） |
|---|---|---|
| **不管資源** | shell pipe / script | — |
| **管資源** | one-shot 程式 | 持續性程式 |
| **管併發** | — | server |

Hub 是橫切的——它是這些東西的目錄與彙整，不屬於哪一格。

---

## 各執行模型說明

### pipe-and-script
外部工具、輕量、快速、命令行操作。直接用 shell pipe 串接，頂多加 shell script 做膠水黏合。

```bash
professor.sh --type "senior c coder" \
  | modify_c_code_segment.sh --file main.c --line 44-55 --prompt "no pointer" \
  | code_linter.sh --lang c \
  > new_main.c
```

不在乎執行時間與記憶體，隨手可用，用什麼語言實作都可以。

### one-shot
需要記憶體或執行時間管理的單次程式。請求進來、處理完、結束。可以用任何語言寫，但此時 shell script 已不夠用。仍可被 pipe 串接或直接呼叫。

### persistent
需要多輪複雜狀態保存與管控的長期程式。特徵：
- 用 Ctrl-C 取消
- 把狀態存到外部檔案
- 在 stdout 持續輸出狀態
- 本質上是單一使用者的長期存在行程

**對外介面選項**：one-shot 工具要使用 persistent 程式，有兩條路：
- **HTTP API**（往 server 方向走，引入更多複雜度）
- **JSON-RPC over stdin/stdout**（LSP 模式）：輕量、不需要 port、不需要 HTTP stack，一個 shell 直接對接，同時保留「不是 server」的身份——這條路更適合 persistent 程式的定位

### server
觸發條件比「用了 HTTP API」更本質：**資源是有限的，且請求者是多個不認識彼此的 caller**。LLM entry 是標準案例：token rate limit 是共享資源，多個 caller 不知道彼此，所以需要 queue 和 server 集中管理。用來處理高併發、高流量、佇列任務、管控受限資源。

---

## Hub 的定位

單一工具在檔案系統中的路徑本身就是一種索引（可尋址）。Hub 的功能不是「建立索引」，而是把分散的索引**聚集**起來——例如 `prompt_hub` 把所有 prompt 片段工具集中成一份清單。

當外部工具或 shell script 很多時，hub 做一個整合彙整的簡單程式。實作語言隨便，重點是理念：掃描可用工具、收集 metadata、彙整成清單。

---

## 邊緣議題

### 「上一步」的語意隨執行模型不同

「上一步」問的是：**這個程式的副作用是不是可逆的？用什麼機制可逆？**

| 執行模型 | 上一步的實現方式 |
|---|---|
| pipe-and-script | 只能靠 checkpoint 檔案，pipe 本身不可逆 |
| one-shot | 重跑就是上一步，前提是 idempotent（`retry_safe` metadata 欄位） |
| persistent | 需要 snapshot/checkpoint 機制，本質是 mini git |
| server | cancel task + undo task 副作用（undo 目前尚未設計） |

這個問題可以加進 metadata：`reversible: bool` + `undo_method`（描述如何撤銷）。

### 調用鏈管理（輕量做法）

Ledger server 已移除（太後期），但輕量的調用鏈追蹤可以很早就有用：**每個工具在 stderr 印一行結構化紀錄**。

```json
{"caller": "modify_c_code_segment.sh", "tool": "professor.sh", "status": "ok", "ms": 320}
```

成本接近零，由最外層的呼叫者決定要不要收集。讓 debug 從「不知道哪步壞了」變成「能看到整條鏈」。

---

## Metadata 新增欄位小結

基於以上討論，`MetadataView` 應補充：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `execution_model` | `str` | `pipe-and-script` / `one-shot` / `persistent` / `server` |
| `reversible` | `bool` | 副作用是否可撤銷 |
| `undo_method` | `str` | 如何撤銷（`rerun`、`snapshot`、`api-cancel`、`none`…） |
| `retry_safe` | `bool` | 重跑是否安全（idempotent） |
| `memory_hints` | `list[str]` | 成功執行後哪些輸出值得跨輪次記住 |
| `complexity` | `str` | `low` / `medium` / `high`，agent 判斷認知負擔用 |
| `semantic_coupling` | `list[str]` | 使用模式上常與哪些函式搭配 |
