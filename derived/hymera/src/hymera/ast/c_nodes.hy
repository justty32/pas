;; hymera.ast.c_nodes — C 節點定義
;;
;; 設計：docs/02_ast_shape.md §3
;; 對照 c-mera：projects/c-mera/src/c/nodes.lisp:8-73
;;
;; 每個 defNODE 展開為一個繼承 Node/Statement/Expression/Leaf 的類別，
;; 並登記 _value_slots / _subnode_slots。需先 import 基底類別。

(import hymera.ast.base [Node Expression Statement Leaf])
(require hymera.ast.base [defexpression defstatement defleaf])

;; ------------------------------------------------------------------
;; 葉節點
;; ------------------------------------------------------------------
(defleaf ident          (name)         ())   ; C 識別字（renamer 會改寫 .name）
(defleaf scalar-literal (value suffix) ())   ; 數字/字串/字元字面值；suffix 如 "f"/"U"/"L"
(defleaf type-ref       (name)         ())   ; 型別名（int / Point / char ...）

;; ------------------------------------------------------------------
;; 表達式
;; ------------------------------------------------------------------
(defexpression infix-expression      (op) (operands))         ; (+ a b c) → operands 為 NodeList
(defexpression prefix-expression     (op) (operand))          ; -x, !x, &x, *x
(defexpression postfix-expression    (op) (operand))          ; i++, i--
(defexpression assignment-expression (op) (variable value))   ; =, +=, ...
(defexpression function-call         ()   (func args))        ; f(a, b)
(defexpression member-access         (kind) (object name))    ; kind '. 或 '->
(defexpression subscript-expression  ()   (array index))      ; a[i]
(defexpression cast-expression       ()   (type expr))        ; (T) x
(defexpression ternary-expression    ()   (test then else))   ; c ? a : b
(defexpression paren-expression      ()   (expr))             ; 顯式括號

;; ------------------------------------------------------------------
;; 語句
;; ------------------------------------------------------------------
(defstatement if-statement        (else-if?)    (test if-body else-body))
(defstatement for-statement       (need-block?) (init test step body))
(defstatement while-statement     (need-block?) (test body))
(defstatement do-while-statement  ()            (body test))
(defstatement switch-statement    ()            (test body))
(defstatement case-clause         (is-default?) (value body))
(defstatement break-statement     ()            ())
(defstatement continue-statement  ()            ())
(defstatement return-statement    ()            (value))
(defstatement expression-statement ()           (expr))
(defstatement compound-statement  ()            (statements))   ; { ... }

;; ------------------------------------------------------------------
;; 宣告
;; ------------------------------------------------------------------
(defstatement declaration-item    ()        (specifier type id init))  ; const int x = 0
(defstatement declaration-list    (in-block?) (items))
(defstatement function-definition ()        (item parameter body))     ; item=回傳型別+名稱
(defstatement struct-definition   (kind)    (name body))               ; kind 'struct / 'union
(defstatement typedef-definition  ()        (type alias))
(defstatement enum-definition     ()        (name members))

;; ------------------------------------------------------------------
;; 前處理與頂層
;; ------------------------------------------------------------------
(defstatement preproc-include  (is-system?) (path))     ; #include <x> 或 "x"
(defstatement preproc-define   ()           (name value))
(defstatement preproc-ifdef    ()           (name body else-body))
(defstatement translation-unit ()           (items))    ; 整個檔案
