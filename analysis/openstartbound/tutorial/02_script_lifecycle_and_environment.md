# 教學 02：腳本生命週期與沙箱環境

OpenStarbound 的腳本不是從頭執行到尾，而是由引擎在特定時機調用預定義的「鉤子函數」。

## 1. 核心鉤子函數 (Hooks)
在你的 Lua 腳本中，引擎會尋找並執行以下函數：

### `init()`
- **觸發時機：** 實體或腳本上下文首次創建時。
- **用途：** 初始化變量、緩存配置、註冊初始狀態。

### `update(dt)`
- **觸發時機：** 每一幀 (通常是 60Hz)。
- **參數：** `dt` 是自上一幀以來的秒數（通常約 0.016s）。
- **用途：** 處理物理計算、AI 邏輯、狀態檢查。

### `uninit()`
- **觸發時機：** 實體被銷毀或腳本被移除時。
- **用途：** 清理定時器、釋放資源、保存持久化數據。

## 2. 沙箱環境 (_ENV)
每個實體都有獨立的 `_ENV`。
- **局部變量：** 使用 `local` 關鍵字定義的變量僅在當前代碼塊可見。
- **實體全局變量：** 不加 `local` 定義的變量在當前實體的所有腳本文件中共享。
- **引擎命名空間：** 引擎提供了預裝載的全局表，如 `world`, `object`, `entity`, `animator`。

## 3. 範例腳本結構
```lua
local healAmount = 0

function init()
  -- 從 JSON 配置讀取數值
  healAmount = config.getParameter("healAmount", 10)
  sb.logInfo("Healing script initialized with amount: %s", healAmount)
end

function update(dt)
  -- 每幀邏輯
  if entity.id() then
    -- 執行某些檢查
  end
end

function uninit()
  sb.logInfo("Cleaning up...")
end
```
注意：`sb` 是 **Starbound** 縮寫，提供日誌 (`sb.logInfo`) 與數據轉換工具。
