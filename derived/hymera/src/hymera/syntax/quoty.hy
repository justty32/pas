;; syntax.quoty — quoty 函式（編譯期符號 binding 判斷 + 字串拆解）+ HYMERA-SPECIAL-FORMS
;; 設計：../../../docs/05_syntax_macros.md §3、../../../docs/decisions/0002-implement-quoty.md
;;       ../../../docs/decisions/0004-reader-sugar-and-arr-asymmetry.md
;; 對照 c-mera：projects/c-mera/src/c-mera/utils.lisp:53
;; 實測驗證：bound? 用 (scope.defined ∪ builtins ∪ _hy_macros) 三表聯查
;; 狀態：⏳ 骨架
