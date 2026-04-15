# 擴充型別：typedef 與型別別名 (11)

本章介紹在 LISP/c 中如何使用 `typedef` 建立型別別名，以及 LISP/c 專屬的「翻譯期別名」機制 `syn`。這兩種機制雖然都叫「別名」，但作用層次完全不同。

---

## 兩種別名機制的區別

| 機制 | 關鍵字 | 作用層 | 輸出 |
|------|--------|--------|------|
| C 的型別別名 | `typedef`（`c.lisp:622`） | C 編譯期 | 在 C 程式碼中輸出 `typedef ...` |
| LISP/c 的翻譯別名 | `syn`（`c.lisp:479`） | LISP/c 翻譯期 | 無 C 輸出，只影響翻譯行為 |

---

## 1. `typedef`：C 層的型別別名

### 基本語法

`(typedef 原始型別 新名稱)`（`c.lisp:622`）

```lisp
;; typedef int my_int;
(typedef int my-int)

;; typedef unsigned long size_t;
(typedef (unsigned long) size-t)

;; typedef float real_t;
(typedef float real-t)
```

輸出：
```c
typedef int my_int;
typedef unsigned long size_t;
typedef float real_t;
```

> **注意**：`typedef` 在 LISP/c 中會自動加上結尾的 `;\n`（`c.lisp:624`），不需要手動加。

---

## 2. 指標型別別名

用 `t*`（`c.lisp:473`）或 `pt`（`c.lisp:530`）表示指標型別：

```lisp
;; typedef char* string_t;
(typedef (t* char) string-t)

;; typedef int* int_ptr;
(typedef (t* int) int-ptr)

;; typedef void** handle_t;
(typedef (t* void 2) handle-t)
```

輸出：
```c
typedef char* string_t;
typedef int* int_ptr;
typedef void** handle_t;
```

---

## 3. struct typedef（最常見用法）

C 語言中最常見的 `typedef struct` 有兩種做法：

### 做法 A：`typedef` + `struct` 分開寫（允許前向宣告）

```lisp
;; 先 typedef（前向宣告，讓 struct 裡的指標可以用 linked_list_node 型別）
(typedef (struct linked-list-node) linked-list-node)

;; 再定義 struct
(struct linked-list-node
  (((pt prev) linked-list-node)
   ((pt next) linked-list-node)
   ((pt data) void)))
```

輸出：
```c
typedef struct linked_list_node linked_list_node;

struct linked_list_node{
  linked_list_node *prev;
  linked_list_node *next;
  void *data;
};
```

這也是 `test.cl` 中使用的模式（`test.cl:3–4`）。

### 做法 B：inline typedef（struct 和別名一起定義）

```lisp
;; typedef struct { int x; int y; } point_t;
(typedef (struct point ((x int) (y int))) point-t)
```

輸出：
```c
typedef struct point{
  int x;
  int y;} point_t;
```

---

## 4. 函式指標型別別名

函式指標使用 `funcarg`（`c.lisp:612`）表示：

```lisp
;; typedef void (*callback_t)(int, void*);
(typedef (funcarg callback-t void ((x int) ((pt data) void))) callback-t)
```

輸出：
```c
typedef void(*callback_t)(int x,void *data) callback_t;
```

常見的函式指標 typedef 範式：

```lisp
;; 比較函式（用於 qsort）
(typedef (funcarg comparator int (((pt a) void) ((pt b) void))) comparator)

;; 事件處理函式
(typedef (funcarg event-handler void ((event-type int) ((pt data) void))) event-handler)

;; 不帶參數的回呼
(typedef (funcarg thunk void ()) thunk)
```

---

## 5. 用 `template` 批次產生 typedef

結合 `template`（`c.lisp:701`）可以一次產生多種型別的別名：

```lisp
;; 為每個型別產生 xxx_array_t = xxx*
(template make-array-type (typ)
  (typedef (t* typ) (sym/add typ -array-t)))

(make-array-type int)
(make-array-type float)
(make-array-type double)
```

輸出：
```c
typedef int* int_array_t;
typedef float* float_array_t;
typedef double* double_array_t;
```

---

## 6. `syn`：LISP/c 翻譯期的型別別名

`syn`（`c.lisp:479`）和 `unsyn`（`c.lisp:482`）操作的是 `*c-synonyms*` hash table（`c.lisp:10`），在翻譯期讓一個名稱被替換成另一個名稱，**不會在 C 輸出中留下任何東西**。

### 基本用法

```lisp
;; 在 .cl 檔中
(syn my-int int)         ;; 之後 my-int 在翻譯時等同於 int
(var x my-int 42)        ;;=> "int x=42"
(func foo my-int ()      ;;=> "int foo(){...}"
  (return x))
```

### 與 `typedef` 的比較

```lisp
;; typedef：在 C 程式碼中真的定義別名
(typedef int my-int)
;; C 輸出：typedef int my_int;
;; 之後 C 程式碼中 my_int 和 int 是同一個型別

;; syn：只在 LISP/c 翻譯期有效
(syn my-int int)
;; C 輸出：（無）
;; 翻譯時 my-int 直接變成 int，最終 C 碼看不到 my_int 這個名稱
```

### `syn` 的實用場景

#### 場景一：給長型別名稱取簡稱

```lisp
;; 在這份 .cl 檔裡，用 str 代替 (t* char)
(syn str (t* char))

(func greet void ((name str))   ;; name 的型別翻譯成 char*
  (@printf (s. "Hello, %s\n") name))
```

> **警告**：`str` 本身是 LISP/c 的字串字面量關鍵字（`c.lisp:545`），不要真的用 `str` 作為 `syn` 的名稱。

#### 場景二：平台相關型別切換

```lisp
;; 根據平台選擇 int 或 long
(lisp
  (if (> most-positive-fixnum (expt 2 31))
    (cof '(syn platform-int long))
    (cof '(syn platform-int int))))

(var x platform-int 0)   ;; 自動選擇正確的 C 型別
```

#### 場景三：取消別名

```lisp
(syn alias real-name)
;; ... 一段程式碼 ...
(unsyn alias)   ;; 之後 alias 不再是 real-name 的別名
```

---

## 7. 完整範例：定義一套自訂數值型別系統

```lisp
(header stdint)   ;; 引入 uint8_t, uint16_t 等

;; C 層 typedef（讓 C 程式碼和外部函式庫可見）
(typedef (unsigned char)  u8)
(typedef (unsigned short) u16)
(typedef (unsigned int)   u32)
(typedef (t* u8)          u8-ptr)

;; LISP/c 層別名（只在翻譯時有效，C 輸出看不到）
(syn byte u8)
(syn word u16)

;; 現在可以用 byte/word 寫程式碼，編譯結果使用 u8/u16
(func read-byte u8 (((pt buf) u8-ptr) (offset u32))
  (return ([]buf offset)))

(func read-word u16 (((pt buf) u8-ptr) (offset u32))
  (var lo byte ([]buf offset))
  (var hi byte ([]buf (+ offset 1)))
  (return (+ lo (<< hi 8))))
```

輸出：
```c
#include <stdint.h>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef u8* u8_ptr;

u8 read_byte(u8_ptr buf,u32 offset){
   return (buf)[offset];
}

u16 read_word(u8_ptr buf,u32 offset){
   u8 lo=(buf)[offset];
   u8 hi=(buf)[(offset)+(1)];
   return (lo)+((hi)<<(8));
}
```

注意：`byte` 和 `word` 在輸出中被替換成 `u8`/`u16`，因為它們是 `syn` 定義的翻譯期別名。
