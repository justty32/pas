# Wesnoth 核心技術大解構：AI 決策引擎與戰鬥數學模型

本文件深入探討 Wesnoth AI 系統的底層實作，重點放在 RCA 任務排程框架以及基於機率分佈的戰鬥模擬評估。原始碼主要位於 `src/ai/default/` 目錄。

## 1. RCA 任務排程器 (Recursive Candidate Action)

AI 核心採用競爭性評分系統，將複雜的戰略拆解為獨立的行為候選者（Candidate Actions）。

### 1.1 執行流程
1.  **Candidate Action (CA) 收集**: 收集如：招募 (Recruit)、進攻 (Attack)、佔領 (Move to Targets) 等候選行動。
2.  **Evaluate 階段**: 每個 CA 根據當前局勢計算實數分數 $S$。
3.  **排序與執行**: 選擇 $S > 0$ 且分數最高的行動執行。執行後遊戲狀態改變，**遞歸觸發**下一輪全局重新評估。

---

## 2. 戰鬥評估：馬可夫機率分布模擬 (Combat Probability Distribution)

在發起攻擊前，AI 必須計算確切的機率期望值，而非單純比較血量。

### 2.1 數學評分公式
評分函數定義為：
$$ \text{Score} = (P_{kill} \cdot V_{target}) - (E[Loss] \cdot (1 - \alpha)) - \beta \cdot \text{Exposure} $$

- $P_{kill}$: 擊殺目標的精確機率。
- $V_{target}$: 目標戰略價值（基礎成本 + 經驗折算）。
- $\alpha \in [0, 1]$: **好戰度 (Aggression)**。
- $\beta$: **謹慎係數 (Caution)**。
- **Exposure (風險敞口)**: 計算單位在攻擊後，於該地形所承受的反擊風險。

### 2.2 戰鬥模擬虛擬碼 (Algorithm: Monte-Carlo Combat Analysis)
```pascal
Algorithm Analyze_Attack(Attacker, Target, AI_Context):
    // 1. 執行戰鬥模擬，產生 HP 機率分佈矩陣
    Sim ← Simulate_Battle(Attacker, Target)
    P_Kill ← Sim.Defender_HP_Distribution[0] // 目標 HP 為 0 的機率
    P_Die ← Sim.Attacker_HP_Distribution[0]  // 自身 HP 為 0 的機率
    
    // 2. 計算單位戰略價值 (包含經驗值加成)
    Unit_Value ← Attacker.Cost + (Attacker.XP / Attacker.Max_XP) * Attacker.Cost
    Expected_Loss ← P_Die * Unit_Value
    
    // 3. 升級誘因 (Advancement Reward)
    If Attacker_Will_Advance(Sim):
        // 若能升級，將帶來負損失（即收益）
        Expected_Loss ← Expected_Loss - (Unit_Value * P_Kill)
        
    // 4. 基礎價值計算
    Base_Value ← (P_Kill * Target.Strategic_Value) - (Expected_Loss * (1 - Aggression))
    
    // 5. 地形曝露風險 (Exposure Analysis)
    Terrain_Quality ← Attacker.Defense(Attack_Pos)
    Alt_Quality ← AI.Get_Best_Defensive_Pos(Attacker)
    
    If Terrain_Quality < Alt_Quality:
        // 放棄優良防禦陣地帶來的風險懲罰
        Risk ← Caution * Unit_Value * (Alt_Quality - Terrain_Quality)
        Base_Value ← Base_Value - Risk * (1 - Aggression)
    
    // 6. 領袖威脅加成
    If Target.Is_Leader: Base_Value ← Base_Value * 5.0
    
    Return Base_Value
```

---

## 3. 招募決策反制模型 (Recruitment Counter-Modeling)

AI 的招募邏輯（`recruitment.cpp`）是一個結合經濟預測與兵種相剋的模型。

- **經濟預測 (Economic Forecasting)**:
  AI 模擬未來 5 回合的財政狀況：$Gold_{future} = Gold_{now} + (Villages \cdot 2 - Upkeep) \cdot 5$。若 $Gold_{future} < 0$，AI 會切換至 `SAVE_GOLD` 狀態，拒絕招募低評分單位。
- **地形與敵軍感知**:
  掃描前線地形，並統計敵軍已招募的兵種與傷害類型（如 Pierce, Blade, Impact）。AI 會從自己的招募清單中，動態提升對這些敵軍具備抗性或高命中率單位的權重分數。
