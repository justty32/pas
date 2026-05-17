# C++ 六角格地圖：形狀生成與拼接教學

這份教學將教你如何使用軸向座標 (Axial Coordinates) 生成不同形狀的遊戲地圖，包括常見的「正方形 (矩形)」與「大六邊形」，並解釋不同的旋轉朝向。

---

## 1. 地圖朝向：尖頂 (Pointy Top) vs 平頂 (Flat Top)

在實作形狀前，必須先決定格子的旋轉方式。
*   **尖頂 (Pointy Top)**：Unciv 使用的方式。頂角向上，鄰居分布在 2, 4, 6, 8, 10, 12 點鐘方向。
*   **平頂 (Flat Top)**：邊緣向上，鄰居分布在 1, 3, 5, 7, 9, 11 點鐘方向。

**本教學統一使用 Unciv 的「尖頂」朝向。**

---

## 2. 生成正方形 (矩形) 地圖

要在六角格系統中生成矩形地圖，最簡單的方式是先定義「行 (Row)」與「列 (Column)」，然後轉換為軸向座標 $(q, r)$。

### 核心演算法：Offset 到 Axial 轉換
由於六角格的每一行會交錯（Odd/Even Shifting），我們需要處理這個偏移量。

```cpp
#include <vector>

struct HexCoord { int q, r; };

// 針對尖頂 (Pointy Top) 的矩形生成
// 使用 Odd-R 偏移系統 (單數行向右偏移)
std::vector<HexCoord> generate_rectangular_map(int width, int height) {
    std::vector<HexCoord> map;
    for (int r = 0; r < height; r++) {
        // 計算這一行的起始偏移
        int r_offset = r >> 1; // 相當於 floor(r/2)
        for (int q = -r_offset; q < width - r_offset; q++) {
            map.push_back({q, r});
        }
    }
    return map;
}

// 另一種更直觀的寫法 (參考 Unciv HexMath.kt)
HexCoord from_col_row(int col, int row) {
    // 透過 row 與 col 計算軸向座標
    int q = col - (row - (row & 1)) / 2;
    int r = row;
    return {q, r};
}
```

---

## 3. 生成大六邊形地圖 (Hexagonal Shape)

這是《文明》類遊戲最經典的地圖形狀，具有完美的對稱性。

### 核心演算法：三軸約束
一個半徑為 $N$ 的六邊形，其地塊必須滿足：$|q| \le N, |r| \le N, |s| \le N$。

```cpp
#include <algorithm>

std::vector<HexCoord> generate_hexagonal_map(int radius) {
    std::vector<HexCoord> map;
    for (int q = -radius; q <= radius; q++) {
        // 根據 q 限制 r 的範圍，確保 s (-q-r) 也在範圍內
        int r1 = std::max(-radius, -q - radius);
        int r2 = std::min(radius, -q + radius);
        for (int r = r1; r <= r2; r++) {
            map.push_back({q, r});
        }
    }
    return map;
}
```

---

## 4. 地圖旋轉與拼接 (0度 vs 90度)

「旋轉」在地圖生成中通常指的是座標系的重新映射。

### 4.1 旋轉 60 度 (六角格的自然旋轉)
如果你想把地圖旋轉 60 度，只需對座標進行置換：
$(q, r, s) \rightarrow (-r, -s, -q)$

### 4.2 處理「尖頂」與「平頂」的拼接
如果你希望地圖是 90 度轉向的（例如從 Unciv 的尖頂換成平頂）：
*   **軸向座標公式不變**，但你的**渲染邏輯**需要改變（$X, Y$ 座標的計算公式會對調 $\sin$ 與 $\cos$）。
*   **拼接邏輯**：如果你有多塊小地圖（Chunks）要拼成大模型，建議統一使用「中心偏移量」。
    `Global_Hex = Chunk_Offset + Local_Hex`

---

## 5. 實戰建議：地圖形狀選擇器

你可以實作一個簡單的工廠類別：

```cpp
class MapFactory {
public:
    enum class Shape { Rectangle, Hexagon };

    static std::vector<HexCoord> create(Shape shape, int size1, int size2 = 0) {
        if (shape == Shape::Hexagon) 
            return generate_hexagonal_map(size1);
        else 
            return generate_rectangular_map(size1, size2);
    }
};
```

---

## 6. 教學總結

1.  **正方形地圖**：本質上是帶有「行偏移」的軸向座標集合。使用 `(col, row)` 轉換法最符合人類直覺。
2.  **大六邊形地圖**：利用 `q + r + s = 0` 的對稱性，最適合做為對戰地圖，因為中心點到各邊的距離相等。
3.  **拼接技巧**：永遠記住，六角格是**軸向對齊**的。只要你的 $(q, r)$ 運算正確，不論什麼形狀都能無縫拼接。
