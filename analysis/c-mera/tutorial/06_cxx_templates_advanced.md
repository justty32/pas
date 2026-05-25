# 教學 06：Template 進階語法

C-Mera 的 template 不是新發明——它把 C++ 的 template 直接映射成 sexp。記住兩個核心形式：**`template`** 宣告模板、**`instantiate`** 具現化型別或函式。

---

## 一、基本模板（複習）

```lisp
(template ((typename T))
  (function identity ((T x)) -> T
    (return x)))
```

產生：
```cpp
template<typename T>
T identity(T x) { return x; }
```

**模板參數列表語法**：每個參數一組括號，第一個 token 是 `typename`、`class` 或型別（非型別參數）：

```lisp
((typename T))                ; 一個型別參數
((typename T) (typename U))   ; 兩個型別參數
((typename T) (int N))        ; 型別 + 非型別整數參數
((class T) (class Alloc))     ; 用 class 也行，等同 typename
```

---

## 二、多參數、非型別參數

固定大小的陣列容器——示範非型別模板參數 `N`：

```lisp
(include <iostream>)
(using-namespace std)

(template ((typename T) (int N))
  (class Array ()
    (private
     (decl ((T data[N])))
           ((int sz = 0)))
    (public
     (function push ((const T& v)) -> bool
       (if (== sz N) (return false))
       (set data[sz++] v)
       (return true))

     (function get ((int i)) const -> (const T&)
       (return data[i]))

     (function size () const -> int
       (return sz))

     (function fill ((const T& v)) -> void
       (for ((int i = 0) (< i N) ++i)
         (set data[i] v))
       (set sz N)))))

(function main () -> int
  (decl (((instantiate Array (int) (5)) a))   ; Array<int, 5>
    (a.push 10)
    (a.push 20)
    (a.push 30)
    (for ((int i = 0) (< i (a.size)) ++i)
      (<< cout (a.get i) " "))
    (<< cout endl))   ; 10 20 30
  (return 0))
```

**`instantiate` 的每個引數也要一組括號**：`(instantiate Array (int) (5))` — 因為每個模板引數都以型別方式處理，括號標示邊界。

---

## 三、預設模板參數

```lisp
(include <vector>)
(include <memory>)
(using-namespace std)

(template ((typename T)
           (typename Alloc = (instantiate #:std::allocator (T))))
  (class MyVec ()
    (private
     (decl (((instantiate #:std::vector (T) (Alloc)) data))))
    (public
     (function push ((const T& v)) -> void
       (data.push_back v))
     (function size () const -> int
       (return (data.size))))))

(function main () -> int
  (decl (((instantiate MyVec (int)) v))   ; 使用預設 allocator
    (v.push 1) (v.push 2) (v.push 3)
    (<< cout (v.size) endl))   ; 3
  (return 0))
```

若預設值的 `instantiate` 導致展開問題，最穩的 workaround 是先 typedef：

```lisp
(typedef (instantiate #:std::allocator (int)) IntAlloc)
(template ((typename T) (typename A = IntAlloc)) ...)
```

---

## 四、模板特化（完全特化）

C-Mera 沒有專門的特化語法——**直接用 `instantiate-explicit` 拼出帶尖括號的名字，然後定義那個版本**：

```lisp
(include <iostream>)
(using-namespace std)

;; 泛用版
(template ((typename T))
  (function type-name () -> (const char*)
    (return "unknown")))

;; int 特化
(template ()                                ; 空模板參數列表 = 完全特化
  (function (instantiate-explicit (type-name (int))) () -> (const char*)
    (return "int")))

;; float 特化
(template ()
  (function (instantiate-explicit (type-name (float))) () -> (const char*)
    (return "float")))

(function main () -> int
  (<< cout (type-name<int>) endl)     ; int
  (<< cout (type-name<float>) endl)   ; float
  (<< cout (type-name<double>) endl)  ; unknown
  (return 0))
```

產生的 C++：
```cpp
template<typename T> const char* type_name() { return "unknown"; }
template<> const char* type_name<int>() { return "int"; }
template<> const char* type_name<float>() { return "float"; }
```

---

## 五、類別部分特化

```lisp
(include <iostream>)
(using-namespace std)

;; 泛用版
(template ((typename T))
  (class TypeTraits ()
    (public
     (decl ((static const bool is_ptr = false)))
     (decl ((static const bool is_ref = false))))))

;; 指標的部分特化
(template ((typename T))
  (class (instantiate-explicit (TypeTraits (T*))) ()
    (public
     (decl ((static const bool is_ptr = true)))
     (decl ((static const bool is_ref = false))))))

;; 參考的部分特化
(template ((typename T))
  (class (instantiate-explicit (TypeTraits (T&))) ()
    (public
     (decl ((static const bool is_ptr = false)))
     (decl ((static const bool is_ref = true))))))

(function main () -> int
  (<< cout (TypeTraits<int>::is_ptr) " "
           (TypeTraits<int*>::is_ptr) " "
           (TypeTraits<int&>::is_ref) endl)   ; 0 1 1
  (return 0))
```

---

## 六、顯式實例化

```lisp
;; 強制產生特定版本的符號（用於 .cpp / .h 分離時）
(instantiate-explicit (identity (int)))
; => template int identity<int>(int);

(instantiate-explicit (MyVec (double)))
; => template class MyVec<double>;
```

這在「模板定義在 .h，明確實例化在 .cpp」的分離編譯模式中是必要的。

---

## 七、STL 容器的 `instantiate` 慣用法

複雜型別用 `typedef` 簡化，避免到處寫一大串：

```lisp
(include <vector>)
(include <map>)
(include <string>)
(using-namespace std)

;; vector<int>
(typedef (instantiate vector (int)) IVec)

;; map<string, vector<int>>
(typedef (instantiate map (string) (IVec)) StrToIVec)

;; pair<int, string>
(typedef (instantiate pair (int) (string)) IntStr)

(function make-index () -> StrToIVec
  (decl ((StrToIVec result))
    (result["hello"].push_back 1)
    (result["hello"].push_back 2)
    (result["world"].push_back 3)
    (return result)))

(function main () -> int
  (decl ((StrToIVec idx = (make-index)))
    (for ((const auto& kv) idx)
      (<< cout kv.first ": ")
      (for ((int v) kv.second)
        (<< cout v " "))
      (<< cout endl)))
  (return 0))
```

---

## 八、CRTP（Curiously Recurring Template Pattern）

靜態多態——不用虛函式，零開銷：

```lisp
(include <iostream>)
(using-namespace std)

;; CRTP 基類
(template ((typename Derived))
  (class Printable ()
    (public
     (function print () -> void
       (decl ((Derived* self = (static-cast Derived* this)))
         (self->do-print))))))

(class Point ((public (instantiate Printable (Point))))
  (public
   (decl ((int x) (int y)))
   (constructor ((int x) (int y)) :init ((x x) (y y)))
   (function do-print () -> void
     (<< cout "Point(" x ", " y ")" endl))))

(class Circle ((public (instantiate Printable (Circle))))
  (public
   (decl ((double r)))
   (constructor ((double r)) :init ((r r)))
   (function do-print () -> void
     (<< cout "Circle(r=" r ")" endl))))

(function main () -> int
  (decl ((Point p 3 4)
         (Circle c 5.0))
    (p.print)    ; Point(3, 4)
    (c.print))   ; Circle(r=5)
  (return 0))
```

**重點**：`(instantiate Printable (Point))` 在繼承列表裡，產生 `Printable<Point>`。

---

## 九、variadic template（可變參數模板）

這是 C-Mera 最弱的地方——sexp 沒有對應的 `...` 符號。解法是用 `#:|Args...|` 技巧：

```lisp
(include <iostream>)
(include <utility>)
(using-namespace std)

(template ((typename #:|Args...|))
  (function log-all ((#:|Args...| &rest args)) -> void
    ;; 用 fold expression 需要 cpp 嵌入
    (cpp "(void)std::initializer_list<int>{(std::cout << args << ' ', 0)...};")
    (<< cout endl)))

(function main () -> int
  (log-all 1 "hello" 3.14 'x')
  (return 0))
```

`#:|...|` 是「強制保留 `...` 字元的符號名」，因為符號名有 `.`，要用豎線 `|` 框住。

**誠實建議**：若需要大量 variadic template，直接在 `.lisp` 裡用 `cpp "..."` 嵌入完整的 C++ 片段，比勉強用 sexp 更容易維護。

---

## 十、查錯小撇步

1. **先輸出到 stdout 看**：`cm c++ file.lisp`（不加 `-o`）直接印到 terminal，馬上看到展開結果。
2. **用 typedef 拆解複雜型別**：`(instantiate A (B) (C))` 很難讀的時候，先 typedef 再用。
3. **不確定是 C-Mera 問題還是 C++ 問題**：先用 `cpp "..."` 把那段 C++ 原樣寫進去跑通，再慢慢換回 sexp。
4. **模板錯誤訊息很長**：先看最後一行，找「which instantiation」定位問題。

---

## 十一、常見坑

| 坑 | 解法 |
|---|---|
| `(instantiate Foo (int))` 和 `(instantiate Foo (int) (double))` 忘了括號 | 每個模板引數一組括號，不能省 |
| `instantiate-explicit` 和 `instantiate` 搞混 | `instantiate` 是型別表達式（用在宣告裡）；`instantiate-explicit` 是產生「帶 `<>` 函式名」的符號 |
| 特化時忘了寫 `(template ())` | 完全特化的 `template` 要有空的參數列表 |
| variadic template 展開 `...` 語法 | 目前靠 `cpp "..."` 嵌入，這是已知限制 |
