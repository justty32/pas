# ADR 0003：v1 實作 proxy 節點機制（`with-proxynodes` / `make-proxy` / `del-proxy` / `defproxyprint`）

> 取代先前「v1 跳過 proxy 節點」案。改為「全面對齊 c-mera」的指示要求。

## 背景

c-mera 用 proxy 節點處理「不屬於任何單一節點的列印細節」（`projects/c-mera/src/c-mera/pretty.lisp:62-75`）。代表例：型別後加空白、運算子的優先序括號、宣告之間的分隔符。

c-mera API（`projects/c-mera/src/c-mera/traverser.lisp:30-74`）：
- `(with-proxynodes (NAME ...) body)` — 在 body 內動態註冊 proxy 類別
- `(make-proxy slot proxy-class)` — 把當前節點的 `slot` 槽位包成 proxy
- `(del-proxy slot)` — 解包
- `(defproxyprint :before/:after PROXY-CLASS body)` — 註冊 proxy 的列印方法

## 決策

**v1 實作上述 4 個 API，語意與 c-mera 對應。**

### 實作骨架

```hylang
;; src/hymera/ast/base.hy 內
(defclass Proxy [Node]
  "Proxy 節點基底。"
  (defn __init__ [self wrapped]
    (setv self.wrapped wrapped))
  (setv _subnode_slots #("wrapped")))   ; 預設遍歷會走 wrapped

;; defproxy 宏：跟 defnode 一樣，但繼承 Proxy
(defmacro defproxy [name #* slots]
  `(defclass ~name [Proxy]
     ~@(lfor s slots `(setv ~s None))
     (setv _value_slots ~(tuple (lfor s slots (str s))))
     (setv _subnode_slots #("wrapped"))))

;; src/hymera/emit/core.hy 內
(defmacro with-proxynodes [names #* body]
  "建立區域範圍可見的 proxy 類別；離開時自動清除註冊。"
  ;; 用一個 emitter 屬性 ._proxy_registry：dict[str, type]
  ;; 進入時把 names 對映到動態建立的型別並 push 到 stack；
  ;; 離開時 pop。
  ...)

(defn make-proxy [emitter slot-name proxy-class]
  "把目前正在列印的節點之 slot 槽位包成 proxy。
   實作上 mutating；列印階段 AST 已穩定，可變更。"
  (setv current emitter.current-node)
  (setv original (getattr current slot-name))
  (setattr current slot-name (proxy-class original)))

(defn del-proxy [emitter slot-name]
  "解包：把 proxy 換回原節點。"
  (setv current emitter.current-node)
  (setv wrapped (. (getattr current slot-name) wrapped))
  (setattr current slot-name wrapped))

(defmacro defproxyprint [qualifier proxy-class #* body]
  "等價於 (defprettymethod qualifier proxy-class body)。"
  `(defprettymethod ~qualifier ~proxy-class ~@body))
```

### 使用範例：型別後加空白

對映 `projects/c-mera/src/c/pretty.lisp:62-75`：

```hylang
(with-proxynodes (type-space)
  (defproxyprint :after type-space
    (.write emitter " "))

  (defprettymethod :before Declaration
    (make-proxy emitter "type" type-space))

  (defprettymethod :after Declaration
    (del-proxy emitter "type")))
```

效果：每次列印 Declaration 時，type 槽位被臨時包成 `type-space` proxy；走完 type 子節點後 proxy 的 `:after` 印一個空白。

## 設計細節

### 「列印階段可以變更 AST」

c-mera 的 traverser 在 pretty-printer 跑時會就地包/解 proxy。這違反「AST 不可變」原則。hymera 選擇**只在 Emitter 階段允許就地修改**——前面的 Pass 全部走「回傳新節點」風格，到 Emitter 是 AST 已穩定，這時 mutating 安全。

### 動態註冊與多執行緒

`with-proxynodes` 用 `contextvars.ContextVar`（執行緒安全）儲存目前 proxy registry，避免並行使用 Emitter 時撞名。

## 後果

### 正面
- API 與 c-mera 1:1，所有 pretty.lisp 慣用法都可直接搬。
- 列印程式碼可分層：節點主體做骨架、proxy 做裝飾。
- 加新「橫切列印關注」不必動主節點 emit 函式。

### 負面
- **多一層基礎設施**：使用者要懂 proxy 概念才能讀懂某些列印方法。緩解：在 `docs/04_emit_interface.md` 加詳細範例。
- **動態建立型別**：`type(name, (Proxy,), {})` 在執行期建立 class，IDE 看不到。緩解：型別主要在 `defproxyprint`/`make-proxy` 字串引用，影響有限。
- **效能**：proxy 包/解開有開銷。緩解：列印階段不在熱路徑（總長度 << ms），實際影響可忽略。

## 連結

- c-mera 對應：`projects/c-mera/src/c-mera/traverser.lisp:30-74`、`projects/c-mera/src/c-mera/pretty.lisp:62-75`
- 對應分析：`analysis/c-mera/architecture/level5_pretty_printer.md` §「Proxy 列印」
- hymera 設計：`docs/04_emit_interface.md` §6
- hymera 實作位置：`src/hymera/ast/base.hy`（Proxy 基底 + defproxy）、`src/hymera/emit/core.hy`（with-proxynodes / make-proxy / del-proxy / defproxyprint）
