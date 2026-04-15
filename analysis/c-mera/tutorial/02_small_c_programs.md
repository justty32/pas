# 教學 02：三支完整的小 C 程式

把速查表拿來用。每支程式都是完整可編譯的，路徑放在 `~/playground/` 下練手即可。

## 程式 A：K&R 版 strcmp

`strcmp.lisp`：
```lisp
(include <stdio.h>)

(function strcmp ((char *p) (char *q)) -> int
  (decl ((int i = 0))
    (for (() (== p[i] q[i]) i++)
      (if (== p[i] #\null)
          (return 0)))
    (return (- p[i] q[i]))))

(function main () -> int
  (printf "%d\\n" (strcmp "abc" "abc"))
  (printf "%d\\n" (strcmp "abc" "abd"))
  (return 0))
```

```bash
cm c strcmp.lisp -o strcmp.c && gcc strcmp.c -o strcmp && ./strcmp
# 0
# -1
```

重點：
- `for` 的第一段是空 `()`（不宣告變數，因為 `i` 已在外面宣告）。
- `p[i]`、`i++`、`#\null` 全部是 reader 直接吃進來的形式。

## 程式 B：wc -l（統計行數）

`wcl.lisp`：
```lisp
(include <stdio.h>)

(function main () -> int
  (decl ((int c)
         (int nl = 0))
    (while (!= (set c (getchar)) EOF)
      (if (== c #\newline)
          ++nl))
    (printf "%d\\n" nl)
    (return 0)))
```

```bash
cm c wcl.lisp -o wcl.c
gcc wcl.c -o wcl
echo -e "a\nb\nc" | ./wcl    # 3
```

重點：
- `(set c (getchar))` 當作一個回傳值用，就像 C 的 `c = getchar()` 在 while 頭裡。
- `EOF`、`getchar` 都沒定義——直接當 C 符號/函式輸出。

## 程式 C：Shellsort

`shellsort.lisp`：
```lisp
(include <stdio.h>)

(function shellsort ((int *v) (int n)) -> void
  (decl ((int temp))
    (for ((int gap = (/ n 2)) (> gap 0) (/= gap 2))
      (for ((int i = gap) (< i n) i++)
        (for ((int j = (- i gap))
              (&& (>= j 0) (> v[j] v[(+ j gap)]))
              (-= j gap))
          (set temp v[j]
               v[j] v[(+ j gap)]
               v[(+ j gap)] temp))))))

(function main () -> int
  (decl ((int a[] = (clist 5 3 8 1 4 7 2 6))
         (int n = (/ (sizeof a) (sizeof a[0]))))
    (shellsort a n)
    (for ((int i = 0) (< i n) ++i)
      (printf "%d " a[i]))
    (printf "\\n"))
  (return 0))
```

```bash
cm c shellsort.lisp -o shell.c && gcc shell.c -o shell && ./shell
# 1 2 3 4 5 6 7 8
```

重點：
- 多重賦值 `(set a x b y c z)` = `a = x; b = y; c = z;`（按順序展開）。
- 陣列字面值 `(clist 5 3 8 ...)` → `{5, 3, 8, ...}`。
- `sizeof a` 與 `sizeof a[0]` 直接寫。

## 程式 D（加分）：struct + 指標 + 函式指標

`points.lisp`：
```lisp
(include <stdio.h>)
(include <math.h>)

(struct point
  (decl ((double x)
         (double y))))

(function dist ((struct point *a) (struct point *b)) -> double
  (decl ((double dx = (- a->x b->x))
         (double dy = (- a->y b->y)))
    (return (sqrt (+ (* dx dx) (* dy dy))))))

(function main () -> int
  (decl (((struct point) p1 = (clist 0.0 0.0))
         ((struct point) p2 = (clist 3.0 4.0))
         (double (fpointer fp ((struct point*) (struct point*))) = dist))
    (printf "%.2f\\n" (fp &p1 &p2)))
  (return 0))
```

```bash
cm c points.lisp -o pts.c && gcc pts.c -lm -o pts && ./pts
# 5.00
```

重點：
- `struct point` 當型別時要括號 `(struct point)`（C-Mera 需要知道型別邊界）。
- 函式指標用 `fpointer`：`(double (fpointer fp ((struct point*) (struct point*))) = dist)`。
- `a->x`、`b->y` reader 會自動展開為 `pref`。

## 小練習
拿這三隻改一改：把 strcmp 擴充成 strncmp；wc -l 加上字元總數；shellsort 換成 quicksort。別急著去學 macro，先用純轉換把感覺建起來。
