# Veloren 核心模組深度拆解分析

本文件深入分析 `veloren-common`、`veloren-server` 與 `veloren-world` 的內部構造與協作關係。

## 1. veloren-common: 遊戲規則的基石

`common` 模組是整個遊戲的物理、組件與系統的容器。它被設計為「平台無關」，既能在高效能的 `voxygen` 客戶端運行，也能在無頭伺服器上運行。

### 1.1 數據結構 (Components)
在 `common/src/comp/` 中定義了所有玩家、NPC 與環境的數據模型：
- **`Body`**: 存儲 Voxel 模型資訊與動畫狀態。
- **`Pos` / `Vel`**: 基本空間數據。
- **`Item`**: 道具與背包系統。
- **`Health` / `Energy`**: 玩家狀態屬性。

### 1.2 核心系統 (Systems)
`common/systems/` 下的系統負責處理數據的轉換：
- **`ProjectileSystem`**: 處理遠程武器的飛行與碰撞。
- **`MeleeSystem`**: 處理近戰攻擊判斷。
- **`PhysicsSystem`**: 處理重力、碰撞反應與地形交互。
- **`BuffSystem`**: 處理狀態效果（如中毒、燃燒）。

---

## 2. veloren-server: 權威的心臟

伺服器負責維護一個全球統一的遊戲狀態，並處理持久化存儲。

### 2.1 核心循環 (The Tick Loop)
伺服器在 `server/src/lib.rs` 中維護主要循環，每秒執行固定次數的 Tick（通常是 30Hz 或 60Hz）。
- **流程**：接收網路封包 -> 更新系統 -> 執行 AI -> 持久化數據 -> 廣播差異。

### 2.2 持久化 (Persistence)
- **技術**：使用 `rusqlite` (SQLite)。
- **範疇**：玩家存檔、建築、城鎮狀態以及特定的地形變動。
- **目錄**：`server/src/persistence/`。

### 2.3 NPC 智慧 (Server-Agent)
位於 `server/agent/`，這是一個獨立的子模組，負責處理 NPC 的決策樹、仇恨管理與尋路請求。

---

## 3. veloren-world: 世界生成的魔法

這是 Veloren 最具特色的部分，採用多層級的生成策略。

### 3.1 生成層級 (Generation Layers)
1. **Macro-scale (`world/src/sim/`)**: 生成大陸形狀、板塊活動、氣候、降雨與基礎氣壓圖。
2. **Meso-scale (`world/src/civ/`)**: 模擬歷史演進，決定城鎮位置、道路網絡與國家邊界。
3. **Micro-scale (`world/src/site/`)**: 生成具體的建築、地城細節與植被。

### 3.2 地形索引 (The Index)
`world/src/index.rs` 提供了高效的空間索引系統。當伺服器需要查詢某個坐標的地貌（如：這裡是森林還是雪山？）時，會調用此索引。

---

## 4. 三者間的協作流 (Collaboration Flow)

1. **伺服器啟動**：`server` 調用 `world` 生成或載入地圖種子。
2. **玩家進入**：`server` 建立一個 `common` 中的 `Entity`，並掛載 `common/comp/` 中的組件。
3. **戰鬥發生**：玩家在 `voxygen` 發動攻擊 -> 訊號傳至 `server` -> `server` 調用 `common/systems/melee.rs` 進行判斷 -> 如果生物死亡，`server` 調用 `persistence` 更新資料庫。

---
*本報告旨在提供核心模組的結構性導航，細節實現代碼請參考各模組的 `lib.rs`。*
