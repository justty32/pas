# Wesnoth 核心技術大解構：地圖生成函數逐一解構 (Function-by-Function Anatomy)

本文件對 `src/generators/default_map_generator_job.cpp` 中的每一個函數進行極致深度的解析。本手冊旨在從原始碼層級解構 Wesnoth 隨機地圖生成的每一個齒輪，提供工業級的工程參考。

---

## 1. 構造函數 (Constructors)

### 1.1 `default_map_generator_job::default_map_generator_job()`
- **語義**: 預設構造函數。
- **內部行為**: 初始化隨機數生成器 `rng_`。若未提供種子，通常會回溯至系統時鐘或全域隨機池。
- **工程意義**: 確保地圖生成的起點具備隨機性，是所有非同步生成作業 (Job) 的基石。

### 1.2 `default_map_generator_job::default_map_generator_job(uint32_t seed)`
- **語義**: 帶種子的構造函數。
- **參數**: `seed` (32位無符號整數) - 用於確定性生成的隨機種子。
- **工程意義**: 這是 Wesnoth 支援「地圖種子回放」的核心。給定相同的種子，此作業產生的所有隨機序列（丘陵位置、河流走向、城堡位置）將完全一致，這對網路對戰中的地圖同步至關重要。

---

## 2. 高度圖生成：丘陵演算法 (Height Map Generation)

### 2.1 `generate_height_map` (多態重載)
這是 Wesnoth 地貌生成的數學核心。

#### **函數 A (具備島嶼偏移量)**
`height_map generate_height_map(width, height, iterations, hill_size, island_size, island_off_center)`
- **參數剖析**:
  - `iterations`: 疊加丘陵的次數。越高則地形越平滑，越低則越崎嶇。
  - `hill_size`: 丘陵半徑的最大上限。
  - `island_size`: 控制陸地凝聚力的核心參數。
  - `island_off_center`: 偏離中心的擾動量，防止地圖過於對稱。
- **核心算法流程**:
  1. 根據 `island_off_center` 計算邏輯中心點。
  2. 呼叫底層的高度圖生成引擎。

#### **函數 B (核心生成引擎)**
`height_map generate_height_map(width, height, iterations, hill_size, island_size, center_x, center_y)`
- **底層數學解構**:
  - 每個丘陵對點 $(x_2, y_2)$ 的貢獻 $H_{delta} = Radius - \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$。
  - **區域化優化**: 演算法並非遍歷全圖，而是計算丘陵的 **Bounding Box** ($[x_1-R, x_1+R] \times [y_1-R, y_1+R]$)，將複雜度從 $O(I \cdot W \cdot H)$ 降至 $O(I \cdot R^2)$，其中 $R \ll \sqrt{W^2+H^2}$。
- **正規化 (Normalization)**:
  - 遍歷最終數據查找 $H_{min}$ 與 $H_{max}$。
  - 將所有點映射至 $[0, 1000]$ 區間。
  - **數值穩定性**: 透過 `if(highest != 0)` 防止除以零。

---

## 3. 水文模擬：湖泊與河流 (Hydrology)

### 3.1 `generate_lake`
- **語義**: 基於機率衰減的遞歸湖泊生成。
- **參數**: `lake_fall_off` - 決定湖泊「擴散性」的衰減因子。
- **數學特性**: 湖泊大小遵循**幾何分佈**。每次擴散機率減半，這能產生自然的、不規則邊緣的圓形水域。
- **狀態管理**: 使用 `std::set<map_location>& locs_touched` 防止遞歸陷入死循環並記錄湖泊範圍。

### 3.2 `generate_river_internal` (遞歸核心)
- **語義**: 尋路式的河流生成。
- **關鍵邏輯**: 
  - **重力約束**: 河流傾向於流向高度較低的地方。
  - **侵蝕能力 (`river_uphill`)**: 允許河流克服微小的高度障礙（如切開山脊）。
  - **隨機性**: 在搜尋路徑時，對六個方向進行隨機洗牌 (`std::shuffle`)，確保河流曲折多變。
- **成功條件**: 只有當河流成功連接到預有的水體 (Sea/Lake) 或到達地圖邊界時，路徑才會正式寫入 `terrain` 矩陣。

---

## 4. 戰略設施配置 (Strategic Placement)

### 4.1 `rank_castle_location` (靜態輔助)
- **語義**: 城堡候選位置的品質評估函數。
- **權重因子分析**:
  - **距離約束**: 與現有城堡距離過近時回傳 0 (無效)。
  - **地形合法性**: 檢查城堡及其周圍 1 格是否全為可通行地形。
  - **邊界評分**: 傾向於讓城堡遠離極端邊緣，使用 `min(x_from_border, y_from_border)` 計算權重。
  - **空間密度**: 遍歷 $11 \times 11$ 區域計算地形豐饒度。
- **工程設計**: 使用 `highest_ranking` 參數進行早停 (Early Exit) 優化，減少無謂計算。

### 4.2 `place_village` (靜態輔助)
- **語義**: 戰略村莊的局部最優放置。
- **核心機制**: 在給定半徑內搜尋最合適的地形（如：丘陵上的村莊比平地更有價值）。
- **快取優化 (`tcode_list_cache`)**: 使用快取存儲地形的鄰接偏好規則（如村莊喜歡鄰近農田），大幅提升在數千次村莊試點中的計算效能。

---

## 5. 主生成流程 (Master Generation Workflow)

### 5.1 `default_generate_map`
這是整個作業的控制中樞。

#### **5.1.1 空間尺度縮放 (Contextual Context)**
- **設計哲學**: Wesnoth 會生成比目標地圖大 **9 倍** 的原始區域 (`width *= 3`, `height *= 3`)。
- **目的**: 提供邊界上下文。這讓河流能「從地圖外流進來」，避免邊緣地帶的地貌產生突兀的斷裂感。最終透過 `output_map` 裁剪出中間的 1/9 區塊。

#### **5.1.2 氣候模擬：溫度圖與地形轉換**
- **溫度圖生成**: 再次調用 `generate_height_map` 但參數不同，作為第二維度的標量場。
- **多維映射 (N-dimensional Mapping)**:
  - 遍歷所有格子，根據 (高度, 溫度) 對應 WML 中的 `[convert]` 標籤。
  - **優先權設計**: WML 規則按順序匹配，這允許開發者實現「寒冷的高山是冰川，炎熱的高山是火山」等複雜氣候邏輯。

#### **5.1.3 路徑路網：道路蜿蜒度演算法**
- **路徑成本計算 (`road_path_calculator`)**: 
  - 核心包含一個隨機噪音注入點。
  - **噪聲公式**: `int noise = random % (windiness_ * 137) / 137;`
  - **工程意圖**: `windiness_` 參數能控制道路偏離最短路徑的程度。這讓遊戲中的道路看起來更像人走出來的曲折小徑，而非完美的幾何直線。

---
*本手冊僅完成 `default_map_generator_job.cpp` 之解析。後續章節將對 AI 戰鬥核心 `attack.cpp` 執行相同等級之解剖。*
*最後更新: 2026-05-17*
