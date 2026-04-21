# 教學 09：Neovim / LazyVim 整合 C-Mera (2026 更新版)

C-Mera 官方雖然只附 Emacs 和 Vim 8 的整合，但在 2026 年的 Neovim 生態下，透過 LazyVim 的 Extras 與內建 API，我們可以獲得遠超原生的開發體驗。

## 目標
1. **Lisp 結構編輯與高亮**：基於 Treesitter 與專屬 Query。
2. **非同步建置**：使用 `vim.system` 進行背景編譯，不卡頓 UI。
3. **Snacks 整合**：利用 LazyVim 內建的 `Snacks.terminal` 與 `Snacks.scratch` 顯示輸出。
4. **REPL 互動**：透過 Conjure 連接 Lisp 環境。

## 一、啟用 LazyVim Extras

在 `~/.config/nvim/lua/config/lazy.lua` 或透過 `:LazyExtras` 啟用以下模組：
- `lang.lisp` (自動安裝 Treesitter, Conjure, vim-sexp)
- `ui.treesitter`
- `util.dot` (選用，處理一些傳統設定)

## 二、自訂 C-Mera 核心邏輯

建立 `~/.config/nvim/lua/config/cmera.lua`。這裡我們使用 Neovim 0.10+ 的非同步 API。

```lua
local M = {}

local CM_BIN = "cm" -- 假設已安裝到 PATH

-- 偵測語言模式
local function detect_lang(buf)
  local first = vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or ""
  if first:match("cm:%s*c%+%+") or first:match("cm:%s*cxx") then return "c++" end
  local name = vim.api.nvim_buf_get_name(buf)
  if name:match("cxx") or name:match("%.cpp%.lisp$") then return "c++" end
  return "c"
end

-- 使用 vim.system 非同步執行編譯
function M.build()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  if file == "" then Snacks.notify.warn("請先儲存檔案"); return end
  
  vim.cmd("silent! write")
  local lang = detect_lang(buf)

  Snacks.notify.info("C-Mera 編譯中: " .. lang)

  vim.system({ CM_BIN, lang, file }, { text = true }, function(obj)
    vim.schedule(function()
      if obj.code ~= 0 then
        Snacks.notify.error("編譯失敗:\n" .. obj.stderr)
        return
      end
      
      -- 使用 Snacks.scratch 顯示結果
      Snacks.scratch({
        icon = "󰙲 ",
        name = "C-Mera Output (" .. lang .. ")",
        ft = (lang == "c++" and "cpp" or "c"),
        content = obj.stdout,
      })
    end)
  end)
end

-- 編譯並執行 (透過 Snacks.terminal)
function M.run()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.api.nvim_buf_get_name(buf)
  local lang = detect_lang(buf)
  local ext = (lang == "c++") and ".cpp" or ".c"
  local compiler = (lang == "c++") and "g++" or "gcc"
  local tmpc = vim.fn.tempname() .. ext
  local tmpe = vim.fn.tempname()

  vim.cmd("silent! write")
  
  -- 這裡直接在終端執行複合指令
  local cmd = string.format("%s %s %s -o %s && %s %s -o %s && %s", 
    CM_BIN, lang, file, tmpc, compiler, tmpc, tmpe, tmpe)
    
  Snacks.terminal.toggle(cmd, { title = "C-Mera Run" })
end

return M
```

## 三、按鍵映射 (Keymaps)

在 `~/.config/nvim/lua/config/keymaps.lua` 加入：

```lua
local cmera = require("config.cmera")

-- 僅在 lisp 檔案類型下生效
vim.api.nvim_create_autocmd("FileType", {
  pattern = "lisp",
  callback = function(ev)
    vim.keymap.set("n", "<leader>cb", cmera.build, { buffer = ev.buf, desc = "C-Mera Build (Scratch)" })
    vim.keymap.set("n", "<leader>cr", cmera.run,   { buffer = ev.buf, desc = "C-Mera Run (Terminal)" })
  end,
})
```

## 四、Treesitter 高亮增強 (2026 規範)

建立 `~/.config/nvim/queries/commonlisp/highlights.scm`。2026 年的 capture groups 更加細分：

```scheme
;; extends

((sym_lit) @keyword.directive
 (#any-of? @keyword.directive
   "include" "cpp" "pragma"))

((sym_lit) @keyword.function
 (#any-of? @keyword.function
   "function" "decl" "for" "while" "if" "when" "cond"
   "switch" "return" "break" "continue"
   "class" "namespace" "template" "instantiate" "constructor" "destructor"))

((sym_lit) @type.builtin
 (#any-of? @type.builtin
   "int" "char" "void" "float" "double" "long" "short"
   "unsigned" "signed" "bool" "size_t" "auto" "const" "static"))
```

## 五、格式化 (Conform.nvim)

現在 LazyVim 使用 `conform.nvim`。若要針對 Lisp 進行對齊，建議保持預設或使用 `lisp-format`：

```lua
-- ~/.config/nvim/lua/plugins/formatting.lua
return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      lisp = { "lisp_format" },
    },
  },
}
```

## 六、實戰 Tips (2026 版)

1. **Snacks Scratch**：產生的 C 源碼會出現在一個浮動視窗中，你可以按 `q` 快速關閉，或按 `<C-s>` 儲存。
2. **LSP 支援**：雖然 C-Mera 是 Lisp，但產生的 C++ 可以觸啟動 `clangd`。如果你在 `Snacks.scratch` 裡設定正確的 filetype，甚至能直接對生成的程式碼進行 LSP 檢查。
3. **AI 輔助**：如果你啟用了 `coding.copilot` 或 `coding.supermaven` Extras，它們現在能很好地理解 C-Mera 的 DSL 結構。

## 小結

2026 年的 LazyVim 整合關鍵在於 **非同步 (Async)** 與 **整合 (Snacks)**。不要再使用同步的 `vim.fn.system`，那會讓你的編輯器在處理複雜巨集時顯得笨重。
