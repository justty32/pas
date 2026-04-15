# LISP/c 進階教學 (02)：指標、結構與宏的威力

本章將帶領你掌握 LISP/c 中最具威力的部分：複雜的 C 指標、結構、強大的模板系統，以及對高效能運算的支持。

## 1. 指標 (Pointers)

在 Lisp 中宣告指標有兩種主要方式。

### 變數宣告中的指標
*   **C:** `int *p = NULL;`
*   **Lispsy:** `(var (pt p) int !null)`
    *   使用 `pt` 來修飾變數名稱。（`pt` → `c.lisp:530`）
*   **雙重指標:** `char **argv` 寫作 `((pt argv 2) char)`。

### 型別中的指標
*   **C:** `void* ptr;`
*   **Lispsy:** `(var ptr (t* void))`（`t*`/`typ*` → `c.lisp:473`）

### 指標操作
*   **取位址 (&):** `(&x)` 或 `(addr x)`。（`addr` → `c.lisp:525`）
*   **解引用 (*):** `(*p)` 或 `(ptr p)`。（`ptr` → `c.lisp:528`）
*   **結構存取 (->):** `(slot p member)`。（`slot` → `c.lisp:465`）

---

## 2. 陣列與結構 (Arrays & Structs)

### 陣列
*   **C:** `int arr[10];`
*   **Lispsy:** `(var (arr arr 10) int)`（`arr` → `c.lisp:536`）
*   **存取:** `([]arr i)` 或 `(nth arr i)`。（`nth` → `c.lisp:532`，`[]` 前綴 → `cof` `c.lisp:380`）

### 結構 (Structs)（`struct` → `c.lisp:569`）
*   **C 定義:**
    ```c
    struct point {
        int x;
        int y;
    };
    ```
*   **Lispsy 定義:**
    ```lisp
    (struct point (
        x
        y))
    ```

---

## 3. 模板系統 (Templates)

這是 LISP/c 超越傳統 C 預處理器的核心功能。它允許你寫出「會生成程式碼」的程式碼，且比 C 的 `#define` 巨集強大許多。

LISP/c 有三層模板機制，威力依序遞增：

| 機制 | 關鍵字 | 特性 |
|------|--------|------|
| 基本模板 | `template` | 文字替換，適合簡單重複 |
| 批次模板 | `templates` | 一次呼叫產生多份程式碼 |
| Lisp 巨集 | `lispmacro` / `lisp/c-macro` | 任意 Lisp 邏輯，最強大 |

---

### 3.1 `template`：基本模板

語法：`(template 模板名 (參數...) 模板本體)`（`template` → `c.lisp:701`，底層使用 `replacify` → `c.lisp:397` 和 `replacify-lambda` → `c.lisp:405`）

定義一個「模板」後，每次呼叫它就會把參數代入本體，產生一份 C 程式碼：

```lisp
(template swap-gen (typ)
    (func (sym/add swap- typ) void (((pt a) typ) ((pt b) typ))
        (var tmp typ (*a))
        (= (*a) (*b))
        (= (*b) tmp)))

(swap-gen int)    ;; 展開產生 swap_int
(swap-gen float)  ;; 展開產生 swap_float
(swap-gen double) ;; 展開產生 swap_double
```

C 輸出（以 `int` 為例）：
```c
void swap_int(int *a,int *b){
   int tmp=*(a);
   *(a)=*(b);
   *(b)=tmp;
}
```

**`sym/add`**（`c.lisp:462`）是模板裡最常用的輔助函式，它把多個 symbol 拼接成一個識別字（內部使用 `strsof` → `c.lisp:122` 和 `cofsy` → `c.lisp:395`）：

```lisp
(sym/add swap- int)    ;;=> "swap_int"
(sym/add vec3- float)  ;;=> "vec3_float"
(sym/add get- x -)     ;;=> "get_x_"
```

---

### 3.2 多參數模板

模板可以有多個參數：

```lisp
(template array-op (typ op-name op-sym)
    (func (sym/add array- op-name - typ) typ
          (((pt a) typ) ((pt b) typ) (n int))
        (var i int 0)
        (var (pt result) typ (@malloc (* n (@sizeof typ))))
        (for (= i 0) (< i n) (++ i)
            (= ([]result i) (op-sym ([]a i) ([]b i))))
        (return result)))

(array-op int  add  +)
(array-op int  mul  *)
(array-op float add +)
```

輸出：
```c
int *array_add_int(int *a,int *b,int n){ ... }
int *array_mul_int(int *a,int *b,int n){ ... }
float *array_add_float(float *a,float *b,int n){ ... }
```

---

### 3.3 `templates`：一次展開多份

`templates`（`c.lisp:708`）是 `template` 的批次版本，一個呼叫可以展開多個型別：

```lisp
(templates make-print (typ)
    (func (sym/add print- typ) void ((val typ))
        (@printf (str "%d\n") val)))

;; 一次呼叫，展開 int / long / float 三個版本
(make-prints int long float)
```

等同於依序呼叫 `(make-print int)` `(make-print long)` `(make-print float)`，但更簡潔。

---

### 3.4 模板內使用條件邏輯：`lispmacro`

`lispmacro`（`c.lisp:684`）讓你在翻譯期執行**任意 Lisp 程式碼**，並輸出 C 字串。這比 `template` 強大得多，因為你可以使用 `if`、`loop`、遞迴等 Lisp 功能。定義後的 `lispmacro` 名稱會被記錄在 `*macrolist*`（`c.lisp:11`）中，防止重複定義：

```lisp
;; 根據型別選擇不同的 printf 格式字串
(lispmacro typed-print (typ val)
    (let ((fmt (cond
                 ((eq typ 'int)    "%d")
                 ((eq typ 'float)  "%f")
                 ((eq typ 'double) "%lf")
                 (t                "%p"))))
        (c `(@printf (str ,fmt) ,val))))

;; 呼叫
(typed-print int   x)    ;;=> printf("%d",x)
(typed-print float y)    ;;=> printf("%f",y)
(typed-print char  z)    ;;=> printf("%p",z)  (fallback)
```

**關鍵差異：`template` vs `lispmacro`**

| | `template` | `lispmacro` |
|--|-----------|-------------|
| 邏輯 | 只能做文字替換 | 可以執行任意 Lisp 程式碼 |
| 參數 | 在本體中用符號替換 | 是普通 Lisp 函式參數，可以做任何運算 |
| 本體寫法 | 直接寫 LISP/c S-expression | 需要在最後用 `(c ...)` 或 `(cof ...)` 產生 C 字串 |

---

### 3.5 `lisp/c-macro`：遞迴模板

`lisp/c-macro` 是最強的機制（Lisp 層巨集定義於 `c.lisp:44`，LISP/c 層的翻譯函式定義於 `c.lisp:694`）。它允許模板**呼叫自己**（遞迴），用於產生巢狀或可變深度的 C 結構：

```lisp
;; 產生 N 層巢狀 for 迴圈
(lisp/c-macro nested-for (vars limits body)
    (if (or (null vars) (null limits))
        ;; 基本情況：no more vars，直接展開 body
        `(block ,body nil)
        ;; 遞迴情況：wrap 一個 for，再遞迴
        `(for (var ,(car vars) int 0)
              (< ,(car vars) ,(car limits))
              (++ ,(car vars))
              (nested-for ,(cdr vars) ,(cdr limits) ,body))))

;; 使用：3 層 for 迴圈
(nested-for (i j k) (3 4 5)
    (@printf (str "%d %d %d\n") i j k))
```

展開成：
```c
for(int i=0;((i)<(3));++(i)){
   for(int j=0;((j)<(4));++(j)){
      for(int k=0;((k)<(5));++(k)){
         printf("%d %d %d\n",i,j,k);
      };
   };
}
```

---

### 3.6 完整範例：用模板實作「泛型容器」

```lisp
;; 定義 stack 模板：為各型別生成完整的 stack 實作
(template make-stack (typ)
    (progn
        ;; Struct 定義
        (struct (sym/add typ -stack)
            (((pt data) typ)
             (size int)
             (capacity int)))

        ;; new
        (func (sym/add typ -stack-new) (t* (sym/add typ -stack)) ()
            (var (pt s) (sym/add typ -stack) (@malloc (@sizeof (struct (sym/add typ -stack)))))
            (= (slot s capacity) 16)
            (= (slot s size) 0)
            (= (slot s data) (@malloc (* 16 (@sizeof typ))))
            (return s))

        ;; push
        (func (sym/add typ -stack-push) void
              (((pt s) (sym/add typ -stack)) (val typ))
            (= ([]  (slot s data) (slot s size)) val)
            (++ (slot s size)))

        ;; pop
        (func (sym/add typ -stack-pop) typ
              (((pt s) (sym/add typ -stack)))
            (--- (slot s size))
            (return ([] (slot s data) (slot s size))))))

;; 一行產生 int 和 float 兩個完整的 stack 實作
(make-stack int)
(make-stack float)
```

---

## 4. 高效能運算支援 (HPC Support)

LISP/c 針對並行運算（Parallel Computing）內建了許多關鍵字與別名。

### Pthreads 範例
你可以直接使用 `pthread/create` 等名稱，它們會正確編譯成 C 的 `pthread_create`。（Pthread 同義詞表 → `c.lisp:1286–1327`）
```lisp
(headers pthread)
(main
    (var (arr threads !nthreads) pthread-t)
    (@pthread/create (addr ([]threads i)) !null (addr func) !null))
```

### CUDA 核心宣告
使用 `cuda/global`（`c.lisp:608`）或 `cuda/device`（`c.lisp:610`）來定義 GPU 核心。（CUDA 同義詞表 → `c.lisp:1113–1143`）
*   **Lispsy:**
    ```lisp
    (cuda/global kernel void (((pt data) float))
        (var i int thread/idx/x) ;; threadIdx.x → c.lisp:1125
        (= ([]data i) (* ([]data i) 2.0f)))
    ```

---

## 5. 總結：開發心法

1.  **善用縮寫：** 熟練後多用 `@`、`[]`、`->` 等縮寫。
2.  **變數命名：** 習慣 `kebab-case`（`my-var`），產出的 C 會是標準的 `snake_case`（`my_var`）。
3.  **大寫符號：** 所有的 `#define` 和關鍵字常數請加 `!`。
4.  **括號哲學：** 只要記住「括號內第一個字是動作」，你就能輕鬆閱讀任何 LISP/c 代碼。
