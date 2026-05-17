# Wesnoth 核心技術大解構：地圖生成與水文模擬演算法

本文件深入探討 Wesnoth 核心引擎中，用於生成隨機地圖的程序化生成演算法（Procedural Generation Algorithms）。本節重點放在 `default_map_generator_job.cpp` 中的實作細節。

## 1. 標量高度場的幾何合成：丘陵加法演算法 (Hill-based Additive Synthesis)

Wesnoth 的地圖生成並非單純的雜訊（如 Perlin Noise）疊加，而是一套基於**標量場疊加 (Scalar Field Superposition)** 的多階段管線。

### 1.1 數學模型
令地圖為二維整數張量 $H \in \mathbb{R}^{W \times H}$。
生成過程為 $N$ 次迭代的隨機過程。在每次迭代 $i$ 中，採樣一個隨機元組 $(C_i, R_i, T_i)$，其中：
- $C_i = (x_i, y_i)$ 為中心座標。
- $R_i \in [1, R_{max}]$ 為球體半徑（丘陵大小）。
- $T_i \in \{1, -1\}$ 為極性（1 代表丘陵，-1 代表山谷）。

對於地圖上任一點 $P(x, y)$，其高度增量 $\Delta h$ 定義為半球體高度函數：
$$ \Delta h_i(P) = T_i \cdot \max\left(0, R_i - \sqrt{(x-x_i)^2 + (y-y_i)^2}\right) $$

### 1.2 邊界懲罰與島嶼偏置 (Island Morphology)
為了確保地圖邊緣多為水域（形成島嶼），引入了**向心勢能函數**。若 $dist(P, Center) > Island\_Size$，則 $T_i$ 強制設為 $-1$（生成山谷），形成天然的海平線。

### 1.3 虛擬碼實作 (Pseudocode)
```pascal
Algorithm Synthesis_Heightmap(Width, Height, Iterations, Radius_Max, Island_Mode):
    H_Map[Width][Height] ← 0
    Center ← (Width / 2, Height / 2)
    
    For i from 1 to Iterations:
        If Island_Mode:
            // 在中心區域隨機偏移
            Pos_X ← Center_X - Island_Size + Rand(0, Island_Size * 2)
            Pos_Y ← Center_Y - Island_Size + Rand(0, Island_Size * 2)
        Else:
            Pos_X ← Rand(0, Width), Pos_Y ← Rand(0, Height)
            
        R ← Rand(1, Radius_Max)
        Dist_To_Center ← Euclidean_Dist((Pos_X, Pos_Y), Center)
        
        // 判斷地形極性：邊緣傾向山谷，中心傾向高山
        Is_Valley ← (Island_Mode AND Dist_To_Center > Island_Size)
        
        // 優化：僅迭代 Bounding Box [Pos.x - R, Pos.x + R]
        X_Start ← max(0, Pos_X - R), X_End ← min(Width - 1, Pos_X + R)
        Y_Start ← max(0, Pos_Y - R), Y_End ← min(Height - 1, Pos_Y + R)
        
        For x from X_Start to X_End:
            For y from Y_Start to Y_End:
                D ← sqrt((x - Pos_X)^2 + (y - Pos_Y)^2)
                h_val ← max(0, R - D)
                If Is_Valley:
                    H_Map[x][y] ← max(0, H_Map[x][y] - h_val) // 侵蝕
                Else:
                    H_Map[x][y] ← H_Map[x][y] + h_val         // 堆積
                    
    // 正規化至 [0, 1000] 的整數區間
    Normalize_Tensor(H_Map, 0, 1000)
    Return H_Map
```

---

## 2. 動態水文系統：遞歸湖泊與侵蝕河流 (Hydrological Logic)

### 2.1 遞歸湖泊生成 (Stochastic Recursive Growth)
Wesnoth 的湖泊生成並非簡單的高度裁剪，而是基於**機率衰減的擴散模型**。

```pascal
Algorithm Generate_Lake(Map, x, y, Prob, Touched_Set):
    // 邊界與機率剪枝
    If (x, y) invalid OR Prob <= 0: Return
    If (x, y) in Touched_Set: Return
    
    Map[x][y] ← SHALLOW_WATER
    Touched_Set.Add((x, y))
    
    // 遞歸向四個正交/六個六角鄰接格擴散，機率減半 (Prob / 2)
    For each Dir in Directions:
        If Rand(0, 100) < Prob:
            Generate_Lake(Map, x + Dir.dx, y + Dir.dy, Prob / 2, Touched_Set)
```

### 2.2 高度梯度河流搜尋 (Gradient-based River Flow)
河流從高點起始，始終尋找 $\nabla H$（高度梯度）下降最快的方向，直到匯入海洋或出界。
- **侵蝕機制 (River Uphill)**：為了模擬河流穿過丘陵的切割作用，河流允許最大 $U$ 單位的「逆坡爬行」，這在實作中由 `river_uphill` 參數控制。演算法會採用深度優先搜尋 (DFS) 尋找第一條能夠合法抵達水域的路徑。
