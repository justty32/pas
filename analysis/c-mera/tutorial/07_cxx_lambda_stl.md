# 教學 07：Lambda、STL、現代 C++ 常用組合

---

## 一、lambda 完整語法

C-Mera 的 lambda 叫 **`lambda-function`**（不是 `lambda`，那是 Common Lisp 自己的形式）。完整格式：

```
(lambda-function <捕獲列表> <參數列表> [qualifiers...] -> <回傳型別> <body...>)
```

各段都可省略，但**順序固定**，不能調換。

### 最簡：無捕獲、自動推導回傳型別

```lisp
(decl ((auto f = (lambda-function () ((int x))
                    (return (* x x))))))
; C++: auto f = [](int x) { return x * x; };

(f 5)   ; => f(5);
```

### 加明確回傳型別

```lisp
(lambda-function () ((int x)) -> int (return (* x x)))
; [](int x) -> int { return x * x; }
```

### 捕獲語法對照

| C-Mera | C++ | 意思 |
|---|---|---|
| `(lambda-function () ...)` | `[]` | 無捕獲 |
| `(lambda-function (=) ...)` | `[=]` | 全部值捕獲 |
| `(lambda-function (&) ...)` | `[&]` | 全部參考捕獲 |
| `(lambda-function (x) ...)` | `[x]` | 值捕獲 x |
| `(lambda-function (&y) ...)` | `[&y]` | 參考捕獲 y |
| `(lambda-function (= &y) ...)` | `[=, &y]` | 全值捕獲，但 y 用參考 |
| `(lambda-function (x &y) ...)` | `[x, &y]` | 混合 |
| `(lambda-function (this) ...)` | `[this]` | 捕獲 this 指標 |

### mutable（可修改值捕獲的副本）

```lisp
(decl ((int counter = 0))
  (decl ((auto inc = (lambda-function (=) ()
                        mutable -> int
                        (return ++counter)))))
  (inc) (inc) (inc)
  ; counter 仍為 0（值捕獲只改副本）
  (<< cout counter endl))   ; 0
```

`mutable` 放在參數列表後、`->` 前（和 `const`、`override`、`noexcept` 同位置）。

### 立即呼叫（IIFE）

```lisp
(decl ((int result =
         (funcall (lambda-function () () -> int
                    (decl ((int x = 6) (int y = 7))
                      (return (* x y))))))))
; result = 42
```

用 `funcall` 包住 lambda 再加引數。不能直接把 lambda 放第一位，因為 C-Mera 的 reader 會把它當函式名。

### C++14 init-capture（搬移語意）

```lisp
(decl (((instantiate #:std::unique_ptr (Widget)) uptr ((new Widget))))
  (decl ((auto f = (lambda-function ((= owned (funcall #:std::move uptr))) ()
                      -> void
                      (owned->work))))))
; [owned = std::move(uptr)]() { owned->work(); }
```

---

## 二、STL 容器完整範例

```lisp
(include <vector>)
(include <list>)
(include <map>)
(include <unordered_map>)
(include <set>)
(include <string>)
(include <algorithm>)
(include <numeric>)
(include <iostream>)
(using-namespace std)

(function main () -> int
  ;; --- vector ---
  (decl (((instantiate vector (int)) v { 3 1 4 1 5 9 2 6 5 }))
    ;; 排序
    (funcall sort (v.begin) (v.end))

    ;; 去重
    (decl ((auto last = (funcall unique (v.begin) (v.end)))))
    (funcall (oref v erase) last (v.end))

    ;; 印出
    (for ((int x) v)
      (<< cout x " "))
    (<< cout endl)   ; 1 2 3 4 5 6 9

    ;; 總和
    (decl ((int s = (funcall accumulate (v.begin) (v.end) 0))))
    (<< cout "sum=" s endl)   ; sum=30

    ;; 找特定值
    (decl ((auto it = (funcall find (v.begin) (v.end) 5))))
    (if (!= it (v.end))
        (<< cout "found 5" endl)))

  ;; --- map ---
  (decl (((instantiate map (string) (int)) scores))
    (set scores["Alice"] 95
         scores["Bob"]   87
         scores["Carol"] 92)

    ;; 遍歷（自動排序）
    (for ((const auto& kv) scores)
      (<< cout kv.first ": " kv.second endl)))

  ;; --- set ---
  (decl (((instantiate set (int)) s { 5 3 1 4 1 5 9 2 6 }))
    (<< cout "set size=" (s.size) endl)   ; 7（自動去重）
    (<< cout (if (s.count 5) "has 5" "no 5") endl))

  (return 0))
```

**重點：成員函式呼叫的語法**

```lisp
(v.begin)           ; v.begin()   ← 括號外覆是呼叫
v.begin             ; v.begin     ← 沒括號是取成員（不呼叫）
(funcall sort (v.begin) (v.end))   ; sort(v.begin(), v.end())
```

---

## 三、algorithm 常用組合

```lisp
(include <vector>)
(include <algorithm>)
(include <numeric>)
(include <iostream>)
(using-namespace std)

(function demo ((instantiate vector (int)) v) -> void
  ;; 排序（降冪）
  (funcall sort (v.begin) (v.end)
           (lambda-function () ((int a) (int b)) (return (> a b))))

  ;; remove_if + erase
  (funcall (oref v erase)
           (funcall remove_if (v.begin) (v.end)
                    (lambda-function () ((int x)) (return (== 0 (% x 2)))))
           (v.end))

  ;; transform：每個元素乘以 2
  (funcall transform (v.begin) (v.end) (v.begin)
           (lambda-function () ((int x)) (return (* x 2))))

  ;; count_if：計算大於 5 的個數
  (decl ((int cnt = (funcall count_if (v.begin) (v.end)
                             (lambda-function () ((int x)) (return (> x 5))))))
    (<< cout "count > 5: " cnt endl))

  ;; for_each
  (funcall for_each (v.begin) (v.end)
           (lambda-function () ((int x))
             (<< cout x " ")))
  (<< cout endl))

(function main () -> int
  (decl (((instantiate vector (int)) v { 1 2 3 4 5 6 7 8 9 10 }))
    (demo v))
  (return 0))
```

---

## 四、smart pointer

```lisp
(include <memory>)
(include <iostream>)
(using-namespace std)

(class Widget ()
  (public
   (decl ((int id)))
   (constructor ((int id)) :init ((id id))
     (<< cout "Widget " id " created" endl))
   (destructor
     (<< cout "Widget " id " destroyed" endl))
   (function work () -> void
     (<< cout "Widget " id " working" endl))))

(function main () -> int
  ;; unique_ptr（C++14）
  (decl (((instantiate unique_ptr (Widget)) p
            = (funcall (instantiate make_unique (Widget)) 1)))
    (p->work)
    ;; p 在這裡離開 scope，Widget 自動銷毀
    )

  ;; shared_ptr
  (decl (((instantiate shared_ptr (Widget)) a
            = (funcall (instantiate make_shared (Widget)) 2))
         ((instantiate shared_ptr (Widget)) b = a))   ; 共享
    (<< cout "use_count=" (a.use_count) endl)    ; 2
    (a->work))

  (return 0))
```

`make_unique<Widget>` 寫成 `(instantiate make_unique (Widget))`，再用 `funcall` 呼叫。

---

## 五、move / forward

```lisp
(include <utility>)
(include <string>)
(include <iostream>)
(using-namespace std)

;; move
(decl ((string s = "hello"))
  (decl ((string t = (funcall #:std::move s))))
    ; s 現在是空字串，t 是 "hello"
  (<< cout "s=" s " t=" t endl))

;; perfect forward
(template ((typename T))
  (function relay ((T&& x)) -> T&&
    (return (funcall (instantiate #:std::forward (T)) x))))
```

---

## 六、exception / noexcept

```lisp
(function safe-divide ((int a) (int b)) noexcept -> int
  (if (== b 0) (return 0))
  (return (/ a b)))

(function risky ((int x)) -> int
  (if (< x 0)
      (throw (runtime_error "negative")))
  (return x))

;; noexcept 的 qualifier 位置
(function get-value () noexcept -> int (return 42))
(function process () const noexcept -> void ...)
```

---

## 七、Lisp macro × C++ template（組合玩法）

用 C-Mera 最獨特的方式：**macro 產生多個具體的模板容器列印函式**，不用手寫 template。

```lisp
(include <vector>)
(include <list>)
(include <set>)
(include <iostream>)
(using-namespace std)

(defmacro def-print-container (fn-name container-type elem-type)
  `(function ,fn-name ((const ,container-type& c) (const char* label)) -> void
     (<< cout label ": [")
     (for ((const auto& x) c)
       (<< cout x " "))
     (<< cout "]" endl)))

(def-print-container print-ivec  (instantiate vector (int))    int)
(def-print-container print-dlist (instantiate list   (double)) double)
(def-print-container print-sset  (instantiate set    (string)) string)

(function main () -> int
  (decl (((instantiate vector (int))    v { 1 2 3 4 5 })
         ((instantiate list   (double)) l { 1.1 2.2 3.3 })
         ((instantiate set    (string)) s { "c" "a" "b" }))
    (print-ivec  v "ints")
    (print-dlist l "doubles")
    (print-sset  s "strings"))
  (return 0))
```

產生的 C++：
```cpp
void print_ivec(const vector<int>& c, const char* label) {
    cout << label << ": [";
    for (const auto& x : c) cout << x << " ";
    cout << "]" << endl;
}
// ... 另外兩個類似的函式
```

**template 做不到這個**——template 要寫 `template<typename C>` 一個版本；C-Mera 的 macro 在展開期直接產生三個具體函式，各自有明確型別。

---

## 常見坑

| 坑 | 原因 | 解法 |
|---|---|---|
| lambda 用 `lambda` 而非 `lambda-function` | `lambda` 是 Common Lisp 的 macro，會被它攔截 | 一律用 `lambda-function` |
| `(v.begin)` 沒括號 `v.begin` | 前者是呼叫，後者是取成員 | STL algorithm 都要傳呼叫結果，記得加括號 |
| `funcall sort ...` 但參數順序錯 | C-Mera 沒有特殊對待，`funcall` 就是函式呼叫 | 和 C++ 的參數順序完全相同 |
| `(oref v erase)` 很奇怪 | 這是 `v.erase` 的顯式寫法 | `(funcall (oref v erase) iter)` = `v.erase(iter)` |
