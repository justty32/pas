# Veloren 進階模擬與 AI 邏輯深度拆解

本報告詳盡細說決策鏈、歷史模擬、建築生成、實時經濟以及文明對 AI 的影響，並標註原始碼位置。

---

## 1. 決策鏈 (Decision Chain / Behavior Tree)
Veloren 的 AI 採用層級式行為樹架構，將高層意圖拆解為底層動作。

### 1.1 核心結構
- **原始碼位置**：`server/agent/src/action_nodes.rs`
- **邏輯拆解**：
    - **行為節點 (`ActionNode`)**：這是 AI 的基本單位。每個節點會返回 `Success`, `Failure` 或 `Running`。
    - **選擇器 (Selector) 與 序列 (Sequence)**：
        - `Selector` 會按順序執行子節點，直到有一個成功。
        - `Sequence` 會按順序執行子節點，直到有一個失敗。
    - **戰鬥決策 (`attack.rs`)**：在 `server/agent/src/attack.rs` 中，AI 會計算當前技能的有效距離（`min_range`, `max_range`）並結合 `Health` 狀態決定是否切換為 `Flee` (逃跑) 狀態。

---

## 2. 歷史模擬 (Civilization & History Simulation)
在世界生成階段，Veloren 會運行一個簡化的歷史模擬來決定城鎮的分佈。

### 2.1 模擬管線
- **原始碼位置**：`world/src/civ/mod.rs` (主要邏輯在 `fn initial_civ_count` 與其後的生成循環)
- **邏輯拆解**：
    - **文明起源**：根據地圖大小計算初始文明數量 (`initial_civ_count`, 約 25 行)。
    - **擴張模擬**：文明會從起始點向外輻射，尋找資源豐富（水源、平原）的地點建立 `Site` (遺址/城鎮)。
    - **道路網絡**：在 `world/src/civ/mod.rs` 中，系統會計算城鎮間的連通性，並生成 `Track` (路徑) 與 `Bridge` (橋樑)。

---

## 3. 建築生成 (Building & Site Generation)
城鎮內的建築並非隨機放置，而是遵循佈局規則。

### 3.1 佈局與生成
- **原始碼位置**：`world/src/site/gen.rs` 與 `world/src/site/plot/`
- **邏輯拆解**：
    - **地塊劃分 (Plotting)**：在 `world/src/site/plot/` 中，系統將城鎮劃分為不同的 `Plot`。
    - **建築類型**：根據城鎮的功能（如礦鎮、農村），`gen.rs` 會調用不同的生成器。
    - **體素填充**：使用 `world/src/site/gen.rs` 中的算法，根據地塊大小動態填充 Voxel。例如，民宅會根據 `NameGen` 生成的名稱賦予不同的裝飾風格。

---

## 4. 實時經濟模擬 (Real-Time Economic Simulation / RTSim)
`rtsim` 是一個與遊戲同步運行的「高階抽象模型」。

### 4.1 核心機制
- **原始碼位置**：`rtsim/src/lib.rs` (哲學定義) 與 `rtsim/src/rule/` (具體規則)
- **邏輯拆解**：
    - **資源流動**：`rtsim/src/rule/trade.rs` (推測位置) 處理資源在不同 `Site` 間的供需平衡。
    - **動態定價**：物品價格由資源的稀缺度決定。
    - **離線模擬**：即使玩家不在該區域，`rtsim` 也會持續更新 NPC 的資產與位置，確保世界的連續性。

---

## 5. 文明決定 AI (Civilization-Driven AI)
文明的屬性直接影響了其中 NPC 的行為模式。

### 5.1 數據聯結
- **原始碼位置**：`rtsim/src/rule/npc_ai.rs` (關鍵橋樑) 與 `server/agent/src/data.rs`
- **邏輯拆解**：
    - **職業與身分**：NPC 的職業（農夫、衛兵、商人）由其所屬城鎮的文明類型（`Civ`）與經濟需求決定。
    - **行為約束**：在 `server/agent/src/action_nodes.rs` 中，AI 會讀取 NPC 的 `Alignment` (陣營) 與 `Role` (角色)。例如，一個衛兵 AI 節點會優先執行 `Patrol` (巡邏) 而非 `Wander` (漫遊)。
    - **社會動態**：文明間的戰爭或同盟狀態（存儲於 `rtsim`）會改變 NPC 對玩家或其他 NPC 的敵對行為。

---
*本分析結合了靜態原始碼掃描與系統邏輯推導，旨在提供 Veloren 模擬系統的底層運作視圖。*
