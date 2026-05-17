# Wesnoth 核心技術大解構：A* 路徑搜尋與空間幾何

本文件專注於解析 `src/pathfind/astarsearch.cpp` 中實作的六角格 A* 路徑搜尋演算法，特別是其為了視覺體驗而設計的偏置啟發式函數。

## 1. 具備歐幾里得偏置的六角 A* (Biased Hexagonal A*)

在標準六角格地圖中，多條不同形狀的路徑（如鋸齒狀與直線）往往具有**完全相同的移動代價**。為了解決 A* 展開過多等價節點，並讓 AI/單位的移動路徑在視覺上更直，Wesnoth 加入了微量的歐幾里得偏置。

### 1.1 偏置啟發式函數模型
定義兩個六角格座標 $S(x_1, y_1)$ 與 $D(x_2, y_2)$。考慮偶奇列的 Y 軸錯位（Hex imbrication），真實的投影幾何距離定義為：
$$ \Delta x' = (x_1 - x_2) \times 0.75 $$
$$ \Delta y' = (y_1 - y_2) + \frac{(x_1 \bmod 2) - (x_2 \bmod 2)}{2} $$

歐幾里得距離平方：
$$ D_{euclid}^2 = \Delta x'^2 + \Delta y'^2 $$

最終的啟發式函數 $H(S, D)$ 為：
$$ H(S, D) = \text{HexDistance}(S, D) + \frac{D_{euclid}^2}{900,000,000} $$

### 1.2 演算法分析與虛擬碼
分母 $9 \times 10^8$ 是一個經過極端設計的常數。地圖對角線平方最大約為 90,000，除以 $9 \times 10^8$ 確保偏置量始終小於 0.0001。這既打破了等價路徑的平局 (Tie-breaking)，又確保不會超過最小移動代價（1 MP），從而維持 A* 的可容許性 (Admissibility)。

```pascal
Algorithm Biased_Heuristic(src, dst):
    // 1. 計算六角格拓撲距離 (作為主要 Admissible H)
    base_h ← HexDistance(src, dst)
    
    // 2. 計算考慮六角格錯位的投影坐標差
    xdiff ← (src.x - dst.x) * 0.75
    parity_offset ← ((src.x MOD 2) - (dst.x MOD 2)) * 0.5
    ydiff ← (src.y - dst.y) + parity_offset
    
    // 3. 計算微小偏置 (Tie-breaker)
    euclid_bias ← (xdiff^2 + ydiff^2) / 900000000.0
    
    Return base_h + euclid_bias
```

## 2. 控制區 (Zone of Control, ZOC) 的權重阻斷

ZOC 會強制單位停止。在 A* 的 `cost_calculator` 中，這被實作為一個非線性成本跳變：
- 若鄰接格包含敵軍且具備 `emits_zoc` 屬性，移動成本將被設為該單位剩餘的移動力 (Remaining Movement Points)。
- 這使得 A* 搜尋樹在遇到 ZOC 時，會將該路徑分支的權重瞬間拉滿，迫使演算法繞道尋找其他更安全的路線。
