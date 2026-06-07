# 遊戲引擎與開源遊戲分析

> [← 回總索引 index.md](../index.md)。本檔收錄遊戲引擎、開源遊戲與其重寫/實作專案。

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **Luanti (Minetest)**| 遊戲引擎 | 極高 (Level 1-12) | 已遷移 | 完整的引擎剖析、Lua API 綁定、渲染管線與 13 篇開發教學。 |
| **Godot** | 遊戲引擎 | 高 (GDExtension) | 已遷移 | 核心對象系統、物理、渲染分析，以及大量 GDExtension 教學。 |
| **Veloren** | 開源遊戲 (Rust)| 高 (Full System) | 已遷移 | 包含氣候、經濟、AI 行為與網絡同步的深度分析。 |
| **OpenNefia** | 遊戲實作 (C#) | 高 (Architecture 14 篇) + HTML | 分析中 (源碼核對 2026-06-01) | Elona 開源重製引擎（C# .NET 8.0）。三大支柱：ECS（純資料 Component + EntitySystem + EntityEventBus 解耦）、IoC（thread-local 容器 + `[Dependency]` 反射注入）、YAML 資料驅動原型（可繼承可熱重載）。源碼核對修正舊分析：.NET 6.0→8.0、補全 17 項依賴（XamlX/Harmony/ImageSharp 等）。新增 14_xaml_wisp_ui.md：XamlX 編譯期將 .xaml 注入為 IL（同 Avalonia 技術，含「假裝是 Avalonia」騙過 Rider 的技巧）+ Wisp 自動版面 UI 框架。附 C++ 重寫計畫（EnTT+cereal+yaml-cpp，Godot GDExtension 方向）與 HTML 導覽層。核心 Phase 0–4 已完成（詳見 opennefia-cpp）。 |
| **opennefia-cpp** | 衍生小專案分析 (C++20) | 事後分析（Architecture 1 篇）+ HTML | 分析完成 (2026-06-01) | derived/opennefia-cpp/ 的事後架構分析。godot-free 純 C++20 引擎核心重寫（仿 medps 藍本）。Phase 0–4 全部完成：CMake 雙目標骨架（cmake 4.0+ 相容）→ ECS（EntityManager + EventBus void* 定向派發 + entt::dispatcher 廣播）→ 原型系統（yaml-cpp 拓撲繼承解析 + YAML::Clone 防污染 + ComponentLoader 零反射登錄）→ 序列化三件套（AllComponents type_list + entt_cereal_archive + save_load fold expression + FolderSaveStore）→ 地圖邏輯（MapData 稠密 tile + 可走性系統 + 整合測試）。36 test cases / 139 assertions 全綠。 |
| **T-Engine** | 遊戲引擎 | 中 (ToME4) | 已遷移 | 引擎架構分析與 17 篇模組/插件開發教學。 |
| **OpenStartbound** | 遊戲引擎 | 中 (Universe) | 已遷移 | 宇宙生成、實體層級、渲染管線與 Lua 整合分析。 |
| **VCMI** | 遊戲引擎 | 中 (H3 Clone) | 已遷移 | 伺服器/客戶端架構、Lua 整合與 C++ 核心修改教學。 |
| **Taisei** | 遊戲引擎 | 中 (Bullet Hell) | 已遷移 | 渲染引擎、任務 DSL 與 C 語言開發範例。 |
| **ASC-HQ** | 遊戲引擎 | 基礎 (Core) | 已遷移 | 核心引擎、數據管理與子系統架構分析。 |
| **cultivation-world-simulator** | AI 驅動修仙世界模擬器 (Python/FastAPI + Vue3) | Level 1-2 | 分析中 (核對 2026-06-01) | 玩家扮演「天道」觀察 LLM 全員驅動的修仙世界自行演化。v3.4.0，Python 3.10+/FastAPI/Uvicorn/WebSocket 後端 + Vue3/PixiJS 前端。Simulator.step() = 1 月/回合，20 相位（感知→AI決策→行動→社交→死亡→年度維護）。LLM 接口用 urllib 直呼 OpenAI 相容/Anthropic 原生，無 SDK 依賴，Semaphore 控制並發。設定三層：只讀 config.yml / 用戶 settings.json / 本局 RunConfig。事件以 SQLite 持久化，query/command 分離 REST API，WebSocket 即時推播 tick 狀態。 |
