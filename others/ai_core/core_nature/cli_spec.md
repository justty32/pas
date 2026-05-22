# cli_spec.md

本規範對 CLI 的標準定義。以 `terminal_model.md` §1 為基礎，記錄本規範的選擇與新增項目。

---

## §2 本規範的 CLI 標準

### 2.0 概念模型：回到 Lisp

CLI 呼叫本質上是一個 **Lisp 風格的函式呼叫**，只是用不同語法序列化：

```lisp
; Lisp
(program pos1 pos2 :key1 val1 :key2 val2)

; CLI 等價形式
program pos1 pos2 --key1 val1 --key2 val2
```

對應關係：

| CLI 元素 | Lisp 對應 | 說明 |
|---|---|---|
| 第一個 word（程式名） | `car` | 函式本體 |
| Positional args | list 的 bare cdr 元素 | 沒有 key 裝飾的純值 |
| `--key value` | keyword pair（`:key value`） | 嵌入 list 的 key-value pair |

整個 argv（去掉程式名後）是一個線性 list，裡面混雜著 bare 元素（positionals）與 pair（flags）。實作時把 pair 部分彙聚成 dict，bare 部分保留為 array——這只是實作層的便利形式，概念上仍是同一個 list。

```
argv cdr = [pos1, pos2, (:key1, val1), (:key2, val2)]
           ↓ 實作時分拆
positionals = [pos1, pos2]
flags       = {key1: val1, key2: val2}
```

`--` 前綴就是 Lisp 的 `:` 前綴——標示「這是 keyword，不是 bare value」。

---

### 2.1 解析工具

- **Python**：`argparse`（標準庫，零外部相依）
- 解析結果透過 `vars(parser.parse_args())` 取得 dict，可直接 `json.dumps()`
- 短旗標透過 `add_argument('-x', '--flag', ...)` 宣告為長旗標的別名

### 2.2 解析結果結構

各旗標的值型別由 `argparse` 宣告決定：

| 宣告方式 | value 型別 | 範例 |
|---|---|---|
| `action='store_true'` | `bool` | `--verbose` → `True` |
| `type=str`（預設） | `str` | `--output a.txt` → `"a.txt"` |
| `nargs='+'` | `list[str]` | `--files a.txt b.txt` → `["a.txt", "b.txt"]` |
| `nargs='*'` | `list[str]`（可空） | 同上，允許零個 |

---

### 2.3 本規範的取捨

**不採用**（argparse 不原生支援或本規範排除）：

| 特性 | 原因 |
|---|---|
| `-abc`（短旗標合併） | argparse 不原生支援 |
| `--flag=value`（等號形式） | argparse 支援但不強制，規範不要求 |

**新增**（超出 `terminal_model.md` 的本系統規定）：

| 特性 | 說明 |
|---|---|
| `--metadata` | 所有工具必須實作，回傳 JSON 描述自身（執行時間、記憶體用量、格式等） |
