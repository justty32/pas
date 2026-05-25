# 教學 10：Emacs / SLIME / SLY 整合 C-Mera

C-Mera 誕生於 Lisp 社群，因此 Emacs 是它的「母體」。如果你追求極致的互動開發體驗（REPL-Driven Development），Emacs + SLIME/SLY 是最完整的選擇。

---

## 一、安裝 `cm-mode`

`cm-mode.el` 在 `util/emacs/cm-mode.el`。加進 `load-path`：

```elisp
;; ~/.emacs.d/init.el 或 ~/.config/emacs/init.el

(add-to-list 'load-path "/path/to/c-mera/util/emacs/")
(require 'cm-mode)

;; 讓 .lisp 檔案自動使用 cm-mode（它繼承自 lisp-mode）
(add-to-list 'auto-mode-alist '("\\.lisp\\'" . cm-mode))
```

或者用 `use-package` 搭配 `straight.el`：

```elisp
;; 直接從本地路徑載入
(use-package cm-mode
  :load-path "/path/to/c-mera/util/emacs/"
  :mode "\\.lisp\\'")
```

---

## 二、安裝 SLIME 或 SLY

**SLIME**（較傳統，穩定）：

```bash
# 透過 Quicklisp 安裝（在 CCL/SBCL 的 REPL 裡）
(ql:quickload :swank)
```

在 Emacs 裡：

```elisp
;; M-x package-install RET slime RET
(setq inferior-lisp-program "ccl")   ; 或 "sbcl"
(require 'slime)
(slime-setup '(slime-fancy slime-repl))
```

**SLY**（SLIME 的現代 fork，推薦新手）：

```elisp
;; M-x package-install RET sly RET
(setq inferior-lisp-program "ccl")
(require 'sly)
```

---

## 三、縮排設定

C-Mera 的 DSL（`function`、`decl`、`for` 等）在標準 `lisp-mode` 下縮排不好看。`cm-mode` 已內建常見關鍵字的縮排規則。

針對自訂巨集，有兩種方式：

**方式 A：檔案區域設定（per-file）**

在每個 `.lisp` 檔案頂端加：

```lisp
;; -*- mode: cm; cm-indent: ((my-loop 1) (with-resource 2)) -*-
```

**方式 B：全域設定（all files）**

```elisp
;; cm-mode 繼承 lisp-mode 的縮排系統
(put 'function    'common-lisp-indent-function 2)
(put 'decl        'common-lisp-indent-function 1)
(put 'for         'common-lisp-indent-function 1)
(put 'when        'common-lisp-indent-function 1)
(put 'while       'common-lisp-indent-function 1)
(put 'switch      'common-lisp-indent-function 1)
(put 'namespace   'common-lisp-indent-function 1)
(put 'class       'common-lisp-indent-function 2)
(put 'template    'common-lisp-indent-function 1)
(put 'catching    'common-lisp-indent-function 1)
(put 'macrolet    'common-lisp-indent-function 1)
```

---

## 四、互動式工作流（REPL-Driven Development）

這是 C-Mera 最強大的工作方式，完全不需要離開編輯器就能看到 C 程式碼。

### 4-1 啟動 REPL 並載入 C-Mera

```
M-x slime   ; 或 M-x sly
```

在 REPL 裡：

```lisp
;; 載入 C++ 後端（或 :cmu-c 只用 C）
(asdf:load-system :cmu-c++)
(in-package :cmu-c++)

;; 切換到 C-Mera 的 reader（重要！否則 -> 等符號無法正確剖析）
(cm-reader)
```

### 4-2 即時預覽 C 輸出

寫好一個 `function` form，游標在 form 裡面，用 SLIME 的 `C-c C-p`（Pretty-print）或直接在 REPL 呼叫：

```lisp
;; 在 REPL 裡：把你的 form 包在 simple-print 裡
(cm-cxx:simple-print
  (function add ((int a) (int b)) -> int
    (return (+ a b))))
```

REPL 立刻輸出：

```c
int add(int a, int b)
{
    return a + b;
}
```

### 4-3 展開 macro 看 AST

游標在 `(defmax int)` 這個 form 上，按 `C-c C-m`（`slime-macroexpand-1`）。SLIME 彈出視窗，顯示展開後的 sexp（還不是 C，是 C-Mera 的 AST）。再次展開可以看更深的層次。

### 4-4 完整 REPL 工作流示範

```lisp
;; 在 REPL 裡一步一步測試

;; 1. 定義一個 macro
(defmacro defmax (type)
  (let ((name (cintern (format nil "max_~a" type))))
    `(function ,name ((,type a) (,type b)) -> ,type
       (if (> a b) (return a) (return b)))))

;; 2. 展開看看
(macroexpand-1 '(defmax int))
;; => (FUNCTION MAX_INT ((INT A) (INT B)) -> INT (IF (> A B) (RETURN A) (RETURN B)))

;; 3. 看最終 C 輸出
(cm-cxx:simple-print (defmax int))
;; int max_int(int a, int b)
;; {
;;     if (a > b)
;;         return a;
;;     return b;
;; }

;; 4. 批次產生
(cm-cxx:simple-print
  (defmax int)
  (defmax float)
  (defmax double))
```

---

## 五、快捷鍵總覽

| 按鍵 | SLIME 功能 | 說明 |
|---|---|---|
| `C-c C-c` | `slime-compile-defun` | 編譯游標所在的 top-level form |
| `C-c C-l` | `slime-load-file` | 載入整個 `.lisp` 檔案 |
| `C-c C-m` | `slime-macroexpand-1` | 展開一層 macro |
| `C-c M-m` | `slime-macroexpand-all` | 全部展開 |
| `C-c C-p` | `slime-pprint-eval-last-expression` | 格式化輸出最後一個運算式 |
| `C-c C-z` | `slime-switch-to-output-buffer` | 切到 REPL |
| `C-c C-d d` | `slime-describe-symbol` | 查詢符號說明 |

---

## 六、自動化建置（呼叫外部 `cm`）

```elisp
(defun cmera-detect-backend ()
  "偵測當前 .lisp 檔是 C 還是 C++ 後端。"
  (save-excursion
    (goto-char (point-min))
    (if (re-search-forward "cm:\\s-*c\\+\\+" nil t)
        "c++"
      "c")))

(defun cmera-build ()
  "呼叫外部 cm 指令，把當前檔案翻譯成 C/C++，輸出到 *cmera-output* buffer。"
  (interactive)
  (save-buffer)
  (let* ((backend (cmera-detect-backend))
         (file    (buffer-file-name))
         (out     (concat (file-name-sans-extension file)
                          (if (string= backend "c++") ".cpp" ".c")))
         (cmd     (format "cm %s %s -o %s" backend file out)))
    (message "C-Mera: %s" cmd)
    (with-current-buffer (get-buffer-create "*cmera-output*")
      (erase-buffer)
      (insert (format "$ %s\n\n" cmd))
      (let ((exit (call-process-shell-command cmd nil t)))
        (if (= exit 0)
            (progn
              (insert (format "\n\n=== 產生：%s ===\n" out))
              (insert-file-contents out)
              (c++-mode)
              (message "C-Mera: 成功 → %s" out))
          (message "C-Mera: 建置失敗（exit %d），見 *cmera-output*" exit))))
    (display-buffer "*cmera-output*")))

;; 建置並執行
(defun cmera-run ()
  "建置並執行，輸出到 *cmera-run* buffer。"
  (interactive)
  (save-buffer)
  (let* ((backend (cmera-detect-backend))
         (file    (buffer-file-name))
         (compiler (if (string= backend "c++") "g++" "gcc"))
         (tmpc (make-temp-file "cmera" nil (if (string= backend "c++") ".cpp" ".c")))
         (tmpe (make-temp-file "cmera-bin")))
    (let ((cmd (format "cm %s %s -o %s && %s %s -o %s && %s"
                       backend file tmpc compiler tmpc tmpe tmpe)))
      (with-current-buffer (get-buffer-create "*cmera-run*")
        (erase-buffer)
        (call-process-shell-command cmd nil t)
        (message "C-Mera: 執行完成"))
      (display-buffer "*cmera-run*"))))

;; 綁定到 cm-mode
(with-eval-after-load 'cm-mode
  (define-key cm-mode-map (kbd "C-c C-b") #'cmera-build)
  (define-key cm-mode-map (kbd "C-c C-r") #'cmera-run))
```

---

## 七、常見問題

**Q：為什麼 `if` 的縮排在 cm-mode 裡變亂了？**

`cm-mode` 繼承 `lisp-mode` 的縮排，但 `if` 在 C-Mera 是控制流程（第一個子 form 後縮 2 格），而在 Lisp 裡是 `(if cond then else)`（縮 4 格）。確保你在 `(in-package :cmu-c)` 環境下工作，讓 cm-mode 的規則生效。

**Q：REPL 的 `->` 被解讀成 Lisp 符號了？**

忘了呼叫 `(cm-reader)` 切換 reader。這個步驟是必要的，且每次新連接 REPL 都要做一次。

**Q：如何同時編輯 C 和 C++ 的 `.lisp` 檔？**

在檔案頂端加 File Variables 讓 Emacs 自動選後端：

```lisp
;; -*- mode: cm; cm-backend: c++ -*-
```

**Q：`simple-print` 說找不到函式**

確認 package 正確：用 `(in-package :cmu-c)` 後用 `cm-c:simple-print`；用 `(in-package :cmu-c++)` 後用 `cm-cxx:simple-print`。

---

## 八、Emacs 整合的核心優勢

Emacs + C-Mera 的真正價值是**「模糊編譯期與開發期的界線」**：

- 寫 macro 的同時，在 REPL 裡立刻展開看它長什麼樣。
- 不用離開編輯器就能確認產出的 C 程式碼正確。
- `macroexpand-1` 一步一步看展開過程，找 macro 問題比 `printf` 調試快很多。

這比「寫 .lisp → 跑 cm → 看 .c → 發現錯誤 → 回去改」的循環快幾倍。
