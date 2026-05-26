;; hymera.ast.base — Node / Expression / Statement / Leaf / Proxy / NodeList 基底
;;                   + defnode / defstatement / defexpression / defleaf / defproxy 五件套
;;
;; 設計：docs/02_ast_shape.md §1-5
;; 對照 c-mera：projects/c-mera/src/c-mera/nodes.lisp:22-68

;; ------------------------------------------------------------------
;; 基底類別
;; ------------------------------------------------------------------

(defclass Node []
  "所有 AST 節點的基底。

  類層級 metadata：
    _value_slots   —— 純值槽（traverser 不遞迴）
    _subnode_slots —— 子節點槽（traverser 會遞迴）
  兩者皆為 Python 屬性名（連字號已轉底線）的 tuple。"

  (setv _value_slots #())
  (setv _subnode_slots #())

  (defn __init__ [self #** kwargs]
    ;; 宣告的槽位先設 None
    (for [slot (+ self._value_slots self._subnode_slots)]
      (setattr self slot None))
    ;; kwargs 覆寫（含額外旗標，如 else_if?、need_block? 等由 Pass 寫入）
    (for [#(k v) (.items kwargs)]
      (setattr self k v)))

  (defn __repr__ [self]
    (+ "(" (. (type self) __name__)
       (.join "" (gfor slot (+ self._value_slots self._subnode_slots)
                       (+ " :" slot " " (repr (getattr self slot None)))))
       ")")))


(defclass Expression [Node]
  "C/C++ 表達式（有值）。")

(defclass Statement [Node]
  "C/C++ 語句。")

(defclass Leaf [Node]
  "葉節點：無子節點（識別字、字面值、型別參考）。")


(defclass NodeList [Node]
  "包子節點序列的容器。flatten-nodelists pass 保證不嵌套。"

  (setv _value_slots #())
  (setv _subnode_slots #("nodes"))

  (defn __init__ [self [nodes None]]
    (setv self.nodes (list (or nodes []))))

  (defn __iter__    [self] (iter self.nodes))
  (defn __len__     [self] (len self.nodes))
  (defn __getitem__ [self k] (get self.nodes k))
  (defn __repr__    [self]
    (+ "(node-list " (.join " " (gfor n self.nodes (repr n))) ")")))


(defclass Proxy [Node]
  "Emit 階段臨時插入的代理節點：包住某槽位，列印完拆掉。"

  (setv _value_slots #())
  (setv _subnode_slots #("wrapped"))

  (defn __init__ [self [wrapped None] #** kwargs]
    (setv self.wrapped wrapped)
    (for [#(k v) (.items kwargs)]
      (setattr self k v))))


;; ------------------------------------------------------------------
;; 定義宏：把連字號槽名轉成 Python 屬性名，生成 defclass
;; ------------------------------------------------------------------

(eval-and-compile
  (defn _py-slot [name]
    "槽位名轉 Python 屬性名。用 hy.mangle 而非單純換連字號，
     才能和 Hy 對 kwarg / 屬性存取的 mangling 一致（例如 else-if? →
     hyx_else_ifXquestion_markX，而非 else_if?）。"
    (hy.mangle (str name)))

  (defn _node-class-form [name base values subnodes]
    "產出 (defclass name [base] ...) 形式，供五個定義宏共用。
     base 為裸符號（Node/Statement/...）；使用 defNODE 的模組需先
     (import hymera.ast.base [Node Expression Statement Leaf Proxy])。"
    (setv val-slots (lfor v values (_py-slot v)))
    (setv sub-slots (lfor s subnodes (_py-slot s)))
    `(defclass ~name [~base]
       (setv _value_slots   ~(tuple val-slots))
       (setv _subnode_slots ~(tuple sub-slots)))))


(defmacro defnode [name values subnodes]
  "(defnode point () (x y)) → 繼承 Node 的節點類。"
  (_node-class-form name 'Node values subnodes))

(defmacro defstatement [name values subnodes]
  "(defstatement if-statement (else-if?) (test if-body else-body))"
  (_node-class-form name 'Statement values subnodes))

(defmacro defexpression [name values subnodes]
  "(defexpression infix-expression (op) (operands))"
  (_node-class-form name 'Expression values subnodes))

(defmacro defleaf [name values subnodes]
  "(defleaf ident (name) ())"
  (_node-class-form name 'Leaf values subnodes))

(defmacro defproxy [name values subnodes]
  "(defproxy type-space () ()) → 繼承 Proxy；_subnode_slots 永遠含 wrapped。"
  (setv val-slots (lfor v values (_py-slot v)))
  (setv sub-slots (lfor s subnodes (_py-slot s)))
  `(defclass ~name [Proxy]
     (setv _value_slots   ~(tuple val-slots))
     (setv _subnode_slots ~(tuple (+ ["wrapped"] sub-slots)))))
