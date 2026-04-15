# VCMI_client 模組分析 (`client/`)

`VCMI_client` 負責展現遊戲狀態、處理使用者輸入以及播放動畫。它是與玩家互動的唯一介面。

## 核心組件

### 1. 使用者介面與輸入 (`CPlayerInterface`)
- 這是客戶端的「大腦」。它過濾使用者的鼠標、鍵盤輸入，並將其轉換為遊戲動作。
- 它管理 UI 堆疊，決定當前顯示哪個視窗（城鎮視窗、英雄視窗等）。

### 2. 網路通訊 (`CServerHandler`)
- 負責與 `VCMI_server` 維持連接。
- 接收來自伺服器的封包 (`NetPack`)，更新本地的 `CGameState` 複本。
- 發送玩家的請求封包到伺服器。

### 3. 渲染引擎 (`render/`, `renderSDL/`)
- 基於 SDL2。
- **`render/`**: 抽象渲染邏輯，處理精靈 (Sprites)、圖層管理。
- **`renderSDL/`**: 具體的 SDL2 實作，處理窗口、緩衝區交換、基本的 2D 繪圖。

### 4. 遊戲引擎控制器 (`GameEngine`)
- 管理客戶端的生命週期：從主選單、載入介面到地圖視圖切換。

### 5. GUI 組件與視窗 (`widgets/`, `windows/`, `gui/`)
- **`CIntObject`**: UI 物件的基類。
- **`widgets/`**: 可重用的 UI 組件，如按鈕 (`Buttons.cpp`)、滑塊 (`Slider.cpp`)、文字輸入框 (`CTextInput.cpp`)。
- **`windows/`**: 預定義的遊戲視窗，如戰鬥視窗、城鎮視窗等。

## 關鍵流程
1. **渲染流程**: `MainGUI` 執行緒循環調用渲染器，遍歷當前可見的 UI 組件和地圖層進行繪製。
2. **事件處理**: 使用者點擊 -> `CPlayerInterface` 識別物件 -> 發送請求到伺服器 -> 伺服器驗證並廣播狀態變更 -> 客戶端接收變更並更新顯示。
