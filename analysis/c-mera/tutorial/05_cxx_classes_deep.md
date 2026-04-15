# 教學 05：C++ 類別深入（virtual、pure、operator、nested、access 切換）

`03_cxx_basics.md` 只示範皮毛。C-Mera 的 class 幾乎支援你在 C++ 裡會寫的一切，這篇把能玩的都攤出來。

## 一、virtual / pure virtual（抽象類別）

在 C-Mera 裡，**virtual 不是關鍵字寫在前面，而是「修飾符」寫在 `->` 附近**。可以放兩個位置：`function foo () virtual -> void` 或 `function foo () -> (virtual void)`；兩者等價。pure virtual 同樣寫法改成 `pure`。

```lisp
(include <iostream>)
(using-namespace std)

(defmacro say (x) `(<< cout ,x endl))

(class Shape ()                              ; 抽象類別
  (public
   (function area () pure -> double)         ; = 0 的 pure virtual
   (destructor virtual (say "~Shape"))))     ; 虛擬解構子（強烈建議）

(class Circle ((public Shape))
  (private (decl ((double r))))
  (public
   (constructor ((double r)) :init ((r r)))
   (function area () -> double
     (return (* 3.14159 r r)))
   (destructor (say "~Circle"))))

(class Rect ((public Shape))
  (private (decl ((double w) (double h))))
  (public
   (constructor ((double w) (double h)) :init ((w w) (h h)))
   (function area () -> double
     (return (* w h)))
   (destructor (say "~Rect"))))

(function main () -> int
  (decl ((Shape* shapes[2] { (new (Circle 3.0)) (new (Rect 2.0 5.0)) }))
    (for ((int i = 0) (< i 2) ++i)
      (<< cout (shapes[i]->area) endl)       ; 多型呼叫
      (delete shapes[i])))
  (return 0))
```

產生 C++：
```cpp
class Shape { public: virtual double area() = 0; virtual ~Shape() { ... } };
class Circle : public Shape { ... };
```

重點：
- `pure` 關鍵字展開後附加 `= 0` 並自動設為 virtual。
- `destructor virtual` 在 destructor 後緊接著寫 `virtual`。
- 多重繼承：`(class Name ((public A) (public B)))`。

## 二、Operator overloading

把運算子當函式名寫（`src/cxx/syntax.lisp` 的 `operator[]` 測試檔示範）：
```lisp
(class Vec3 ()
  (public
   (decl ((double x) (double y) (double z)))
   (constructor ((double x_) (double y_) (double z_))
     :init ((x x_) (y y_) (z z_)))

   (function operator+ ((const Vec3& o)) -> Vec3
     (return (Vec3 (+ x o.x) (+ y o.y) (+ z o.z))))

   (function operator* ((double s)) -> Vec3
     (return (Vec3 (* x s) (* y s) (* z s))))

   (function operator[] ((int i)) -> double&
     (switch i
       (0 (return x))
       (1 (return y))
       (2 (return z))
       (default (throw (out_of_range "bad idx")))))

   (function operator== ((const Vec3& o)) -> bool
     (return (and (== x o.x) (== y o.y) (== z o.z))))))
```

需要自由函式版本（例如 `double * Vec3`）：
```lisp
(function operator* ((double s) (const Vec3& v)) -> Vec3
  (return (Vec3 (* v.x s) (* v.y s) (* v.z s))))
```

印刷用 `<<`：
```lisp
(function operator<< ((#:std::ostream& os) (const Vec3& v)) -> #:std::ostream&
  (<< os "(" v.x ", " v.y ", " v.z ")")
  (return os))
```

## 三、成員初始化列表的幾種形式

```lisp
(constructor ((int x_) (int y_))
  :init ((x x_)                    ; 一般初始化
         (y y_)
         (vec 10 0)                ; 以 (10, 0) 呼叫 vec 的建構子
         (data { 1 2 3 })))         ; C++11 花括號初始化
```

## 四、Nested class（類別內嵌）

`03_cxx_basics.md` 沒提過。在 class 內直接寫另一個 class 或 struct：
```lisp
(class Outer ()
  (public
   (struct Inner
     (decl ((int x) (int y))))

   (class Node ()
     (public
      (decl ((int value)))
      (decl ((Node* next)))))

   (decl ((Node* head)))

   (function push ((int v)) -> void
     (decl ((Node* n = (new Node)))
       (set n->value v
            n->next head
            head n)))))
```

存取：`Outer::Inner`、`Outer::Node`，在 C-Mera 寫成 `#:Outer::Inner` 或 `(from-namespace Outer Inner)`。

## 五、access specifier 任意切換（C-Mera 特例）

正規 C++ 一個 class 的 `private:` / `public:` 是順序切換；**C-Mera 允許巢狀**，展開時會自動攤平（`tests/cxx.class.04.lisp`）：
```lisp
(class Weird ()
  (public
   (private
    (protected
     (decl ((int a)))))         ; a 最終是 protected
   (decl ((int b))))            ; b 是 public
  (decl ((int c))))             ; c 依前一個指定器；實務上建議別這樣寫
```
建議維持扁平寫法，只是知道這個特性存在即可。

## 六、static 成員、const 成員函式

C-Mera 不為 `static` 另設關鍵字，直接把它放進 specifier：
```lisp
(class Counter ()
  (private
   (decl ((static int total))))           ; 宣告
  (public
   (constructor () (++ total))
   (function count () -> int
     (return total))))

;; 在 class 外定義 static 成員
(decl ((int Counter::total = 0)))
```

const 成員函式：把 `const` 當修飾符，跟 `virtual` 一樣位置：
```lisp
(function size () -> (const int)       ; 回傳型別 const
  (return n))

(function size () const -> int         ; const 成員（不改變 this）
  (return n))
```
實務中常用前者 return-type 的 const；後者的 qualifier 形式詳細寫法見 `cxx.misc.lambda.00.lisp` 對 qualifier 的處理。

## 七、friend / 前向宣告

前向宣告直接 `(class Foo)`（不給 body）。`friend` 目前 C-Mera 沒有專門語法；用 `cpp` 預處理寫或直接 `(lisp ...)` 塞原始字串；若需要輕量 workaround：
```lisp
(class Foo ()
  (public
   (cpp "friend class Bar;")             ; 原樣嵌入
   ...))
```

## 八、class template（類別模板）

```lisp
(include <iostream>)

(template ((typename T))
  (class Stack ()
    (private
     (decl ((T* data))
           ((int cap))
           ((int top))))
    (public
     (constructor ((int c))
       :init ((cap c) (top 0))
       (set data (new T[c])))
     (destructor (delete[] data))

     (function push ((const T& v)) -> void
       (set data[(++ top)] v))

     (function pop () -> T
       (return data[(-- top)]))

     (function empty () -> bool
       (return (== top 0))))))
```

使用：
```lisp
(decl (((instantiate Stack (int)) s 16)))   ; Stack<int> s(16);
(s.push 42)
(<< cout (s.pop) endl)
```

或用 typedef 收短：
```lisp
(typedef (instantiate Stack (int)) IStack)
(decl ((IStack s 16)))
```

## 九、SFINAE / type traits 風格

C-Mera 沒有專屬語法，但**完全不妨礙你用**——`enable_if` 就是個型別：
```lisp
(include <type_traits>)

(template ((typename T))
  (function square ((T x))
    ;; 回傳型別用 typename std::enable_if<std::is_integral<T>::value, T>::type
    -> ((instantiate #:std::enable_if
                     ((instantiate #:std::is_integral (T)))
                     T)::type)
    (return (* x x))))
```

寫起來很醜？對，這就是 C-Mera 想給你 macro 的地方（見教學 07）。

## 十、練習
- 寫一個 `Matrix<T, Rows, Cols>` template，支援 `+`、`*`、`operator()(i, j)`。
- 為 Shape/Circle/Rect 加一個 virtual `clone()`（虛擬拷貝建構慣用法）。
- 用 nested class 實作一個 linked list 的 iterator，支援 range-based for。
