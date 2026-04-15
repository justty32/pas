# Level 3：AST 與 Traverser 機制

## AST 節點體系
核心類別階層（`src/c-mera/nodes.lisp:55-58`）：

```
node
├── expression
├── statement
└── leaf
```

另有兩個特殊類別：
- `nodelist`：**唯一**持有節點列表（`nodes` 槽）的節點型別（`c-mera/nodes.lisp:68`）。所有「多個子節點」的位置都用 nodelist 包起來。
- `proxy`：為 traverser 暫時插入 AST 的代理節點（`c-mera/nodes.lisp:65`）。

### 定義節點的五個宏
定義於 `src/c-mera/nodes.lisp:22-50`。所有五個都：
1. 用 `defclass#` 產生類別，每個槽的 `:initarg` 自動對應到同名 keyword。
2. 用 `make-instance#` 產生 `MAKE-<NAME>` 的建構用巨集，同時記錄 `:values`（純值槽）與 `:subnodes`（子節點槽）兩個列表——這個分野就是 traverser 能自動下鑽的依據。

| 宏 | 父類 | 使用時機 |
|---|---|---|
| `defnode` | `node` | 一般結構節點 |
| `defstatement` | `statement` | C 語句 |
| `defexpression` | `expression` | C 運算式 |
| `defleaf` | `leaf` | 無子節點的葉（識別字、字面值） |
| `defproxy` | `proxy` | traverser 臨時節點 |

### 關鍵槽位的語意
每個節點類別都帶有兩個 meta 槽：
- `values`：列印時僅讀取、不遞迴的純值。
- `subnodes`：名稱列表，每個都是一個子節點槽，traverser 會依序下鑽（`c-mera/traverser.lisp:14`）。

範例（`src/c/nodes.lisp:8, 70, 73`）：
- `(defnode function-definition () (item parameter body))`
- `(defstatement if-statement () (test if-body else-body))`
- `(defstatement for-statement () (init test step body))`

## Traverser 泛型
`traverser` 是一個三參數 (`traverser`, `node`, `level`) 的泛型函式（`c-mera/traverser.lisp:6`）。預設方法（`c-mera/traverser.lisp:13`）簡單地走訪所有 `subnodes` 槽。`nodelist` 有獨立方法（`c-mera/traverser.lisp:22`）處理清單。

使用者要寫一個 traverser 只需：
1. `(defclass my-traverser () (...))`
2. 為感興趣的節點型別定義 `(defmethod traverser ((tr my-traverser) (node some-node-type) level) ...)`。
3. 其它節點型別會走預設路徑，自動遞迴。

## C 後端內建的 traverser（執行順序）
在 `src/c/cm-c.lisp:18` 的 `c-processor` 依序執行：

1. **`nested-nodelist-remover`**：把 nodelist 中巢狀 nodelist 攤平。
2. **`else-if-traverser`**：把 `if` 的 `else-body` 是另一個 `if-statement` 時，標記為「else if」而非新的獨立縮排塊。
3. **`if-blocker`**：決定 `if` 分支要不要加大括號（單敘述時不加）。
4. **`decl-blocker`**：掃描 `declaration-list`，依照是否巢狀決定加不加大括號。
5. **`renamer`**：把 Lisp 風格的識別字（含 `-`）轉成 C 合法識別字（轉 `_`），偵測衝突並以底線補位（`c/traverser.lisp:14-60`）。同一個字元序列會被快取到 `name-map` hash，確保整個 AST 保持一致。

接著 pretty-printer 再跑一次 traverser，輸出文字。

## Proxy 節點：在不破壞 AST 的情況下插入列印鉤子
三個工具（`src/c-mera/traverser.lisp:30, 58, 74`）：
- `(with-proxynodes (name …) body)`：在區域動態產生一個新的 proxy 類別。
- `(make-proxy slot proxy-class)`：把指定槽位包進一個 proxy 節點。
- `(del-proxy slot)`：移除該 proxy 節點。

pretty-printer 在 `:before` / `:after` 手動包 proxy，再為 proxy 定義 `defproxyprint`；這讓「型別後要加空白」這類細節（`src/c/pretty.lisp:62-75`）不需要改動原節點定義。
