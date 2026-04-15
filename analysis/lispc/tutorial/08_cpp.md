# LISP/c C++ 語法教學 (08)

LISP/c 支援 C++ 的大部分特性，包括 class、命名空間、繼承、運算子多載、template 等。本章系統性地介紹這些功能。

---

## 0. 編譯 C++ 程式碼

C++ 程式碼需要用 `g++` 而不是 `gcc` 來編譯：

```lisp
(load "c.lisp")
(compile-cl-file "myapp.cl"
                 :cc "g++"
                 :tags "-std=c++17"
                 :fileout "myapp")
```

或者先翻譯再手動編譯：

```bash
# 在 CLISP 裡
(c-cl-file "myapp.cl" "myapp.cpp")
# 在 shell 裡
g++ -std=c++17 myapp.cpp -o myapp
```

---

## 1. 標頭檔

C++ 的標頭檔不帶 `.h` 副檔名：

```lisp
(headers++ iostream string vector)
```

翻譯成：
```cpp
#include <iostream>
#include <string>
#include <vector>
```

自訂本地標頭：

```lisp
(header++ ("myheader" :local t))
```

→ `#include "myheader.hh"`

---

## 2. 命名空間 (Namespace)

### `using namespace`

```lisp
(using std)
```

→ `using namespace std;`

### 命名空間宣告（定義 namespace 區塊）

```lisp
(namespacedecl mylib
  (func add int ((a int) (b int))
    (return (+ a b))))
```

→
```cpp
namespace mylib{
   int add(int a,int b){
      return ((a)+(b));
   };
}
```

### 存取命名空間成員

使用 `(namespace ...)` 或縮寫 `(ns ...)` 或 `(@ ...)` 表示 `::` 存取：

```lisp
(@ std cout)          ;; std::cout
(ns std string)       ;; std::string
```

---

## 3. Struct（C++ 版）

C++ 的 struct 可以有成員函式，使用 `struct++`（或縮寫 `s{}+`）：

```lisp
(struct++ point
  (public
    (var x float)
    (var y float)
    (func length float ()
      (return (@sqrt (+ (* x x) (* y y)))))))
```

→
```cpp
struct point{
public:
   float x;
   float y;
   float length(){
      return sqrt(((x)*(x))+((y)*(y)));
   };
};
```

---

## 4. Class

`class` 的語法與 `struct++` 類似，預設成員是 private。

```lisp
(headers++ iostream)
(using std)

(class counter
  (private
    (var count int))
  (public
    ;; 建構子：用 cx 或 construct
    (cx ((n int 0)) ((count n)))
    ;; 成員函式
    (func increment void ()
      (++ count))
    (func get-count int ()
      const
      (return count))
    ;; 解構子：用 dx 或 destroy
    (dx nil)))
```

翻譯成：
```cpp
class counter{
private:
   int count;
public:
   counter(int n=0) : count(n){}
   void increment(){
      ++count;
   };
   int get_count() const {
      return count;
   };
   ~counter(){}
};
```

### 建構子語法（`cx`）

```lisp
(cx args init-pairs body...)
```

| 部分 | 說明 |
|------|------|
| `args` | 參數列表，同 `func` |
| `init-pairs` | `((成員 初始值) ...)` 對應 `: member(value)` |
| `body` | 建構子的主體 |

### 存取控制

| LISP/c | C++ |
|--------|-----|
| `(public ...)` | `public:` |
| `(private ...)` | `private:` |
| `(protected ...)` | `protected:` |

---

## 5. 繼承

繼承用 `(inherits ...)` 或 `(inh ...)` 放在 class 名稱後面：

```lisp
(class dog
  ((inherits (public animal)))
  (public
    (cx ((name (t* char))) ((name name)))
    (func speak void ()
      (<<+ cout (s. "Woof!") endl))))
```

→
```cpp
class dog : public animal{
public:
   dog(char* name) : name(name){}
   void speak(){
      cout << "Woof!" << endl;
   };
};
```

---

## 6. 運算子多載（`op` / `operator`）

```lisp
(class vec2
  (public
    (var x float)
    (var y float)
    ;; + 運算子
    (op + vec2 ((other vec2))
      (var result vec2)
      (= (slot result x) (+ x (slot other x)))
      (= (slot result y) (+ y (slot other y)))
      (return result))
    ;; [] 運算子（const 版）
    (op [] (const float) ((i int))
      const
      (if (== i 0) (return x))
      (return y))))
```

→
```cpp
class vec2{
public:
   float x;
   float y;
   vec2 operator+(vec2 other){
      vec2 result;
      ((result).x)=(((x)+((other).x)));
      ((result).y)=(((y)+((other).y)));
      return result;
   };
   const float operator[](int i) const {
      if((i)==(0)) {
         return x;
      }
      return y;
   };
};
```

---

## 7. Template（C++ 泛型）

C++ 的 `template<typename T>` 用 `decltemp`（或縮寫 `t<>`）表示：

```lisp
;; template<typename T>
;; T mymax(T a, T b) { return (a > b) ? a : b; }
(t<> t typename
  (func mymax t ((a t) (b t))
    (return (? (> a b) a b))))
```

→
```cpp
template <typename T>
T mymax(T a,T b){
   return (((a)>(b)))?a:(b);
};
```

### 多個 template 參數

```lisp
(t<> ((n int) (t typename))
  (func fill void ((arr (t* t)))
    (for (var i int 0) (< i n) (++ i)
      (= ([]arr i) (cast 0 t)))))
```

→
```cpp
template <int N, typename T>
void fill(T* arr){
   for(int i=0;((i)<(N));++(i)){
      arr[i]=((T)(0));
   };
};
```

### Template Class

```lisp
(t<> t typename
  (class stack
    (private
      (var data (t* t))
      (var top-idx int))
    (public
      (cx nil nil
        (= data (new (arr t 100)))
        (= top-idx -1))
      (func push void ((val t))
        (= ([]data (++ top-idx)) val))
      (func pop t ()
        (return ([]data (--- top-idx))))
      (func empty bool ()
        const
        (return (< top-idx 0))))))
```

---

## 8. 串流輸出 (`<<+` / `>>+`)

`<<+` 用於 C++ 的串流輸出（`cout <<`），不同於位元移位的 `<<`，它不加括號：

```lisp
(headers++ iostream)
(using std)

(main
  (<<+ cout "Hello, " "world!" endl)
  (var x int 42)
  (<<+ cout "x = " x endl)
  (return 0))
```

→
```cpp
int main(int argc,char **argv){
   cout << "Hello, " << "world!" << endl;
   int x=42;
   cout << "x = " << x << endl;
   return 0;
}
```

`>>+` 用於串流輸入（`cin >>`）：

```lisp
(var n int)
(>>+ cin n)
```

→ `cin >> n`

---

## 9. Lambda（C++11）

使用 `lambda++`（或縮寫 `l++`）：

```lisp
;; [capture](params) -> ret { body }
(lambda++ (x y) ((a int) (b int)) int
  (return (+ a b)))
```

→ `[x,y](int a,int b) -> int { return ((a)+(b)); }`

簡化版 `lambda++*`（`l++*`）：自動推斷，不指定 capture 和 return type：

```lisp
(lambda++* ((a int) (b int))
  (return (+ a b)))
```

→ `[](int a,int b){ return ((a)+(b)); }`

實際使用範例：

```lisp
(headers++ iostream algorithm vector)
(using std)

(main
  (var nums (temp vector int) (arr-decl 5 3 1 4 2))
  (@sort (@begin nums) (@end nums)
         (lambda++* ((a int) (b int))
           (return (< a b))))
  (mapcar nil (@begin nums) (@end nums)
          (lambda++* ((n int))
            (<<+ cout n " ")))
  (<<+ cout endl)
  (return 0))
```

---

## 10. try/catch（例外處理）

```lisp
(try/catch ((e (ns std exception))
  (@some-risky-function)
  (throw (new (ns std runtime-error) (s. "something went wrong"))))
  (<<+ cerr "Error: " (@e.what) endl))
```

→
```cpp
try{
   some_risky_function();
   throw new std::runtime_error("something went wrong");
}catch(std::exception e){
   cerr << "Error: " << e.what() << endl;
}
```

---

## 11. LISP/c 自身的 `template` 與 C++ `template` 的區別

LISP/c 有兩種完全不同的「template」概念，容易混淆：

| | LISP/c `template` | C++ `template` |
|--|--|--|
| **時機** | **翻譯期**（Lisp 執行時） | **編譯期**（C++ 編譯時） |
| **語法** | `(template make-foo (typ) ...)` | `(t<> T typename ...)` |
| **輸出** | 直接展開成多份 C/C++ 程式碼 | 輸出 `template<...>` 關鍵字 |
| **用途** | 消除重複、程式碼生成 | 泛型型別、函式多載 |

**LISP/c `template`**（翻譯期展開）：

```lisp
;; 翻譯時產生 3 個獨立函式定義
(template make-print (typ)
  (func (sym/add print- typ) void ((val typ))
    (@printf (s. "%d\n") val)))
(make-print int)
(make-print long)
(make-print float)
```

**C++ `template`**（編譯期泛型）：

```lisp
;; 輸出一個 C++ template 函式
(t<> t typename
  (func myprint void ((val t))
    (@printf (s. "%d\n") val)))
```

兩者也可以**結合使用**，用 LISP/c template 產生多個 C++ template 特化版本。

---

## 12. virtual 函式與抽象類別

`virtual`（`c.lisp:804`）可以包裝任何 `func` 宣告。加上第二個參數 `0` 就是純虛擬函式：

```lisp
(class shape
  (public
    ;; 一般 virtual 函式（有預設實作）
    (virtual (func area float () const
               (return 0.0)))
    ;; pure virtual（= 0），使 shape 成為抽象類別
    (virtual (func draw void ()) 0)
    (virtual (func describe void () const) 0)
    ;; virtual 解構子（多型刪除必備）
    (virtual (dx nil))))
```

→
```cpp
class shape{
public:
   virtual float area() const {
      return 0.0;
   };
   virtual void draw() = 0;
   virtual void describe() const = 0;
   virtual ~shape(){}
};
```

繼承並實作抽象類別：

```lisp
(class circle
  ((inherits (public shape)))
  (public
    (cx ((r float)) ((radius r)))
    (func area float () const
      (return (* 3.14159 radius radius)))
    (func draw void ()
      (<<+ cout "Drawing circle r=" radius endl))
    (func describe void () const
      (<<+ cout "Circle with radius " radius endl)))
  (private
    (var radius float)))
```

---

## 13. `friend` 函式與 `friend` 類別

`friend`（`c.lisp:931`）讓外部函式或類別存取 private 成員：

```lisp
(class matrix
  (public
    (cx ((r int) (c int)) ((rows r) (cols c)))
    ;; 宣告 operator<< 為 friend，讓它可存取 private 成員
    (friend (t<> t typename
              (func (ns std ostream) (t& (ns std ostream)) 2
                    (((t& (ns std ostream)) os) ((const (t& matrix)) m))))))
  (private
    (var rows int)
    (var cols int)))
```

friend 也可以是另一個 class：

```lisp
(class node
  (private
    (var value int)
    (var (pt next) node))
  (public
    (friend (class linked-list))))  ;;=> friend class linked_list;
```

---

## 14. `static` 成員

使用 `var` 的 modifiers 參數（`c.lisp:555`）來加上 `static` 前綴。modifiers 放在 `init` 之後：

```lisp
;; static int count = 0;
(var count int 0 static)
;;=> "static int count=0"

;; static const int MAX = 100;   (兩個 modifier)
(var !max int 100 static const)
;;=> "static const int MAX=100"

;; 無初始值：init 位置用 nil
(var count int nil static)
;;=> "static int count"
```

在 class 裡使用：

```lisp
(class counter
  (private
    (var count int nil static))    ;; static int count;
  (public
    (func increment void ()
      (++ count))
    (func get-count int () const
      (return count))))

;; class 外部定義 static 成員（C++ 必須）
(var (ns counter count) int 0)    ;;=> "int counter::count=0"
```

---

## 15. `inline` 函式

`inline`（`c.lisp:606`）包裝一個 `func` 宣告：

```lisp
(inline
  (func square float ((x float))
    (return (* x x))))
;;=> "inline float square(float x){ return ((x)*(x)); }"
```

在 class 內直接定義本體的函式**自動是 inline**（C++ 標準行為），不需要額外加 `inline`。

---

## 16. `auto` 型別與型別推斷

LISP/c 的 `c-strify` 會把 `auto` 直接傳遞，因此可以直接用作型別：

```lisp
(var x auto 42)
;;=> "auto x=42"

(var it auto (@vec.begin))
;;=> "auto it=vec.begin()"
```

範圍式 for 迴圈（Range-based for）：

```lisp
;; for (auto& x : vec) { ... }
;; LISP/c 沒有直接的 range-for 語法，用 cpp 輸出原始 C++ 較方便
(lisp (format nil "for(auto& x : ~a)" (cof 'vec)))
```

或者用 `cpp` 直接插入：

```lisp
(cpp "for(auto& x : vec){")
  (@process x)
(cpp "}")
```

---

## 17. `constexpr`

`constexpr` 可以直接當作 modifier 或型別前綴使用：

```lisp
;; constexpr int MAX = 256;
(var !max int 256 constexpr)
;;=> "constexpr int MAX=256"

;; constexpr 函式
(inline
  (func cube int ((x int))
    constexpr
    (return (* x x x))))
```

注意：`constexpr` 前綴目前最可靠的方式是用 `var` 的 modifiers，或直接用 `(cpp constexpr ...)` 輸出。

---

## 18. 多重繼承

`inherits`（或 `inh`）接受多個父類別：

```lisp
(class flying-fish
  ((inherits (public fish) (public bird)))
  (public
    (cx ())
    (func describe void ()
      (<<+ cout "I can swim and fly!" endl))))
```

→
```cpp
class flying_fish : public fish public bird{
public:
   flying_fish(){}
   void describe(){
      cout << "I can swim and fly!" << endl;
   };
};
```

---

## 19. 更多運算子多載範例

### 比較運算子

```lisp
(class point
  (public
    (var x int) (var y int)
    (cx ((px int) (py int)) ((x px) (y py)))
    (op == bool ((other (const (t& point))))
      const
      (return (&& (== x (slot other x))
                  (== y (slot other y)))))
    (op != bool ((other (const (t& point))))
      const
      (return (! (== (*this) other))))))
```

### 型別轉換運算子

```lisp
;; operator float() — 把物件轉成 float
(op float float ()
  const
  (return (cast (+ (* x x) (* y y)) float)))
```

→ `float operator float() const { return (float)(((x)*(x))+((y)*(y))); }`

### 前置 `++` 與後置 `++`

```lisp
;; 前置 ++
(op ++ (t& iterator) ()
  (++ ptr)
  (return (*this)))

;; 後置 ++（dummy int 參數）
(op ++ iterator ((dummy int))
  (var tmp iterator (*this))
  (++ ptr)
  (return tmp))
```

---

## 20. `explicit` 建構子

> **注意**：`explicit`（`c.lisp:965`）目前有 bug，format 字串缺少 `xs` 參數，會輸出空字串。請用 `(cpp explicit ...)` 或直接在 `cwrite` 裡手動加前綴。

目前建議的寫法：

```lisp
;; 用 cpp 直接輸出 explicit 建構子宣告
(cpp "explicit MyClass(int x);")

;; 或在翻譯後的字串前手動加 explicit：
(let ((ctor (cof '(cx ((x int)) nil))))
  (format nil "explicit ~a" ctor))
```

---

## 21. `using` 型別別名（C++11 `using`）

`usevar`（`c.lisp:951`，縮寫 `uv` / `use`）產生 `using name = type`：

```lisp
(usevar (int-vec (temp (ns std vector) int)))
;;=> "using int_vec = std::vector<int>"

(usevar (callback (t* (funcarg f (void) ((x int))))))
;;=> "using callback = void(*f)(int x)"
```

---

## 已知限制

| 功能 | 狀態 | 建議替代 |
|------|------|---------|
| `explicit` 關鍵字 | Bug（`c.lisp:965`，輸出空字串） | `(cpp "explicit ...")` |
| `ifndef`/`ifdef` | Bug（`c.lisp:650`，expr 未插入） | `(cpp ifndef ...)` / `(pragma once)` |
| Range-based `for` | 無直接支援 | `(cpp "for(auto& x : ...){")` |
| `static_assert` | 無直接支援 | `(cpp "static_assert(...)")` |
| `decltype` | 無直接支援 | 當作型別名稱 `decltype(x)` 用字串 |
