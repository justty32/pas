# 教學 07：Lambda、STL、現代 C++ 常用組合

## 一、lambda 完整語法

C-Mera 的 lambda 叫 `lambda-function`（注意不是 `lambda`，`lambda` 是 Common Lisp 自己的）。一般格式：

```
(lambda-function <capture> <parameters> [qualifiers...] -> <return-type> <body>)
```

各段都可省略（但順序固定）。看完整範例（改寫自 `tests/cxx.misc.lambda.00.lisp`）：

### 1. 最簡：無捕獲、無回傳型別
```lisp
(decl ((auto f = (lambda-function () ((int x)) (return (* x x))))))
(f 5)        ; 25
```
對應 `[](int x) { return x * x; }`。

### 2. 加回傳型別
```lisp
(lambda-function () ((int x)) -> int (return (* x x)))
```

### 3. 值捕獲 `=`、參考捕獲 `&`、混合
```lisp
(lambda-function (=)      ((int n)) (return (+ x n)))    ; [=](int n) { ... }
(lambda-function (&)      ((int n)) (return (+ x n)))    ; [&]
(lambda-function (= &y)   ((int n)) (return (+ x y n)))  ; [=, &y]
(lambda-function (x &y)   ((int n)) ...)                  ; [x, &y]
(lambda-function (this)   ()       (return this->value)) ; [this]
```

### 4. 有修飾符 mutable
```lisp
(lambda-function (=) ((const int& a) (const int& b))
   mutable                                   ; qualifier 位置
   -> int
   (progn ++x (return (+ a b))))
```
對應 `[=](const int& a, const int& b) mutable -> int { ... }`。

### 5. 立即呼叫 IIFE
```lisp
(decl ((int result = (funcall (lambda-function () () -> int (return 42))))))
```
`funcall` 是 C-Mera 的「函式物件呼叫」工具；可讀性好過把 lambda 直接放第一個位置（reader 會想當函式名）。

## 二、STL 容器速覽

以下全部需要 `(using-namespace std)` 或用 `#:std::...`。

```lisp
(include <vector>)
(include <list>)
(include <map>)
(include <unordered_map>)
(include <set>)
(include <string>)
(include <algorithm>)
(include <numeric>)

;; vector
(decl (((instantiate vector (int)) v { 3 1 4 1 5 9 2 6 })))

;; iterator
(for ((auto it = (v.begin)) (!= it (v.end)) ++it)
  (<< cout *it " "))

;; range-based for
(for ((auto& x) v)
  (<< cout x " "))

;; sort
(funcall sort (v.begin) (v.end))

;; sort 帶 lambda
(funcall sort (v.begin) (v.end)
         (lambda-function () ((int a) (int b)) (return (> a b))))

;; accumulate
(decl ((int s = (funcall accumulate (v.begin) (v.end) 0))))

;; find
(decl ((auto it = (funcall find (v.begin) (v.end) 5))))
(if (!= it (v.end))
    (<< cout "found" endl))

;; map
(decl (((instantiate map (string) (int)) m)))
(set m["apple"] 1
     m["pear"]  2)
(for ((const auto& kv) m)
  (<< cout kv.first ":" kv.second endl))
```

小坑：成員函式呼叫想寫得像 C++ 一點，就用 reader 的 dot：`v.begin()` 要寫 `(v.begin)`（括號外覆）；一般不能省括號，因為 `v.begin` 單獨是「取成員」而非「呼叫」。

## 三、range-based for（再強調）

`(for ((型別 名稱) 容器) body)` 兩段式（沒有 test / step）就是 C++11 的 `for (auto x : v)`：
```lisp
(for ((const auto& item) v)
  (<< cout item endl))
```

## 四、smart pointer

```lisp
(include <memory>)
(using-namespace std)

(decl (((instantiate unique_ptr (Foo)) p = (funcall make_unique<Foo> 42))))
;; 或 C++14 以前：
(decl (((instantiate unique_ptr (Foo)) p ((new (Foo 42))))))   ; 花括號版

;; shared
(decl (((instantiate shared_ptr (Foo)) sp = (funcall make_shared<Foo> 1 2 3))))
```

`make_unique<Foo>` 這種「帶模板參數的符號」可以寫 `#:make_unique<Foo>` 直接當一個字面符號，或乾脆用 `(instantiate make_unique (Foo))` 再 `funcall`。

## 五、move / forward / 右值參考

右值參考 `&&` C-Mera 沒有專用符號；直接寫成符號：
```lisp
(function take ((Foo&& f)) -> void       ; Foo&& f
  ...)

(decl ((Foo f))
  (take (funcall #:std::move f)))        ; std::move(f)
```

完美轉發：
```lisp
(template ((typename T))
  (function wrap ((T&& x)) -> void
    (funcall inner (funcall (instantiate #:std::forward (T)) x))))
```

## 六、exception / noexcept

```lisp
(function maybe-throw () -> int
  (throw (runtime_error "oops"))
  (return 0))

;; noexcept qualifier 寫在 qualifier 位置
(function safe () noexcept -> int
  (return 0))
```

try-catch 在 C-Mera 叫 `catching`（`tests/cxx.misc.trycatch.00.lisp`）：
```lisp
(catching (((int i)
            (<< cout "caught int: " i endl))
           ((runtime_error &e)
            (<< cout "runtime: " (e.what) endl))
           ((exception &e)
            (<< cout "base: " (e.what) endl))
           (t                                  ; catch (...)
            (<< cout "???" endl)))
  (throw (runtime_error "bad")))
```
語法：`(catching (clauses...) body)`，每個 clause 是 `(參數宣告 body...)`；`t` 代表 `catch(...)`。

## 七、auto 與 decltype

`auto` 就寫 `auto`：
```lisp
(decl ((auto x = 42))
      ((auto& r = v)))
```

`decltype` 當型別用：
```lisp
(decl (((decltype x) y = x)))
```
在函式回傳位置也能用（C++14 `decltype(auto)` 同理）：
```lisp
(function get-ref () -> (decltype (cpp "(v[0])"))
  (return v[0]))
```
`decltype` 的內容要完整的表達式時，最乾淨的做法是用 `cpp "..."` 嵌。

## 八、STL + lambda 綜合

經典「排序 + 去重 + 取奇數」：
```lisp
(include <vector>)
(include <algorithm>)
(using-namespace std)

(function clean ((vector<int>& v)) -> void
  (funcall sort   (v.begin) (v.end))
  (decl ((auto last = (funcall unique (v.begin) (v.end)))))
  (funcall (oref v erase) last (v.end))
  (funcall (oref v erase)
           (funcall remove_if (v.begin) (v.end)
                    (lambda-function () ((int x)) (return (== 0 (% x 2)))))
           (v.end)))
```

## 九、Lisp macro ✕ C++ template（真正的玩法）

假設你要為多種 container 產生 `print_container`：
```lisp
(defmacro def-print (name container-type)
  `(function ,name ((const ,container-type& c)) -> void
     (<< #:std::cout "[ ")
     (for ((const auto& x) c)
       (<< #:std::cout x " "))
     (<< #:std::cout "]" #:std::endl)))

(def-print print-vec (instantiate vector (int)))
(def-print print-list (instantiate list (double)))
(def-print print-set (instantiate set (string)))
```
**這是 template 都做不到的**——template 要寫 `template<typename C>`，C-Mera 的 `defmacro` 是在展開期直接產生具體類別。兩者可混用：macro 產生 template 函式，template 處理多型。

下一篇會專門講 macro 和 template 合體的技巧。
