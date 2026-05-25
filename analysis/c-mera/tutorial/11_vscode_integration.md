# 教學 11：VS Code 整合 C-Mera

VS Code 沒有 Emacs 那種深度 Lisp 整合，但透過 **Alive 擴充功能**和 `tasks.json`，可以打造出接近 REPL-Driven 的工作流。

---

## 一、必要插件

| 插件 | 用途 |
|---|---|
| **[Alive](https://marketplace.visualstudio.com/items?itemName=rheller.alive)** | Common Lisp REPL、補全、文件、Inline Eval |
| **C/C++ (Microsoft)** | 對產出的 `.c`/`.cpp` 做 IntelliSense、調試 |
| **[Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)** | 可選，若用 TOML 設定檔 |

---

## 二、Alive 設定

安裝後，在 `.vscode/settings.json` 或全域 `settings.json` 設定：

```json
{
    "alive.lsp.startLisp": true,
    "alive.lsp.executablePath": "ccl",
    "alive.lsp.startupScripts": [
        "(ql:quickload :cmu-c++)",
        "(in-package :cmu-c++)",
        "(cm-reader)"
    ]
}
```

`startupScripts` 讓每次啟動 Alive REPL 時自動載入 C-Mera 並切換 reader——**省去每次手動輸入三行的麻煩**。

啟動 REPL：`Ctrl+Alt+S`（或開啟命令面板 `Alive: Start REPL`）。

---

## 三、Inline Evaluation 工作流

Alive 最強的功能是 **Inline Eval**：

1. 在 `.lisp` 檔案裡寫好一個 form
2. 游標放在 form 末尾，按 `Alt+Enter`
3. 結果（或錯誤訊息）直接顯示在程式碼旁邊，不需要切視窗

**即時預覽 C 輸出**：

```lisp
;; 在 .lisp 檔案裡這樣寫，然後 Alt+Enter

(cm-cxx:simple-print
  (function fib ((int n)) -> int
    (if (<= n 1) (return n))
    (return (+ (fib (- n 1))
               (fib (- n 2))))))
```

Alive 會在 `simple-print` form 旁邊顯示輸出的 C++ 程式碼。

**展開 macro**：游標在 `(defmax int)` 上，開命令面板選 `Alive: Macroexpand 1`。

---

## 四、建置自動化（tasks.json）

在專案根目錄建立 `.vscode/tasks.json`：

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "C-Mera: Build (C++)",
            "type": "shell",
            "command": "cm",
            "args": [
                "c++",
                "${file}",
                "-o",
                "${fileDirname}/${fileBasenameNoExtension}.cpp"
            ],
            "group": {
                "kind": "build",
                "isDefault": true
            },
            "presentation": {
                "reveal": "always",
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "C-Mera: Build (C)",
            "type": "shell",
            "command": "cm",
            "args": [
                "c",
                "${file}",
                "-o",
                "${fileDirname}/${fileBasenameNoExtension}.c"
            ],
            "group": "build",
            "problemMatcher": []
        },
        {
            "label": "C-Mera: Build and Run (C++)",
            "type": "shell",
            "command": "bash",
            "args": [
                "-c",
                "cm c++ '${file}' -o /tmp/cmera_out.cpp && g++ -std=c++17 /tmp/cmera_out.cpp -o /tmp/cmera_bin && /tmp/cmera_bin"
            ],
            "group": "test",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            },
            "problemMatcher": []
        },
        {
            "label": "C-Mera: Build and Run (C)",
            "type": "shell",
            "command": "bash",
            "args": [
                "-c",
                "cm c '${file}' -o /tmp/cmera_out.c && gcc -std=c99 /tmp/cmera_out.c -o /tmp/cmera_bin && /tmp/cmera_bin"
            ],
            "group": "test",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            },
            "problemMatcher": []
        }
    ]
}
```

用法：
- `Ctrl+Shift+B`：執行預設建置任務（Build C++）
- `Ctrl+Shift+P` → `Tasks: Run Task`：選擇其他任務

---

## 五、自訂 Snippet

建立 `.vscode/lisp.code-snippets`，快速輸入常用模板：

```json
{
    "C-Mera Function": {
        "prefix": "cmfn",
        "body": [
            "(function ${1:name} (${2:(int ${3:x})}) -> ${4:int}",
            "  ${0:body})"
        ],
        "description": "C-Mera function definition"
    },
    "C-Mera Include": {
        "prefix": "cminc",
        "body": ["(include <${1:stdio.h}>)"],
        "description": "C-Mera include"
    },
    "C-Mera Main": {
        "prefix": "cmmain",
        "body": [
            "(include <stdio.h>)",
            "",
            "(function main () -> int",
            "  ${0}",
            "  (return 0))"
        ],
        "description": "C-Mera main template"
    },
    "C-Mera For Loop": {
        "prefix": "cmfor",
        "body": [
            "(for ((int ${1:i} = 0) (< ${1:i} ${2:n}) ++${1:i})",
            "  ${0})"
        ],
        "description": "C-Mera for loop"
    },
    "C-Mera Defmacro": {
        "prefix": "cmdm",
        "body": [
            "(defmacro ${1:name} (${2:args})",
            "  \\`(${0}))"
        ],
        "description": "C-Mera defmacro"
    },
    "C-Mera Class": {
        "prefix": "cmcls",
        "body": [
            "(class ${1:Name} ()",
            "  (private",
            "   (decl ((${2:int} ${3:x}))))",
            "  (public",
            "   (constructor () :init ((${3:x} 0)))",
            "   ${0}))"
        ],
        "description": "C-Mera class template"
    }
}
```

---

## 六、語法高亮強化

Alive 預設把 C-Mera 的關鍵字當普通符號。加進 `settings.json` 來加強高亮：

```json
"editor.tokenColorCustomizations": {
    "textMateRules": [
        {
            "scope": [
                "keyword.declaration.lisp",
                "keyword.control.lisp",
                "storage.type.lisp"
            ],
            "settings": {
                "foreground": "#569CD6",
                "fontStyle": "bold"
            }
        }
    ]
}
```

更進一步，可以在 `~/.config/nvim/queries/commonlisp/` 放自訂的 Treesitter query（若用 Neovim），或用 Alive 的語意高亮功能（需要 REPL 連線後才啟動）。

---

## 七、調試（Debug）

C-Mera 產出的是標準 C/C++，可以直接用 VS Code 的 C++ Debugger：

1. 建置時加入 `-g` 旗號：

```json
{
    "label": "C-Mera: Build Debug",
    "type": "shell",
    "command": "bash",
    "args": [
        "-c",
        "cm c++ '${file}' -o /tmp/dbg.cpp && g++ -std=c++17 -g -O0 /tmp/dbg.cpp -o /tmp/dbg_bin"
    ]
}
```

2. 建立 `.vscode/launch.json`：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug C-Mera output",
            "type": "cppdbg",
            "request": "launch",
            "program": "/tmp/dbg_bin",
            "stopAtEntry": false,
            "cwd": "${workspaceFolder}",
            "MIMode": "gdb",
            "miDebuggerPath": "/usr/bin/gdb"
        }
    ]
}
```

3. 在產出的 `/tmp/dbg.cpp` 裡設斷點，按 `F5` 調試。

**注意**：你是在調試產出的 C++ 程式碼，不是 Lisp 原始碼。斷點要設在 `.cpp` 檔，不是 `.lisp` 檔。

---

## 八、常見問題

**Q：Alive REPL 啟動後顯示「C-Mera not found」**

確認 `startupScripts` 裡的 `ql:quickload` 成功。在 REPL 裡手動執行：

```lisp
(ql:system-apropos "cmu")
; 應該看到 cmu-c、cmu-c++ 等
```

**Q：`tasks.json` 的 `cm` 找不到**

確認 `cm` 在 PATH 裡：在 VS Code 的 terminal 試試 `which cm`。若 C-Mera 是本地建置沒有 install，改成完整路徑：

```json
"command": "/path/to/c-mera/cm"
```

**Q：Windows 上 bash 指令跑不動**

把 `"command": "bash"` 改成用 PowerShell 或 Git Bash：

```json
"command": "cmd",
"args": ["/c", "cm c++ ${file} -o ${fileDirname}\\${fileBasenameNoExtension}.cpp"]
```

或在 WSL2 裡開發（推薦）。

---

## 九、VS Code vs Emacs 選擇建議

| 面向 | VS Code | Emacs |
|---|---|---|
| 初始設定難度 | 低 | 中 |
| REPL 整合深度 | 中（Alive） | 高（SLIME/SLY） |
| Macro 展開工作流 | 可以，但不如 Emacs 流暢 | 最佳（C-c C-m 展開） |
| 現代 UI / 插件生態 | 強 | 弱 |
| Windows 支援 | 好 | 需要 WSL |

**建議**：如果你已經用 VS Code 寫 C++，從 VS Code + Alive 開始最順。如果你願意學 Emacs，長遠來看 REPL-Driven 開發體驗更好。
