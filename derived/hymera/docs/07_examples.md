# 07 — v1 預計達成的四個範例

> 修訂版（2026-05-26）：依「都依照 c-mera」指示，**範例寫法全部對齊 c-mera 體驗**——`(printf ...)` 直接寫、`if`/`for`/`+` 用原名、`p->x` 自動拆。`arr[i]` 維持為 `(aref arr i)`（唯一不對齊，見 ADR 0004）。

每個範例都會：(a) 給使用者要寫的 hymera 程式；(b) 給預期 C/C++ 輸出；(c) 必須能被外部編譯器無 warning 接受。

## 範例 A：hello.c

### A.1 hymera 程式碼
```hylang
;; examples/hello.hy
(import hymera.cli [c-file])
(hymera-c)              ; (pragma :warn-on-core-shadow False) + (require hymera.syntax.c *)

(c-file "hello.c"
  (include <stdio.h>)
  (function main () -> int
    (printf "hello, world\n")    ; quoty 把 printf 識別為 C 函式呼叫
    (return 0)))
```

### A.2 預期輸出（hello.c）
```c
#include <stdio.h>

int main()
{
    printf("hello, world\n");
    return 0;
}
```

### A.3 驗收
```
gcc hello.c -o hello && ./hello
# stdout: hello, world
```

### A.4 quoty 行為要點

`printf` 在編譯期未綁定（沒 import、不在 scope.defined、不是 builtin），quoty 轉成 `(function-call (ident 'printf) (make-nodelist "hello, world\n"))`。

`return` 是核心 shadow 後的 hymera 宏，跳過 quoty 直接展開為 `(return-statement :value 0)`。

## 範例 B：含 struct 的 C 程式

### B.1 hymera
```hylang
(import hymera.cli [c-file])
(hymera-c)

(c-file "point.c"
  (include <stdio.h>)
  (struct Point
    (decl ((int x))
          ((int y))))
  (function distance-sq ((const Point * p)) -> int
    (return (+ (* p->x p->x) (* p->y p->y))))     ; p->x 自動拆成 (-> p x)
  (function main () -> int
    (decl ((Point p)))
    (= p.x 3)                                       ; p.x 自動拆成 (. p x)
    (= p.y 4)
    (printf "%d\n" (distance-sq (& p)))             ; & 一元前綴運算子
    (return 0)))
```

### B.2 預期輸出
```c
#include <stdio.h>

struct Point
{
    int x;
    int y;
};

int distance_sq(const Point* p)
{
    return p->x * p->x + p->y * p->y;
}

int main()
{
    Point p;
    p.x = 3;
    p.y = 4;
    printf("%d\n", distance_sq(&p));
    return 0;
}
```

### B.3 注意
- `distance-sq` 在 renamer 後成 `distance_sq`。
- `p->x` symbol 字串內含 `->`，quoty 階段 cook 為 `(member-access :kind '-> :object p :name x)`。
- `p.x` 同理 cook 為 `(member-access :kind '. :object p :name x)`。
- `(& p)` —— `&` 在 hymera.syntax.c 註冊為**前綴運算子**（與中綴 `&` 同名），quoty 看到第一個位置時依參數個數判斷成 prefix。
- 此範例完全不需要顯式 `(ident ...)` / `(call ...)`，與 c-mera 體驗一致。

## 範例 C：用 namespace 的 C++

### C.1 hymera
```hylang
(import hymera.cli [cpp-file])
(hymera-cpp)             ; 像 hymera-c 但同時 require .c 與 .cpp

(cpp-file "greet.cpp"
  (include <iostream>)
  (using-namespace std)
  (namespace mylib
    (function greet ((const std::string & name)) -> void
      (<< std::cout "Hello, " name "\n")))         ; << 是 c-syntax 註冊的中綴運算子
  (function main () -> int
    (mylib::greet "World")                          ; mylib::greet 是單一 symbol，quoty 走 dotted/colon
    (return 0)))
```

### C.2 預期輸出
```cpp
#include <iostream>
using namespace std;

namespace mylib
{
    void greet(const std::string& name)
    {
        std::cout << "Hello, " << name << "\n";
    }
}

int main()
{
    mylib::greet("World");
    return 0;
}
```

### C.3 驗收
```
clang++ -std=c++17 greet.cpp -o greet && ./greet
# stdout: Hello, World
```

### C.4 quoty 對 `::` 與 `&` 的處理

- `std::cout`、`mylib::greet` —— quoty 對含 `::` 的 symbol 拆成 `(scope-ref std cout)` 等節點。`cook-symbol` 對 `::` 的處理列在 ADR 0004 §「邊角案例」。
- `&` 接在型別後（`std::string & name`）—— 由 `decl`/`parse-params` 拆 declarator 時偵測，產生 `ReferenceDeclarator`，不走 quoty。

## 範例 D：template 容器

### D.1 hymera
```hylang
(import hymera.cli [cpp-file])
(hymera-cpp)

(cpp-file "stack.hpp"
  (include <vector>)
  (namespace mylib
    (template ((typename T))
      (class Stack
        (private
          (decl ((std::vector<T> vec))))            ; std::vector<T> symbol 內含 `<>`
        (public
          (function push ((const T & v)) -> void
            (this->vec.push_back v))                ; this->vec.push_back 多層 cook
          (function pop () -> T
            (decl ((T result = this->vec.back))))
            (this->vec.pop_back)
            (return result))
          (function empty () -> bool
            (return (this->vec.empty))))))))
```

### D.2 預期輸出
```cpp
#include <vector>

namespace mylib
{
    template <typename T>
    class Stack
    {
    private:
        std::vector<T> vec;
    public:
        void push(const T& v)
        {
            this->vec.push_back(v);
        }
        T pop()
        {
            T result = this->vec.back();
            this->vec.pop_back();
            return result;
        }
        bool empty()
        {
            return this->vec.empty();
        }
    };
}
```

### D.3 driver + 驗收
```cpp
// main.cpp
#include "stack.hpp"
#include <iostream>
int main() {
    mylib::Stack<int> s;
    s.push(1); s.push(2); s.push(3);
    while (!s.empty()) {
        std::cout << s.pop() << " ";
    }
    std::cout << "\n";
}
```
```
clang++ -std=c++17 main.cpp -o stackdemo && ./stackdemo
# stdout: 3 2 1
```

### D.4 體驗對照

c-mera 同等程式的寫法（用 c-mera 的 `cmu-c`／`cl:`）：
```lisp
(c-syntax::function push ((const T & v)) -> void
  (this->vec.push_back v))
```

hymera 寫法**完全相同**。這就是「全面對齊」要達成的價值——讀 c-mera 程式碼可直接搬到 hymera。

## 整體完工檢核清單

對應 `PROJECT.md` §5：

- [ ] 範例 A 通過 gcc
- [ ] 範例 B 通過 gcc，且輸出值正確（25 + `緊急`-style 視程式）
- [ ] 範例 C 通過 clang++ `-std=c++17`
- [ ] 範例 D 含 driver 一起通過 clang++ `-std=c++17`，輸出正確
- [ ] 五個 Pass（flatten / else-if / if-blocker / decl-blocker / renamer）全部對 c-mera 1:1 對齊且各有對照測試
- [ ] 五個 defNODE 宏（defnode/defstatement/defexpression/defleaf/defproxy）齊備
- [ ] `defgeneric` / `defmethod` / `:before` / `:after` / `:self` 方法組合機制完成
- [ ] `defprettymethod` / `defproxyprint` / `with-proxynodes` / `make-proxy` / `del-proxy` 完整
- [ ] `defsyntax` / `c-syntax` 機制
- [ ] `quoty` + symbol cooking（`->`、`.`、`++`、`--`、`::`、浮點後綴）齊備
- [ ] 至少一個 proxy 列印場景（型別後空白）
- [ ] README 含安裝、第一個範例、與 c-mera 對照表
- [ ] 四份 ADR（0001-0004）完整

當所有勾都打上，v1 結束，與 c-mera 對齊度達到「**設計層 1:1 + 體驗層 95% +（reader）`arr[i]` 一處例外**」。
