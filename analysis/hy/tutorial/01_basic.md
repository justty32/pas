# Hy 基礎語法詳解 (01_basic.md)

本章節介紹 Hy 的原子類型、賦值操作以及基礎算術邏輯。

## 1. 註釋
```hylang
; 單行註釋：用於行尾說明
;; 雙分號：通常用於代碼塊上方的說明
;;; 三分號：用於文件頂部的標題或重大段落
```

## 2. 變量賦值與多重賦值 (setv)
在 Hy 中，我們不使用 `=` 來賦值，而是使用 `setv`。
```hylang
;; 基礎賦值
(setv x 10)

;; 多重賦值 (對應 Python 的 a, b = 1, 2)
(setv a 1
      b 2
      c (+ a b))

(print a b c) ; 輸出: 1 2 3
```

## 3. 原子數據類型
*   **數字**: `123`, `3.14`, `2e10`
*   **布林**: `True`, `False`
*   **空值**: `None`
*   **字串**: `"普通字串"`
*   **格式化字串 (f-string)**:
    ```hylang
    (setv name "Hy")
    (print f"Hello, {name}!") ; 輸出: Hello, Hy!
    ```

## 4. 前綴算術運算 (Prefix Notation)
與 Python 的中綴運算 (`1 + 2`) 不同，Hy 使用前綴運算 (`+ 1 2`)。
```hylang
;; 複雜運算練習： (10 + 5) * 2 / (6 - 4)
(setv result (/ (* (+ 10 5) 2) 
                (- 6 4)))
(print result) ; 輸出: 15.0

;; 其他運算符
(print (// 10 3))  ; 整除: 3
(print (% 10 3))   ; 取餘: 1
(print (** 2 10))  ; 次方: 1024
```

## 5. 比較與邏輯運算
Hy 的比較操作符可以接收多個參數（鏈式比較）。
```hylang
;; 鏈式比較 (對應 Python 的 1 < x < 20)
(setv x 10)
(print (< 1 x 20)) ; True

;; 等於比較 (使用 = 而非 ==)
(print (= x 10)) ; True

;; 邏輯運算
(print (and True (> x 5)))  ; True
(print (or False (< x 0)))  ; False
(print (not (= x 0)))       ; True
```

## 6. 範例：計算圓面積
```hylang
(setv pi 3.14159
      radius 5)
(setv area (* pi (** radius 2)))
(print f"半徑為 {radius} 的圓面積是：{area}")
```
