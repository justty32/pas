# 教學 08：現代 C++ 特性的 C-Mera 寫法

C++11/14/17/20 常見特性在 C-Mera 都可以寫出來；有些有專門語法，有些需要繞一下。這篇把你會用到的特性都列出來，每個給一段可跑的範例。

## 特性對照總表

| C++ 特性 | C-Mera 語法 | 備註 |
|---|---|---|
| `auto` | `(decl ((auto x = 1)))` | 直接寫 |
| `decltype(x)` | `((decltype x) y)` | 括號內放運算式 |
| range-based for | `(for ((T x) container) body)` | 兩段式 |
| lambda | `(lambda-function ...)` | 見教學 07 |
| rvalue ref `T&&` | 符號裡含 `&&` 直接寫 | `(T&& x)` |
| `std::move` | `(funcall #:std::move x)` | |
| `nullptr` | `nullptr` | 當一般符號 |
| `override` / `final` | qualifier 位置 | 見下方 |
| `noexcept` | qualifier 位置 | `function foo () noexcept -> int` |
| `constexpr` | specifier | `(decl ((constexpr int x = 1)))` |
| `static_assert` | `(cpp "static_assert(...)")` 或自製 macro | 沒專屬 |
| `enum class` | `(enum class Name ...)` | |
| range init list | `{ ... }` 寫法 | 僅 C++ |
| structured binding | `(cpp "auto [a, b] = ...;")` | 目前沒專用 |
| initializer_list | 花括號 `{ ... }` | 自動 |
| `this` | 寫 `this` | 當變數 |
| uniform init | `(Name arg1 arg2)` 或 `(Name { ... })` | |
| variadic template | `#:|Args...|` 符號技巧 | 醜 |
| fold expression | `(cpp "(... + args)")` | 目前沒專用 |
| concepts (C++20) | `(cpp "requires ...")` | 目前沒專用 |

## 一、override / final

當 qualifier 寫（和 `virtual`、`pure`、`const` 同位置）：
```lisp
(class Base ()
  (public
   (function greet () pure -> void)))

(class Derived ((public Base))
  (public
   (function greet () override -> void            ; override
     (<< #:std::cout "hi" #:std::endl))))

(class Sealed ((public Base))
  (public
   (function greet () final -> void               ; final
     (<< #:std::cout "done" #:std::endl))))
```

## 二、constexpr / constinit

```lisp
(decl ((constexpr int MAX = 1024))
      ((constexpr double PI = 3.14159)))

(template ((typename T))
  (function constexpr sq ((T x)) -> T            ; constexpr 寫在 specifier
    (return (* x x))))
```
C-Mera 的 specifier 是 vararg，所以 `(constexpr inline static int ...)` 都可以。

## 三、enum class

```lisp
(enum class Color red green blue)                ; 基本型
(enum class (Priority : int) low medium high)    ; 指定底層型別

;; 使用
(decl ((Color c = Color::red)))
(if (== c Color::green) ...)
```
指定底層型別的寫法需要用括號包住整個 `(Name : type)`；C-Mera 會把冒號當成識別字字元。若不工作，fallback：`(cpp "enum class Priority : int { ... };")`。

## 四、右值參考、move 語意

```lisp
(include <utility>)
(include <string>)
(using-namespace std)

(class Buffer ()
  (private (decl ((char* data)) ((int n)))))
  (public
   (constructor ((int n)) :init ((n n)) (set data (new char[n])))

   ;; 拷貝建構子
   (constructor ((const Buffer& o))
     :init ((n o.n))
     (set data (new char[o.n]))
     (funcall memcpy data o.data o.n))

   ;; 搬移建構子
   (constructor ((Buffer&& o))
     :init ((data o.data) (n o.n))
     (set o.data nullptr o.n 0))

   ;; 搬移賦值
   (function operator= ((Buffer&& o)) -> Buffer&
     (if (!= this &o)
         (progn
           (delete[] data)
           (set data o.data n o.n
                o.data nullptr o.n 0)))
     (return *this))

   (destructor (delete[] data)))
```

## 五、initializer_list 建構子

```lisp
(include <initializer_list>)

(class IntSet ()
  (public
   (constructor (((instantiate #:std::initializer_list (int)) lst))
     (for ((int x) lst)
       (funcall this->insert x)))))

(decl ((IntSet s { 1 2 3 4 5 })))
```

## 六、structured binding（C++17）

沒專屬語法，直接用 `cpp`：
```lisp
(include <tuple>)
(include <string>)

(function info () -> (instantiate #:std::tuple (int) (#:std::string))
  (return (funcall (instantiate make_tuple (int) (#:std::string)) 42 "ok")))

(function main () -> int
  (cpp "auto [code, msg] = info();")
  (<< #:std::cout (cpp "code") ":" (cpp "msg") #:std::endl)
  (return 0))
```
可讀性不佳——這是 sexp 先天限制之一。若頻繁使用，寫 macro 包：
```lisp
(defmacro bind2 (a b expr)
  `(cpp ,(format nil "auto [~a, ~a] = <expr>;" a b)))
```

## 七、if constexpr（C++17）

```lisp
(template ((typename T))
  (function process ((T x)) -> void
    (cpp "if constexpr (std::is_integral<T>::value) {")
    (<< #:std::cout "int: " x #:std::endl)
    (cpp "} else {")
    (<< #:std::cout "other: " x #:std::endl)
    (cpp "}")))
```
目前 C-Mera 沒有 `if-constexpr` 專門巨集，用 `cpp "..."` 嵌。要漂亮：自己寫一個 macro 把 `(if-constexpr cond then else)` 展開為上述字串。

## 八、concept / requires（C++20）

```lisp
(cpp "template<typename T> concept Numeric = std::is_arithmetic_v<T>;")

(template ((typename T))
  (function add ((T a) (T b)) -> T
    (cpp "requires Numeric<T>")
    (return (+ a b))))
```
同樣是 `cpp` 嵌碼。要純 sexp 寫法目前沒有。

## 九、Lambda 捕獲進階

```lisp
;; C++14 init-capture (move)
(decl ((auto f = (lambda-function ((= ptr (funcall #:std::move uptr))) () 
                    -> void
                    (ptr->work)))))
```
對應 `[ptr = std::move(uptr)]() { ptr->work(); }`。捕獲列表的元素 `(= ptr (move uptr))` 會被 C-Mera 的 `make-declaration-node` 當成初始化宣告處理。

## 十、模板實務：policy-based design

```lisp
(template ((typename T) (typename Policy))
  (class Container ()
    (private
     (decl ((Policy policy))))
    (public
     (function add ((const T& x)) -> void
       (funcall policy.check x)
       ...))))

(class StrictPolicy ()
  (public
   (template ((typename T))
     (function check ((const T& x)) -> void
       (if (funcall x.invalid) (throw (runtime_error "bad")))))))

(typedef (instantiate Container (int) (StrictPolicy)) SafeIntBag)
```

## 十一、終極技巧：用 Lisp 把 C++ 醜陋部分包掉

如果某段 C++ 在 C-Mera 裡寫得很醜（例如 variadic template、fold expression、complex SFINAE），**寫 Lisp 巨集產生整段字串**再交給 `cpp`：

```lisp
(defmacro define-variant (name &rest types)
  (let ((type-list (format nil "~{~a~^, ~}" types)))
    `(cpp ,(format nil "using ~a = std::variant<~a>;" name type-list))))

(define-variant Value int double "std::string" bool)
;; => using Value = std::variant<int, double, std::string, bool>;
```

這個心法可以總結成一句話：**C-Mera 的 sexp 不是要打贏 C++ 的語法，而是要讓你在外面套一層 Lisp 去控制 C++ 程式碼的生成**。sexp 醜的地方就用 macro 包，macro 不方便就用 `cpp` 原樣嵌；兩把工具合起來幾乎沒有寫不出來的東西。

## 十二、調試與建議流程

1. 先用 `cpp "..."` 把你要的 C++ 原封不動丟進去跑通。
2. 跑通後，把變動部分逐步改回 sexp / template。
3. 覺得 sexp 寫太醜，退一步用 `defmacro` 把它包起來（給自己用，不是給別人看）。
4. 最後檢查 `cm c++ file.lisp`（不加 `-o`）的輸出 C++ 是不是你預期的樣子。

這樣的流程比「一開始就想用 sexp 寫完」輕鬆很多，而且保留所有現代 C++ 特性的可能性。
