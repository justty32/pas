# 建立 C++ 六角格工具庫：遍歷與演算法篇

這份教學將教你如何基於軸向座標 (Axial Coordinates) 建立一個功能強大的 C++ 工具庫，實作「環形擴張遍歷」與「直線路徑遍歷」等遊戲開發中極其常用的便捷操作。

---

## 1. 基礎工具擴充：座標運算

要進行遍歷，我們需要先為 `HexCoord` 加上基礎的數學運算。

```cpp
#include <vector>
#include <cmath>
#include <algorithm>

struct HexCoord {
    int q, r;

    // 向量加法
    HexCoord operator+(const HexCoord& other) const { return {q + other.q, r + other.r}; }
    // 向量乘法 (縮放)
    HexCoord operator*(int scalar) const { return {q * scalar, r * scalar}; }
    
    bool operator==(const HexCoord& other) const { return q == other.q && r == other.r; }

    // 第三軸 s 座標 (s = -q - r)
    int s() const { return -q - r; }
};

// 六個標準方向的偏移量 (從 2 點鐘方向順時針旋轉)
const HexCoord HEX_DIRECTIONS[6] = {
    {1, 0}, {1, -1}, {0, -1}, {-1, 0}, {-1, 1}, {0, 1}
};

HexCoord get_direction(int direction) {
    return HEX_DIRECTIONS[direction % 6];
}
```

---

## 2. 環形擴張遍歷 (Ring & Spiral Traversal)

在《文明》類遊戲中，獲取「城市三環內的格子」是最基礎的需求。

### 2.1 獲取特定半徑的一圈 (Ring)
演算法思路：從中心向某個方向移動 $N$ 步到達邊界，然後沿著六角形的六條邊各走 $N$ 步。

```cpp
std::vector<HexCoord> get_hex_ring(HexCoord center, int radius) {
    if (radius == 0) return {center};

    std::vector<HexCoord> results;
    // 1. 先走到環的起點 (例如沿著方向 4 走 radius 步)
    HexCoord cube = center + HEX_DIRECTIONS[4] * radius;

    // 2. 沿著 6 個方向遍歷
    for (int i = 0; i < 6; i++) {
        for (int j = 0; j < radius; j++) {
            results.push_back(cube);
            cube = cube + HEX_DIRECTIONS[i];
        }
    }
    return results;
}
```

### 2.2 獲取範圍內的所有格子 (Spiral/Range)
遍歷從半徑 0 到 $N$ 的所有環。

```cpp
std::vector<HexCoord> get_hex_spiral(HexCoord center, int max_radius) {
    std::vector<HexCoord> results;
    results.push_back(center); // 半徑 0
    for (int r = 1; r <= max_radius; r++) {
        auto ring = get_hex_ring(center, r);
        results.insert(results.end(), ring.begin(), ring.end());
    }
    return results;
}
```

---

## 3. 直線路徑遍歷 (Line Traversal)

直線遍歷通常用於「遠程單位攻擊範圍」或「視野檢查」。

### 演算法核心：線性插值與取整
六角格的直線不能簡單地對 $q, r$ 取整，必須轉換到三維空間 $(q, r, s)$ 進行插值，再使用特殊的 `hex_round` 演算法。

```cpp
// 六角格取整函數 (關鍵！)
HexCoord hex_round(double q, double r) {
    double s = -q - r;
    int rq = std::round(q);
    int rr = std::round(r);
    int rs = std::round(s);

    double q_diff = std::abs(rq - q);
    double r_diff = std::abs(rr - r);
    double s_diff = std::abs(rs - s);

    if (q_diff > r_diff && q_diff > s_diff) {
        rq = -rr - rs;
    } else if (r_diff > s_diff) {
        rr = -rq - rs;
    }
    return {rq, rr};
}

std::vector<HexCoord> get_hex_line(HexCoord start, HexCoord end) {
    int dist = hex_distance(start, end); // 需實作之前的距離函數
    std::vector<HexCoord> results;
    
    for (int i = 0; i <= dist; i++) {
        double t = (dist == 0) ? 0.0 : (double)i / dist;
        // 線性插值公式
        double q = start.q * (1.0 - t) + end.q * t;
        double r = start.r * (1.0 - t) + end.r * t;
        results.push_back(hex_round(q, r));
    }
    return results;
}
```

---

## 4. 實戰建議：便捷操作封裝

你可以將這些功能封裝進一個 `HexUtility` 類別，並與你的 `TileMap` 結合。

### 範例用法：遍歷範圍並執行邏輯
```cpp
// 獲取中心 3 環內的所有森林地塊
auto coords = HexUtility::get_hex_spiral(cityCenter, 3);
for (const auto& coord : coords) {
    Tile* t = map.getTile(coord.q, coord.r);
    if (t && t->terrain == Terrain::Forest) {
        // 執行你的邏輯...
    }
}
```

---

## 5. 教學總結

1.  **向外擴張**：利用 `get_hex_ring` 與 `get_hex_spiral`。注意六角形的邊際效應，$N$ 環的總格數公式為 $1 + 3N(N+1)$。
2.  **直線路徑**：必須使用 `hex_round` 處理浮點數取整，否則在格子邊界會出現抖動或跳格現象。
3.  **效能考量**：
    *   對於頻繁的範圍查詢，可以預計算 (Pre-calculate) 偏移量。
    *   如果地圖具有「世界循環 (World Wrap)」，在計算鄰居與遍歷時需額外加上模數運算 (Modulo)。
