# Wesnoth 專案分析 - Level 2: 核心模組權責

## 1. 程式入口與生命週期 (Entry Point & Lifecycle)
- **入口點**: `src/wesnoth.cpp`
  - 包含 `main` 與 `wesnoth_main`。
  - 初始化 SDL、設定線程、處理命令行參數。
- **啟動器**: `src/game_launcher.cpp`
  - 管理遊戲的啟動流程，包括基礎資源加載、配置初始化。

## 2. 數據序列化與 WML 引擎 (Serialization & WML Engine)
- **目錄**: `src/serialization/`
- **核心組件**: `parser.cpp`, `tokenizer.cpp`, `preprocessor.cpp`
- **職責**: 
  - 解析 Wesnoth 特有的標記語言 WML (Wesnoth Markup Language)。
  - 處理宏 (Macros) 的預處理。
  - 將 WML 數據結構轉換為 C++ 中的 `config` 對象。

## 3. 遊戲邏輯與行動 (Gameplay Logic & Actions)
- **目錄**: `src/actions/`
- **關鍵功能**:
  - `attack.cpp`: 處理戰鬥邏輯、傷害計算。
  - `move.cpp`: 處理單位移動與路徑執行。
  - `create.cpp`, `recruit.cpp`: 處理單位創建與招募。
  - `vision.cpp`: 處理戰爭迷霧 (Fog of War) 與視野計算。

## 4. 單位管理 (Unit Management)
- **目錄**: `src/units/`
- **核心對象**: `unit.cpp`, `types.cpp`
- **職責**: 定義單位的屬性（血量、經驗、抗性）、類型 (Unit Type) 與種族 (Race)。

## 5. 人工智慧 (AI System)
- **目錄**: `src/ai/`
- **架構**: 採用組合模式 (Composite Design Pattern)。
- **組件**: 
  - `composite/`: 包含 `stages`, `goals`, `aspects`。
  - `rca/`: (Recruitment and Combat AI) 負責招募與戰鬥決策的核心邏輯。
  - `lua/`: 支援使用 Lua 編寫 AI。

## 6. 使用者介面 (User Interface)
- **目錄**: `src/gui/`
- **架構**: `gui/core/` 定義了基礎框架，`gui/widgets/` 包含各種 UI 組件（按鈕、列表、窗口等）。
- **技術**: 基於 SDL2，並使用 Pango/Cairo 進行高品質的文字渲染。

## 7. 腳本系統 (Scripting)
- **目錄**: `src/lua/`, `src/scripting/`
- **職責**: 整合 Lua 腳本引擎，允許在 WML 之外進行更靈活的邏輯擴展（如自定義事件、複雜的場景邏輯）。

## 8. 路徑搜尋 (Pathfinding)
- **目錄**: `src/pathfind/`
- **職責**: 實現 A* 演算法及其變體，用於地圖導航與 AI 決策。

---
*最後更新: 2026-05-17*
