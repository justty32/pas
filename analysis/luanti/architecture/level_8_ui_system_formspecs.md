# Level 8: UI 系統 (Formspecs) 深度分析

## 1. 核心定義：Formspec DSL
Luanti 的 UI 採用了一種獨特的字串定義方式。這種字串會從伺服器傳送到客戶端，由客戶端進行解析與繪製。
- **原始碼位置**：`src/gui/guiFormSpecMenu.cpp`
- **解析器入口**：`GUIFormSpecMenu::element_parsers` (行號 2895)。
- **支援元素**：包含 `size`, `list` (背包格), `button`, `field` (輸入框), `label`, `image` 等。

## 2. 解析與生成流程 (String to GUI)
以按鈕 (`button`) 為例：
1. **指令接收**：伺服器呼叫 `minetest.show_formspec`，將 `button[1,1;2,1;btn_id;Click Me]` 發送給客戶端。
2. **標籤匹配**：客戶端的 `GUIFormSpecMenu` 匹配到 `button` 標籤，呼叫 `parseButton` (行號 974)。
3. **座標換算**：使用 `getRealCoordinateBasePos` 將抽象座標轉換為實際的像素座標。
4. **組件實例化**：呼叫 `GUIButton::addButton` (行號 1025)，在 Irrlicht 的介面樹中新增一個按鈕物件。
5. **元數據儲存**：將按鈕的 ID (`btn_id`) 儲存在 `FieldSpec` 結構中，以便後續辨識。

## 3. 互動回傳機制 (Event Handling)
UI 的核心挑戰在於如何將客戶端的點擊傳回伺服器的 Lua 環境：
1. **事件捕捉**：`GUIFormSpecMenu::OnEvent` (行號 4203) 監聽 Irrlicht 的 GUI 事件。
2. **數據封裝**：當點擊發生時，呼叫 `acceptInput()`。這會掃描介面上所有的輸入框與按鈕狀態。
3. **網路傳輸**：將這些數據封裝為 `TOSERVER_INVENTORY_FIELDS` 封包並發送到伺服器。
4. **Lua 觸發**：伺服器接收後，將 ID 與數值轉換為 Lua Table，觸發 `minetest.register_on_player_receive_fields` 回呼。

## 4. 特殊機制：客戶端與伺服器 Formspec
- **伺服器端 (Server-side)**：由 Mod 定義，用於遊戲邏輯（如商店、任務選單）。
- **客戶端端 (Client-side)**：內建於引擎中，用於登入選單、設定頁面。
- **靜態與動態**：Formspec 是靜態的。若要更新 UI（例如進度條），伺服器必須重新發送整個 Formspec 字串。
