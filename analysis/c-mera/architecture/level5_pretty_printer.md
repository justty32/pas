# Level 5：Pretty Printer 與技術流水線

## Pretty Printer 資料結構
`pretty-printer` 是一個特殊的 traverser 類別（由 `with-pp` 宏建立上下文）。它在走訪 AST 時維護：
- `stream`：輸出流。
- `indent`：當前縮排字串（每層加一個 `*indent*`，預設 `#\tab`，見 `src/c-mera/traverser.lisp:8`）。
- `info-stack`：上下文堆疊，用 `push-info` / `pop-info` / `top-info`；用來決定「目前身處 for / while / if / else / block 哪個上下文」。
- `sign-stack`：運算子優先序堆疊，類似用途。

所有 API（`stream`、`indent`、`++indent`、`--indent`、`push-info`、`top-info`、`pop-info`、`node-slot`、`make-proxy`、`del-proxy`）見 `c-mera.asd:302-309` 的匯出列表。

## `defprettymethod` 的三種時機
在 `with-pp` 區塊內可定義：
- `(defprettymethod :before <node-type> ...)`：下鑽前執行（通常印開頭、調縮排、push-info）。
- `(defprettymethod :after <node-type> ...)`：下鑽後執行（印結尾、pop-info）。
- `(defprettymethod :self <node-type> ...)`：取代預設下鑽邏輯（用於 leaf，例如 `src/c-mera/pretty.lisp:6`）。

### 範例：`expression-statement` 何時加分號
見 `src/c/pretty.lisp:5-23`：只有當包住的運算式是 `function-call` / `infix-expression` / `prefix-expression` / `postfix-expression` / `empty` 或強制旗標設定時才印 `;`。這個邏輯保證 `set`、`decl` 等會自帶 `;` 的語法不會重複加。

### 範例：`compound-statement` 的上下文判斷
見 `src/c/pretty.lisp:30-45`：若目前 `top-info` 是 `for` / `while` / `do` / `if` / `else`，就緊接著印 ` {`；否則另起一行再印 `{`。這就是 C 程式 `if (...) {` 與獨立 `{` 區塊格式差異的實作方式。

## Proxy 列印
某些「裝飾」不屬於任何單一節點，例如「型別後要有空白」。做法（`src/c/pretty.lisp:62-75`）：
1. `with-proxynodes (type)` 建立一個只在此檔案範圍可見的 proxy 型別。
2. `:before declaration-item` 中 `(make-proxy type type)` 把 `type` 槽包成 proxy。
3. 用 `defproxyprint :after type` 印空白。
4. `:after declaration-item` 中 `(del-proxy type)` 拆掉。

## 整體處理流水線（從命令列到輸出）
對應 `src/c/cm-c.lisp` 的頂層定義：

1. **啟動**：由 `cm` 前端分派到 `cm-c` 可執行檔；image 的進入點是 `c-processor`（由 `define-processor` 生成，`src/c-mera/c-mera.lisp:55`）。
2. **命令列解析**：`parse-cmdline` 分離 input / output / debug。
3. **讀檔**：`read-in-file`（`src/c-mera/c-mera.lisp:5` 生成）開啟輸入檔：
   - 複製 readtable，設 `readtable-case :invert`（保留符號原大小寫）。
   - 掛入預處理 reader macros（`src/c/cm-c.lisp:8-11`，攔截空白、Tab、換行、`(`）。
   - 逐個 `read` + `eval`，收集產出的 AST 節點成一個大的 `nodelist`。
4. **AST 重寫**（依序跑完）：
   `nested-nodelist-remover` → `else-if-traverser` → `if-blocker` → `decl-blocker` → `renamer`。
5. **輸出**：建立 `pretty-printer` 實例，將 `stream` 指向目標檔或 stdout，跑 `(traverser pprint tree 0)`。

## 資料流觀察點
- AST 巢狀結構：用 `(print! tree)`（`src/c-mera/c-mera.lisp:98`）可以同時觸發 `debug-traverser` 與 pretty-printer。
- REPL：`(simple-print (function main () -> int (return 0)))`（定義於 `src/c/cm-c.lisp:32`）會跑完所有 traverser 後印到 stdout，不必寫檔。
