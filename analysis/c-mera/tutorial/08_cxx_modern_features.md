# 教學 08：現代 C++ 特性（C++11/14/17/20）

C++11/14/17/20 的常見特性在 C-Mera 幾乎都能寫；有些有專門語法，有些需要用 `cpp "..."` 橋接。這篇每個特性都給一段可以直接跑的範例。

---

## 特性支援速查表

| C++ 特性 | C-Mera 語法 | 支援度 |
|---|---|---|
| `auto` | `(decl ((auto x = 1)))` | ✓ 完整 |
| `decltype(x)` | `((decltype x) y)` | ✓ 完整 |
| range-based for | `(for ((T x) container) body)` | ✓ 完整 |
| lambda | `(lambda-function ...)` | ✓ 完整 |
| rvalue ref `T&&` | 符號直接寫 `T&&` | ✓ 完整 |
| `std::move` / `std::forward` | `(funcall #:std::move x)` | ✓ 完整 |
| `nullptr` | `nullptr` | ✓ 完整 |
| `override` / `final` | qualifier 位置 | ✓ 完整 |
| `noexcept` | qualifier 位置 | ✓ 完整 |
| `constexpr` | specifier 位置 | ✓ 完整 |
| `enum class` | `(enum class Name ...)` | ✓ 完整 |
| initializer_list `{ }` | 花括號寫法 | ✓ 僅 C++ |
| `static_assert` | `(cpp "static_assert(...)")` | △ 靠 cpp |
| structured binding `auto [a,b]` | `(cpp "auto [a, b] = ...;")` | △ 靠 cpp |
| `if constexpr` | `(cpp "if constexpr ...")` | △ 靠 cpp |
| fold expression | `(cpp "(... + args)")` | △ 靠 cpp |
| concepts (C++20) | `(cpp "requires ...")` | △ 靠 cpp |

---

## 一、override / final

qualifier 放在參數列表後、`->` 前：

```lisp
(include <iostream>)
(using-namespace std)

(class Base ()
  (public
   (function greet ((const char* name)) pure -> void)
   (destructor virtual)))

(class Child ((public Base))
  (public
   (function greet ((const char* name)) override -> void
     (<< cout "Hello from Child, " name endl))))

(class Sealed ((public Base))
  (public
   (function greet ((const char* name)) final -> void
     (<< cout "Sealed: " name endl))))

(function main () -> int
  (decl ((Base* b = (new Child)))
    (b->greet "world")    ; Hello from Child, world
    (delete b))
  (return 0))
```

產生的 C++（片段）：
```cpp
virtual void greet(const char* name) override { ... }
virtual void greet(const char* name) final { ... }
```

---

## 二、constexpr / consteval

`constexpr` 放在 specifier 位置（型別的前面）：

```lisp
(include <iostream>)
(using-namespace std)

;; constexpr 全域常數
(decl ((constexpr int MAX_SIZE = 1024)
       (constexpr double PI = 3.14159265358979)))

;; constexpr 函式
(template ((typename T))
  (function constexpr sq ((T x)) -> T
    (return (* x x))))

;; constexpr class
(class Point ()
  (public
   (decl ((int x) (int y)))
   (constructor constexpr ((int x) (int y)) :init ((x x) (y y)))
   (function constexpr manhattan () const -> int
     (return (+ (if (< x 0) (- x) x)
                (if (< y 0) (- y) y))))))

(function main () -> int
  (decl ((constexpr int a = (sq 7))))          ; 49，編譯期計算
  (decl ((constexpr Point p 3 -4)))
  (<< cout (p.manhattan) endl)   ; 7
  (return 0))
```

---

## 三、enum class

```lisp
(include <iostream>)
(using-namespace std)

;; 基本 enum class
(enum class Color red green blue)
; => enum class Color { red, green, blue };

;; 指定底層型別
(enum class (Status : int) ok error timeout)
; => enum class Status : int { ok, error, timeout };

;; 使用
(function describe ((Color c)) -> (const char*)
  (switch (cast int c)
    (0 (return "red"))
    (1 (return "green"))
    (2 (return "blue"))
    (default (return "unknown"))))

(function main () -> int
  (decl ((Color c = Color::green))
    (<< cout (describe c) endl)   ; green

    ;; 比較
    (if (== c Color::green)
        (<< cout "it's green!" endl)))
  (return 0))
```

`(cast int c)` 可以把 enum class 轉成底層整數。

---

## 四、右值參考與 move 語意

完整的「Rule of Five」實作：

```lisp
(include <iostream>)
(include <cstring>)
(include <utility>)
(using-namespace std)

(class Buffer ()
  (private
   (decl ((char* data))
         ((int n))))

  (public
   ;; 一般建構子
   (constructor ((int size))
     :init ((n size))
     (set data (new char[size]))
     (funcall memset data 0 size)
     (<< cout "Buffer(" size ") created" endl))

   ;; 解構子
   (destructor
     (delete[] data)
     (<< cout "Buffer destroyed" endl))

   ;; 拷貝建構子
   (constructor ((const Buffer& o))
     :init ((n o.n))
     (set data (new char[o.n]))
     (funcall memcpy data o.data o.n)
     (<< cout "Buffer copy" endl))

   ;; 搬移建構子
   (constructor ((Buffer&& o))
     :init ((data o.data) (n o.n))
     (set o.data nullptr o.n 0)
     (<< cout "Buffer move" endl))

   ;; 拷貝賦值
   (function operator= ((const Buffer& o)) -> Buffer&
     (if (!= this &o)
         (progn
           (delete[] data)
           (set n o.n
                data (new char[o.n]))
           (funcall memcpy data o.data o.n)))
     (return *this))

   ;; 搬移賦值
   (function operator= ((Buffer&& o)) -> Buffer&
     (if (!= this &o)
         (progn
           (delete[] data)
           (set data o.data
                n    o.n
                o.data nullptr
                o.n    0)))
     (return *this))

   (function write ((const char* s)) -> void
     (funcall strncpy data s (- n 1))
     (set data[(- n 1)] #\null))

   (function read () const -> (const char*)
     (return data))))

(function make-buffer ((int size)) -> Buffer
  (decl ((Buffer b size))
    (b.write "hello")
    (return (funcall #:std::move b))))    ; 觸發搬移

(function main () -> int
  (decl ((Buffer b1 = (make-buffer 64)))   ; move
    (<< cout (b1.read) endl)               ; hello

    (decl ((Buffer b2 = b1)))              ; copy
      (<< cout (b2.read) endl))            ; hello

  (return 0))
```

---

## 五、initializer_list 建構子

```lisp
(include <initializer_list>)
(include <vector>)
(include <iostream>)
(using-namespace std)

(class IntBag ()
  (private
   (decl (((instantiate vector (int)) data))))
  (public
   ;; initializer_list 建構子
   (constructor (((instantiate #:std::initializer_list (int)) lst))
     (for ((int x) lst)
       (data.push_back x)))

   (function sum () const -> int
     (decl ((int s = 0))
       (for ((int x) data)
         (+= s x))
       (return s)))

   (function size () const -> int
     (return (data.size)))))

(function main () -> int
  (decl ((IntBag bag { 1 2 3 4 5 6 7 8 9 10 }))
    (<< cout "size=" (bag.size) " sum=" (bag.sum) endl))
  ; size=10 sum=55
  (return 0))
```

---

## 六、structured binding（C++17，靠 cpp）

C-Mera 沒有 `auto [a, b] = ...` 的原生語法，用 `cpp` 橋接：

```lisp
(include <tuple>)
(include <string>)
(include <iostream>)
(using-namespace std)

(function get-result () -> (instantiate #:std::tuple (int) (string) (double))
  (return (funcall (instantiate make_tuple (int) (string) (double))
                   42 "ok" 3.14)))

(function main () -> int
  (cpp "auto [code, msg, val] = get_result();")
  (<< cout (cpp "code") " " (cpp "msg") " " (cpp "val") endl)
  ; 42 ok 3.14
  (return 0))
```

若常用，可以包一個 macro：

```lisp
(defmacro bind (vars expr)
  (let ((vars-str (format nil "~{~a~^, ~}" vars)))
    `(cpp ,(format nil "auto [~a] = ~a;" vars-str expr))))

;; 使用
(bind (x y z) (get_result()))
; => auto [x, y, z] = get_result();
```

---

## 七、if constexpr（C++17，靠 cpp）

```lisp
(include <type_traits>)
(include <iostream>)
(using-namespace std)

(template ((typename T))
  (function process ((T x)) -> void
    (cpp "if constexpr (std::is_integral_v<T>) {")
    (<< cout "integer: " x endl)
    (cpp "} else if constexpr (std::is_floating_point_v<T>) {")
    (<< cout "float: " x endl)
    (cpp "} else {")
    (<< cout "other" endl)
    (cpp "}")))

(function main () -> int
  (process 42)      ; integer: 42
  (process 3.14)    ; float: 3.14
  (process "hi")    ; other
  (return 0))
```

想要漂亮的 sexp 版本，自己包一個 macro：

```lisp
(defmacro if-constexpr (cond-str then &optional else)
  (if else
      `(progn
         (cpp ,(format nil "if constexpr (~a) {" cond-str))
         ,then
         (cpp "} else {")
         ,else
         (cpp "}"))
      `(progn
         (cpp ,(format nil "if constexpr (~a) {" cond-str))
         ,then
         (cpp "}"))))

;; 使用
(template ((typename T))
  (function show ((T x)) -> void
    (if-constexpr "std::is_integral_v<T>"
      (<< cout "int: " x endl)
      (<< cout "other: " x endl))))
```

---

## 八、concepts（C++20，靠 cpp）

```lisp
(include <concepts>)
(include <iostream>)
(using-namespace std)

;; 定義 concept（用 cpp）
(cpp "template<typename T> concept Numeric = std::is_arithmetic_v<T>;")

;; 在 template 裡使用 requires
(template ((typename T))
  (function add ((T a) (T b)) -> T
    (cpp "requires Numeric<T>")
    (return (+ a b))))

(function main () -> int
  (<< cout (add 1 2) endl)         ; 3
  (<< cout (add 1.5 2.5) endl)     ; 4
  ; (add "a" "b")  <- 編譯錯誤，string 不是 Numeric
  (return 0))
```

---

## 九、終極技巧：用 Lisp macro 包裝醜陋的 C++ 部分

C-Mera 最強的心法：**sexp 寫起來醜的地方，就用 Lisp macro 產生字串，再交給 cpp**。

範例：`std::variant`（C++17）

```lisp
(defmacro define-variant (name &rest types)
  (let ((type-list (format nil "~{~a~^, ~}" types)))
    `(cpp ,(format nil "using ~a = std::variant<~a>;" name type-list))))

(define-variant Value "int" "double" "#:std::string" "bool")
; => using Value = std::variant<int, double, std::string, bool>;
```

範例：fold expression

```lisp
(defmacro fold-sum (&rest args)
  (let ((args-str (format nil "~{~a~^, ~}" args)))
    `(cpp ,(format nil "(~a)" args-str))))   ; 需要手動補 ... 語法
```

範例：`static_assert`

```lisp
(defmacro static-assert-eq (a b msg)
  `(cpp ,(format nil "static_assert(~a == ~a, \"~a\");" a b msg)))

(static-assert-eq "sizeof(int)" 4 "int must be 4 bytes")
; => static_assert(sizeof(int) == 4, "int must be 4 bytes");
```

---

## 十、調試與建議流程

1. **先用 `cpp "..."` 把目標 C++ 跑通**，不要一開始就想用 sexp 寫。
2. **確認能跑後，把改動部分逐步換回 sexp**。
3. **sexp 太醜就包成 macro**（給自己用，不是對外 API）。
4. **最後驗證**：`cm c++ file.lisp`（不加 `-o`）看輸出的 C++ 是不是預期的。

這個「cpp → sexp → macro」的遞進流程，比「一開始就想用純 sexp 寫完所有現代 C++」輕鬆很多，且幾乎沒有寫不出來的東西。
