# 05 — 使用者層 Syntax 宏 + quoty

> 對照：`analysis/c-mera/architecture/level4_syntax_macros.md`、`projects/c-mera/src/c-mera/utils.lisp:19-71`、`projects/c-mera/src/c/syntax.lisp:3-267`
>
> 對齊度：高。`defsyntax` / `c-syntax` / `quoty` 全部實作。

## 1. 角色定位

Syntax 層的工作：**把使用者寫的 sexp 轉成 AST 節點呼叫**。完全不做語意檢查（型別、未宣告變數等），所有檢查交給目標編譯器（gcc / clang）。

兩個關鍵基礎設施：

1. **`defsyntax` / `c-syntax`**：c-mera 風格的「一段宏覆寫多個運算子」。
2. **`quoty`**：在編譯期判斷符號是否綁定，未綁定者自動變成 C 識別字/函式呼叫。

## 2. `defsyntax` / `c-syntax`

對映 `projects/c-mera/src/c-mera/utils.lisp:19` 與 `projects/c-mera/src/c/syntax.lisp:3`。`c-syntax` 是 `defsyntax` 的縮寫，固定把宏匯出到 hymera.syntax.c。

c-mera 寫法：
```lisp
(c-syntax (= *= /= %= += -= <<= >>= &= ^= \|=) (variable value)
  `(assignment-expression ',tag (make-node ,variable) (make-node ,value)))
```

hymera 對應寫法：
```hylang
(c-syntax (= *= /= %= += -= <<= >>= &= ^= |=) (variable value)
  `(assignment-expression :op '~tag
                          :variable (make-node ~variable)
                          :value    (make-node ~value)))
```

要點：
- **`tag` 是 c-syntax 為每個運算子綁的區域變數**，展開時可取得當前符號（`=`、`*=` 等）。
- 一條 `c-syntax` 等於替清單裡每個符號各自 `defmacro` 一次，body 相同。
- `make-node`：把單一 sexp 項目包成節點（如果它本身不是節點呼叫，套 `quoty` 處理）。

### 中綴運算式範例

```hylang
(c-syntax (+ - * / % < > <= >= == != && || & | ^ << >>) (#* operands)
  `(infix-expression :op '~tag
                     :operands (make-nodelist ~operands)))
```

一條 `c-syntax` 涵蓋全部中綴運算子。這就是「為什麼這個寫法值得**完全對齊 c-mera**」的核心理由——少寫 17 個一模一樣的 `defmacro`。

### 與 Hy 核心衝突的處理

`+`、`-`、`*`、`/` 是 Hy 核心宏（運算子宏，`projects/hy/hy/core/result_macros.py:433`）。`c-syntax` 展開後等於對它們做 `defmacro`，會觸發 `RuntimeWarning`（`projects/hy/hy/compiler.py:376`）。

**對策**：`hymera.syntax.c` 模組頂端寫 `(pragma :warn-on-core-shadow False)` 一勞永逸關掉警告（實測 2026-05-26，shadow `for` / `+` / `if` 等核心宏完全可行）。

## 3. `quoty`：使用者可以直接寫 `(printf "%d" x)`

對映 `projects/c-mera/src/c-mera/utils.lisp:53`。完整決策見 [`decisions/0002-implement-quoty.md`](decisions/0002-implement-quoty.md)。

### 3.1 規則

| 形式 | 是否綁定 | 轉換結果 |
|---|---|---|
| `Symbol foo` | 已綁定（Hy/Python builtin 或 scope.defined 或 macro） | 原樣（Lisp 求值） |
| `Symbol foo` | 未綁定 | `(ident 'foo)` → C 識別字 |
| `(foo a b)` | head 已綁定 | 視為 Lisp 函式呼叫，**遞迴對 args quoty** |
| `(foo a b)` | head 未綁定 | `(function-call (ident 'foo) (make-nodelist (quoty a) (quoty b)))` |
| `(if ...)` 之類特殊形式 | head 在 `HYMERA-SPECIAL-FORMS` | 跳過 quoty，原樣展開 |
| `"abc"` / `123` / 字面值 | — | 原樣 |

### 3.2 編譯期 binding 判斷（實測通過）

```hylang
(eval-and-compile
  (import builtins)

  (defn bound? [compiler name-str]
    (setv m (hy.mangle name-str))
    (or
      (in m (. compiler scope defined))                            ; defn/setv/import/let 後
      (hasattr builtins m)                                         ; Python builtin
      (in m (or (getattr builtins "_hy_macros" None) {}))          ; Hy 核心宏
      (in m (or (getattr compiler.module "_hy_macros" None) {})))))  ; 本模組 require 的宏
```

實測結果（`projects/hy/.venv` Hy 1.3）：

| 名稱 | 預期 | 實際 |
|---|---|---|
| `print` | BOUND（Python builtin） | ✅ |
| `printf` | UNBOUND | ✅ |
| `math`（剛 `import math`） | BOUND | ✅ |
| `myvar`（剛 `setv`） | BOUND | ✅ |
| `helper`（剛 `defn`） | BOUND | ✅ |
| `foo-undef` | UNBOUND | ✅ |

### 3.3 quoty 函式骨架

```hylang
;; src/hymera/syntax/quoty.hy
(eval-and-compile
  (defn quoty [form compiler]
    (cond
      (isinstance form hy.models.Symbol)
        (cook-or-ident form compiler)

      (isinstance form hy.models.Expression)
        (do
          (setv head (get form 0))
          (cond
            ;; 特殊形式：不動
            (and (isinstance head hy.models.Symbol)
                 (in (str head) HYMERA-SPECIAL-FORMS))
              form
            ;; head 未綁定 → 變 function-call
            (and (isinstance head hy.models.Symbol)
                 (not (bound? compiler (str head))))
              `(function-call
                  (ident '~head)
                  (make-nodelist ~@(lfor x (cut form 1 None) (quoty x compiler))))
            ;; head 綁定：遞迴對 args quoty
            True
              (hy.models.Expression
                [head ~@(lfor x (cut form 1 None) (quoty x compiler))])))

      ;; List / Dict 等：照遞迴
      (isinstance form hy.models.List)
        (hy.models.List (lfor x form (quoty x compiler)))

      ;; 字面值：原樣
      True form))

  (defn cook-or-ident [sym compiler]
    "對單一 Symbol 做：(1) 字串拆解（p->x, i++, ...）  (2) 若仍是 symbol 且未綁定 → ident"
    (setv cooked (cook-symbol sym))
    (if (!= cooked sym)
        cooked
        (if (bound? compiler (str sym))
            sym
            `(ident '~sym)))))
```

`cook-symbol` 的字串拆解規則見 [`decisions/0004-reader-sugar-and-arr-asymmetry.md`](decisions/0004-reader-sugar-and-arr-asymmetry.md) §「quoty 階段的拆解規則」。

### 3.4 `HYMERA-SPECIAL-FORMS` 維護

清單**集中在 `src/hymera/syntax/quoty.hy` 頂端**：

```hylang
(eval-and-compile
  (setv HYMERA-SPECIAL-FORMS
    #{
      ;; Hy 原生不可動的
      "quote" "quasiquote" "unquote" "unquote-splice"
      "setv" "fn" "do" "let" "require" "import" "annotate"
      "yield" "await" "raise" "try" "global" "nonlocal" "del"
      ;; hymera 頂層使用者宏
      "function" "decl" "include" "define" "struct" "typedef" "enum"
      "if" "for" "while" "do-while" "switch" "case" "default"
      "return" "break" "continue"
      ;; C++
      "class" "namespace" "template" "using-namespace" "using-decl" "using-alias"
      "new" "delete"
      ;; 內部 / 顯式呼叫
      "function-call" "ident" "infix-expression" "prefix-expression"
      "postfix-expression" "assignment-expression" "ternary-expression"
      "member-access" "subscript-expression" "cast-expression"
      "aref" "." "->" "post++" "post--" "pre++" "pre--"
      "make-node" "make-nodelist"
    }))
```

每加一個頂層使用者宏，請同步登記。

## 4. 控制流宏（直接用核心名稱）

對齊 c-mera 直接用 `if` / `for` / `while`（c-mera 透過 `cmu-c` 套件 shadow `cl:if`）。hymera 用 pragma + defmacro 達到同樣效果：

```hylang
;; src/hymera/syntax/c.hy 頂端
(pragma :warn-on-core-shadow False)

(defmacro if [test then [else None]]
  "(if t then else) → if-statement node。"
  `(if-statement :test ~test :if-body ~then :else-body ~else))

(defmacro for [init test step #* body]
  `(for-statement :init ~init :test ~test :step ~step
                  :body (compound-statement :statements (make-nodelist ~@body))))

(defmacro while [test #* body]
  `(while-statement :test ~test
                    :body (compound-statement :statements (make-nodelist ~@body))))

(defmacro return [[value None]]
  `(return-statement :value ~value))
```

> ⚠️ **要付出的代價**：在 hymera 程式碼裡你不能再用 Hy 原生 `if`/`for` 做編譯期計算。需要時走 `hy.pyops.if`（其實 Hy 沒有，要用 `(hy.eval ...)` 之類繞道）或在另一個模組裡寫不 require hymera.syntax.c 的程式。實務上撰寫 C 生成程式時不會混 Lisp 流程；這個取捨與 c-mera 用 `cmu-c` shadow 後仍可用 `cl:if` 一致。

## 5. 頂層宏

### 5.1 `function` 對映 c-mera

```hylang
(defmacro function [name params return-arrow ret-type #* body]
  "(function main () -> int (printf \"hi\") (return 0))"
  (when (!= return-arrow '->)
    (raise (HymeraSyntaxError "function 第三個 token 必須是 ->")))
  `(function-definition
     :item       (declaration-item :specifier None :type (type-ref '~ret-type)
                                   :id (ident '~name) :init None)
     :parameter  (make-nodelist ~@(parse-params params))
     :body       (compound-statement
                   :statements (make-nodelist ~@(lfor s body
                                                  `(quoty-form ~s _hy_compiler))))))
```

> `quoty-form` 是包裝：在編譯期呼叫 `(quoty ~form _hy_compiler)`。具體機制是把 `function` 寫成 compiler-aware 宏（第一參數 `_hy_compiler`），然後在展開時對 body 的每個 form 呼叫 `quoty`。

### 5.2 `decl` 對映 c-mera

對映 `projects/c-mera/src/c/syntax.lisp:254`：

```hylang
(defmacro decl [bindings #* body]
  "(decl ((int i = 0) (const unsigned long x)) body...)"
  `(compound-statement
     :statements (make-nodelist
                   (declaration-list
                     :items (make-nodelist
                              ~@(lfor b bindings `(make-declaration-node '~b))))
                   ~@body)))

(eval-and-compile
  (defn make-declaration-node [binding]
    "拆 (specifier... type id [= init]) 並建 declaration-item。"
    (setv toks (list binding))
    (cond
      ;; 倒數第二個是 = → (... type id = init)
      (and (>= (len toks) 4) (= (get toks -2) '=))
        (do
          (setv init  (get toks -1))
          (setv id    (get toks -3))
          (setv type  (get toks -4))
          (setv spec  (cut toks 0 -4))
          `(declaration-item :specifier (make-nodelist ~@spec)
                             :type (type-ref '~type)
                             :id   (ident '~id)
                             :init ~init))
      ;; 否則 (... type id)
      True
        (do
          (setv id    (get toks -1))
          (setv type  (get toks -2))
          (setv spec  (cut toks 0 -2))
          `(declaration-item :specifier (make-nodelist ~@spec)
                             :type (type-ref '~type)
                             :id   (ident '~id)
                             :init None)))))
```

`decompose-declaration` 直接對應 `projects/c-mera/src/c/syntax.lisp:195` 的同名函式。

## 6. 對照：c-mera vs hymera 使用者體驗

| 使用者意圖 | c-mera | hymera v1 |
|---|---|---|
| 函式定義 | `(function main () -> int ...)` | **同** |
| 變數宣告 | `(decl ((int i = 0)) ...)` | **同** |
| 條件 | `(if c then else)` | **同**（核心 shadow） |
| 迴圈 | `(for (= i 0) (< i 10) (++ i) body)` | **同**（核心 shadow） |
| 函式呼叫 | `(printf "hi")` ✨ quoty | **同**（quoty 接管） |
| 變數參照 | `x`（未綁定就是 C 名稱） | **同**（quoty 接管） |
| `p->x` | `p->x` reader | `p->x`（quoty 階段 cook） |
| `obj.x` | `obj.x` reader | `obj.x`（quoty 階段 cook） |
| `i++` | `i++` reader | `i++`（quoty 階段 cook） |
| `arr[i]` | `arr[i]` reader | **`(aref arr i)`** ⚠️ 唯一不對齊 |
| 浮點 `0.5f` | `0.5f` reader | `0.5f`（cook 識別） |

## 7. 模組命名空間建議

對齊 c-mera 風格：

```hylang
;; 使用者程式碼開頭
(pragma :warn-on-core-shadow False)        ; 接受 if/for/+/- 被 shadow
(require hymera.syntax.c *)                ; 取出全部 C 宏
;; 寫 C++ 加：
(require hymera.syntax.cpp *)
```

對單純 C 使用者，`hymera.syntax.c` 是入口；對 C++ 加上 cpp。pragma 設定可由我們提供的「meta require」`(hymera-c)` 一次到位：

```hylang
(defmacro hymera-c []
  `(do
     (pragma :warn-on-core-shadow False)
     (require hymera.syntax.c *)))

;; 使用者：
(hymera-c)
```
