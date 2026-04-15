# VCMI 腳本系統分析 (`scripting/`)

VCMI 整合了 **Lua (LuaJIT)** 作為其主要的腳本引擎，極大地擴展了遊戲的可定制性。

## 1. Lua 整合 (`scripting/lua/`)
- **核心架構**: VCMI 通過 `LuaScriptingContext` 管理 Lua 狀態。
- **封裝器 (`LuaCallWrapper.h`, `LuaWrapper.h`)**: 用於 C++ 物件與 Lua 腳本之間的自動數據轉換。
- **序列化**: Lua 腳本的狀態（全域變數、回調等）支持序列化，確保載入存檔後腳本邏輯能無縫繼續。

## 2. Lua API (`scripting/lua/api/`)
VCMI 暴露了大量底層 API 給腳本使用：
- **`battle/`**: 戰鬥回調、AI 行為介入。
- **`events/`**: 地圖事件（如：當英雄進入特定區域）。
- **`BonusSystem.cpp`**: 允許腳本動態添加或修改 `lib/bonuses/` 中的加成。
- **對象存取**: `HeroInstance.cpp`, `TownInstance.cpp`, `StackInstance.cpp` 等，提供對遊戲實體屬性的讀寫訪問。

## 3. ERM 支援 (`scripting/erm/`)
- **ERM (Event Related Model)**: Heroes III WoG (Wake of Gods) 模組使用的原始腳本語言。
- **解析器**: VCMI 包含一個 ERM 解析器，嘗試將舊有的 ERM 腳本轉換或對應到 VCMI 的內部規則。

## 4. 腳本的應用場景
- **Mod 邏輯**: 大多數高級 Mod 使用 Lua 來實現新的遊戲機制。
- **戰役/場景腳本**: 控制特定關卡的特殊觸發器與敘事事件。
- **自定義 UI**: 腳本可以介入 UI 佈局與事件處理。
