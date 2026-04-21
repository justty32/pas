# 教學 09：Neovim / LazyVim 整合 C-Mera (2026 WSL/Linux 世界太平版)

這份教學專為追求「編輯自由」的開發者打造。我們去除了會干擾輸入感的結構編輯器，保留核心的非同步編譯與 REPL 功能，讓你找回「想刪就刪、想貼就貼」的快感。

## 一、系統環境準備 (核心依賴)

1.  **安裝 SBCL 與 Quicklisp**：
    ```bash
    sudo apt install sbcl
    curl -O https://beta.quicklisp.org/quicklisp.lisp
    sbcl --load quicklisp.lisp --eval '(quicklisp-quickstart:install)' --eval '(ql:add-to-init-file)' --quit
    ```
2.  **安裝 Swank (用於 Conjure REPL)**：
    在 `sbcl` 中執行：`(ql:quickload :swank)`。
3.  **確保 `cm` 指令在 PATH 中**：輸入 `cm --version` 應有反應。

## 二、世界太平：插件配置 (`lua/plugins/cmera.lua`)

此配置直接**禁用**了過於聰明的 `vim-sexp`，並修正了 `autopairs`，讓你找回完全的貼上與輸入自由。

```lua
return {
  -- 1. 語法高亮 (保留 Treesitter)
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      if type(opts.ensure_installed) == "table" then
        vim.list_extend(opts.ensure_installed, { "commonlisp" })
      end
    end,
  },

  -- 2. 核心修正：徹底禁用 vim-sexp (世界太平版)
  -- 這樣你就再也不會遇到「無法貼上」或「括號跳轉」的問題了
  { "guns/vim-sexp", enabled = false },
  { "tpope/vim-sexp-mappings-for-regular-people", enabled = false },

  -- 3. 修正 autopairs 行為，防止它在你輸入右括號時亂跳
  {
    "windwp/nvim-autopairs",
    opts = {
      enable_moveright = false, 
    },
  },

  -- 4. Conjure REPL (保留強大的即時求值功能)
  {
    "Olical/conjure",
    ft = { "lisp" },
    init = function()
      vim.g["conjure#filetype#lisp"] = "conjure.client.common-lisp.swank"
    end,
  },

  -- 5. 載入自訂建置邏輯
  {
    "nvim-lua/plenary.nvim",
    config = function()
      require("config.cmera")
    end,
  },
}
```

## 三、C-Mera 核心邏輯實作 (`lua/config/cmera.lua`)

此腳本負責非同步編譯並在右側預覽產出的 C/C++ 源碼。

```lua
local M = {}

local function detect_lang(buf)
  local first = vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or ""
  if first:match("cm:%s*c%+%+") or first:match("cm:%s*cxx") then return "c++" end
  return "c"
end

local function notify(msg, level)
  if _G.Snacks and _G.Snacks.notify then
    local fn = _G.Snacks.notify[level]
    if type(fn) == "function" then fn(msg) else _G.Snacks.notify.info(msg) end
  else
    vim.notify(msg, vim.log.levels[level:upper()] or vim.log.levels.INFO)
  end
end

function M.build()
  local buf = vim.api.nvim_get_current_buf()
  local file = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(buf), ":.") 
  if file == "" then return end
  
  vim.cmd("silent! write")
  local lang = detect_lang(buf)
  notify("C-Mera 編譯中: " .. file, "info")

  vim.system({ "cm", lang, file }, { text = true }, function(obj)
    vim.schedule(function()
      if obj.code ~= 0 then
        notify("編譯出錯 (Exit " .. obj.code .. "):\n" .. (obj.stderr or ""), "error")
        return
      end

      local content = obj.stdout or ""
      if content == "" then notify("執行成功但無產出。", "warn") return end
      local lines = vim.split(content:gsub("\r", ""), "\n")

      if _G.Snacks then
        local out_buf = vim.api.nvim_create_buf(false, true)
        vim.api.nvim_buf_set_lines(out_buf, 0, -1, false, lines)
        vim.bo[out_buf].filetype = (lang == "c++" and "cpp" or "c")
        
        _G.Snacks.win({
          buf = out_buf,
          width = 0.45,
          position = "right",
          backdrop = false,
          wo = { cursorline = true, number = true },
          keys = { ["q"] = "close" },
        })
      else
        vim.cmd("vnew")
        local new_buf = vim.api.nvim_get_current_buf()
        vim.api.nvim_buf_set_lines(new_buf, 0, -1, false, lines)
        vim.bo[new_buf].filetype = (lang == "c++" and "cpp" or "c")
        vim.bo[new_buf].buftype = "nofile"
        vim.bo[new_buf].bufhidden = "wipe"
      end
      
      notify("C-Mera 編譯成功！", "info")
    end)
  end)
end

vim.api.nvim_create_user_command("CmeraBuild", M.build, {})
return M
```

## 四、為什麼「世界太平版」更好？

1.  **想貼就貼**：不再有 Smart Paste 檢查，無論括號平不平衡，文字都能直接進去。
2.  **想刪就刪**：不再有結構保護，按退格鍵就真的會刪除字元。
3.  **直覺輸入**：輸入右括號時，游標不會莫名其妙跳到外面，而是會在當前位置留下括號。

## 五、按鍵映射設定 (`lua/config/keymaps.lua`)

```lua
require("config.cmera")
vim.keymap.set("n", "<leader>cb", ":CmeraBuild<CR>", { desc = "C-Mera Build (Right-View)" })
```
