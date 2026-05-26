# ADR 0001：自製 `defgeneric` / `defmethod` 並支援 `:before` / `:after` / `:self` 方法組合

> 取代先前的「用 `functools.singledispatch`」案。改為「全面對齊 c-mera」的指示要求泛型函式與方法組合的形狀與 CLOS / c-mera 一致。

## 背景

c-mera 的核心抽象 `traverser` 是 CLOS 三參數泛型函式 `(traverser tr node level)`（`projects/c-mera/src/c-mera/traverser.lisp:6`）。Pretty-printer 進一步用 `defprettymethod :before/:after/:self` 三種限定詞註冊方法（`projects/c-mera/src/c-mera/pretty.lisp`）。`renamer`、`if-blocker` 等所有 Pass 都靠這套基礎。

對映到 hymera 必須提供：

1. `defgeneric NAME [params]` —— 宣告泛型函式
2. `defmethod NAME [:qualifier] [(var type) ...] body...` —— 註冊方法
3. 標準方法組合：
   - `:before` 方法：**全部依序執行**，最具體優先
   - 主要方法（primary）：**只執行最具體一個**
   - `:after` 方法：**全部依序執行**，最不具體優先
   - `:self` 方法（c-mera 特有）：**若存在則完全接管**，跳過 :before/primary/:after
4. 多重派發：c-mera 用 `(traverser-class, node-class)` 雙派發

## 決策

**自製 `defgeneric` / `defmethod` 宏與一個 `GenericFunction` 執行期類別，支援上述 4 點。**

實作骨架（虛擬程式碼）：

```hylang
;; src/hymera/generic.hy
(defclass GenericFunction []
  (defn __init__ [self name]
    (setv self.name name)
    (setv self.methods {}))      ; key: (qualifier, type-tuple) → fn

  (defn add-method [self qualifier types fn]
    (setv (get self.methods #(qualifier types)) fn))

  (defn __call__ [self #* args]
    (setv types (tuple (lfor a args (type a))))
    ;; 1. 若有 :self 方法 applicable → 接管
    (setv self-fn (.find-applicable self ":self" types))
    (when self-fn (return (self-fn #* args)))
    ;; 2. :before（全部，最具體→最不具體）
    (for [fn (.find-all-applicable self ":before" types :most-specific-first True)]
      (fn #* args))
    ;; 3. primary（只執行最具體一個）
    (setv prim (.find-applicable self None types))
    (setv result (when prim (prim #* args)))
    ;; 4. :after（全部，最不具體→最具體）
    (for [fn (.find-all-applicable self ":after" types :most-specific-first False)]
      (fn #* args))
    result)

  (defn find-applicable [self qualifier types]
    "依 MRO 從最具體往上找第一個註冊的方法。")

  (defn find-all-applicable [self qualifier types [most-specific-first True]]
    "依 MRO 收集所有註冊的方法。"))

;; defgeneric / defmethod 是宏，把對應 GenericFunction 物件存到模組命名空間
(defmacro defgeneric [name params]
  `(setv ~name (GenericFunction ~(str name))))

(defmacro defmethod [name #* rest]
  "(defmethod walk :before ((tr Renamer) (n Ident)) body...)"
  ...)
```

**多重派發策略**：用 Python class MRO。對每個方法註冊的型別 tuple，檢查「每個位置上，呼叫時實際型別是否為註冊型別的子類」。所有位置都過 → applicable。多個 applicable 方法時，比較其 specificity（型別 tuple 在 MRO 上的位置和）。

**對齊 c-mera 的限制**：
- 只支援 **位置參數** 的型別派發（不做 keyword param 派發）
- 不實作 `:around` 與 `call-next-method`（c-mera 對 traverser 不需要這兩者）
- 不實作 `eql-specializer`（直接派發到值），c-mera 也不用

## 後果

### 正面

- API 與 c-mera 對齊：使用者讀 c-mera 的書寫慣例可以直接套用。
- 行為一致：`:before`/`:after`/`:self` 限定詞語意完全照 CLOS 標準方法組合。
- 多重派發為 traverser 雙派發（`(traverser-instance, node)`）打好基礎，未來實作可控。

### 負面

- **實作成本**：相比 `singledispatch`，要多寫 ~100-150 行核心 + 測試。
- **效能**：每次呼叫要走 MRO 計算 applicable methods；可能比 `singledispatch` 慢。預期透過快取（key by `types` tuple）緩解。
- **除錯難度**：方法組合多層，使用者不熟 CLOS 時，stack trace 可能不直觀。緩解：在 `GenericFunction` 加 `dispatch-trace` 模式列出實際呼叫順序。

## 連結

- c-mera 對應：`projects/c-mera/src/c-mera/traverser.lisp:1-30`、`projects/c-mera/src/c-mera/pretty.lisp:1-30`
- hymera 設計：`docs/03_traverser_and_passes.md`、`docs/04_emit_interface.md`
- hymera 實作位置：`src/hymera/generic.hy`
- CLOS 標準方法組合：[CLHS 7.6.6.2](http://www.lispworks.com/documentation/HyperSpec/Body/07_ffb.htm)
