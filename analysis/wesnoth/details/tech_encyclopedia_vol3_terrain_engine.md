# Wesnoth 技術全典：AI 與地圖原始碼全函數解剖 (第三卷：地形渲染與規則引擎)

本卷解構 `src/terrain/builder.cpp` 及其相關標頭檔中定義的地形建構器類別之所有成員函數。這是 Wesnoth 視覺表現層的核心，負責將抽象的地形代碼轉化為具體的過渡圖像。

---

## 1. 地形快取管理：`terrain_builder::tile` 類別

### 1.1 緩存重構與清理
- **`rebuild_cache(const std::string& tod, logs* log)`**: 
  - **工程解析**：根據當前的「晝夜時間 (TOD)」重新計算該座標處應顯示的圖像列表。
  - **視覺一致性**：處理光影變體，確保地形色調與遊戲時間同步。
- **`clear()`**: 重置該格子的所有圖像緩存，通常在地圖動態編輯後觸發。

---

## 2. 規則解析與應用：`terrain_builder` 核心類別

### 2.1 引擎初始化與配置
- **`terrain_builder(...)`**: 
  - **構造函數**：綁定 `gamemap` 指標，並讀取 WML 中的地形規則定義（`terrain_graphics`）。
- **`set_terrain_rules_cfg(const game_config_view& cfg)`**: 動態更新全域地形規則庫。

### 2.2 規則旋轉與對稱性 (Symmetry & Rotations)
Wesnoth 使用「模板」定義地形規則，並透過數學變換自動生成對稱規則。
- **`rotate(terrain_constraint& ret, int angle)`**: 
  - **幾何坐標變換**：將地形約束坐標繞中心旋轉 $N \times 60$ 度。
- **`rotate_rule(building_rule& ret, int angle, ...)`**: 
  - **邏輯複製**：深拷貝一條現有規則，並將其應用範圍旋轉至指定角度。
- **`replace_rotate_tokens(...)`**: 
  - **符號替換**：在規則模板中搜索旋轉佔位符（如 `@R0`），並根據當前角度替換為正確的圖像路徑。
- **`add_rotated_rules(...)`**: 
  - **自動擴展**：給定一條 WML 規則模板，自動生成全部 6 個方向的對應規則。這大幅減少了 Mod 開發者的工作量。

### 2.3 地形合成演算法 (Terrain Synthesis)
- **`build_terrains()`**: 
  - **主管線**：遍歷全圖所有格子，對每一格掃描所有匹配的 `building_rule`。
- **`apply_rule(const building_rule& rule, const map_location& loc)`**: 
  - **模式匹配**：檢查坐標 `loc` 周圍的鄰居是否滿足規則定義的地形代碼約束。若滿足，則將規則指定的圖像圖層疊加至 `tile` 緩存中。
- **`rebuild_terrain(const map_location& loc)`**: 
  - **局部更新**：當單一座標地形改變時，僅重新計算該點及其鄰接區域（受規則半徑影響）的渲染緩存。

### 2.4 資源加載與效能
- **`load_images(building_rule& rule)`**: 
  - **延遲加載**：在規則匹配成功前不預載圖像。檢查硬碟上是否存在對應的地形貼圖。
- **`get_tile(const map_location& loc)`**: 
  - **邊界保護**：封裝了對 `tilemap` 矩陣的存取，處理越界保護並回傳邊界外的預設地形。

---
*第三卷解析完畢，已涵蓋地形渲染引擎所有關鍵函數。下卷將進入 `src/generators/` 目錄，剖析 Wesnoth 內建的所有地圖生成演算法。*
*最後更新: 2026-05-17*
