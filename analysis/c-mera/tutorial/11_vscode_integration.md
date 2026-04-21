# 教學 11：VS Code 整合 C-Mera

VS Code 是目前最流行的開發環境。雖然 C-Mera 官方沒有提供插件，但透過結合高品質的 Common Lisp 擴充功能與 VS Code 的任務系統，我們可以打造出不輸給 Emacs 的開發體驗。

## 推薦插件

1.  **[Alive](https://marketplace.visualstudio.com/items?itemName=rheller.alive)** (Preferred): 目前 VS Code 上最強大的 Common Lisp 擴充功能，支援 REPL、代碼補全、文件查詢。
2.  **C/C++ (Microsoft)**: 用於高亮與調試 C-Mera 產出的 `.c` / `.cpp` 檔案。
3.  **vscode-lisp-indent**: 提供更好的 Lisp 縮排支援。

---

## 一、Alive 插件配置

Alive 需要一個 SBCL 或 CCL 作為後端。

1.  安裝 Alive 後，在 `settings.json` 中配置 Lisp 路徑：
    ```json
    "alive.lsp.executablePath": "sbcl", // 或 "ccl"
    ```
2.  在 `.lisp` 檔案中，按 `Ctrl+Alt+S` 啟動 Alive REPL。
3.  **切換環境**：在 REPL 中輸入：
    ```lisp
    (asdf:load-system :cmu-c++)
    (in-package :cmu-c++)
    (cm-reader)
    ```

---

## 二、建置自動化 (`tasks.json`)

我們希望按下 `Ctrl+Shift+B` 時，VS Code 自動將當前檔案轉為 C++ 並編譯。

在專案根目錄建立 `.vscode/tasks.json`：

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "C-Mera: Build current file",
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
            "problemMatcher": []
        },
        {
            "label": "C-Mera: Build and Run",
            "type": "shell",
            "command": "cm c++ ${file} -o ${fileDirname}/tmp.cpp && g++ ${fileDirname}/tmp.cpp -o ${fileDirname}/tmp.out && ${fileDirname}/tmp.out",
            "group": "test",
            "presentation": {
                "reveal": "always",
                "panel": "new"
            }
        }
    ]
}
```

---

## 三、語法高亮優化

Alive 預設會將 C-Mera 的 `function` 或 `decl` 當成普通符號。我們可以透過 `settings.json` 強化它們：

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

---

## 四、互動式開發工作流 (REPL-Driven)

VS Code + Alive 最強大的功能是 **「Inline Evaluation」**：

1.  **求值單個 Form**：將游標放在 `(function ...)` 末尾，按 `Alt+Enter`。Alive 會直接在代碼旁邊顯示結果（或錯誤）。
2.  **查看展開結果**：
    在代碼中包裹 `(cm-c:simple-print ...)`，然後 `Alt+Enter`。C 代碼會直接印在 VS Code 的 Output 視窗中。
3.  **片段庫 (Snippets)**：建議建立自定義 Snippets 來快速輸入 `cmu-c++` 的 preamble。

---

## 五、調試 (Debugging)

由於 C-Mera 產出的是原生 C++，你可以直接使用 VS Code 的 C++ Debugger：

1.  使用上述 `tasks.json` 產生帶有 `-g` 參數的二進位檔。
2.  在產出的 `.cpp` 檔案中設置斷點。
3.  按 `F5` 啟動 `cppdbg`。
    *注意：你是在調試生成的 C++ 代碼，而不是 Lisp 原始碼。*

## 總結

VS Code 提供了最現代化的介面與豐富的插件生態。雖然它不像 Emacs 那樣與 Lisp 深度集成，但透過 `tasks.json` 的靈活性，它能為 C-Mera 開發提供極佳的生產力。
