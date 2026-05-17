# Wesnoth 技術全典：六角格渲染與視覺表現層 (第十七卷)

本卷解構 `src/display.cpp` 與 `src/display_context.cpp`。所有的地圖數據、單位狀態與 AI 決策，最終都必須透過這個渲染管線 (Rendering Pipeline) 轉化為玩家螢幕上的像素。

---

## 1. 核心渲染器：`display` 類別 (`display.cpp`)

`display` 類別是 Wesnoth 的繪圖總管，基於 SDL2 實作。

### 1.1 座標轉換數學 (Hex-to-Pixel Mapping)
螢幕是矩形的像素陣列，但地圖是六角格。
- **幾何映射**：`display` 內部實作了一組極度頻繁呼叫的內聯函數，將 `map_location(q, r)` 轉換為螢幕上的 $(x, y)$ 像素坐標。
  - **數學特性**：這包含了針對六邊形交錯特性（奇數行/偶數行）的像素位移，以及考慮到目前攝影機縮放比例 (Zoom Level) 的矩陣乘法。

### 1.2 局部重繪與髒矩形優化 (Dirty Rectangles)
在 60 FPS 下每一幀都重繪整張地圖是不可能的。
- **`invalidate(loc)` 與 `invalidate_all()`**：
  - **工程解析**：當單位於某一格移動，或地圖某一格發生變化時，系統只會呼叫 `invalidate(loc)`。這會將該六角格的 Bounding Box 標記為「髒的 (Dirty)」。
  - **渲染循環**：在下一幀繪製時，GPU 僅會將這些被標記的局部矩形範圍重新上色，未變化的地圖區域則直接保留。這種「局部重繪」技術是 Wesnoth 能在舊電腦上流暢運行的效能關鍵。

### 1.3 渲染層級 (Z-Index Layers)
`display::draw()` 是主繪圖函數，它嚴格遵循多層次的畫家演算法 (Painter's Algorithm)：
1.  **底層地形 (Base Terrain)**：畫出水、平原。
2.  **覆蓋地形 (Overlay Terrain)**：畫出樹木、山峰、村莊。
3.  **網格線 (Hex Grid)**：依玩家設定決定是否繪製。
4.  **腳印與移動軌跡**：繪製尋路系統算出的移動箭頭。
5.  **光環與光照 (Halos)**：在單位底下繪製發光效果。
6.  **單位實體 (Units)**：處理左右朝向翻轉 (Flipping) 與攻擊動畫偏移。
7.  **文字與血條 (Labels & Bars)**：最頂層，包含傷害數字飄字與 HP 條。

---

## 2. 顯示上下文：`display_context.cpp`

`display_context` 提供了一個唯讀 (Read-only) 的抽象介面，讓渲染層能安全地讀取遊戲狀態。

- **解耦設計 (Decoupling)**：
  - `display` 引擎不需要知道 `game_board` 或 AI 是如何運作的。它只透過 `display_context` 查詢「這個坐標的地形代碼是什麼？」、「這個坐標上有沒有單位？」。
  - **應用場景**：這種解耦設計使得 Wesnoth 可以在主遊戲畫面、存檔預覽小地圖、以及地圖編輯器中，**共用同一套 `display` 渲染程式碼**，只需傳入不同的 `display_context` 即可。

---
*第十七卷解析完畢。渲染管線的數學映射與髒矩形優化，為 Wesnoth 複雜的底層運算披上了華麗且流暢的外衣。這也是本《技術全典》的最終卷。*
*最後更新: 2026-05-17*
