# LISP/c 環境準備與執行教學 (Prepare)

本教學將引導您從零開始安裝 Common Lisp 環境，並一步步完成 LISP/c 程式的撰寫、編譯與執行。

---

## 第一步：安裝 CLISP 與 GCC

LISP/c 需要 **CLISP** (Common Lisp 的一種實作) 來執行翻譯引擎，並需要 **GCC** 來將產出的 C 程式碼編譯成執行檔。

### 1. Windows 系統
*   **CLISP**: 建議前往 [CLISP 官方下載頁面](https://sourceforge.net/projects/clisp/files/clisp/) 下載安裝檔，或是使用 `scoop` 安裝：`scoop install clisp`。
*   **GCC**: 安裝 [MinGW-w64](https://www.mingw-w64.org/) 或使用 `scoop install gcc`。

### 2. Linux (Ubuntu/Debian)
執行以下指令：
```bash
sudo apt update
sudo apt install clisp gcc
```

### 3. macOS
使用 Homebrew 安裝：
```bash
brew install clisp gcc
```

---

## 第二步：準備專案檔案

請確保您的資料夾中包含以下檔案：
1.  `c.lisp`: LISP/c 的核心翻譯引擎（專案內建）。
2.  `my_app.cl`: 您的 Lispsy 原始碼（稍後建立）。

---

## 第三步：撰寫您的第一個程式

建立一個名為 `my_app.cl` 的檔案，內容如下：

```lisp
(header stdio)

(func say-hello void ((name (t* char)))
    (@printf (str "哈囉, %s! 歡迎來到 LISP/c 的世界。\\n") name))

(main
    (@say-hello (str "開發者"))
    (return 0))
```

---

## 第四步：執行翻譯與編譯

您可以選擇「手動兩步法」或「自動一步法」。

### 方法 A：手動兩步法 (理解流程用)

1.  **進入 CLISP 並載入引擎**：
    在終端機輸入 `clisp`，進入後輸入：
    ```lisp
    (load "c.lisp")
    ```

2.  **將 .cl 翻譯成 .c**：
    ```lisp
    (c-cl-file "my_app.cl" "my_app.c")
    ```
    完成後輸入 `(quit)` 離開 Lisp。

3.  **使用 GCC 編譯 C 代碼**：
    在終端機輸入：
    ```bash
    gcc my_app.c -o my_app
    ```

4.  **執行**：
    ```bash
    ./my_app
    ```

### 方法 B：自動一步法 (開發最快)

LISP/c 內建了整合指令，可以直接完成編譯與執行：

1.  進入 `clisp` 並載入 `(load "c.lisp")`。
2.  執行：
    ```lisp
    (compile-and-run-cl-file "my_app.cl")
    ```
    這會自動呼叫 GCC 並直接執行結果。

---

## 常見問題排查 (Troubleshooting)

*   **找不到指令**: 請確保 `clisp` 和 `gcc` 已經加入您的系統環境變數 (PATH)。
*   **路徑問題**: 建議在專案根目錄執行，確保 `c.lisp` 與您的 `.cl` 檔案在同一個資料夾。
*   **語法錯誤**: 如果翻譯時出錯，請檢查括號是否成對，Lisp 對括號的完整性非常敏感。

恭喜！您已經完成了 LISP/c 的環境準備。接下來可以參考 `01_basic.md` 開始深入學習語法！
