# Hy 函數式編程與線程宏 (07_functional_threading.md)

> 對齊版本：**Hy 1.3.0**。本章重點：**線程宏 (`->`/`->>`/`as->`/`doto`) 與許多函數式工具在 Hy 1.x 已不在核心，全部移到了 `hyrule` 套件**。

## 0. 前置：安裝並 require hyrule

```bash
pip install hyrule
```

```hylang
;; 宏要用 require、函數要用 import（規則見 04 與 11）
(require hyrule [-> ->> as-> doto])
(import hyrule [inc dec])
```

`hyrule` 是 Hy 的官方擴充標準函式庫。本章後續所有範例都假設你已照上面 require/import。

---

## 1. 線程宏 (Threading Macros)

巢狀呼叫 `func3(func2(func1(data)))` 在 Hy 用線程宏拉平。

### 1.1 第一槽插入：`->`

把上一步結果塞進下一個呼叫的**第一個參數位置**：

```hylang
;; 等價於 (.replace (.upper (.strip "  hello world  ")) "HELLO" "HI")
(print (-> "  hello world  "
           (.strip)
           (.upper)
           (.replace "HELLO" "HI")))
;; ✅ → HI WORLD
```

```hylang
(print (-> 5 (+ 3) (* 2)))   ; ✅ → 16   ((5+3)*2)
```

### 1.2 最後一槽插入：`->>`

把上一步結果塞進**最後一個參數位置**——適合資料管線（map/filter/reduce 慣常吃 collection 在最後）。

```hylang
(import functools [reduce])

;; 0..9 中偶數的平方和
(print (->> (range 10)
            (filter (fn [x] (= (% x 2) 0)))
            (map (fn [x] (* x x)))
            (reduce + 0)))   ; ✅ → 120

;; 注意：直接傳 + 為函數需要 hy.pyops（運算子本身是宏）
;; 若無 (import hy.pyops *)，可用 (reduce (fn [a b] (+ a b)) ... 0)
```

### 1.3 指定槽位：`as->`

更彈性，給定一個臨時名稱，自己決定塞哪：

```hylang
(print (as-> [1 2 3 4] $
              (filter (fn [x] (> x 1)) $)
              (list $)
              (sum $)))    ; ✅ → 9
```

### 1.4 副作用串連：`doto`

依序對同一個物件呼叫一連串方法，回傳物件本身：

```hylang
(setv xs (doto []
           (.append "a")
           (.append "b")
           (.append "c")))
(print xs)   ; ✅ → ['a', 'b', 'c']
```

---

## 2. 運算子當函數：`hy.pyops`

`+ - * / < = and or not` 等在 Hy 是**編譯期宏**，無法直接當值傳入 `map`/`filter`/`reduce`。要拿到函數版，從 `hy.pyops` 取：

```hylang
(import hy.pyops *)
(import functools [reduce])
(print (reduce + [1 2 3 4]))   ; ✅ → 10
```

來源：`projects/hy/hy/pyops.hy`。

---

## 3. 常用的 hyrule 函數式工具

下列**全部來自 `hyrule`**（不是 Hy 核心）：

```hylang
(import hyrule [inc dec
                comp constantly identity
                none?])

(print (inc 9))                    ; ✅ → 10
(print (dec 9))                    ; ✅ → 8
(print ((constantly 42) 1 2 3))    ; ✅ → 42（不論參數永遠回 42）
(print ((identity) 5) )            ; identity 回傳原值
(print (none? None))               ; ✅ → True
```

`comp` 做函數組合：`((comp f g h) x)` = `(f (g (h x)))`。

> 完整 hyrule 函數列表見 hyrule 文件；本章只列教學常用的。

---

## 4. 推薦寫法

- 短鏈、第一槽插：用 `->`
- 資料管線（filter/map/reduce）：用 `->>`
- 同一物件連續方法呼叫：用 `doto`
- 需要中間取個名再決定塞哪：用 `as->`
- 真的會混淆讀者時：寫普通巢狀，不要硬套線程宏。
