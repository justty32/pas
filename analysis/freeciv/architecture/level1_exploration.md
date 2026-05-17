# Freeciv Level 1 分析：初始探索與技術棧

## 專案基本資訊
- **名稱**: Freeciv
- **類型**: 開源帝國建設策略遊戲 (類似 Civilization)
- **架構**: 主從式架構 (Client-Server)
- **版本**: 3.4-dev

## 技術棧 (Technology Stack)
- **核心語言**: C (ISO C99/C11)
- **建構系統**: Meson (推薦), Autotools (傳統)
- **使用者介面 (Client UI)**:
    - GTK+ (3.22, 4.0, 5.0)
    - Qt
    - SDL2 / SDL3
- **腳本系統**: Lua (用於遊戲規則、伺服器腳本與客戶端擴展)
- **網路通訊**: 自定義協議，使用 `common/generate_packets.py` 自動生成封包處理代碼
- **資料儲存**: 自定義存檔格式 (`server/savegame`)

## 核心目錄職責
- `common/`: 存放客戶端與伺服器共用的核心邏輯、資料結構 (如 `city`, `unit`, `map`) 及網路協議定義。
- `server/`: 伺服器端邏輯，負責遊戲循環、世界生成、規則執行及 AI 管理。
    - `server/srv_main.c`: 伺服器進入點。
- `client/`: 客戶端邏輯，包含多個 GUI 後端實現。
    - `client/client_main.c`: 客戶端進入點。
- `ai/`: AI 玩家的實現，包含不同的算法與策略。
- `lua/`: Lua 引擎整合。
- `utility/`: 通用的工具函式庫 (字串處理、日誌、記憶體管理)。
- `data/`: 遊戲資源檔案 (rulesets, tilesets, 翻譯)。

## 初步見解
1. **高度模組化**: 透過 `common` 層實現邏輯復用，且客戶端與介面實現分離 (gui-stub, gui-gtk 等)，顯示出極佳的架構設計。
2. **網路自動化**: 封包自動生成機制降低了維護複雜度。
3. **跨平台與多前端**: 支持多種介面庫，顯示其對不同平台的高度適應性。
