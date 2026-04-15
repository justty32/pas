# C 前置處理器巨集 (12)：#define、#ifdef 與 #pragma

本章說明如何在 LISP/c 中使用 C 的前置處理器指令（preprocessor directives），包括常數定義、條件編譯、pragma，以及直接插入任意前置處理器指令的方式。

---

## 重要提醒：`ifdef`/`ifndef` 的已知 Bug

LISP/c 內建的 `(ifdef ...)`（`c.lisp:650`）和 `(ifndef ...)`（`c.lisp:653`）在目前版本有 bug：format 字串中的 expr 沒有被插入輸出，會輸出字面的 `#ifdef ~%` 而不是 `#ifdef YOUR_MACRO`。

**所有條件編譯都請改用 `(cpp ...)` 來撰寫。**（`cpp` → `c.lisp:678`）

---

## 1. `define`：常數與無參數巨集

`(define 名稱 值)`（`c.lisp:646`）產生 `#define NAME value`。

名稱前加 `!` 會自動全大寫（`c-strify` → `c.lisp:145`）：

```lisp
(define !pi 3.14159)
(define !max-size 1024)
(define !version "1.0.0")
(define !debug 1)
```

輸出：
```c
#define PI 3.14159
#define MAX_SIZE 1024
#define VERSION "1.0.0"
#define DEBUG 1
```

> **注意**：`define` 只接受兩個參數（名稱和值），不能定義帶參數的 function-like macro。若需要帶參數的巨集，請用 `(cpp define ...)` 直接輸出（見第 5 節）。

---

## 2. `cpp`：任意前置處理器指令

`(cpp 關鍵字 引數...)`（`c.lisp:678`）輸出 `#關鍵字 引數...`，是最通用的做法：

```lisp
(cpp define !max-size 1024)    ;;=> "#define MAX_SIZE 1024"
(cpp ifndef !my-header-h)      ;;=> "#ifndef MY_HEADER_H"
(cpp define !my-header-h)      ;;=> "#define MY_HEADER_H"
(cpp endif)                    ;;=> "#endif"
(cpp pragma once)              ;;=> "#pragma once"
(cpp include "<stdio.h>")      ;;=> "#include <stdio.h>"
(cpp error "missing config")   ;;=> "#error missing_config"
(cpp warning "deprecated")     ;;=> "#warning deprecated"
```

---

## 3. 條件編譯：`#ifdef` / `#ifndef` / `#if`

### 正確的 include guard 寫法

```lisp
;; mylib.h 的內容
(cpp ifndef !mylib-h)
(cpp define !mylib-h)

;; ... 標頭檔內容 ...
(struct point ((x float) (y float)))
(func point-add point ((a point) (b point)))

(cpp endif)
```

輸出：
```c
#ifndef MYLIB_H
#define MYLIB_H

struct point{
  float x;
  float y;
}

point point_add(point a,point b)

#endif
```

### `#if` / `#else` / `#endif`

使用 `if#`（`c.lisp:656`）、`else#`（`c.lisp:659`）和 `endif`（`c.lisp:661`）：

```lisp
(if# (>= !version 2))
  (func new-api void ())
(else#)
  (func old-api void ())
(cpp endif)
```

輸出：
```c
#if VERSION>=2
void new_api()

#else
void old_api()

#endif
```

> **注意**：`else#` 和 `endif` 的回傳值包含 `~%`（`c.lisp:660,662`），這只在透過 `write-out` 路徑時才會展開成換行。在 `cwf` 或直接使用 `cof` 時，`~%` 會保持字面形式。若遇到輸出有 `~%` 字串，改用 `(cpp else)` 和 `(cpp endif)` 代替。

### `#ifdef` 用法

```lisp
(cpp ifdef !debug)
  (@printf (s. "[DEBUG] x = %d\n") x)
(cpp endif)
```

輸出：
```c
#ifdef DEBUG
   printf("[DEBUG] x = %d\n",x);
#endif
```

### `#ifndef` 用法

```lisp
(cpp ifndef !ndebug)
  (define !debug-mode 1)
(cpp endif)
```

輸出：
```c
#ifndef NDEBUG
#define DEBUG_MODE 1
#endif
```

---

## 4. `pragma`：編譯器提示

`(pragma 引數...)`（`c.lisp:663`）輸出 `#pragma ...`：

```lisp
(pragma once)
;;=> "#pragma once"

(pragma pack 1)
;;=> "#pragma pack 1"

(pragma GCC optimize "O3")
;;=> "#pragma GCC optimize O3"

(pragma comment lib "user32.lib")
;;=> "#pragma comment lib user32.lib"
```

---

## 5. 帶參數的 function-like macro

LISP/c 的 `define` 只能定義無參數的常數巨集。帶參數的巨集需要用 `(cpp define ...)` 直接插入：

```lisp
;; #define MAX(a,b) ((a)>(b)?(a):(b))
(cpp "define MAX(a,b) ((a)>(b)?(a):(b))")

;; #define SWAP(type,a,b) do { type _tmp=a; a=b; b=_tmp; } while(0)
(cpp "define SWAP(type,a,b) do { type _tmp=a; a=b; b=_tmp; } while(0)")
```

> **建議**：對於複雜的 function-like macro，通常用 LISP/c 的 `template` 或 `lispmacro` 直接在翻譯期展開會更清楚，不需要輸出 C 巨集。

---

## 6. `include`：包含標頭檔

`include`（`c.lisp:634`）用於包含標頭檔：

```lisp
;; 系統標頭（尖括號）
(include stdio)         ;;=> "#include <stdio>"  （通常搭配 h-file）
(include (h-file stdio)) ;;=> "#include <stdio.h>"

;; 本地標頭（引號）
(include ("mylib" :local t))   ;;=> "#include \"mylib\""
(include ((h-file mylib) :local t)) ;;=> "#include \"mylib.h\""
```

實際上 `header`（`c.lisp:674`）和 `headers`（`c.lisp:676`）是更常用的包裝：

```lisp
(header stdio)             ;;=> "#include <stdio.h>"
(headers stdio stdlib math) ;;=> 三行 #include
(header ("mylib" :local t)) ;;=> "#include \"mylib.h\""
```

---

## 7. `lisp`：在翻譯期執行任意 Lisp 並插入結果

`lisp`（`c.lisp:681`）讓你在翻譯期執行 Lisp 程式碼，把結果插入 C 輸出：

```lisp
;; 在翻譯期決定要 define 什麼
(lisp
  (if (eq :unix *features*)
    "#define PLATFORM_UNIX 1"
    "#define PLATFORM_WIN32 1"))
```

```lisp
;; 在翻譯期產生一系列 #define
(lisp
  (format nil "~{~a~%~}"
    (loop for i from 0 to 7 collect
      (format nil "#define BIT~a (1<<~a)" i i))))
```

輸出：
```c
#define BIT0 (1<<0)
#define BIT1 (1<<1)
...
#define BIT7 (1<<7)
```

---

## 8. 完整範例：帶條件編譯的可移植標頭

```lisp
;; portable_types.h.cl → portable_types.h

(pragma once)

;; 平台偵測
(cpp ifndef !windows)
(cpp define !int64-t "long long")
(cpp define !uint32-t "unsigned int")
(cpp else)
(cpp define !int64-t "__int64")
(cpp define !uint32-t "unsigned long")
(cpp endif)

;; 型別定義
(typedef !int64-t  i64)
(typedef !uint32-t u32)
(typedef (unsigned char) u8)

;; Debug 巨集（只在 DEBUG 模式啟用）
(cpp ifdef !debug)
(cpp "define LOG(fmt,...) fprintf(stderr,\"[DBG] \" fmt \"\\n\",##__VA_ARGS__)")
(cpp else)
(cpp "define LOG(fmt,...) ((void)0)")
(cpp endif)

;; API 可見性
(cpp ifndef !api-export)
(cpp ifdef !windows)
(cpp "define API_EXPORT __declspec(dllexport)")
(cpp else)
(cpp "define API_EXPORT __attribute__((visibility(\"default\")))")
(cpp endif)
(cpp endif)
```

---

## 快速參考表

| 功能 | LISP/c 語法 | 原始碼 | 注意 |
|------|------------|--------|------|
| `#define NAME val` | `(define !name val)` | `c.lisp:646` | 只能無參數 |
| `#define` 任意 | `(cpp define ...)` | `c.lisp:678` | 通用 |
| `#ifdef` | `(cpp ifdef !name)` | `c.lisp:678` | 勿用內建 `ifdef`（有 bug） |
| `#ifndef` | `(cpp ifndef !name)` | `c.lisp:678` | 勿用內建 `ifndef`（有 bug） |
| `#if expr` | `(if# expr)` | `c.lisp:656` | |
| `#else` | `(cpp else)` | `c.lisp:678` | `else#` 有 `~%` 問題 |
| `#endif` | `(cpp endif)` | `c.lisp:678` | `endif` 有 `~%` 問題 |
| `#pragma ...` | `(pragma ...)` | `c.lisp:663` | |
| `#pragma once` | `(pragma once)` | `c.lisp:663` | 推薦 include guard |
| `#include <x.h>` | `(header x)` | `c.lisp:674` | |
| `#include "x.h"` | `(header ("x" :local t))` | `c.lisp:674` | |
| 翻譯期插入 | `(lisp ...)` | `c.lisp:681` | 執行 Lisp，插入結果字串 |
