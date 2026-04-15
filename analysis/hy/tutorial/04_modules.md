# Hy 模組系統、導入與 REPL (04_modules.md)

本章節介紹如何組織程式碼、導入外部庫，以及 Hy 的編譯機制。

## 1. 導入模組 (import)
Hy 的 `import` 語法非常靈活。

```hylang
;; 基礎導入
(import os)

;; 部分導入 (from math import sqrt, pi)
(import [math [sqrt pi]])

;; 帶有別名的導入
(import [datetime [datetime :as dt]])

;; 使用導入的內容
(print (sqrt pi))
(print (os.getcwd))
```

## 2. 導入宏 (require)
**重要概念**：宏是在編譯期執行的。如果你想使用另一個文件定義的宏，你必須使用 `require` 而不是 `import`。
`import` 導入的是運行時的對象（函數、類），`require` 導入的是編譯時的規則（宏）。

```hylang
;; 假設在 my_lib.hy 中定義了一個名為 'my-macro' 的宏
(require [my-lib [my-macro]])

;; 現在可以使用該宏了
(my-macro ...)
```

## 3. 模組主入口
```hylang
(if (= __name__ "__main__")
  (do
    (print "程式啟動中...")
    (main-func)))
```

## 4. 自動編譯與 Hook
Hy 提供了一個導入鉤子 (Import Hook)。一旦你在 Python 程式中執行了 `import hy`，你就可以直接 `import` `.hy` 文件，Python 會自動將其編譯並載入。

**python_side.py**:
```python
import hy
import my_hy_module  # 這會加載 my_hy_module.hy
```

## 5. REPL 的實用技巧
在 `hy` REPL 中：
*   使用 `(doc 函數名)` 查看文檔字串。
*   使用 `(help 對象)` 獲取詳細幫助。
*   最後一個運算結果會存儲在變量 `*1` 中（類似 Python 的 `_`）。
