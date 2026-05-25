# 教學 02：完整的 C 程式實戰

這篇的目的是把速查表裡的語法**用起來**——每支程式都是完整可編譯的，能看到輸出。每段程式後附產生的 C 原始碼，讓你確認 C-Mera 輸出長什麼樣。

---

## 程式 A：K&R 版 strcmp

最基本的字串比較。示範 `for`（空 init）、陣列索引、字元字面值。

`strcmp.lisp`：
```lisp
(include <stdio.h>)

(function my-strcmp ((char *p) (char *q)) -> int
  (decl ((int i = 0))
    (for (() (== p[i] q[i]) i++)
      (when (== p[i] #\null)
        (return 0)))
    (return (- p[i] q[i]))))

(function main () -> int
  (printf "%d\n" (my-strcmp "abc" "abc"))
  (printf "%d\n" (my-strcmp "abc" "abd"))
  (printf "%d\n" (my-strcmp "z" "a"))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>

int my_strcmp(char *p, char *q)
{
    int i = 0;
    for (; p[i] == q[i]; i++) {
        if (p[i] == '\0') {
            return 0;
        }
    }
    return p[i] - q[i];
}

int main(void)
{
    printf("%d\n", my_strcmp("abc", "abc"));
    printf("%d\n", my_strcmp("abc", "abd"));
    printf("%d\n", my_strcmp("z", "a"));
    return 0;
}
```

```bash
cm c strcmp.lisp -o strcmp.c && gcc -std=c99 strcmp.c -o strcmp && ./strcmp
# 0
# -1
# 25
```

**重點**：
- `for` 的 init 段空 `()`——因為 `i` 已在外面的 `decl` 宣告。
- `p[i]`、`i++`、`#\null` 全部由 reader 直接剖析，不需要額外語法。
- 函式名 `my-strcmp` → C 的 `my_strcmp`（`-` 轉 `_`）。

---

## 程式 B：wc -l（統計行數）

示範 `set` 在 `while` 條件裡當運算式用、字元 EOF 的處理。

`wcl.lisp`：
```lisp
(include <stdio.h>)

(function main () -> int
  (decl ((int c)
         (int nl = 0))
    (while (!= (set c (getchar)) EOF)
      (when (== c #\newline)
        ++nl))
    (printf "%d\n" nl)
    (return 0)))
```

產生的 C：
```c
#include <stdio.h>

int main(void)
{
    int c;
    int nl = 0;
    while ((c = getchar()) != EOF) {
        if (c == '\n') {
            ++nl;
        }
    }
    printf("%d\n", nl);
    return 0;
}
```

```bash
cm c wcl.lisp -o wcl.c && gcc wcl.c -o wcl
echo -e "a\nb\nc" | ./wcl   # 3
```

**重點**：
- `(set c (getchar))` 會展開成 `c = getchar()`，然後整個被 `(!= ... EOF)` 包住。
- `EOF` 沒有定義——直接當 C 識別字輸出，gcc 從 `<stdio.h>` 找到。

---

## 程式 C：Shellsort

示範巢狀 `for`、多重賦值 `(set a x b y)`、陣列字面值 `clist`。

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
          (set temp      v[j]
               v[j]      v[(+ j gap)]
               v[(+ j gap)] temp))))))

(function main () -> int
  (decl ((int a[] = (clist 5 3 8 1 4 7 2 6))
         (int n = (/ (sizeof a) (sizeof a[0]))))
    (shellsort a n)
    (for ((int i = 0) (< i n) ++i)
      (printf "%d " a[i]))
    (printf "\n"))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>

void shellsort(int *v, int n)
{
    int temp;
    for (int gap = n / 2; gap > 0; gap /= 2) {
        for (int i = gap; i < n; i++) {
            for (int j = i - gap; j >= 0 && v[j] > v[j + gap]; j -= gap) {
                temp = v[j];
                v[j] = v[j + gap];
                v[j + gap] = temp;
            }
        }
    }
}

int main(void)
{
    int a[] = {5, 3, 8, 1, 4, 7, 2, 6};
    int n = sizeof(a) / sizeof(a[0]);
    shellsort(a, n);
    for (int i = 0; i < n; ++i)
        printf("%d ", a[i]);
    printf("\n");
    return 0;
}
```

```bash
cm c shellsort.lisp -o shell.c && gcc shell.c -o shell && ./shell
# 1 2 3 4 5 6 7 8
```

**重點**：
- `(set a x  b y  c z)` 是多重賦值，**按順序**展開為三行 `a=x; b=y; c=z;`。
- `(clist 5 3 8 ...)` → `{5, 3, 8, ...}`（只在 C 後端有效）。
- `(sizeof a)` / `(sizeof a[0])` 直接寫，不需要括號技巧。

---

## 程式 D：struct + 指標 + 函式指標

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

(typedef (double (fpointer distance-fn ((struct point*) (struct point*)))))

(function main () -> int
  (decl (((struct point) p1 = (clist 0.0 0.0))
         ((struct point) p2 = (clist 3.0 4.0))
         (distance-fn fp = dist))
    (printf "dist = %.2f\n" (fp &p1 &p2)))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>
#include <math.h>

struct point {
    double x;
    double y;
};

double dist(struct point *a, struct point *b)
{
    double dx = a->x - b->x;
    double dy = a->y - b->y;
    return sqrt(dx * dx + dy * dy);
}

typedef double (*distance_fn)(struct point*, struct point*);

int main(void)
{
    struct point p1 = {0.0, 0.0};
    struct point p2 = {3.0, 4.0};
    distance_fn fp = dist;
    printf("dist = %.2f\n", fp(&p1, &p2));
    return 0;
}
```

```bash
cm c points.lisp -o pts.c && gcc pts.c -lm -o pts && ./pts
# dist = 5.00
```

**重點**：
- `struct point` 當型別用時，括號 `(struct point)` 是必要的——C-Mera 需要知道型別的邊界在哪裡。
- 函式指標用 `fpointer`：`(double (fpointer fp ((struct point*) (struct point*))))`，格式是 `(回傳型別 (fpointer 名稱 (參數型別列表)))`。
- `a->x` 由 reader 自動展開為 `(pref a x)` → `a->x`。

---

## 程式 E：strncpy + 緩衝區複製（綜合練習）

這支程式把所有基礎語法合在一起：字元陣列、迴圈、指標操作、`sizeof`。

`strbuf.lisp`：
```lisp
(include <stdio.h>)

(function safe-copy ((char *dst) (const char *src) (int max)) -> int
  (decl ((int i = 0))
    (while (&& (< i (- max 1)) src[i])
      (set dst[i] src[i])
      i++)
    (set dst[i] #\null)
    (return i)))

(cpp "define BUF_SIZE 64")

(function main () -> int
  (decl ((char buf[BUF_SIZE]))
    (decl ((int len = (safe-copy buf "Hello, C-Mera!" BUF_SIZE)))
      (printf "copied %d chars: %s\n" len buf)))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>

int safe_copy(char *dst, const char *src, int max)
{
    int i = 0;
    while (i < max - 1 && src[i]) {
        dst[i] = src[i];
        i++;
    }
    dst[i] = '\0';
    return i;
}

#define BUF_SIZE 64

int main(void)
{
    char buf[BUF_SIZE];
    {
        int len = safe_copy(buf, "Hello, C-Mera!", BUF_SIZE);
        printf("copied %d chars: %s\n", len, buf);
    }
    return 0;
}
```

```bash
cm c strbuf.lisp -o strbuf.c && gcc strbuf.c -o strbuf && ./strbuf
# copied 14 chars: Hello, C-Mera!
```

**重點**：
- `(cpp "define BUF_SIZE 64")` 插入 `#define`。
- 巢狀 `decl` 會產生巢狀 `{ }` scope——C99 允許這樣做。
- `src[i]` 在 C 裡是「如果字元非零則為 true」，直接用作 while 條件。

---

## 小練習建議

按難度排：

1. **改 strcmp**：把 `my-strcmp` 擴充成 `my-strncmp`，加上第三個 `int n` 參數，最多比較 n 個字元。
2. **wc 擴充**：在 `wc -l` 基礎上再加字元計數和單字計數（遇到空白切斷算一個單字）。
3. **Quicksort**：把 Shellsort 改成 Quicksort，熟悉遞迴寫法。
4. **矩陣乘法**：`(function mat-mul ((int m) (int n) (int p) ...) -> void)`，三重 `for` 迴圈。

不用急著學巨集，先用純語法把感覺建起來。
