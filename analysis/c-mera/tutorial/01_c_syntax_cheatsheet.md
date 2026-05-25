# 教學 01：C 語法速查（sexp ↔ C 完整對照）

每行左邊是 C-Mera 寫法，右邊是產生的 C。只要熟這張表，就能寫 95% 的 C 程式。

---

## 關鍵心法（讀懂這五條，後面不需要背）

1. **所有東西都是 `(頭 參數 …)`**；運算子也寫在前面。`a + b` → `(+ a b)`。
2. **型別在變數名前面**，像 C：`int x = 0` → `(int x = 0)`。
3. **你沒定義的符號都當 C 函式呼叫**；`printf`、`malloc`、`EOF` 全部原樣輸出。
4. **標識字中的 `-` 轉 `_`**：`my-var` → `my_var`。用 `-` 命名是慣例，不是強制。
5. **大小寫保留**：C-Mera 的 readtable 設定了 `:invert`，會把 UPPER 變 lower，但 `#:MyVar` 前綴可強制保留任意大小寫。`MAX_LEN`、`TRUE`、`std` 都能直接寫。

---

## 字面值

| C-Mera | 產生的 C | 說明 |
|---|---|---|
| `42` | `42` | 整數 |
| `0xff` | `0xff` | 十六進位（原樣） |
| `3.14` | `3.14` | 浮點 |
| `0.5f` | `5.0e-01` | `f` 結尾觸發 float 字面；reader 把它正規化 |
| `"hello"` | `"hello"` | 字串 |
| `#\A` | `'A'` | 字元字面值 |
| `#\newline` | `'\n'` | 換行 |
| `#\null` | `'\0'` | 空字元 |
| `#\space` | `' '` | 空白 |

**坑**：`0.5f` 在 SBCL 會印成 `5.0e-01` 而非 `0.5f`——這是 Lisp reader 的浮點格式問題，不影響語意，但看起來奇怪。想輸出原樣，改用 `(cpp "0.5f")`。

---

## 運算子

### 算術 / 比較

```lisp
(+ a b c)           ; => a + b + c
(- a b)             ; => a - b
(- a)               ; => -a（一元負號）
(* a b)             ; => a * b
(* p)               ; => *p（一元 * = 解參考）
(/ a b)             ; => a / b
(% a b)             ; => a % b

(== a b)            ; => a == b
(!= a b)            ; => a != b
(< a b)             ; => a < b
(<= a b)            ; => a <= b
(> a b)             ; => a > b
(>= a b)            ; => a >= b
```

### 邏輯

```lisp
(and a b)           ; => a && b
(or a b)            ; => a || b
(not a)             ; => !a
(! a)               ; => !a（同上，兩種寫法）
(&& a b)            ; => a && b（也可直接寫符號形式）
(|| a b)            ; => a || b
```

### 位元

```lisp
(& a b)             ; => a & b（二元 AND）
(| a b)             ; => a | b
(^ a b)             ; => a ^ b（XOR）
(~ a)               ; => ~a（NOT）
(<< a n)            ; => a << n
(>> a n)            ; => a >> n
```

**注意**：`(& a)` 是取址（addr-of），`(& a b)` 是 bitwise AND——由運算元個數決定。

### 取址與解參考

```lisp
(& a)               ; => &a（取址，一個運算元）
(addr-of a)         ; => &a（更明確的寫法）
(* p)               ; => *p（解參考，一個運算元）
(dref p)            ; => *p（更明確的寫法）
(targ-of p)         ; => *p（第三種寫法，見 reader）
```

Reader 也能自動拆解：寫 `&myvar` 這個符號，reader 會變成 `(addr-of myvar)`；寫 `*ptr` 會變成 `(targ-of ptr)`。

### 遞增 / 遞減

```lisp
++i                 ; => ++i（前置，reader 直接認）
i++                 ; => i++（後置）
--j                 ; => --j
j--                 ; => j--
```

這些**不是括號形式**，直接寫符號名，reader 會剖析名字裡的 `++`/`--`。

---

## 賦值

```lisp
(= x 3)             ; => x = 3;
(set x 3)           ; => x = 3;（推薦寫法，不會被 Lisp 變數遮蔽）
(set x 3 y 4 z 5)   ; => x = 3; y = 4; z = 5;（多重賦值，依序展開）
(+= x 1)            ; => x += 1;
(-= x 2)            ; => x -= 2;
(*= x 3)            ; => x *= 3;
(/= x 2)            ; => x /= 2;
(%= x 7)            ; => x %= 7;
(&= mask 0xff)      ; => mask &= 0xff;
(|= flags 0x01)     ; => flags |= 0x01;
(^= val bit)        ; => val ^= bit;
(<<= x 1)           ; => x <<= 1;
(>>= x 1)           ; => x >>= 1;
```

**`set` 和 `=` 的差異**：在 C-Mera 的 Common Lisp 環境裡，`=` 在某些 package 可能被遮蔽；用 `set` 最穩。

---

## 控制流程

### if / else

```lisp
(if (< a b)
    (printf "a\n")         ; then（單一敘述）
    (printf "b\n"))         ; else（可省）
```

產生：
```c
if (a < b) printf("a\n"); else printf("b\n");
```

**多敘述用 `progn`**（這是 C-Mera 最容易忘的規則）：

```lisp
(if (< a b)
    (progn
      (printf "small: %d\n" a)
      (set result a))
    (progn
      (printf "big: %d\n" b)
      (set result b)))
```

產生：
```c
if (a < b) {
    printf("small: %d\n", a);
    result = a;
} else {
    printf("big: %d\n", b);
    result = b;
}
```

### when（if + progn + 無 else）

```lisp
(when (< a b)
  (printf "less\n")
  (set x 1))
```

產生：
```c
if (a < b) {
    printf("less\n");
    x = 1;
}
```

C-Mera **沒有 `unless`**——用 `(when (not ...))` 或 `(if (not ...) ...)`。

### cond

```lisp
(cond ((< a 0) (printf "neg\n"))
      ((== a 0) (printf "zero\n"))
      (t        (printf "pos\n")))
```

產生：
```c
if (a < 0) printf("neg\n");
else if (a == 0) printf("zero\n");
else printf("pos\n");
```

`t` 代表 else（Lisp 的真值常數）。

### switch

```lisp
(switch x
  (0 (printf "zero\n") break)
  (1 (printf "one\n")  break)
  (2
   (printf "two-a\n")
   (printf "two-b\n")
   break)
  (default (printf "other\n")))
```

產生：
```c
switch (x) {
    case 0:  printf("zero\n"); break;
    case 1:  printf("one\n"); break;
    case 2:  printf("two-a\n"); printf("two-b\n"); break;
    default: printf("other\n");
}
```

`break` 直接寫在 case body 裡，不需要括號。

### for（三段式）

```lisp
(for ((int i = 0) (< i n) ++i)
  (printf "%d\n" i))
```

產生：
```c
for (int i = 0; i < n; ++i)
    printf("%d\n", i);
```

頭部是**一個括號包三段**：`(init test step)`。每段可以是宣告、運算式或空 `()`：

```lisp
(for (() (< i 10) i++)        ; 不宣告初始變數，只有 test + step
  ...)

(for ((int i = 0) (< i n) ()) ; 沒有 step（但通常 body 裡有 i++）
  ...)
```

### while

```lisp
(while (< i 10)
  (printf "%d\n" i)
  ++i)
```

產生：
```c
while (i < 10) {
    printf("%d\n", i);
    ++i;
}
```

`do-while` 目前不支援（README 有提）——繞法是用 `(while t ... (if exit-cond break))`。

### break / continue / return / goto

```lisp
break                ; => break;
continue             ; => continue;
(return 0)           ; => return 0;
(return (+ a b))     ; => return a + b;
(goto done)          ; => goto done;
(label done)         ; => done:
```

---

## 變數宣告 `decl`

`decl` 是 C-Mera 的核心形式，它同時代表「宣告 + 進入一個 scope」：

```lisp
(decl ((int i = 0)
       (int j = 5)
       (const unsigned long x = 0xDEAD)
       (char buf[128])
       (int *p = &i))
  (printf "%d %d\n" i j))
```

產生：
```c
{
    int i = 0;
    int j = 5;
    const unsigned long x = 0xdead;
    char buf[128];
    int *p = &i;
    printf("%d %d\n", i, j);
}
```

**重要規則**：
- 分隔符 `=` 是**必須的**，不能省。
- 型別可以跨多個 token：`const unsigned long x` 會把前三個 token 當型別，`x` 是名字。
- 指標寫 `int *p` 或 `int* p` 都行（C-Mera 不挑剔空格位置）。
- 陣列尺寸寫在名字後面：`char buf[128]`。

### 多行宣告 vs. 單行宣告

```lisp
;; 多行：宣告幾個變數 + body
(decl ((int a = 1) (int b = 2))
  (printf "%d\n" (+ a b)))

;; 單行（無 body）：只宣告，不開 scope
(decl ((int x = 0)))
```

### 陣列初始化

```lisp
(decl ((int days[] = (clist 31 28 31 30 31 30 31 31 30 31 30 31))))
```

產生：
```c
int days[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
```

`clist` = "C list"，就是 `{ ... }` 的 sexp 對應。

---

## 函式宣告與定義

```lisp
;; 基本形式
(function add ((int a) (int b)) -> int
  (return (+ a b)))

;; 無回傳值
(function greet () -> void
  (printf "hi\n"))

;; 複合回傳型別（超過一個 token 要括號）
(function get-size () -> (unsigned int)
  (return n))

;; Prototype（無 body）
(function add ((int a) (int b)) -> int)
```

產生（以 `add` 為例）：
```c
int add(int a, int b)
{
    return a + b;
}
```

**可變參數（varargs）**：

```lisp
(function my-printf ((const char* fmt) &rest) -> void
  ...)
```

產生：
```c
void my_printf(const char* fmt, ...)
{
    ...
}
```

---

## 函式呼叫

```lisp
(printf "%d\n" x)              ; => printf("%d\n", x);
(strcmp s1 s2)                 ; => strcmp(s1, s2);
(malloc (* n (sizeof int)))    ; => malloc(n * sizeof(int));
```

**任何你沒在 C-Mera 定義的符號，都直接輸出為 C 識別字**。所以標準庫函式、全域巨集全部可以直接呼叫。

---

## 標頭引入

```lisp
(include <stdio.h>)            ; => #include <stdio.h>
(include "myheader.h")         ; => #include "myheader.h"
```

---

## 前置處理器

```lisp
(cpp "define MAX 100")         ; => #define MAX 100
(cpp "undef MAX")              ; => #undef MAX
(cpp "ifdef DEBUG")            ; => #ifdef DEBUG
(cpp "endif")                  ; => #endif
(pragma "once")                ; => #pragma once
```

### 單行 / 區塊註解

```lisp
(comment "這是 C 風格單行注釋")
; => // 這是 C 風格單行注釋

(comment "block comment" :prefix "/*")
; => /* block comment */
```

注意：**Lisp 的 `;` 不輸出到 C**。只有 `(comment ...)` 才會在產出的 C 裡留下 `//`。

---

## 型別轉換 / sizeof

```lisp
(cast int x)                   ; => (int)x
(cast (unsigned char) c)       ; => (unsigned char)c
(sizeof int)                   ; => sizeof(int)
(sizeof x)                     ; => sizeof(x)
(sizeof (struct foo))          ; => sizeof(struct foo)
```

---

## struct / union / enum

```lisp
;; struct 定義
(struct point
  (decl ((int x)
         (int y))))
```

產生：
```c
struct point {
    int x;
    int y;
};
```

```lisp
;; 宣告並初始化
(decl ((struct point p = (clist 1 2))))
```

產生：
```c
struct point p = {1, 2};
```

```lisp
;; union
(union data
  (decl ((int i)
         (float f)
         (char bytes[4]))))
```

```lisp
;; enum（基本）
(enum color red green blue)
;; => enum { red, green, blue };

;; enum（指定初值）
(enum direction (north 0) south east west)
;; => enum { north = 0, south, east, west };
```

### 成員存取（reader 自動拆）

```lisp
p.x                   ; => p.x
ptr->y                ; => ptr->y
arr[i]                ; => arr[i]
arr[i][j]             ; => arr[i][j]
a.b.c                 ; => a.b.c（鏈式存取）
```

也可以顯式形式：

```lisp
(oref p x)            ; => p.x（object reference）
(pref ptr y)          ; => ptr->y（pointer reference）
(aref arr i j)        ; => arr[i][j]（array reference）
```

---

## typedef

```lisp
(typedef (decl ((unsigned int u32))))
; => typedef unsigned int u32;

(typedef (struct point) Point)
; => typedef struct point Point;
```

---

## 常見坑整理

| 坑 | 原因 | 解法 |
|---|---|---|
| `if` 的 then/else 有多行卻沒 `progn` | C-Mera 只把緊跟的第一個 sexp 當 body | 用 `(progn ...)` 包起來 |
| 函式名有 `do-something`，輸出卻是 `do_something`？不見 | 正常行為，`-` → `_` | 這就是預期輸出 |
| `(* a b c)` 展開 `a * b * c`，但 `(* p)` 卻是 `*p` | 一個運算元時是解參考，多個時是乘法 | 用 `(dref p)` 或 `(targ-of p)` 更明確 |
| 型別名含空格（`unsigned int`）在宣告裡被吃錯 | C-Mera 會貪婪吃直到 `=` 或最後一個 token | 正常工作；若不確定，加括號 `((unsigned int) x)` |
| 把 `(& a b)` 當取址用 | 兩個運算元是 bitwise AND | 取址用 `(& a)` 或 `(addr-of a)` |
| `3.14f` 變成科學記號 | SBCL/CCL 的浮點輸出格式 | 語意正確，若要原樣用 `(cpp "3.14f")` |

---

下一篇（02）：三支完整的小 C 程式——把這張表裡的每個功能都用上一遍。
