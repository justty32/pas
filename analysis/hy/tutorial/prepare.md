# Hy (Hylang) 環境準備與實戰快速上手 (prepare.md)

本指南旨在為初學者提供「手把手」的引導，從環境建置到運行一個具備模組化設計的 Hy 程式。

---

## 1. 環境安裝與虛擬環境建置

使用虛擬環境是 Python 開發的最佳實踐，它能確保 Hy 的安裝不會污染你的系統環境。

### 第一步：建立工作目錄
打開你的終端機 (Terminal 或 PowerShell)，輸入以下指令：

```bash
# 建立一個新的專案資料夾
mkdir my_hy_project
cd my_hy_project
```

### 第二步：初始化虛擬環境 (venv)
根據你的作業系統，執行對應的指令：

**Windows (PowerShell):**
```powershell
# 建立虛擬環境資料夾 venv
python -m venv venv

# 啟動虛擬環境 (這會讓你的命令列前方出現 (venv) 字樣)
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
# 建立虛擬環境資料夾 venv
python3 -m venv venv

# 啟動虛擬環境
source venv/bin/activate
```

### 第三步：安裝 Hy 與相關工具
啟動虛擬環境後，升級 pip 並安裝 Hy：

```bash
# 確保 pip 是最新版本
python -m pip install --upgrade pip

# 安裝 Hy 核心包
pip install hy
```

### 第四步：驗證安裝結果
```bash
# 檢查版本
hy --version

# 進入互動式介面 (REPL) 測試
hy
```
進入 REPL 後輸入 `(print "Hello Hy")`，看到輸出後按 `Ctrl+D` (Linux/macOS) 或 `Ctrl+Z` (Windows) 退出。

---

## 2. 實戰範例：建立一個多模組系統

我們將模擬一個簡單的「任務管理系統」，學習如何進行檔案間的導入與宏的應用。

### 目錄結構
請在 `my_hy_project` 目錄下建立以下檔案：
```text
my_hy_project/
├── core_macros.hy   (定義編譯期工具)
├── logic.hy         (定義運算邏輯)
└── main.hy          (程式主入口)
```

### 檔案一：core_macros.hy (定義宏)
宏必須分開存放，以便其他檔案使用 `require` 導入。

```hylang
;; core_macros.hy - 此檔案存放編譯期執行的「宏」

(defmacro log-action [action-name &rest body]
  "此宏會在執行 body 代碼前後自動印出 Log 訊息"
  `(do
     (print f"[LOG] 開始執行：{~action-name}...")
     (setv result (do ~@body))
     (print f"[LOG] 執行完成，結果為: {result}")
     result))
```

### 檔案二：logic.hy (定義函數)
這裡存放一般的 Python 函數邏輯。

```hylang
;; logic.hy - 此檔案存放運行時執行的「函數」

(defn calculate-task-priority [score weight]
  "根據分數與權重計算優先級"
  (* score weight))

(defn get-status-label [priority]
  "根據優先級返回標籤文字"
  (if (> priority 50) 
      "緊急" 
      "普通"))
```

### 檔案三：main.hy (主程式)
這是我們最後執行的檔案。

```hylang
;; main.hy - 核心入口

;; 1. 導入其他檔案的函數 (使用 import)
(import [logic [calculate-task-priority get-status-label]])

;; 2. 導入其他檔案的宏 (使用 require)
(require [core_macros [log-action]])

(defn run-main []
  (print "=== 任務系統啟動 ===")
  
  ;; 使用 log-action 宏包裹一段計算邏輯
  (setv my-priority (log-action "計算核心優先級"
                       (calculate-task-priority 15 4)))
  
  ;; 使用線程宏 (->) 簡化調用鏈
  (-> my-priority
      (get-status-label)
      (print))
  
  (print "=== 系統關閉 ==="))

;; 確保直接執行此檔時才運行 run-main
(if (= __name__ "__main__")
    (run-main))
```

---

## 3. 執行與調試指令

### 執行程式
在 `my_hy_project` 目錄下執行：
```bash
hy main.hy
```
**預期輸出：**
```text
=== 任務系統啟動 ===
[LOG] 開始執行：計算核心優先級...
[LOG] 執行完成，結果為: 60
緊急
=== 系統關閉 ===
```

### 調試技巧：查看編譯後的 Python 程式碼
如果你想知道 Hy 到底把你的程式碼變成了什麼樣的 Python，可以使用 `hy2py`：
```bash
hy2py main.hy
```
這對於理解「連字號轉底線」或「宏展開」的底層運作非常有幫助。

### 查看特定函數的說明文件 (REPL 中)
如果你在 REPL 中想查看某個函數的用法：
```hylang
=> (import logic)
=> (doc logic.calculate-task-priority)
```

---

## 4. 常見問題排除 (Troubleshooting)

1. **找不到指令**: 
   - 確保你已經執行了 `activate` 指令啟動虛擬環境。
2. **ImportError**: 
   - 檢查檔名是否拼錯。
   - 記住：`import` 用於函數，`require` 用於宏。
3. **語法錯誤**:
   - 檢查括號是否成對 `()`。
   - 在 Hy 中，符號之間必須有空格，例如 `(+ 1 2)` 而不是 `(+1 2)`。

現在你已經成功運行了第一個 Hy 專案！請繼續閱讀 `01_basic.md` 深入了解細節。
