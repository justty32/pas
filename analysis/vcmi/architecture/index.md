# VCMI 1.7.3 架構分析

這份文件詳細分析了 VCMI (Heroes of Might & Magic III 開源引擎) 1.7.3 版本的原始碼結構、模組職責及核心流程。

## 核心組件 (Core Components)

VCMI 由三個主要二進制文件組成：

1.  **VCMI_lib (lib/)**: 核心共享庫，包含遊戲邏輯、資料結構、序列化、網路協議等。客戶端與伺服器均依賴此庫。
2.  **VCMI_server (server/)**: 遊戲伺服器，負責維護遊戲狀態 (GameState)、處理玩家請求、執行遊戲規則及事件分發。
3.  **VCMI_client (client/)**: 遊戲客戶端，負責圖形渲染 (SDL)、接收使用者輸入、展示遊戲狀態及動畫。

## 目錄導覽 (Directory Navigation)

- [`lib/`](lib.md): 核心共通庫，遊戲規則與基礎設施。
- [`client/`](client.md): 客戶端邏輯與渲染。
- [`server/`](server.md): 伺服器邏輯與狀態管理。
- [`AI/`](ai.md): AI 實作（戰鬥 AI 與冒險 AI）。
- [`config/`](config.md): 遊戲配置與 JSON 定義。
- [`scripting/`](scripting.md): Lua 腳本整合。
- [`launcher/` & `mapeditor/`](gui.md): 以 Qt 為基礎的圖形化介面工具。

## 關鍵技術 (Key Technologies)

- **渲染 (Rendering)**: SDL2
- **通訊 (Networking)**: Boost.Asio (序列化基於類 Boost.Serialization)
- **並行處理 (Concurrency)**: Intel TBB (用於 AI 運算、RMG、影像縮放等)
- **數據存儲 (Data)**: JSON (用於 Mod 定義與配置), .LOD/.TXT (原始遊戲資源)
- **腳本 (Scripting)**: Lua (LuaJIT)
- **模糊邏輯 (Fuzzy Logic)**: FuzzyLite (用於 AI 決策)

## 系統整體運作流程 (Overall System Flow)

VCMI 的運作可以概括為以下三個關鍵階段：

### 1. 初始化與加載 (Initialization & Loading)
- **資源掛載**: `VCMI_lib` 遍歷遊戲目錄與 Mod 目錄，根據 `config/filesystem.json` 掛載所有資源。
- **配置解析**: 加載並解析 `config/` 下的所有 JSON 檔案，構建兵種、寶物、法術等靜態數據庫。
- **紅利系統初始化**: 根據靜態配置構建初始的紅利系統樹。

### 2. 遊戲進行中 (Game Loop & Synchronization)
- **權威伺服器**: 無論單機還是聯網，`VCMI_server` 始終是唯一的權威。它維護著完整的 `CGameState`。
- **狀態同步**:
    - 客戶端監聽使用者輸入，發送動作請求封包。
    - 伺服器驗證並修改狀態，隨後廣播狀態增量變更。
    - 客戶端根據增量變更更新本地副本並觸發動畫與渲染。
- **並行處理**: AI (Nullkiller) 在後台線程中計算最優路徑與目標評分，計算完成後發送動作請求。

### 3. 模組化擴展 (Modding Expansion)
- **JSON 修改**: 通過 Mod 覆蓋原本的 JSON 配置。
- **Lua 介入**: 通過回調函數介入遊戲核心流程，實現複雜的邏輯變更。
