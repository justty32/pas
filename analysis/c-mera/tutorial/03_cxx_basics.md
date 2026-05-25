# 教學 03：C++ 基礎（namespace、class、template、lambda、異常）

用 `cm c++ file.lisp -o file.cpp` 或 `cm cxx file.lisp -o file.cpp`。C++ 後端繼承 C 後端，前兩篇的寫法全部適用，這篇只介紹 C++ 多出來的部分。

---

## 一、namespace

### 自定義 namespace

```lisp
(namespace math
  (function square ((int x)) -> int
    (return (* x x)))
  (function cube ((int x)) -> int
    (return (* x x x))))
```

產生：
```cpp
namespace math {
    int square(int x) { return x * x; }
    int cube(int x) { return x * x * x; }
}
```

呼叫時用 `#:math::square`（`#:` 前綴讓 reader 原樣保留冒號）：

```lisp
(function main () -> int
  (<< #:std::cout (#:math::square 5) #:std::endl)
  (return 0))
```

### using-namespace

```lisp
(using-namespace std)     ; => using namespace std;

(function main () -> int
  (<< cout "hello" endl)  ; 不需要 #:std:: 前綴了
  (return 0))
```

**建議**：在教學 / 小程式用 `(using-namespace std)` 省事；在大型專案或 header 裡，保留 `#:std::` 前綴避免命名空間污染。

### `#:` 前綴的含義

`#:symbol` 是 Common Lisp 的「uninterned symbol」——C-Mera 把它的名字原樣輸出為 C++ 識別字，不做任何大小寫轉換或 `-` → `_` 的處理。

| C-Mera 寫法 | 輸出 |
|---|---|
| `std::cout` | `STD::COUT`（Lisp 把名字轉大寫了） |
| `#:std::cout` | `std::cout`（原樣保留） |
| `#:std::vector<int>` | `std::vector<int>` |
| `MAX_LEN` | `max_len`（被轉小寫） |
| `#:MAX_LEN` | `MAX_LEN` |

規則：**只要遇到 namespace、模板實例化語法（`::`、`<>`），幾乎都要用 `#:`**。

---

## 二、基本 class

完整的計數器範例（含建構子、解構子、成員函式）：

```lisp
(include <iostream>)
(using-namespace std)

(class Counter ()           ; () 是繼承列表，空代表無父類
  (private
   (decl ((int n))))
  (public
   (constructor () :init ((n 0))
     (<< cout "Counter() created" endl))
   (constructor ((int start)) :init ((n start))
     (<< cout "Counter(" start ") created" endl))
   (destructor
     (<< cout "Counter destroyed, n=" n endl))

   (function inc () -> void  ++n)
   (function dec () -> void  --n)
   (function value () const -> int  (return n))
   (function reset () -> void  (set n 0))))

(function main () -> int
  (decl ((Counter a))
    (a.inc) (a.inc) (a.inc)
    (<< cout "a=" (a.value) endl))    ; a=3

  (decl ((Counter b 10))
    (b.dec)
    (<< cout "b=" (b.value) endl))    ; b=9

  (return 0))
```

產生：
```cpp
class Counter {
private:
    int n;
public:
    Counter() : n(0) { std::cout << "Counter() created" << std::endl; }
    Counter(int start) : n(start) { std::cout << "Counter(" << start << ") created" << std::endl; }
    ~Counter() { std::cout << "Counter destroyed, n=" << n << std::endl; }
    void inc() { ++n; }
    void dec() { --n; }
    int value() const { return n; }
    void reset() { n = 0; }
};
```

```bash
cm c++ counter.lisp -o counter.cpp && g++ -std=c++11 counter.cpp -o counter && ./counter
# Counter() created
# Counter(10) created
# a=3
# b=9
# Counter destroyed, n=9
# Counter destroyed, n=3
```

---

## 三、繼承

```lisp
(include <iostream>)
(using-namespace std)

(class Animal ()
  (public
   (constructor ((const char* name)) :init ((name name)))
   (function speak () virtual -> void
     (<< cout name " says ..." endl))
   (destructor virtual)
  (protected
   (decl ((const char* name)))))

(class Dog ((public Animal))
  (public
   (constructor ((const char* name)) :init ((Animal name)))
   (function speak () override -> void
     (<< cout name " says Woof!" endl))))

(class Cat ((public Animal))
  (public
   (constructor ((const char* name)) :init ((Animal name)))
   (function speak () override -> void
     (<< cout name " says Meow!" endl))))

(function make-speak ((Animal& a)) -> void
  (a.speak))

(function main () -> int
  (decl ((Dog d "Rex")
         (Cat c "Whiskers"))
    (make-speak d)       ; Rex says Woof!
    (make-speak c))      ; Whiskers says Meow!
  (return 0))
```

**重點**：
- 繼承列表：`(class Dog ((public Animal)))` — 每個父類用括號包，指定存取等級。
- 父類建構子初始化：`:init ((Animal name))` — 括號裡是父類名加參數。
- `virtual` qualifier 放在 `->` 前：`(function speak () virtual -> void)`。
- `override` 同位置：`(function speak () override -> void)`。

---

## 四、new / delete

```lisp
(include <iostream>)
(using-namespace std)

(function main () -> int
  ;; 單個物件
  (decl ((Counter* p = (new (Counter 5))))
    (<< cout (p->value) endl)   ; 5
    (delete p))

  ;; 陣列
  (decl ((int* arr = (new int[10])))
    (for ((int i = 0) (< i 10) ++i)
      (set arr[i] (* i i)))
    (<< cout arr[7] endl)       ; 49
    (delete[] arr))

  (return 0))
```

---

## 五、基本 template 函式

```lisp
(include <iostream>)
(using-namespace std)

(template ((typename T))
  (function max-val ((T a) (T b)) -> T
    (if (> a b) (return a) (return b))))

(function main () -> int
  (<< cout (max-val 3 7) endl)           ; 7
  (<< cout (max-val 3.14 2.71) endl)     ; 3.14
  (<< cout (max-val 'z' 'a') endl)       ; z
  (return 0))
```

產生：
```cpp
template<typename T>
T max_val(T a, T b) {
    if (a > b) return a;
    return b;
}
```

`instantiate` 用於**明確具現化**（通常不需要，讓編譯器自動推導即可）：

```lisp
(instantiate max-val (int))
; => template int max_val<int>(int, int);
```

---

## 六、range-based for

兩段式 `for`：`(for ((型別 名稱) 容器) body)`，對應 C++11 的 `for (auto x : v)`。

```lisp
(include <vector>)
(include <iostream>)
(using-namespace std)

(function main () -> int
  (decl (((instantiate vector (int)) v { 1 2 3 4 5 }))
    ;; 值複製
    (for ((int x) v)
      (<< cout x " "))
    (<< cout endl)

    ;; const 參考（大型物件用這個）
    (for ((const auto& x) v)
      (<< cout x " "))
    (<< cout endl))
  (return 0))
```

---

## 七、lambda

C-Mera 的 lambda 叫 `lambda-function`（不是 `lambda`，那是 Common Lisp 本身的）：

```lisp
(include <iostream>)
(include <vector>)
(include <algorithm>)
(using-namespace std)

(function main () -> int
  (decl (((instantiate vector (int)) v { 5 3 1 4 2 }))
    ;; 最簡 lambda：無捕獲、自動推導回傳型別
    (funcall sort (v.begin) (v.end)
             (lambda-function () ((int a) (int b))
               (return (< a b))))

    ;; 捕獲變數（值捕獲 =）
    (decl ((int threshold = 3))
      (funcall #:std::remove_if (v.begin) (v.end)
               (lambda-function (threshold) ((int x))
                 (return (< x threshold)))))

    (for ((int x) v)
      (<< cout x " "))
    (<< cout endl))
  (return 0))
```

捕獲語法對照：

| C-Mera | C++ |
|---|---|
| `(lambda-function () ...)` | `[]` 無捕獲 |
| `(lambda-function (=) ...)` | `[=]` 全部值捕獲 |
| `(lambda-function (&) ...)` | `[&]` 全部參考捕獲 |
| `(lambda-function (x &y) ...)` | `[x, &y]` 混合 |
| `(lambda-function (this) ...)` | `[this]` |

---

## 八、try / catch

C-Mera 的 try/catch 語法叫 `catching`（來源：`tests/cxx.misc.trycatch.00.lisp`）：

```lisp
(include <iostream>)
(include <stdexcept>)
(using-namespace std)

(function risky ((int x)) -> int
  (when (< x 0)
    (throw (invalid_argument "negative")))
  (when (> x 100)
    (throw (overflow_error "too big")))
  (return (* x x)))

(function main () -> int
  (catching
    (((invalid_argument& e)
      (<< cerr "invalid: " (e.what) endl))
     ((overflow_error& e)
      (<< cerr "overflow: " (e.what) endl))
     (t                           ; catch (...)
      (<< cerr "unknown error" endl)))

    ;; try body
    (<< cout (risky 5) endl)      ; 25
    (<< cout (risky -1) endl)     ; 丟出例外
    (<< cout (risky 200) endl))   ; 丟出例外

  (return 0))
```

產生的 C++（核心部分）：
```cpp
try {
    std::cout << risky(5) << std::endl;
    std::cout << risky(-1) << std::endl;
    std::cout << risky(200) << std::endl;
} catch (invalid_argument& e) {
    std::cerr << "invalid: " << e.what() << std::endl;
} catch (overflow_error& e) {
    std::cerr << "overflow: " << e.what() << std::endl;
} catch (...) {
    std::cerr << "unknown error" << std::endl;
}
```

**語法**：`(catching (clauses...) body...)`，每個 clause 是 `((型別& 名稱) body...)`，`t` 是 `catch(...)`。注意和一般的 `try { ... } catch { ... }` 順序相反——body 在後面。

---

## 九、cast 家族

```lisp
(static-cast int x)                   ; => (int)x（static cast）
(static-cast (double) i)              ; => (double)i
(dynamic-cast #:Base* ptr)            ; => dynamic_cast<Base*>(ptr)
(reinterpret-cast void* ptr)          ; => reinterpret_cast<void*>(ptr)
(const-cast char* str)                ; => const_cast<char*>(str)
```

---

## 十、常見坑

| 坑 | 原因 | 解法 |
|---|---|---|
| `cout` 寫了但沒輸出 | 沒有 `(using-namespace std)` 也沒寫 `#:std::cout` | 加 `(using-namespace std)` 或改用 `#:std::cout` |
| `#:std::vector<int>` 輸出的 `<` 被誤解 | 要用 `instantiate` 才能做模板具現化 | 用 `(instantiate vector (int))` |
| `(function f () -> void ...)` 裡多行沒 `progn` | 函式 body 自動包成 `{}`，所以**函式 body 不需要 `progn`** | 直接寫多行敘述即可；但 `if` 的 body 還是需要 `progn` |
| `new (MyClass arg)` 語法 | `(new (MyClass arg))` 是 C-Mera 的 placement/constructor 語法 | `(new (MyClass arg1 arg2))` 等同 `new MyClass(arg1, arg2)` |
| lambda 用了 `lambda` 而非 `lambda-function` | `lambda` 是 Common Lisp 的 macro | C-Mera 裡改用 `lambda-function` |

---

下一篇（04）：Lisp 巨集——C-Mera 真正的殺手功能。
