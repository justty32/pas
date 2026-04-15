# LISP/c 專家教學 (03)：C++ 支援、MPI 與命名轉換

本章介紹 LISP/c 針對現代開發環境（C++）與平行運算（MPI）的深度整合。

## 1. C++ 深度支援
LISP/c 不只是翻譯 C，它也能寫出優雅的 C++。

### 核心關鍵字
*   `(headers++ iostream)` -> 生成 `#include <iostream>` (不加 .h)。（`headers++` → `c.lisp:795`，`header++` → `c.lisp:791`）
*   `(using std)` -> 生成 `using namespace std;`。（`using` → `c.lisp:949`）
*   `<<+` 與 `>>+`：流操作符（串接多個參數且不加多餘括號）。（`<<+` → `c.lisp:439`，`>>+` → `c.lisp:440`）
*   `(new ...)` 與 `(delete[] ...)`。（`new` → `c.lisp:956`，`delete` → `c.lisp:813`）

### 完整 C++ 範例：Vector 類別
（`class` → `c.lisp:857`，`cx`/`construct` → `c.lisp:877`，`op`/`operator` → `c.lisp:903`，`t&`/`typ&` → `c.lisp:839`）
```lisp
(headers++ iostream)
(using std)

(class vec
    (public
        (var x float)
        (var y float)
        ;; 建構子 (cx)
        (cx ((f1 float) (f2 float)) 
            ((x f1) (y f2)))
        ;; 運算子重載 (+)
        (op + vec ((v (t& vec)))
            (var res vec)
            (= (slot res x) (+ x (slot v x)))
            (= (slot res y) (+ y (slot v y)))
            (return res))))

(main
    (v (@v1 1.0 2.0) vec)
    (v (@v2 3.0 4.0) vec)
    (v v3 vec (+ v1 v2))
    (<<+ cout (str "Result: ") (slot v3 x) (str ", ") (slot v3 y) endl)
    (return 0))
```

## 2. MPI 平行運算
LISP/c 使用「斜線語法」來對應 MPI 的複雜常數與函數。（MPI 同義詞表完整定義於 `c.lisp:1143–1283`）

| Lispsy 語法 | 編譯後的 C 程式碼 | 原始碼位置 |
| :--- | :--- | :--- |
| `mpi/comm/world` | `MPI_COMM_WORLD` | `c.lisp:1198` |
| `mpi/init` | `MPI_Init` | `c.lisp:1242` |
| `mpi/success` | `MPI_SUCCESS` | `c.lisp:1144` |

### MPI 範例
```lisp
(headers mpi stdio)
(main
    (vars (rank size))
    (@mpi/init (addr argc) (addr argv))
    (@mpi/comm/rank mpi/comm/world (addr rank))
    (@mpi/printf (str "Hello from rank %d\\n") rank)
    (@mpi/finalize))
```

## 3. 命名轉換工具 (Naming Tools)
當您需要轉換變數風格（例如 C++ 常用的 CamelCase）時，LISP/c 提供極速轉換。所有命名轉換最終都在 `c-strify`（`c.lisp:139`）與 `cof`（`c.lisp:367`）中處理：

*   **`=` (大寫開頭)**：`(=this-is-test)` -> `ThisIsTest`（`cof` 中 `#\=` 分支 → `c.lisp:387`，`camelcase-c` → `c.lisp:316`）
*   **`%` (小寫開頭)**：`(%this-is-test)` -> `thisIsTest`（`cof` 中 `#\%` 分支 → `c.lisp:388`，`lcamelcase-c` → `c.lisp:328`）
*   **`!` (全大寫)**：`(!my-const)` -> `MY_CONST`（`c-strify` 中 `#\!` 分支 → `c.lisp:145`）

## 4. 進階編譯指令
在 CLISP REPL 中，您可以使用更細緻的編譯指令。（`compile-cl-file` → `c.lisp:1440`，`compile-and-run-cl-file` → `c.lisp:1454`）

```lisp
;; 指定編譯器與連結庫
(compile-cl-file "main.cl" :cc "nvcc" :libs "-lm -lpthread")
```
