# ADR 0002：v1 實作 `quoty`，使用者寫 `(printf "%d" x)` 即等同於 C 函式呼叫

> 取代先前「v1 跳過 quoty」案。改為「全面對齊 c-mera」的指示要求。

## 背景

c-mera 的 `quoty`（`projects/c-mera/src/c-mera/utils.lisp:53`）規則：
- 未綁定符號 → 變成 C 識別字
- 未綁定函式呼叫形式 → 變成 C 的 `function-call`
- 已綁定的 Lisp 符號 → 原樣求值

這是讓 c-mera 程式碼讀起來像 C 的關鍵。

之前 ADR 0002 認為「Hy 端拿不到編譯期 binding 資訊」所以跳過。**那個判斷錯了**——實測（2026-05-26）顯示，三個資料來源的聯查可以準確判斷：

```hylang
(defn bound? [compiler sym]
  (setv name (hy.mangle (str sym)))
  (or
    (in name (. compiler scope defined))      ; defn / setv / import / let 都會更新
    (hasattr builtins name)                   ; Python builtin
    (in name (or (getattr builtins "_hy_macros" None) {}))
    (in name (or (getattr compiler.module "_hy_macros" None) {}))))
```

實測 6 個 case 全部正確：`print`/`math`/`myvar`/`helper` → BOUND；`printf`/`foo-undef` → UNBOUND。

## 決策

**v1 實作 `quoty` 函式**，所有 hymera 宏在處理 body 前都先 `(quoty body _hy_compiler)`。

### 實作概觀

```hylang
;; src/hymera/syntax/quoty.hy
(eval-and-compile
  (import builtins)
  (import hy.models [Expression Symbol List]))

(eval-and-compile
  (defn bound? [compiler name]
    (setv m (hy.mangle name))
    (or (in m (. compiler scope defined))
        (hasattr builtins m)
        (in m (or (getattr builtins "_hy_macros" None) {}))
        (in m (or (getattr compiler.module "_hy_macros" None) {}))))

  (defn quoty [form compiler]
    "把 form 中所有未綁定符號轉成 C 識別字、未綁定函式呼叫轉成 C function-call。"
    (cond
      ;; Symbol：未綁定 → (ident name)
      (isinstance form Symbol)
        (do
          ;; 字串拆解：p->x, obj.x, i++, ++i, 0.5f
          (setv cooked (cook-symbol form))
          (if (!= cooked form)
              cooked                                  ; 拆出複合形式
              (if (bound? compiler (str form))
                  form                                 ; 已綁定 → 原樣（Lisp 求值）
                  `(ident '~form))))                  ; 未綁定 → C 識別字

      ;; Expression：先看 head
      (isinstance form Expression)
        (do
          (setv head (get form 0))
          (cond
            ;; 特殊形式：不要動（if/for/setv/defn/...）
            (and (isinstance head Symbol) (in (str head) HYMERA-SPECIAL-FORMS))
              form
            ;; head 未綁定 → C 函式呼叫
            (and (isinstance head Symbol) (not (bound? compiler (str head))))
              `(function-call '~head ~@(lfor x (list (cut form 1 None)) (quoty x compiler)))
            ;; head 綁定 → 維持 call，但遞迴處理 args
            True
              (hy.models.Expression
                [head ~@(lfor x (list (cut form 1 None)) (quoty x compiler))])))

      ;; List/Dict/字面值 → 原樣
      True form))

  (defn cook-symbol [sym]
    "處理 p->x / obj.x / i++ / ++i / 0.5f 等字串級拆解。"
    (setv s (str sym))
    (cond
      (.endswith s "++")  `(post++ ~(Symbol (cut s 0 -2)))
      (.endswith s "--")  `(post-- ~(Symbol (cut s 0 -2)))
      (.startswith s "++") `(pre++ ~(Symbol (cut s 2 None)))
      (.startswith s "--") `(pre-- ~(Symbol (cut s 2 None)))
      (and (in "->" s) (not (= s "->"))) (split-arrow s)
      (and (in "." s) (not (.startswith s ".")) (not (.endswith s ".")))
        (split-dot s)
      True sym)))
```

### 「特殊形式不轉換」清單

`HYMERA-SPECIAL-FORMS` 至少包含：
- Hy 核心：`quote`、`quasiquote`、`unquote`、`unquote-splice`、`setv`、`fn`、`do`、`let`、`require`、`import`、`annotate`、`yield`、`await`、`raise`、`try`、`except`、`finally`、`global`、`nonlocal`、`del`
- hymera 自家頂層宏：`function`、`decl`、`include`、`define`、`struct`、`typedef`、`enum`、`if`、`for`、`while`、`do-while`、`switch`、`case`、`default`、`return`、`break`、`continue`、`class`、`namespace`、`template`、`using-namespace`、`using-decl`、`using-alias`、`new`、`delete`

擴充新宏時必須同步把名稱加進這份清單。

## 與 c-mera 的微差

| 場景 | c-mera | hymera v1 |
|---|---|---|
| `(printf "hi")` 在 module 起始 | ✅ printf 變 C 函式呼叫 | ✅ 同 |
| `(setv x 10)` 後再 `(printf x)` | x 視為 Lisp 變數 | ✅ x 已在 `scope.defined`，視為 Lisp 變數 |
| `(defn helper ...)` 後 `(helper a)` | helper 視為 Lisp 函式 | ✅ helper 已在 `scope.defined` |
| Reader 字串便利 `arr[i]` | ✅ 拆 token 變 `(aref arr i)` | ❌ Hy 的 `[` 是語法分隔符；需顯式 `(aref arr i)`。見 ADR 0004 |
| 動態 `(let ((x 1)) (printf x))` | x 視為 Lisp 變數 | ✅ `let` 透過 `ScopeLet` 改寫綁定 |

## 後果

### 正面
- 使用者體驗對齊 c-mera，學習曲線降低。
- 寫 `(printf "%d" x)` 不必包 `(call ...)`，視覺重量明顯減輕。

### 負面
- **複雜度**：quoty 函式要正確處理所有特殊形式、巢狀 quasiquote、宏自展開後再走 quoty 等場景。
- **錯誤訊息變糊**：使用者寫錯 Lisp 變數名時可能會被「靜默地」變成 C 識別字，導致編譯期錯誤位於生成的 C 端而非源 Hy 端。緩解：debug 模式（環境變數 `HYMERA_QUOTY_VERBOSE=1`）列印每個轉換。
- **`HYMERA-SPECIAL-FORMS` 維護負擔**：新增宏時記得登記。實作上做成一個註冊 decorator `@hymera-special-form`，新增宏時順手標記，避免遺漏。

## 連結

- c-mera quoty：`projects/c-mera/src/c-mera/utils.lisp:53`
- 對應分析：`analysis/c-mera/architecture/level4_syntax_macros.md` §「三個搬運工具」
- 實測支撐：`analysis/hy/tutorial/11_macros_advanced.md` §7（`_hy_compiler`）
- hymera 實作位置：`src/hymera/syntax/quoty.hy`
