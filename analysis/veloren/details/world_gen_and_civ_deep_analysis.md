# 世界生成、文明與地質模擬深度分析 (Analysis)

## 1. 地質侵蝕算法 (`world/src/sim/erosion.rs`)
Veloren 的地圖並非靜態，而是模擬了水文與物理侵蝕的結果。

### 核心邏輯拆解：
- **水流累積 (`fn get_multi_drainage`)**：
    - **位置**：`world/src/sim/erosion.rs` (約 60 行)
    - **邏輯**：這是一個權責分發過程。降雨作為初始權重，根據地形的「坡度」(`downhill`) 向下傳遞，累積出流量數據 (`flux`)。這決定了河流的寬度與深度。
- **湖泊溢流機制 (`RiverKind::Lake`)**：
    - **位置**：`world/src/sim/erosion.rs` (約 105 行)
    - **邏輯**：當河流進入低窪地，系統會標記為 `Lake`。它會尋找一個 `neighbor_pass_pos` (溢流點)，模擬湖泊填滿後河水重新流出的物理現象。

## 2. 文明擴張與選址 (`world/src/civ/mod.rs`)
### 核心邏輯拆解：
- **文明數計算 (`fn initial_civ_count`)**：
    - **位置**：`world/src/civ/mod.rs` (約 40 行)
    - **邏輯**：基於地圖 Log 尺度計算初始文明點，確保在地圖縮放時文明密度保持一致。
- **城鎮平整與生成 (`establish_site`)**：
    - **位置**：`world/src/civ/mod.rs` (約 420 行)
    - **邏輯**：在放置建築前，會對地塊進行 `Flatten ground` 操作，避免體素建築在斜坡上產生懸空。

---
*本文件由分析任務自動生成。*
