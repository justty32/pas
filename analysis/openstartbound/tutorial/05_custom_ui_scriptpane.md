# 教學 05：自定義 UI (ScriptPane)

`ScriptPane` 允許開發者製作完全自定義的交互視窗。這在製作自定義工作檯、商店或複雜的機器控制面板時非常有用。

## 1. UI 定義 (Config)
UI 通常在 `.config` 文件中定義佈局，並指定一個處理腳本：
```json
{
  "gui": {
    "background": { "type": "background", "fileHeader": "...", "fileBody": "..." },
    "close": { "type": "button", "base": "/interface/x.png", "position": [161, 189] },
    "myLabel": { "type": "label", "value": "Current Score: 0", "position": [50, 100] }
  },
  "scripts": ["/interface/scripted/myscript.lua"]
}
```

## 2. UI 腳本回調
在 UI 腳本中，有一些特殊的命名空間：
- **`pane`：** 控制視窗本身（如 `pane.dismiss()`）。
- **`widget`：** 控制視窗內的組件（按鈕、標籤、輸入框）。

### 常用函數
- `widget.setText(name, text)`：更新標籤或輸入框文本。
- `widget.setVisible(name, bool)`：隱藏或顯示組件。
- `widget.registerMemberCallback(name, function)`：註冊按鈕點擊事件。

## 3. 實作練習：計數器視窗
```lua
local count = 0

function init()
  count = 0
  updateLabel()
end

-- 此函數在佈局中對應的按鈕點擊時被調用 (需在 config 註冊)
function incrementClicked()
  count = count + 1
  updateLabel()
end

function updateLabel()
  widget.setText("myLabel", "Current Score: " .. count)
end

function update(dt)
  -- 可在此處執行即時的 UI 動畫或刷新邏輯
end
```

## 4. 結語
至此，你已經掌握了 OpenStarbound 的核心 Modding 流程。
- **基礎：** Mod 結構與 JSON Patch。
- **邏輯：** 實體生命週期與世界交互。
- **表現：** 動畫器與視覺同步。
- **介面：** ScriptPane 自定義 UI。

建議深入閱讀 `source/game/scripting/` 下的各個 `Bindings.cpp` 檔案，以發現更多強大的隱藏 API。
