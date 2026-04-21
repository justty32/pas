# 教學 10：Emacs / SLIME / SLY 整合 C-Mera

C-Mera 誕生於 Lisp 社群，因此 Emacs 是它的「母體」。如果你追求極致的互動開發體驗（REPL-Driven Development），Emacs + SLIME/SLY 是唯一的選擇。

## 核心組件

- **`cm-mode.el`**: 官方提供的編輯模式，負責縮排與按鍵綁定。
- **SLIME / SLY**: 連結 Emacs 與 Lisp 實作（CCL/SBCL）的橋樑。
- **`cm-reader`**: 讓 Lisp REPL 識別 C-Mera 語法的關鍵函式。

## 一、安裝 `cm-mode`

`cm-mode.el` 位於 `util/emacs/cm-mode.el`。你可以將它加到你的 `load-path`：

```elisp
(add-to-list 'load-path "/path/to/c-mera/util/emacs/")
(require 'cm-mode)

;; 自動對 .lisp 檔案開啟 cm-mode (它繼承自 lisp-mode)
(add-to-list 'auto-mode-alist '("\\.lisp\\'" . cm-mode))
```

## 二、配置縮排

C-Mera 的 DSL（如 `function`, `decl`, `for`）在標準 `lisp-mode` 下縮排會很難看。`cm-mode` 已經內建了常見關鍵字的縮排規則。

如果你有自定義的巨集，可以在檔案中加入：

```lisp
;; -*- cm-indent: ((my-macro 1) (with-timer 1)) -*-
```

或者在 Emacs 中全域設定：

```elisp
(put 'function 'common-lisp-indent-function 2)
(put 'decl 'common-lisp-indent-function 1)
```

## 三、互動式工作流 (The SLIME/SLY Way)

這是 C-Mera 最強大的地方：**你不需要離開編輯器就能看到 C 代碼**。

1. **啟動 REPL**: `M-x slime` 或 `M-x sly`。
2. **載入 C-Mera**:
   在 REPL 中輸入：
   ```lisp
   (asdf:load-system :cmu-c++)
   (in-package :cmu-c++)
   (cm-reader)  ; 重要：切換到 C-Mera 的讀取器
   ```
3. **即時展開**:
   將游標放在一個 `function` 或 `defmacro` 上，按 `C-c C-m` (slime-macroexpand-1)。
   SLIME 會彈出一個視窗，顯示展開後的 AST。

4. **即時預覽 C 代碼**:
   在檔案中寫一個輔助函式：
   ```lisp
   (defun preview ()
     (cm-c:simple-print (your-current-form)))
   ```
   或者直接選中代碼塊，按 `C-c C-e` 求值，結果會印在 REPL。

## 四、`cm-mode` 快捷鍵

| 按鍵 | 功能 |
|---|---|
| `C-c C-c` | 編譯當前定義 (Compile Defun) |
| `C-c C-m` | 展開當前巨集 (Macroexpand) |
| `C-c C-l` | 載入整個檔案到 REPL |
| `C-c C-z` | 切換到 REPL 視窗 |

## 五、進階：自動化建置

你可以定義一個 Emacs 函式來呼叫 `cm` 指令：

```elisp
(defun cmera-build-current-file ()
  "呼叫外部 cm 指令編譯當前檔案。"
  (interactive)
  (save-buffer)
  (let ((cmd (format "cm c++ %s -o %s.cpp" 
                     (buffer-file-name) 
                     (file-name-sans-extension (buffer-file-name)))))
    (message "Running: %s" cmd)
    (shell-command cmd)))

(define-key cm-mode-map (kbd "C-c C-b") 'cmera-build-current-file)
```

## 六、常見問題

1. **為什麼我的 `if` 縮排變亂了？**
   因為 `cm-mode` 會遮蔽 (shadow) Common Lisp 原生的 `if` 縮排。確保你是在 `(in-package :cmu-c)` 下工作。
2. **如何處理多個後端？**
   如果你同時在寫 C 和 CUDA，建議在檔案開頭使用 `File Variables`：
   ```lisp
   ;; -*- mode: cm; cm-backend: cuda -*-
   ```

## 總結

Emacs + C-Mera 的核心在於 **「模糊編譯期與執行期的界線」**。你可以在寫 C 代碼的同時，利用 Lisp REPL 測試你的邏輯生成器，這比傳統的「寫檔 -> 編譯 -> 報錯 -> 改檔」循環快上數倍。
