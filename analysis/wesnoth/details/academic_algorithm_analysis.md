# The Battle for Wesnoth 演算法與數學模型深度剖析 (Academic Algorithm Analysis)

本報告以學術級的嚴謹度，深入剖析 Wesnoth 核心系統中的三大關鍵演算法：**六邊形 A* 搜尋之偏置啟發式函數**、**加法丘陵地形生成模型**，以及 **AI 蒙地卡羅戰鬥評估系統**。透過虛擬碼 (Pseudocode) 與數學公式，揭示其底層設計的巧思。

---

## 1. 六邊形 A* 搜尋與偏置啟發式函數 (Biased Heuristic in Hexagonal A*)

在傳統的 A* 路徑搜尋中，啟發式函數 $h(n)$ 必須滿足 $h(n) \le d(n, t)$（即不大於實際最小代價）以確保找到最佳解。但在六角格地圖中，多條不同形狀的路徑往往具有**完全相同的移動代價**（例如鋸齒狀路徑與直線路徑）。為了提升玩家的視覺體驗，Wesnoth 實作了一種加入微小歐幾里得偏置的混合啟發式函數。

### 1.1 數學模型
定義兩個六角格座標 $S(x_1, y_1)$ 與 $D(x_2, y_2)$，考量到偶數列與奇數列的 Y 軸錯位（Hex imbrication），真實的投影幾何距離被定義為：

$$ \Delta x' = (x_1 - x_2) \times 0.75 $$
$$ \Delta y' = (y_1 - y_2) + \frac{(x_1 \bmod 2) - (x_2 \bmod 2)}{2} $$

歐幾里得距離平方：
$$ D_{euclid}^2 = \Delta x'^2 + \Delta y'^2 $$

最終的啟發式函數 $H(S, D)$ 為：
$$ H(S, D) = HexDistance(S, D) + \frac{D_{euclid}^2}{900,000,000} $$

### 1.2 演算法分析與虛擬碼
分母 $9 \times 10^8$ 被設計為極大值，確保偏置量遠小於最小移動代價（1 MP）。這打破了等價路徑的平局 (Tie-breaking)，迫使 A* 優先展開最接近幾何直線的節點。

```pascal
// Pseudocode: Hexagonal Biased Heuristic
Function Heuristic(src, dst):
    // 1. 計算六角格拓撲距離 (作為主要 Admissible H)
    base_h = HexDistance(src, dst)
    
    // 2. 計算考慮六角格錯位的投影坐標差
    xdiff = (src.x - dst.x) * 0.75
    parity_offset = ((src.x MOD 2) - (dst.x MOD 2)) * 0.5
    ydiff = (src.y - dst.y) + parity_offset
    
    // 3. 計算微小偏置 (Tie-breaker)
    // 最大地圖對角線平方約為 90,000，除以 900,000,000 確保其值恆小於 0.0001
    euclid_bias = (xdiff^2 + ydiff^2) / 900000000.0
    
    Return base_h + euclid_bias
End Function
```

---

## 2. 隨機地形生成：加法丘陵模型 (Additive Hill Terrain Generation)

Wesnoth 捨棄了常見的 Perlin Noise，採用基於粒子轟擊思想的「加法丘陵模型」。此演算法透過在二維陣列上疊加數千個幾何半球體，形成自然的高地與深谷。

### 2.1 丘陵生成方程式
給定地圖上一點 $P(x, y)$，對於第 $i$ 個中心點在 $C_i(x_i, y_i)$、半徑為 $R_i$ 的丘陵，其對點 $P$ 的高度貢獻 $\Delta h_i(P)$ 為：
$$ \Delta h_i(P) = \max\left(0, R_i - \sqrt{(x - x_i)^2 + (y - y_i)^2}\right) $$

若該丘陵被標記為「山谷（Valley）」（通常位於地圖邊緣，用於生成海洋），則貢獻為負值。

### 2.2 虛擬碼實作

```pascal
// Pseudocode: Additive Heightmap Generation
Function GenerateHeightMap(width, height, iterations, max_radius, island_size, center):
    heightmap = Array[width][height] initialized to 0
    
    For i = 1 to iterations:
        // 隨機決定丘陵中心點與半徑
        c_x = Random(0, width)
        c_y = Random(0, height)
        radius = Random(1, max_radius)
        
        // 判斷是否為邊緣山谷 (Island logic)
        dist_to_center = EuclideanDistance(c_x, c_y, center.x, center.y)
        is_valley = (dist_to_center > island_size)
        
        // 僅計算受影響的 Bounding Box 以提升效能
        min_x = max(0, c_x - radius), max_x = min(width, c_x + radius)
        min_y = max(0, c_y - radius), max_y = min(height, c_y + radius)
        
        For x from min_x to max_x:
            For y from min_y to max_y:
                distance = sqrt((x - c_x)^2 + (y - c_y)^2)
                hill_height = radius - distance
                
                If hill_height > 0:
                    If is_valley:
                        heightmap[x][y] = max(0, heightmap[x][y] - hill_height)
                    Else:
                        heightmap[x][y] = heightmap[x][y] + hill_height
                        
    Normalize(heightmap, 0, 1000)
    Return heightmap
End Function
```

---

## 3. AI 戰鬥決策：風險加權評估模型 (Risk-Weighted Combat Evaluation)

Wesnoth AI 判斷是否攻擊並非單純比較血量，而是執行深度的機率分佈運算（在 `attack_analysis::analyze` 實作），計算預期報酬與曝露風險。

### 3.1 數學評分模型
攻擊的基礎期望值 $E(V)$ 計算如下：
$$ E(V) = (P_{kill} \times V_{target}) - (E_{loss} \times (1 - Aggression)) $$

其中：
- $P_{kill}$: 在所有可能的戰鬥機率分支中，成功擊殺目標的機率總和。
- $V_{target}$: 目標單位的戰略價值（包含其經驗值的折算）。
- $E_{loss}$: 己方單位陣亡機率乘以其自身價值。
- $Aggression$: AI 的好戰度參數 $[0, 1]$。

**暴露風險 (Exposure Penalty)**:
若攻擊後所在的六角格防禦力差，AI 會扣除暴露懲罰：
$$ Penalty = Caution \times C_{unit} \times \Delta Q_{terrain} \times \left( \frac{Vulnerability}{Support + \epsilon} \right) $$
這確保 AI 不會為了一個低價值目標，將高價單位（$C_{unit}$）暴露在缺乏友軍支援（$Support$）的危險平地（$\Delta Q_{terrain} < 0$）中。

### 3.2 虛擬碼實作

```pascal
// Pseudocode: AI Attack Evaluation
Function EvaluateAttack(attacker, target, AI_Context):
    bc = SimulateBattle(attacker, target) // 產生所有 HP 機率分佈
    
    prob_killed = bc.defender_hp_dist[0]
    prob_died = bc.attacker_hp_dist[0]
    
    // 計算經驗值與升級獎勵
    unit_cost = attacker.cost + (attacker.xp / attacker.max_xp) * attacker.cost
    expected_losses = unit_cost * prob_died
    
    If Attacker_Will_Advance(bc):
        expected_losses = expected_losses - (unit_cost * prob_killed) // 升級為負損失
        
    // 基礎價值
    base_value = (prob_killed * target.value) - (expected_losses * (1 - AI_Context.Aggression))
    
    // 計算防禦陣地劣勢
    current_terrain_def = attacker.defense(attacker.current_loc)
    attack_terrain_def = attacker.defense(attack_loc)
    terrain_diff = current_terrain_def - attack_terrain_def
    
    If terrain_diff > 0: // 意味著我們放棄了優良防禦陣地
        exposure = AI_Context.Caution * unit_cost * terrain_diff * (EnemyThreat / Max(1, FriendlySupport))
        base_value = base_value - exposure * (1 - AI_Context.Aggression)
        
    Return base_value
End Function
```

---
*本報告提供了 Wesnoth 核心程式碼背後最精確的演算法與數學模型，展現了其在空間路徑、地貌生成及 AI 決策上的深度工程巧思。*
*最後更新: 2026-05-17*
