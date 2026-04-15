# 教學 04：用 Lisp 巨集做元編程（C-Mera 的真正價值）

到這裡為止，C-Mera 只是「換皮的 C」——皮甚至還比較醜。它真正值得用的原因是 **Lisp 巨集**：你可以在編譯期（也就是 sexp→C 的那一步）**跑任意的 Common Lisp 程式**，產生 C 程式碼。這比 C 的 `#define` 強太多了。

下面幾招從「簡單好用」排到「有點酷」，不需要懂整個 CL，只要記住幾個關鍵字就夠。

## 關鍵字三件套

- **`defmacro`**：在**編譯期**定義一個展開函式。模板裡用反引號 `` ` ``、`,` 插值、`,@` 展開清單。
- **`lisp`**：在 C-Mera 程式碼中插入「一段純 Lisp，結果當 sexp 用」。
- **`cintern` / `symbol-append`**：把字串變符號（組合出新的 C 識別字）。

就這三件，夠你做很多事。

## 招式 1：參數化的 include（避免重複 include guard）

C 的 `#define`：
```c
#define SQ(x) ((x) * (x))
```
C-Mera：
```lisp
(defmacro sq (x)
  `(* ,x ,x))

(decl ((int a = (sq 5))))     ; => int a = 5 * 5;
```
**差別**：`x` 不會被求值兩次嗎？其實 `(sq (++ i))` 會展開成 `(* (++ i) (++ i))`，副作用兩次——跟 C 的 `#define` 一樣的坑。要避開就多包一層：
```lisp
(defmacro sq (x)
  (let ((g (gensym)))                ; 產生唯一名字，像 C 的 __v_123
    `(decl ((int ,g = ,x))
       (* ,g ,g))))
```
C 的 `#define` 做不到 hygienic，C-Mera 可以。

## 招式 2：`static_assert` 風格的編譯期計算

C 裡陣列大小只能是常數；想寫「一個陣列的大小 = 另一個常數乘 2」這種需求，用 C-Mera：
```lisp
(decl ((int BASE = 16)))          ; 這是 C 的變數

;; 但這個展開是在 Lisp 期算的：
(defmacro buf-size () 
  (* 16 2))                        ; 返回 32（Lisp 數字，不是 sexp）

(decl ((char buf[(buf-size)])))    ; => char buf[32];
```
`(buf-size)` 在 C-Mera 處理時就被計算成 `32`，寫進 C 原始碼。

## 招式 3：產生一整族相似的函式

寫一個「針對 int、float、double 各產生一版」的 `max`：
```lisp
(defmacro defmax (type)
  (let ((name (cintern (format nil "max_~a" type))))
    `(function ,name ((,type a) (,type b)) -> ,type
       (if (> a b) (return a) (return b)))))

(defmax int)
(defmax float)
(defmax double)
```
展開後產生三個 C 函式：`max_int`、`max_float`、`max_double`。

這是 C 宏做不到的——C 的 `#define` 不能用 `type` 拼接出 `max_int`（其實可以用 `##` 但很醜）。

## 招式 4：條件編譯（比 `#ifdef` 聰明）

```lisp
(defparameter *debug* t)            ; 一個 Lisp 變數

(defmacro log-if-debug (msg)
  (if *debug*
      `(fprintf stderr ,msg)
      nil))                          ; 返回 nil = 不產生任何 C 程式碼

(function work () -> void
  (log-if-debug "entered work\\n")
  ...)
```
把 `*debug*` 改成 `nil`，`log-if-debug` 就完全消失——連一行 `#ifdef` 都沒有，最終 `.c` 裡沒有任何痕跡。

## 招式 5：從資料生成程式

最能展現 Lisp 威力的寫法。假設要為十個欄位分別產生 getter：
```lisp
(defparameter *fields* '((int  id)
                          (char name[32])
                          (double balance)))

(defmacro make-getters (struct-name fields)
  `(progn
     ,@(loop for f in fields collect
             (let* ((type (first f))
                    (name (second f))
                    (fn-name (cintern (format nil "~a_get_~a" struct-name name))))
               `(function ,fn-name ((,struct-name* s)) -> ,type
                  (return s->,name))))))

(struct account
  (decl ,*fields*))

(make-getters account #.*fields*)
```
`make-getters` 在展開期遍歷 `*fields*`，為每個欄位吐出一個 C 函式。**欄位改了就不必同步改 getter**，整批重生。

## 招式 6：`lisp` 逃生門

在一段程式中間需要用純 Lisp 運算：
```lisp
(decl ((int table[] = (clist
                        (lisp (loop for i from 0 below 10 collect (* i i)))))))
;; => int table[] = {0, 1, 4, 9, 16, 25, 36, 49, 64, 81};
```
`(lisp ...)` 裡面整段以純 Lisp 求值，結果（一個數字列表）被 `clist` 直接當 C 陣列初始化值。

## 招式 7：macrolet（區域巨集）

在一個函式內部暫時定義一個巨集，不外洩：
```lisp
(function main () -> int
  (macrolet ((twice (x) `(progn ,x ,x)))
    (twice (printf "hi\\n")))
  (return 0))
```

## 何時動巨集、何時別動？

**該動**：
- 重複的樣板程式碼（getter、tag dispatch table、switch 根據 enum 分支）。
- 編譯期就能算完的常數表、lookup table。
- 有多個型別的同構程式（int/float/double 各一版）。
- 想在 C 裡做「條件編譯」但又想比 `#ifdef` 乾淨。

**別動**：
- 一次性的邏輯，寫 macro 反而害人看不懂。
- 本來 C 的 inline 函式就能解決（讓 C 編譯器去處理）。
- 沒有重複的東西硬寫 macro。

## 調試技巧

1. **先用 REPL 展開看看**：
   ```lisp
   (asdf:load-system :cmu-c)
   (in-package :cmu-c)
   (macroexpand-1 '(defmax int))     ; 看 macro 展開成什麼
   ```
2. **`simple-print` 看最終 C**：
   ```lisp
   (cm-c:simple-print
     (function foo () -> int
       (decl ((int x = (sq 5))))
       (return x)))
   ```
   直接把產出的 C 印到 stdout，不用進 make。
3. **常見錯誤**：忘了反引號的 `,` → 會把 Lisp 變數當成 C 識別字輸出，結果 `.c` 裡會冒出奇怪名字；用 `macroexpand-1` 一看就發現。

## 下一步
- 讀 `tests/c.misc.03.macrolet.defmacro.lisp` 和 `c.misc.06.macrolet2.lisp`，這是官方的巨集範例。
- 看 C++ 的 `tests/cxx.class.00.lisp`：裡面有「在 class 外用 `defmacro className` 動態產生類別名」的示範。
- 要更野的話，讀 C-Mera 的論文 *Defmacro for C: Lightweight, Ad Hoc Code Generation* (ELS'14)，就是講這套設計的。
