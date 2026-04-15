# 翻譯錯誤處理 (10)

當你在自己的程式中大量呼叫 `cof`/`c` 來把 quoted list 轉成 C 程式碼時，翻譯可能因各種原因失敗。本章說明錯誤的種類、如何捕捉它們，以及如何在生產環境中建立穩健的翻譯包裝。

---

## 會發生的錯誤種類

### 1. 未知關鍵字（Undefined Function）

最常見的錯誤。當你用了 LISP/c 不認識的關鍵字時（`c.lisp:377–391`），CLISP 會拋出 `UNDEFINED-FUNCTION` 條件：

```lisp
(cof '(blahblah x y))
;; *** - EVAL: undefined function BLAHBLAH-C
```

原因：`cof` 嘗試呼叫 `blahblah-c`，但這個函式不存在。

### 2. 參數數量或型別錯誤

傳了錯誤的參數數量，或傳了不該傳的型別：

```lisp
(cof '(if))          ;; if-c 預期至少一個參數
;; *** - EVAL: ...wrong number of arguments...

(cof '(var 123 int)) ;; 123 不是有效的識別字
;; 可能輸出奇怪的 C 字串，或拋出 TYPE-ERROR
```

### 3. `lispmacro` 重複定義

如果用 `lispmacro` 定義了一個已存在的函式（不是先前由 lispmacro 定義的），翻譯不會拋出 Lisp 錯誤，而是把錯誤訊息**寫入 C 輸出**（`c.lisp:686–689`）：

```lisp
(cof '(lispmacro var (x) x))
;;=> "/**ERROR: \"VAR\" ALREADY DEFINED.**/"
```

這個錯誤藏在字串裡，不會中斷執行。

### 4. 巢狀結構中的錯誤

錯誤可以發生在任意深度：

```lisp
(cof '(func add int ((a int) (b int))
        (bad-keyword x)))
;; *** - EVAL: undefined function BAD-KEYWORD-C
;; 整個翻譯失敗，不會有部分結果
```

---

## 基本捕捉：`handler-case`

Common Lisp 的 `handler-case`（相當於 try/catch）可以捕捉所有翻譯錯誤：

```lisp
(load "c.lisp")

(defun safe-cof (expr)
  "翻譯一個 S-expression；失敗時回傳 nil 和錯誤訊息"
  (handler-case
    (values (cof expr) nil)
    (error (e)
      (values nil (format nil "~a" e)))))

;; 使用
(multiple-value-bind (result err)
    (safe-cof '(func add int ((a int) (b int)) (return (+ a b))))
  (if err
    (format t "ERROR: ~a~%" err)
    (format t "OK: ~a~%" result)))
```

---

## 生產環境用的翻譯包裝

以下是一個較完整的包裝，適合在大量使用 `cof` 的程式中作為統一入口：

```lisp
(load "c.lisp")

(defun translate (expr &key (on-error :comment) context)
  "把一個 S-expression 翻譯成 C 字串。

   :on-error 控制失敗時的行為：
     :comment  — 回傳 /* ERROR: ... */ 注解字串（預設）
     :nil      — 回傳 nil
     :signal   — 重新拋出錯誤

   :context 是一個字串，用於錯誤訊息中說明是在翻譯什麼"
  (handler-case
    (let ((result (cof expr)))
      ;; 檢查是否有「藏在字串裡」的錯誤訊息（lispmacro 重複定義）
      (if (and (stringp result)
               (search "/**ERROR:" result))
        (ecase on-error
          (:comment result)
          (:nil     nil)
          (:signal  (error "LISPC embedded error in output: ~a" result)))
        result))
    (error (e)
      (let ((msg (format nil "~a~@[ [context: ~a]~]" e context)))
        (ecase on-error
          (:comment (format nil "/* TRANSLATION ERROR: ~a */" msg))
          (:nil     nil)
          (:signal  (error "~a" msg)))))))

;; 批量翻譯：收集結果與錯誤
(defun translate-all (exprs &key (on-error :skip))
  "翻譯一個 expression 列表，回傳 (results errors)。
   :on-error :skip = 跳過失敗的項目，:keep = 保留錯誤注解"
  (let (results errors)
    (dolist (expr exprs)
      (handler-case
        (push (cof expr) results)
        (error (e)
          (push (cons expr (format nil "~a" e)) errors)
          (when (eq on-error :keep)
            (push (format nil "/* ERROR translating ~s: ~a */" expr e) results)))))
    (values (nreverse results) (nreverse errors))))
```

使用範例：

```lisp
;; 成功
(translate '(func add int ((a int) (b int)) (return (+ a b))))
;;=> "int add(int a,int b){...}"

;; 失敗，預設回傳 comment
(translate '(unknwon-keyword x))
;;=> "/* TRANSLATION ERROR: EVAL: undefined function UNKNWON-KEYWORD-C */"

;; 失敗，回傳 nil
(translate '(unknwon-keyword x) :on-error :nil)
;;=> NIL

;; 批量，跳過錯誤
(multiple-value-bind (ok errs)
    (translate-all '((var x int 0)
                     (bad-thing x)
                     (var y float 1.0)))
  (format t "Translated ~d exprs, ~d errors~%" (length ok) (length errs))
  (dolist (e errs)
    (format t "  FAILED: ~s -> ~a~%" (car e) (cdr e))))
```

---

## 輸入驗證：在翻譯前檢查

有些錯誤可以在呼叫 `cof` 之前就發現：

```lisp
(defun valid-lispc-expr-p (expr)
  "快速檢查一個 expression 是否可能合法（不保證翻譯成功）"
  (cond
    ((null expr)   t)           ;; nil 合法（翻譯成 ""）
    ((atom expr)   t)           ;; 單一 symbol/數字 合法
    ((not (listp expr)) nil)    ;; 不是 list 也不是 atom：不合法
    ((null (car expr)) nil)     ;; (nil ...) 不合法
    ;; 如果 car 是 symbol，檢查對應的 -c 函式是否存在
    ;; 排除特殊前綴字元 @ [] & ^ * = -（這些是 cof 內部處理的）
    ((symbolp (car expr))
     (let* ((s (symbol-name (car expr)))
            (first-char (char s 0)))
       (or (member first-char '(#\@ #\[ #\] #\& #\^ #\* #\= #\-))
           (fboundp (intern (format nil "~a-C" s))))))
    (t t)))

;; 使用
(valid-lispc-expr-p '(var x int 0))    ;;=> T
(valid-lispc-expr-p '(blahblah x))     ;;=> NIL  (快速失敗)
(valid-lispc-expr-p '(@printf (s. "hi"))) ;;=> T  (@ 前綴直接通過)
```

---

## 找出翻譯結果中藏著的錯誤

`lispmacro` 重複定義的錯誤不會拋出 Lisp condition，而是以 `/**ERROR:...**/` 注解混在 C 輸出裡（`c.lisp:688`）。翻譯完成後要主動掃描：

```lisp
(defun check-output-for-errors (c-code)
  "掃描 C 程式碼字串，找出 LISP/c 嵌入的錯誤注解。
   回傳 (has-errors-p error-messages-list)"
  (let ((errors '())
        (start 0))
    (loop
      (let ((pos (search "/**ERROR:" c-code :start2 start)))
        (unless pos (return))
        (let ((end (search "**/" c-code :start2 (+ pos 9))))
          (when end
            (push (subseq c-code (+ pos 2) (+ end 3)) errors))
          (setf start (if end (+ end 3) (length c-code))))))
    (values (not (null errors)) (nreverse errors))))

;; 使用
(let ((output (c '(lispmacro var (x) x)   ;; 故意觸發 lispmacro 衝突
                 '(var y int 0))))
  (multiple-value-bind (has-err msgs)
      (check-output-for-errors output)
    (when has-err
      (format t "Found ~d error(s) in output:~%" (length msgs))
      (dolist (m msgs) (format t "  ~a~%" m)))))
```

---

## 測試你的 `cof` 呼叫

建議為你程式中每個「動態組裝 + 翻譯」的路徑寫對應的測試：

```lisp
(defun assert-translates-to (expr expected-substring &optional label)
  "確認 expr 翻譯後的結果包含 expected-substring"
  (let ((result (handler-case
                  (cof expr)
                  (error (e) (format nil "ERROR: ~a" e)))))
    (if (search expected-substring result)
      (format t "[PASS]~@[ ~a~]~%" label)
      (format t "[FAIL]~@[ ~a~] expected ~s in ~s~%" label expected-substring result))
    result))

(defun assert-translation-fails (expr &optional label)
  "確認 expr 翻譯時會拋出錯誤"
  (handler-case
    (progn (cof expr)
           (format t "[FAIL]~@[ ~a~] expected error but got success~%" label))
    (error ()
      (format t "[PASS]~@[ ~a~] (correctly errored)~%" label))))

;; 測試範例
(assert-translates-to '(var x int 0) "int x" "basic var")
(assert-translates-to '(func add int ((a int)) (return a)) "int add" "basic func")
(assert-translation-fails '(nonexistent-keyword 1 2 3) "undefined keyword")
```

---

## 錯誤處理策略選擇

| 情境 | 建議策略 |
|------|---------|
| 開發/除錯時 | `(translate expr :on-error :signal)` — 讓錯誤直接浮出 |
| 批量程式碼生成，允許部分失敗 | `(translate-all exprs :on-error :skip)` + 事後報告 |
| 生成的程式碼會立刻交給 GCC 編譯 | `:on-error :comment`，讓 GCC 的錯誤訊息也指出哪裡有問題 |
| 生成的程式碼是核心功能，不能有任何錯誤 | `:on-error :signal` + 每個 expression 都有 `assert-translates-to` 測試 |
