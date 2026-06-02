# Hy 語法細節與 Python 互操作性 (06_details.md)

本章節介紹 Hy 在底層如何處理名稱、類定義以及與 Python 的細微差異。

## 1. 名稱重整 (Mangling)
為了讓 Lisp 風格的符號能對應到合法的 Python 識別字，Hy 會進行「重整」。**Hy 1.x 採 Unicode 字元名 + `hyx_` 前綴的通用規則**，而非舊版的特例（`?`→`is_`、`->`→`to_` 等規則已**全部移除**，請忘掉）。

| Hy 符號 | Python 識別字 | 規則 |
| :--- | :--- | :--- |
| `my-variable` | `my_variable` | 連字號 → 底線（首字保留） |
| `valid?` | `hyx_validXquestion_markX` | 非法字元換成 `X+Unicode 名+X` |
| `*cache*` | `hyx_XasteriskXcacheXasteriskX` | 星號不被剝離，照規則重整 |
| `str->int` | `hyx_str_XgreaterHthan_signXint` | `-` 轉 `_`，`>` 變 `XgreaterHthan_signX` |
| `🦑` | `hyx_XsquidX` | emoji 也照 Unicode 名 |

驗證方式（任何時候不確定都可實測）：

```hylang
(print (hy.mangle 'valid?))      ; ✅ → hyx_validXquestion_markX
(print (hy.mangle 'my-var))      ; ✅ → my_var
(print (hy.unmangle "hyx_validXquestion_markX"))  ; ✅ → valid?
```

或 `hy2py file.hy` 看完整編譯結果。

> 規則來源：`projects/hy/hy/reader/mangling.py:9`。要點：(1) 首字以外的 `-` 換 `_`；(2) 若仍非合法識別字，整體加 `hyx_` 前綴，每個非法字元用 `X{Unicode 名}X` 包裹；(3) NFKC 正規化。整個流程是冪等的：`(hy.mangle (hy.mangle x))` = `(hy.mangle x)`。

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
