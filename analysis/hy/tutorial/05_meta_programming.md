# Hy 元編程：宏與 AST 操作 (05_meta_programming.md)

宏 (Macros) 是 Hy 的靈魂。它們讓你能夠自定義語言語法。

## 1. 代碼即數據：引用 (Quoting)
在編寫宏之前，必須理解如何操作程式碼結構。

*   **Quote (`'`)**: 告訴 Hy 「不要執行這段代碼，把它當作一個列表給我」。
*   **Quasiquote (`` ` ``)**: 類似 Quote，但允許使用 `~` 插入動態內容。
*   **Unquote (`~`)**: 在 Quasiquote 內部「切換回」執行模式。

```hylang
(setv x 10)
(print '(+ 1 x))   ; 輸出: [Symbol('+'), 1, Symbol('x')]
(print `(+ 1 ~x))  ; 輸出: [Symbol('+'), 1, 10]
```

## 2. 定義你的第一個宏 (defmacro)
宏就像一個「程式碼工廠」，它接收代碼，修改代碼，然後返回新的代碼供編譯器執行。

### 範例：實現 `unless` (與 `if` 相反)
```hylang
(defmacro unless [condition &rest body]
  `(if (not ~condition)
       (do ~@body)))

;; 使用 unless
(setv x 5)
(unless (> x 10)
  (print "x 不大於 10")
  (print "這是 unless 的威力"))
```

## 3. 宏調試：macroexpand
如果你不確定宏生成了什麼，使用 `macroexpand`。
```hylang
(setv code '(unless (= 1 1) (print "impossible")))
(print (macroexpand code))
;; 輸出: (if (not (= 1 1)) (do (print "impossible")))
```

## 4. 實戰：一個帶有計時功能的宏
```hylang
(import time)

(defmacro with-timer [label &rest body]
  `(do
     (setv start (time.time))
     ~@body
     (setv end (time.time))
     (print f"{~label} 耗時: {(- end start):.4f} 秒")))

;; 使用計時宏
(with-timer "大循環"
  (lfor x (range 1000000) (* x x)))
```

## 5. 注意事項
*   **衛生宏 (Hygienic Macros)**：Hy 的宏並非完全衛生，這意味著宏內部的變量可能會與外部衝突。建議使用 `(gensym)` 生成唯一名稱來避免污染。
*   **何時使用宏**：只有當函數無法完成任務（例如需要改變求值順序或定義新語法）時才使用宏。
