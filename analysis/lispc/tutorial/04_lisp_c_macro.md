# LISP/c 深度探索 (04)：Lisp/C-Macro 的魔力

這是 LISP/c 最強大的地方：**在 C 程式碼生成之前，先執行 Lisp 運算。**

## 1. Template vs. Lisp/C-Macro
*   **Template (模板)**（`c.lisp:701`）：簡單的文字/語法替換，底層使用 `replacify`（`c.lisp:397`）。類似 C++ 的 Template 或進階版的 `#define`。
*   **Lisp/C-Macro**（Lisp 巨集定義 `c.lisp:44`，LISP/c 翻譯函式 `c.lisp:694`）：它是一個**真正的 Common Lisp 函數**。它在翻譯時運行，可以做遞迴、條件判斷、清單處理，最後回傳一個「語法樹」給編譯器。

## 2. 語法結構
（`lisp/c-macro` → `c.lisp:44` 和 `c.lisp:694`）
```lisp
(lisp/c-macro [名稱] ([參數])
    (Lisp 代碼...))
```

## 3. 經典範例：自動生成巢狀迴圈 (Loop Unrolling)
（`for` → `c.lisp:506`，`var` → `c.lisp:555`，`++` 前置 → `c.lisp:447`）
假設您需要生成 5 層巢狀迴圈，手寫很累。我們可以用宏來遞迴生成：

```lisp
(lisp/c-macro for-nested (vars limits &rest body)
    (if (or (null vars) (null limits))
        `(progn ,@body) ;; 如果沒有變數了，就直接放主體
        `(for (var ,(car vars) int 0) (< ,(car vars) ,(car limits)) (++ ,(car vars))
            (for-nested ,(cdr vars) ,(cdr limits) ,@body))))

;; 使用方式：
(main
    (for-nested (i j k) (3 4 5)
        (@printf (str "%d %d %d\\n") i j k)))
```
**翻譯後的 C 程式碼：** 會自動產生三層 `for` 迴圈。

## 4. 範例：根據清單自動生成 Struct 成員
（`struct` → `c.lisp:569`，`var` → `c.lisp:555`，`t*`/`typ*` → `c.lisp:473`）
如果您有一組設定清單，想自動生成對應的變數宣告：

```lisp
(lisp/c-macro auto-vars (name-list type)
    `(progn
        ,@(mapcar (lambda (name) `(var ,name ,type)) name-list)))

;; 使用方式：
(struct config
    (auto-vars (timeout retry-count port) int)
    (auto-vars (ip-address domain) (t* char)))
```
**這在 C 語言中是做不到的**，因為 C 的預處理器無法走訪（Iterate）一個清單。

## 5. 為什麼這很重要？
1.  **DRY (Don't Repeat Yourself)**：您可以將複雜的模式抽象化。
2.  **效能**：所有的邏輯都在「編譯時期」完成，產出的 C 程式碼是純粹且高效的。
3.  **維護性**：修改一個 Lisp 宏，就能改變全專案數千行重複的 C 代碼。

## 6. 注意事項
*   在 `lisp/c-macro` 內部使用的是 Common Lisp。
*   輸出的代碼通常要使用「反引號 (Backtick \`)」與「逗號 (Comma ,)」來建立語法模板。
*   這是高階技術，建議在熟悉 Common Lisp 的 List 處理後再深入。
