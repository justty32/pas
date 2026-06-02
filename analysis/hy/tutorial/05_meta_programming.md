# Hy 元編程（一）：宏的基礎 (05_meta_programming.md)

> 對齊版本：**Hy 1.3.0**（實測於 `projects/hy/`，2026-05-26 核對）。
> 本系列的進階主題（編譯期/執行期模型、跨檔案 `require`、reader macro、局部宏、`hy.R`/`hy.I`）見 [`11_macros_advanced.md`](11_macros_advanced.md)。
> 凡標「✅ 實測」的範例皆以 `hy` 1.3 實際執行驗證過輸出。

宏 (Macro) 是 Hy 的靈魂：它讓你在**編譯期**改寫程式碼，等於用 Hy 擴充 Hy 自己的語法。本章先打穩基礎。

---

## 1. 為什麼需要宏？函數做不到什麼

函數在**執行期**接收「已經求值完的值」。宏在**編譯期**接收「還沒求值的程式碼」（以 model 形式），可以決定要不要、以什麼順序求值它們，甚至生成全新的程式碼。

判斷準則：
- 只是要算一個值 → 用**函數**。
- 需要改變求值順序、延後求值、引入新語法、生成重複樣板 → 才用**宏**。

舉例：你無法用函數寫出 `unless`，因為函數會在進入前就把 body 求值完。`unless` 必須是宏。（順帶一提，Hy 1.x 的核心**不再內建** `unless`，它被移到 `hyrule` 套件——所以下面自己實作一個正好是最佳教材。詳見 [`11_macros_advanced.md`](11_macros_advanced.md) 的核心/hyrule 分工表。）

---

## 2. 程式即資料：先認識 model

Hy 原始碼經 reader 解析後，會變成一棵 **model 樹**（`hy.models.*`），宏操作的就是這棵樹。常見型別：

| Model | 對應語法 | 說明 |
|---|---|---|
| `hy.models.Symbol` | `foo`、`+` | 符號（識別字／運算子名） |
| `hy.models.Expression` | `(f a b)` | 括號表達式（呼叫／特殊形式） |
| `hy.models.List` | `[1 2 3]` | 方括號列表（也用於參數列、for 子句） |
| `hy.models.Integer/Float/String` | `1`、`1.5`、`"x"` | 字面量 |
| `hy.models.Keyword` | `:foo` | 關鍵字 |

用 `hy.read` 把字串解析成 model（不求值），即可窺見結構（來源：`projects/hy/hy/models.py`）：

```hylang
(print (hy.read "(+ 1 x)"))
;; ✅ 實測輸出：
;; hy.models.Expression([
;;   hy.models.Symbol('+'),
;;   hy.models.Integer(1),
;;   hy.models.Symbol('x')])
```

關鍵心法：`(+ 1 x)` 在宏眼中不是「3」，而是一個長度為 3 的 `Expression`，第一個元素是符號 `+`。宏就是在改寫這種樹。

---

## 3. 引用 (Quoting)：取得程式碼而非求值

| 語法 | 名稱 | 作用 |
|---|---|---|
| `'expr` | quote | 「不要求值，把這段程式碼當資料給我」 |
| `` `expr `` | quasiquote | 同 quote，但允許 `~` / `~@` 插入動態內容 |
| `~x` | unquote | 在 quasiquote 內「切回求值模式」，插入 `x` 的值 |
| `~@xs` | unquote-splice | 把 `xs` 這個序列「攤平」插入 |

```hylang
(setv x 10  xs [1 2 3])
(print '(+ 1 x))     ; ✅ 不求值 → Expression([Symbol('+'), Integer(1), Symbol('x')])
(print `(+ 1 ~x))    ; ✅ 插值   → Expression([Symbol('+'), Integer(1), Integer(10)])
(print `(+ ~@xs))    ; ✅ 攤平   → Expression([Symbol('+'), Integer(1), Integer(2), Integer(3)])
```

`~`（插單一個值）與 `~@`（把序列攤平成多個元素）的差別是宏裡最常用、也最容易搞錯的一組。`~@body` 幾乎一定搭配 `&rest` 收集到的多個 body 表達式。

> reader 對應：`'`→`quote`、`` ` ``→`quasiquote`、`~`→`unquote`、`~@`→`unquote-splice`，定義於 `projects/hy/hy/reader/hy_reader.py:336`。

---

## 4. 第一個宏：`defmacro`

宏是「程式碼工廠」：吃進 model，吐出 model，編譯器再把吐出的 model 編譯成 Python。

### 範例：實作 `unless`（= `if` 反向）

```hylang
(defmacro unless [condition #* body]
  `(if (not ~condition)
       (do ~@body)
       None))            ; ⚠️ Hy 1.x 的 if 必須有三個引數（見下方注意事項）

(setv x 5)
(unless (> x 10)
  (print "x 不大於 10")
  (print "這就是 unless 的威力"))
;; ✅ 實測：兩行都印出
```

要點：
- `#* body` 收集「剩餘所有表達式」成一個序列（**取代 Hy 0.x 的 `&rest body`**，後者在 1.x 已移除）。
- `~condition` 插入單一條件 model；`~@body` 把收集到的多個 body 攤平進 `do`。

> ⚠️ **`if` 必須三引數**：Hy 1.x 的 `if` 是 `(if 條件 then else)`，**沒有 else 也要寫**（常填 `None`）。寫成兩引數 `(if c then)` 會直接報語法錯誤（`projects/hy/hy/core/result_macros.py:736` 規定恰好三個 form）。只想要「條件成立才做」時，請改用核心宏 `when`：`(when c ...)`。

### 宏的參數列跟函數一樣強

`defmacro` 的參數列支援所有現代 lambda list 特性：`#*`（剩餘位置參數）、`#**`（剩餘關鍵字參數）、`/`（純位置）、`[name default]`（預設值）。

```hylang
(defmacro my-print [msg [end "\n"]]
  `(print ~msg :end ~end))
```

---

## 5. 衛生 (Hygiene) 與 `gensym`

Hy 的宏**不是完全衛生**的：宏展開後產生的變數名，可能與使用者程式碼裡的同名變數打架（變數捕獲）。

### 問題示範

```hylang
(defmacro bad-swap [a b]
  `(do (setv tmp ~a)      ; 這個 tmp 會污染外部
       (setv ~a ~b)
       (setv ~b tmp)))

(setv x 1  tmp 99)
(bad-swap x tmp)          ; 展開後 setv tmp ... 把使用者的 tmp 蓋掉 → 邏輯錯誤
```

### 解法：`(hy.gensym)` 產生唯一名稱

```hylang
(defmacro good-swap [a b]
  (setv g (hy.gensym))    ; 在宏的「執行期」（= 編譯期）產生一個保證唯一的符號
  `(do (setv ~g ~a)
       (setv ~a ~b)
       (setv ~b ~g)))
;; ✅ (hy.gensym) → _hy_gensym__1 ；(hy.gensym "tmp") → _hy_gensym_tmp_2
```

`(hy.gensym)` 回傳一個獨一無二的 `Symbol`，避免與任何使用者變數衝突；可給字串前綴方便除錯（`(hy.gensym "tmp")`）。`hyrule` 另提供 `defmacro/g!` 等糖衣，能用 `g!name` 自動 gensym（見進階篇）。

---

## 6. 除錯宏：看清楚到底展開成什麼

| 工具 | 作用 |
|---|---|
| `(hy.macroexpand-1 'form)` | 只展開**最外層一次**——看單一宏做了什麼 |
| `(hy.macroexpand 'form)` | 反覆展開到不能再展——看最終結果 |
| `hy2py file.hy` | 直接看整檔編譯成的 Python 原始碼 |

```hylang
(print (hy.macroexpand-1 '(when c a b)))
;; ✅ 實測 → (if c (do a b) None)
;; 一眼看出 when 就是「填了 None 當 else 的 if」
```

```hylang
(defmacro twice [x] `(do ~x ~x))
(print (hy.macroexpand '(twice (foo))))
;; ✅ 展開 → (do (foo) (foo))
```

`hy2py` 是理解任何宏（與名稱重整）最快的方法：

```bash
hy2py myfile.hy        # 印出等效 Python 原始碼
```

> 注意 `hy.macroexpand` 是 `hy.` 命名空間下的函數（不是裸名 `macroexpand`），引數要傳 **model**（記得加 `'` 引用）。

---

## 7. 小結與下一步

- 宏在**編譯期**改寫程式碼樹；函數在執行期處理值。
- 用 `` ` `` / `~` / `~@` 組裝要回傳的程式碼。
- 用 `(hy.gensym)` 維持衛生。
- 用 `hy.macroexpand-1` / `hy2py` 除錯。

進階主題——**為什麼宏要 `require` 不能 `import`**、跨檔案分享、reader macro、局部宏、`hy.R`/`hy.I` 一次性宏、compiler-aware 宏與實戰範例——全部在 [`11_macros_advanced.md`](11_macros_advanced.md)。
