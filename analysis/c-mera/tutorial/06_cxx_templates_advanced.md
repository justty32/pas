# 教學 06：Template 進階語法（C-Mera 對照）

C-Mera 的 template 不是新發明——它把 C++ 的 template 模板機制直接映射成 sexp。只要記住兩個巨集：**`template`** 宣告模板、**`instantiate`** 具現化。

## 一、最小模板

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

**參數列表語法**：`((typename T) (typename U) (int N) (class Allocator))` 等——每個括號都是一個模板參數，第一個 token 是類別／`typename`／`int`（非型別參數）之類。

## 二、多參數、非型別參數

```lisp
(template ((typename T) (int N))
  (class Array ()
    (public
     (decl ((T data[N])))
     (function size () -> int (return N)))))

;; 使用
(decl (((instantiate Array (int) (16)) a)))  ; Array<int, 16> a;
```

**`instantiate` 的每個參數也要一組括號**：`(instantiate Array (int) (16))`，因為每個「模板引數」是當成型別來 decompose。

## 三、預設模板參數

```lisp
(template ((typename T) (typename Alloc = (instantiate #:std::allocator (T))))
  (class MyVec () ...))
```
目前 C-Mera 對「預設值帶有 `instantiate`」的情境需要顯式寫；如果失敗，最穩的做法是 `typedef` 先簡化：
```lisp
(typedef (instantiate #:std::allocator (int)) IntAlloc)
(template ((typename T) (typename A = IntAlloc)) ...)
```

## 四、模板特化（full specialization）

C-Mera 沒有專門的「specialization」語法——**直接再寫一個不帶 `template` 開頭的函式／類別版本**即可，只是型別用 `instantiate` 拼出來：
```lisp
(template ((typename T))
  (function type-name () -> (const char*)
    (return "unknown")))

;; 特化 T = int：直接定義同名但帶 <> 的具現函式
(function (instantiate-explicit (type-name (int))) () -> (const char*)
  (return "int"))

(function (instantiate-explicit (type-name (float))) () -> (const char*)
  (return "float"))
```

`instantiate-explicit` 用於產生 `type_name<int>` 的字面字串當符號。更常見的做法其實是直接用巨集產生（教學 07 會示範）。

## 五、部分特化（類別）

同樣沒有專屬語法——照 C++ 寫法即可：
```lisp
(template ((typename T))
  (class Traits ()
    (public (decl ((static bool is_ptr = false))))))

(template ((typename T))
  (class (instantiate-explicit (Traits (T*))) ()    ; Traits<T*>
    (public (decl ((static bool is_ptr = true))))))
```

## 六、模板函式實例化（顯式）

```lisp
;; 觸發實例化（告訴編譯器產生這個版本的符號）
(instantiate-explicit (identity (int)))
```

產生 `template int identity<int>(int);`。常用於把模板實作和宣告拆檔時強制產生符號。

## 七、型別別名 / typedef / using 別名

經典 typedef：
```lisp
(typedef (instantiate #:std::vector (int)) IntVec)
(typedef int (fpointer Handler ((int)))) 
```

C++11 的 `using` 別名 C-Mera 沒有專屬巨集，用 `using`：
```lisp
(using (instantiate-explicit (IntVec)))   ; 比較少見
```
實務上 `typedef` 比較穩。也可直接插：
```lisp
(cpp "using IntVec = std::vector<int>;")
```

## 八、variadic template（可變參數模板）

C-Mera 沒有 `...` 的 sexp 等價符號；需要時可以這樣：
```lisp
(template ((typename #:|Args...|))
  (function log-all ((#:|Args...| args)) -> void
    (cpp "using expander = int[];")
    ...))
```
`#:|...|` 是「強制保留原始字元的符號」；因為名稱裡有 `.`，要用豎線 `| |` 框住整個符號名。老實說，**可變模板在 C-Mera 裡寫起來很醜**，這是 sexp 的限制。折衷方案：只把 variadic 部分用 `cpp "..."` 原樣塞進去。

## 九、常見組合：STL 容器 + 模板

```lisp
(include <vector>)
(include <map>)
(include <string>)
(using-namespace std)

;; vector<pair<int, string>>
(typedef (instantiate pair (int) (string))      IntStr)
(typedef (instantiate vector (IntStr))          Rows)

(function make-rows () -> Rows
  (decl ((Rows r))
    (r.push_back (IntStr 1 "a"))
    (r.push_back (IntStr 2 "b"))
    (return r)))

;; map<string, vector<int>>
(typedef (instantiate vector (int))              IVec)
(typedef (instantiate map (string) (IVec))       StrToIVec)
```

## 十、CRTP（Curiously Recurring Template Pattern）

```lisp
(template ((typename Derived))
  (class Base ()
    (public
     (function interface () -> void
       (funcall (cast (Derived*) this) ->impl)))))

(class My ((public (instantiate Base (My))))
  (public
   (function impl () -> void
     (<< #:std::cout "My::impl" #:std::endl))))
```

`(cast (Derived*) this)` → `(Derived*)this`。`(funcall (cast ...) ->impl)` 有點繞，可讀性更好的寫法：
```lisp
(decl ((Derived* d = (static-cast Derived* this)))
  (d->impl))
```

## 十一、查錯小撇步

當模板展開產出奇怪 C++ 時：
1. 先把中間 typedef 抽出來命名，讓產出對應更直觀。
2. `cm c++ file.lisp` 不加 `-o` 就印到 stdout，立刻 diff。
3. 實在過不去：用 `cpp "..."` 把那段 C++ 原樣寫進去當逃生門，之後再慢慢改回 sexp。
