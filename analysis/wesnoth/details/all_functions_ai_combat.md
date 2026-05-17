# Wesnoth 全函數工程解析：AI 戰鬥與決策核心 (`attack.cpp`)

本文件窮舉並解析了 Wesnoth 戰鬥決策模組 `src/ai/default/attack.cpp` 中的所有函數。此模組解決了 AI 如何在不確定性環境（機率傷害）下進行期望值最佳化。

---

## 1. 戰鬥評估系統 (`attack_analysis` 類別)

此類別封裝了一次「潛在攻擊行動」的所有環境變數與結果指標。

### 1.1 `attack_analysis::analyze(...)`
- **工程語義**：執行確定性戰鬥模擬，產生機率分布與特徵值。
- **參數解析**：
  - `map`, `units`: 當前遊戲世界狀態的唯讀視圖。
  - `dstsrc`, `srcdst`: 單位移動的可能性映射圖。
  - `aggression`: 好戰度，影響損失折算的係數。
- **演算法細節**：
  1. **動態身價計算 (Valuation)**：目標單位的基本建造成本（Cost）加上其經驗值（XP）比例的加成：$Value = Cost \cdot (1 + \frac{XP}{Max\_XP})$。這定義了目標的戰略價值。
  2. **空間模擬 (Spatial Pre-computation)**：將攻擊者在記憶體中暫時移至預定的攻擊格子。
  3. **快取查詢 (Caching)**：利用 `unit_stats_cache` 查找之前是否計算過相同的攻擊者與防禦者對決，若有則直接讀取機率分佈，時間複雜度由 $O(N)$ 降至 $O(1)$。
  4. **期望值提取 (Expectation Extraction)**：
     - 從戰鬥矩陣中提取 $P(Defender\_HP = 0)$ 作為 `chance_to_kill`。
     - 提取 $P(Attacker\_HP = 0)$ 並乘上攻擊者價值，得到 `avg_losses`（預期損失）。
  5. **狀態補償 (State Compensation)**：若攻擊者中毒，預期損失會額外增加，反映持續傷害的潛在成本；若攻擊者能升級，損失轉為負值（視為收益）。

### 1.2 `attack_analysis::attack_close(loc)`
- **工程語義**：空間聚類檢查 (Spatial Proximity Check)。
- **演算法細節**：
  - 接收一個坐標 `loc`。
  - 遍歷全域紀錄中最近發生過戰鬥的坐標集合。
  - 使用曼哈頓/六角格距離計算。若距離小於 $4$，回傳 `true`。
  - **應用場景**：提供戰場熱點 (Hotspot) 資訊，幫助 AI 判斷是否需要前往該處進行群體支援，避免單位分散。

### 1.3 `attack_analysis::rating(...)`
- **工程語義**：決策目標函數 (Objective Function)。返回一個實數作為該行動的最終權重。
- **演算法細節**：
  1. **基礎期望值計算**：
     $$ Value = P_{kill} \cdot V_{target} - E_{loss} \cdot (1 - \alpha) $$
     其中 $\alpha$ 為好戰度 (`aggression`)。當 $\alpha \rightarrow 1$，損失項趨近於 $0$。
  2. **風險敞口懲罰 (Exposure Penalty)**：
     - 若攻擊位置的防禦力 (`terrain_quality`) 低於原本可能待著的最佳位置 (`alternative_terrain_quality`)，觸發懲罰。
     - 懲罰項：$Exposure = Cost \cdot \Delta Q \cdot \frac{Vulnerability}{Support}$。
     - 這是一個非線性懲罰。若單位陷入敵陣（$Vulnerability$ 極高）且無隊友（$Support \rightarrow 0$），評分將被大幅扣除，導致 $Value < 0$ 而放棄攻擊。
  3. **殘血優化 (Low-HP Bias)**：對目標已損失的血量給予微小的加分，迫使 AI 在期望值相近的多個目標中，優先選擇收割殘血單位。
  4. **理智檢查 (Sanity Check)**：
     - 若 `vulnerability > 50` 且 $P_{kill} < 0.02$，強制作廢該決策（回傳 $-1.0$）。
     - **例外條件 (困獸之鬥)**：若單位已經被完全包圍 (`is_surrounded`) 且無隊友支援，則忽略理智檢查，強制執行攻擊以最大化死前輸出。
  5. **領袖威脅乘數**：若該次攻擊能威脅到敵方領袖，最終 $Value$ 乘以 $5.0$，使其成為絕對優先的決策。
