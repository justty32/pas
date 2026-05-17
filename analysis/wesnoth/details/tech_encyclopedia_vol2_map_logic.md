# Wesnoth 技術全典：AI 與地圖原始碼全函數解剖 (第二卷：地圖管理層)

本卷解構 `src/map/map.hpp` 與 `map.cpp` 中定義的 `gamemap` 與 `gamemap_base` 類別之所有成員函數。

---

## 1. 地圖基礎容器：`gamemap_base` 類別

這是所有地圖物件的基類，負責矩陣存儲與邊界管理。

### 1.1 生命週期與核心存取
- **`gamemap_base(int w, int h, const terrain_code& t)`**: 
  - **工程解析**：初始化一個 $W \times H$ 的地形矩陣 `tiles_`。
  - **邊界處理**：自動將 $W, H$ 加上兩倍的 `default_border` (通常為 1)，為地形規則計算預留緩衝區。
- **`on_board(const map_location& loc)`**: 
  - **範圍檢查**：判斷坐標是否位於「有效遊戲區域」內（不含緩衝區）。
- **`on_board_with_border(const map_location& loc)`**: 
  - **擴張檢查**：判斷坐標是否位於包含緩衝區的總體矩陣內。

### 1.2 戰略座標管理 (Special Locations)
- **`set_starting_position(int side, const map_location& loc)`**: 
  - **雙向索引**：將「陣營編號」與「座標」進行關聯。這直接決定了 AI 招募領袖的初始位置。
- **`num_valid_starting_positions()`**: 統計當前地圖上註冊的起始點總數。
- **`is_special_location(const map_location& loc)`**: 
  - **反向查找**：給定座標，返回該處註冊的特殊標籤（如 "Keep", "Citadel"）。

### 1.3 地圖空間運算
- **`overlay(const gamemap_base& m, ...)`**: 
  - **地圖疊加演算法**：將另一張地圖 `m` 覆蓋到當前地圖的指定位置。
  - **規則映射**：支援 `overlay_rule`，允許自定義地形的合併邏輯（例如：在已有山上疊加森林）。

---

## 2. 遊戲邏輯地圖：`gamemap` 類別

繼承自 `gamemap_base`，整合了與遊戲規則（WML）相關的地形屬性判定。

### 2.1 地圖解析與序列化
- **`gamemap(std::string_view data)`**: 
  - **詞法加載**：解析 WML 格式的地圖字串。包含對舊版地圖標頭的相容性處理。
- **`read(std::string_view data, bool allow_invalid)`**: 
  - **解析引擎**：逐行掃描字串，將地形代碼（如 `Gg`, `Hh`）編譯為內部的 `terrain_code`。
- **`write()`**: 
  - **反序列化**：將內存中的 `terrain_code` 矩陣轉換回 WML 字串格式，用於存檔。

### 2.2 地形屬性檢索 (Terrain Semantics)
這些函數是 AI 與遊戲邏輯頻繁調用的核心介面：
- **`is_village(const map_location& loc)`**: 
  - **語義判定**：查詢該座標的地形是否具備「村莊」屬性。
- **`gives_healing(const map_location& loc)`**: 
  - **數值檢索**：返回該地形的治療量。AI 在 `analyze_attack` 時會調用此函數來判斷撤退價值。
- **`is_castle(const map_location& loc)` / `is_keep(const map_location& loc)`**: 
  - **招募空間判定**：判斷是否能進行招募行為。
- **`get_terrain_info(const map_location& loc)`**: 
  - **物件解讀**：從全域地形數據庫中獲取對應坐標的完整 `terrain_type` 物件。

### 2.3 座標轉換與 WML 對接
- **`get_terrain_string(const map_location& loc)`**: 將座標處的地形編碼轉換為 WML 可讀字串。
- **`write_terrain(const map_location &loc, config& cfg)`**: 將單點地形資訊寫入 WML 配置節點。

---
*第二卷解析完畢，已涵蓋 `map/map` 系列所有函數。下卷將進入 `src/terrain/` 目錄，解構地形渲染規則與拼接演算法。*
*最後更新: 2026-05-17*
