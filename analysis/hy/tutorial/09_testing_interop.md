# 類型提示、測試與進階互操作 (09_testing_interop.md)

本章介紹如何編寫更健壯的 Hy 程式碼，並與 Python 工具鏈深度集成。

## 1. 類型提示 (Type Hinting)
Hy 支持 Python 的類型註釋語法，這對於 IDE 支持和 `mypy` 檢查非常重要。

```hylang
(defn add [^int x ^int y] ^int
  (+ x y))

;; 對於複雜類型
(import [typing [List Dict]])
(defn process-names [^ (List str) names]
  (for [n names] (print n)))
```

## 2. 使用 pytest 測試 Hy
你可以像測試 Python 一樣測試 Hy。只需要確保安裝了 `hy`。

**test_logic.hy**:
```hylang
(import [my_module [add]])

(defn test-add []
  (assert (= (add 1 2) 3)))

(defn test-fail []
  (assert (= (+ 1 1) 3))) ; 這會失敗
```
執行命令：`pytest test_logic.hy`

## 3. 從 Python 調用 Hy (進階)
除了 `import hy`，你也可以在 Python 中動態執行 Hy 代碼。

```python
import hy
# 執行字串
result = hy.eval('(print "Hello from Hy")')

# 調用 Hy 文件中的函數
import my_hy_script
my_hy_script.some_func(1, 2)
```

## 4. 檢查 Hy 對象
使用 `hy.repr` 可以獲得對象的 Hy 風格字串表示，這在調試時比 Python 的 `repr` 更有用。

```hylang
(setv data [1 2 {"a" 3}])
(print (hy.repr data)) ; 輸出: [1 2 {"a" 3}]
```
