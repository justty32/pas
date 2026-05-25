# 教學 04：用 Lisp 巨集做元編程（C-Mera 真正的價值）

到這裡為止，C-Mera 只是「換皮的 C」——而且皮甚至比 C 醜一點。它真正值得用的原因是 **Lisp 巨集**：你可以在「sexp → C」那一步裡跑任意的 Common Lisp 程式，產生 C 程式碼。這比 `#define` 強很多——它是一個完整的程式語言，不是字串替換。

---

## 核心工具三件套

- **`defmacro`**：在展開期定義一個函式。用反引號 `` ` `` 當模板，`,` 插入值，`,@` 展開列表。
- **`lisp`**：在 C-Mera 程式碼中間插入「一段純 Lisp，結果當 sexp 用」。
- **`cintern` / `symbol-append`**：把字串或符號組合成新的 C 識別字。

---

## 招式 1：Hygienic macro（避免副作用重複）

C 的 `#define SQ(x) ((x)*(x))` 有個著名的坑：

```c
int n = 0;
SQ(++n);    // 展開成 ((++n) * (++n))，n 被遞增兩次
```

C-Mera 可以解決：

```lisp
;; 不安全版（和 C 的 #define 一樣）
(defmacro sq-unsafe (x)
  `(* ,x ,x))

;; 安全版：用 gensym 產生唯一的臨時變數名
(defmacro sq (x)
  (let ((g (gensym)))
    `(decl ((int ,g = ,x))
       (* ,g ,g))))
```

展開結果（`(sq (++ n))`）：
```c
{
    int g1234 = ++n;    /* gensym 產生的名字 */
    g1234 * g1234;
}
```

`gensym` 每次產生不同的名字，保證不和外部衝突。C 的 `##` 做不到這點。

**完整範例**：

```lisp
(include <stdio.h>)

(defmacro sq (x)
  (let ((g (gensym)))
    `(decl ((int ,g = ,x))
       (* ,g ,g))))

(function main () -> int
  (decl ((int n = 3))
    (printf "%d\n" (sq n))       ; 9（n 不變）
    (printf "%d\n" (sq (++ n)))  ; 16（n 先從 3 → 4，sq(4)=16）
    (printf "n=%d\n" n))         ; n=4
  (return 0))
```

---

## 招式 2：編譯期計算常數

C 裡陣列大小必須是常數；但你可以在 C-Mera 展開期**用 Lisp 計算**，寫進 C：

```lisp
(include <stdio.h>)

(defmacro buf-size ()
  (* 16 1024))    ; Lisp 在展開期算出 16384，數字被輸出為 C 整數字面值

(defmacro log2-of (n)
  (round (/ (log n) (log 2))))   ; 也可以做更複雜的計算

(decl ((char buf[(buf-size)])))
; => char buf[16384];

(decl ((int depth = (log2-of 256))))
; => int depth = 8;
```

**和 `#define` 的差別**：`#define BUF (16 * 1024)` 是字串替換，編譯器要算；`(buf-size)` 是 Lisp 已算好的數字，產出時就是 `16384`。

---

## 招式 3：產生一族相似的函式

這是 C-Mera 最典型的用法——不想為 `int`/`float`/`double` 分別寫三個幾乎一樣的函式：

```lisp
(include <stdio.h>)

(defmacro defmax (type)
  (let ((name (cintern (format nil "max_~a" type))))
    `(function ,name ((,type a) (,type b)) -> ,type
       (if (> a b) (return a) (return b)))))

(defmax int)
(defmax float)
(defmax double)

(function main () -> int
  (printf "%d\n" (max-int 3 7))
  (printf "%.2f\n" (max-float 1.5 2.3))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>

int max_int(int a, int b) { if (a > b) return a; return b; }
float max_float(float a, float b) { if (a > b) return a; return b; }
double max_double(double a, double b) { if (a > b) return a; return b; }

int main(void) {
    printf("%d\n", max_int(3, 7));
    printf("%.2f\n", max_float(1.5, 2.3));
    return 0;
}
```

`cintern` 把字串 `"max_int"` 變成 Lisp 符號，然後被 `,name` 插入 sexp 模板裡。

---

## 招式 4：條件編譯（比 `#ifdef` 乾淨）

```lisp
(defparameter *debug* t)    ; Lisp 變數，不進 C

(defmacro log-debug (fmt &rest args)
  (if *debug*
      `(fprintf stderr ,fmt ,@args)
      nil))                  ; nil = 不產生任何 C 程式碼

(function work ((int x)) -> void
  (log-debug "work called with x=%d\n" x)
  ...)

(function main () -> int
  (work 42)
  (return 0))
```

把 `*debug*` 改成 `nil`：`log-debug` 完全消失，最終 `.c` 裡一行都不留。最終使用者看不到任何 `#ifdef`——因為條件判斷在 Lisp 層就發生了。

---

## 招式 5：從資料生成程式（最強的模式）

假設你有一個 `account` 結構，想為每個欄位自動產生 getter 函式：

```lisp
(include <stdio.h>)

(defparameter *account-fields*
  '((int    id)
    (double balance)
    (int    age)))

;; 產生 struct 定義
(defmacro def-struct (name fields)
  `(struct ,name
     (decl ,fields)))

;; 批次產生 getter
(defmacro def-getters (struct-name fields)
  `(progn
     ,@(loop for f in fields collect
             (let* ((ret-type (first f))
                    (field    (second f))
                    (fn-name  (cintern (format nil "~a_get_~a" struct-name field))))
               `(function ,fn-name ((,struct-name* s)) -> ,ret-type
                  (return s->,field))))))

(def-struct account #.*account-fields*)
(def-getters account #.*account-fields*)

(function main () -> int
  (decl ((account a = (clist 1 999.9 30)))
    (printf "id=%d balance=%.1f age=%d\n"
            (account-get-id &a)
            (account-get-balance &a)
            (account-get-age &a)))
  (return 0))
```

產生的 C：
```c
#include <stdio.h>

struct account {
    int id;
    double balance;
    int age;
};

int account_get_id(account* s) { return s->id; }
double account_get_balance(account* s) { return s->balance; }
int account_get_age(account* s) { return s->age; }

int main(void) {
    account a = {1, 999.9, 30};
    printf("id=%d balance=%.1f age=%d\n",
           account_get_id(&a),
           account_get_balance(&a),
           account_get_age(&a));
    return 0;
}
```

**欄位改了，一行程式碼不用動**——`*account-fields*` 是唯一的事實來源，struct 定義和所有 getter 都從它生成。

---

## 招式 6：`lisp` 逃生門

在一段程式中間需要跑 Lisp 計算，把結果嵌入 C：

```lisp
(include <stdio.h>)

;; 用 Lisp 在展開期產生一個平方表
(decl ((int table[] = (clist
                        (lisp (loop for i from 0 below 10 collect (* i i)))))))
; => int table[] = {0, 1, 4, 9, 16, 25, 36, 49, 64, 81};

(function main () -> int
  (for ((int i = 0) (< i 10) ++i)
    (printf "%d " table[i]))
  (printf "\n")
  (return 0))
```

`(lisp ...)` 裡整段以純 Lisp 求值，回傳值（這裡是一個數字列表）被 `clist` 當作 C 陣列初始化值。

另一個例子——產生有規律的字串常數：

```lisp
(defparameter *day-names*
  #("Sun" "Mon" "Tue" "Wed" "Thu" "Fri" "Sat"))

(decl ((const char* days[] =
         (clist (lisp (coerce *day-names* 'list))))))
; => const char* days[] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
```

---

## 招式 7：macrolet（函式內的區域巨集）

有時候你不想讓巨集外洩，只在一個函式裡用：

```lisp
(function process ((int *data) (int n)) -> void
  (macrolet ((swap (a b)
               (let ((tmp (gensym)))
                 `(decl ((int ,tmp = ,a))
                    (set ,a ,b ,b ,tmp))))
             (check-bounds (i)
               `(when (>= ,i n)
                  (fprintf stderr "out of bounds: %d\n" ,i)
                  (return))))
    (for ((int i = 0) (< i (- n 1)) ++i)
      (check-bounds i)
      (check-bounds (+ i 1))
      (when (> data[i] data[(+ i 1)])
        (swap data[i] data[(+ i 1)])))))
```

`swap` 和 `check-bounds` 只在 `process` 裡有效，外面看不到。

---

## 招式 8：defmacro 產生 enum + switch dispatch

一個完整的「tag dispatch」模式——enum 和 switch 來自同一份資料：

```lisp
(include <stdio.h>)

(defparameter *ops*
  '((ADD . "add")
    (SUB . "sub")
    (MUL . "mul")
    (DIV . "div")))

(defmacro def-op-enum (ops)
  `(enum opcode ,@(mapcar #'car ops)))

(defmacro def-op-dispatch (ops)
  `(function dispatch ((opcode op) (int a) (int b)) -> int
     (switch op
       ,@(loop for (tag . name) in ops collect
               `(,tag
                 (printf "%s: %d\n" ,name (funcall ,(cintern name) a b))
                 break))
       (default
        (fprintf stderr "unknown op\n")
        (return -1)))
     (return 0)))

(def-op-enum #.*ops*)
(def-op-dispatch #.*ops*)

(function add ((int a) (int b)) -> int (return (+ a b)))
(function sub ((int a) (int b)) -> int (return (- a b)))
(function mul ((int a) (int b)) -> int (return (* a b)))
(function div ((int a) (int b)) -> int (return (/ a b)))

(function main () -> int
  (dispatch ADD 10 3)
  (dispatch MUL 4 5)
  (return 0))
```

新增一個 op 只要改 `*ops*`，enum 和 switch 都自動跟著更新。

---

## 調試技巧

**1. 在 REPL 看 macro 展開**

```lisp
;; 先載入套件
(asdf:load-system :cmu-c)
(in-package :cmu-c)

;; 看展開結果
(macroexpand-1 '(defmax int))
; => (FUNCTION MAX_INT ((INT A) (INT B)) -> INT (IF (> A B) (RETURN A) (RETURN B)))
```

**2. `simple-print` 直接看 C 輸出**

```lisp
(cm-c:simple-print
  (function foo () -> int
    (decl ((int x = (sq 5)))
      (return x))))
```

直接印出產生的 C，不用跑 `cm` 指令。

**3. 常見錯誤：忘了反引號的 `,`**

```lisp
(defmacro bad-sq (x)
  `(* x x))    ; 忘了寫 ,x

;; 展開：(* X X)，把 X 當 C 變數名輸出
;; 應該：(* ,x ,x)
```

用 `macroexpand-1` 一看就發現：如果輸出裡有大寫的 `X` 而不是你傳進去的變數名，就是忘了逗號。

**4. `format nil` 拼接名字**

```lisp
(cintern (format nil "~a_~a" 'prefix 'suffix))
; => 'PREFIX_SUFFIX（Lisp symbol）
```

`~a` 是「原樣輸出」；`~(~a~)` 可以強制小寫；`format` 的完整語法見 Common Lisp HyperSpec。

---

## 何時用巨集、何時別用

**該用**：
- 重複的樣板程式碼（getter、setter、tag dispatch）。
- 編譯期就能算完的常數表或 lookup table。
- 同構程式（多個型別共用邏輯）。
- 條件編譯但又不想留 `#ifdef` 痕跡。

**不該用**：
- 一次性的程式碼——寫個普通函式就好。
- C 的 inline 函式或 `static` 函式能解決的事。
- 複雜的執行期邏輯——巨集在展開期跑，對執行期沒有幫助。

---

## 下一步

- 讀 `tests/c.misc.03.macrolet.defmacro.lisp`、`c.misc.06.macrolet2.lisp`——官方的巨集示範。
- 讀 `tests/cxx.class.00.lisp`——在 class 外用 `defmacro` 動態產生類別名的技法。
- 想深入理解：讀論文 *Defmacro for C: Lightweight, Ad Hoc Code Generation* (ELS'14)，是 C-Mera 設計理念的原始來源。
