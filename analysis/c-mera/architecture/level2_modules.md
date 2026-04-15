# Level 2：核心模組職責

C-Mera 以「核心 + 可插拔後端」分層，全部透過 `c-mera.asd` 的 ASDF 系統與 `defpackage*` 宏（`c-mera.asd:11`）組織。

## 核心層：`src/c-mera/`（套件 `:c-mera`）
| 檔案 | 職責 | 關鍵符號 |
|---|---|---|
| `version.lisp` | 版本字串 `*version*`、`*generator*` | — |
| `cmd.lisp` | 命令列參數解析 | `parse-cmdline` |
| `nodes.lisp` | AST 基礎：`node` / `expression` / `statement` / `leaf` / `proxy` / `nodelist`；提供 `defnode`、`defstatement`、`defexpression`、`defleaf`、`defproxy` | `c-mera/nodes.lisp:22-50` |
| `utils.lisp` | `cintern`（大小寫反轉以配合 `readtable-case :invert`）、`defsyntax`（定義使用者層巨集）、`fboundp!` / `vboundp!` / `quoty`、`make-nodelist` | `c-mera/utils.lisp:7, 19, 53, 71` |
| `traverser.lisp` | 通用 traverser 泛型與 proxy node 機制 `make-proxy` / `del-proxy` / `with-proxynodes` | `c-mera/traverser.lisp:6, 30, 74` |
| `pretty.lisp` | 葉節點通用列印（字串/字元/數字/識別字） | `c-mera/pretty.lisp:5` |
| `c-mera.lisp` | 三個大型巨集 `define-reader`、`define-processor`、`save-generator`；以及 REPL 用的 reader 切換 `define-switch` / `define-switches` | `c-mera/c-mera.lisp:3, 55, 79, 107, 121` |

## C 後端：`src/c/`（套件 `:cm-c` 實作、`:cmu-c` 使用者介面）
| 檔案 | 職責 | 備註 |
|---|---|---|
| `utils.lisp` | 小工具（例如 `get-declaration-name`） | — |
| `nodes.lisp` | C 語法的具體 AST：`function-definition`、`declaration-list`、`for-statement`、`if-statement` … | `c/nodes.lisp:8, 70, 73` |
| `traverser.lisp` | `renamer`（合法化 C 識別字）、`decl-blocker`（插入大括號）、`if-blocker`、`else-if-traverser`、`nested-nodelist-remover` | `c/traverser.lisp:7` |
| `syntax.lisp` | 使用者層巨集 `function`、`decl`、`for`、`if`、`set`、`=`、`aref`、`oref`、`pref`、`struct`、`include`…全用 `c-syntax` 宏包起（就是帶預設套件的 `defsyntax`） | `c/syntax.lisp:3` |
| `pretty.lisp` | 每個 AST 節點的 `defprettymethod`；涵蓋 `expression-statement`、`compound-statement`、`declaration-item`、`if-statement`…（746 行，最厚） | `c/pretty.lisp:1` |
| `reader.lisp` | 空白觸發的預處理器 `pre-process` / `pre-process-heads`；負責把 `p->x`、`a.b`、`a[i]`、`i++`、`0.5f` 這類 C 常見寫法展開為對應節點 | `c/reader.lisp:4` |
| `cm-c.lisp` | 組裝：`define-reader` 建立 `read-in-file`；`define-processor` 以 traverser 清單組成 `c-processor`；`save-generator` 產生 `save` 用於 dump executable | `c/cm-c.lisp:4, 14, 26` |
| `cmu-c.lisp` | 使用者套件中的補充定義（例如 `use-variables`、`use-functions` 相關函式） | — |

## 上層後端
- **C++**：`src/cxx/`，套件 `:cm-c++` 繼承 `:cm-c`；新增 `class`、`namespace`、`template`、`new`/`delete`、`try`/`catch`、lambda、`for-each`、cast 家族、`instantiate`、`from-namespace` 等（`c-mera.asd:80`）。
- **CUDA**：`src/cuda/`，套件 `:cm-cuda` 繼承 `:cm-c++`；新增 `launch`、共享記憶體、執行設定 `threads`/`blocks` 等。
- **OpenCL**：`src/opencl/`，類似 CUDA 但以 `cl` 為基礎。
- **GLSL**：`src/glsl/`，套件 `:cm-glsl` 繼承 `:cm-c`；加入 `layout` 等 shader 修飾。

## 套件命名三件組（`c-mera.asd:251-423`）
- `c-mera`：核心後端符號。
- `cm-<lang>`：後端實作套件（`cm-c`、`cm-c++`、`cm-cuda`、`cm-glsl`、`cm-opencl`）。
- `cmu-<lang>`：**使用者套件**，使用者的 `.lisp` 就在這裡讀進來；會 `:shadow` 所有和 Common Lisp 衝突的符號（`if`、`for`、`=`、`+`、`function`…），同時透過 `c-exports` 重新匯出全部 CL 符號。
- `cms-<lang>`：swap 套件，用於 reader 在 Lisp / C-Mera 模式之間切換時暫存符號。

## 前端分派器
`src/front/cm.c` 是一支普通的 C 程式，會依第一個參數（`c`、`c++`、`cuda`…）`execvp` 對應的 `cm-c` / `cm-cxx` 可執行檔（由 `make` 以 `save-generator` dump 出來）。
