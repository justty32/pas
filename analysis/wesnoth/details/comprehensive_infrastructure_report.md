# Wesnoth 技術大普查：全維度地圖與 AI 決策引擎報告

本報告從「原始碼底層」出發，深入解構 Wesnoth 在地圖數據、路徑搜尋以及 AI 多面向決策系統的實作細節，提供最高保真的技術解讀。

---

## 第一部分：地圖引擎底層架構 (Map Infrastructure)

Wesnoth 的地圖不只是圖片，而是具備語義的高效數據結構。

### 1. 地形代碼與編譯機制 (`t_translation::terrain_code`)
- **高效存儲**: 地形不再以字符串存儲，而是編譯為 `uint32_t` 類型的 `terrain_code`。
- **地形層級**: 每個 `terrain_code` 實際上編碼了基礎地形（Base）與覆蓋地形（Overlay），這使得系統能快速判斷諸如「森林中的草地」等複合屬性。

### 2. `gamemap` 數據模型
- **緩衝區管理**: `gamemap` 使用 `t_translation::ter_map` 管理一個 2D 數組。
- **邊界保護 (Border Size)**: 地圖周圍預留了 1 格邊界（`default_border = 1`），用於地形渲染時的鄰接規則計算，防止越界訪問。
- **村莊索引**: `gamemap` 維護了一個專門的 `villages_` 向量，用於快速定位戰略資源，這直接支持了 AI 的佔領決策。

---

## 第二部分：路徑搜尋與空間幾何 (Pathfinding & Geometry)

Wesnoth 的路徑搜尋是其戰術深度核心，完美解決了六角格與控制區 (ZOC) 的交互。

### 1. A* 搜尋的精確啟發式函數 (`heuristic`)
為了讓路徑看起來自然且計算高效，啟發式函數採用了「曼哈頓距離」與「微量歐幾里得偏置」的結合：
$$H = distance\_between(src, dst) + \frac{\Delta X^2 + \Delta Y^2}{900,000,000}$$
- **目的**: 這種微小的偏置能讓 A* 在多條等代價路徑中優先選擇視覺上較直的那一條，而不影響演算法的優化性 (Admissibility)。

### 2. 控制區 (ZOC) 的數學處理
- **`enemy_zoc` 函數**: 遍歷鄰接的 6 個六角格，檢查是否有具備 `emits_zoc` 屬性的敵方單位。
- **路徑阻斷**: 在路徑搜尋時，若進入敵方 ZOC，移動成本會被設為剩餘移動力，強制終止當前回合移動。

### 3. 傳送機制 (Teleportation) 整合
- A* 搜尋器 (`a_star_search`) 整合了 `teleport_map`。在展開節點時，不僅考慮鄰接格，還會檢查所有可用的傳送出口，並動態調整啟發式值。

---

## 第三部分：AI 多面向決策系統 (AI Aspect System)

Wesnoth 的 AI 決策並非硬編碼，而是基於一個「組合模式 (Composite Pattern)」的參數化架構。

### 1. Aspect (面向) 系統架構
- **`typesafe_aspect<T>`**: 使用模板確保 AI 參數（如好戰度、謹慎度）的類型安全。
- **Facet (切面) 權重層次**: 每個 Aspect 可以有多個 Facet。AI 會根據當前環境（如：第幾回合、誰在領先）動態切換使用的 Facet。
- **Invalidation 機制**: 當遊戲狀態、晝夜或回合更換時，Aspect 會自動標記為 `invalid_`，觸發重新計算。

### 2. 公式引擎 (Formula Engine) 整合
- **`lua_aspect`**: 允許直接在 WML 中嵌入 Lua 或 Wesnoth Formula 語言來定義 AI 參數。
- **動態評分**: 例如，AI 的 `aggression` 可以是一個公式：`1.0 - (own_units / enemy_units)`。

---

## 第四部分：單位與地形的動態交互

- **防禦加成緩存**: 單位的防禦率 (`chance_to_hit`) 並非實時計算，而是由 `movetype` 根據地形代碼進行高度優化的緩存查找。
- **隱形與視野**: 視野計算涉及「戰爭迷霧 (Fog)」與「黑幕 (Shroud)」的雙重處理，AI 在決策時會根據 `viewing_team` 的可視區域過濾目標。

---
*本報告為 Wesnoth 地圖與 AI 系統的全維度解構。*
*最後更新: 2026-05-17*
