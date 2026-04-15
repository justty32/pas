# 架構概覽 - Advanced Strategic Command (ASC)

ASC (Advanced Strategic Command) 是一款使用 C++ 編寫的複雜回合制策略遊戲引擎。本文件提供其架構的高階概覽。

## 主要進入點 (Main Entry Points)

- **遊戲本體**: `source/sg.cpp` - 遊戲應用程式的主要進入點。它負責初始化 SDL、ParaGUI，並啟動處理核心遊戲迴圈的 `gamethread`。
- **地圖編輯器**: `source/edmain.cpp` - 地圖編輯器應用程式的進入點。
- **公用工具**: 其他如 `source/map2pcx.cpp` 等工具，提供用於資源處理的命令列工具。

## 高階組件交互

ASC 遵循經典的遊戲引擎架構，將邏輯與渲染分離，儘管由於程式碼的長期演進，部分界線有時較為模糊。

1.  **核心引擎**: 管理遊戲狀態，包括地圖網格、玩家及遊戲實體（單位、建築）。
2.  **UI 與圖形**: 建立在 SDL 和 ParaGUI 之上。負責處理使用者輸入，並渲染遊戲世界與 UI 元件。
3.  **數據管理**: 從自定義文本格式和二進制存檔中載入遊戲資源（圖形、聲音、單位定義、地圖數據）。
4.  **子系統**: 專用於 AI、Lua 腳本、網路功能以及事件/觸發器系統的專門組件。

## 關鍵技術

- **語言**: C++
- **圖形與輸入**: SDL (Simple DirectMedia Layer)
- **UI 框架**: ParaGUI (基於 SDL 的跨平台 C++ GUI 函式庫)
- **腳本**: Lua
- **建置系統**: Autotools (configure.ac, Makefile.am)

## 目錄結構亮點

- `source/`: 主要 C++ 原始碼。
- `source/ai/`: AI 實作。
- `source/lua/`: Lua 腳本整合。
- `source/network/`: 網路程式碼。
- `source/widgets/`: 自定義 UI 組件。
- `source/libs/`: 包含的函式庫（如 ParaGUI）。
- `data/`: 遊戲資源、地圖與設定檔。
