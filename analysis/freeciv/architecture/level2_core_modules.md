# Freeciv Level 2 分析：核心模組職責與進入點

## 程式進入點 (Entry Points)

### 伺服器端 (Server)
- **檔案**: `server/srv_entrypoint.c` 與 `server/srv_main.c`
- **流程**:
    1. `main()` (`srv_entrypoint.c`): 處理命令列參數、初始化基本工具 (日誌、隨機數、安全性檢查)。
    2. `srv_main()` (`srv_main.c`): 核心伺服器循環。
- **核心循環**:
    - 採用 `do { ... } while(TRUE)` 結構，每個循環代表一個遊戲階段 (從 Initial 到 Running 再到 Over)。
    - 使用 `server_sniff_all_input()` 進行非同步 I/O 輪詢 (基於 `select()`)，處理網路封包與控制台輸入。

### 客戶端 (Client)
- **檔案**: `client/gui-<ui_backend>/gui_main.c` 與 `client/client_main.c`
- **流程**:
    1. `main()` (`gui_main.c`): 介面相關的初始設定，隨後呼叫 `client_main()`。
    2. `client_main()` (`client_main.c`): 跨前端的通訊與邏輯初始化。
    3. `ui_main()` (`gui_main.c`): 進入特定介面庫的主循環 (如 `gtk_main()`)。
- **抽象層**: 透過 `client/include/` 下的 `*_g.h` (Generic Headers) 定義介面，具體 GUI 後端需實作這些介面。

## 核心權責劃分

### 1. Common 層 (`common/`)
- **封裝數據模型**: 定義 `struct player`, `struct city`, `struct unit`, `struct map` 等核心資料結構。
- **通訊協議**: 定義與處理網路封包。使用 `generate_packets.py` 自動生成封包編碼/解碼代碼，確保 C/S 端一致。
- **規則運算**: 處理不涉及 UI 或 I/O 的純邏輯 (如戰鬥結果計算、科研進度)。

### 2. Server 層 (`server/`)
- **權威管理**: 維護遊戲的「真實狀態」(True State)。
- **遊戲流程控制**: 處理回合切換 (`cityturn.c`)、世界生成 (`generator/`) 與存檔 (`savegame/`)。
- **AI 驅動**: 管理電腦玩家的決策。

### 3. Client 層 (`client/`)
- **狀態鏡像**: 維護伺服器傳回的遊戲狀態副本。
- **介面呈現**: 處理地圖渲染、視窗管理、音效播放。
- **代理 (Agents)**: 提供自動化助手 (如 CMA 城市管理代理) 協助玩家。

## 介面抽象機制 (Interface Abstraction)
Freeciv 使用 `struct functions` 結構體將特定上下文的函數綁定到通用邏輯中：
- `fc_interface_init_server()`: 綁定伺服器專屬函數 (如設定檔讀取)。
- `fc_interface_init_client()`: 綁定客戶端專屬函數 (如 UI 提示)。

## 網路模型
- **非同步 I/O**: 伺服器使用 `server_sniff_all_input` 統一處理所有輸入。
- **事件驅動**: 收到封包後，透過分發器 (Dispatcher) 呼叫對應的處理函式 (如 `handle_unit_move`)。
