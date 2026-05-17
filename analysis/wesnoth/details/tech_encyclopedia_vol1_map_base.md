# Wesnoth 技術全典：AI 與地圖原始碼全函數解剖 (第一卷：地圖基礎層)

本卷詳盡解構 `src/map/` 目錄下所有函數的底層實作。

---

## 1. 座標系統核心：`location.hpp` / `location.cpp`

`map_location` 是 Wesnoth 引擎中最重要的基礎結構，負責處理六角格幾何。

### 1.1 `map_location` 構造函數系列
- **`map_location()`**: 預設構造函數，將坐標初始化為 $(-1000, -1000)$，代表無效或空位置。
- **`map_location(int x, int y)`**: 標準構造函數，直接賦值內部整數。
- **`map_location(int x, int y, wml_loc)`**: WML 座標適配器。由於 WML 使用從 1 開始的座標，而 C++ 從 0 開始，此函數自動執行 `x-1, y-1` 的修正。
- **`map_location(const config& cfg, ...)`**: 從 WML `config` 對象中解析坐標。

### 1.2 幾何與方向操作
- **`all_directions()`**: 靜態函數。返回包含六角格 6 個基本方向的 `std::vector`。
- **`rotate_direction(direction d, int steps)`**: 
  - **工程實現**：透過 $(d + steps) \bmod 6$ 計算旋轉後的方向。
  - **偏置校正**：針對負數 `steps` 進行了 `steps * -5` 的線性偏置，避開 C++ 負數求餘的非預期行為，確保方向旋轉永遠正確。
- **`get_opposite_direction(direction d)`**: 調用 `rotate_direction` 旋轉 3 步（180度），精確取得反向坐標方向。
- **`parse_direction(const std::string& str)`**: 詞法解析器。支援 WML 字串（如 `"n"`, `"se"`, `"-n"` 代表南）轉換為列舉值。支援括號嵌套解析。
- **`get_direction(direction dir, unsigned int n)`**: 座標位移函數。計算沿著方向 `dir` 移動 `n` 格後的目標座標。考量了六角格「偶數列與奇數列 Y 軸錯位」的拓撲特性。

### 1.3 空間算術 (Vector Arithmetic)
Wesnoth 將六角格坐標空間定義為一個「阿貝爾群 (Abelian Group)」。
- **`vector_negation()`**: 反向向量計算。在奇數 X 座標時需對 Y 軸進行額外偏移補償。
- **`vector_sum_assign(const map_location& a)`**: 座標加法。
  - **核心邏輯**：`y += ((x & 1) && (a.x & 1))`。這行代碼精確處理了兩個錯位座標疊加時的幾何跳變。
- **`to_cubic()` / `from_cubic()`**: 
  - **座標轉換**：將標準座標轉換為「立方座標系 (Cubic Coordinates)」。
  - **數學原理**：透過 $q, r, s$ 三軸坐標（滿足 $q+r+s=0$），將複雜的六角格位移與旋轉簡化為簡單的向量線性運算。

### 1.4 空間查詢與拓撲
- **`valid(...)`**: 邊界檢查重載系列。檢查座標是否位於指定 $W \times H$ 矩陣或含 $Border$ 的緩衝區內。
- **`get_ring(int min, int max)`**: 空間環形採樣。返回所有距離當前座標 $D \in [min, max]$ 的座標集合。
- **`rotate_right_around_center(const map_location& center, int k)`**: 空間旋轉。以 `center` 為原點，將座標順時針旋轉 $k \times 60$ 度。
- **`tiles_adjacent(a, b)`**: 鄰接判定。檢查兩座標之間的拓撲距離是否恰好等於 1。

---

## 2. 地圖異常處理：`exception.hpp`

- **`incorrect_map_format_error(msg)`**: 異常類別。當 `gamemap` 解析非法 WML 地圖字串時拋出，用於觸發上層加載器的錯誤處理管線。

---
*第一卷解析完畢，已涵蓋 `map/location` 系列所有函數。下卷將進入 `map/map.hpp` 矩陣存儲與地形轉換模組。*
*最後更新: 2026-05-17*
