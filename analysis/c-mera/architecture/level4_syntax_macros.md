# Level 4：使用者語法層（Syntax Macros）

這一層把「人類手寫的 sexp」轉成「AST 節點樹」。C-Mera 刻意**不做語意檢查**，完全交給目標語言的編譯器；因此 syntax 層的工作就是「換形狀」。

## `defsyntax` 與 `c-syntax`
- `defsyntax`（`src/c-mera/utils.lisp:19`）：為多個 tag、多個 package 同時建立巨集；每個巨集展開時會有一個區域變數 `tag` 指向當前符號，讓同一段展開邏輯能覆寫多個運算子。
- `c-syntax`（`src/c/syntax.lisp:3`）：`defsyntax` 的簡寫，固定把 tag 匯出到 `:cmu-c` 套件。

典型用法（`src/c/syntax.lisp:50-56`）：
```lisp
(c-syntax (= *= /= %= += -= <<= >>= &= ^= \|=) (variable value)
  `(assignment-expression ',tag (make-node ,variable) (make-node ,value)))

(c-syntax (/ > < == != >= <= \| \|\| % << >> or and ^ &&) (&rest rest)
  `(infix-expression ',tag (make-nodelist ,rest)))
```
一條 `c-syntax` 等同替清單內每個符號定義了一個巨集；透過區域 `tag` 把運算子符號保留到 AST 節點。

## 三個搬運工具
- `make-node`：把單一 sexp 項目包成節點（必要時會套 `quoty`）。
- `make-nodelist`（`src/c-mera/utils.lisp:71`）：把 sexp 列表轉成 `nodelist`，可選 `:prepend` 指定每個元素先經過某個節點建構器（例如 `make-declaration-node`）；`:quoty t` 則用 `quoty` 自動識別未綁定符號。
- `quoty`（`src/c-mera/utils.lisp:53`）：**C-Mera 最關鍵的小工具**。
  - 如果項目是未定義的函式呼叫形式（`(foo 1 2)` 而 `foo` 沒有巨集 / 函式綁定），展開為 `function-call` 節點（變成 C 的函式呼叫）。
  - 如果是未綁定符號，保留為 quoted 符號（變成 C 的識別字）。
  - 如果是已綁定的 Lisp 符號，原樣傳回（讓 Lisp 計算）。
  - 結果：使用者可以自由混合 Lisp 與 C 程式碼，未宣告的函式不會出錯，會直接當成 C 的函式呼叫發射。

## 宣告（decl）的展開路徑
使用者寫：
```lisp
(decl ((int i = 0) (const unsigned long x)) ... body ...)
```
展開步驟：
1. `(c-syntax decl (bindings &body body) …)` (`src/c/syntax.lisp:254`) 產生 `(declaration-list t (make-nodelist ,bindings :prepend make-declaration-node) ...body...)`。
2. `make-declaration-node`（`src/c/syntax.lisp:216`）呼叫 `decompose-declaration`（`src/c/syntax.lisp:195`）把列表切成 `(specifier, type, id, init)` 四段：
   - 若倒數第二個符號是 `=`，截出最後 4 項 `(type id = init)`，剩下都當 specifier。
   - 否則截出最後 2 項 `(type id)`。
3. 組成 `declaration-item` 節點（節點定義於 `src/c/nodes.lisp:20`）。

這個 decomposer 也被 `function` 語法重用（`src/c/syntax.lisp:267`），因此**「型別能貪婪吃掉多個符號」的能力對 `decl` 與 `function` 都適用**。

## 函式定義
```lisp
(function main () -> int (return 0))
```
`function` 巨集（`src/c/syntax.lisp:267`）把 `-> type` 拆出，用 `make-declaration-node` 把 `(type name)` 組成函式名＋回傳型別的 `declaration-item`，再把 `parameters` 以 `make-declaration-node` 作為 prepend 轉成 `parameter-list`，最後 body 用 `make-block` 包上大括號。

## Lisp / C-Mera 符號衝突
因為 `cmu-c` shadow 掉 `if`、`for`、`=`…，要明確呼叫 Lisp 版本時請用 `cl:if`；或把一整段 Lisp 寫在 `(lisp ...)` 之內（後者會在讀取期切換 reader/套件上下文，內部符號按 Lisp 綁定來解析）。

## C-Mera 對 C 寫法的貼近
除了巨集，`src/c/reader.lisp` 的 `dissect` 讓使用者可以直接寫：
- `p->field`（`split-pref`）
- `obj.field`（`split-oref`）
- `arr[i]`（`split-aref`）
- `i++`、`++i`（`split-unary`）
- `0.5f`（`read-float`）

這些都是在空白 / 左括號 reader 觸發時，對符號名稱做字串解析後改寫。
