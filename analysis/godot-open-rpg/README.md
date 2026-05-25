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
| Level 3 | 回合制戰鬥系統深度剖析 (Battler / Action / Stats / 傷害公式) | ✅ 已完成 | [architecture/level_3_combat_system.md](architecture/level_3_combat_system.md) |
| Level 3 | Signal Bus 與事件系統 (FieldEvents / CombatEvents) | ✅ 已完成 | [architecture/level_3_signal_bus_and_events.md](architecture/level_3_signal_bus_and_events.md) |
| Level 4 | Resource 驅動資料 與 場域系統 (.tres / Gameboard / field↔combat) | ✅ 已完成 | [architecture/level_4_resource_data_and_scene_states.md](architecture/level_4_resource_data_and_scene_states.md) |

> 每個 Level 3+ 子系統皆附「GDExtension 遷移點」小節（標註可移往 C++ 後端的純邏輯與留在 Godot 的表現層）。

## HTML 導覽層

`.md` 文件增多後，於 [`html/`](html/) 生成導覽層（不取代 .md，僅索引與呈現）：

- [`html/index.html`](html/index.html)：總覽（技術棧、Autoload、三大支柱、關鍵資料流）
- [`html/architecture.html`](html/architecture.html)：Level 1–4 彙整
- [`html/tutorial.html`](html/tutorial.html)：改造教學與 target/ 衍生計畫入口

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
