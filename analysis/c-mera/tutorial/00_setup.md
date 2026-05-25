# 教學 00：安裝與 Hello World

## 這份教學的假設

你會寫 C / C++，但不太碰 Lisp。我們把 C-Mera 當成「另一種寫 C 的語法」：你寫 `.lisp` 檔，它吐出 `.c` 或 `.cpp`，然後用 gcc/g++ 編譯執行。Lisp 只是皮，產物就是平常的 C。

---

## 一、安裝 Common Lisp 環境

C-Mera 需要 Common Lisp 實作（推薦 **CCL**，SBCL 也支援但建置稍慢）、Quicklisp、autotools。

### Linux（Arch / Manjaro）

```bash
sudo pacman -S ccl autoconf automake make gcc
```

### Linux（Ubuntu / Debian）

```bash
sudo apt install build-essential autoconf automake
# CCL 的 deb 包不夠新，建議直接下載 binary：
# https://github.com/Clozure/ccl/releases
# 解壓後把 lx86cl64（或 armcl）加進 PATH

# 或者用 SBCL（Ubuntu 官方有包）：
sudo apt install sbcl
```

### macOS

```bash
brew install ccl autoconf automake gcc
```

### Windows（WSL2 推薦）

```bash
# 在 WSL2 的 Ubuntu 環境裡做，和 Ubuntu 步驟相同
wsl --install -d Ubuntu
```

---

## 二、安裝 Quicklisp

Quicklisp 是 Common Lisp 的套件管理器，裝一次就好：

```bash
curl -O https://beta.quicklisp.org/quicklisp.lisp
ccl --load quicklisp.lisp
```

進入 CCL 的 Lisp prompt 後輸入：

```lisp
(quicklisp-quickstart:install)
(ql:add-to-init-file)          ; 讓每次啟動都自動載入 Quicklisp
(ql:quickload :net.didierverna.clon.core)   ; C-Mera 的命令列依賴
(quit)
```

用 SBCL 的話，把 `ccl` 換成 `sbcl`，步驟相同。

**確認 Quicklisp 安裝成功**：

```bash
ccl --eval '(ql:system-apropos "clon")' --eval '(quit)'
# 應該看到 net.didierverna.clon 相關輸出
```

---

## 三、建置 C-Mera

```bash
git clone https://github.com/kiselgra/c-mera.git
cd c-mera
autoreconf -if
./configure --with-ccl          # 使用 CCL（推薦）
# ./configure --with-sbcl       # 使用 SBCL
make
```

`make` 會產生：
- `cm-c`：C 後端
- `cm-cxx`：C++ 後端
- `cm-cuda`：CUDA 後端
- `cm-glsl`：GLSL 後端
- `cm-opencl`：OpenCL 後端
- `cm`：前端分派器（根據第一個參數決定呼叫哪個後端）

```bash
sudo make install    # 安裝到 /usr/local/bin（可選）
# 或者直接在 c-mera 目錄裡用 ./cm
```

**確認安裝成功**：

```bash
echo '(function main () -> int (return 0))' | cm c
# 應該輸出：
# int main(void)
# {
#     return 0;
# }
```

---

## 四、Hello World（C）

建一個檔案 `hello.lisp`：

```lisp
(include <stdio.h>)

(function main () -> int
  (printf "Hello, C-Mera!\n")
  (return 0))
```

翻譯成 C：

```bash
cm c hello.lisp -o hello.c
cat hello.c
```

你會看到：

```c
#include <stdio.h>

int main(void)
{
    printf("Hello, C-Mera!\n");
    return 0;
}
```

編譯執行：

```bash
gcc -std=c99 hello.c -o hello && ./hello
# Hello, C-Mera!
```

也可以直接輸出到 stdout 而不寫檔：

```bash
cm c hello.lisp          # 輸出到 stdout
cm c hello.lisp | gcc -x c -o hello -   # 通過 pipe 直接編譯
```

---

## 五、Hello World（C++）

`hello_cxx.lisp`：

```lisp
(include <iostream>)

(function main () -> int
  (<< #:std::cout "Hello, C-Mera C++!" #:std::endl)
  (return 0))
```

```bash
cm c++ hello_cxx.lisp -o hello_cxx.cpp
g++ -std=c++11 hello_cxx.cpp -o hello_cxx && ./hello_cxx
# Hello, C-Mera C++!
```

說明：
- `#:std::cout` 的 `#:` 前綴讓 Lisp reader 把 `std::cout` 原樣輸出，不做大小寫轉換。
- `<<` 在 C-Mera 的 C++ 後端被識別為中綴串接運算子，展開為 `std::cout << ... << std::endl`。

---

## 六、跑測試套件

C-Mera 自帶大量測試，每個測試檔案本身就是很好的語法範例：

```bash
cd tests
make              # 執行全部測試
make c.for.00.ok  # 只跑特定測試（去掉 .lisp 後綴，加 .ok）
```

每個 `.lisp` 測試檔案末尾的 `;;## ...` 是期望輸出。想學某個功能，直接翻 `tests/` 找最接近的測試：

```bash
# 找所有跟 struct 有關的測試
ls tests/c.misc.09.*
ls tests/cxx.class.*.lisp
```

---

## 七、常見安裝問題排查

**問題：`autoreconf: command not found`**

```bash
# Debian/Ubuntu
sudo apt install autoconf automake libtool
# macOS
brew install autoconf automake
```

**問題：`./configure` 找不到 CCL**

```bash
# 確認 ccl binary 的名字（可能是 ccl、lx86cl64、armcl 等）
which ccl || which lx86cl64
# 如果不在 PATH 裡，用 --with-ccl= 明確指定路徑
./configure --with-ccl=/usr/local/bin/lx86cl64
```

**問題：make 失敗，報 `clon` 找不到**

```bash
# 確認 Quicklisp 有安裝 clon
ccl --eval '(ql:quickload :net.didierverna.clon.core)' --eval '(quit)'
# 如果失敗，確認 ~/.quicklisp 目錄存在且 init.lisp 有載入
```

**問題：Windows 上跑不動（非 WSL）**

C-Mera 的建置系統需要 GNU make 和 autotools，**建議在 WSL2 裡操作**。或者使用 Roswell 腳本（`roswell/cm.ros`）——Roswell 有 Windows 版，但路徑比較複雜。

**問題：`cm c hello.lisp` 輸出是空的**

確認 hello.lisp 的 `printf` 裡的 `\n` 要寫成 `\\n`（雙反斜線），因為 Lisp 字串裡 `\` 是跳脫字元：

```lisp
(printf "Hello\\n")    ; 正確：輸出 Hello\n 到 C
(printf "Hello\n")     ; 在 Lisp 層就被解釋為換行字元，C 看到的是 "Hello" + 換行
```

---

## 八、目錄結構概覽

```
c-mera/
├── src/
│   ├── c-mera/    # 核心框架（AST、traverser、pretty-printer）
│   ├── c/         # C 後端
│   ├── cxx/       # C++ 後端
│   ├── cuda/      # CUDA 後端
│   ├── glsl/      # GLSL 後端
│   ├── opencl/    # OpenCL 後端
│   └── front/cm.c # 命令列分派器
├── tests/         # 測試套件（最好的範例庫）
├── util/
│   ├── emacs/     # cm-mode.el
│   └── vim/       # cm.vim
└── c-mera.asd     # ASDF 系統定義
```

---

## 九、下一步

- 教學 01：C 語法速查（sexp ↔ C 完整對照）
- 教學 02：三支完整的小 C 程式
- 教學 03：C++ 基礎（class、namespace、template）
- 教學 04：Lisp 巨集——C-Mera 的真正價值
