# Godot 4 TileMap 系統架構分析 - Level 2 & 3

## 1. 架構重構概覽
在 Godot 4.x 中，TileMap 系統經歷了徹底的重構。原本單一節點的邏輯被拆分為多個層次：

### 核心組件：
- **`TileMapLayer` (`scene/2d/tile_map_layer.h`)**：
    - 這是現在建議使用的基礎節點。每一層都是一個獨立的節點。
    - 負責儲存格位資料 (`CellData`)、處理渲染指令與物理生成。
- **`TileSet` (`scene/resources/2d/tile_set.h`)**：
    - 資源類別，定義了磁磚的屬性。
    - 包含 `TileSetSource` (通常是 `TileSetAtlasSource`)，管理貼圖區域。
    - 包含 **Terrain (地形)** 系統，取代了舊版的 Autotile。
- **`TileMapCell`**：
    - 一個 64 位元的 `union`，儲存 `source_id` (來自哪個 TileSetSource)、`atlas_coords` (貼圖座標) 與 `alternative_tile`。

## 2. 數據存儲與渲染
- **格位索引**：使用 `Vector2i` 作為座標索引。
- **Quadrant (象限) 系統**：為了優化渲染與物理，TileMap 將格位劃分為多個 Quadrant。
- **繪製流程**：`TileMapLayer` 根據 `CellData` 內的 `TileMapCell` 資訊，從 `TileSet` 檢索貼圖 UV，並提交給 `RenderingServer`。

## 3. 重要發現
- **Scene Tiles**：Godot 4 支援將特定格位替代為一個完整的 `PackedScene` 實例。
- **Runtime 修改**：`TileMapLayer` 的資料可以完全透過 C++ 在執行時動態修改，這為程序化生成提供了基礎。
- **效能**：`TileMapLayer` 比舊版 `TileMap` 更輕量，且更容易進行並行處理（因為不同層是不同節點）。

---
*檔案位置：`scene/2d/tile_map_layer.h`, `scene/resources/2d/tile_set.h`*
