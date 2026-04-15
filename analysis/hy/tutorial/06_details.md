# Hy 語法細節與 Python 互操作性 (06_details.md)

本章節介紹 Hy 在底層如何處理名稱、類定義以及與 Python 的細微差異。

## 1. 名稱重整 (Mangling)
為了讓 Lisp 風格的符號能在 Python 中運行，Hy 會進行「重整」。

| Hy 符號 | Python 變量名 | 說明 |
| :--- | :--- | :--- |
| `my-variable` | `my_variable` | 連字號轉底線 |
| `valid?` | `is_valid` | 問號結尾轉 `is_` 前綴 |
| `*star*` | `star` | 移除裝飾性星號 |
| `->list` | `to_list` | `->` 轉 `to_` |

```hylang
(defn even? [x] (= (% x 2) 0))
;; 在 Python 中調用時： even_query (基本規則) 或根據最新規則重整
```

## 2. 萬物皆表達式 (Everything is an Expression)
在 Hy 中，幾乎所有東西都會返回一個值。
```hylang
;; 在 Python 中，print(if True: 1) 是語法錯誤
;; 在 Hy 中，這非常自然：
(print (if True "A" "B"))

;; setv 也返回被賦的值
(print (setv a 100)) ; 輸出 100
```

## 3. 定義類 (defclass)
Hy 的 `defclass` 與 Python 的 `class` 完美對應。

```hylang
(defclass Animal []
  (defn __init__ [self name]
    (setv self.name name))
  
  (defn talk [self]
    (print f"{self.name} 正在發出聲音")))

(defclass Dog [Animal]  ; 繼承 Animal
  (defn talk [self]
    (print f"{self.name} 在汪汪叫")))

(setv my-dog (Dog "小白"))
(.talk my-dog) ; 輸出: 小白 在汪汪叫
```

## 4. 方法調用的三種形式
假設我們有一個字串對象 `s`。

1.  **Python 風格**：`(s.upper)`
2.  **Lisp 風格**：`(.upper s)` (推薦，更符合 Lisp 審美)
3.  **帶參數調用**：`(.join ", " ["a" "b"])`

## 5. 與 Python 的語義差異
*   **= 符號**：在 Hy 中，`(= a b)` 是比較（等於），`setv` 才是賦值。
*   **None 的求值**：在 REPL 中，如果結果是 `None`，通常不會印出任何內容。
*   **邏輯真值**：Hy 遵循 Python 的真值判定（空列表、0、None 皆為假）。

## 6. 結論
Hy 是一個兼具 Lisp 靈活性與 Python 實用性的語言。透過這系列教學，你現在已經具備了開發 Hy 應用程式的基礎知識。繼續探索，享受「編程的快樂」！
