# Veloren 特色子系統深度拆解：AI、地形、城鎮與經濟

本報告專注於 Veloren 中最具技術挑戰性的四個核心子系統。

## 1. AI 行為系統 (Artificial Intelligence)

Veloren 的 AI 採用 **行為樹 (Behavior Tree)** 架構，主要集中在 `server/agent` 模組。

### 1.1 決策鏈 (Decision Chain)
- **行動節點 (`action_nodes.rs`)**：定義了 AI 的基礎原子行為，如 `SeekTarget` (尋找目標)、`Flee` (逃跑)、`Idle` (發呆)。這些節點組合成複雜的樹狀結構。
- **戰鬥 AI (`attack.rs`)**：根據目標距離、血量與技能冷卻時間，動態選擇攻擊方式。它會考慮 NPC 的 `Body` 類型（如四足動物 vs 人類）來套用不同的戰鬥風格。
- **感知系統**：透過 `common/src/astar.rs` 進行路徑搜尋，並結合視野範圍判斷仇恨。

---

## 2. 地圖生成與生物群系 (Procedural Map & Biomes)

Veloren 採用 **模擬引導生成 (Simulation-guided Generation)**，而不僅是單純的噪音函數。

### 2.1 地理物理模擬
- **地形形成 (`erosion.rs`)**：在原始海拔數據上模擬降雨沖刷與侵蝕，形成自然的山脊與河谷。
- **生物群系 (Biomes)**：
    - 根據 **Whittaker 生物群系分類法**，利用模擬出的溫度（海拔與緯度決定）與濕度（降雨與水體決定）來映射不同的群系（如：熱帶雨林、凍原、荒漠）。

---

## 3. 城鎮生成與文明模擬 (Civ & Site Generation)

### 3.1 歷史模擬 (`world/src/civ/`)
在生成具體地塊前，`civ` 模組會進行一場短暫的「歷史演進」：
- 決定肥沃的土地 -> 吸引文明定居 -> 建立道路 (`way.rs`) -> 發展航線 (`airship_travel.rs`)。

### 3.2 建築生成 (`world/src/site/`)
- **生成規則 (`gen.rs`)**：使用程序化算法根據場地大小與文化風格生成房屋、地城、城牆。
- **多樣性**：透過 `genstat.rs` 管理不同文明（如矮人、人族）的建築參數與風格多樣性。

---

## 4. 經濟與實時模擬 (RT-Sim & Economy)

這是 Veloren 最具野心的系統，模擬了一個「活的世界」。

### 4.1 實時模擬 (`rtsim/`)
- **非玩家實體 (Offline Simulation)**：即使玩家不在附近，`rtsim` 也會模擬 NPC 的移動、交易與生產行為。
- **商貿流動**：`rtsim` 會決定商隊從 A 城搬運資源到 B 城。

### 4.2 供需與價格 (`world/src/civ/econ.rs`)
- 資源的分佈決定了價格。如果某地缺乏礦產，該地的裝備價格就會攀升。
- 此系統直接影響 `rtsim` 的商貿路徑選擇。

---

## 5. 系統間的深度耦合 (The Big Picture)

1. **地理影響經濟**：`world/sim` 決定了礦山的位置 -> `civ/econ` 建立產能 -> `rtsim` 派商隊運輸。
2. **文明決定 AI**：城鎮的 `site` 生成 -> 決定 NPC 的生活軌跡 -> `server/agent` 驅動 NPC 的日常與防禦行為。

---
*本報告揭示了 Veloren 如何透過多層次模擬構建出具有深度與代入感的動態世界。*
