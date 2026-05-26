# CLAUDE.md — hymera

## 衍生背景

- **本專案**：Hymera — Hy 寫的 c-mera 風格 C/C++ 生成器。
- **源專案**：c-mera（Common Lisp）。**無法直接執行**，僅作為設計藍本。
- **詳細目標**：見 `PROJECT.md`。
- **設計文件**：`docs/01_architecture.md` 起依序閱讀。

## 工作模式（Create）

依 `../../create_workflow.md`。所有技術細節寫入 `docs/`；操作日誌 append 至 `session_log.md`。

## 開發約定

### 1. 語言與輸出
- **所有輸出與留檔使用繁體中文。**
- 程式碼提到任何源碼處時必附 `path/to/file.hy:line`。引用 c-mera 時用 `projects/c-mera/src/...` 路徑或 `analysis/c-mera/architecture/levelN_xxx.md`。

### 2. Hy / Python 約定
- 對齊 **Hy 1.3.0**（已 venv 實測；見 `analysis/hy/tutorial/`）。
- 使用者面 API 用 **Hy 宏**寫；底層機制（dispatch、dataclass）可用純 Python。
- **核心 vs hyrule 分工**：core form 隨手用；需要 `->`/`unless`/`inc` 等請 `(require hyrule [...])` / `(import hyrule [...])`，見 `analysis/hy/tutorial/10_hy_core_ref.md`。
- 宏跨檔分享：`(require module [...])`；同檔輔助函數用 `(eval-and-compile ...)` 提升到編譯期。

### 3. 節點與遍歷器約定（全面對齊 c-mera）
- 新節點用 **`defnode` / `defstatement` / `defexpression` / `defleaf` / `defproxy`** 五件套定義（在 `src/hymera/ast/base.hy` 提供），不要直接寫 `defclass` 或 `@dataclass`。
- 簽章：`(defstatement NAME (純值槽...) (子節點槽...))`，與 c-mera 1:1。
- 遍歷／Pass／Emit 三種任務皆用 **自製 `defgeneric` / `defmethod`**（`src/hymera/generic.hy`）做型別分派，支援 `:before` / `:after` / `:self` 方法組合。
- 列印方法用 **`defprettymethod`** 註冊，是 `defmethod traverse` 對 Emitter 的封裝。
- 橫切列印關注用 **proxy 節點**：`with-proxynodes` / `make-proxy` / `del-proxy` / `defproxyprint`。
- Pass 介面：`(defclass MyPass [Pass] ...)`、`(defmethod traverse :before ((p MyPass) (n SomeNode)) ...)`；走「回傳新節點」風格。

### 4. 命名規則
- Hy 端用 kebab-case（`function-call`、`expression-statement`）；Python class 名為 PascalCase（`FunctionCall`、`ExpressionStatement`）。Hy mangling 不會處理 PascalCase，請手動對齊。
- 避免直接 shadow Hy/Python 內建（不要在 hymera 命名空間定義裸 `if`/`for`）。c-mera 那種「shadow 整個 cl 套件」的招在 Python 模組系統下不適用。

### 4.5 quoty 與核心 shadow
- 使用者程式碼用 `(hymera-c)` 或 `(hymera-cpp)` 起手，會自動 `(pragma :warn-on-core-shadow False)` 並 require 所有 hymera 宏，允許 `if`/`for`/`+`/`-`/`return` 等被 shadow。
- `quoty` 函式（`src/hymera/syntax/quoty.hy`）在編譯期被每個頂層宏呼叫，把 body 內未綁定符號／呼叫轉為 C 識別字／函式呼叫。
- 新增頂層宏時，記得把名稱加進 `HYMERA-SPECIAL-FORMS` 集合（在 `quoty.hy` 內），否則 quoty 會去 cook 你的關鍵字參數。

### 5. 不引入新外部依賴
- 標準函式庫優先：`io.StringIO`、`enum`、`pathlib`、`contextvars`（給 `with-proxynodes` 用）。
- 唯一第三方依賴：`hy`（執行期 + 編譯 .hy）、必要時 `hyrule`。
- 測試：`pytest`。
- 不引入模板引擎、不引入 AST 套件（pycparser/libclang 等留待 v2 對接時再說）。

## 構建與測試

```bash
cd derived/hymera
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .                # 開工後才會有 pyproject.toml
pytest tests
```

## 與分析產物的連結方式

| 我要找… | 去這裡 |
|---|---|
| c-mera 怎麼設計 AST | `analysis/c-mera/architecture/level3_ast_and_traverser.md` |
| c-mera 怎麼設計 syntax macros | `analysis/c-mera/architecture/level4_syntax_macros.md` |
| c-mera 怎麼設計 pretty-printer | `analysis/c-mera/architecture/level5_pretty_printer.md` |
| Hy 宏怎麼寫（特別是進階） | `analysis/hy/tutorial/11_macros_advanced.md` |
| Hy 1.x 與 0.x 差異 | `analysis/hy/tutorial/10_hy_core_ref.md` §5 |
| 為什麼不直接跑 c-mera | `analysis/hy/answers/hy_run_cmera.md` |
| 重要設計取捨 | `derived/hymera/docs/decisions/*.md` |

## 圖表呈現
依 `../../analysis_workflow.md` §7：禁 ASCII 框線圖。`.md` 用 Mermaid 或表格；HTML 導覽層用 `_shared.css` 的 `.card` / `.g3` 等。
