# 核心引擎架構 - Advanced Strategic Command (ASC)

ASC 的核心引擎負責管理遊戲狀態、地圖網格及所有遊戲實體。

## 核心類別: GameMap (`source/gamemap.h`)

`GameMap` 是引擎的中央類別，包含：

- **MapFields 網格**: 代表六角網格的 `MapField` 物件 2D 陣列或向量。
- **玩家 (Players)**: 代表遊戲中各勢力的 `Player` 物件列表。
- **遊戲參數**: 規則、地形與地圖範圍屬性。

## 地圖網格: MapField (`source/mapfield.h`)

地圖上的每個欄位由 `MapField` 物件表示，保存：

- **地形 (Terrain)**: 欄位的地形類型。
- **單位 (Units)**: 目前在該欄位上的單位列表。
- **建築 (Buildings)**: 指向該欄位建築的指標（若有）。
- **物件 (Objects)**: 其他地圖物件（如障礙物或資源）。
- **可見度 (Visibility)**: 各玩家對該欄位的視野資訊（戰爭迷霧）。

## 實體: ContainerBase (`source/containerbase.h`)

ASC 中大多數互動實體皆繼承自 `ContainerBase`。此基類提供「容納」其他單位的實體功能。

### 載具 (Vehicle, `source/vehicle.h`)

代表坦克、步兵、船隻及飛機等單位，具備：

- **移動**: 燃料、移動力、移動類型。
- **戰鬥**: 武器、裝甲、經驗值。
- **負載**: 搭載其他單位的武力。

### 建築 (Building, `source/buildings.h`)

代表基地、工廠及資源收集站等固定結構，具備：

- **生產**: 製造單位或資源的能力。
- **防禦**: 結構完整度與防禦武器。
- **研究**: 用於解鎖新技術的設施。

## 遊戲邏輯

- **戰鬥系統 (`source/attack.cpp`)**: 處理攻擊、傷害與反擊的計算。
- **移動系統**: 為 `Vehicle` 與 `GameMap` 的一部分，管理路徑搜尋（常使用 A* 演算法，`source/astar2.h`）。
- **研究系統 (`source/research.cpp`)**: 管理科技樹及每個玩家的研究進度。
- **事件系統 (`source/gameevents.cpp`)**: 一個基於觸發器的系統，允許在地圖上實作腳本化行為（例如進入特定欄位時生成單位）。
