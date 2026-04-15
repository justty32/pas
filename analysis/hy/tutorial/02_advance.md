# Hy 進階流程控制與函數 (02_advance.md)

本章節介紹如何定義函數、處理條件判斷以及循環邏輯。

## 1. 條件判斷
### if 語句
格式：`(if 條件 成立執行 [不成立執行])`
```hylang
(setv score 85)
(if (>= score 60)
    (print "及格")
    (print "不及格"))
```

### cond (多重條件)
對應 Python 的 `if-elif-else` 鏈。
```hylang
(setv x 15)
(cond
  (> x 20) (print "非常大")
  (> x 10) (print "中等")
  True     (print "小")) ; 最後一個 True 相當於 else
```

## 2. 函數定義 (defn)
Hy 的函數支援 Python 的所有參數特性（默認值、*args, **kwargs）。

```hylang
;; 基礎函數
(defn add [a b]
  (+ a b))

;; 帶有默認參數與可變參數
(defn complex-func [x [y 10] &rest args &kwargs kwargs]
  (print f"x: {x}, y: {y}")
  (print f"其餘位置參數: {args}")
  (print f"關鍵字參數: {kwargs}"))

(complex-func 1 2 3 4 :extra "hello")
;; 輸出:
;; x: 1, y: 2
;; 其餘位置參數: (3, 4)
;; 關鍵字參數: {'extra': 'hello'}
```

## 3. 循環與迭代
### for 循環
```hylang
;; 基本迭代
(for [i (range 3)]
  (print f"第 {i} 次迭代"))

;; 迭代字典
(setv d {"a" 1 "b" 2})
(for [[k v] (.items d)]
  (print f"鍵: {k}, 值: {v}"))
```

### while 循環
```hylang
(setv count 0)
(while (< count 3)
  (print f"計數中: {count}")
  (setv count (+ count 1)))
```

## 4. 異常處理 (try)
```hylang
(try
  (setv val (/ 10 0))
  (except [e ZeroDivisionError]
    (print "捕獲到除以零錯誤！"))
  (else
    (print "沒有發生異常"))
  (finally
    (print "不論如何都會執行")))
```

## 5. 作用域管理
Hy 遵循 Python 的作用域規則。可以使用 `global` 或 `nonlocal`。
```hylang
(setv counter 0)
(defn increment []
  (global counter)
  (setv counter (+ counter 1)))
```
