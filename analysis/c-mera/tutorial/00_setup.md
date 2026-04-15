# 教學 00：安裝與 Hello World

## 這份教學的假設
你會寫 C / C++，但不太碰 Lisp。我們把 C-Mera 當成「另一種寫 C 的語法」：你寫 `.lisp` 檔，它吐出 `.c` 或 `.cpp`，然後用 gcc/g++ 編譯執行。Lisp 只是皮，產物就是平常的 C。

## 一、安裝

C-Mera 需要一個 Common Lisp 實作（推薦 **CCL**，SBCL 比較慢）、Quicklisp、autotools。在 Arch/Manjaro 上：

```bash
sudo pacman -S ccl autoconf automake make gcc
# 或 sbcl 亦可
```

安裝 Quicklisp（只要一次）：
```bash
curl -O https://beta.quicklisp.org/quicklisp.lisp
ccl --load quicklisp.lisp
# 在 Lisp prompt 裡：
# (quicklisp-quickstart:install)
# (ql:add-to-init-file)
# (ql:quickload :net.didierverna.clon.core)
# (quit)
```

然後建置 C-Mera：
```bash
cd ~/repo/c-mera
autoreconf -if
./configure --with-ccl          # 如果用 SBCL 改成 --with-sbcl
make
sudo make install               # 裝到 /usr/local/bin (可選)
```

`make` 會產生 `cm-c`、`cm-cxx`、`cm-cuda`、`cm-glsl`、`cm-opencl` 幾支可執行檔，以及一個分派器 `cm`。

## 二、Hello World（C）

建一個檔案 `hello.lisp`：
```lisp
(include <stdio.h>)

(function main () -> int
  (printf "Hello, C-Mera!\\n")
  (return 0))
```

翻譯成 C：
```bash
./cm c hello.lisp -o hello.c
# 也可以直接輸出到 stdout：./cm c hello.lisp
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
```

## 三、Hello World（C++）

`hello.lisp`：
```lisp
(include <iostream>)

(function main () -> int
  (<< #:std::cout "Hello, C-Mera C++!" #:std::endl)
  (return 0))
```

```bash
./cm c++ hello.lisp -o hello.cpp
g++ -std=c++11 hello.cpp -o hello && ./hello
```

說明：
- `#:std::cout` 是「雙冒號的原樣命名空間字串」。`#:` 前綴是保留大小寫、不被 reader 改寫的符號。
- `<<` 在這裡被當成中綴運算子，展開為 `std::cout << "..." << std::endl;`。

## 四、怎麼跑測試
專案附帶的測試很適合當範例字典：
```bash
cd tests
make              # 全跑
make c.for.00.ok  # 單一測試（檔名拿掉 .lisp、改 .ok）
```
每個 `.lisp` 檔最後的 `;;## ...` 是期望輸出。要學某個功能怎麼寫，直接翻 `tests/` 找對應檔最快。

## 五、下一步
- 教學 01：基本語法速查（C 對照）。
- 教學 02：struct、指標、陣列、函式指標。
- 教學 03：C++（class、template、namespace、lambda）。
- 教學 04：用 Lisp 做元編程（這才是 C-Mera 真正好玩的地方）。
