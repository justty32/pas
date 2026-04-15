# GDExtension 教學：程序化生成 TileMap

本教學將介紹如何在 C++ 中透過 `TileMapLayer` 動態生成 2D 地圖。

## 1. 目標導向
- 如何在執行時清除並填充磁磚。
- 如何根據雜訊 (Noise) 生成隨機地形。
- 如何利用 Godot 4 的地形系統 (Terrains) 自動處理連接。

## 2. 前置知識
- 已建立 `TileSet` 資源並設定好 `Source ID` 與 `Atlas Coords`。
- 了解 `Vector2i` 座標系統。

## 3. 原始碼導航
- **圖層操作**: `scene/2d/tile_map_layer.h` (L200+: `set_cell`)
- **地形系統**: `scene/2d/tile_map_layer.h` (搜尋 `set_cells_terrain_connect`)

## 4. 實作步驟

### 步驟 A：基礎單格填充
在 C++ 中，您可以直接操作 `TileMapLayer`。

```cpp
void MyWorldGenerator::fill_solid_rect(TileMapLayer *p_layer, Rect2i p_rect, int p_source_id, Vector2i p_atlas_coords) {
    if (!p_layer) return;

    for (int x = p_rect.position.x; x < p_rect.get_end().x; x++) {
        for (int y = p_rect.position.y; y < p_rect.get_end().y; y++) {
            // 設定磁磚：(座標, 來源ID, 貼圖座標, 替換索引)
            p_layer->set_cell(Vector2i(x, y), p_source_id, p_atlas_coords);
        }
    }
}
```

### 步驟 B：基於 FastNoiseLite 的地形生成
雜訊常被用於生成自然的地圖邊界。

```cpp
void MyWorldGenerator::generate_noise_map(TileMapLayer *p_layer, Ref<FastNoiseLite> p_noise) {
    int width = 100;
    int height = 100;
    
    for (int x = 0; x < width; x++) {
        for (int y = 0; y < height; y++) {
            float val = p_noise->get_noise_2d(x, y);
            
            if (val > 0.2) {
                // 草地
                p_layer->set_cell(Vector2i(x, y), 0, Vector2i(0, 0));
            } else {
                // 水面
                p_layer->set_cell(Vector2i(x, y), 0, Vector2i(1, 0));
            }
        }
    }
}
```

### 步驟 C：利用地形系統自動連通 (Auto-tiling)
這是 Godot 4 的強大功能，C++ 也可以輕鬆呼叫。

```cpp
void MyWorldGenerator::generate_with_terrains(TileMapLayer *p_layer, TypedArray<Vector2i> p_cells) {
    // 參數：(儲存格陣列, 地形集合ID, 地形ID, 是否忽略空單格)
    // 這會自動根據 TileSet 中的 Terrain 規則選擇正確的磁磚外觀
    p_layer->set_cells_terrain_connect(p_cells, 0, 0, true);
}
```

## 5. 效能優化與進階技巧
1. **大量更新**：
    - `TileMapLayer` 在每次 `set_cell` 後可能觸發內部重繪。
    - 對於極大規模的生成，建議先在記憶體中準備 `TileMapPattern`，然後一次性貼上。
2. **清除資料**：呼叫 `p_layer->clear()` 可以快速清空整個圖層。
3. **多圖層處理**：您可以建立多個 `TileMapLayer` 分別處理「背景」、「裝飾」與「碰撞」。

## 6. 驗證方式
1. **編輯器執行**：在 `_ready` 中呼叫您的生成函數。
2. **座標檢查**：確保使用的 `source_id` 與 `atlas_coords` 在 `TileSet` 中確實存在，否則格位會顯示為空白。
