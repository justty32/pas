# UI 與圖形系統 - Advanced Strategic Command (ASC)

ASC 的 UI 與圖形系統採用基於 SDL 與 ParaGUI 的分層架構。

## 圖形引擎: SDL (Simple DirectMedia Layer)

ASC 使用 SDL 進行底層圖形與事件處理。此抽象層允許遊戲在多個平台（Windows、Linux、macOS）執行。

- **Surface 與 Blitting**: 大多數渲染操作涉及將 Surface (SDL_Surface) 繪製到螢幕上。
- **事件處理**: SDL 的事件迴圈用於捕捉鍵盤、滑鼠與系統事件。

## UI 框架: ParaGUI (`source/libs/paragui`)

ParaGUI 是建立在 SDL 之上的跨平台 C++ GUI 函式庫。ASC 將其用於：

- **視窗管理**: 建立並管理主遊戲視窗及子視窗。
- **基礎元件**: 由 ParaGUI 提供的按鈕、標籤、文本欄位與列表框。
- **事件路由**: ParaGUI 管理事件（點擊、按鍵）向正確 UI 元件的傳遞。

## 自定義組件 (`source/widgets/`)

ASC 為策略遊戲的需求擴充了 ParaGUI 的自定義組件：

- **ASC_MainScreenWidget**: 顯示遊戲地圖與 UI 控制的主要組件。
- **地圖檢視器 (Map Viewers)**: 用於渲染六角網格與互動元素的專門組件。
- **對話框 (`source/dialogs/`)**: 用於遊戲互動的複雜 UI 組件，如單位資訊、基地管理與研究選單。

## 地圖渲染 (`source/mapdisplay.cpp`)

地圖按圖層渲染：

1.  **背景**: 繪製到六角網格上的地形紋理。
2.  **物件**: 地形物件、障礙物與資源。
3.  **建築**: 欄位上的結構實體。
4.  **單位**: 戰鬥與支援單位。
5.  **疊加層 (Overlays)**: 戰爭迷霧、選擇高亮、移動路徑與 UI 標記。

地圖顯示支援縮放、捲動及多種視覺化模式。
