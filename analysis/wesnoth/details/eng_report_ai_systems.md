# Wesnoth 技術解析工程手冊 - 第二卷：AI 決策與戰鬥模型 (AI Combat & Strategy)

本手冊深入剖析 `src/ai/default/attack.cpp` 與 `src/ai/default/recruitment.cpp`。解構 Wesnoth AI 如何利用機率論與動態權重模型執行最優行動選擇。

---

## 1. 戰鬥評估函數：`attack_analysis::rating`

AI 的攻擊決策並非隨機，而是基於一個最大化「價值期望值」的目標函數。

### 1.1 動態目標定價 (Dynamic Unit Valuation)
```cpp
target_value = cost + (static_cast<double>(defend_experience) / max_experience()) * cost;
```
**工程解析**：
- **資源折算**：單位價值不等於招募成本。AI 會將「累積的經驗值」視為已經投入的沉沒成本，並按比例轉化為黃金價值。
- **優先級權重**：這導致快要升級（Level-up）的單位在 AI 的目標清單中具有極高的「邊際價值」，觸發 AI 的集火行為。

### 1.2 目標函數：期望值模型 (Expectation Maximization)
```cpp
double value = chance_to_kill * target_value - avg_losses * (1.0 - aggression);
```
**工程解析**：
- **收益項**：擊殺機率 ($P_{kill}$) $\times$ 目標身價 ($V_{target}$)。
- **成本項**：預期自身損耗 ($E_{loss}$) $\times$ 好戰度補償係數。
- **好戰度 $\alpha$**：這是一個調節係數。當 $\alpha=1$ 時，AI 進入「零成本偏好」模式，忽略自身損失。這在領袖受到威脅時會被強制觸發，作為一種緊急防禦狀態。

### 1.3 風險敞口懲罰 (Exposure Penalty)
```cpp
const double exposure = exposure_mod * resources_used * (terrain_quality - alt_quality) * vulnerability / std::max(0.01, support);
```
**工程解析**：
這是 Wesnoth AI 能夠理解「防禦陣地」的數學基礎。
- **地形質量差值 ($\Delta Q$)**：比較當前位置與潛在最佳位置的防禦力。若為了攻擊而移動到防禦力較差的位置，則 $\Delta Q > 0$。
- **環境壓力係數**：`vulnerability / support`（敵軍密度 / 友軍支援度）。
- **邏輯推導**：當 AI 發現攻擊行為會導致單位暴露在大量敵軍面前（高 $V$），且自身所在的地形防禦力顯著下降（高 $\Delta Q$），則會產生一個極大的負向分值，抵消攻擊帶來的收益，最終導致 AI 放棄該行動。

---

## 2. 招募引擎：經濟預測與動態反制

### 2.1 財政流量預測：`get_estimated_income`
```cpp
income = (current_villages * village_income - current_upkeep) * turns;
```
**工程解析**：
- **動態平衡預測**：AI 不僅檢查當前餘額（`gold`），還會計算未來 $T$ 回合的現金流淨值。
- **負反饋機制**：若預測未來 5 回合的總收入為負，則 `state_` 切換至 `SAVE_GOLD`。這是一個預防性的破產保護機制，確保 AI 不會招募過多單位導致維持費耗盡所有積蓄。

### 2.2 兵種相剋矩陣：`do_combat_analysis`
**工程解析**：
AI 會執行一次 $N \times M$ 的全兵種模擬（$N$: 可招募單位, $M$: 敵方現有單位）。
- **核心演算法**：調用 `battle_context` 進行成對模擬。
- **權重注入**：模擬後的勝率評分會反饋到招募決策清單中。如果發現敵軍全是高抗性、重裝甲單位，對應的反制單位（如法師）的分數會被動態乘上一個放大係數，實現了代碼級別的兵種壓制邏輯。
