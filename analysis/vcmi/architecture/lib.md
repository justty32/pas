# VCMI_lib 模組分析 (`lib/`)

`VCMI_lib` 是專案的核心庫，被客戶端和伺服器共享。它定義了遊戲的所有基本規則、資料結構以及跨模組的基礎設施。

## 核心子模組

### 1. 遊戲狀態 (`gameState/`)
- **`CGameState`**: 遊戲數據的中央存儲庫。包含地圖 (`CMap`)、所有玩家狀態 (`CPlayerState`)、軍隊、資源等。
- **`GameStatePackVisitor`**: 負責遊戲狀態的序列化與反序列化，用於存檔載入及網路傳輸。

### 2. 紅利系統 (`bonuses/`)
VCMI 的靈魂。幾乎所有的遊戲修正項（英雄技能、寶物加成、地形影響等）都通過此系統處理。
- **`CBonusSystemNode`**: 紅利系統的基礎節點。加成效果在節點樹中傳遞。
- **`Bonus`**: 代表單個加成效果（類型、數值、持續時間、來源）。
- **`Limiters` & `Propagators`**: 用於控制加成的適用範圍（例如：僅限特定兵種）及傳遞方式。

### 3. 地圖物件 (`mapObjects/`)
定義了地圖上所有可交互物件。
- **`CGObjectInstance`**: 地圖物件的基底類。
- 具體實作包括：`CGHeroInstance` (英雄), `CGTownInstance` (城鎮), `CGResourceInstance` (資源) 等。

### 4. 網路與序列化 (`network/`, `serializer/`)
- **序列化**: 自定義的序列化框架，旨在高效傳輸 `CGObjectInstance`（僅傳送 ID 而非完整對象）。
- **`networkPacks/`**: 定義了所有客戶端與伺服器之間交換的封包 (`NetPack`)。

### 5. AI 與路徑搜尋 (`pathfinder/`)
- 提供冒險地圖與戰鬥地圖的路徑運算，考慮英雄移動力、地形損耗及障礙物。

### 6. 配置處理 (`json/`, `config/`)
- 大量使用 JSON 來定義遊戲數據（兵種屬性、寶物數值等），使得 VCMI 非常易於模組化 (Modding)。

### 7. 其他重要組件
- **`filesystem/`**: 處理遊戲資源檔案載入。
- **`rmg/`**: 隨機地圖生成邏輯。
- **`spells/`**: 魔法系統邏輯。
- **`battle/`**: 戰鬥規則與邏輯。
