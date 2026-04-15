# 模塊分析：02_base_assets_simulation (資源與模擬基礎層)

## 1. 資源系統 (Assets)
`StarAssets.hpp` 實現了高度動態的數據驅動框架。
- **JSON Patching：** 支持 RFC 6902 標準，允許 Mod 通過 `add`, `remove`, `replace`, `move`, `copy`, `test` 指令修改原始數據。
- **多層級加載：** 支持從目錄、壓縮包 (`.pak`) 以及內存中讀取資源。
- **圖像處理指令 (Directives)：** 
  - 支持在路徑後附加參數 (如 `image.png?hflip?replace;ff0000=00ff00`)。
  - 這些指令在加載時實時處理，不修改原始文件。

## 2. 流體模擬 (CellularLiquid)
`StarCellularLiquid.hpp` 定義了基於壓力模型的元胞自動機模擬。
- **壓力模型：** 液體具有 `level` (水位) 和 `pressure` (壓力) 屬性。
- **流向計算：** 
  - 優先考慮重力流向（向下）。
  - 若下方已滿，則根據壓力差向兩側擴散。
  - 支持壓力向上溢出（噴泉效果）。
- **交互機制：** 通過 `liquidInteraction` 支持不同液體接觸時的化學反應（如水與岩漿生成岩石）。

## 3. 世界幾何 (WorldGeometry)
`StarWorldGeometry.hpp` 處理 Starbound 獨特的星球幾何特性。
- **環面模型 (Wrapping)：** 世界在地圖邊界處是連通的（左右循環）。
- **距離計算：** 所有距離計算（`diff`, `distance`, `rect`）都必須考慮 Wrapping，防止在邊界處發生錯誤的物理判定。
