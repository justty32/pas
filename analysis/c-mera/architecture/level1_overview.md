# Level 1：初始探索與基礎架構

## 專案定位
C-Mera 是以 Common Lisp 撰寫的**來源到來源（source-to-source）編譯器**，把 S-運算式形式的程式碼轉成 C 家族語言（C、C++、CUDA、GLSL、OpenCL）的原生文字。它刻意不引入任何抽象層，使用者寫的 sexp 與目標語言的語意一對一對應；Lisp 的角色是提供一個超強的巨集系統，讓 C 程式碼能被元編程（metaprogramming）。

## 技術棧
- 語言：Common Lisp（支援 SBCL、CCL、ECL；作者推薦 CCL 以獲得較短編譯時間）。
- 依賴：`net.didierverna.clon.core`（命令列解析與 image dump），見 `c-mera.asd:468`。
- 建構系統：GNU Autotools（`configure.ac`、`Makefile.am`）。
- 前端分派器：一個極小的 C 程式 `src/front/cm.c`，呼叫對應的 `cm-c` / `cm-cxx` 等後端可執行檔。
- 測試：純 Makefile 驅動，產物為 C/C++ 檔案編譯後執行，比對 `;;## ` 標註的預期輸出（見 `tests/Makefile:116`）。

## 目錄結構（最高層）
- `src/c-mera/`：AST/traverser/pretty-printer 的核心框架。
- `src/c/`、`src/cxx/`、`src/cuda/`、`src/opencl/`、`src/glsl/`：各語言後端。
- `src/front/cm.c`：命令列分派器。
- `tests/`：回歸測試。
- `util/emacs/`、`util/vim/`：編輯器整合。
- `roswell/`：Roswell 腳本入口。
- `c-mera.asd`：ASDF 系統定義，集中管理所有套件與符號匯出。

## 建構與執行
```
autoreconf -if
./configure --with-ccl        # 或 --with-sbcl
make && make install
cm c input.lisp -o out.c
cm c++ input.lisp -o out.cpp
```

## 快速心智模型
輸入 `.lisp` 檔 → 透過 `cmu-c`（或 `cmu-c++`…）套件內建的巨集展開為 AST 節點 → 數個 traverser 重寫 AST → pretty-printer 把 AST 轉成目標語言文字。整個流水線的入口定義在 `src/c/cm-c.lisp:14` 的 `define-processor`。
