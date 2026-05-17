# 如何在 C++ 中實作高效的六角格地圖資料結構

這份教學將引導你參考 Unciv 的設計理念，在 C++ 中實作一個高效、可擴展且現代化的六角格地圖系統。

---

## 1. 核心座標系統：軸向座標 (Axial Coordinates)

在六角格地圖中，**軸向座標 $(q, r)$** 是數學上最簡潔的選擇。
*   $q$：類似 $x$ 軸。
*   $r$：類似 $y$ 軸。
*   $s$：隱含的第三軸，$s = -q - r$。

### C++ 實作：
```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdint>

// 參考 Unciv 的 InlineHexCoord 理念，我們可以用一個 uint32_t 打包座標
struct HexCoord {
    int16_t q, r;

    // 將座標打包進 32 位元整數以利傳輸與存儲
    uint32_t pack() const {
        return (static_cast<uint32_t>(q) << 16) | (static_cast<uint32_t>(r) & 0xFFFF);
    }

    static HexCoord unpack(uint32_t packed) {
        return { static_cast<int16_t>(packed >> 16), static_cast<int16_t>(packed & 0xFFFF) };
    }

    bool operator==(const HexCoord& other) const { return q == other.q && r == other.r; }
};

// 距離計算
int hex_distance(HexCoord a, HexCoord b) {
    return (std::abs(a.q - b.q) 
          + std::abs(a.q + a.r - b.q - b.r) 
          + std::abs(a.r - b.r)) / 2;
}
```

---

## 2. 地塊資料與效能優化 (Tile Data)

在 C++ 中，我們應該區分「靜態資料」與「動態資料」。為了效能，我們可以使用 **AoS (Array of Structures)** 或 **SoA (Structure of Arrays)**。

### C++ 實作：
```cpp
enum class TerrainType { Grassland, Plains, Desert, Ocean, Mountain };

struct Tile {
    HexCoord pos;
    TerrainType baseTerrain;
    float movementCost;
    bool hasRiver[3]; // 參考 Unciv：存儲特定方向的河流狀態
    
    // 指向單位或城市的指標（動態資料）
    int unitID = -1; 
};
```

---

## 3. 地圖容器：二維存取與線性序列化

參考 Unciv 的 `tileList` (序列化) 與 `tileMatrix` (存取)，我們在 C++ 中可以使用 `std::vector` 來管理。

### C++ 實作：
```cpp
class TileMap {
private:
    int width, height;
    std::vector<Tile> tiles; // 線性存儲，利於快取與序列化
    std::vector<std::vector<Tile*>> grid; // 二維存取陣列

public:
    TileMap(int w, int h) : width(w), height(h) {
        tiles.reserve(w * h);
        grid.resize(h, std::vector<Tile*>(w, nullptr));

        // 初始化座標
        for (int r = 0; r < h; ++r) {
            for (int q = 0; q < w; ++q) {
                Tile t;
                t.pos = { (int16_t)q, (int16_t)r };
                t.baseTerrain = TerrainType::Plains;
                tiles.push_back(t);
            }
        }

        // 建立快取指標矩陣
        for (int i = 0; i < tiles.size(); ++i) {
            grid[tiles[i].pos.r][tiles[i].pos.q] = &tiles[i];
        }
    }

    Tile* getTile(int q, int r) {
        if (q < 0 || r < 0 || q >= width || r >= height) return nullptr;
        return grid[r][q];
    }
};
```

---

## 4. 教學：如何重寫類似的系統

如果你要用 C++ 重寫，請遵循以下步驟：

### 第一步：定義座標數學
不要重複發明輪子。六角格座標的數學非常成熟。推薦使用 **Axial (q, r)**。
*   **關鍵點**：實作 `getNeighbors(q, r)` 函數。
*   **提示**：在六角格中，鄰居偏移量是固定的：`(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)`。

### 第二步：記憶體佈局優化
C++ 的優勢在於對記憶體的精確控制。
*   **Unciv 做法**：用 `ArrayList` 存所有 Tile，用二維陣列存指標。
*   **你的做法**：使用一個連續的 `std::vector<Tile>`。連續的記憶體對 CPU 快取極度友好，這在進行 Pathfinding (A*) 時會快上數倍。

### 第三步：河流處理
不要在地塊中心畫河流，要在地塊的「邊緣」處理。
*   **建議**：每個 Tile 只負責定義它「下方」、「右下方」、「左下方」的三條邊。這樣可以保證每條邊只被定義一次，不會發生衝突。

---

## 5. 完整範例 (現代 C++ 20)

```cpp
#include <iostream>
#include <vector>
#include <optional>

struct Hex {
    int q, r;
    // 鄰居方向偏移
    static inline const Hex directions[6] = {
        {1, 0}, {1, -1}, {0, -1}, {-1, 0}, {-1, 1}, {0, 1}
    };
};

struct MapTile {
    Hex coord;
    std::string terrainName;
    int food = 0;
};

class HexMap {
public:
    HexMap(int radius) : _radius(radius) {
        // 分配六角形範圍內的空間
        for (int q = -radius; q <= radius; q++) {
            for (int r = std::max(-radius, -q - radius); r <= std::min(radius, -q + radius); r++) {
                _tiles.push_back({{q, r}, "Grassland", 2});
            }
        }
    }

    const MapTile* getTile(int q, int r) const {
        for (const auto& tile : _tiles) {
            if (tile.coord.q == q && tile.coord.r == r) return &tile;
        }
        return nullptr;
    }

private:
    int _radius;
    std::vector<MapTile> _tiles;
};

int main() {
    HexMap gameMap(10);
    auto t = gameMap.getTile(0, 0);
    if (t) std::cout << "Center tile is " << t->terrainName << std::endl;
    return 0;
}
```

---

## 6. 進階建議：使用模板與 ECS
如果你的地圖非常大（10萬格以上）：
1.  **使用 ECS (Entity Component System)**：將地形資料 (靜態) 與 單位資料 (動態) 分開。
2.  **空間分割**：使用 **Quadtree** 或 **Hex-based Chunks** 來優化渲染裁剪。
3.  **SIMD 優化**：利用 C++ 的底層能力，在計算視野 (FOV) 時使用 SIMD 指令集。
