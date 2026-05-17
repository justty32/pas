# Wesnoth 技術解析工程手冊 - 第一卷：程序化地圖生成 (Procedural Map Generation)

本手冊針對 `src/generators/default_map_generator_job.cpp` 執行逐函數之工程化剖析，旨在解構其地貌合成的底層演算法。

---

## 1. 標量高度場合成函數：`generate_height_map`

此函數的核心任務是透過疊加多個幾何實體，構建一個代表海拔高度的二維整數矩陣。

### 1.1 矩陣初始化與空間分配
```cpp
height_map res(width, std::vector<int>(height,0));
```
**工程解析**：系統在記憶體中分配一個 $W \times H$ 的二維 `std::vector`。所有元素初始值設為 $0$。此矩陣將作為標量場（Scalar Field）的容器，存儲後續步驟產生的海拔數值。

### 1.2 迭代疊加過程 (Iterative Additive Process)
```cpp
for(std::size_t i = 0; i != iterations; ++i) { ... }
```
**工程解析**：高度圖的生成並非一次性計算，而是透過 $N$ 次隨機迭代。每一次迭代代表在地圖中加入一個特定的幾何擾動，利用疊加原理形成最終的自然地形。

### 1.3 空間約束與島嶼偏置 (Spatial Constraints)
```cpp
if(island_size != 0) {
    const std::size_t dist = std::size_t(std::sqrt(diffx*diffx + diffy*diffy));
    is_valley = dist > island_size;
}
```
**工程解析**：
- **島嶼形態學 (Island Morphology)**：系統透過歐幾里得距離公式計算採樣點與中心坐標的偏移。
- **極性反轉 (Polarity Inversion)**：當距離超過 `island_size` 時，布林變數 `is_valley` 被觸發。此時，演算法從「海拔增量模式」轉為「海拔減量模式」。在工程上，這是一種邊界侵蝕演算法，確保高度矩陣的邊緣數值趨近於 $0$，為後續的地形轉換提供「海平線」的空間基礎。

### 1.4 Bounding Box 效能最佳化
```cpp
const int min_x = x1 - radius > 0 ? x1 - radius : 0;
const int max_x = x1 + radius < res.size() ? x1 + radius : res.size();
```
**工程解析**：為了避免在每次迭代中對全圖 $W \times H$ 格子進行遍歷，系統計算了一個受半徑 $R$ 影響的局部區域（Bounding Box）。這將演算法的時間複雜度從 $O(I \cdot W \cdot H)$ 顯著降低至 $O(I \cdot R^2)$，在工業實踐中是處理大規模空間數據的必備優化。

### 1.5 幾何高度函數：半球體映射 (Hemispherical Distribution)
```cpp
const int hill_height = radius - static_cast<int>(std::sqrt(xdiff*xdiff + ydiff*ydiff));
```
**工程解析**：這是一個線性的距離衰減函數。高度增量 $H_{\Delta}$ 與中心點距離呈線性負相關。其產生的幾何形狀在三維空間中為一個圓錐體或半球體。
- **海拔賦值**：`res[x2][y2] += hill_height` 或 `res[x2][y2] -= hill_height`。這一步體現了「加法合成」的本質，複雜的地貌是成千上萬個簡單幾何體相互干涉的結果。

### 1.6 線性正規化 (Linear Normalization)
```cpp
res[x2][y2] -= lowest;
res[x2][y2] *= 1000;
if(highest != 0) res[x2][y2] /= highest;
```
**工程解析**：原始矩陣的數值範圍不確定，無法直接用於地形碼轉換。系統執行了**線性重新映射 (Linear Mapping)**。
1. **零基準校準**：減去全域最小值。
2. **量化縮放**：將剩餘範圍等比例放大。
3. **區間標準化**：除以極差（Range）。
**最終產出**：一個範圍固定在 $[0, 1000]$ 的整數矩陣。這在軟體工程中稱為「數據標準化」，讓後續的配置規則（如：海拔 > 800 定義為冰川）具備高度的確定性。
