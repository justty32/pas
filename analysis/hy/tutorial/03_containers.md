# Hy 容器、切片與推導式 (03_containers.md)

本章節深入探討如何操作 Python 的內建資料結構。

## 1. 定義容器
```hylang
(setv my-list [1 2 3])             ; List
(setv my-tuple #(1 2 3))           ; Tuple
(setv my-set #{1 2 3})             ; Set
(setv my-dict {"name" "Hy" "age" 1}) ; Dict
```

## 2. 存取與修改 (get / setv)
使用 `get` 來獲取元素，它可以接收多個索引來存取巢狀結構。
```hylang
(setv data [[1 2] [3 4]])

;; 獲取單個元素 (data[0])
(print (get data 0)) ; [1 2]

;; 獲取巢狀元素 (data[1][0])
(print (get data 1 0)) ; 3

;; 修改列表元素
(setv (get my-list 0) 100)
(print my-list) ; [100, 2, 3]
```

## 3. 切片操作 (cut)
對應 Python 的 `obj[start:end:step]`。
```hylang
(setv nums (list (range 10)))
;; 獲取索引 1 到 7，步長為 2
(print (cut nums 1 8 2)) ; [1, 3, 5, 7]

;; 省略參數
(print (cut nums 5)) ; 獲取前 5 個: [0, 1, 2, 3, 4]
```

## 4. 強大的推導式 (Comprehensions)
Hy 提供了一系列以 `for` 結尾的推導式：
*   `lfor`: List comprehension
*   `dfor`: Dict comprehension
*   `sfor`: Set comprehension
*   `gfor`: Generator expression

```hylang
;; 範例 1: 平方列表
(setv squares (lfor x (range 5) (* x x)))
(print squares) ; [0, 1, 4, 9, 16]

;; 範例 2: 帶條件的過濾 (僅保留偶數)
(setv evens (lfor x (range 10) :if (= (% x 2) 0) x))
(print evens) ; [0, 2, 4, 6, 8]

;; 範例 3: 字典推導式
(setv name-map (dfor x ["apple" "banana"] [x (len x)]))
(print name-map) ; {'apple': 5, 'banana': 6}

;; 範例 4: 嵌套推導式
(setv matrix-flat (lfor row [[1 2] [3 4]] x row x))
(print matrix-flat) ; [1, 2, 3, 4]
```

## 5. 常用容器方法
由於 Hy 就是 Python，你可以直接調用所有方法。
```hylang
(setv items [])
(.append items "A")
(.extend items ["B" "C"])
(print (.pop items)) ; "C"
```
