# Hy 模組系統、導入與 REPL (04_modules.md)

本章節介紹如何組織程式碼、導入外部庫，以及 Hy 的編譯機制。

## 1. 導入模組 (import)
Hy 的 `import` 語法與 Python 對應，但寫法是 Lisp 形式。**Hy 1.x 起，模組名直接放在第一位，不再有內層多餘的中括號**：

```hylang
;; 基礎導入
(import os)

;; 部分導入 (from math import sqrt, pi)
(import math [sqrt pi])

;; 帶有別名的導入
(import datetime [datetime :as dt])

;; 取得全部公開名稱（對應 from m import *）
(import math *)

;; 多重來源一次寫
(import os
        sys
        json [loads dumps])

;; 使用導入的內容
(print (sqrt pi))
(print (os.getcwd))
```

> ⚠️ **0.x → 1.x 變更**：舊寫法 `(import [math [sqrt pi]])` 在 Hy 1.x **會直接報語法錯誤**。

## 2. 導入宏 (require)
**重要概念**：宏在**編譯期**執行。要用另一個檔案定義的宏，必須用 `require`，**不能**用 `import`。`import` 載的是執行期物件（函數、類），`require` 載的是編譯期規則（宏）。

```hylang
;; 假設 my_lib.hy 內定義了名為 my-macro 的宏（注意：Hy 模組名通常用底線）
(require my_lib [my-macro])

;; 別名與全部
(require my_lib [my-macro :as my-m])
(require my_lib *)               ; 取全部（謹慎）

;; reader macro 要走 :readers
(require my_lib :readers [my-tag])
```

跨檔案宏分享、`hy.R.` 一次性宏、編譯期/執行期模型等深入主題，見 [`11_macros_advanced.md`](11_macros_advanced.md)。

## 3. 模組主入口
```hylang
;; ⚠️ Hy 1.x 的 if 必須三引數；「只在成立時做」請用 when
(when (= __name__ "__main__")
  (print "程式啟動中...")
  (main-func))
```

## 4. 自動編譯與 Hook
Hy 提供了一個導入鉤子 (Import Hook)。一旦你在 Python 程式中執行了 `import hy`，你就可以直接 `import` `.hy` 文件，Python 會自動將其編譯並載入。

**python_side.py**:
```python
import hy
import my_hy_module  # 這會加載 my_hy_module.hy
```

## 5. REPL 的實用技巧
在互動式 `hy` REPL 中：
*   `(help 對象)`：Python 內建的 help。
*   `(print obj.__doc__)`：查看 docstring。
*   `*1`、`*2`、`*3`：最近三次運算結果（最新在 `*1`）。
*   `*e`：最近一次未捕捉的例外。
*   來源：`projects/hy/hy/repl.py:293`。注意：這些是**互動 REPL 專屬**，從 stdin 一次餵入腳本時不一定可用。
