# 教學 09：Neovim / LazyVim 整合 C-Mera

C-Mera 官方只附 Emacs（`cm-mode.el`）和 Vim 8（`lisp_cmera.vim`，依賴 Vlime）的整合。Neovim/LazyVim 沒現成的，但組合既有生態就很夠用。這篇提供一套可落地的設定。

## 目標
1. 開 `.lisp` 檔自動有 **Lisp 語法高亮**（treesitter）與結構編輯。
2. `:CmeraBuild` 或按鍵把當前 buffer 轉成 C/C++ 並預覽輸出。
3. REPL 互動（可選）：送 form 到 CCL/SBCL REPL 即時測試巨集展開。
4. 識別 `cm.indent` 裡的關鍵字作為高亮與縮排。

## 一、前置套件

LazyVim 已內建 treesitter、none-ls、toggleterm 等。需要多裝的：

| 套件 | 功能 |
|---|---|
| `nvim-treesitter` 的 `commonlisp` parser | 語法高亮 |
| `Olical/conjure` | Lisp REPL 互動（類似 SLIME） |
| `guns/vim-sexp` + `tpope/vim-sexp-mappings-for-regular-people` | 結構編輯（cut/wrap/raise s-expression） |
| `akinsho/toggleterm.nvim`（LazyVim 通常已有） | 執行建置指令 |
| CCL 或 SBCL | Common Lisp 實作 |

## 二、LazyVim plugin spec

在 `~/.config/nvim/lua/plugins/cmera.lua` 新增：

```lua
return {
  -- 1. treesitter commonlisp parser
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      vim.list_extend(opts.ensure_installed or {}, { "commonlisp" })
    end,
  },

  -- 2. Conjure (Lisp REPL)
  {
    "Olical/conjure",
    ft = { "lisp" },
    init = function()
      vim.g["conjure#filetype#lisp"] = "conjure.client.common-lisp.swank"
      vim.g["conjure#client#common_lisp#swank#connection#default_host"] = "127.0.0.1"
      vim.g["conjure#client#common_lisp#swank#connection#default_port"] = 4005
    end,
  },

  -- 3. Structural editing
  { "guns/vim-sexp", ft = { "lisp", "scheme", "clojure" } },
  {
    "tpope/vim-sexp-mappings-for-regular-people",
    ft = { "lisp", "scheme", "clojure" },
    dependencies = { "guns/vim-sexp" },
  },

  -- 4. C-Mera 專屬 ftplugin / 建置指令（見第三節）
  {
    "nvim-lua/plenary.nvim",  -- 只是讓我們能分一個 lua 模組
    config = function()
      require("cmera")        -- 見下方自建模組
    end,
  },
}
```

## 三、自建 C-Mera lua 模組

建立 `~/.config/nvim/lua/cmera.lua`：

```lua
local M = {}

-- 把路徑指向你的 cm 可執行檔
local CM_BIN = vim.fn.expand("~/repo/c-mera/cm")   -- 未 make install 時
-- 或 CM_BIN = "cm" (裝到 /usr/local/bin 後)

-- 依 buffer 最上面的註解或檔名決定語言：.lisp 預設 C；含 "cxx" 或開頭 `; -*- cm: c++ -*-` 則 C++
local function detect_lang(buf)
  local first = vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or ""
  if first:match("cm:%s*c%+%+") or first:match("cm:%s*cxx") then return "c++" end
  local name = vim.api.nvim_buf_get_name(buf)
  if name:match("cxx") or name:match("%.cpp%.lisp$") then return "c++" end
  return "c"
end

-- :CmeraBuild  -> 編譯當前 buffer，在右邊 split 顯示輸出
function M.build()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  if file == "" then
    vim.notify("save the buffer first", vim.log.levels.WARN); return
  end
  vim.cmd("silent! write")
  local lang = detect_lang(buf)
  local out = vim.fn.system({ CM_BIN, lang, file })
  if vim.v.shell_error ~= 0 then
    vim.notify("cm failed:\n" .. out, vim.log.levels.ERROR); return
  end
  -- 開一個右側 scratch buffer 顯示結果
  vim.cmd("vnew")
  local out_buf = vim.api.nvim_get_current_buf()
  vim.api.nvim_buf_set_lines(out_buf, 0, -1, false, vim.split(out, "\n"))
  vim.bo[out_buf].buftype = "nofile"
  vim.bo[out_buf].filetype = (lang == "c++") and "cpp" or "c"
  vim.bo[out_buf].modifiable = false
end

-- :CmeraRun -> 編譯 + 用 gcc/g++ 編 + 執行
function M.run()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  local lang = detect_lang(buf)
  local ext = (lang == "c++") and ".cpp" or ".c"
  local compiler = (lang == "c++") and "g++" or "gcc"
  local std = (lang == "c++") and "-std=c++17" or "-std=c99"
  local tmpc = vim.fn.tempname() .. ext
  local tmpe = vim.fn.tempname()
  vim.cmd("silent! write")
  local o = vim.fn.system({ CM_BIN, lang, file, "-o", tmpc })
  if vim.v.shell_error ~= 0 then
    vim.notify("cm failed:\n" .. o, vim.log.levels.ERROR); return
  end
  local c = vim.fn.system({ compiler, std, tmpc, "-o", tmpe })
  if vim.v.shell_error ~= 0 then
    vim.notify(compiler .. " failed:\n" .. c, vim.log.levels.ERROR); return
  end
  -- 以 toggleterm 執行
  require("toggleterm").exec(tmpe)
end

function M.setup()
  vim.api.nvim_create_user_command("CmeraBuild", M.build, {})
  vim.api.nvim_create_user_command("CmeraRun",   M.run,   {})

  -- 對 .lisp 檔自動掛 filetype = lisp 並加 buffer-local 鍵
  vim.api.nvim_create_autocmd("FileType", {
    pattern = "lisp",
    callback = function(ev)
      vim.keymap.set("n", "<leader>cb", M.build, { buffer = ev.buf, desc = "C-Mera build" })
      vim.keymap.set("n", "<leader>cr", M.run,   { buffer = ev.buf, desc = "C-Mera run" })
      vim.bo[ev.buf].commentstring = ";; %s"
    end,
  })
end

M.setup()
return M
```

現在重啟 nvim，打開任一 `.lisp` 檔，按 `<leader>cb` 就能預覽生成的 C／C++；`<leader>cr` 會直接跑起來。

## 四、讓 C-Mera 關鍵字有高亮

treesitter 的 `commonlisp` parser 預設只認 CL 關鍵字。要讓 `function`、`decl`、`struct`、`class`、`template`、`for`、`constructor` 這類 C-Mera 形式有額外樣式，加一個 query 覆蓋。

建立 `~/.config/nvim/queries/commonlisp/highlights.scm`（注意是附加，不是取代）：

```scheme
;; extends

((sym_lit) @keyword.function
 (#any-of? @keyword.function
   "function" "decl" "for" "while" "if" "when" "cond"
   "switch" "return" "break" "continue"
   "struct" "union" "enum" "typedef" "include" "cpp" "pragma"
   "class" "namespace" "template" "instantiate" "constructor" "destructor"
   "public" "private" "protected" "using" "using-namespace" "from-namespace"
   "new" "delete" "throw" "catching"
   "lambda-function" "for-each"))

((sym_lit) @type.builtin
 (#any-of? @type.builtin
   "int" "char" "void" "float" "double" "long" "short"
   "unsigned" "signed" "bool" "size_t" "auto" "const" "static"
   "virtual" "inline" "constexpr" "noexcept" "override" "final" "pure"
   "this" "nullptr" "true" "false"))

((sym_lit) @function.builtin
 (#any-of? @function.builtin
   "printf" "scanf" "malloc" "free" "memcpy" "strlen" "strcmp"
   "cout" "cin" "endl" "make_shared" "make_unique" "move" "forward"))
```

同目錄再放 `indents.scm`（commonlisp 預設就可用），縮排靠 treesitter 內建即可。

## 五、若你要 cm.indent 的相容體驗

`cm.indent` 是 vim 老版本用的 indent 數字表。Neovim 的 treesitter-indent 不需要它，但若你想在某個專案用既有的 `cm.indent` 附加關鍵字，在上面 `cmera.lua` 的 `setup()` 末尾加：

```lua
vim.api.nvim_create_autocmd({ "BufReadPost", "BufNewFile" }, {
  pattern = "*.lisp",
  callback = function()
    local dir = vim.fn.expand("%:p:h")
    while dir ~= "/" do
      local f = dir .. "/cm.indent"
      if vim.fn.filereadable(f) == 1 then
        local content = table.concat(vim.fn.readfile(f), "\n")
        local kws = content:match(":keywords%s*%(([^)]+)%)")
        if kws then
          for kw in kws:gmatch("%S+") do
            vim.cmd(("syntax keyword lispFunc %s"):format(kw))
          end
        end
        break
      end
      dir = vim.fn.fnamemodify(dir, ":h")
    end
  end,
})
```

不過我認為 treesitter 的 highlights.scm 比較好維護，這段純粹是給你 fallback 用。

## 六、REPL 工作流（選用但超香）

1. 先在終端機啟動 swank server：
   ```bash
   ccl --eval '(ql:quickload :swank)' --eval '(swank:create-server :port 4005 :dont-close t)'
   ```
   或做成腳本：`~/bin/cm-swank.sh`。
2. 在 nvim 裡打開 `.lisp`，`:ConjureConnect`（Conjure 會自動連 4005）。
3. 在檔案頂端放上 C-Mera 需要的 preamble：
   ```lisp
   (asdf:load-system :cmu-c++)
   (in-package :cmu-c++)
   (cm-reader)
   ```
   每行按 `<localleader>ee` 送到 REPL 求值。
4. 寫一段函式或巨集後，按 `<localleader>ef` 送整個 form。用 `(simple-print ...)` 立即看 C/C++ 產出，不必寫檔。

建議：檔案頂端一律這樣起頭，方便 REPL 裡 `<localleader>ef` 一次載完整個檔。

## 七、建議按鍵總表

| 鍵 | 行為 |
|---|---|
| `<leader>cb` | `:CmeraBuild` — 產生 C/C++ 文字到 split |
| `<leader>cr` | `:CmeraRun` — 產生 + 編譯 + 執行 |
| `<localleader>ee` | Conjure eval 當前 expression |
| `<localleader>ef` | Conjure eval 整個 form |
| `<localleader>er` | Conjure eval root form |
| `>)` / `<)` | vim-sexp 把游標的 form 往右／左移 |
| `>e` / `<e` | slurp / barf（從旁邊吞進或吐出一個 sexp） |
| `dsf` | raise form（把當前 sexp 取代外層） |

## 八、.editorconfig / formatter

Lisp 沒有普及的 formatter 工具；用 `vim-sexp` 就手工對齊。若你用 [lisp-format](https://github.com/eschulte/lisp-format)（實驗性），可在 none-ls 加：

```lua
{
  "nvimtools/none-ls.nvim",
  opts = function(_, opts)
    local nls = require("null-ls")
    table.insert(opts.sources, nls.builtins.formatting.lisp_format or nls.builtins.formatting.prettier)
  end,
}
```
但 C-Mera 的 DSL 特殊形式太多，我不推薦用 formatter；靠結構編輯比較安全。

## 九、檔案模板（snippet）

在 `~/.config/nvim/lua/plugins/snippets.lua` 或 LazyExtras 的 luasnip 裡加：

```lua
local ls = require("luasnip")
local s, t, i = ls.s, ls.t, ls.i
ls.add_snippets("lisp", {
  s("cmc", {
    t({ "(include <stdio.h>)", "", "(function main () -> int", "  " }),
    i(1, "(printf \"hello\\\\n\")"),
    t({ "", "  (return 0))" }),
  }),
  s("cmcxx", {
    t({ "(include <iostream>)", "(using-namespace std)", "", "(function main () -> int", "  " }),
    i(1, "(<< cout \"hello\" endl)"),
    t({ "", "  (return 0))" }),
  }),
})
```

打 `cmc<Tab>` 就生 C hello world，`cmcxx<Tab>` 生 C++ 版。

## 十、一些實戰 tips

1. **切到 C-Mera reader**：在 REPL 先跑 `(cm-reader)`，之後 `(cl-reader)` 可切回純 Lisp。
2. **預覽 macro 展開**：用 `(macroexpand-1 '(defmax int))`，Conjure 把結果列在 HUD；這是寫 `defmacro` 的關鍵調試點。
3. **tests/ 當字典**：碰到某個語法不會寫，`:Telescope find_files cwd=~/repo/c-mera/tests` 直接找檔名對應。
4. **多檔**：C-Mera 本身沒有 include 機制，靠 Lisp 的 `load`：在 `main.lisp` 開頭 `(load "helpers.lisp")`，或用 `asdf:defsystem`。
5. **commit 之前**：記得把產生的 `.c` / `.cpp` 加到 `.gitignore`——這些都是 build output。

## 小結

LazyVim + Conjure + vim-sexp + 一個小小的 `cmera.lua` = 跟 Emacs SLIME 差不多的體驗。重點是建置指令與結構編輯；語法高亮靠 treesitter 就夠，不必硬搬 `cm-mode.el`。
