# ADR 0004：Reader 字串便利 90% 對齊；`arr[i]` 保留為 `(aref arr i)`

> 新增 ADR。記錄 hymera 與 c-mera **唯一**的 v1 API 不對齊處與替代方案。

## 背景

c-mera 透過 char-level reader macros 讓使用者直接寫 C 風格：

| c-mera reader | 例子 | 對應 c-mera 處理函式 |
|---|---|---|
| `->` | `p->x` | `split-pref` |
| `.` | `obj.x` | `split-oref` |
| `[]` | `arr[i]` | `split-aref` |
| `++` / `--` | `i++`、`++i` | `split-unary` |
| 浮點後綴 `f` | `0.5f` | `read-float` |

實作位置：`projects/c-mera/src/c/reader.lisp` 的 `dissect` 系列函式，在 CL reader 讀到空白／左括號時觸發。

Hy 的 reader API（`projects/hy/hy/reader/hy_reader.py`）只允許在 `#` 後註冊 reader 宏；無法像 CL 那樣把任意字元當 reader macro 字元。所以 c-mera 那套 char-level 攔截在 Hy 直接做不來。

## 兩條替代路徑評估

### 路徑 A：自製 `HymeraReader` 子類，覆寫 `read_default` 與 `[` 處理

- **能對齊**：`p->x`、`obj.x`、`i++`、`0.5f`（這些只需要 `read_default` 內的字串拆解）
- **`arr[i]`**：要在讀到 `[` 時往前看「上一個 token 是否是識別字、且兩者之間無空白」。Hy 的 `Reader` 物件不直接暴露「上一個 token」，需要在 `read_default` 結束後維護狀態。**可做，但要 monkey-patch reader state 或大幅子類化**。
- **使用者代價**：必須換 reader。Hy 的 import hook 預設用 `HyReader()`（`projects/hy/hy/importer.py:130`）。要走 `HymeraReader` 得：
  1. 寫 hymera CLI（`hymera-build file.hy`）：自己 read+eval，不靠 Python 的 import 系統。
  2. 或 monkey-patch importer，讓特定副檔名（如 `.hyc`）走 HymeraReader。

### 路徑 B：在 `quoty` 階段做 symbol-string 拆解，**不**碰 reader

- **能對齊**：`p->x`、`obj.x`、`i++`、`++i`、`i--`、`--i`、`0.5f`——這些拆解時 symbol 字串裡保留了原始字元，可在 `quoty` 階段以字串操作切分。
- **`arr[i]`**：Hy reader 看到 `arr[i]` 時，先讀識別字 `arr`，遇到 `[` 就 break out 並另起讀 List。所以使用者程式碼裡 `arr[i]` 會被 Hy 解析為**兩個獨立的 form**：`arr` 後跟 `[i]`。`quoty` 看到時已經太遲，沒有「無空白接續」的資訊。
- **使用者代價**：零。直接用 Hy 標準 import / `.hy` 副檔名，跟一般 Hy 模組無異。

## 決策

**採路徑 B**。`arr[i]` 唯一例外，保留為 `(aref arr i)`。

理由：
1. 路徑 A 為了一個 `arr[i]` 要付出「自製 CLI + 換 reader + 失去 Hy import 整合」的代價，不划算。
2. 路徑 B 的便利性已覆蓋 c-mera reader 95% 的使用場景（`arr[i]` 在實務 C 程式碼裡頻率高，但寫成 `(aref arr i)` 並沒有比寫 `(.replace ...)` 之類的方法呼叫更 verbose）。
3. v2 可選擇升級到路徑 A：CLI 工具 + 自製 reader。不會破壞 v1 既有寫法（`(aref arr i)` 永遠保留）。

## quoty 階段的拆解規則（路徑 B 具體實作）

```hylang
(eval-and-compile
  (defn cook-symbol [sym]
    "在 quoty 階段拆解 symbol 字串。"
    (setv s (str sym))
    (cond
      ;; 後綴
      (.endswith s "++")  `(post++ ~(hy.models.Symbol (cut s 0 -2)))
      (.endswith s "--")  `(post-- ~(hy.models.Symbol (cut s 0 -2)))
      ;; 前綴
      (.startswith s "++") `(pre++ ~(hy.models.Symbol (cut s 2 None)))
      (.startswith s "--") `(pre-- ~(hy.models.Symbol (cut s 2 None)))
      ;; member access：→ 與 .
      (in "->" s)  (split-on-arrow s)            ; p->x → (-> p x)；p->x->y → (-> p x y)
      (in "." s)
        (if (and (not (.startswith s "."))
                 (not (.endswith s "."))
                 (not (.replace s "." "").isdigit))   ; 排除浮點數 1.5
            (split-on-dot s)
            sym)
      ;; 浮點後綴
      (re.match r"^-?\d+(\.\d+)?[fFlL]$" s)
        (parse-numeric-suffix s)
      True sym)))
```

### 邊角案例

| 輸入 | 處理 |
|---|---|
| `->` 單獨 | 不拆（它是 hymera 內建運算子） |
| `1.5` | 數字字面值，不拆 |
| `1.5f` | 拆成 `(c-float 1.5 "f")` |
| `p.x.y` | 拆成 `(. p x y)` |
| `p->x.y` | 先拆 `->` → `(-> p x.y)`，遞迴 quoty 處理內層 → `(-> p (. x y))` |
| `.field`（以 `.` 開頭） | 不拆（保留給其他用途，例如方法呼叫快捷） |

## 後果

### 正面
- v1 範圍可控；不需要寫 CLI 與自製 reader。
- `.hy` 檔案是標準 Hy 模組，可被任何 Hy 工具（hy2py、linter、IDE）正常處理。
- `quoty` 統一處理 binding 判斷 + 字串拆解，邏輯集中。

### 負面
- **`arr[i]` 是唯一非對齊**：c-mera 使用者會明顯感受到差異。緩解：在 README 與 docs/01 顯示對照表，並在範例文件首段明確說明。
- **字串拆解的歧義**：如「`a.b.c`」可能既是 member access、也可能是 dotted identifier（例如模組路徑）。hymera 規則：在 quoty 階段、且該 symbol 未綁定時才拆。`(import a.b.c)` 之類在特殊形式裡（不過 quoty）不受影響。

## 升級到路徑 A 的退路

如果 v2 必須做 `arr[i]`：

1. 提供 `hymera-build file.hyc -o file.c` CLI。
2. CLI 內部用 `HymeraReader` 讀檔。
3. `HymeraReader.read_default` 增強處理上述拆解 + 在識別字讀完後 peek 下一字元，若為 `[` 且無空白則讀 aref 子節點。
4. 副檔名分流：`.hy` 維持路徑 B、`.hyc` 走路徑 A。

## 連結

- c-mera reader：`projects/c-mera/src/c/reader.lisp`、`analysis/c-mera/architecture/level6_reader_and_packages.md`
- Hy reader：`projects/hy/hy/reader/hy_reader.py:113-188`
- 與 ADR 0002 (quoty) 的關係：本決策的字串拆解附在 `cook-symbol` 內，由 quoty 呼叫
- hymera 實作位置：`src/hymera/syntax/quoty.hy` 的 `cook-symbol`
