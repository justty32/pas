# Hy 元編程（二）：宏的進階與實戰 (11_macros_advanced.md)

> 對齊版本：**Hy 1.3.0**（實測於 `projects/hy/`，2026-05-26 核對）。
> 前置：先讀 [`05_meta_programming.md`](05_meta_programming.md)（quoting、`defmacro`、`gensym`、`macroexpand`）。
> 凡標「✅ 實測」者皆以 `hy` 1.3 實際執行驗證。

本章處理「真正寫專案會踩到」的宏議題：編譯期/執行期的時間軸、跨檔案分享宏、reader macro、局部宏，以及一次性宏糖衣。

---

## 1. 心智模型：編譯期 vs 執行期（最重要的一節）

Hy 程式有**兩條時間軸**：

```mermaid
flowchart LR
    A[原始碼 .hy] -->|reader| B[model 樹]
    B -->|compiler：展開宏| C[Python AST]
    C -->|compile| D[bytecode .pyc]
    D -->|執行| E[結果]
    B -. 宏在這裡執行 .-> C
```

- **宏在「編譯期」執行**：當編譯器遇到 `(my-macro ...)`，它會*立刻呼叫* `my-macro` 函數來改寫程式碼。此時你的一般函數**還沒被定義**（它們要等執行期）。
- **函數在「執行期」執行**：bytecode 跑起來時。

由此推出兩條鐵則：

1. **宏要用 `require`，函數要用 `import`。** 因為宏必須在「編譯目標檔案」時就到位，這發生在執行期 `import` 之前。
2. **宏的程式體所依賴的東西，必須在編譯期就存在**（用 `eval-and-compile` 讓某段程式碼「編譯期也執行一次」）。

> 來源：`require` / `macroexpand` 的查找邏輯見 `projects/hy/hy/macros.py:189`、`:346`；宏存在模組的 `_hy_macros` 字典裡，以重整後的名稱為鍵。

---

## 2. `require`：載入別人的宏

`import` 載入的是執行期物件（函數、類別）；`require` 載入的是編譯期規則（宏）。語法與 `import` 平行，但**括號形狀已是 Hy 1.x 寫法**（無內層多餘括號）：

```hylang
;; 假設 mylib.hy 內有 (defmacro shout [x] `(.upper ~x)) 與 whisper

(require mylib [shout])            ; 取單一宏
(require mylib [shout :as yell])   ; 取別名         ✅ 實測
(require mylib *)                  ; 取全部（謹慎）  ✅ 實測
(require mylib [shout whisper])    ; 取多個

(print (shout "hi"))   ; ✅ → HI
(print (yell "ho"))    ; ✅ → HO
```

> ⚠️ **Hy 0.x → 1.x 變更**：舊寫法 `(require [mylib [shout]])` 在 1.x **會報語法錯誤**。新寫法把模組名直接放在第一位：`(require mylib [shout])`。`import` 同理（`(import math [sqrt])`）。

`:macros` 與匯出：在被 require 的模組裡用 `(export :macros [shout whisper])`（核心宏 `export`，`projects/hy/hy/core/macros.hy:137`）可控制 `(require mylib *)` 會帶出哪些宏。

---

## 3. 同檔案內定義並使用宏：`eval-and-compile`

如果宏與用它的程式在**同一個檔案**，`defmacro` 已自動處理（它內部用 `eval-and-compile` 包裝，讓宏定義在編譯期就生效）。但若你的**宏程式體**要呼叫某個輔助函數，那個函數也得在編譯期存在：

```hylang
;; ❌ 會壞：helper 是執行期函數，編譯展開 my-macro 時它還不存在
(defn helper [x] (* x x))
(defmacro my-macro [x] `(+ 1 ~(helper x)))   ; 編譯期呼叫 helper → NameError

;; ✅ 正解：用 eval-and-compile 讓 helper 在編譯期也被定義
(eval-and-compile
  (defn helper [x] (* x x)))
(defmacro my-macro [x] `(+ 1 ~(helper x)))
```

三個相關特殊形式（`projects/hy/hy/core/result_macros.py:117`）：

| 形式 | 編譯期執行 | 執行期保留 | 用途 |
|---|---|---|---|
| `eval-and-compile` | ✅ | ✅ | 宏輔助函數、常數，兩期都要 |
| `eval-when-compile` | ✅ | ❌ | 只在編譯期需要（不留進輸出） |
| `do-mac` | ✅（並把回傳的 model 當程式碼編譯） | — | 編譯期算好程式碼／常數再嵌入 |

```hylang
;; do-mac：把查表結果在「編譯期」算好，烤進 bytecode（執行期零成本）
(setv SQUARES (do-mac `[~@(lfor i (range 5) (* i i))]))
(print SQUARES)   ; ✅ 實測 → [0, 1, 4, 9, 16]
```

---

## 4. 一次性宏與 import 糖衣：`hy.R` / `hy.I`

不想為了用一次某模組的宏就寫 `require`？用 **`hy.R.模組.宏名`**（one-shot require，`projects/hy/hy/macros.py:373`）：

```hylang
(print (hy.R.hyrule.inc 5))   ; 等於先 require hyrule 的 inc 宏再用 ✅（需先 pip install hyrule）
```

同理，**`hy.I.模組.屬性`** 是 import 糖衣（避免把名稱帶進 scope，宏內尤其好用，`projects/hy/hy/__init__.py`）：

```hylang
(print (hy.I.math.sqrt 49))         ; ✅ → 7.0，等於臨時 import math 再取 sqrt
(print (hy.I.os/path.basename "a/b")) ; 模組名有點時用斜線：os/path
```

在寫宏時用 `hy.I` / `hy.R` 展開出的程式碼，可避免污染使用者的命名空間，是衛生宏的好搭檔。

---

## 5. Reader Macro：在「解析期」動手

一般宏作用在 model 樹上；**reader macro** 更早一步，作用在**字元流**上，由 `#名稱` 觸發。用核心宏 `defreader` 定義（`projects/hy/hy/core/macros.hy:51`），透過 `&reader` 取得 reader、`.parse-one-form` 讀下一個 form：

```hylang
(defreader up
  (setv form (.parse-one-form &reader))
  `(.upper ~form))

(print #up "hello")   ; ✅ 實測 → HELLO
```

跨檔案使用 reader macro 要用 `(require mod :readers [up])`。reader macro 適合做字面量 DSL（如自訂時間/向量字面量），但因為改變的是最底層的解析，**請節制使用**。

---

## 6. 局部宏：限定在一個 scope 內

在函數（或任何區塊）內 `defmacro`，這個宏只在該區塊可見——適合把區域樣板收斂在原地，不污染模組層級：

```hylang
(defn f []
  (defmacro local-double [x] `(* 2 ~x))   ; 只在 f 內有效
  (print (local-double 21)))              ; ✅ 實測 → 42
(f)
;; (local-double 1) 在 f 外呼叫會是 NameError
```

需要把目前可見的局部宏傳給 `hy.eval` 時，用核心宏 `(local-macros)` 取得它們的字典（`projects/hy/hy/core/macros.hy:112`）。

---

## 7. Compiler-aware 宏：拿到編譯器物件

若宏的**第一個參數名叫 `_hy_compiler`**，Hy 會自動把目前的編譯器物件傳進來（`projects/hy/hy/macros.py:403`），讓你存取檔名、丟語法錯誤、查 scope 等。核心宏 `defreader`、`export`、`get-macro` 都用這招。一般應用宏很少需要，但要寫框架級工具時很有用：

```hylang
(defmacro where-am-i [_hy_compiler]
  `(print "compiling:" ~(str _hy_compiler.filename)))
```

---

## 8. 實戰範例：計時宏

把「在 body 前後計時」這個橫切關注點包成宏（注意用 `hy.I` 取 `time` 不污染命名空間、用 `gensym` 保持衛生）：

```hylang
(defmacro with-timer [label #* body]
  (setv start (hy.gensym "start")
        result (hy.gensym "result"))
  `(do
     (setv ~start (hy.I.time.perf-counter))
     (setv ~result (do ~@body))
     (print f"{~label} 耗時：{(- (hy.I.time.perf-counter) ~start):.4f} 秒")
     ~result))

(with-timer "大迴圈"
  (sum (lfor x (range 1000000) (* x x))))   ; ✅ 回傳總和並印出耗時
```

要點回顧：`#* body` 收集多個表達式 → `~@body` 攤平進 `do`；`gensym` 避免 `start`/`result` 撞名；`hy.I.time` 避免 import 污染；最後 `~result` 讓宏「有回傳值」。

---

## 9. 常見陷阱與最佳實踐

| 陷阱 | 症狀 | 解法 |
|---|---|---|
| 用 `import` 載入宏 | 宏「不存在」/ 被當函數找 → NameError | 改用 `require` |
| 宏體呼叫未在編譯期定義的函數 | 編譯期 NameError | 把該函數包進 `eval-and-compile` |
| 變數捕獲 | 宏內 `tmp` 蓋掉使用者的 `tmp` | 用 `(hy.gensym)` |
| 直接傳運算子當函數，如 `(reduce + xs)` | `NameError: hyx_Xplus_signX` | `+` 是編譯期宏，需 `(import hy.pyops *)` 取得函數版 |
| 兩引數 `if` | 語法錯誤 | `if` 必須三引數，或改用 `when` |
| 以為 `->`/`unless`/`inc` 是核心 | NameError | 它們在 **hyrule**：宏 `require`、函數 `import`（見下表） |
| 該用函數卻寫成宏 | 難除錯、無法當值傳遞 | 只在需要控制求值/生成語法時才用宏 |

> 運算子非函數：`+ - * / < =` 等在 Hy 是編譯期宏，不能當值傳遞。`(import hy.pyops *)` 後即可 `(reduce + [1 2 3])`（`projects/hy/hy/pyops.hy`）。✅ 實測。

### 核心 vs hyrule 速查（宏用 require、函數用 import）

| 名稱 | 在哪 | 載入方式 |
|---|---|---|
| `if` `when` `cond` `for` `while` `setv` `defn` `fn` `defmacro` `import` `require` `let` `match` | **Hy 核心**（特殊形式/核心宏） | 內建，免載入 |
| `defreader` `export` `get-macro` `local-macros` `eval-and-compile` `do-mac` | **Hy 核心宏** | 內建 |
| `hy.gensym` `hy.macroexpand` `hy.read` `hy.eval` `hy.repr` `hy.mangle` | **Hy 核心函數** | `hy.` 命名空間，免載入 |
| `->` `->>` `as->` `doto` `unless` `defmain` `comment` `ncut` … | **hyrule（宏）** | `(require hyrule [->])` |
| `inc` `dec` `none?` `even?` `odd?` `empty?` `coll?` `flatten` … | **hyrule（函數）** | `(import hyrule [inc])` |

安裝 hyrule：`pip install hyrule`（本工作區已驗證 hyrule 1.0.1 可用）。

---

## 10. 小結

- 宏跑在編譯期 → 用 `require` 載入、依賴要 `eval-and-compile`。
- `hy.R` / `hy.I` 寫一次性宏與避免命名污染。
- reader macro（`defreader`/`#tag`）在解析期動手，節制使用。
- 局部宏收斂樣板；`_hy_compiler` 給框架級工具。
- 牢記核心 vs hyrule 分工，別把 `->`/`inc` 當內建。

回到 [`00_overview.md`](00_overview.md) 看整體學習路徑。
