;; hymera.cli — c-file / cpp-file 兩個頂層宏 + 命令列入口
;; 流水線：reader → AST → flatten → else-if → blocker → renamer → emit → 寫檔
;; 設計：../../docs/01_architecture.md §1、../../docs/03_traverser_and_passes.md §3
;; 對照 c-mera：projects/c-mera/src/c-mera/c-mera.lisp:5、cm-c.lisp:18
;; 狀態：⏳ 骨架
