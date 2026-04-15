# Level 6：Reader、Package 切換、執行檔封裝

## Reader 預處理器
C-Mera 沒有自製獨立的 tokenizer；它用 Common Lisp 的 reader hook 把 sexp **在讀入時**改寫。C 後端註冊的預處理來源：`src/c/reader.lisp` 的 `pre-process`、`pre-process-heads`、`dissect`。

### 觸發點（`src/c/cm-c.lisp:8-11` 與 `:50-65`）
- `#\Space` / `#\Tab` / `#\Newline` → `pre-process`（逐符號檢查）。
- `#\(` → `pre-process-heads`（檢查 list 開頭符號）。

### `dissect` 做了什麼（`src/c/reader.lisp:4`）
對每個剛讀進來的符號，依字面樣式判斷：
| 樣式 | 展開為 |
|---|---|
| `"..."` / `<...>` / `*...*` | 原樣（字串 / include 路徑 / 特殊名） |
| `&name`（長度 > 1） | `split-addrof` → `(addr-of name)` |
| `*name`（前綴 `*`） | `split-targof` → `(targ-of name)` |
| 數字結尾 `F` | `read-float` → `float-type` |
| 含 `.` | `split-oref` → `(oref a b ...)` |
| 含 `->` | `split-pref` → `(pref p x)` |
| 含 `]` | `split-aref` → `(aref a i)` |
| 含 `+-!*~`（尾端為 `++` / `--` 等） | `split-unary` → `(prefix++ i)` 類 |
| 純數字 | `parse-integer` |

這樣使用者寫 `p->field`、`a.b.c`、`arr[i][j]`、`++i`、`0.5f` 等「一看就是 C」的形式都能被直接吸收。

## Reader 切換（REPL 模式）
`define-switch`（`src/c-mera/c-mera.lisp:107`）與 `define-switches`（`:121`）產生兩個 API：
- `(cm-reader)`：切到 C-Mera 模式：掛 macro characters、`readtable-case :invert`。
- `(cl-reader)`：還原到純 Common Lisp 模式。

C 後端在 `src/c/cm-c.lisp:58-65` 把兩者實際化；C++ 後端會 shadow 掉這兩個符號再重新定義（`c-mera.asd:349`），以便各自掛載自己的 reader 擴充。

## Swap 套件（`cms-<lang>`）
`cms-c`、`cms-c++`、`cms-cuda`、`cms-opencl`、`cms-glsl` 是**空的 `(:use)` 套件**（`c-mera.asd:430-448`），本身不匯出任何符號；它們的任務是做為 `(lisp ...)` 形式切換上下文時的「佔位」命名空間，避免污染 `cmu-*`。

## Package 三件組再覆盤
| 層級 | 目的 | 特點 |
|---|---|---|
| `c-mera` | 核心引擎 | 不匯出使用者語法；只供 backend `:use` |
| `cm-<lang>` | backend 實作 | 每個 backend `:use :c-mera :cm-c …`，堆疊而上 |
| `cmu-<lang>` | 使用者層 | 匯出所有 `c-exports` / `c++exports` …；`:shadow` 掉衝突的 CL 符號 |
| `cms-<lang>` | 模式切換暫存 | `(:use)` 空殼 |

## 可執行檔是怎麼做出來的
`save-generator`（`src/c-mera/c-mera.lisp:79`）呼叫 `net.didierverna.clon:dump`，把目前 Lisp image 連同 `dump-start` 啟動函式整體保存成執行檔。`dump-start` 做三件事：
1. `in-package` 切到對應 `:cmu-<lang>`。
2. 設 `readtable-case :invert`。
3. 依實作呼叫 `sb-ext:*posix-argv*` / `ccl::*command-line-argument-list*` / `si:argv` 取得參數後呼叫 `c-processor`。

## 前端分派
`src/front/cm.c` 是一支小小的 C 程式，從 `argv[1]` 取語言關鍵字（`c` / `c++` / `cuda` …）決定 `execvp` 哪個 image 可執行檔。安裝後 `cm` 與 `cm-c` / `cm-cxx` 等共存於同一 bin 目錄。
