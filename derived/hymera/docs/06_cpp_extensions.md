# 06 — C++ 子集擴充

> 範圍依 `PROJECT.md` §2：class/struct + 成員、namespace、template 基本、reference declarator、auto、using declaration、new/delete。**不含** RTTI / 移動語意 / constexpr / concepts / coroutines / lambda 完整捕獲。

## 1. 多檔分工

| 檔案 | 內容 |
|---|---|
| `src/hymera/ast/cpp_nodes.hy` | C++ 節點定義（透過 `defstatement` / `defexpression`） |
| `src/hymera/emit/cpp.hy` | 上述節點的 `defprettymethod` 註冊 |
| `src/hymera/syntax/cpp.hy` | `class` / `namespace` / `template` / `using-namespace` / `using-decl` / `using-alias` / `new` / `delete` 等使用者層宏 |

Emitter 透過 `defgeneric` `traverse` 自動派到 cpp 那組；C 那邊已實作的節點型別（`if-statement` / `for-statement` / `function-definition` 等）**完全不需要重寫**，C++ 直接複用。

## 2. 節點定義（用 `defstatement` / `defexpression`）

對照 c-mera：`projects/c-mera/src/cpp/nodes.lisp`（若分析過）或在 c-mera 的 C 節點上以類似命名擴充。

```hylang
;; src/hymera/ast/cpp_nodes.hy
(import hymera.ast.base [defstatement defexpression defleaf])

;; -- 類別 ---------------------------------
(defstatement class-definition (kind) (name bases body))   ; kind: 'class or 'struct
(defstatement base-clause       (access) (name))           ; access: 'public 等
(defstatement access-specifier  (kind) ())                 ; kind: 'public/'private/'protected
(defstatement method-definition (owner) (item parameter body))  ; owner 指向 class-definition

;; -- 命名空間 -----------------------------
(defstatement namespace-definition () (name body))         ; name 為 None → 匿名 namespace

;; -- 樣板 ---------------------------------
(defstatement template-definition () (parameters target))
(defstatement template-type-param  (kind) (name default))  ; kind: 'typename or 'class
(defstatement template-value-param () (type name default))

;; -- using ---------------------------------
(defstatement using-declaration (kind) (qualified-name alias-target))
;; kind: 'namespace / 'declaration / 'type-alias

;; -- new / delete --------------------------
(defexpression new-expression    () (type ctor-args array-size))
(defexpression delete-expression (is-array?) (target))

;; -- 修飾子（給 declaration） --------------
(defleaf reference-declarator (kind) ())                   ; kind: '& or '&&（v1 只支援 &）
(defleaf auto-type             ()    ())
```

## 3. 使用者層宏

對齊 c-mera 風格，**直接使用 `class` / `namespace` / `template` 等核心化名稱**（透過 `(pragma :warn-on-core-shadow False)` 已被 syntax.c 開啟）：

```hylang
;; src/hymera/syntax/cpp.hy
(pragma :warn-on-core-shadow False)

(defmacro class [name #* body]
  "(class Stack
     (private (decl ((vec std::vector<T>))))
     (public  (function push ((const T & v)) -> void ...)))
   → class-definition 節點。body 內可直接寫 (public ...) / (private ...) / (protected ...)
   區段，由 parse-class-body 轉成 access-specifier + 後續成員的序列。"
  `(class-definition :kind 'class :name (ident '~name) :bases None
                     :body (make-nodelist ~@(parse-class-body body))))

(defmacro struct [name #* body]
  `(class-definition :kind 'struct :name (ident '~name) :bases None
                     :body (make-nodelist ~@(parse-class-body body))))

(defmacro namespace [name #* body]
  `(namespace-definition :name (ident '~name)
                         :body (make-nodelist ~@body)))

(defmacro template [params target]
  "(template ((typename T) (typename U = int)) target-node)"
  `(template-definition :parameters (make-nodelist ~@(parse-tpl-params params))
                        :target ~target))

(defmacro using-namespace [name]
  `(using-declaration :kind 'namespace
                      :qualified-name (qualify '~name)
                      :alias-target None))

(defmacro using-decl [name]
  `(using-declaration :kind 'declaration
                      :qualified-name (qualify '~name)
                      :alias-target None))

(defmacro using-alias [name target]
  `(using-declaration :kind 'type-alias
                      :qualified-name (qualify '~name)
                      :alias-target ~target))

(defmacro new [type #* args]
  `(new-expression :type (type-ref '~type)
                   :ctor-args (make-nodelist ~@args)
                   :array-size None))

(defmacro delete [target]
  `(delete-expression :is-array? False :target ~target))

(defmacro delete[] [target]
  `(delete-expression :is-array? True  :target ~target))
```

`parse-class-body` 把 `(public ...)` / `(private ...)` 區段拆成 `access-specifier` + 後續成員的扁平序列，對應 c-mera 對 C++ access 區段的處理。

## 4. 與 C 的互操作

C 那邊已提供的宏（`decl`、`function`、`if`、`for` 等）在 cpp 範圍**完全可重用**。在 class body 內：

```hylang
(class Stack
  (public
    (function push ((const T & v)) -> void
      (this->vec.push_back v))))      ; 普通 function 在 class body 內被 parse-class-body 升格為 method-definition
```

**`function` 在 ClassDefinition 的 body 裡會被特別處理**：`parse-class-body` 把 `function` 表達式改包成 `method-definition`，多帶一個 `_owner` 指向所屬 class。

## 5. 不在 v1 範圍（保留 v2 候選）

| 功能 | 為什麼 v1 不做 |
|---|---|
| 移動語意（`&&` / `std::move`） | 影響 reference declarator、function 簽章、constructor 設計，連鎖大 |
| `constexpr` / `consteval` / `constinit` | 一個獨立的「修飾子層」，要改 declaration-item 結構 |
| Lambda 完整捕獲清單（`[&, x, this]`） | 捕獲清單本身是個子語言，值得獨立節點 |
| RTTI（`typeid` / `dynamic_cast`） | 與型別系統深度耦合 |
| Concepts、coroutines、modules、可變參數模板、模板模板參數、模板偏特化 | 各自都是獨立工作量 |

每個 v2 候選都有具體理由先擺一邊。

## 6. emit 與 traverser 共用

`src/hymera/emit/cpp.hy` 只增加上面節點的 `defprettymethod`，**完全不重複** c 那邊已寫的（包含 `function-definition` / `compound-statement` / `if-statement` 等）。`defgeneric traverse` 的多重派發看到 `ClassDefinition` 走 cpp 列印，看到 `IfStatement` 走 c 列印，無需手動 dispatch。
