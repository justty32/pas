# 04 — Emitter 與 Pretty-Printer

> 對照：`analysis/c-mera/architecture/level5_pretty_printer.md`、`projects/c-mera/src/c-mera/pretty.lisp:1-30`、`projects/c-mera/src/c/pretty.lisp:5-75`
>
> 對齊度：完全。`defprettymethod` / `defproxyprint` / `with-proxynodes` / `make-proxy` / `del-proxy` API 與 c-mera 1:1。

## 1. 角色定位

Emitter 是「印出 C/C++ 文字」的特殊 traverser。它本身是 `Traverser` 的子類，所以一切 `defmethod traverse` 機制可直接套用——但為了清晰，提供一個包裝 `defprettymethod`。

## 2. Emitter 類別

```hylang
;; src/hymera/emit/core.hy
(import io [StringIO])
(import enum [Enum auto])

(defclass Context [Enum]
  "info-stack 推的標籤。"
  (setv FOR (auto)) (setv WHILE (auto)) (setv DO (auto))
  (setv IF (auto))  (setv ELSE (auto))  (setv BLOCK (auto))
  (setv FUNC (auto)) (setv DECL (auto))
  (setv CLASS (auto)) (setv NS (auto)) (setv TPL (auto)))

(defclass Emitter [Traverser]
  (defn __init__ [self [stream None] [indent-str "    "]]
    (setv self.stream     (or stream (StringIO)))
    (setv self.indent-str indent-str)
    (setv self.depth      0)
    (setv self.info-stack [])
    (setv self.sign-stack [])
    (setv self.current-node None)        ; proxy 機制要用：knowing 當前節點以包/解槽位
    (setv self._proxy-stack []))

  (defn write [self s] (.write self.stream s))
  (defn nl    [self]   (.write self "\n" (* self.indent-str self.depth)))
  (defn indent-inc [self] (setv self.depth (+ self.depth 1)))
  (defn indent-dec [self] (setv self.depth (- self.depth 1)))
  (defn push-info  [self ctx] (.append self.info-stack ctx))
  (defn pop-info   [self]     (.pop self.info-stack))
  (defn top-info   [self]     (if self.info-stack (get self.info-stack -1) None))
  (defn push-sign  [self prec] (.append self.sign-stack prec))
  (defn pop-sign   [self]     (.pop self.sign-stack))
  (defn top-sign   [self]     (if self.sign-stack (get self.sign-stack -1) None))
  (defn getvalue   [self]     (.getvalue self.stream)))
```

各欄位對映 c-mera：`stream` / `indent` / `info-stack` / `sign-stack` 完全平行（`projects/c-mera/src/c-mera/traverser.lisp:7-10`）。

## 3. `defprettymethod`

包裝 `defmethod traverse`，限定第一參數為 `Emitter`。對映 c-mera `defprettymethod`：

```hylang
(defmacro defprettymethod [qualifier node-type #* body]
  "(defprettymethod :before If-Statement body...)
   等價於：
   (defmethod traverse :before ((e Emitter) (n If-Statement)) body...)
   並把 body 內可隱式取 e 與 n 兩個變數（透過 anaphoric）。"
  ;; 簡化版：要求使用者顯式寫參數
  `(defmethod traverse ~qualifier ((emitter Emitter) (node ~node-type))
     ~@body))
```

> 為對齊 c-mera 的「`defprettymethod :before NODE-TYPE body`」這種**不寫 emitter 與 node 變數名**的寫法，v1 提供「anaphoric」版本：body 內可直接用 `emitter` 與 `node` 兩個名字（由宏綁定）。c-mera 的版本則是用 `pp-let` 把當前 node-slot 綁進區域變數，hymera 暫先用更直接的「兩個固定名」版本。

## 4. 三種限定詞如何使用

對映 `projects/c-mera/src/c-mera/pretty.lisp:1-30`：

| 限定詞 | 何時用 |
|---|---|
| `:before` | 印節點開頭、push 上下文、調縮排 |
| `:after` | 印節點結尾、pop 上下文 |
| `:self` | 對控制結構等「**子節點之間要插字**」的場景完全接管 |

預設行為（無限定詞、無 `:self`）：跑完 `:before`，遍歷 `_subnode_slots`，跑完 `:after`。

### 4.1 範例：`expression-statement` 自動加分號

對映 `projects/c-mera/src/c/pretty.lisp:5-23`：

```hylang
(defprettymethod :after expression-statement
  (when (isinstance node.expr [FunctionCall InfixOp PrefixOp PostfixOp])
    (.write emitter ";")))
```

### 4.2 範例：`compound-statement` 看 top-info 決定大括號位置

對映 `projects/c-mera/src/c/pretty.lisp:30-45`：

```hylang
(defprettymethod :self compound-statement
  (cond
    (in (.top-info emitter) [Context.IF Context.ELSE Context.FOR Context.WHILE Context.DO])
      (.write emitter " {")           ; 緊接前文
    True
      (do (.nl emitter) (.write emitter "{")))
  (.push-info emitter Context.BLOCK)
  (.indent-inc emitter)
  (for [s node.statements]
    (.nl emitter)
    (traverse emitter s))
  (.indent-dec emitter)
  (.pop-info emitter)
  (.nl emitter)
  (.write emitter "}"))
```

注意：`:self` 接管後**必須自己呼叫 `traverse`** 走子節點，預設遍歷不會發生。

### 4.3 範例：`if-statement` 完整接管

```hylang
(defprettymethod :self if-statement
  (.push-info emitter Context.IF)
  (.write emitter (if node.else-if? " if (" "if ("))
  (traverse emitter node.test)
  (.write emitter ")")
  (traverse emitter node.if-body)
  (when (is-not node.else-body None)
    (cond
      ;; 後面的 else-body 本身被標 else-if？則不另起 " else"，直接 traverse
      (and (isinstance node.else-body if-statement) node.else-body.else-if?)
        (traverse emitter node.else-body)
      True
        (do (.write emitter " else") (traverse emitter node.else-body))))
  (.pop-info emitter))
```

## 5. 運算子優先序：sign-stack

中綴運算式輸出時要決定子表達式要不要加括號。對映 c-mera `sign-stack`。

```hylang
(setv PRECEDENCE
  {"||" 12  "&&" 11
   "|"  10  "^"   9  "&"  8
   "==" 7   "!="  7
   "<"  6   "<="  6  ">"  6  ">=" 6
   "<<" 5   ">>"  5
   "+"  4   "-"   4
   "*"  3   "/"   3  "%" 3})

(defprettymethod :self infix-expression
  (setv my-prec (.get PRECEDENCE (str node.op) 0))
  (setv parent-prec (or (.top-sign emitter) -1))
  (setv need-parens (< my-prec parent-prec))
  (when need-parens (.write emitter "("))
  (.push-sign emitter my-prec)
  (setv ops (list node.operands))
  (traverse emitter (get ops 0))
  (for [o (cut ops 1 None)]
    (.write emitter (str node.op))
    (traverse emitter o))
  (.pop-sign emitter)
  (when need-parens (.write emitter ")")))
```

## 6. Proxy 機制（與 c-mera 1:1）

詳細決策見 [`decisions/0003-implement-proxy-nodes.md`](decisions/0003-implement-proxy-nodes.md)。

### 6.1 API 對映

| c-mera | hymera | 用途 |
|---|---|---|
| `(with-proxynodes (NAME ...) body)` | `(with-proxynodes (NAME ...) body)` | 區域註冊 proxy 類別 |
| `(make-proxy slot proxy-class)` | `(make-proxy emitter slot proxy-class)` | 把當前節點某槽位包成 proxy |
| `(del-proxy slot)` | `(del-proxy emitter slot)` | 解包 |
| `(defproxyprint :before P body)` | `(defproxyprint :before P body)` | 註冊 proxy 的列印方法 |

### 6.2 範例：型別後加空白

對映 `projects/c-mera/src/c/pretty.lisp:62-75`：

```hylang
(with-proxynodes (type-space)

  (defproxyprint :after type-space
    (.write emitter " "))

  (defprettymethod :before declaration-item
    (make-proxy emitter "type" type-space))

  (defprettymethod :after declaration-item
    (del-proxy emitter "type")))
```

效果：每次列印 `declaration-item` 時，`type` 槽位被臨時包成 `type-space` proxy。Emitter 遍歷 `_subnode_slots` 時碰到 proxy 會 dispatch 到 proxy 的方法；proxy 的 `:after` 印空白。

### 6.3 實作關鍵：`Emitter.current-node`

`with-proxynodes` 用一個 stack 維護目前正在處理的節點：`:before` 進入時 push，`:after` 退出時 pop。`make-proxy` / `del-proxy` 直接 mutate 該節點的指定 slot。這違反「AST 不可變」原則——但**只發生在 emit 階段**，前面 Pass 全部走「回傳新節點」（見 [`03_traverser_and_passes.md`](03_traverser_and_passes.md) §3）。

## 7. C++ Emit 與 C 共用 dispatcher

`src/hymera/emit/cpp.hy` 不重寫 C 那邊已實作的節點 emit。它**只註冊 C++ 專屬節點**（`class-definition`、`namespace-definition`、`template-definition`、`using-declaration`、`new-expression`、`delete-expression`、`access-specifier` 等）。`traverse` 泛型同個函式、同個 dispatcher，看到 ClassDefinition 走 cpp 那組 `defprettymethod`，看到 If-Statement 仍走 c 那組——`defgeneric` 的多型自動處理。

## 8. 寫法總結

| 節點分類 | 用哪種限定詞 |
|---|---|
| 葉節點（Ident、ScalarLiteral、TypeRef） | `:before` 印文字，`:after` 通常省略 |
| 線性節點（Return、FunctionCall、InfixOp） | `:before` + `:after` 對稱包圍，或 `:self` |
| 複合控制結構（If、For、While、Switch、Ternary） | `:self` 完全接管（子節點間要插字） |
| Compound（區塊） | `:self`（要看 top-info 決定大括號位置） |
| 橫切列印關注（型別空白、優先序括號） | `defproxyprint` |
