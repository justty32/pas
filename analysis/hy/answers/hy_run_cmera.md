# 能否用 Hy 跑 c-mera？

> 提問日期：2026-05-26  ｜  對齊版本：Hy 1.3.0
>
> 結論先講：**直接拿 c-mera 的 Common Lisp 原始碼放到 Hy 跑，不行。但用 Hy 重新實作一個 c-mera 風格的「Lisp → C/C++/CUDA 生成器」，完全可行而且不難。**

## 1. 結論一句話

| 問題 | 答案 |
|---|---|
| 把 `projects/c-mera/src/*.lisp` 餵給 `hy` 執行？ | ❌ 不可能 |
| 在 Hy 中重新實作 c-mera 的概念？ | ✅ 可行（Hy 的宏系統有條件做到） |

## 2. 為什麼不能直接跑

c-mera 是貨真價實的 **Common Lisp 專案**（依據 `projects/c-mera/c-mera.asd`）：

- 使用 ASDF 系統定義（`(defsystem ...)`、`(asdf:load-system ...)`）
- 顯式相依 SBCL：`#+sbcl (require :sb-cltl2)`
- 透過 Quicklisp 載入依賴
- 大量使用 CL 專屬語意：`defpackage`、`do-external-symbols`、`*foo*` 動態變數、reader 巨集字元 (`set-macro-character`)、`defmethod`/CLOS、`handler-case`／restart

Hy 表面看是 Lisp，**但骨子裡是 Python**——Hy 原始碼編譯為 Python AST，在 CPython 上執行。差異對應如下：

| c-mera 需要 | Common Lisp 提供 | Hy 對應 / 缺口 |
|---|---|---|
| ASDF / quicklisp 載入 | ✅ | ❌ 用 Python 的 `import` 系統，協定不同 |
| `defpackage` 套件 + `:shadow`/`:export` | ✅ | ❌ Hy 用 Python 模組，無 CL 套件系統 |
| 動態（特殊）變數 `*var*` | ✅ | ❌ Hy 沒有 thread-local 動態綁定原語 |
| CLOS：`defclass`/`defgeneric`/`defmethod` + 方法組合 | ✅ | 🟡 Hy 只有 Python class／單派發 |
| `eval-when` 四種時間鍵 | ✅ | 🟡 Hy 有 `eval-and-compile`/`eval-when-compile`/`do-mac`，但語意不完全對應 |
| reader macro 字元層 (`set-macro-character`) | ✅ | 🟡 Hy 的 `defreader` 走的是 `#name` 觸發協定，行為不同 |
| `format` 指令語言、`loop` 巨集 | ✅ | ❌ 沒有等價物 |
| condition / restart 系統 | ✅ | ❌ 只有 Python 例外（無 restart） |

光是 `defpackage` + reader macro + 特殊變數這三項，就足以讓 c-mera 的源碼**完全跑不起來**。這不是相容性問題，是**不同的 Lisp 方言**。

## 3. 那 Hy 的長處是什麼？

Hy 能做的核心 c-mera 也做的事：

1. **以 S-expression 寫程式碼模板**（quasiquote／unquote）。
2. **編譯期改寫程式碼樹**（`defmacro` + `hy.models.*`）。
3. **自訂解析器擴展**（reader macro：`defreader`）。
4. **編譯期計算常數／程式碼**（`do-mac`、`eval-and-compile`）。

加上 Hy 站在 Python 上，**有現成的好處**：

- Python 的字串模板、`f-string`、`textwrap`、`black/clang-format` 都可直接用。
- 與 numpy/pytorch/CUDA 工具鏈整合容易（c-mera 主打 CUDA 場景）。
- 大量 C 解析／生成函式庫可用：`pycparser`、`libclang` Python binding。
- 套件管理用 pip，部署簡單。

## 4. 在 Hy 重新實作 c-mera 的可行藍圖

c-mera 的本質結構（見 `analysis/c-mera/architecture/level3_ast_and_traverser.md` 等）：
**AST 節點型別 → 遍歷器 (traverser) → 漂亮列印器 (pretty printer)**，加上**語法宏層**讓使用者寫起來像 C。

在 Hy 落地，每一層的對應：

| c-mera 層 | Hy 實作 |
|---|---|
| AST 節點型別（`defclass`） | 用 `defclass` 或 `dataclasses`／`attrs` 定義節點 |
| 節點建構巨集（`for-statement` 等） | `defmacro`，回傳 `(MyNode ...)` 形式的 Hy AST |
| 遍歷器 / visitor pattern | Python class 多型；或用 `functools.singledispatch` |
| Pretty printer | 普通函數逐節點吐字串／用 `io.StringIO` |
| 自訂讀者語法（`switch-reader`） | `defreader`（功能較淺，但夠用） |
| 條件式編譯 / 平台 dispatch | Python 端 `if`／`match` |

### 最小可行範例骨架（草圖，未實測）

```hylang
(import dataclasses [dataclass field])

(defclass [dataclass] CNode []
  "C 程式碼節點基底")

(defclass [dataclass] CFor [CNode]
  (setv init None  test None  step None  body None))

(defmacro c-for [init test step #* body]
  `(CFor :init ~init :test ~test :step ~step :body [~@body]))

(defn emit [node]
  ;; 依節點型別吐 C 字串
  (cond
    (isinstance node CFor)
      f"for ({(emit (. node init))}; {(emit (. node test))}; {(emit (. node step))}) {{
  {(.join \"\\n  \" (lfor s (. node body) (emit s)))}
}}"
    True (str node)))

;; 使用端
(print (emit (c-for "int i = 0" "i < 10" "++i" "printf(\"%d\\n\", i);")))
```

骨架說明：宏 `c-for` 在編譯期把 S-expression 包成 `CFor` 節點；執行期 `emit` 把節點吐成 C 源碼。要做到 c-mera 的完整度，再補：

- 更多節點型別（function、struct、switch、CUDA kernel attr…）
- 縮排管理／註解保留
- C 表達式優先級處理
- 子集驗證（如 CUDA `__global__`/`__device__`）

## 5. 結語

- **跑 c-mera 原始碼？** 死路。語言不同，差異不只是表面語法。
- **想得到 c-mera 那種「在 Lisp 中寫 C」的體驗？** 用 Hy 自製一個 Hy-mera，省下安裝 SBCL 與 Quicklisp 的步驟，並直接接上 Python 生態系。設計可參考 `analysis/c-mera/architecture/level3_ast_and_traverser.md` 與 `level4_syntax_macros.md`。
- **替代路徑**：若就是想要 c-mera 本人，直接 `apt install sbcl && quicklisp install c-mera` 比較快；Hy 適合用來吸取它的設計重做一份 Python 流派版本。
