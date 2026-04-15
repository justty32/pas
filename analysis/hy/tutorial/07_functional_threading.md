# Hy 函數式編程與線程宏 (07_functional_threading.md)

Hy 作為 Lisp，提供了許多函數式編程的工具，特別是「線程宏」，能極大提升代碼的可讀性。

## 1. 線程宏 (Threading Macros)
在 Python 中，嵌套調用會變成 `func3(func2(func1(data)))`。Hy 使用線程宏將其「拉平」。

### 第一步插入宏 (->)
將上一個結果作為下一個函數的**第一個參數**。
```hylang
;; Python:  val = func3(func2(func1(data, a), b), c)
(-> data
    (func1 a)
    (func2 b)
    (func3 c))

;; 實例：處理字串
(print (-> "  hello world  "
           (.strip)
           (.upper)
           (.replace "HELLO" "HI")))
;; 輸出: "HI WORLD"
```

### 最後一步插入宏 (->>)
將上一個結果作為下一個函數的**最後一個參數**。這在處理數據流時非常有用。
```hylang
;; 實例：計算 (range 10) 中偶數的平方和
(import [functools [reduce]])
(defn add [a b] (+ a b))

(print (->> (range 10)
            (filter (fn [x] (= (% x 2) 0)))
            (map (fn [x] (* x x)))
            (reduce add)))
;; 流程: range -> filter -> map -> reduce
```

## 2. 函數式工具
Hy 內建了許多經典的函數式工具：
*   `complement`: 返回一個函數的反邏輯函數。
*   `identity`: 返回參數本身。
*   `constantly`: 返回一個永遠返回固定值的函數。

```hylang
(setv is-not-even (complement (fn [x] (= (% x 2) 0))))
(print (list (filter is-not-even [1 2 3 4 5]))) ; [1, 3, 5]
```

## 3. 部分應用 (Partial Application)
雖然可以使用 `functools.partial`，但 Hy 有更簡潔的匿名函數寫法。
```hylang
(setv add-ten (fn [x] (+ 10 x)))
(print (add-ten 5)) ; 15
```
