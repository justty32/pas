# Hymera 實作進度 (progress.md)

> 更新：2026-05-26　｜　模式：Create（v1 實作中）
> 設計文件全在 `docs/`；本檔記錄「實作」進度與冷啟動接手所需上下文。

## 一句話現況

設計階段完成（38 檔），v1 實作已起步：**基礎設施 + 泛型函式 + AST 基底 + 全套 C 節點定義**已完成並通過 smoke test；尚未做 traverser/pass/emit/syntax，故還無法端對端產出任何 C 檔。

## 構建與測試

```bash
cd derived/hymera
# venv 已建好並 editable-install（.venv 已 gitignore）
.venv/Scripts/hy.exe <某腳本.hy>          # 跑單檔
.venv/Scripts/python.exe -m pytest        # 測試（tests/ 尚未填）
```
- 環境：Windows、Python 3.13、Hy 1.3.0、已 `pip install -e ".[dev]"`（含 pytest、hyrule）。
- 套件根是 **`src/hymera/__init__.py`（Python）**，第一行 `import hy` 註冊 .hy 鉤子；其餘皆 .hy。

## 已完成（通過 smoke test）

| 檔案 | 內容 | 驗證 |
|---|---|---|
| `pyproject.toml` | 套件設定（src layout、package-data 收 .hy、pytest 設定） | editable install 成功 |
| `src/hymera/__init__.py` | `import hy` bootstrap | ✅ |
| `src/hymera/generic.hy` | `GenericFunction` + `defgeneric` / `defmethod`，支援 `:before`/`:after`/`:self` 方法組合（CLOS 標準組合：:before 最具體先、primary 最具體一個、:after 最不具體先） | ✅ 三種限定詞順序正確、:self 接管正確 |
| `src/hymera/ast/base.hy` | `Node`/`Expression`/`Statement`/`Leaf`/`NodeList`/`Proxy` + 五件套 `defnode`/`defstatement`/`defexpression`/`defleaf`/`defproxy` | ✅ 建構、繼承、proxy、槽名一致都驗過 |
| `src/hymera/ast/c_nodes.hy` | 全套 C 節點（leaf/表達式/語句/宣告/前處理/translation-unit，約 30 種） | ✅ 載入、建構、slot 正確 |

## 剩餘待辦（依 Phase 順序）

- [ ] **Phase 3 剩餘**：`traverser.hy`（`Traverser` + `Pass` 基底 + `traverse` 泛型，預設方法走 `_subnode_slots`）；`passes/flatten.hy`（攤平巢狀 NodeList）；`passes/renamer.hy`（kebab→snake，衝突補底線）。
- [ ] **Phase 4**：`emit/core.hy`（`Emitter` 類：stream/indent/info-stack/sign-stack + `defprettymethod` 封裝）；`emit/c.hy`（先做範例 A 需要的節點 emit）。
- [ ] **Phase 5**：`syntax/quoty.hy`（編譯期 binding 檢查；先做基本版，symbol cooking 後補）；`syntax/c.hy`（`function`/`return`/`include`/`hymera-c` 宏）；`cli.hy`（`c-file` 宏：reader→AST→pipeline→emit→寫檔）。
- [ ] **Phase 6**：`tests/conftest.py`（`import hy`）+ `tests/test_example_a.hy`；產出 hello.c 並用 gcc 編譯執行驗證。
- [ ] 之後：擴張到範例 B（struct/控制流/member access + else-if/if-blocker/decl-blocker pass + quoty cooking `->`/`.`/`++`）、C（namespace/using + cpp_nodes/emit/syntax + `::` cooking）、D（class/template + proxy「型別後空白」）。

## 冷啟動必讀的關鍵踩坑（已學到）

1. **迴圈/區域變數不要命名 `fn`**：`(fn ...)` 會被當 Hy 的 lambda 特殊形式。generic.hy 曾因此爆掉，改用 `m`。
2. **`+ - * /` 是 macro 不是函數**：不能 `(reduce + xs)` 或把 `+` 當值傳。要嘛改用 `sum`，要嘛 `(import hy.pyops *)`。
3. **槽名一律用 `hy.mangle`**（base.hy 的 `_py-slot`）：`else-if?` 必須 mangle 成 `hyx_else_ifXquestion_markX`，才能和 Hy 對 kwarg `:else-if?` 與屬性存取 `node.else-if?` 的 mangling 一致；單純換 `-`→`_` 會讓 traverser 用槽名 getattr 時讀到 None。
4. **`hy.I.module.Class` 不能用 `(hy.models.Symbol "...")` 建構**（含 `/` 會被判為非法 symbol）。所以 `defNODE` 的 base 用**裸符號**，使用 defNODE 的模組（c_nodes.hy / cpp_nodes.hy）必須先 `(import hymera.ast.base [Node Expression Statement Leaf Proxy])`。`hy.I` 當基類本身在「直接寫死」時可行（已驗），但無法在宏裡用字串組出來。
5. **節點建構是執行期**：宏層（function/c-file 等）只在編譯期把 sexp 展開成「節點建構式」，真正的節點物件在 .hy 執行時才生成。

## 設計對齊備忘

- v1 全面對齊 c-mera；唯一不對齊 = `arr[i]`（保留 `(aref arr i)`，見 `docs/decisions/0004-...md`）。
- 兩個關鍵假設已實測通過：核心 shadow（`pragma :warn-on-core-shadow False`）、quoty 的 binding 判斷（`scope.defined ∪ builtins ∪ _hy_macros`）。
- 下一個動作建議：寫 `traverser.hy`，並馬上用一個手刻的小 AST（hello.c 對應的節點樹）測 `traverse` 預設走訪。
