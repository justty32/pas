# 批量轉換 .cl 檔案 (06)

LISP/c 本身沒有內建「批量轉換多個檔案」的指令，但由於引擎就是一個普通的 Common Lisp 程式，你有幾種方法可以做到批量轉換。

---

## 方法一：在 CLISP REPL 內用迴圈

最直接的方式：在 CLISP 裡用 `mapcar` 或 `loop` 對一個檔案列表逐一呼叫 `c-cl-file`。

```lisp
(load "c.lisp")

;; 把下面換成你的實際檔案列表
(mapcar #'(lambda (name)
            (c-cl-file (format nil "~a.cl" name)
                       (format nil "~a.c"  name)))
        '(foo bar baz))
```

這會依序把 `foo.cl` → `foo.c`、`bar.cl` → `bar.c`、`baz.cl` → `baz.c`。

---

## 方法二：寫一個批量腳本 `batch.lisp`，從 shell 呼叫

建立一個 `batch.lisp`：

```lisp
;; batch.lisp
(load "c.lisp")

;; 從命令列引數取得要轉換的檔案
;; clisp 把額外引數放在 ext:*args*
(dolist (stem ext:*args*)
  (let ((cl-file (format nil "~a.cl" stem))
        (c-file  (format nil "~a.c"  stem)))
    (format t "Converting ~a -> ~a~%" cl-file c-file)
    (c-cl-file cl-file c-file)))
```

然後在 shell 執行：

```bash
clisp batch.lisp foo bar baz
```

這會批量轉換 `foo.cl`、`bar.cl`、`baz.cl`。

---

## 方法三：用 shell glob 搭配一行指令

如果你想轉換某個目錄下所有 `.cl` 檔案，可以在 shell 用 `for` 迴圈：

```bash
# 轉換當前目錄所有 .cl 檔
for f in *.cl; do
    stem="${f%.cl}"
    clisp -x "(load \"c.lisp\") (c-cl-file \"${stem}.cl\" \"${stem}.c\")"
done
```

> **注意**：每次呼叫 `clisp -x` 都是一個全新的 session，引擎會重新載入。如果有跨檔案共用的 `template` 或 `lispmacro`，這個方法**無法**共用全域狀態。請改用方法一或方法二。

---

## 方法四：`c-cl-file-continuous`（監控單一檔案、自動重新翻譯）

引擎內建了一個「持續監控」模式，每隔幾秒自動重新翻譯同一個檔案，適合開發時使用：

```lisp
(load "c.lisp")

;; 每 2 秒重新翻譯 foo.cl → foo.c，遇到錯誤時忽略繼續
(c-cl-file-continuous "foo.cl" "foo.c" t 2)
;; 按 Ctrl+C 停止
```

函式簽章：`(c-cl-file-continuous filein &optional fileout ignore-errors interval)`

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `filein` | — | 輸入 `.cl` 檔 |
| `fileout` | 同名 `.c` | 輸出 `.c` 檔 |
| `ignore-errors` | `nil` | `t` = 翻譯失敗時繼續，`nil` = 出錯停止 |
| `interval` | `1` | 重新翻譯的間隔秒數 |

---

## 方法五：寫一個完整的 `Makefile`

如果你的專案有多個 `.cl` 檔案，可以用 Makefile 管理相依性：

```makefile
# Makefile
SRCS := $(wildcard src/*.cl)
OBJS := $(SRCS:src/%.cl=build/%.c)

all: $(OBJS)

build/%.c: src/%.cl c.lisp
	@mkdir -p build
	clisp -x "(load \"c.lisp\") (c-cl-file \"$<\" \"$@\")"

clean:
	rm -f build/*.c
```

使用方式：

```bash
make        # 只重新翻譯有變動的 .cl 檔
make clean  # 清除所有 .c 輸出
```

---

## 注意：跨檔案共用 `template` 或 `lispmacro`

如果你的多個 `.cl` 檔案共用同一組 `template`/`lispmacro`，最好的做法是：

1. 把共用的 macro/template 定義放在一個單獨的 `.cl` 檔（例如 `common.cl`）。
2. 在需要它們的 `.cl` 檔頭部用 `(import common)` 載入。

```lisp
;; common.cl
(template make-add (typ)
  (func (sym/add add- typ) typ ((a typ) (b typ))
    (return (+ a b))))
```

```lisp
;; main.cl
(import common)   ;; 等同於把 common.cl 的內容嵌入此處
(make-add int)
(make-add float)
(main (return 0))
```

`import` 會直接在當前 session 裡執行 `common.cl` 的所有 S-expression，然後在輸出 C 碼中插入一行 `/* common.cl LOADED */` 作為標記。
