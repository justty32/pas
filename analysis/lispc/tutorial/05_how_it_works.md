# LISP/c 內部運作原理 (05)

本章深入說明 LISP/c 的翻譯引擎是如何把一個 `.cl` 檔案變成 C 程式碼的。理解這個流程，能讓你更有效地除錯，也能讓你在整合到其他系統時知道該從哪裡下手。

---

## 整體流程概覽

```
your-file.cl
     │
     ▼
 (load "c.lisp")          ← 載入引擎，定義所有翻譯函式
     │
     ▼
 (c-whole-file "file.cl") ← 讀取 .cl 檔，逐一 read S-expression
     │  對每個 S-expression 呼叫 (c ...)
     ▼
 (cof expr)               ← 核心遞迴翻譯，回傳 C 字串
     │
     ▼
  C source string
     │
     ▼
 寫入 .c 檔 / 傳給 gcc
```

---

## 第一步：載入引擎 `c.lisp`

`c.lisp` 本身是一個普通的 Common Lisp 程式。它做的事情很簡單：**定義一大堆 Lisp 函式**，每個函式對應一個 LISP/c 語法關鍵字，並回傳對應的 C 字串。

載入時引擎會：
1. 初始化全域狀態（hash table、目前輸出檔案路徑等）。（`c.lisp:3–12`）
2. 利用 `cdefun` 巨集定義所有翻譯函式，並立刻編譯（`compile`）成原生碼以加速執行。（`cdefun` 定義於 `c.lisp:192`）
3. 用 `cfunc-syn` 把大量的別名（如 `f{}` = `func`、`->` = `slot`）綁定到同一個翻譯函式。（別名表位於 `c.lisp:973–1108`）
4. 用 `csyn` 把常數別名（如 `integer` → `int`、`null` → `NULL`、`mpi/sum` → `MPI_SUM`）存入 `*c-synonyms*` hash table。（常數表位於 `c.lisp:1113–1358`）

---

## 第二步：`cdefun` 與命名慣例

引擎裡的所有翻譯函式都用 `cdefun` 定義（`c.lisp:192`）。`cdefun foo ...` 實際上定義的是 `foo-c`，函式名稱由 `cnym`（`c.lisp:186`）產生。

```lisp
;; c.lisp:192 — cdefun 巨集定義
(defmacro cdefun (f args &body body)
  `(progn
     (defun ,(cnym f) ,args ,@body)
     (compile ',(cnym f))))

;; c.lisp:186 — cnym：把名稱加上 -c 後綴
(defun cnym (nym)
  (nth-value 0 (addsyms nym '-c)))
```

這表示：當你在 `.cl` 裡寫 `(var x int 10)`，LISP/c 會呼叫 `var-c`（`c.lisp:555`），它回傳字串 `"int x=10"`。

---

## 第三步：核心翻譯函式 `cof`

`cof`（C-ify）是整個引擎最重要的函式，定義於 `c.lisp:367`。它接受一個任意的 Lisp 物件，遞迴地把它轉成 C 字串。

```
cof 的決策邏輯（c.lisp:367–392）：

輸入 x
 ├─ x 是 nil？              → 回傳 ""                         (c.lisp:368)
 ├─ x 是 atom？
 │   ├─ 在 *c-synonyms* 裡？ → 把值再丟回 cof（遞迴）          (c.lisp:371–372)
 │   └─ 否則？              → c-strify（轉換識別字）            (c.lisp:373)
 └─ x 是 list？
     ├─ (car x) 是 atom？
     │   ├─ 開頭是 @？        → 呼叫 call-c（函式呼叫）          (c.lisp:379, call-c 於 c.lisp:540)
     │   ├─ 開頭是 []？       → 呼叫 nth-c（陣列索引）           (c.lisp:380, nth-c 於 c.lisp:532)
     │   ├─ 開頭是 &？        → 呼叫 addr-c（取位址）            (c.lisp:382, addr-c 於 c.lisp:525)
     │   ├─ 開頭是 ^？        → 呼叫 cast-c（型別轉換）          (c.lisp:383, cast-c 於 c.lisp:551)
     │   ├─ 開頭是 *？        → 呼叫 ptr-c（取值）               (c.lisp:384, ptr-c 於 c.lisp:528)
     │   ├─ 開頭是 =？        → camelcase-c（大寫駝峰）          (c.lisp:387, camelcase-c 於 c.lisp:316)
     │   ├─ 開頭是 -？        → lcamelcase-c（小寫駝峰）         (c.lisp:389, lcamelcase-c 於 c.lisp:328)
     │   └─ 否則？            → 找 (car x)-c 函式並呼叫          (c.lisp:390–391)
     └─ (car x) 是 list？    → 對每個元素呼叫 cof，用 ;\n 分隔   (c.lisp:392)
```

### 實際追蹤範例

輸入：`(var x int 10)`

1. `cof`（`c.lisp:367`）看到這是個 list，`(car x)` = `var`（atom）。
2. 找到 `var-c`，呼叫 `(var-c 'x 'int 10)`。（`c.lisp:391`：`(apply (cnym (car x)) (cdr x))`）
3. `var-c`（`c.lisp:555`）內部對 `x` 和 `int` 呼叫 `cof`（透過 `cofy`，`c.lisp:394`），得到 `"x"` 和 `"int"`。
4. 組合回傳 `"int x=10"`。

---

## 第四步：`c-strify` 識別字轉換

當 `cof` 遇到一個普通的 symbol（例如 `my-var`），它會呼叫 `c-strify`（`c.lisp:139`）來決定 C 的識別字長什麼樣：

| 輸入 | 規則 | C 輸出 | 原始碼位置 |
|------|------|--------|-----------|
| `my-var` | 把 `-` 換成 `_`，全小寫 | `my_var` | `c.lisp:148` |
| `!nthreads` | 去掉 `!`，全大寫（`replace-char` + `cof`） | `NTHREADS` | `c.lisp:145` |
| `=camel-case` | 去掉 `=`，呼叫 `camelcase-c` | `CamelCase` | `c.lisp:146, 316` |
| `-camel-case` | 去掉 `-`，呼叫 `Lcamelcase-c` | `camelCase` | `c.lisp:147, 328` |
| `"LITERAL"` | 字串保持原樣（`stringp` 分支） | `LITERAL` | `c.lisp:140` |

---

## 第五步：`c-whole-file` 讀取 `.cl` 檔

`c-whole-file` 定義於 `c.lisp:1381`，`read-whole-file`（被它呼叫）定義於 `c.lisp:1369`。

```lisp
;; c.lisp:1381
(defun c-whole-file (filename)
  (let ((s (read-whole-file filename)) (result t) (n 0))
    (format nil "/*~a*/~%~a"
            (stamp-time)      ;; c.lisp:1377
      (apply #'c (loop while result collect
                   (progn
                     (multiple-value-setq (result n)
                       (read-from-string s nil))
                     (setf s (subseq s n))
                     result))))))
```

它的做法是：
1. 用 `read-whole-file`（`c.lisp:1369`）把整個 `.cl` 檔讀成一個字串 `s`。
2. 用 `read-from-string` 反覆從字串頭部解析出一個 S-expression，`n` 是消耗掉的字元數。
3. 把所有 S-expression 收集成一個 list，然後一次傳給 `c`（`c.lisp:267`）。

`c` 函式（`c.lisp:267`，注意：這個 `c` 是翻譯用的，不是 `cof`）把每個 S-expression 的翻譯結果用 `;\n\n` 串接起來，最後回傳整份 C 原始碼字串。

`cwf`（`c.lisp:1391`）則是把 `c-whole-file` 的結果直接印到 stdout，用於 REPL 預覽。

---

## 第六步：全域狀態

引擎使用幾個全域變數，全部在 `c.lisp:3–12` 初始化：

| 變數 | 初始化位置 | 用途 |
|------|-----------|------|
| `*c-synonyms*` | `c.lisp:10` | hash table，存常數別名（`null`→`NULL` 等） |
| `*macrolist*` | `c.lisp:11` | hash table，記錄哪些 `lispmacro` 已被定義（`lispmacro-c` 於 `c.lisp:684`） |
| `*templatelist*` | `c.lisp:12` | hash table，記錄哪些 `template` 已被定義（`template-c` 於 `c.lisp:701`） |
| `*file-out*` | `c.lisp:7` | 目前輸出的 `.c` 檔案路徑（nil = 不寫檔，`write-out` 於 `c.lisp:82`） |
| `*exec-out*` | `c.lisp:8` | 目前輸出的執行檔名稱（`change-exec` 於 `c.lisp:91`） |
| `*last-compiled*` | `c.lisp:9` | 上次編譯產生的暫存 `.c` 檔（`compile-cl-file` 在 `c.lisp:1447` 刪除它） |

> **重要**：這些都是 **全域** 狀態。如果你在同一個 CLISP session 裡連續翻譯多個檔案，`*c-synonyms*` 裡的 `syn` 定義和 `template`/`lispmacro` 定義 **會累積**。這是 LISP/c 允許跨檔案共用巨集的機制，但也代表你需要注意名稱衝突。

---

## 小結：翻譯一個 S-expression 的完整路徑

```
(func add int ((a int) (b int)) (return (+ a b)))
  │
  └─ cof (c.lisp:367)
       └─ func-c (c.lisp:601) 收到 "add", "int", ((a int)(b int)), (return (+ a b))
               │
               ├─ cof("add")   → c-strify (c.lisp:139) → "add"
               ├─ cof("int")   → c-strify (c.lisp:139) → "int"
               ├─ vars-c (c.lisp:564) 處理參數列   → "int a,int b"
               └─ block-c (c.lisp:580) 處理函式主體
                    └─ cof((return (+ a b)))
                         └─ return-c (c.lisp:617)
                              └─ cof((+ a b))
                                   └─ +-c (c.lisp:411，由 lredop/c.lisp:205 產生) → "((a)+(b))"
  │
  └─ 最終輸出："int add(int a,int b){\n   return ((a)+(b));\n}"
```
