# 教學 03：C++ 基礎（class、namespace、template、lambda）

用 `cm c++ file.lisp -o file.cpp`（或 `cm cxx`）。C++ 後端繼承 C 後端，前兩篇的寫法全都能用，**只是多了下面這些形式**。

## namespace 與字串型別名
`std::cout`、`std::vector<int>` 這類包含雙冒號的名字，直接當一個符號寫：`#:std::cout`、`#:std::vector`。`#:` 開頭在 Lisp 裡表示「uninterned symbol」，C-Mera 把它當成字面的 C++ 名稱丟出去。

```lisp
(include <iostream>)

(function main () -> int
  (<< #:std::cout "hello" #:std::endl)
  (return 0))
```

自己定義 namespace：
```lisp
(namespace math
  (function square ((int x)) -> int
    (return (* x x))))
;; =>
;; namespace math { int square(int x) { return x * x; } }
```
呼叫：`(#:math::square 3)` 或在檔案頂端 `(using-namespace math)`。

## class
```lisp
(include <iostream>)

(class Counter ()                     ; () 是繼承列表，空即無父類
  (private
   (decl ((int n))))
  (public
   (constructor () :init ((n 0)))
   (constructor ((int start)) :init ((n start)))
   (destructor
     (<< #:std::cout "bye " n #:std::endl))

   (function inc () -> void
     (++ n))
   (function value () -> int
     (return n))))

(function main () -> int
  (decl ((Counter c 10))
    (c.inc)
    (c.inc)
    (<< #:std::cout (c.value) #:std::endl)) ; 12
  (return 0))
```

要點：
- `(class Name (父類1 父類2) (private ...) (public ...) (protected ...))`。
- `constructor` / `destructor` 跟 `function` 寫法類似，但在 class 內自動取類別名。
- `:init ((member value) ...)` 是 member initializer list，對應 C++ 的 `: n(0)`。
- 在 class 外定義：`(constructor #:ClassName::ClassName (參數) ...)`。

## 繼承範例
```lisp
(class Base ()
  (public (function greet () -> void (<< #:std::cout "base\\n"))))

(class Derived ((public Base))
  (public (function greet () -> void (<< #:std::cout "derived\\n"))))
```

## new / delete
```lisp
(decl ((Counter* p = (new (Counter 5)))))   ; new Counter(5)
(delete p)

(decl ((int* arr = (new int[10]))))         ; new int[10]
(delete[] arr)
```

## template
```lisp
(template ((typename T))
  (function max ((T a) (T b)) -> T
    (return (?: (> a b) a b))))            ; 其實 ?: 要用 if-expr；見下方備註
```
C-Mera 傳統寫法是直接用 `if` 當運算式位置：
```lisp
(template ((typename T))
  (function maxv ((T a) (T b)) -> T
    (if (> a b) (return a) (return b))))
```

使用：
```lisp
(instantiate maxv (int))      ; 產生 maxv<int>
(maxv 3 5)                    ; 直接呼叫就行，C++ 會型別推導
```

類別 template：
```lisp
(template ((typename T))
  (class Box ()
    (private (decl ((T value))))
    (public
     (constructor ((T v)) :init ((value v)))
     (function get () -> T (return value)))))

(decl ((Box<int> b 42)))       ; 有些情境會需要 (instantiate Box (int)) 先展
```

用 `vector`：
```lisp
(include <vector>)

(decl (((instantiate #:std::vector (int)) v { 1 2 3 4 })))
;; 或 typedef 一下比較乾淨
(typedef (instantiate #:std::vector (int)) IntVec)
(decl ((IntVec v2 { 10 20 30 })))
```

## for-each (range-based for)
```lisp
(for-each ((int x) v)
  (<< #:std::cout x " "))
```
對應 C++ 的 `for (int x : v) { ... }`。

## lambda
```lisp
(decl ((auto f = (lambda ((int x)) -> int (return (* x x))))))
(f 5)  ; 25
```
捕獲清單：`(lambda (capture ((= x))) ((int y)) -> int ...)`（細節看 `tests/cxx.misc.lambda.00.lisp`）。

## try / catch / throw
```lisp
(try
  (progn
    (throw (runtime_error "boom")))
  (catch ((#:std::exception& e))
    (<< #:std::cerr (e.what) #:std::endl)))
```

## cast 家族
```lisp
(static-cast int x)
(dynamic-cast Base* ptr)
(reinterpret-cast void* ptr)
(const-cast char* str)
```

## 初始化清單（花括號）
```lisp
(decl ((IntVec v { 1 2 3 })))
```
**只有** C++ 後端才能用花括號；C 只能用 `(clist ...)`。這是 README 特別強調的區別。

## 看不懂寫法時
直接翻 `tests/cxx.*.lisp`；每個檔案都附預期輸出，最短路徑學某特性就是挑最接近的測試檔當範本。
