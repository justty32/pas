# Hy 核心 vs hyrule 速查 (10_hy_core_ref.md)

> 對齊版本：**Hy 1.3.0** / **hyrule 1.0.1**（2026-05-26 實測）。
>
> 本檔修正過去把 `inc`/`dec`/`none?`/`even?`/`empty?` 標為「Hy 核心」的錯誤——**它們全部在 hyrule，不在 Hy 核心**。Hy 1.x 把核心瘦身了不少，許多舊朋友請改去 hyrule 找。

---

## 1. 一句話原則

| 載入哪種 | 用什麼 |
|---|---|
| 宏（編譯期規則） | `(require 模組 [...])` |
| 函數／類別／值（執行期物件） | `(import 模組 [...])` |

兩條時間軸，兩種載入機制，**不能混用**。詳見 [`11_macros_advanced.md`](11_macros_advanced.md) §1。

---

## 2. Hy 核心（內建，免載入）

### 2.1 特殊形式與核心宏

流程／賦值／資料結構：
`if`（必須三引數）、`when`、`cond`、`do`、`setv`、`setx`、`del`、`let`、`global`、`nonlocal`、`get`、`cut`、`unpack-iterable`/`unpack-mapping`（即 `#*`/`#**`）。

函數／類別／模組：
`fn`、`defn`、`defclass`、`return`、`yield`、`await`、`defmacro`、`defreader`、`get-macro`、`local-macros`、`export`、`import`、`require`、`annotate`、`#^`。

控制流／例外：
`for`、`while`、`break`、`continue`、`with`、`try`/`except`/`else`/`finally`、`raise`、`match`、`assert`、`chainc`、`pragma`。

推導式：
`lfor`、`sfor`、`dfor`、`gfor`。

引用：
`quote`（`'`）、`quasiquote`（`` ` ``）、`unquote`（`~`）、`unquote-splice`（`~@`）。

編譯期工具：
`eval-and-compile`、`eval-when-compile`、`do-mac`、`py`、`pys`。

> 完整清單見 `projects/hy/hy/core/result_macros.py`（特殊形式）與 `projects/hy/hy/core/macros.hy`（核心宏）。

### 2.2 核心函數（`hy.*` 命名空間）

| 名稱 | 作用 |
|---|---|
| `hy.eval` | 對 **model**（不是字串）求值 |
| `hy.read` | 把字串解析成單一 model |
| `hy.read-many` / `hy.read_many` | 把字串解析成 model 序列 |
| `hy.mangle` / `hy.unmangle` | 名稱重整／反重整 |
| `hy.gensym` | 產生唯一符號（衛生宏必備） |
| `hy.macroexpand` / `hy.macroexpand-1` | 展開宏 |
| `hy.repr` / `hy.repr-register` | Hy 風格的字串表示 |
| `hy.models.*` | 各種 model 型別（Symbol、Expression、List …） |
| `hy.I.模組.屬性` | 一次性 import 糖衣 |
| `hy.R.模組.宏` | 一次性 require 糖衣 |
| `hy.pyops.*` | 運算子的函數版本（`+ - * /` 等） |

### 2.3 REPL 專屬

| 名稱 | 作用 |
|---|---|
| `*1` `*2` `*3` | 最近三次運算結果 |
| `*e` | 最近一次未捕捉的例外 |
| `_hy_repl` | 目前 REPL 物件 |

來源：`projects/hy/hy/repl.py:293`。

---

## 3. hyrule（需 `pip install hyrule` 後 require/import）

`hyrule` 是官方擴充標準函式庫，把 Hy 0.x 核心曾經有過、但 1.x 移出的功能（與一些好用工具）整理在這裡。

### 3.1 hyrule 宏（用 `require`）

```hylang
(require hyrule [-> ->> as-> doto
                 unless comment defmain
                 ncut ignore branch
                 do-n list-n
                 cfor
                 with-gensyms defmacro/g!])
```

| 宏 | 用途 |
|---|---|
| `->`、`->>`、`as->` | 線程宏（第一槽／最後槽／指定位置） |
| `doto` | 對同一物件連串呼叫並回傳該物件 |
| `unless` | `if not` 的糖衣 |
| `comment` | 整段註解掉，不參與編譯 |
| `defmain` | 自動產生 `if __name__ == "__main__"` 入口 |
| `ncut` | numpy 風格切片 |
| `branch`、`ebranch` | 多分支匹配 |
| `do-n`、`list-n` | 重複 N 次／取 N 個結果 |
| `cfor` | 條件 for（同時當 filter 與 transformer） |
| `with-gensyms`、`defmacro/g!` | 衛生宏輔助 |

### 3.2 hyrule 函數（用 `import`）

```hylang
(import hyrule [inc dec
                comp constantly identity
                none? coll? empty?
                flatten butlast rest])
```

| 函數 | 用途 |
|---|---|
| `inc`、`dec` | 加一／減一 |
| `comp` | 函數組合 |
| `constantly`、`identity` | 經典函數式工具 |
| `none?` | 是否為 `None`（注意 Hy 1.x 起 `?` 不再特殊重整） |
| `coll?` | 是否為集合（list、tuple、set、dict） |
| `empty?` | 是否為空 |
| `flatten`、`butlast`、`rest` | 序列輔助 |

> hyrule 完整參考見其官方文件；上表只列出常用項目。

---

## 4. 我該找哪裡？決策表

| 我想… | 在哪 | 怎麼載入 |
|---|---|---|
| 寫 `if`/`when`/`cond` | 核心 | 內建 |
| 寫 `for`/`while`/`try` | 核心 | 內建 |
| 用 `lfor`/`dfor`/`sfor`/`gfor` | 核心 | 內建 |
| 用線程宏 `->`/`->>` | hyrule | `(require hyrule [-> ->>])` |
| 用 `unless` 或 `defmain` | hyrule | `(require hyrule [unless defmain])` |
| 用 `inc`/`dec`/`none?` | hyrule | `(import hyrule [inc dec none?])` |
| 把 `+` `*` 當函數值傳 | `hy.pyops` | `(import hy.pyops *)` |
| 衛生宏取得唯一符號 | 核心 | `(hy.gensym)` |
| 展開宏看結果 | 核心 | `(hy.macroexpand-1 '...)` |
| 把字串解析成 Hy form | 核心 | `(hy.read "(+ 1 2)")` |

---

## 5. 從 0.x 過渡的速查

| 0.x 寫法 | 1.x 寫法 | 備註 |
|---|---|---|
| `(import [m [a b]])` | `(import m [a b])` | 內層方括號移除 |
| `(require [m [x]])` | `(require m [x])` | 同上 |
| `(defn f [a &rest r])` | `(defn f [a #* r])` | `&rest` 移除 |
| `(defn f [a &kwargs k])` | `(defn f [a #** k])` | `&kwargs` 移除 |
| `(defn f [&optional [a 1]])` | `(defn f [[a 1]])` | 直接 `[name default]` |
| `(if c then)` | `(when c then)` 或 `(if c then None)` | `if` 強制三引數 |
| `async-defn` | `(defn :async ...)` | 用關鍵字標註 |
| `(yield-from x)` | `(yield :from x)` | 同上 |
| `with-decorator` | `(defn [deco] name [] ...)` | 裝飾器寫在名稱前的方括號內 |
| `^int x` | `#^ int x` | 註解改用 reader macro |
| `valid?` → `is_valid` | `valid?` → `hyx_validXquestion_markX` | `?`/`!`/`->` 等不再有特殊重整 |
| `->`/`->>`/`unless` 是核心 | 移至 hyrule | 需 `require hyrule` |
| `inc`/`dec`/`none?` 是核心 | 移至 hyrule | 需 `import hyrule` |
