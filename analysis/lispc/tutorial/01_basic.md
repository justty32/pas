# LISP/c 基礎教學 (01)：從 C 到 Lispsy 的語法映射

本章將詳細介紹如何將 C 語言中最基礎的元素轉換為 LISP/c 語法。

## 1. 變數與型別 (Variables & Types)

在 LISP/c 中，宣告變數使用 `var`（`c.lisp:555`）或 `vars`（`c.lisp:564`）。

### 基本宣告
*   **C:** `int a = 10;`
*   **Lispsy:** `(var a int 10)`（`var` → `c.lisp:555`）

### 常見型別對照
LISP/c 提供了一些更具語意化的別名（Synonyms），定義於 `c.lisp:1330–1358`：
| C 型別 | Lispsy 名稱 | 別名 |
| :--- | :--- | :--- |
| `int` | `int` | `integer`（`c.lisp:1337`） |
| `long` | `long` | `integer+`（`c.lisp:1338`） |
| `float` | `float` | `real`（`c.lisp:1343`） |
| `double` | `double` | `real+`（`c.lisp:1344`） |
| `unsigned int` | `natural` | （`c.lisp:1340`） |
| `char` | `char` | `boolean`（`c.lisp:1345`） |

### 一次宣告多個變數
*   **C:** `int x, y; float z;`
*   **Lispsy:** `(vars (x y) (z float))` (預設型別為 `int`)（`vars` → `c.lisp:564`）

---

## 2. 流程控制 (Control Flow)

### 條件判斷 (if / else)
在 Lisp 中，如果 `if` 區塊需要執行多個指令，必須使用 `progn` 包起來（類似 C 的 `{}`）。（`if` → `c.lisp:492`，`progn` → `c.lisp:485`）
*   **C:**
    ```c
    if (x > 0) {
        printf("Positive");
        x--;
    } else {
        printf("Non-positive");
    }
    ```
*   **Lispsy:**
    ```lisp
    (if (> x 0)
        (progn
            (@printf (str "Positive"))
            (-- x))
        (@printf (str "Non-positive")))
    ```

### 迴圈 (Loops)
*   **For 迴圈:** `(for [初始] [條件] [步進] [主體])`（`for` → `c.lisp:506`）
    *   **C:** `for(int i=0; i<10; i++) { ... }`
    *   **Lispsy:** `(for (var i int 0) (< i 10) (++ i) ...)`
*   **While 迴圈:**（`while` → `c.lisp:509`）
    *   **C:** `while(cond) { ... }`
    *   **Lispsy:** `(while cond ...)`

---

## 3. 函數 (Functions)

### 定義函數
語法結構：`(func [名稱] [回傳型別] ([參數清單]) [主體])`（`func` → `c.lisp:601`）
*   **C:**
    ```c
    float square(float n) {
        return n * n;
    }
    ```
*   **Lispsy:**
    ```lisp
    (func square float ((n float))
        (return (* n n)))
    ```

### 主程式 (Main)
*   **C:** `int main(int argc, char** argv) { ... }`
*   **Lispsy:** `(main ...)` (會自動處理 `argc` 和 `argv`)（`main` → `c.lisp:504`，`return` → `c.lisp:617`）

---

## 4. 預處理器 (Preprocessor)

### 標頭檔
*   **C:** `#include <stdio.h>`
*   **Lispsy:** `(header stdio)`（`header` → `c.lisp:674`）
*   **一次包含多個:** `(headers stdio stdlib string)`（`headers` → `c.lisp:676`）

### 宏定義 (#define)
*   **C:** `#define PI 3.14`
*   **Lispsy:** `(define !pi 3.14)` (注意 `!` 會轉換成大寫 `PI`)（`define` → `c.lisp:646`，`!` 前綴處理 → `c.lisp:145`）

### 條件編譯
*   **C:** `#ifdef DEBUG ... #endif`
*   **Lispsy:** `(ifdef debug ...)`（`ifdef` → `c.lisp:650`，**注意**：此函式有 bug，expr 未插入輸出，建議改用 `(cpp ifdef ...)`；`cpp` → `c.lisp:678`）
