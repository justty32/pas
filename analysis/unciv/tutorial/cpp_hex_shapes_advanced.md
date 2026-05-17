# C++ 六角格地圖：進階幾何形狀與射線教學

這份教學將教你如何在六角格系統中生成「三角形」、「扇形 (Wedge)」以及「散射射線 (Scattered Rays)」。這些功能常用於法術範圍 (AOE)、單位視野錐以及特殊的技能特效。

---

## 1. 生成三角形地圖 (Triangular Shape)

在軸向座標系中，生成一個正三角形非常直觀，只需要限制兩個座標軸的範圍以及它們的和。

### 核心演算法：
對於一個邊長為 $N$ 的三角形，地塊必須滿足：$q \ge 0, r \ge 0, q + r < N$。

```cpp
#include <vector>

struct HexCoord { int q, r; };

std::vector<HexCoord> generate_triangular_map(int size) {
    std::vector<HexCoord> map;
    for (int q = 0; q < size; q++) {
        for (int r = 0; r < size - q; r++) {
            map.push_back({q, r});
        }
    }
    return map;
}
```
*註：這會生成一個「尖頭向上」且左下角為 $(0,0)$ 的三角形。*

---

## 2. 生成扇形/楔形區域 (Wedge/Fan)

扇形通常用於「噴火技能」或「偵查兵的視角範圍」。

### 實作思路：
扇形可以被視為「螺旋遍歷 (Spiral)」的一個子集。我們指定一個「起始方向」和一個「旋轉範圍」。

```cpp
// 獲取從方向 dir1 旋轉到 dir2，半徑為 radius 的扇形
std::vector<HexCoord> get_hex_wedge(HexCoord center, int radius, int start_dir, int end_dir) {
    std::vector<HexCoord> results;
    results.push_back(center); // 加入中心點

    for (int r = 1; r <= radius; r++) {
        // 取得該半徑的環起點 (例如沿著 start_dir 方向走 r 步)
        // 實際上更精確的做法是計算 start_dir 與 end_dir 之間的夾角
        for (int d = start_dir; d <= end_dir; d++) {
            // 沿著環的特定弧段遍歷
            // 這部分邏輯可以結合 get_hex_ring 的內部實作
        }
    }
    return results;
}

// 更簡單的實作方式：使用距離 + 方向夾角過濾
bool is_in_wedge(HexCoord origin, HexCoord target, int max_dist, int center_dir, int width) {
    if (hex_distance(origin, target) > max_dist) return false;
    
    // 計算 target 相對於 origin 的方向向量
    // 使用 atan2 轉換為角度，判斷是否在 [center_dir - width/2, center_dir + width/2] 之間
}
```

---

## 3. 散射射線 (Scattered Rays)

散射射線模擬從一點向外發散的多條直線，常用於「散射箭」或「爆炸衝擊波」。

### 實作思路：
利用之前教學中的 `get_hex_line`，對多個目標點進行投射。

```cpp
std::vector<std::vector<HexCoord>> get_scattered_rays(HexCoord origin, int radius, int num_rays) {
    std::vector<std::vector<HexCoord>> all_rays;
    
    // 獲取半徑為 radius 的最外環所有地塊
    auto outer_ring = get_hex_ring(origin, radius);
    
    // 根據 num_rays 步長從外環選取目標點
    int step = std::max(1, (int)outer_ring.size() / num_rays);
    for (int i = 0; i < outer_ring.size(); i += step) {
        all_rays.push_back(get_hex_line(origin, outer_ring[i]));
        if (all_rays.size() >= num_rays) break;
    }
    
    return all_rays;
}
```

---

## 4. 進階：帶寬度的直線 (Thick Lines)

有時候你需要的不是一條細線，而是一條「有寬度的射線」（如雷射炮）。

### 實作思路：
先計算一條直線，然後對直線上的每一個地塊取鄰居（或半徑為 1 的圓）。

```cpp
std::vector<HexCoord> get_thick_line(HexCoord start, HexCoord end, int width) {
    auto base_line = get_hex_line(start, end);
    std::set<HexCoord> thick_line_set;

    for (const auto& tile : base_line) {
        auto area = get_hex_spiral(tile, width);
        for (const auto& a : area) {
            thick_line_set.insert(a);
        }
    }
    return {thick_line_set.begin(), thick_line_set.end()};
}
```

---

## 5. 教學總結

1.  **三角形**：最簡單的形狀生成，依賴座標軸的線性不等式。
2.  **扇形**：常用於限制視角的偵查或技能，實作時建議結合「方向角」進行篩選。
3.  **散射射線**：是「直線遍歷」的批量應用，適合處理發散性的特效邏輯。
4.  **寬直線**：透過對直線地塊進行「向外擴張」操作，可以輕鬆實作具有打擊寬度的重型技能。

至此，你已經掌握了六角格地圖中**點、線、面、環、扇、楔**所有核心幾何形狀的 C++ 實作方法。
