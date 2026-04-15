# 專門子系統 - Advanced Strategic Command (ASC)

ASC 包含多個用於 AI、腳本、網路與遊戲事件的子系統。

## AI 系統 (`source/ai/`)

AI 系統旨在為玩家提供自動化的對手。

- **AI 介面 (`source/baseaiinterface.h`)**: 定義 AI 玩家的契約。
- **AI 實作**: 多種 AI 行為實作於 `source/ai/` 中。這些 AI 分析 `GameMap` 並向其單位與建築發布命令。
- **策略與戰術**: AI 組件處理高階策略（攻擊地點、建築內容）與低階戰術（單位部署、武器選擇）。

## Lua 腳本 (`source/lua/`)

ASC 整合了 Lua 腳本語言，以實現靈活的地圖腳本與遊戲邏輯自定義。

- **Lua 整合**: 將遊戲物件（如 `GameMap`、`Player`、`Vehicle`）暴露給 Lua 腳本。
- **地圖腳本**: Lua 腳本可嵌入到地圖文件中，以建立複雜的場景、觸發器與自定義規則。
- **模組化 (Modding) 支援**: Lua 允許在不重新編譯整個引擎的情況下輕鬆修改遊戲行為。

## 網路系統 (`source/network/`)

ASC 支援透過網路進行多人遊戲。

- **網路介面 (`source/networkinterface.h`)**: 網路通信的抽象層。
- **狀態同步**: 網路系統確保多人遊戲對話中所有玩家的遊戲狀態一致。
- **PBEM (電子郵件遊戲)**: 歷史上，ASC 對非同步多人遊戲 (PBEM) 有強大的支援。

## 事件系統 (`source/gameevents.cpp`)

一個用於地圖特定事件的複雜觸發器系統。

- **觸發器 (Triggers)**: 如「玩家 X 進入欄位 (Y, Z)」或「單位類型 A 被摧毀」等條件。
- **動作 (Actions)**: 如「生成單位類型 B」、「更改地形」或「顯示訊息」等結果。
- **史前事件 (Prehistoric Events, `source/prehistoricevents.cpp`)**: 事件系統的歷史部分，可能源於遊戲的早期版本。
