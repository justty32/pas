# Hy (Hylang) 專案總覽 (00_overview.md)

本文件提供 Hy 的高層次介紹，幫助你理解為什麼要使用 Hy 以及它在 Python 生態系中的地位。

## 1. 核心哲學：當 Lisp 遇上 Python
Hy 不是一個運行在 Python 之上的解釋器，它**就是** Python。Hy 原始碼在編譯階段會直接轉換為 Python 的抽象語法樹 (AST)。

*   **100% 兼容性**：任何 Python 能做的，Hy 都能做；反之亦然。
*   **強大的元編程**：利用 Lisp 的「程式碼即數據」(Homoiconicity) 特性，透過宏 (Macros) 在編譯期生成程式碼。
*   **簡潔的語法**：擺脫縮進限制與繁瑣的標點符號，使用 S-表達式管理邏輯。

---

## 2. 環境建置與第一個程式

### 安裝
推薦在虛擬環境中安裝：
```bash
pip install hy
```

### 第一個程式：hello.hy
創建一個名為 `hello.hy` 的文件：
```hylang
;; hello.hy
(defn greet [name]
  "這是一個簡單的問候函數"
  (print f"哈囉，{name}！歡迎來到 Hy 的世界。"))

(if (= __name__ "__main__")
  (greet "開發者"))
```

### 執行方式
1.  **直接執行**：`hy hello.hy`
2.  **查看編譯後的 Python**：`hy2py hello.hy`
    *   這會顯示 Hy 是如何將 Lisp 轉換為等效的 Python 程式碼的。

---

## 3. 核心工具鏈
*   **hy**: 編譯並執行 Hy 程式，或啟動 REPL。
*   **hyc**: 將 Hy 文件編譯為 Python 字節碼 (`.pyc`)。
*   **hy2py**: 將 Hy 原始碼轉換為 Python 原始碼，是學習 Hy 對應關係的最佳工具。

---

## 4. 學習路徑建議
1.  **01_basic**: 掌握前綴表達式與基礎類型。
2.  **02_advance**: 學習函數定義與流程控制。
3.  **03_containers**: 熟悉 Python 資料結構在 Hy 中的展現。
4.  **04_modules**: 理解 Python 模組導入與 Hy 宏的特殊處理。
5.  **05_meta_programming**: 探索 Lisp 最強大的宏系統。
6.  **06_details**: 深入了解名稱重整與底層互操作細節。
