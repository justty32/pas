# 教學 01：C 語法速查（sexp ↔ C 對照）

每行左邊是 C-Mera 寫法，右邊是產生的 C。只要熟這張表，就能寫 95% 的 C 程式。

## 關鍵心法
1. **所有東西都是 `(頭 參數 …)`**；運算子也寫在前面。`a + b` → `(+ a b)`。
2. **型別在變數名前面**，像 C：`int x = 0` → `(int x = 0)`。
3. **運算式就地 eval**；你在 repl 沒看過的函式名，C-Mera 會當成 C 函式呼叫（例如 `(printf "x")` → `printf("x");`）。
4. **Lisp 預設不分大小寫**，但 C-Mera 有做「保留原大小寫」的設定，所以 `MAX_LEN`、`std` 都能寫。若遇到自動變大寫的情況，用 `#:Foo` 強制保留。
5. **標識字中的 `-` 會被轉成 `_`**：`my-var` → `my_var`。

## 字面值
| C-Mera | C |
|---|---|
| `42` | `42` |
| `0xff` | `0xff` |
| `3.14f` | `3.14e+00` (float 字尾 f 觸發) |
| `"hello"` | `"hello"` |
| `#\A` | `'A'` |
| `#\newline` | `'\n'` |
| `#\null` | `'\0'` |

## 運算子
| C-Mera | C |
|---|---|
| `(+ a b c)` | `a + b + c` |
| `(- a b)` / `(- a)` | `a - b` / `-a` |
| `(* a b)` / `(* p)` | `a * b` / `*p`（只有一個運算元變解參考） |
| `(/ a b)` | `a / b` |
| `(% a b)` | `a % b` |
| `(== a b)` `(!= a b)` `(< a b)` `(>= a b)` | 如 C |
| `(and a b)` `(or a b)` | `a && b`、`a \|\| b`（也可寫 `&&`、`\|\|`） |
| `(not a)` / `(! a)` | `!a` |
| `(& a)` / `(addr-of a)` | `&a` |
| `(dref p)` / `(targ-of p)` | `*p` |
| `++i` / `--i` | `++i` / `--i`（直接寫在符號後） |
| `i++` / `i--` | `i++` / `i--`（reader 自動認） |
| `(?: c a b)`（概念上）實際用 `(if c a b)` 當 expr 很少，建議用明碼：見下方 |

## 賦值
| C-Mera | C |
|---|---|
| `(= x 3)` | `x = 3;` |
| `(set x 3)` | `x = 3;` |
| `(set x 3 y 4 z 5)` | `x = 3; y = 4; z = 5;`（多重賦值） |
| `(+= x 1)` `(*= x 2)` `(\|= mask F)` 等 | 同 C |

## 控制流程
```lisp
(if (< a b)
    (printf "a\\n")        ; then
    (printf "b\\n"))       ; else (可省)
```
```c
if (a < b) printf("a\n"); else printf("b\n");
```

多敘述 then / else：**必須用 `progn` 或 `when` 包起來**。
```lisp
(if (< a b)
    (progn (printf "a\\n") (set x 1))
    (printf "b\\n"))

(when (< a b)                     ; == if + progn + 無 else
  (printf "less\\n")
  (set x 1))
```

C-Mera **沒有 `unless`**（README 明說）。

### cond
```lisp
(cond ((< a 0) (printf "neg\\n"))
      ((== a 0) (printf "zero\\n"))
      (t        (printf "pos\\n")))
```

### switch
```lisp
(switch x
  (0 (printf "zero\\n") break)
  (1 (printf "one\\n")  break)
  (default (printf "other\\n")))
```

### for
```lisp
(for ((int i = 0) (< i n) ++i)
  (printf "%d\\n" i))
```
三段式頭部用一組括號包起來；第一段可以是宣告也可以空 `()`。

### while
```lisp
(while (< i 10)
  ++i)
```
`do-while` 尚未支援（README 也有提）。

### break / continue / return / goto
```lisp
break
continue
(return 0)
(goto done)
(label done)
```

## 變數宣告 `decl`
```lisp
(decl ((int i = 0)
       (int j = 5)
       (const unsigned long x = 0)
       (char buf[128])
       (int *p = &i))
  ;; body：在這個 scope 裡的敘述
  (printf "%d %d\\n" i j))
```
翻譯為：
```c
{
    int i = 0;
    int j = 5;
    const unsigned long x = 0;
    char buf[128];
    int *p = &i;
    printf("%d %d\n", i, j);
}
```

- **型別可以貪婪吃多個詞**：`const unsigned long x` 會正確把前面當 specifier + type。
- **分隔符 `=` 是必要的**（舊版會猜，現在必須寫）。
- **指標**寫 `int *p` 或 `int* p` 都行。
- **陣列**寫 `(char buf[128])`；初始化用 `(char days[] = (clist 31 28 31 ...))`。

## 函式
```lisp
(function add ((int a) (int b)) -> int
  (return (+ a b)))

(function greet () -> void
  (printf "hi\\n"))
```
- `-> type` 指定回傳型別；複合回傳型別（例如 `unsigned int`）要用括號：`-> (unsigned int)`。
- 參數也用括號群組，每個都是 `(型別 名稱)`。
- 沒有 body 時就是 prototype 宣告。

變數參數：
```lisp
(function log ((const char* fmt) &rest) -> void
  ...)
```

## 函式呼叫
```lisp
(printf "%d\\n" x)             ; => printf("%d\n", x);
(strcmp s1 s2)                 ; => strcmp(s1, s2)
```
**你沒定義的符號都會被當 C 函式呼叫**——這就是為什麼能直接寫 `printf`。

## 標頭引入
```lisp
(include <stdio.h>)
(include "myheader.h")
```

## 註解與 C 預處理
```lisp
(comment "這是單行註解")                       ; => // 這是單行註解
(comment "block" :prefix "/*")                ; 自訂開頭
(cpp "define MAX 100")                        ; => #define MAX 100
(pragma "once")                               ; => #pragma once
```

## 型別轉換 / sizeof
```lisp
(cast int x)                                  ; => (int)x
(sizeof int)                                  ; => sizeof(int)
(sizeof (cast (struct foo) 0))                ; => sizeof((struct foo)0)
```

## struct / union / enum
```lisp
(struct point
  (decl ((int x)
         (int y))))

(decl ((struct point p = (clist 1 2))))        ; struct point p = {1, 2};

(enum color red green blue)                    ; enum { red, green, blue }
(enum direction (north 0) south east west)     ; 指定初值
```

存取欄位（reader 會自動拆開）：
```lisp
p.x                                            ; => p.x
ptr->y                                         ; => ptr->y
arr[i]                                         ; => arr[i]
arr[i][j]                                      ; => arr[i][j]
```
或顯式：`(oref p x)`、`(pref ptr y)`、`(aref arr i j)`。

## typedef
```lisp
(typedef (decl ((unsigned int u32)))) 
;; => typedef unsigned int u32;
```

下一篇實戰一點：把 K&R 的 `strcmp` 與一個小 wc 寫過一遍。
