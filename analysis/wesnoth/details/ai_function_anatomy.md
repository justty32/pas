# Wesnoth 核心技術大解構：AI 決策函數逐一解構 (Function-by-Function Anatomy)

本文件深入解構 `src/ai/default/attack.cpp` 與 `src/ai/default/recruitment.cpp` 中的關鍵函數。本手冊旨在揭示 Wesnoth AI 複雜決策背後的每一行邏輯與數學邏輯。

---

## 1. 戰鬥評估核心：`attack.cpp`

### 1.1 `attack_analysis::analyze`
- **語義**: 針對特定目標建立全方位的攻擊場景分析。
- **內部演算法流程**:
  1. **威脅評估**: 遍歷目標鄰接格，檢查是否威脅到己方領袖 (`leader_threat`)。
  2. **目標定價**: `target_value = cost + (XP/Max_XP) * cost`。這將單位的經驗值轉化為經濟價值，使 AI 傾向於優先擊殺快升級的敵軍。
  3. **位置預模擬**: 將攻擊者暫時「移動」到目標位置，構建 `battle_context`。
  4. **快取機制**: 使用 `unit_stats_cache` 加速重複的戰鬥計算（約 1000 倍加速）。
  5. **損失計算**: 結合「中毒」狀態對損失進行加權 (`cost * poisoned / 2`)，這反映了 AI 對長期損耗的預見性。
  6. **升級回報**: 若攻擊能觸發升級，則將損失標記為負值（即收益）。

### 1.2 `attack_analysis::rating` (評分決策器)
這是 AI 決定「是否執行該攻擊」的核心方程式。
- **數學模型**: 
  $Value = (P_{kill} \cdot V_{target}) - (AvgLoss \cdot (1 - Aggression))$
- **細節解構**:
  - **好戰度彈性**: 若目標威脅到領袖，`aggression` 被強制設為 1.0，忽略所有自身損失。
  - **暴露風險懲罰**: 
    - 計算 `terrain_quality` 與 `alternative_terrain_quality`（原本能待的最佳位置）。
    - $Exposure = Resources \cdot \Delta Quality \cdot \frac{Vulnerability}{Support}$。
    - **物理語義**: 若單位為了攻擊必須離開高山進入平地，且周圍敵軍威脅高於友軍支援，則評分會大幅下降。
  - **尾刀優先級**: `(target_starting_damage/3 + avg_damage_inflicted)` 確保 AI 傾向於完成對殘血目標的補刀。

---

## 2. 招募決策引擎：`recruitment.cpp`

### 2.1 `recruitment::evaluate` (RCA 評等)
- **語義**: 向 RCA 框架報告當前「招募行為」的優先級分數。
- **決策邏輯**:
  - **狀態檢查**: 若 `Gold < Cheapest_Unit`，回傳 0 分。
  - **緊急模式**: 若領袖正受到威脅，回傳極高分（50+），強制中斷一切進攻行動轉向招募防禦。
  - **經濟冷卻**: 若處於 `SAVE_GOLD` 狀態，且當前回合非預定的招募回合，則回傳低分。

### 2.2 `recruitment::do_combat_analysis` (兵種相剋矩陣)
- **語義**: 計算「我方可招募單位」對抗「敵方場上單位」的勝率權重。
- **核心演算法**:
  1. 統計敵軍所有單位的類型分佈。
  2. 對於我方每一種可招募單位 $U_{own}$：
     - 模擬 $U_{own}$ 對抗所有敵方類型 $U_{enemy}$ 的戰鬥。
     - 使用 `battle_context::better_combat` 選擇最優武器。
     - $Score = \sum (P_{kill} \cdot V_{target} - E_{loss})$。
- **目的**: 實現自動化的兵種壓制（例如：敵方重裝甲多時，自動提升法師的招募優先級）。

### 2.3 `recruitment::update_important_hexes` (戰略坐標採樣)
- **語義**: 識別地圖上最關鍵的戰鬥點。
- **採樣邏輯**:
  - 統計所有敵方單位當前位置。
  - 統計所有村莊坐標。
  - **熱力圖權重**: 越靠近前線或戰略資源的格子，權重越高。
- **應用**: AI 招募單位的防禦評分將以這些「重要格子」的地形為基準。若前線全是森林，則優先招募精靈。

### 2.4 `recruitment::get_estimated_income` (經濟預測模型)
- **數學模型**: 
  $Income = Turns \cdot (Base + Villages \cdot 2 - Upkeep)$
- **工程意圖**: AI 不會只看現在有多少錢。它會預測未來 5 回合的財政狀況。若預測到未來會因為過度招募而陷入財政赤字（維持費過高），AI 會主動停止招募低評分單位。

### 2.5 `recruitment::do_similarity_penalty` (多樣性維護)
- **語義**: 對重複招募相同單位的行為進行懲罰。
- **邏輯**: 若 AI 已經擁有了大量某種單位，其招募評分會依據「邊際效用遞減」進行扣分。
- **目的**: 防止 AI 生成過於單一的兵團，增加陣容的韌性與戰術多樣性。

---

## 3. 空間幾何與移動：`pathfind.cpp`

### 3.1 `find_vacant_tile`
- **語義**: 在目標點附近搜尋最近的空位。
- **演算法**: 廣度優先搜尋 (BFS)。
- **邊界限制**: 
  - 搜索半徑上限為 50 格。
  - 整合了 `pass_check`，確保找到的空位是該單位「能進入」的地形。
  - 整合了 `shroud_check`，AI 不會將單位移動到其視野外的黑幕中（除非有特殊權重）。

### 3.2 `enemy_zoc`
- **語義**: 判斷坐標是否處於敵方控制區。
- **底層實作**: 
  - 直接查閱鄰接的六個坐標。
  - 核心條件：`unit->emits_zoc()` 為真且 side 是敵對。
  - **特殊性**: 忽略「隱形」的敵軍，除非該 side 具備看穿隱形的能力。

---
*本手冊完成了對 Wesnoth AI 核心決策函數的深度解剖。結合前一章的地圖生成分析，已構成一套完整的技術骨架解析。*
*最後更新: 2026-05-17*
