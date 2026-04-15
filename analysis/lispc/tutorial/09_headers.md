# 生成 .h 與 .c/.cpp 檔案 (09)

本章說明在 LISP/c 中如何分別產生標頭檔（`.h`/`.hh`）和實作檔（`.c`/`.cpp`），以及兩者在內容上的差異。

---

## 核心差異：宣告 vs. 實作

| | 標頭檔 `.h` | 實作檔 `.c` / `.cpp` |
|--|------------|-------------------|
| 目的 | 給其他檔案 `#include`，宣告介面 | 函式的實際程式碼 |
| 包含 | include guards、struct/typedef、函式宣告（無本體）、inline 函式、巨集 | `#include "foo.h"`、函式實作（有本體） |
| LISP/c 關鍵差異 | `(func name ret args)`（**無 body**） | `(func name ret args body...)` |

在 LISP/c 中，`func` 不傳 body 就會產生純宣告（forward declaration）：

```lisp
;; 宣告（放在 .h）
(func add int ((a int) (b int)))
;;=> "int add(int a,int b)"

;; 實作（放在 .c）
(func add int ((a int) (b int))
  (return (+ a b)))
;;=> "int add(int a,int b){\n   return ((a)+(b));\n}"
```

---

## 生成 .h 檔的兩種方法

### 方法一：直接指定輸出路徑（最簡單）

`c-cl-file`（`c.lisp:1404`）的第二個參數就是輸出路徑，直接寫 `.h` 副檔名即可：

```lisp
(load "c.lisp")
(c-cl-file "mylib.cl" "mylib.h")   ;; 輸出 .h
(c-cl-file "mylib.cl" "mylib.c")   ;; 輸出 .c
```

你只需要在 `.cl` 檔的內容上決定要放宣告還是實作，副檔名本身對 LISP/c 沒有語意差異。

### 方法二：`change-file` + `cwrite`（串流模式）

`change-file`（`c.lisp:88`）設定當前的輸出目標，之後每次呼叫 `cwrite` 或 `write-out` 都會追加到那個檔案：

```lisp
(load "c.lisp")

;; 切換到 .h 輸出
(change-file "mylib" t)     ;; t = 輸出 mylib.h
(cwrite '(pragma once))
(cwrite '(struct point ((x float) (y float))))
(cwrite '(func add int ((a int) (b int))))

;; 切換到 .c 輸出
(change-file "mylib")       ;; nil = 輸出 mylib.c
(cwrite '(include ("mylib" :local t)))
(cwrite '(func add int ((a int) (b int))
            (return (+ a b))))
```

`cwrite` 是 `write-out` 的巨集封裝（`c.lisp:277`），會在翻譯結果後自動加上 `;\n`。

---

## Include Guard 的寫法

### 建議：`pragma once`（最簡潔）

```lisp
(pragma once)
;;=> "#pragma once"
```

### 傳統 include guard

**注意**：LISP/c 內建的 `(ifndef ...)` 和 `(ifdef ...)` 在目前版本（`c.lisp:650–655`）有 bug：expr 沒有被插入 format 字串，會輸出字面的 `#ifdef ~%` 而不是 `#ifdef YOUR_MACRO`。請用 `(cpp ...)` 代替：

```lisp
;; 正確做法：用 (cpp ...) 產生任意前置處理器指令
(cpp ifndef !my-lib-h)   ;;=> "#ifndef MY_LIB_H"
(cpp define !my-lib-h)   ;;=> "#define MY_LIB_H"
;; ... 內容 ...
(cpp endif)              ;;=> "#endif"
```

---

## 完整範例：把一個模組分成 .h + .c

### 模組：`vec2`

**`vec2.h.cl`**（用來產生 `vec2.h`）：

```lisp
(pragma once)

(typedef (struct vec2) vec2)

(struct vec2
  ((x float)
   (y float)))

;; 函式宣告（不含 body）
(func vec2-add    vec2  ((a vec2) (b vec2)))
(func vec2-scale  vec2  ((v vec2) (s float)))
(func vec2-length float ((v vec2)))
```

**`vec2.c.cl`**（用來產生 `vec2.c`）：

```lisp
(header ("vec2" :local t))
(header math)

(func vec2-add vec2 ((a vec2) (b vec2))
  (var result vec2)
  (= (.> result x) (+ (.> a x) (.> b x)))
  (= (.> result y) (+ (.> a y) (.> b y)))
  (return result))

(func vec2-scale vec2 ((v vec2) (s float))
  (var result vec2)
  (= (.> result x) (* (.> v x) s))
  (= (.> result y) (* (.> v y) s))
  (return result))

(func vec2-length float ((v vec2))
  (return (@sqrtf (+ (* (.> v x) (.> v x))
                     (* (.> v y) (.> v y))))))
```

**shell 編譯指令：**

```bash
clisp -q -x "(load \"c.lisp\") (c-cl-file \"vec2.h.cl\" \"vec2.h\") (quit)"
clisp -q -x "(load \"c.lisp\") (c-cl-file \"vec2.c.cl\" \"vec2.c\") (quit)"
gcc -c vec2.c -o vec2.o
```

---

## C++ 標頭檔：`.hh` 與 class 宣告

C++ 的標頭副檔名慣例上用 `.hh`（或 `.hpp`），LISP/c 的 `hh-file`（`c.lisp:788`）反映了這個慣例，但 `c-cl-file` 的輸出路徑你可以任意指定：

```lisp
(c-cl-file "matrix.cl" "matrix.hpp")
```

C++ 標頭的典型內容（`.cl` 檔）：

```lisp
(pragma once)
(headers++ string vector)

;; class 宣告：只有成員宣告，不含實作
(class string-stack
  (public
    (cx ())                          ;; 建構子宣告
    (dx nil)                         ;; 解構子宣告
    (func push void ((s (ns std string))))
    (func pop (ns std string) ())
    (func empty bool () const)
    (func size int () const))
  (private
    (var data (temp (ns std vector) (ns std string)))))
```

對應的 `.cpp` 實作檔：

```lisp
(header++ ("string-stack" :local t))

(func (ns string-stack push) void ((s (ns std string)))
  (@data.push-back s))

(func (ns string-stack pop) (ns std string) ()
  (var top (ns std string) (@data.back))
  (@data.pop-back)
  (return top))

(func (ns string-stack empty) bool ()
  const
  (return (@data.empty)))
```

> **注意**：C++ 的成員函式在實作檔中用 `(namespace class-name method-name)` 或 `(ns ...)` 來表達 `ClassName::method_name` 的作用域。

---

## 只生成 .h 不生成 .c 的情境

有時候你只需要 `.h`（例如 C++ 的 header-only library），這時把所有 `func` 都加上 `(inline ...)` 或直接把實作寫在 class 宣告裡：

```lisp
;; math_utils.h.cl → math_utils.h (header-only)
(pragma once)

(inline
  (func square float ((x float))
    (return (* x x))))

(inline
  (func clamp float ((val float) (lo float) (hi float))
    (if (< val lo) (return lo))
    (if (> val hi) (return hi))
    (return val)))
```

---

## 使用 `import` 處理跨檔案相依性

如果你的 `.cl` 實作檔需要依賴另一個 `.cl` 定義的 `template` 或 `lispmacro`，用 `import` 在翻譯期載入：

```lisp
;; foo.c.cl
(import common-macros)   ;; 翻譯時執行 common-macros.cl，使其 template/lispmacro 可用
                         ;; 輸出的 C 碼中會插入 /* common-macros.cl LOADED */
(func ...)
```

`import`（`c.lisp:637`）是**翻譯期**的操作，它不會在 C 輸出中產生 `#include`，只是讓 LISP/c 的巨集和 template 在當前 session 中可用。如果需要 C 層面的 `#include`，請另外用 `(header ...)` 或 `(include ...)`。
