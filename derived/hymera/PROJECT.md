# Hymera — Hy 寫的 c-mera 風格 C/C++ 程式碼生成器

> 建立日期：2026-05-26（v1 起草）
> 修訂：2026-05-26 — 依使用者「**都依照 c-mera**」指示，v1 範圍全面對齊 c-mera，先前的三項 deferral（`quoty`、proxy 節點、`c.` 命名前綴）全部納入 v1。
> 模式：Create（衍生小專案）
> 狀態：**設計階段**（PROJECT.md + 設計文件已備齊，等待設計審閱後再開始實作）

---

## 1. 源專案

- **參照分析**：`analysis/c-mera/`（Common Lisp 寫的 C/C++/CUDA 生成器）
- **語言層基礎**：`analysis/hy/`（已對齊 Hy 1.3.0，特別是 `tutorial/11_macros_advanced.md`）

---

## 2. 衍生目標

用 **Hy 1.3 + Python 3.13** 把 c-mera 的設計**完整移植**到 Python 生態系。「完整」指：API 形狀、宏家族、列印機制都儘量對映；只有「Hy 端做不到」的地方退讓並明示。

**範圍**：
- C 全功能
- C++ 基本子集：class/struct + 成員、namespace、template 基本、reference、auto、using、new/delete
- **不含** CUDA、RTTI、移動語意、concepts

**全面對齊 c-mera 的承諾**（v1 必做）：

| c-mera 機制 | hymera v1 對應 | 對齊度 |
|---|---|---|
| `defnode` / `defstatement` / `defexpression` / `defleaf` / `defproxy` 五個定義宏 | 同名五個宏，包 Hy `defclass` 並登記 `subnodes` / `values` 槽位 | 完全 |
| `defsyntax` / `c-syntax`（一段宏覆寫多個運算子） | `defsyntax` / `c-syntax` 同名宏 | 完全 |
| `traverser` CLOS 泛型 + `:before` / `:after` 方法組合 | 自製 `defgeneric` / `defmethod` 三槽（`:before` / `:after` / `:self`）方法組合 | 高 |
| `defprettymethod` / `defproxyprint` | 同名宏 | 完全 |
| `with-proxynodes` / `make-proxy` / `del-proxy` | 同名宏與函式 | 完全 |
| `quoty`：未綁定符號變 C 識別字、未綁定函式呼叫變 C 函式呼叫 | 同 quoty 函式（用 `_hy_compiler.scope.defined + builtins + _hy_macros` 判斷綁定） | 高（語意有細微差異，見下） |
| 直接覆蓋 `if`/`for`/`+`/`-` 等核心名稱（CL 套件 shadow） | 用 `(pragma :warn-on-core-shadow False)` + `defmacro` 覆寫 | 完全 |
| Reader 字串便利：`p->x`、`obj.x`、`i++`、`0.5f` | 在 `quoty` 階段對 symbol 字串做拆解 | 90% |
| Reader 字串便利：`arr[i]` | **無法達成**——`[` 是 Hy 語法分隔符；保留顯式 `(aref arr i)` | **不對齊**（記入 ADR 0004） |

---

## 3. 參照素材

| 文件 | 用途 |
|---|---|
| `analysis/c-mera/architecture/level3_ast_and_traverser.md` | AST 類別體系與 traverser 泛型機制 |
| `analysis/c-mera/architecture/level4_syntax_macros.md` | `defsyntax` / `c-syntax` / `quoty` 三件套 |
| `analysis/c-mera/architecture/level5_pretty_printer.md` | Pretty-printer + `:before` / `:after` + proxy |
| `analysis/c-mera/architecture/level6_reader_and_packages.md` | Reader 層便利 |
| `analysis/hy/tutorial/11_macros_advanced.md` | Hy 進階宏，特別是 `_hy_compiler`、`eval-and-compile`、`pragma`、`require` |
| `projects/c-mera/src/` | CL 原始碼：`cm-c.lisp`、`nodes.lisp`、`syntax.lisp`、`pretty.lisp`、`utils.lisp`、`traverser.lisp` |

---

## 4. 技術棧

| 項目 | 選擇 | 理由 |
|---|---|---|
| 語言 | Hy 1.3 + Python 3.13 | 所有面對使用者的層次（節點定義、宏、列印方法）都用 Hy；底層工具用 Python |
| AST 節點 | **Hy `defclass`**（透過 `defnode` 家族包裝） | 對齊 c-mera 的 `defclass#` 慣例（不用 `@dataclass`） |
| 泛型 dispatch | **自製 `defgeneric` / `defmethod`** + 方法組合 | 對齊 c-mera 的 CLOS 風格 |
| 字串生成 | `io.StringIO` + 縮排堆疊 | 同 c-mera |
| 套件管理 | `pyproject.toml` + `pip install -e .` | 標準 Python 流程 |
| 測試 | `pytest`（含 `conftest.py` 內 `import hy`） | 對應 `analysis/hy/tutorial/09_testing_interop.md` §2 |
| 格式化（選用） | 外部呼叫 `clang-format` | 不在 hymera 內重造輪子 |

---

## 5. 完成定義（v1）

v1 視為「**核心可用、API 與 c-mera 對齊**」的完整版本。

### 5.1 必須能生成（並通過實際編譯）

詳見 [`docs/07_examples.md`](docs/07_examples.md)。四個範例的 hymera 寫法**儘量貼近 c-mera 對應寫法**：

範例 A — hello.c：
```hylang
(c-file "hello.c"
  (include <stdio.h>)
  (function main () -> int
    (printf "hello, world\n")          ; 直接寫，靠 quoty 把 printf 變 C 函式呼叫
    (return 0)))
```

### 5.2 必須涵蓋的節點

- **表達式**：字面值（int/float/string/char）、識別字、infix、prefix、postfix、function-call、cast、subscript、member-access（`.` 與 `->`）、ternary
- **語句**：if/else、for、while、do-while、switch/case/default、break/continue、return、expression-statement、compound（block）、declaration（變數）
- **頂層**：function-definition、struct/union、typedef、enum、preprocessor（include/define/ifdef）、translation-unit
- **C++**：class-def、access-specifier、constructor/destructor、member-function、namespace、template、using-declaration、new-expr、delete-expr、reference declarator

### 5.3 必須完成的多 pass（與 c-mera 一一對應）

| Pass | 對應 c-mera |
|---|---|
| `nested-nodelist-remover` | ✅ |
| `else-if-traverser` | ✅ |
| `if-blocker` | ✅（v1 拆開，不合併） |
| `decl-blocker` | ✅（v1 拆開，不合併） |
| `renamer` | ✅ |

### 5.4 必須涵蓋的宏家族

- **節點定義五件套**：`defnode`、`defstatement`、`defexpression`、`defleaf`、`defproxy`
- **泛型/方法**：`defgeneric`、`defmethod`、`defprettymethod`、`defproxyprint`
- **語法層**：`defsyntax`、`c-syntax`
- **使用者運算子**：`+`、`-`、`*`、`/`、`%`、`<`、`>`、`<=`、`>=`、`==`、`!=`、`&&`、`||`、`!`、`<<`、`>>`、`++`、`--`、`=`、`+=` 等所有 C 運算子（透過 `(pragma :warn-on-core-shadow False)` 直接命名）
- **使用者控制流**：`if`、`for`、`while`、`do-while`、`switch`、`return`、`break`、`continue`（同樣 shadow）
- **使用者宣告**：`function`、`decl`、`struct`、`typedef`、`enum`、`include`、`define`
- **C++ 擴充**：`class`、`struct`、`namespace`、`template`、`using-namespace`、`using-decl`、`using-alias`、`new`、`delete`

### 5.5 必須涵蓋的 proxy 範例

至少一個 proxy 使用：例如「型別後加空白」（`int x`、`Point p`），對映 `projects/c-mera/src/c/pretty.lisp:62-75`。

### 5.6 quoty 涵蓋

- 未綁定符號（如 `x`）→ 自動成 `(ident x)`
- 未綁定函式呼叫（如 `(printf "%d" x)`）→ 自動成 `(function-call printf x)`
- 已綁定（Hy/Python builtin、`scope.defined`、`_hy_macros`）→ 不轉換
- symbol 字串拆解：`p->x` → `(-> p x)`、`obj.x` → `(. obj x)`、`i++` → `(post++ i)`、`++i` → `(pre++ i)`
- `arr[i]` 不轉換（**唯一 asymmetry**，見 ADR 0004）

### 5.7 測試覆蓋

- 每個節點型別：至少一個正向 emit 測試
- 每個 Pass：至少一個輸入/輸出對照測試
- quoty：至少 10 個 case（覆蓋上述各種 binding 狀態與字串拆解）
- proxy：至少一個列印場景
- 端對端：四個整檔範例都要被外部編譯器接受

### 5.8 文件

- README 含安裝、第一個範例
- 與 c-mera 對照表（哪些 1:1、哪些有微差）
- 四份 ADR（0001-0004）齊備

---

## 6. 唯一 v1 不對齊處

只有一個——`arr[i]` 的 reader 層便利。理由與替代方案見 [`docs/decisions/0004-reader-sugar-and-arr-asymmetry.md`](docs/decisions/0004-reader-sugar-and-arr-asymmetry.md)。

---

## 7. 目錄結構

```
derived/hymera/
├── PROJECT.md
├── CLAUDE.md
├── README.md
├── session_log.md
├── session_temp/
├── docs/
│   ├── 01_architecture.md
│   ├── 02_ast_shape.md
│   ├── 03_traverser_and_passes.md
│   ├── 04_emit_interface.md
│   ├── 05_syntax_macros.md
│   ├── 06_cpp_extensions.md
│   ├── 07_examples.md
│   └── decisions/
│       ├── 0001-clos-style-method-combination.md   (取代舊 singledispatch 案)
│       ├── 0002-implement-quoty.md                 (取代舊跳過案)
│       ├── 0003-implement-proxy-nodes.md           (取代舊跳過案)
│       └── 0004-reader-sugar-and-arr-asymmetry.md  (新增：reader 對齊與唯一缺口)
├── src/hymera/
│   ├── __init__.hy
│   ├── ast/
│   │   ├── __init__.hy
│   │   ├── base.hy          # Node / Expression / Statement / Leaf / Proxy / NodeList + defnode 家族
│   │   ├── c_nodes.hy       # C 節點
│   │   └── cpp_nodes.hy     # C++ 擴充節點
│   ├── generic.hy           # defgeneric / defmethod + 方法組合
│   ├── traverser.hy         # walk + Pass 基底
│   ├── passes/
│   │   ├── __init__.hy
│   │   ├── flatten.hy
│   │   ├── else_if.hy
│   │   ├── if_blocker.hy
│   │   ├── decl_blocker.hy
│   │   └── renamer.hy
│   ├── emit/
│   │   ├── __init__.hy
│   │   ├── core.hy          # Emitter + defprettymethod + defproxyprint
│   │   ├── c.hy
│   │   └── cpp.hy
│   ├── syntax/
│   │   ├── __init__.hy
│   │   ├── quoty.hy         # quoty 函式（eval-and-compile）
│   │   ├── c.hy             # 使用者層 C 宏（含 defsyntax / c-syntax）
│   │   └── cpp.hy
│   └── cli.hy
└── tests/
    └── README.md
```

---

## 8. 進度

- [x] 設計階段（修訂版）：PROJECT.md + 設計文件 + 4 份 ADR + src 骨架 —— **等待審閱**
- [ ] 實作 v1
- [ ] 測試 v1
- [ ] 完工 v1
