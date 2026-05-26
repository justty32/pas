# 型別註解、測試與進階互操作 (09_testing_interop.md)

> 對齊版本：**Hy 1.3.0**。本章修正 Hy 0.x 的 `^type` 註解寫法、舊 import 形狀、以及 `hy.eval` 傳字串的錯誤示範。

## 1. 型別註解 (Type Annotation)

Hy 1.x 用 reader macro `#^` 加註型別（規則來源：`projects/hy/hy/reader/hy_reader.py:402`）。**舊版的 `^int` 寫法已移除**。

### 1.1 參數與回傳值

```hylang
(defn #^ int add [#^ int x #^ int y]
  (+ x y))

(print (add 2 3))                   ; ✅ → 5
(print (. add __annotations__))     ; ✅ → {'x': int, 'y': int, 'return': int}
```

語法：`#^ 型別 變數名`。對 `defn` 而言，**回傳型別寫在名稱之前**（`#^ int add`）。

### 1.2 複雜型別 / 泛型

```hylang
(import typing [List Dict Optional])

(defn process-names [#^ (List str) names]
  (for [n names] (print n)))

(defn lookup [#^ (Dict str int) table #^ str key]
  (.get table key))
```

### 1.3 區域變數註解（`annotate`）

```hylang
(setv x #^ int 10)
;; 或用 (annotate target type) 形式：
(setv y (annotate 20 int))
```

### 1.4 Python 3.12+ 的型別參數（`:tp`）

```hylang
(defn :tp [T] identity [#^ T x] x)   ; 等同於 Python 的 def identity[T](x: T) -> T
```

> 規則來源：`projects/hy/hy/core/result_macros.py:1618`（`defn` 的 pattern）。

---

## 2. 用 pytest 測試 Hy

pytest 能直接收 `.hy` 測試檔（前提：pytest 啟動時 `import hy` 已執行，這會註冊 `.hy` 的 import hook）。最穩的做法：在 `conftest.py` 開頭加上 `import hy`。

**conftest.py**：
```python
import hy   # 註冊 .hy 的 import 鉤子
```

**my_module.hy**：
```hylang
(defn add [a b] (+ a b))
```

**test_logic.hy**：
```hylang
(import my-module [add])     ; 注意：Hy 端用連字號，Python 檔名是底線—mangling 會自動對齊

(defn test-add []
  (assert (= (add 1 2) 3)))

(defn test-list-eq []
  (assert (= (list (range 3)) [0 1 2])))
```

執行：`pytest test_logic.hy`。

---

## 3. Python ↔ Hy 互操作

### 3.1 從 Python 載入 Hy 模組

```python
import hy            # 一次性註冊 import 鉤子
import my_hy_script  # 直接 import .hy 檔
print(my_hy_script.some_func(1, 2))
```

### 3.2 在 Python 中執行 Hy 程式碼

`hy.eval` 接收的是**已解析的 model**，不是字串。若你只有字串，先 `hy.read`/`hy.read_many`：

```python
import hy
from hy.reader import read, read_many

# ❌ 錯：hy.eval 不接受字串
# hy.eval('(print "Hello from Hy")')

# ✅ 正：先 read 成 model 再 eval
result = hy.eval(read("(+ 1 2)"))   # → 3

# 多個 form：用 read_many
for form in read_many("(setv x 10) (print x)"):
    hy.eval(form)
```

來源：`hy.eval` 文件字串明言「the first argument should be a model rather than source text」（`projects/hy/hy/compiler.py:770`）。

### 3.3 在 Hy 中直接呼叫 Python 物件

Hy 就是 Python，無接縫。Python 端 `snake_case`、Hy 端 `kebab-case`，重整 (`hy.mangle`) 自動對齊：

```hylang
(import numpy :as np)
(setv arr (np.array [1 2 3]))
(print (np.mean arr))      ; ✅ → 2.0
```

---

## 4. 檢視 Hy 物件：`hy.repr`

`hy.repr` 給出 Hy 風格的字串表示，比 Python `repr` 對 Lisp 開發者更直觀：

```hylang
(setv data [1 2 {"a" 3}])
(print (hy.repr data))     ; → [1 2 {"a" 3}]
(print (repr data))        ; Python repr → [1, 2, {'a': 3}]
```

也可註冊自定型別的 `hy-repr` 處理函式（見 `projects/hy/hy/core/hy_repr.hy`）。
