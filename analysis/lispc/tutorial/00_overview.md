# LISP/c (Lispsy) 快速上手教學：從 C 到 Lisp 的橋樑

如果你熟悉 C 語言但對 Lisp 不太熟，最簡單的理解方式是：**LISP/c 是一個超強大的 C 語言宏（Macro）系統**。它讓你用 Lisp 的語法來撰寫 C 邏輯，最後再幫你翻譯成標準的 C 程式碼。

## 1. 核心觀念：括號與前置表達式

在 Lisp 中，所有的指令都寫在括號 `()` 裡，且**第一個字永遠是動作（函式或運算子）**。

*   **C 語言：** `1 + 2`
*   **Lisp 語法：** `(+ 1 2)`

*   **C 語言：** `printf("Hello %d", 10);`
*   **Lisp 語法：** `(@printf (str "Hello %d") 10)`

---

## 2. 基礎語法對照表

### 變數宣告 (Variable Declaration)
| C 語言 | LISP/c 語法 | 說明 | 原始碼 |
| :--- | :--- | :--- | :--- |
| `int x = 10;` | `(var x int 10)` | `var` [名稱] [型別] [初始值] | `c.lisp:555` |
| `float y;` | `(var y float)` | | `c.lisp:555` |
| `#define MAX 100` | `(define !max 100)` | 開頭加 `!` 會自動轉大寫 | `c.lisp:646` |

### 函式定義 (Functions)
**C 語言：**
```c
int add(int a, int b) {
    return a + b;
}
```
**LISP/c：**（`func` → `c.lisp:601`，`return` → `c.lisp:617`）
```lisp
(func add int ((a int) (b int))
    (return (+ a b)))
```

### 控制流程 (Control Flow)
| C 語言 | LISP/c 語法 | 原始碼 |
| :--- | :--- | :--- |
| `if (a == b) { ... } else { ... }` | `(if (== a b) (progn ...) (progn ...))` | `c.lisp:492` / `c.lisp:485` |
| `for (i=0; i<10; i++) { ... }` | `(for (= i 0) (< i 10) (++ i) ...)` | `c.lisp:506` |
| `while (x > 0) { ... }` | `(while (> x 0) ...)` | `c.lisp:509` |

---

## 3. 指標與陣列 (Pointers & Arrays)

這是 C 程式設計師最關心的部分，LISP/c 提供了一些簡化的記法：

*   **指標型別：** `int *p` 寫作 `((pt p) int)` 或 `(var p (t* int))`。（`pt` → `c.lisp:530`，`t*`/`typ*` → `c.lisp:473`）
*   **取位址 (&)：** `&x` 寫作 `(&x)` 或 `(addr x)`。（`addr` → `c.lisp:525`）
*   **取值 (*)：** `*p` 寫作 `(*p)` 或 `(ptr p)`。（`ptr` → `c.lisp:528`）
*   **陣列索引 ([])：** `arr[i]` 寫作 `([]arr i)` 或 `(nth arr i)`。（`nth` → `c.lisp:532`）
*   **結構存取 (->)：** `p->member` 寫作 `(slot p member)`。（`slot` → `c.lisp:465`）

---

## 4. 進階快捷記法 (Synonyms)

為了讓你寫起來更像 C，LISP/c 有很多縮寫：
*   `@`：呼叫函式。例如 `(@malloc 10)` 等於 `malloc(10)`。（`cof` 中 `#\@` 分支 → `c.lisp:379`，實際呼叫 `call` → `c.lisp:540`）
*   `str`：建立字串字面量。`(str "Hello")`。（`str` → `c.lisp:545`）
*   `headers`：包含標頭檔。`(headers stdio stdlib)` 會生成 `#include <stdio.h>` 和 `#include <stdlib.h>`。（`headers` → `c.lisp:676`，`header` → `c.lisp:674`）

---

## 5. 為什麼要用它？—— 模板 (Template) 的威力

在 C 語言中，如果你想為 `int` 和 `float` 寫同樣邏輯的函式，通常要複製貼上或用複雜的 `#define`。在 Lisp 中，你可以這樣寫：

```lisp
;; 定義一個模板叫做 make-add（template → c.lisp:701，sym/add → c.lisp:462）
(template make-add (typ)
  (func (sym/add add- typ) typ ((a typ) (b typ))
    (return (+ a b))))

;; 產生 int 和 float 版本的 add 函式
(make-add int)   ;; 產生 add_int
(make-add float) ;; 產生 add_float
```

---

## 6. 如何開始實作？

1.  **安裝：** 你需要先安裝 `CLISP`。
2.  **啟動：** 在終端機輸入 `clisp`。
3.  **載入：** `(load "c.lisp")`。
4.  **撰寫：** 建立一個 `hello.cl` 檔案：
    ```lisp
    (header stdio)
    (main
      (@printf (str "哈囉，這是我第一個 Lispsy 程式！\\n"))
      (return 0))
    ```
5.  **編譯：** 在 CLISP 中輸入 `(c-cl-file "hello.cl" "hello.c")`。（`c-cl-file` → `c.lisp:1404`，`cwf` 預覽 → `c.lisp:1391`）
6.  **執行：** 退出 Lisp，使用 `gcc hello.c -o hello` 編譯後執行。

### 小撇步：
*   Lisp 不分大小寫，但 LISP/c 規定**變數名稱中的 `-` 會變成 C 的 `_`**（例如 `my-var` 變成 `my_var`）。
*   想要全大寫（如常數），在前面加驚嘆號：`!nthreads` 會變成 `NTHREADS`。
