# 教學 05：C++ 類別深入（virtual、operator、nested、static、friend）

`03_cxx_basics.md` 只示範了皮毛。C-Mera 的 class 幾乎支援你在 C++ 裡會寫的一切，這篇把能玩的全部攤出來，每個都附可以直接跑的範例和產出的 C++。

---

## 一、virtual / pure virtual（抽象類別）

在 C-Mera 裡，**`virtual` 不是寫在最前面的關鍵字，而是放在 `->` 旁邊的 qualifier**，有兩種等價寫法：

```lisp
(function area () virtual -> double)      ; 寫法 A
(function area () -> (virtual double))    ; 寫法 B（比較少見）
```

`pure` = `= 0`，同位置：

```lisp
(function area () pure -> double)
```

完整抽象類別範例：

```lisp
(include <iostream>)
(using-namespace std)

(class Shape ()
  (public
   (function area () pure -> double)
   (function name () pure -> (const char*)
   (destructor virtual)))    ; 虛擬解構子是良好習慣

(class Circle ((public Shape))
  (private
   (decl ((double r))))
  (public
   (constructor ((double radius)) :init ((r radius)))
   (function area () override -> double
     (return (* 3.14159 r r)))
   (function name () override -> (const char*)
     (return "Circle"))
   (destructor
     (<< cout "~Circle(" r ")" endl))))

(class Rect ((public Shape))
  (private
   (decl ((double w) (double h))))
  (public
   (constructor ((double w) (double h)) :init ((w w) (h h)))
   (function area () override -> double
     (return (* w h)))
   (function name () override -> (const char*)
     (return "Rect"))
   (destructor
     (<< cout "~Rect(" (* w h) ")" endl))))

(function main () -> int
  (decl ((Shape* shapes[2] { (new (Circle 3.0)) (new (Rect 2.0 5.0)) }))
    (for ((int i = 0) (< i 2) ++i)
      (<< cout (shapes[i]->name) " area=" (shapes[i]->area) endl)
      (delete shapes[i])))
  (return 0))
```

產生的 C++（摘要）：
```cpp
class Shape {
public:
    virtual double area() = 0;
    virtual const char* name() = 0;
    virtual ~Shape();
};

class Circle : public Shape {
private:
    double r;
public:
    Circle(double radius) : r(radius) {}
    double area() override { return 3.14159 * r * r; }
    const char* name() override { return "Circle"; }
    ~Circle() { std::cout << "~Circle(" << r << ")" << std::endl; }
};
```

```bash
cm c++ shapes.lisp -o shapes.cpp && g++ -std=c++11 shapes.cpp -o shapes && ./shapes
# Circle area=28.2743
# Rect area=10
# ~Rect(10)
# ~Circle(3)
```

---

## 二、operator overloading

把運算子當函式名寫。在 class 內部定義成員版本，在外部定義自由函式版本：

```lisp
(include <iostream>)
(using-namespace std)

(class Vec3 ()
  (public
   (decl ((double x) (double y) (double z)))

   (constructor ((double x) (double y) (double z)) :init ((x x) (y y) (z z)))

   ;; 成員：Vec3 + Vec3
   (function operator+ ((const Vec3& o)) -> Vec3
     (return (Vec3 (+ x o.x) (+ y o.y) (+ z o.z))))

   ;; 成員：Vec3 * scalar
   (function operator* ((double s)) -> Vec3
     (return (Vec3 (* x s) (* y s) (* z s))))

   ;; 成員：下標存取
   (function operator[] ((int i)) -> double&
     (switch i
       (0 (return x))
       (1 (return y))
       (2 (return z))
       (default (throw (out_of_range "index out of range")))))

   ;; 成員：const 版本下標（回傳 const ref）
   (function operator[] ((int i)) const -> (const double&)
     (switch i
       (0 (return x))
       (1 (return y))
       (2 (return z))
       (default (throw (out_of_range "index out of range")))))

   ;; 成員：相等比較
   (function operator== ((const Vec3& o)) -> bool
     (return (and (== x o.x) (== y o.y) (== z o.z))))))

;; 自由函式：scalar * Vec3（讓 3.0 * v 也能用）
(function operator* ((double s) (const Vec3& v)) -> Vec3
  (return (Vec3 (* v.x s) (* v.y s) (* v.z s))))

;; 自由函式：輸出運算子
(function operator<< ((ostream& os) (const Vec3& v)) -> ostream&
  (<< os "(" v.x ", " v.y ", " v.z ")")
  (return os))

(function main () -> int
  (decl ((Vec3 a (1.0 2.0 3.0))
         (Vec3 b (4.0 5.0 6.0)))
    (<< cout (+ a b) endl)           ; (5, 7, 9)
    (<< cout (* a 2.0) endl)         ; (2, 4, 6)
    (<< cout (* 3.0 b) endl)         ; (12, 15, 18)
    (<< cout a[0] " " a[1] endl))    ; 1 2
  (return 0))
```

**重點**：
- `operator+`、`operator*`、`operator<<` 就是字面函式名，C-Mera 直接輸出。
- `const` qualifier 和回傳型別的 `const ref` 都可以寫（見 `(const double&)` 的括號必要性）。

---

## 三、成員初始化列表的幾種形式

```lisp
(constructor ((int x_) (int y_) (vector<int>& data_))
  :init ((x x_)               ; 普通初始化
         (y y_)
         (buf 10 0)            ; 以 (10, 0) 呼叫 buf 的建構子
         (tags { "a" "b" })    ; C++11 花括號初始化
         (data (move data_)))) ; std::move 搬移
```

產生：
```cpp
Constructor(int x_, int y_, vector<int>& data_)
    : x(x_), y(y_), buf(10, 0), tags({"a", "b"}), data(std::move(data_)) {}
```

---

## 四、Nested class（類別內嵌）

在 class 內直接再寫一個 struct 或 class：

```lisp
(include <iostream>)
(using-namespace std)

(class LinkedList ()
  (public
   ;; 巢狀結構（內部節點）
   (struct Node
     (decl ((int value))
           ((Node* next = nullptr))))

   (constructor () :init ((head nullptr) (size 0)))
   (destructor
     (decl ((Node* cur = head))
       (while cur
         (decl ((Node* nxt = cur->next))
           (delete cur)
           (set cur nxt)))))

   (function push ((int v)) -> void
     (decl ((Node* n = (new Node)))
       (set n->value v
            n->next  head
            head     n)
       ++size))

   (function pop () -> int
     (when (not head) (throw (runtime_error "empty")))
     (decl ((int v = head->value)
            (Node* old = head))
       (set head head->next)
       (delete old)
       --size
       (return v)))

   (function print () -> void
     (for ((Node* p = head) p (set p p->next))
       (<< cout p->value " "))
     (<< cout endl))

  (private
   (decl ((Node* head))
         ((int size)))))

(function main () -> int
  (decl ((LinkedList lst))
    (lst.push 1)
    (lst.push 2)
    (lst.push 3)
    (lst.print)           ; 3 2 1
    (<< cout (lst.pop) endl))  ; 3
  (return 0))
```

存取巢狀型別：`#:LinkedList::Node`（在 C-Mera 外部引用時）。

---

## 五、static 成員

C-Mera 不為 `static` 另設語法，直接把它放進 specifier（型別宣告的前綴）：

```lisp
(include <iostream>)
(using-namespace std)

(class Counter ()
  (private
   (decl ((static int total = 0))))   ; static 在 specifier 位置

  (public
   (constructor ()
     ++total)
   (destructor
     --total)
   (function id () -> int
     (return total))

   (function static count () -> int   ; static 成員函式
     (return total))))

;; 在 class 外定義 static 資料成員（必要）
(decl ((int Counter::total = 0)))

(function main () -> int
  (decl ((Counter a)
         (Counter b)
         (Counter c))
    (<< cout "total=" (Counter::count) endl))   ; total=3
  (return 0))
```

---

## 六、const 成員函式

`const` qualifier 放在參數列表之後、`->` 之前（和 `virtual`/`override` 同位置）：

```lisp
(class Box ()
  (private
   (decl ((int w) (int h))))
  (public
   (constructor ((int w) (int h)) :init ((w w) (h h)))

   ;; const 成員函式：不修改 this
   (function area () const -> int
     (return (* w h)))

   ;; non-const 成員函式：可以修改
   (function scale ((int factor)) -> void
     (set w (* w factor)
          h (* h factor)))))
```

產生：
```cpp
int area() const { return w * h; }
void scale(int factor) { w *= factor; h *= factor; }
```

---

## 七、friend 宣告

C-Mera 沒有專門的 `friend` 語法；用 `cpp` 嵌入：

```lisp
(class Foo ()
  (private
   (decl ((int secret = 42))))
  (public
   (cpp "friend class Bar;")
   (cpp "friend void inspect(const Foo&);")))

(function inspect ((const Foo& f)) -> void
  (<< cout "secret=" f.secret endl))  ; 可存取 private 成員
```

---

## 八、前向宣告

只寫類別名，不給 body：

```lisp
(class Node)         ; forward declaration => class Node;
(class Graph)        ; forward declaration => class Graph;

(class Node ()
  (public
   (decl ((Graph* g)))))  ; 現在才定義

(class Graph ()
  (public
   (decl ((Node* nodes)))))
```

---

## 九、class template（類別模板）

完整的 Stack 實作：

```lisp
(include <iostream>)
(using-namespace std)

(template ((typename T))
  (class Stack ()
    (private
     (decl ((T* data))
           ((int cap))
           ((int top))))
    (public
     (constructor ((int capacity))
       :init ((cap capacity) (top 0))
       (set data (new T[capacity])))

     (destructor
       (delete[] data))

     (function push ((const T& v)) -> void
       (if (== top cap)
           (throw (runtime_error "stack full")))
       (set data[top++] v))

     (function pop () -> T
       (if (== top 0)
           (throw (runtime_error "stack empty")))
       (return data[--top]))

     (function peek () const -> (const T&)
       (if (== top 0)
           (throw (runtime_error "stack empty")))
       (return data[(- top 1)]))

     (function empty () const -> bool
       (return (== top 0)))

     (function size () const -> int
       (return top)))))

(function main () -> int
  (decl (((instantiate Stack (int)) s 8))
    (s.push 10)
    (s.push 20)
    (s.push 30)
    (<< cout "size=" (s.size) endl)       ; size=3
    (<< cout "peek=" (s.peek) endl)       ; peek=30
    (<< cout "pop=" (s.pop) endl)         ; pop=30
    (<< cout "pop=" (s.pop) endl))        ; pop=20
  (return 0))
```

```bash
cm c++ stack.lisp -o stack.cpp && g++ -std=c++11 stack.cpp -o stack && ./stack
```

---

## 十、SFINAE（type traits 風格）

C-Mera 沒有專屬語法，但**完全不妨礙你用**。`enable_if` 就是一個型別：

```lisp
(include <type_traits>)
(include <iostream>)
(using-namespace std)

;; 只對整數型別啟用
(template ((typename T))
  (function square ((T x))
    -> (typename (instantiate #:std::enable_if
                              ((instantiate #:std::is_integral (T)))
                              T)::type)
    (return (* x x))))

(function main () -> int
  (<< cout (square 7) endl)       ; 49
  ; (square 3.14)  <- 會編譯錯誤，double 不是整數
  (return 0))
```

寫起來確實很醜——這正是 macro 的用武之地（教學 07 會示範用 macro 包裝 SFINAE）。

---

## 常見坑

| 坑 | 原因 | 解法 |
|---|---|---|
| `destructor virtual` 寫成 `virtual destructor` | C-Mera 的 qualifier 要寫在 body 之前，`virtual` 緊接 `destructor` | 寫成 `(destructor virtual ...)` |
| `(function f () const -> int)` 和 `(function f () -> (const int))` 意思不同 | 前者是 const 成員函式，後者是回傳 `const int` | 看你要的是哪個 |
| `override` 沒被識別 | 忘了寫，或 qualifier 位置錯 | qualifier 放在參數列表後、`->` 前 |
| 多重繼承訪問 specifier 忘了括號 | `(class D ((public A) (public B)))` 每個父類都要一個括號 | 每對父類寫 `(public Foo)` 形式 |

---

## 下一步

- 讀 `tests/cxx.class.00` ~ `cxx.class.04.lisp`——官方提供的完整 class 測試。
- 讀教學 06 了解更進階的 template 技巧（CRTP、特化、部分特化）。
