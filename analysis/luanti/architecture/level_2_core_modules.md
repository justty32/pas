# Level 2: 核心模組職責分析

## 核心權責劃分

Luanti 採用客戶端-伺服器 (C/S) 架構，核心邏輯主要分布在以下模組：

### 1. 伺服器模組 (src/server)
- **主要類別**：`Server` (`src/server.h`)
- **核心職責**：
    - **世界管理**：透過 `ServerEnvironment` 維護地圖節點、實體 (Entities) 與玩家。
    - **網路通訊**：處理與客戶端的封包交換。
    - **資源調度**：`EmergeManager` 負責非同步的地圖生成與載入。
    - **安全與權限**：驗證玩家行為（反作弊）與權限。
    - **腳本宿主**：初始化並執行伺服器端 Mods。

### 2. 客戶端模組 (src/client)
- **主要類別**：`Client` (`src/client/client.h`)
- **核心職責**：
    - **渲染管線**：`RenderingEngine` 處理所有視覺輸出（包含 Shader, Mesh, Sky）。
    - **使用者交互**：`InputHandler` 捕捉鍵盤、滑鼠與搖桿輸入。
    - **音訊輸出**：透過 `SoundManager` 播放遊戲音效。
    - **本地預測**：處理本地玩家的運動預測以減少延遲感。
    - **GUI 系統**：負責顯示 Formspec（遊戲內選單）與 HUD。

### 3. 腳本系統與 C++ 綁定 (src/script)
- **進入點**：`ServerScripting` 與 `ClientScripting`
- **結構分流**：
    - `src/script/common/`: 客戶端與伺服器共用的腳本輔助工具。
    - `src/script/lua_api/`: 具體的 API 綁定實作（例如：`l_base.cpp`, `l_mapgen.cpp`）。
    - `src/script/cpp_api/`: 提供給 C++ 引擎呼叫 Lua 的封裝。
- **職責**：
    - 將 C++ 內部的複雜物件（如節點定義、物品堆疊）映射為 Lua 可操作的物件。
    - 提供回呼 (Callbacks) 機制（例如：`on_joinplayer`, `on_punchnode`）。

## 技術細節標註
- **伺服器主要循環**：`Server::AsyncRunStep()` (`src/server.cpp`) 處理非同步步進。
- **客戶端主要循環**：`Game::run()` (`src/client/game.cpp`) 封裝了繪圖與事件處理的主要循環。
