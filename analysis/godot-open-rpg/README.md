# Godot-Open-RPG 分析總覽

> 本目錄為 `projects/godot-open-rpg` 的 PAS 分析工作空間。
> 來源：[GDQuest/godot-open-rpg](https://github.com/gdquest-demos/godot-open-rpg)（Godot 4 回合制 RPG 示範）

## 專案一句話簡介

由 GDQuest 製作、使用 Godot 4.5 + GDScript 4 實作的「經典日式回合制 RPG」教學示範專案，強調 **鬆耦合的事件匯流排 (Event Bus)**、**場景組合 (Composition)** 與 **Resource 驅動的戰鬥數據**。

## 分析進度

| 級別 | 主題 | 狀態 | 文件 |
| :--- | :--- | :--- | :--- |
| Level 1 | 初始探索（README / 技術棧 / 目錄） | ✅ 已完成 | [architecture/level_1_initial_exploration.md](architecture/level_1_initial_exploration.md) |
| Level 2 | 核心模組職責（Autoload / Field / Combat） | ✅ 已完成 | [architecture/level_2_core_modules.md](architecture/level_2_core_modules.md) |
| Level 3 | 戰鬥系統深度剖析 (Battler / Action / Stats) | ⏳ 待進行 | - |
| Level 4 | 場景系統 (Gameboard / Gamepiece / Cutscene) | ⏳ 待進行 | - |
| Level 5 | UI 與資產驅動流程 (Dialogic / Inventory) | ⏳ 待進行 | - |
| Level 6 | 開發教學（如何擴充一個新戰技 / 新地圖） | ⏳ 待進行 | - |

## 教學文件

| 標題 | 主題 | 文件 |
| :--- | :--- | :--- |
| 教學 01 | 從 godot-open-rpg 改造為 GDExtension 後端回合制 RPG | [tutorial/01_extraction_and_modification_guide.md](tutorial/01_extraction_and_modification_guide.md) |

## 目錄結構

- `architecture/`: Level 1-6 架構分析
- `tutorial/`: 目標導向開發教學
- `answers/`: 特定問題解答
- `details/`: 原始碼深度剖析
- `gemini_temp/`: 會話保存
- `session_log.md`: 操作日誌

## 技術棧速覽

- **引擎**: Godot 4.5 (GL Compatibility 渲染)
- **語言**: GDScript 4（全域 `class_name`、`@tool`、`@export`、`signal`）
- **第三方插件**: Dialogic（對話系統）
- **美術資產**: Kenney Tiny Town 像素美術包
- **渲染視窗**: 1920×1080 邏輯解析度 / 960×540 視窗
