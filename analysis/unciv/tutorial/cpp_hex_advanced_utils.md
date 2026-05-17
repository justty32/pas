# C++ 六角格工具庫：進階與實用便捷功能

在開發《文明》這類複雜的策略遊戲時，除了基礎的擴張與直線遍歷，你還會頻繁遇到其他進階需求。以下為你整理了幾個非常實用的便捷功能與設計思路。

---

## 1. 地圖邊界循環 (World Wrapping)

地球是圓的，遊戲地圖通常也需要橫向相連（從地圖最右邊走出去會從最左邊出來）。這在六角格的軸向座標系中需要特別的換算。

### 實作思路：
如果你使用的是「矩形地圖的軸向座標」，循環的核心是針對 **行(Row)** 不變，但對 **列(Column)** 取模數 (Modulo)。

```cpp
// 假設你有一個輔助函數將 (q, r) 轉為 (col, row)
int get_col(HexCoord hex) { return hex.q + (hex.r >> 1); }
int get_row(HexCoord hex) { return hex.r; }
HexCoord from_col_row(int col, int row) { return {col - (row >> 1), row}; }

// 橫向循環 (Cylindrical Wrap)
HexCoord wrap_horizontal(HexCoord hex, int map_width) {
    int col = get_col(hex);
    int row = get_row(hex);
    
    // C++ 的 % 運算子對負數會產生負數，因此需要標準化
    int wrapped_col = (col % map_width + map_width) % map_width;
    
    return from_col_row(wrapped_col, row);
}
```

---

## 2. 邊緣與頂點定位 (Edges & Corners)

地塊的「面」用來放單位，但「河流 (Rivers)」與「國界線 (Borders)」是畫在**邊緣**上的；而「河流的交匯點」則是在**頂點**上。

### 實作思路：
不要為邊緣或頂點建立獨立的大陣列。每個六角形有 6 條邊，相鄰的六角形會共用邊。
**最佳實踐：每個地塊只負責管理其東南側的三條邊。**

```cpp
enum class EdgeDirection {
    BottomRight, Bottom, BottomLeft
};

struct EdgeID {
    HexCoord tile;
    EdgeDirection dir;
    
    bool operator==(const EdgeID& o) const {
        return tile == o.tile && dir == o.dir;
    }
};

// 查詢兩個相鄰地塊共享的邊界 ID
EdgeID get_shared_edge(HexCoord a, HexCoord b) {
    HexCoord diff = {b.q - a.q, b.r - a.r};
    // 判斷 b 在 a 的哪個方向，如果 b 在 a 的左上方，則該邊界其實是 b 的 BottomRight 邊界。
    // (這裡需要根據你的 HEX_DIRECTIONS 寫一個 switch 映射)
    // 這保證了無論從 a 問 b，還是從 b 問 a，返回的 EdgeID 都是唯一的。
}
```

---

## 3. 視野與遮擋 (Field of View / Line of Sight)

判斷遠程單位能否攻擊，或是探索迷霧時，需要檢查直線上是否有高山或森林遮擋。

### 實作思路：
結合上一篇教學的 `get_hex_line`，我們可以實作一個 `has_line_of_sight` 函數。

```cpp
bool has_line_of_sight(HexCoord start, HexCoord end, const TileMap& map) {
    auto line = get_hex_line(start, end);
    
    // 略過起點與終點，只檢查中途的格子
    for (size_t i = 1; i < line.size() - 1; i++) {
        Tile* t = map.getTile(line[i].q, line[i].r);
        if (!t) continue;
        
        // 假設山脈會阻擋視野
        if (t->baseTerrain == TerrainType::Mountain) {
            return false;
        }
    }
    return true;
}
```

---

## 4. 區域交集與運算 (Area Operations)

有時候我們需要計算兩個 AOE（範圍效果）的重疊區域，或者找出「在城市 A 範圍內，但不在城市 B 範圍內」的格子。

### 實作思路：
如果你為 `HexCoord` 實作了 `<` 運算子（或是 Hash 函數），你就可以直接使用 C++ 的 `<algorithm>` 庫來做集合運算。

```cpp
#include <set>

// 為了放入 std::set，需要定義排序規則
bool operator<(const HexCoord& a, const HexCoord& b) {
    if (a.q != b.q) return a.q < b.q;
    return a.r < b.r;
}

// 計算交集 (例如兩個城市範圍的重疊處)
std::vector<HexCoord> get_intersection(const std::vector<HexCoord>& areaA, const std::vector<HexCoord>& areaB) {
    std::set<HexCoord> setA(areaA.begin(), areaA.end());
    std::set<HexCoord> setB(areaB.begin(), areaB.end());
    
    std::vector<HexCoord> intersection;
    std::set_intersection(setA.begin(), setA.end(),
                          setB.begin(), setB.end(),
                          std::back_inserter(intersection));
    return intersection;
}
```

---

## 5. 鄰居條件篩選 (Conditional Neighbors)

A* 尋路或擴張演算法最核心的操作就是「尋找合法的鄰居」。

### 實作思路：
寫一個高階函數，允許傳入 Lambda 表達式來過濾鄰居。

```cpp
#include <functional>

std::vector<HexCoord> get_valid_neighbors(HexCoord center, std::function<bool(HexCoord)> is_valid) {
    std::vector<HexCoord> valid_neighbors;
    for (int i = 0; i < 6; i++) {
        HexCoord neighbor = center + HEX_DIRECTIONS[i];
        if (is_valid(neighbor)) {
            valid_neighbors.push_back(neighbor);
        }
    }
    return valid_neighbors;
}

// 使用範例：找出所有可以行走的鄰居 (不是海洋且不是高山)
auto walkable = get_valid_neighbors(unit_pos, [&](HexCoord hex) {
    Tile* t = map.getTile(hex.q, hex.r);
    return t != nullptr && t->baseTerrain != TerrainType::Ocean && t->baseTerrain != TerrainType::Mountain;
});
```

---

## 總結

這些進階操作涵蓋了六角格策略遊戲中絕大多數的場景：
1.  **世界循環**：解決了長卷軸地圖的無縫移動。
2.  **邊界與頂點定址**：讓河流與國界渲染不再重疊衝突。
3.  **視線遮擋 (LOS)**：結合直線插值，輕鬆實作迷霧與射程計算。
4.  **集合運算**：強烈建議為 HexCoord 實作 `<` 和 `==`，讓你直接白嫖 C++ STL 的強大集合演算法。
5.  **條件篩選**：透過 Lambda 讓你的尋路程式碼乾淨俐落。