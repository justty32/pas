# C/C++ 關鍵字處理 (13)：static、const、inline、extern、auto、constexpr、using、static_cast、static_assert、concept

本章說明在 LISP/c 中如何使用各種 C/C++ 儲存類別修飾子（storage class specifiers）、型別修飾子（type qualifiers）以及 C++ 特有關鍵字。

---

## 1. `const`：常數修飾

`(const ...)`（`c.lisp:476`）為宣告加上 `const` 前綴：

```lisp
;; const 變數
(const x int 42)
;;=> "const int x=42"

(const (pt buf) char)
;;=> "const char *buf"

(const msg (t* char) (str "hello"))
;;=> "const char* msg="hello""
```

### const 方法（C++ 專用）

在 `func` 的本體第一個元素放 `const`（`block-c` → `c.lisp:583`），`block-c` 會自動在 `{` 前加上 ` const `：

```lisp
(class point
  (public
    (var x float)
    (var y float)
    (func length float ()
      const                       ;; ← 放在本體第一位
      (return (@sqrt (+ (* x x) (* y y)))))))
```

輸出：
```c
class point{
public:
   float x;
   float y;
   float length() const{
      return sqrt((x*x)+(y*y));
   }
}
```

---

## 2. `static`：靜態儲存類別

LISP/c 沒有獨立的 `static` 關鍵字，但可以把 `static` 作為 `var` 的修飾子（`var` → `c.lisp:555`，`modifiers` 參數）：

```lisp
;; 靜態區域變數
(func counter int ()
  (var count int 0 static)    ;; static 作為第四個以後的修飾子
  (++ count)
  (return count))
```

輸出：
```c
int counter(){
   static int count=0;
   ++(count);
   return count;
}
```

### 靜態全域變數

```lisp
(var file-count int 0 static)
;;=> "static int file_count=0"
```

### 靜態類別成員

在 `class` 中用 `var` + `static` 修飾子：

```lisp
(class singleton
  (private
    (var (pt instance) singleton !null static))
  (public
    (func get-instance (t* singleton) ()
      (if (== instance !null)
        (= instance (new singleton)))
      (return instance))))
```

輸出：
```c
class singleton{
private:
   static singleton *instance=NULL;
public:
   singleton *get_instance(){
      if((instance)==(NULL)){new singleton;}
      return instance;
   }
}
```

### 靜態函式

`func` 本身不支援 modifier，需要用 `inline` 的形式或自定義 `lispmacro`：

```lisp
;; 方法一：inline 包裝模式（改用 static 前綴字串）
(lispmacro static-func (nym typ vars &rest body)
  (format nil "static ~a" (c `(func ,nym ,typ ,vars ,@body))))

(static-func helper int ((x int))
  (return (* x 2)))
;;=> "static int helper(int x){\n   return (x)*(2);\n}"
```

---

## 3. `extern`：外部連結宣告

同樣作為 `var` 的修飾子使用：

```lisp
;; 宣告外部變數
(var global-config (t* char) !null extern)
;;=> "extern char* global_config=NULL"

;; 只宣告（無初始值）
(var error-count int nil extern)
;;=> "extern int error_count"
```

### `extern "C"`（C++ 互通）

使用 `cpp` 直接輸出：

```lisp
(cpp "extern \"C\" {")
(func c-api void ((x int)))     ;; 只寫宣告，不加本體
(cpp "}")
```

輸出：
```c
extern "C" {
void c_api(int x)
}
```

---

## 4. `inline`：行內函式

`(inline expr)`（`c.lisp:606`）在任何運算式前加上 `inline` 前綴：

```lisp
(inline (func add int ((a int) (b int))
  (return (+ a b))))
```

輸出：
```c
inline int add(int a,int b){
   return (a)+(b);
}
```

### `inline` 結合 `static`

可以用 `lispmacro` 組合多個修飾子：

```lisp
(lispmacro static-inline-func (nym typ vars &rest body)
  (format nil "static inline ~a" (c `(func ,nym ,typ ,vars ,@body))))

(static-inline-func clamp float ((x float) (lo float) (hi float))
  (return (? (< x lo) lo (? (> x hi) hi x))))
;;=> "static inline float clamp(float x,float lo,float hi){...}"
```

---

## 5. `auto`：型別推導（C++11）

將 `auto` 作為型別傳給 `var`（`c.lisp:555`）。因為 `cof` 對未知符號直接做 `c-strify`（`c.lisp:139`），`auto` 會原樣輸出：

```lisp
(var result auto (+ a b))
;;=> "auto result=(a)+(b)"

(var it auto (slot container begin))
;;=> "auto it=(container)->begin"
```

### 範圍 for 迴圈中的 auto

```lisp
(for (var x auto (slot vec begin))
     (!= x (slot vec end))
     (++ x)
  (@printf (str "%d\n") (*x)))
```

輸出：
```c
for(auto x=(vec)->begin;(x)!=(vec)->end;++(x)){
   printf("%d\n",*(x));
}
```

---

## 6. `constexpr`：編譯期常數（C++11）

同樣作為 `var` 的修飾子，或包裝函式：

```lisp
;; constexpr 常數
(var max-size int 1024 constexpr)
;;=> "constexpr int max_size=1024"

(var pi double 3.14159265358979 constexpr)
;;=> "constexpr double pi=3.14159265358979"
```

### constexpr 函式

同樣需要 `lispmacro` 組合：

```lisp
(lispmacro constexpr-func (nym typ vars &rest body)
  (format nil "constexpr ~a" (c `(func ,nym ,typ ,vars ,@body))))

(constexpr-func square int ((x int))
  (return (* x x)))
;;=> "constexpr int square(int x){\n   return (x)*(x);\n}"
```

---

## 7. `using`：命名空間與型別別名

### 命名空間 using

`(using namespace)`（`c.lisp:949`）輸出 `using namespace X`：

```lisp
(using std)
;;=> "using namespace std"

(using chrono)
;;=> "using namespace chrono"
```

### 型別別名（C++11 `using = `）

`usevar`（`c.lisp:951`，別名：`use`、`uv`）對應 `using NewName = OldType`：

```lisp
(use string-view std/string-view)
;;=> "using string_view=std_string_view"

(use callback (t* void))
;;=> "using callback=void*"

(use size-t (unsigned long))
;;=> "using size_t=unsigned long"
```

> **注意**：`usevar`/`use` 在內部透過 `var-c` 產生輸出，`=` 號兩側不加空格。

### 與 `syn` 的區別

| | `using` | `syn`（`c.lisp:479`） |
|--|---------|------|
| 輸出 | 在 C 程式碼中有 `using X = Y` | 無 C 輸出 |
| 作用層 | C++ 編譯期 | LISP/c 翻譯期 |
| 適用 | 要讓其他 C++ 程式碼看見別名 | 只在 .cl 檔內部使用 |

---

## 8. `static_cast`：C++ 型別轉換

使用 `temp`（`c.lisp:946`）搭配 `call`（`c.lisp:540`）：

```lisp
;; (call (temp 函式名 型別) 引數)
(call (temp static-cast int) x)
;;=> "static_cast<int>(x)"

(call (temp static-cast float) count)
;;=> "static_cast<float>(count)"

(call (temp static-cast (t* void)) ptr)
;;=> "static_cast<void*>(ptr)"
```

原理：
- `(temp static-cast int)` → `"static_cast<int>"`（`static-cast` 經 `c-strify` → `static_cast`）
- `(call "static_cast<int>" x)` → `"static_cast<int>(x)"`

### 其他 C++ 轉型

同樣的模式適用於所有 C++ 轉型運算子：

```lisp
(call (temp dynamic-cast (t* derived)) base-ptr)
;;=> "dynamic_cast<derived*>(base_ptr)"

(call (temp reinterpret-cast (t* char)) ptr)
;;=> "reinterpret_cast<char*>(ptr)"

(call (temp const-cast (t* int)) const-ptr)
;;=> "const_cast<int*>(const_ptr)"
```

---

## 9. `static_assert`：編譯期斷言（C++11）

使用 `@` 前綴呼叫語法（`c.lisp:379`）：

```lisp
(@static-assert (== (@sizeof int) 4))
;;=> "static_assert(sizeof(int)==4)"

(@static-assert (>= !version 2) (str "requires version 2+"))
;;=> "static_assert(VERSION>=2,"requires version 2+")"
```

由於 `static-assert` 經 `c-strify`（`c.lisp:139`）轉換後得到 `static_assert`（連字號→底線），直接呼叫即可。

---

## 10. `concept`：C++20 概念（無原生支援）

LISP/c 目前沒有內建的 `concept` 關鍵字。有兩種替代方案：

### 方案一：`cpp` 直接插入

```lisp
(cpp "concept Printable = requires(T x) { std::cout << x; }")
;;=> "#concept Printable = requires(T x) { std::cout << x; }"
```

> **注意**：`cpp` 會在最前面加 `#`，所以這個方法輸出是 `#concept ...`，不符合 C++ 語法。

### 方案二：`lispmacro` 自定義

```lisp
(lispmacro concept (name &rest requires-body)
  (format nil "template<typename T>~%concept ~a = requires~a"
    (c-strify name)
    (c `(block ,@requires-body))))

(concept printable
  ((@std/cout << x)))
```

### 方案三：用 `lisp` 直接插入任意字串

```lisp
(lisp "template<typename T>
concept Addable = requires(T a, T b) {
  { a + b } -> std::same_as<T>;
};")
```

`lisp`（`c.lisp:681`）會將回傳的字串直接插入輸出，不做任何處理，是插入 LISP/c 尚未支援語法的最直接方式。

---

## 11. 修飾子在 `var` 上的通用模式

`var`（`c.lisp:555`）的 `&rest modifiers` 參數接受任何符號，透過 `cof` 轉換後放在型別宣告之前。由於 `cof` 對未知符號直接做 `c-strify`（`c.lisp:139`），所以任何合法的 C/C++ 修飾子（只要不和 LISP/c 關鍵字衝突）都可以直接使用：

```lisp
;; 語法：(var 名稱 型別 初始值 修飾子...)
(var x int 0 static)              ;;=> "static int x=0"
(var x int nil extern)            ;;=> "extern int x"
(var x int 42 constexpr)          ;;=> "constexpr int x=42"
(var x int 0 static constexpr)    ;;=> "static constexpr int x=0"  (多個修飾子)
(var x auto nil)                  ;;=> "auto x"
```

> **輸出順序**：修飾子依序出現在型別之前，因此 `(var x int 0 static constexpr)` → `"static constexpr int x=0"` 符合 C++ 慣例。

---

## 12. trailing return type（`->` 尾置返回型別，C++11）

在 `func` 本體中以 `(-> 型別)` 開頭（`block-c` → `c.lisp:588`），可產生尾置返回型別：

```lisp
(func add auto ((a int) (b int))
  (-> int)
  (return (+ a b)))
```

輸出：
```c
auto add(int a,int b) -> int{
   return (a)+(b);
}
```

---

## 快速參考表

| C/C++ 關鍵字 | LISP/c 寫法 | 原始碼 | 備注 |
|-------------|-------------|--------|------|
| `const T x` | `(const x T val)` | `c.lisp:476` | |
| `const` 方法 | `(func f T () const ...)` | `c.lisp:583` | `const` 為本體第一元素 |
| `static T x` | `(var x T val static)` | `c.lisp:555` | 修飾子位置 |
| `extern T x` | `(var x T val extern)` | `c.lisp:555` | |
| `constexpr T x` | `(var x T val constexpr)` | `c.lisp:555` | |
| `auto x = e` | `(var x auto e)` | `c.lisp:555` | auto 作為型別 |
| `inline func` | `(inline (func ...))` | `c.lisp:606` | |
| `using namespace X` | `(using X)` | `c.lisp:949` | 只做命名空間 |
| `using A = B` | `(use A B)` | `c.lisp:951` | `usevar` 別名 |
| `static_cast<T>(x)` | `(call (temp static-cast T) x)` | `c.lisp:946,540` | |
| `dynamic_cast<T>(x)` | `(call (temp dynamic-cast T) x)` | `c.lisp:946,540` | |
| `static_assert(e)` | `(@static-assert e)` | `c.lisp:379,540` | |
| `auto f() -> T` | `(func f auto () (-> T) ...)` | `c.lisp:588` | 尾置返回型別 |
| `concept` | `(lisp "...")` | `c.lisp:681` | 無原生支援 |
